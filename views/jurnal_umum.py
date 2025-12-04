import streamlit as st
import pandas as pd
from supabase_client import supabase
from datetime import date

# --- KONFIGURASI ---
INVENTORY_ACCOUNTS = ['1-1200', '1-1400', '1-1500'] 

@st.cache_data(ttl=60)
def get_master_data():
    """Mengambil data Akun (COA) dan Produk untuk dropdown."""
    try:
        # 1. Ambil COA
        coa_res = supabase.table("chart_of_accounts").select("account_code, account_name").order("account_code").execute()
        coa_options = ["--- Pilih Akun ---"] + [f"{a['account_code']} - {a['account_name']}" for a in coa_res.data]
        coa_map = {f"{a['account_code']} - {a['account_name']}": a['account_code'] for a in coa_res.data}

        # 2. Ambil Produk
        prod_res = supabase.table("products").select("id, name, inventory_account_code, cost_price, stock").execute()
        prod_options = {f"{p['name']} (Stok: {p.get('stock', 0)})": p for p in prod_res.data}
        
        return coa_options, coa_map, prod_options
    except Exception as e:
        st.error(f"Gagal memuat data master: {e}")
        return [], {}, {}

def jurnal_umum_form():
    # Load Data
    coa_options, coa_map, prod_options = get_master_data()
    
    if "journal_lines_manual" not in st.session_state:
        st.session_state.journal_lines_manual = []

    # --- HEADER SECTION ---
    st.markdown("""
        <style>
            .journal-header {
                background: linear-gradient(135deg, #FF6F61 0%, #FF8E53 100%);
                padding: 30px;
                border-radius: 15px;
                color: white;
                margin-bottom: 20px;
                box-shadow: 0 4px 15px rgba(255, 111, 97, 0.3);
            }
        </style>
        <div class="journal-header">
            <h2 style="margin:0; color:white;">📝 Input Jurnal Transaksi</h2>
            <p style="margin:0; opacity:0.9;">Catat transaksi harian atau penyesuaian akuntansi (AJP) di sini.</p>
        </div>
    """, unsafe_allow_html=True)
    
    # --- FORM HEADER JURNAL (Card 1) ---
    with st.container(border=True):
        st.markdown("##### 1. Informasi Dasar")
        c1, c2, c3 = st.columns([1, 1, 2])
        with c1:
            entry_type = st.selectbox("Tipe Transaksi", ["REGULAR", "AJP"], help="Pilih AJP untuk Penyesuaian.")
        with c2:
            jurnal_date = st.date_input("Tanggal", value=date.today())
        with c3:
            description = st.text_input("Keterangan / Memo", placeholder="Contoh: Pembelian Bibit Lobster")

    # --- FORM INPUT AKUN (Card 2) ---
    st.write("")
    with st.container(border=True):
        st.markdown("##### 2. Rincian Akun & Nominal")
        
        with st.form("smart_input_form", clear_on_submit=True):
            selected_account_str = st.selectbox("Cari Akun", coa_options)
            selected_code = coa_map.get(selected_account_str)
            
            # Logika Deteksi
            is_placeholder = selected_account_str == "--- Pilih Akun ---"
            is_inv = selected_code in INVENTORY_ACCOUNTS
            
            # Default Vars
            debit_val = 0.0; credit_val = 0.0
            qty_input = 0; cost_input = 0.0
            prod_id = None; inv_mode = None; note_stok = ""
            
            # Area Input Dinamis
            if is_placeholder:
                st.info("👆 Pilih akun di atas untuk mengaktifkan input nominal.")
                c_d, c_k = st.columns(2)
                c_d.number_input("Debit", disabled=True)
                c_k.number_input("Kredit", disabled=True)
                
            elif is_inv:
                st.warning(f"📦 **Mode Persediaan Aktif** ({selected_account_str})")
                st.markdown("---")
                col_act, col_prod = st.columns([1, 2])
                with col_act:
                    action_type = st.radio("Arah Stok:", ["Masuk (Beli/Retur)", "Keluar (Jual/Pakai)"])
                with col_prod:
                    prod_key = st.selectbox("Pilih Produk", list(prod_options.keys()))
                    prod_data = prod_options[prod_key] if prod_key else {}
                    prod_id = prod_data.get('id')
                    sys_cost = prod_data.get('cost_price', 0) or 0

                c_qty, c_price, c_total = st.columns(3)
                with c_qty:
                    qty_input = st.number_input("Qty (Unit)", min_value=1, step=1)
                with c_price:
                    if "Masuk" in action_type:
                        cost_input = st.number_input("Harga Beli (Rp)", min_value=0.0, step=100.0)
                    else:
                        st.caption(f"HPP Sistem: Rp {sys_cost:,.0f}")
                        cost_input = sys_cost 
                with c_total:
                    total_calc = qty_input * cost_input
                    st.metric("Total (Rp)", f"{total_calc:,.0f}")
                
                if "Masuk" in action_type:
                    debit_val = total_calc; inv_mode = 'IN'
                else:
                    credit_val = total_calc; inv_mode = 'OUT'
                
                note_stok = f"{inv_mode}: {qty_input} Unit @ {cost_input:,.0f}"
                
            else:
                # Manual Input
                c1, c2 = st.columns(2)
                with c1: debit_val = st.number_input("Debit (Rp)", min_value=0.0, step=1000.0)
                with c2: credit_val = st.number_input("Kredit (Rp)", min_value=0.0, step=1000.0)

            st.write("")
            submitted = st.form_submit_button("➕ Tambahkan Baris", use_container_width=True)
            
            if submitted:
                if is_placeholder: st.error("Pilih akun dulu.")
                elif debit_val == 0 and credit_val == 0: st.error("Nominal tidak boleh nol.")
                elif debit_val > 0 and credit_val > 0: st.error("Isi salah satu saja (Debit/Kredit).")
                else:
                    new_line = {
                        "Kode Akun": selected_code, "Akun": selected_account_str,
                        "Debit": int(round(debit_val)), "Kredit": int(round(credit_val)),
                        "Detail Stok": note_stok, "is_inventory": is_inv,
                        "inv_mode": inv_mode, "product_id": prod_id,
                        "qty": int(qty_input), "unit_cost": cost_input 
                    }
                    st.session_state.journal_lines_manual.append(new_line)
                    st.rerun()

    # --- TABEL PREVIEW (Card 3) ---
    if st.session_state.journal_lines_manual:
        st.write("")
        st.markdown("##### 3. Preview Jurnal")
        
        df_view = pd.DataFrame(st.session_state.journal_lines_manual)
        
        # Kalkulasi Total
        d_tot = df_view['Debit'].sum()
        c_tot = df_view['Kredit'].sum()
        balance = d_tot - c_tot
        
        # Tampilan Tabel
        st.dataframe(
            df_view[['Akun', 'Debit', 'Kredit', 'Detail Stok']], 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Debit": st.column_config.NumberColumn(format="Rp %d"),
                "Kredit": st.column_config.NumberColumn(format="Rp %d")
            }
        )
        
        # Footer Balance Check
        bg_color = "#d4edda" if balance == 0 else "#f8d7da"
        text_color = "#155724" if balance == 0 else "#721c24"
        status_icon = "✅ SEIMBANG" if balance == 0 else f"⚠️ SELISIH: {abs(balance):,.0f}"
        
        st.markdown(f"""
            <div style="background-color:{bg_color}; color:{text_color}; padding:15px; border-radius:10px; display:flex; justify-content:space-between; align-items:center; font-weight:bold;">
                <span>Total Debit: Rp {d_tot:,.0f}</span>
                <span>{status_icon}</span>
                <span>Total Kredit: Rp {c_tot:,.0f}</span>
            </div>
            <br>
        """, unsafe_allow_html=True)
        
        # Tombol Aksi
        col_reset, col_space, col_save = st.columns([1, 2, 1.5])
        if col_reset.button("🗑️ Reset Data"):
            st.session_state.journal_lines_manual = []
            st.rerun()
            
        if col_save.button("💾 SIMPAN TRANSAKSI", type="primary", use_container_width=True, disabled=(balance != 0)):
            save_transaction(entry_type, jurnal_date, description)
    else:
        st.info("Belum ada baris akun. Silakan tambah data di form atas.")

