import streamlit as st
import pandas as pd
from supabase_client import supabase
from io import BytesIO
from datetime import date
import numpy as np

# --- 1. STYLING CSS UTAMA ---
def inject_report_css():
    st.markdown("""
        <style>
            .metric-card {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 12px;
                padding: 20px;
                text-align: center;
                box-shadow: 0 2px 10px rgba(0,0,0,0.03);
                transition: transform 0.2s;
            }
            .metric-card:hover { transform: translateY(-5px); box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
            .metric-label { font-size: 0.9rem; color: #666; font-weight: 600; text-transform: uppercase; }
            .metric-value { font-size: 1.8rem; font-weight: 700; margin: 10px 0; }
            .metric-pos { color: #28a745; }
            .metric-neg { color: #dc3545; }
            .metric-neutral { color: #007bff; }
        </style>
    """, unsafe_allow_html=True)

# --- 2. DATA FETCHING (FIX TIMEZONE) ---
@st.cache_data(ttl=60)
def fetch_all_accounting_data():
    try:
        inv = supabase.table("inventory_movements").select("*, products(name)").execute()
        lines = supabase.table("journal_lines").select("*").execute()
        entries = supabase.table("journal_entries").select("*").execute()
        coa = supabase.table("chart_of_accounts").select("*").execute()
        
        df_ent = pd.DataFrame(entries.data)
        if not df_ent.empty:
            # FIX: Convert & Remove Timezone
            df_ent['transaction_date'] = pd.to_datetime(df_ent['transaction_date'])
            if df_ent['transaction_date'].dt.tz is not None:
                df_ent['transaction_date'] = df_ent['transaction_date'].dt.tz_localize(None)
            df_ent['transaction_date'] = df_ent['transaction_date'].dt.normalize()
            
            if 'entry_type' not in df_ent.columns: df_ent['entry_type'] = 'REGULAR'
            df_ent['entry_type'] = df_ent['entry_type'].fillna('REGULAR')
        else:
            df_ent = pd.DataFrame(columns=['id', 'transaction_date', 'description', 'order_id', 'entry_type'])

        df_lines = pd.DataFrame(lines.data).fillna(0)
        return {"lines": df_lines, "entries": df_ent, "coa": pd.DataFrame(coa.data), "mov": pd.DataFrame(inv.data)}
    except Exception as e:
        st.error(f"Data Error: {e}"); return {}

def get_filtered_data(start, end):
    d = fetch_all_accounting_data()
    if not d: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    ent = d["entries"].copy(); lines = d["lines"]
    if ent.empty: return pd.DataFrame(), d["coa"], d["mov"]
    
    # Filtering aman karena timezone sudah dihapus
    mask = (ent['transaction_date'] >= pd.to_datetime(start)) & (ent['transaction_date'] <= pd.to_datetime(end))
    filt = ent.loc[mask].copy()
    if 'description' in filt.columns: filt.rename(columns={'description': 'description_entry'}, inplace=True)
    
    merged = lines.merge(filt, left_on='journal_id', right_on='id').merge(d["coa"], on='account_code')
    return merged, d["coa"], d["mov"]

