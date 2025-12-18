import streamlit as st
import pandas as pd
from datetime import date
from supabase_client import supabase

# Konfigurasi Akun Persediaan
INVENTORY_ACCOUNTS = ["1-1200", "1-1400", "1-1500"]

def inject_journal_css():
    st.markdown("""
        <style>
        .journal-title-card { background-color: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 5px solid #1f77b4; margin-bottom: 20px; }
        .balance-status { padding: 15px; border-radius: 8px; margin-top: 15px; font-weight: bold; }
        .status-ok { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .status-err { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=600)
def get_master_data():
    try:
        # Get COA
        res_coa = supabase.table("coa").select("account_code, account_name").order("account_code").execute()
        coa_options = ["--- Pilih Akun ---"]
        coa_map = {}
        for item in res_coa.data:
            label = f"{item['account_code']} - {item['account_name']}"
            coa_options.append(label)
            coa_map[label] = item['account_code']
        
        # Get Products
        res_prod = supabase.table("products").select("id, name, cost_price").execute()
        prod_options = {p['name']: p for p in res_prod.data}
        
        return coa_options, coa_map, prod_options
    except Exception as e:
        st.error(f"Gagal mengambil data master: {e}")
        return ["--- Pilih Akun ---"], {}, {}

def save_transaction(entry_type, tgl, desc):
    try:
        # 1. Insert Header
        header = {
            "transaction_date": str(tgl),
            "description": desc,
            "entry_type": entry_type,
            "created_by": "System"
        }
        res_h = supabase.table("journal_headers").insert(header).execute()
        if not res_h.data: return
        
        header_id = res_h.data[0]['id']
        
        # 2. Insert Lines & Stock Log
        for line in st.session_state.journal_lines_manual:
            line_data = {
                "header_id": header_id,
                "account_code": line["Kode Akun"],
                "debit": line["Debit"],
                "credit": line["Kredit"]
            }
            supabase.table("journal_lines").insert(line_data).execute()
            
            if line["is_inventory"] and line["product_id"]:
                log_data = {
                    "product_id": line["product_id"],
                    "transaction_type": line["inv_mode"],
                    "quantity": line["qty"],
                    "unit_price": line["unit_cost"],
                    "reference_id": header_id,
                    "notes": f"Jurnal: {desc}"
                }
                supabase.table("stock_logs").insert(log_data).execute()
        
        st.success("✅ Transaksi Berhasil Disimpan!")
        st.session_state.journal_lines_manual = []
        st.rerun()
    except Exception as e:
        st.error(f"Error saat menyimpan: {e}")

def jurnal_umum_form():
    inject_journal_css()
    coa_options, coa_map, prod_options = get_master_data()
    
    if "journal_lines_manual" not in st.session_state:
        st.session_state.journal_lines_manual = []

    st.markdown('<div class="journal-title-card"><h2>📝 Input Jurnal Transaksi</h2></div>', unsafe_allow_html=True)

    # 1. Header Transaksi
    with st.container(border=True):
        c1, c2, c3 = st.columns([1, 1, 2])
        with c1: entry_type = st.selectbox("Jenis", ["REGULAR", "AJP"])
        with c2: jurnal_date = st.date_input("Tanggal", value=date.today())
        with c3: description = st.text_input("Keterangan", placeholder="Contoh: Pembelian Stok")

    # 2. Form Input Baris
    with st.form("input_form", clear_on_submit=True):
        selected_account_str = st.selectbox("Pilih Akun", coa_options)
        selected_code = coa_map.get(selected_account_str, "")
        
        is_inv = selected_code in INVENTORY_ACCOUNTS
        debit_val = 0.0; credit_val = 0.0; qty_input = 0; cost_input = 0.0
        prod_id = None; inv_mode = None; note_stok = ""

        if selected_account_str != "--- Pilih Akun ---":
            if is_inv:
                col_act, col_prod = st.columns([1, 2])
                with col_act: action_type = st.radio("Aksi:", ["Masuk (Debit)", "Keluar (Kredit)"])
                with col_prod:
                    p_name = st.selectbox("Item Produk", list(prod_options.keys()))
                    p_data = prod_options.get(p_name, {})
                    prod_id = p_data.get('id')
                    sys_cost = float(p_data.get('cost_price', 0) or 0)
                
                c1, c2, c3 = st.columns(3)
                with c1: qty_input = st.number_input("Qty", min_value=1, key=f"qty_{prod_id}")
                with c2: 
                    # Key unik agar harga berubah saat produk berubah
                    cost_input = st.number_input("Harga Satuan", value=sys_cost, key=f"cost_{prod_id}")
                with c3: st.metric("Subtotal", f"Rp {qty_input * cost_input:,.0f}")
                
                total = qty_input * cost_input
                if "Masuk" in action_type: 
                    debit_val = total; inv_mode = 'IN'
                else: 
                    credit_val = total; inv_mode = 'OUT'
                note_stok = f"[{inv_mode}] {qty_input}x @{cost_input:,.0f}"
            else:
                c1, c2 = st.columns(2)
                with c1: debit_val = st.number_input("Debit (Rp)", min_value=0.0, key=f"d_{selected_code}")
                with c2: credit_val = st.number_input("Kredit (Rp)", min_value=0.0, key=f"c_{selected_code}")

        submitted = st.form_submit_button("Tambahkan Baris Akun")
        if submitted and selected_account_str != "--- Pilih Akun ---":
            st.session_state.journal_lines_manual.append({
                "Kode Akun": selected_code, "Akun": selected_account_str,
                "Debit": int(debit_val), "Kredit": int(credit_val),
                "Detail Stok": note_stok, "is_inventory": is_inv,
                "inv_mode": inv_mode, "product_id": prod_id,
                "qty": int(qty_input), "unit_cost": cost_input 
            })
            st.rerun()

    # 3. Preview Tabel
    if st.session_state.journal_lines_manual:
        df = pd.DataFrame(st.session_state.journal_lines_manual)
        st.dataframe(df[['Akun', 'Debit', 'Kredit', 'Detail Stok']], use_container_width=True, hide_index=True)
        
        balance = df['Debit'].sum() - df['Kredit'].sum()
        status_cls = "status-ok" if balance == 0 else "status-err"
        st.markdown(f'<div class="balance-status {status_cls}">Selisih: Rp {balance:,.0f}</div>', unsafe_allow_html=True)

        if st.button("💾 SIMPAN KE DATABASE", type="primary", disabled=(balance != 0)):
            save_transaction(entry_type, jurnal_date, description)
        if st.button("❌ Reset"):
            st.session_state.journal_lines_manual = []
            st.rerun()

# PENTING: Panggil fungsi utama agar halaman muncul
if __name__ == "__main__":
    jurnal_umum_form()
