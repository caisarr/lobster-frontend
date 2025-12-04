import streamlit as st
import pandas as pd
from supabase_client import supabase
from io import BytesIO
from datetime import date, timedelta
import numpy as np

# --- FORMATTING UTILITY ---
def format_rupiah(amount):
    if pd.isna(amount) or amount == '': return ''
    if amount < 0: return f"(Rp {-amount:,.0f})".replace(",", ".")
    return f"Rp {amount:,.0f}".replace(",", ".")

# --- DATA FETCHING ---
@st.cache_data(ttl=60)
def fetch_all_accounting_data():
    try:
        inv = supabase.table("inventory_movements").select("*, products(name)").execute()
        lines = supabase.table("journal_lines").select("*").execute()
        entries = supabase.table("journal_entries").select("id, transaction_date, description, order_id, entry_type").execute()
        coa = supabase.table("chart_of_accounts").select("*").execute()
        
        df_ent = pd.DataFrame(entries.data)
        if not df_ent.empty:
            df_ent['transaction_date'] = pd.to_datetime(df_ent['transaction_date']).dt.normalize()
            if 'entry_type' not in df_ent.columns: df_ent['entry_type'] = 'REGULAR'
            df_ent['entry_type'] = df_ent['entry_type'].fillna('REGULAR')
        else:
            df_ent = pd.DataFrame(columns=['id', 'transaction_date', 'description', 'order_id', 'entry_type'])

        df_lines = pd.DataFrame(lines.data).fillna(0)
        return {"lines": df_lines, "entries": df_ent, "coa": pd.DataFrame(coa.data), "mov": pd.DataFrame(inv.data)}
    except Exception as e:
        st.error(f"Error fetching data: {e}"); return {}

def get_data(start, end):
    d = fetch_all_accounting_data()
    if not d: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    ent = d["entries"].copy(); lines = d["lines"]
    if ent.empty or lines.empty: return pd.DataFrame(), d["coa"], d["mov"]
    
    mask = (ent['transaction_date'] >= pd.to_datetime(start)) & (ent['transaction_date'] <= pd.to_datetime(end))
    filt = ent.loc[mask].copy()
    if 'description' in filt.columns: filt.rename(columns={'description': 'description_entry'}, inplace=True)
    
    merged = lines.merge(filt, left_on='journal_id', right_on='id')
    merged = merged.merge(d["coa"], on='account_code')
    return merged, d["coa"], d["mov"]

# --- CALCULATION LOGIC (Sama, hanya dirapikan) ---
def calc_tb(df, coa):
    if df.empty:
        tb = coa.copy(); tb['Debit'] = 0.0; tb['Kredit'] = 0.0
    else:
        tb = df.groupby('account_code').agg(D=('debit_amount', 'sum'), C=('credit_amount', 'sum')).reset_index()
        tb = tb.merge(coa, on='account_code', how='right').fillna(0)
        tb['Net'] = tb['D'] - tb['C']
        tb['Debit'] = tb['Net'].apply(lambda x: x if x > 0 else 0)
        tb['Kredit'] = tb['Net'].apply(lambda x: abs(x) if x < 0 else 0)
    
    tb['Tipe_Num'] = tb['account_code'].str[0].apply(lambda x: int(x) if str(x).isdigit() else 0)
    return tb

def generate_financial_data(df, coa):
    pre = df[df['entry_type'] == 'REGULAR'] if not df.empty and 'entry_type' in df.columns else df
    ajp = df[df['entry_type'] == 'AJP'] if not df.empty and 'entry_type' in df.columns else df[0:0]
    
    tb_pre = calc_tb(pre, coa); tb_ajp = calc_tb(ajp, coa)
    
    # Merge untuk Worksheet
    ws = coa[['account_code', 'account_name', 'account_type']].copy()
    ws = ws.merge(tb_pre[['account_code', 'Debit', 'Kredit']], on='account_code', how='left').fillna(0).rename(columns={'Debit':'TB D', 'Kredit':'TB K'})
    ws = ws.merge(tb_ajp[['account_code', 'Debit', 'Kredit']], on='account_code', how='left').fillna(0).rename(columns={'Debit':'MJ D', 'Kredit':'MJ K'})
    
    def calc_adj(row):
        net = (row['TB D'] - row['TB K']) + (row['MJ D'] - row['MJ K'])
        return (net, 0) if net >= 0 else (0, abs(net))
    
    ws[['Adj D', 'Adj K']] = ws.apply(lambda x: pd.Series(calc_adj(x)), axis=1)
    ws['Tipe_Num'] = ws['account_code'].str[0].apply(lambda x: int(x) if str(x).isdigit() else 0)
    
    # Split Laporan
    AKUN_MODAL = '3-1100'; AKUN_PRIVE = '3-1200'
    Rev = ws[ws['Tipe_Num'].isin([4, 8])]['Adj K'].sum()
    Exp = ws[ws['Tipe_Num'].isin([5, 6, 9])]['Adj D'].sum()
    Net_Income = Rev - Exp
    
    Prive = ws[ws['account_code'] == AKUN_PRIVE]['Adj D'].sum()
    Modal_Awal = ws[ws['account_code'] == AKUN_MODAL]['TB K'].sum() # Asumsi TB K adalah modal awal periode
    Modal_Akhir = Modal_Awal + Net_Income - Prive
    
    return ws, Net_Income, Rev, Exp, Modal_Akhir