# --- 3. LOGIKA KEUANGAN ---
def generate_financial_report(df, coa):
    # Neraca Saldo Helper
    def calc_tb(df_in):
        if df_in.empty: 
            tb = coa.copy(); tb['Debit']=0.0; tb['Kredit']=0.0; return tb
        tb = df_in.groupby('account_code').agg(D=('debit_amount','sum'), C=('credit_amount','sum')).reset_index()
        tb = tb.merge(coa, on='account_code', how='right').fillna(0)
        tb['Net'] = tb['D'] - tb['C']
        tb['Debit'] = tb['Net'].apply(lambda x: x if x>0 else 0)
        tb['Kredit'] = tb['Net'].apply(lambda x: abs(x) if x<0 else 0)
        return tb

    pre = df[df['entry_type'] == 'REGULAR'] if not df.empty and 'entry_type' in df.columns else df
    ajp = df[df['entry_type'] == 'AJP'] if not df.empty and 'entry_type' in df.columns else df[0:0]
    
    tb_pre = calc_tb(pre)
    tb_ajp = calc_tb(ajp)
    
    # Merge Worksheet
    ws = coa[['account_code', 'account_name', 'account_type']].copy()
    ws = ws.merge(tb_pre[['account_code','Debit','Kredit']], on='account_code', how='left').fillna(0).rename(columns={'Debit':'TB_D', 'Kredit':'TB_K'})
    ws = ws.merge(tb_ajp[['account_code','Debit','Kredit']], on='account_code', how='left').fillna(0).rename(columns={'Debit':'MJ_D', 'Kredit':'MJ_K'})
    
    ws['Net_Adj'] = (ws['TB_D'] - ws['TB_K']) + (ws['MJ_D'] - ws['MJ_K'])
    ws['Adj_D'] = ws['Net_Adj'].apply(lambda x: x if x>=0 else 0)
    ws['Adj_K'] = ws['Net_Adj'].apply(lambda x: abs(x) if x<0 else 0)
    ws['Tipe_Num'] = ws['account_code'].str[0].apply(lambda x: int(x) if str(x).isdigit() else 0)
    
    # Kalkulasi Laba Rugi & Neraca
    Rev = ws[ws['Tipe_Num'].isin([4, 8])]['Adj_K'].sum()
    Exp = ws[ws['Tipe_Num'].isin([5, 6, 9])]['Adj_D'].sum()
    Net_Income = Rev - Exp
    
    Prive = ws[ws['account_code'] == '3-1200']['Adj_D'].sum()
    Modal_Awal = ws[ws['account_code'] == '3-1100']['TB_K'].sum()
    Modal_Akhir = Modal_Awal + Net_Income - Prive
    
    return ws, Net_Income, Rev, Exp, Modal_Akhir