def save_transaction(entry_type, t_date, desc):
    lines = st.session_state.journal_lines_manual
    if not lines: return 
    
    try:
        # 1. Header
        h = supabase.table("journal_entries").insert({
            "transaction_date": str(t_date), "description": desc, "entry_type": entry_type
        }).execute().data[0]
        jid = h['id']

        db_lines = []
        db_moves = []

        for row in lines:
            # 2. Lines
            db_lines.append({
                "journal_id": jid, "account_code": row['Kode Akun'], 
                "debit_amount": row['Debit'], "credit_amount": row['Kredit']
            })
            
            # 3. Update Stok Logic
            if row['is_inventory'] and row['product_id']:
                pid = row['product_id']; qty = row['qty']; cost = row['unit_cost']; mode = row['inv_mode']
                
                curr = supabase.table("products").select("stock, cost_price").eq("id", pid).execute().data[0]
                old_s = curr.get('stock', 0) or 0; old_c = curr.get('cost_price', 0) or 0
                
                new_s = old_s + qty if mode == 'IN' else old_s - qty
                new_c = ((old_s * old_c) + (qty * cost)) / new_s if (mode == 'IN' and new_s > 0) else old_c
                
                supabase.table("products").update({
                    "stock": int(new_s), "cost_price": int(round(new_c))
                }).eq("id", pid).execute()
                
                db_moves.append({
                    "product_id": pid, "movement_date": str(t_date),
                    "movement_type": "RECEIPT" if mode == 'IN' else "ISSUE",
                    "quantity_change": qty if mode == 'IN' else -qty,
                    "unit_cost": int(round(cost if mode == 'IN' else old_c)),
                    "reference_id": f"JURNAL-{jid}"
                })

        supabase.table("journal_lines").insert(db_lines).execute()
        if db_moves: supabase.table("inventory_movements").insert(db_moves).execute()
        
        st.toast("Transaksi Berhasil Disimpan!", icon="✅")
        st.session_state.journal_lines_manual = []
        st.cache_data.clear()
        time.sleep(1)
        st.rerun()

    except Exception as e:
        st.error(f"Error Database: {e}")

if __name__ == "__main__":
    jurnal_umum_form()