# --- VISUALIZATION COMPONENTS ---
def show_reports_page():
    # CSS Custom
    st.markdown("""
        <style>
        .report-metric {
            background-color: white; border: 1px solid #eee; padding: 20px; 
            border-radius: 10px; text-align: center; box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }
        .report-title { color: #003366; font-weight: bold; margin-bottom: 5px; }
        </style>
    """, unsafe_allow_html=True)
    
    st.title("📊 Laporan Keuangan")
    
    # Filter Sidebar
    with st.sidebar:
        st.header("Filter Periode")
        start_d = st.date_input("Mulai", date(date.today().year, 1, 1))
        end_d = st.date_input("Akhir", date(date.today().year, 12, 31))
        if st.button("🔄 Refresh Data", use_container_width=True): 
            st.cache_data.clear(); st.rerun()

    # Get Data
    df_journal, coa, mov = get_data(start_d, end_d)
    ws, net_income, rev, exp, modal_akhir = generate_financial_data(df_journal, coa)
    
    # --- EXECUTIVE SUMMARY (METRICS) ---
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
            <div class="report-metric">
                <div class="report-title">Pendapatan</div>
                <h3 style="color:#28a745;">Rp {rev:,.0f}</h3>
            </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
            <div class="report-metric">
                <div class="report-title">Beban</div>
                <h3 style="color:#dc3545;">Rp {exp:,.0f}</h3>
            </div>
        """, unsafe_allow_html=True)
    with c3:
        color = "#28a745" if net_income >= 0 else "#dc3545"
        st.markdown(f"""
            <div class="report-metric">
                <div class="report-title">Laba Bersih</div>
                <h3 style="color:{color};">Rp {net_income:,.0f}</h3>
            </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
            <div class="report-metric">
                <div class="report-title">Modal Akhir</div>
                <h3 style="color:#007bff;">Rp {modal_akhir:,.0f}</h3>
            </div>
        """, unsafe_allow_html=True)

    st.write("")
    
    # --- TABS NAVIGATION ---
    tab1, tab2, tab3, tab4 = st.tabs(["📑 Laporan Utama", "📒 Jurnal & Buku Besar", "⚙️ Kertas Kerja (Worksheet)", "📦 Stok Barang"])
    
    with tab1:
        c_left, c_right = st.columns([1, 1])
        with c_left:
            with st.container(border=True):
                st.subheader("Laba Rugi (Income Statement)")
                # Chart
                chart_data = pd.DataFrame({
                    "Kategori": ["Pendapatan", "Beban", "Laba Bersih"],
                    "Nilai": [rev, exp, net_income]
                })
                st.bar_chart(chart_data, x="Kategori", y="Nilai", color=["#28a745"])
                
                # Table Simple
                st.table(pd.DataFrame([
                    ["Total Pendapatan", format_rupiah(rev)],
                    ["Total Beban", format_rupiah(exp)],
                    ["LABA BERSIH", format_rupiah(net_income)]
                ], columns=["Item", "Nilai"]))

        with c_right:
            with st.container(border=True):
                st.subheader("Posisi Keuangan (Neraca)")
                # Asset calculation
                asset = ws[ws['Tipe_Num'].isin([1])]['Adj D'].sum() - ws[ws['Tipe_Num'].isin([1])]['Adj K'].sum()
                liab = ws[ws['Tipe_Num'].isin([2])]['Adj K'].sum() - ws[ws['Tipe_Num'].isin([2])]['Adj D'].sum()
                
                st.metric("Total Aset", format_rupiah(asset))
                st.metric("Total Liabilitas", format_rupiah(liab))
                st.metric("Total Ekuitas", format_rupiah(modal_akhir))
                st.divider()
                st.caption(f"Balance Check: {format_rupiah(asset)} = {format_rupiah(liab + modal_akhir)}")

    with tab2:
        st.subheader("Rincian Jurnal Umum")
        if not df_journal.empty:
            df_display = df_journal[['transaction_date', 'journal_id', 'account_name', 'description_entry', 'debit_amount', 'credit_amount']].copy()
            df_display.columns = ['Tanggal', 'No. Bukti', 'Akun', 'Ket', 'Debit', 'Kredit']
            st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            st.info("Tidak ada data transaksi pada periode ini.")

    with tab3:
        st.subheader("Neraca Lajur (Worksheet)")
        # Clean up columns for display
        ws_disp = ws[['account_code', 'account_name', 'TB D', 'TB K', 'MJ D', 'MJ K', 'Adj D', 'Adj K']]
        st.dataframe(ws_disp, use_container_width=True, height=500)

    with tab4:
        st.subheader("Kartu Stok Persediaan")
        if not mov.empty:
            st.dataframe(mov[['movement_date', 'product_id', 'movement_type', 'quantity_change', 'unit_cost', 'reference_id']], use_container_width=True)
        else:
            st.info("Belum ada pergerakan stok.")

if __name__ == "__main__":
    show_reports_page()