# --- 4. HALAMAN UTAMA ---
def show_reports_page():
    inject_report_css()
    st.title("📊 Laporan Keuangan & Analisis")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Filter")
        start_d = st.date_input("Dari Tanggal", date(date.today().year, 1, 1))
        end_d = st.date_input("Sampai Tanggal", date(date.today().year, 12, 31))
        if st.button("🔄 Refresh Data", type="primary"): 
            st.cache_data.clear(); st.rerun()

    # Process Data
    df_journal, coa, mov = get_filtered_data(start_d, end_d)
    ws, net_inc, rev, exp, equity = generate_financial_report(df_journal, coa)
    
    # --- A. METRIC CARDS ---
    c1, c2, c3, c4 = st.columns(4)
    def metric_html(label, val, color_cls):
        return f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value {color_cls}">Rp {val:,.0f}</div>
        </div>
        """
    with c1: st.markdown(metric_html("Total Pendapatan", rev, "metric-pos"), unsafe_allow_html=True)
    with c2: st.markdown(metric_html("Total Beban", exp, "metric-neg"), unsafe_allow_html=True)
    with c3: st.markdown(metric_html("Laba Bersih", net_inc, "metric-pos" if net_inc>=0 else "metric-neg"), unsafe_allow_html=True)
    with c4: st.markdown(metric_html("Modal Akhir", equity, "metric-neutral"), unsafe_allow_html=True)
    
    st.write("")
    st.write("")

    # --- B. TAB CONTENT ---
    tab1, tab2, tab3, tab4 = st.tabs(["📑 Ikhtisar Laba Rugi", "📒 Jurnal Umum Detail", "⚙️ Worksheet (Neraca Lajur)", "📦 Kartu Stok"])

    # TAB 1: INCOME STATEMENT
    with tab1:
        col_chart, col_table = st.columns([2, 1])
        with col_chart:
            st.subheader("Grafik Performa")
            chart_df = pd.DataFrame({
                "Kategori": ["Pendapatan", "Beban", "Laba Bersih"],
                "Nilai": [rev, exp, net_inc]
            })
            st.bar_chart(chart_df, x="Kategori", y="Nilai", color="#FF6F61")
        
        with col_table:
            st.subheader("Rincian")
            # Filter baris pendapatan dan beban
            df_is = ws[ws['Tipe_Num'].isin([4,5,6,8,9])].copy()
            df_is['Kategori'] = df_is['Tipe_Num'].map({4:'Pendapatan', 5:'HPP', 6:'Beban Ops', 8:'Pendapatan Lain', 9:'Beban Lain'})
            
            # Format Dataframe untuk Tampilan
            st.dataframe(
                df_is[['account_name', 'Adj_D', 'Adj_K']], 
                use_container_width=True, hide_index=True,
                column_config={
                    "account_name": "Nama Akun",
                    "Adj_D": st.column_config.NumberColumn("Debit", format="Rp %d"),
                    "Adj_K": st.column_config.NumberColumn("Kredit", format="Rp %d")
                }
            )

    # TAB 2: JURNAL UMUM (DIPERCANTIK)
    with tab2:
        st.subheader("Buku Jurnal Umum")
        if not df_journal.empty:
            df_display = df_journal.copy()
            
            # Tambahkan kolom visual untuk debit/kredit
            df_display['Debit_View'] = df_display['debit_amount']
            df_display['Credit_View'] = df_display['credit_amount']
            
            # Sorting
            df_display = df_display.sort_values(['transaction_date', 'journal_id', 'debit_amount'], ascending=[False, False, False])

            st.dataframe(
                df_display[['transaction_date', 'entry_type', 'account_name', 'description_entry', 'Debit_View', 'Credit_View']],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "transaction_date": st.column_config.DateColumn("Tanggal", format="DD/MM/YYYY"),
                    "entry_type": st.column_config.TextColumn("Tipe", width="small"),
                    "account_name": "Nama Akun",
                    "description_entry": "Keterangan",
                    "Debit_View": st.column_config.NumberColumn(
                        "Debit", format="Rp %d", 
                        help="Nominal Debit"
                    ),
                    "Credit_View": st.column_config.NumberColumn(
                        "Kredit", format="Rp %d",
                        help="Nominal Kredit"
                    )
                }
            )
        else:
            st.info("Belum ada data jurnal pada periode ini.")

    # TAB 3: WORKSHEET
    with tab3:
        st.subheader("Kertas Kerja Akuntansi (Worksheet)")
        st.dataframe(
            ws[['account_code', 'account_name', 'TB_D', 'TB_K', 'MJ_D', 'MJ_K', 'Adj_D', 'Adj_K']],
            use_container_width=True, hide_index=True,
            column_config={
                "account_code": "Kode",
                "account_name": "Nama Akun",
                "TB_D": st.column_config.NumberColumn("NS Debit", format="Rp %d"),
                "TB_K": st.column_config.NumberColumn("NS Kredit", format="Rp %d"),
                "MJ_D": st.column_config.NumberColumn("AJP Debit", format="Rp %d"),
                "MJ_K": st.column_config.NumberColumn("AJP Kredit", format="Rp %d"),
                "Adj_D": st.column_config.NumberColumn("NS Disesuaikan (D)", format="Rp %d"),
                "Adj_K": st.column_config.NumberColumn("NS Disesuaikan (K)", format="Rp %d"),
            }
        )

    # TAB 4: KARTU STOK
    with tab4:
        st.subheader("Riwayat Pergerakan Stok")
        if not mov.empty:
            st.dataframe(
                mov[['movement_date', 'product_id', 'movement_type', 'quantity_change', 'unit_cost', 'reference_id']],
                use_container_width=True, hide_index=True,
                column_config={
                    "movement_date": st.column_config.DateColumn("Tanggal"),
                    "movement_type": "Tipe",
                    "quantity_change": st.column_config.NumberColumn("Qty", format="%d"),
                    "unit_cost": st.column_config.NumberColumn("Cost/Unit", format="Rp %d"),
                    "reference_id": "Ref"
                }
            )
        else:
            st.info("Data stok kosong.")

if __name__ == "__main__":
    show_reports_page()
