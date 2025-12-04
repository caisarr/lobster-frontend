import streamlit as st
import pandas as pd
from supabase_client import supabase
from datetime import date

# --- CONFIG & STYLING ---
INVENTORY_ACCOUNTS = ['1-1200', '1-1400', '1-1500'] 

def inject_journal_css():
    st.markdown("""
        <style>
            /* Header Style */
            .journal-title-card {
                background: linear-gradient(120deg, #4facfe 0%, #00f2fe 100%);
                padding: 25px;
                border-radius: 15px;
                color: white;
                box-shadow: 0 4px 15px rgba(0, 242, 254, 0.3);
                margin-bottom: 25px;
            }
            .journal-title-card h2 { margin: 0; color: white; text-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            
            /* Form Container */
            .stForm {
                background-color: white;
                padding: 20px;
                border-radius: 12px;
                border: 1px solid #e0e0e0;
                box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            }
            
            /* Success/Error Message */
            .balance-status {
                padding: 15px;
                border-radius: 10px;
                font-weight: bold;
                text-align: center;
                margin-top: 10px;
            }
            .status-ok { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
            .status-err { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=60)
def get_master_data():
    try:
        coa_res = supabase.table("chart_of_accounts").select("account_code, account_name").order("account_code").execute()
        coa_options = ["--- Pilih Akun ---"] + [f"{a['account_code']} - {a['account_name']}" for a in coa_res.data]
        coa_map = {f"{a['account_code']} - {a['account_name']}": a['account_code'] for a in coa_res.data}
        
        prod_res = supabase.table("products").select("id, name, inventory_account_code, cost_price, stock").execute()
        prod_options = {f"{p['name']} (Stok: {p.get('stock', 0)})": p for p in prod_res.data}
        
        return coa_options, coa_map, prod_options
    except Exception as e:
        st.error(f"Gagal memuat data master: {e}"); return [], {}, {}

def jurnal_umum_form():
    inject_journal_css()
    coa_options, coa_map, prod_options = get_master_data()
    
    if "journal_lines_manual" not in st.session_state:
        st.session_state.journal_lines_manual = []

    # --- 1. HEADER INDAH ---
    st.markdown("""
        <div class="journal-title-card">
            <h2>📝 Input Jurnal Transaksi</h2>
            <p>Catat setiap pergerakan keuangan dengan presisi.</p>
        </div>
    """, unsafe_allow_html=True)

    # --- 2. HEADER TRANSAKSI ---
    with st.container(border=True):
        c1, c2, c3 = st.columns([1, 1, 2])
        with c1: entry_type = st.selectbox("Jenis Transaksi", ["REGULAR", "AJP"], help="AJP: Ayat Jurnal Penyesuaian")
        with c2: jurnal_date = st.date_input("Tanggal Transaksi", value=date.today())
        with c3: description = st.text_input("Keterangan", placeholder="Contoh: Pembayaran Gaji Karyawan Bulan Mei")

    # --- 3. INPUT DINAMIS ---
    st.write("")
    st.markdown("##### ➕ Tambah Rincian Akun")
    
    with st.form("input_form", clear_on_submit=True):
        selected_account_str = st.selectbox("Pilih Akun Perkiraan", coa_options)
        selected_code = coa_map.get(selected_account_str)
        
        # Logika Input
        is_inv = selected_code in INVENTORY_ACCOUNTS
        debit_val = 0.0; credit_val = 0.0
        qty_input = 0; cost_input = 0.0
        prod_id = None; inv_mode = None; note_stok = ""

        if selected_account_str != "--- Pilih Akun ---":
            if is_inv:
                st.info(f"📦 Mode Stok Aktif: {selected_account_str}")
                col_act, col_prod = st.columns([1, 2])
                with col_act: action_type = st.radio("Aksi:", ["Masuk (Debit)", "Keluar (Kredit)"])
                with col_prod:
                    prod_key = st.selectbox("Item Produk", list(prod_options.keys()))
                    prod_data = prod_options[prod_key] if prod_key else {}
                    prod_id = prod_data.get('id')
                    sys_cost = prod_data.get('cost_price', 0) or 0
                
                c1, c2, c3 = st.columns(3)
                with c1: qty_input = st.number_input("Qty", min_value=1, step=1)
                with c2: 
                    cost_input = st.number_input("Harga Satuan", min_value=0.0, value=float(sys_cost)) if "Masuk" in action_type else float(sys_cost)
                    if "Keluar" in action_type: st.caption(f"HPP: Rp {sys_cost:,.0f}")
                with c3: 
                    total = qty_input * cost_input
                    st.metric("Subtotal", f"Rp {total:,.0f}")
                
                if "Masuk" in action_type: debit_val = total; inv_mode = 'IN'
                else: credit_val = total; inv_mode = 'OUT'
                note_stok = f"[{inv_mode}] {qty_input}x @{cost_input:,.0f}"
            else:
                c1, c2 = st.columns(2)
                with c1: debit_val = st.number_input("Debit (Rp)", min_value=0.0, step=1000.0)
                with c2: credit_val = st.number_input("Kredit (Rp)", min_value=0.0, step=1000.0)

        submitted = st.form_submit_button("Tambahkan Baris Akun", use_container_width=True)
        if submitted:
            if selected_account_str == "--- Pilih Akun ---": st.error("Pilih akun terlebih dahulu!")
            elif debit_val == 0 and credit_val == 0: st.error("Nominal harus diisi!")
            else:
                st.session_state.journal_lines_manual.append({
                    "Kode Akun": selected_code, "Akun": selected_account_str,
                    "Debit": int(debit_val), "Kredit": int(credit_val),
                    "Detail Stok": note_stok, "is_inventory": is_inv,
                    "inv_mode": inv_mode, "product_id": prod_id,
                    "qty": int(qty_input), "unit_cost": cost_input 
                }); st.rerun()

    # --- 4. PREVIEW & STATUS ---
    if st.session_state.journal_lines_manual:
        df_view = pd.DataFrame(st.session_state.journal_lines_manual)
        
        # Tampilan Tabel Rapi
        st.write("###### Preview Jurnal")
        st.dataframe(
            df_view[['Akun', 'Debit', 'Kredit', 'Detail Stok']], 
            use_container_width=True, hide_index=True,
            column_config={
                "Debit": st.column_config.NumberColumn(format="Rp %d"),
                "Kredit": st.column_config.NumberColumn(format="Rp %d"),
                "Detail Stok": st.column_config.TextColumn(help="Rincian pergerakan stok")
            }
        )

        d_tot = df_view['Debit'].sum()
        c_tot = df_view['Kredit'].sum()
        balance = d_tot - c_tot
        
        # Status Balance Bar
        css_class = "status-ok" if balance == 0 else "status-err"
        msg = "✅ BALANCE / SEIMBANG" if balance == 0 else f"⚠️ TIDAK SEIMBANG (Selisih: Rp {abs(balance):,.0f})"
        
        st.markdown(f"""
            <div class="balance-status {css_class}">
                <div style="display:flex; justify-content:space-between; padding:0 20px;">
                    <span>Total Debit: Rp {d_tot:,.0f}</span>
                    <span>{msg}</span>
                    <span>Total Kredit: Rp {c_tot:,.0f}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Action Buttons
        st.write("")
        c_del, c_save = st.columns([1, 4])
        if c_del.button("❌ Hapus Data"):
            st.session_state.journal_lines_manual = []
            st.rerun()
        if c_save.button("💾 SIMPAN TRANSAKSI KE DATABASE", type="primary", use_container_width=True, disabled=(balance!=0)):
            save_transaction(entry_type, jurnal_date, description)

def save_transaction(entry_type, t_date, desc):
    try:
        # Header
        h = supabase.table("journal_entries").insert({
            "transaction_date": str(t_date), "description": desc, "entry_type": entry_type
        }).execute().data[0]
        
        lines = st.session_state.journal_lines_manual
        db_lines = []; db_moves = []
        
        for r in lines:
            db_lines.append({
                "journal_id": h['id'], "account_code": r['Kode Akun'], 
                "debit_amount": r['Debit'], "credit_amount": r['Kredit']
            })
            # Logic Stok (Update Produk & Log Movement)
            if r['is_inventory'] and r['product_id']:
                pid = r['product_id']; qty = r['qty']; cost = r['unit_cost']; mode = r['inv_mode']
                curr = supabase.table("products").select("stock, cost_price").eq("id", pid).execute().data[0]
                
                # Hitung Average Cost Baru jika Masuk
                old_s = curr.get('stock', 0); old_c = curr.get('cost_price', 0)
                new_s = old_s + qty if mode == 'IN' else old_s - qty
                new_c = ((old_s * old_c) + (qty * cost)) / new_s if (mode == 'IN' and new_s > 0) else old_c
                
                supabase.table("products").update({"stock": int(new_s), "cost_price": int(new_c)}).eq("id", pid).execute()
                db_moves.append({
                    "product_id": pid, "movement_date": str(t_date), "movement_type": "RECEIPT" if mode=='IN' else "ISSUE",
                    "quantity_change": qty if mode=='IN' else -qty, "unit_cost": int(cost if mode=='IN' else old_c),
                    "reference_id": f"JURNAL-{h['id']}"
                })
        
        supabase.table("journal_lines").insert(db_lines).execute()
        if db_moves: supabase.table("inventory_movements").insert(db_moves).execute()
        
        st.toast("Transaksi Berhasil Disimpan!", icon="🎉")
        st.session_state.journal_lines_manual = []
        st.cache_data.clear()
        st.rerun()
    except Exception as e:
        st.error(f"Gagal Menyimpan: {e}")

if __name__ == "__main__":
    jurnal_umum_form()
