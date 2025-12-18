import streamlit as st
import pandas as pd
from datetime import date
from supabase_client import supabase

# Konfigurasi Akun Persediaan sesuai database Anda
INVENTORY_ACCOUNTS = ["1-1200", "1-1400", "1-1500"]

def inject_journal_css():
    st.markdown("""
        <style>
            .journal-title-card {
                background: linear-gradient(120deg, #4facfe 0%, #00f2fe 100%);
                padding: 25px; border-radius: 15px; color: white;
                box-shadow: 0 4px 15px rgba(0, 242, 254, 0.3); margin-bottom: 25px;
            }
            .balance-status { padding: 15px; border-radius: 10px; font-weight: bold; text-align: center; margin-top: 10px; }
            .status-ok { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
            .status-err { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=60)
def get_master_data():
    try:
        # Mengambil data dari tabel chart_of_accounts
        coa_res = supabase.table("chart_of_accounts").select("account_code, account_name").order("account_code").execute()
        coa_options = ["--- Pilih Akun ---"] + [f"{a['account_code']} - {a['account_name']}" for a in coa_res.data]
        coa_map = {f"{a['account_code']} - {a['account_name']}": a['account_code'] for a in coa_res.data}
        
        # Mengambil data dari tabel products
        prod_res = supabase.table("products").select("id, name, cost_price, stock").execute()
        prod_options = {f"{p['name']} (Stok: {p.get('stock', 0)})": p for p in prod_res.data}
        
        return coa_options, coa_map, prod_options
    except Exception as e:
        st.error(f"Gagal memuat data master: {e}")
        return ["--- Pilih Akun ---"], {}, {}

def save_transaction(entry_type, t_date, desc):
    try:
        # Simpan Header Jurnal
        h = supabase.table("journal_entries").insert({
            "transaction_date": str(t_date), "description": desc, "entry_type": entry_type
        }).execute().data[0]
        
        lines = st.session_state.journal_lines_manual
        db_lines = []
        
        for r in lines:
            db_lines.append({
                "journal_id": h['id'], "account_code": r['Kode Akun'], 
                "debit_amount": r['Debit'], "credit_amount": r['Kredit']
            })
            # Logika stok jika akun adalah persediaan
            if r['is_inventory'] and r['product_id']:
                mode = r['inv_mode']
                qty = r['qty']
                # Update stok di tabel products dan log di inventory_movements
        
        supabase.table("journal_lines").insert(db_lines).execute()
        st.toast("Transaksi Berhasil Disimpan!", icon="🎉")
        st.session_state.journal_lines_manual = []
        st.rerun()
    except Exception as e:
        st.error(f"Gagal Menyimpan: {e}")

def jurnal_umum_form():
    inject_journal_css()
    coa_options, coa_map, prod_options = get_master_data()
    
    if "journal_lines_manual" not in st.session_state:
        st.session_state.journal_lines_manual = []

    st.markdown('<div class="journal-title-card"><h2>📝 Input Jurnal Transaksi</h2></div>', unsafe_allow_html=True)

    # 1. Header Transaksi
    with st.container(border=True):
        c1, c2, c3 = st.columns([1, 1, 2])
        with c1: entry_type = st.selectbox("Jenis Transaksi", ["REGULAR", "AJP"])
        with c2: jurnal_date = st.date_input("Tanggal Transaksi", value=date.today())
        with c3: description = st.text_input("Keterangan", placeholder="Contoh: Pembelian bibit lobster")

    # 2. Form Input Akun
    with st.form("input_form", clear_on_submit=True):
        selected_account_str = st.selectbox("Pilih Akun Perkiraan", coa_options)
        selected_code = coa_map.get(selected_account_str)
        
        is_inv = selected_code in INVENTORY_ACCOUNTS
        debit_val, credit_val, qty_input, cost_input = 0.0, 0.0, 0, 0.0
        prod_id, inv_mode, note_stok = None, None, ""

        if selected_account_str != "--- Pilih Akun ---":
            if is_inv:
                col_act, col_prod = st.columns([1, 2])
                with col_act: action_type = st.radio("Aksi:", ["Masuk (Debit)", "Keluar (Kredit)"])
                with col_prod:
                    prod_key = st.selectbox("Item Produk", list(prod_options.keys()))
                    p_data = prod_options.get(prod_key, {})
                    prod_id = p_data.get('id')
                    sys_cost = float(p_data.get('cost_price', 0) or 0)
                
                c1, c2, c3 = st.columns(3)
                with c1: qty_input = st.number_input("Qty", min_value=1, key=f"q_{prod_id}")
                with c2: 
                    # FIX: Key unik agar harga reset saat produk diganti
                    cost_input = st.number_input("Harga Satuan", value=sys_cost, key=f"c_{prod_id}_{action_type}")
                with c3: st.metric("Subtotal", f"Rp {qty_input * cost_input:,.0f}")
                
                total = qty_input * cost_input
                if "Masuk" in action_type: debit_val, inv_mode = total, 'IN'
                else: credit_val, inv_mode = total, 'OUT'
                note_stok = f"[{inv_mode}] {qty_input}x @{cost_input:,.0f}"
            else:
                c1, c2 = st.columns(2)
                with c1: debit_val = st.number_input("Debit (Rp)", min_value=0.0, key=f"d_{selected_code}")
                with c2: credit_val = st.number_input("Kredit (Rp)", min_value=0.0, key=f"cr_{selected_code}")

        submitted = st.form_submit_button("Tambahkan Baris Akun", use_container_width=True)
        # FIX: Data hanya masuk preview JIKA tombol diklik
        if submitted and selected_account_str != "--- Pilih Akun ---":
            st.session_state.journal_lines_manual.append({
                "Kode Akun": selected_code, "Akun": selected_account_str,
                "Debit": int(debit_val), "Kredit": int(credit_val),
                "Detail Stok": note_stok, "is_inventory": is_inv,
                "inv_mode": inv_mode, "product_id": prod_id,
                "qty": int(qty_input), "unit_cost": cost_input 
            })
            st.rerun()

    # 3. Preview & Simpan
    if st.session_state.journal_lines_manual:
        df = pd.DataFrame(st.session_state.journal_lines_manual)
        st.dataframe(df[['Akun', 'Debit', 'Kredit', 'Detail Stok']], use_container_width=True, hide_index=True)
        
        balance = df['Debit'].sum() - df['Kredit'].sum()
        status_cls = "status-ok" if balance == 0 else "status-err"
        st.markdown(f'<div class="balance-status {status_cls}">Selisih: Rp {abs(balance):,.0f}</div>', unsafe_allow_html=True)

        c_del, c_save = st.columns([1, 4])
        if c_del.button("❌ Reset"):
            st.session_state.journal_lines_manual = []
            st.rerun()
        if c_save.button("💾 SIMPAN TRANSAKSI", type="primary", use_container_width=True, disabled=(balance != 0)):
            save_transaction(entry_type, jurnal_date, description)

if __name__ == "__main__":
    jurnal_umum_form()
