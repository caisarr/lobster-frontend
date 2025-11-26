import streamlit as st
import pandas as pd
from supabase_client import supabase
from datetime import date

# --- KONFIGURASI ---
# Daftar Akun yang memicu Form Stok (Sesuaikan dengan database Anda)
INVENTORY_ACCOUNTS = ['1-1200', '1-1400', '1-1500'] 

@st.cache_data(ttl=60)
def get_master_data():
    """Mengambil data Akun (COA) dan Produk untuk dropdown."""
    # 1. Ambil COA
    coa_res = supabase.table("chart_of_accounts").select("account_code, account_name").order("account_code").execute()
    # Format: "1-1200 - Persediaan Bibit"
    coa_options = [f"{a['account_code']} - {a['account_name']}" for a in coa_res.data]
    coa_map = {f"{a['account_code']} - {a['account_name']}": a['account_code'] for a in coa_res.data}

    # 2. Ambil Produk
    prod_res = supabase.table("products").select("id, name, inventory_account_code, cost_price, stock").execute()
    # Format: "Bibit Lobster Pasir (Stok: 100)"
    prod_options = {f"{p['name']} (Stok: {p.get('stock', 0)})": p for p in prod_res.data}
    
    return coa_options, coa_map, prod_options

def jurnal_umum_form():
    # Load Data
    coa_options, coa_map, prod_options = get_master_data()
    
    if "journal_lines_manual" not in st.session_state:
        st.session_state.journal_lines_manual = []

    st.title("📝 Input Jurnal Umum")
    
    # --- HEADER JURNAL ---
    with st.container(border=True):
        c1, c2 = st.columns([1, 2])
        with c1:
            entry_type = st.selectbox("Tipe Transaksi", ["REGULAR", "AJP"], help="Pilih AJP untuk Penyesuaian.")
        with c2:
            jurnal_date = st.date_input("Tanggal Transaksi", value=date.today())
        description = st.text_area("Keterangan", placeholder="Contoh: Pembelian Bibit / Penjualan Panen")

    # --- TABEL PREVIEW ---
    st.write("### Rincian Jurnal")
    if st.session_state.journal_lines_manual:
        df_view = pd.DataFrame(st.session_state.journal_lines_manual)
        st.dataframe(df_view[['Akun', 'Debit', 'Kredit', 'Detail Stok']], use_container_width=True, hide_index=True)
        
        d_tot = df_view['Debit'].sum()
        c_tot = df_view['Kredit'].sum()
        color = "green" if d_tot == c_tot else "red"
        st.markdown(f"<h4 style='text-align:right; color:{color}'>Total Debit: {d_tot:,.0f} | Total Kredit: {c_tot:,.0f}</h4>", unsafe_allow_html=True)
    else:
        st.info("Belum ada baris akun.")

    # --- FORM INPUT SMART ---
    st.divider()
    st.subheader("➕ Tambah Baris Akun")
    
    with st.form("smart_input_form", clear_on_submit=True):
        # 1. PILIH AKUN DULUAN
        selected_account_str = st.selectbox("Pilih Akun", coa_options)
        selected_code = coa_map.get(selected_account_str)
        
        # --- LOGIKA DETEKSI OTOMATIS ---
        is_inv = selected_code in INVENTORY_ACCOUNTS
        
        # Default Values
        debit_val = 0.0
        credit_val = 0.0
        qty_input = 0
        cost_input = 0.0
        prod_id = None
        inv_mode = None
        note_stok = ""
        
        # JIKA AKUN PERSEDIAAN -> TAMPILKAN FORM STOK
        if is_inv:
            st.info(f"📦 **Akun Persediaan Terdeteksi!** Silakan isi detail bibit/barang di bawah ini.")
            
            # Pilihan Aksi: Masuk (Debit) atau Keluar (Kredit)
            col_act, col_prod = st.columns([1, 2])
            with col_act:
                # User menentukan arah stok di sini
                action_type = st.radio("Arah Stok:", ["Barang Masuk (Beli/Retur)", "Barang Keluar (Jual/Pakai)"])
            with col_prod:
                # Dropdown Produk
                prod_key = st.selectbox("Pilih Produk/Bibit", list(prod_options.keys()))
                prod_data = prod_options[prod_key]
                prod_id = prod_data['id']
                sys_cost = prod_data.get('cost_price', 0) or 0

            # Input Angka
            c_qty, c_price, c_total = st.columns(3)
            with c_qty:
                qty_input = st.number_input("Jumlah Unit (Qty)", min_value=1, step=1)
            with c_price:
                # Jika Masuk -> Input Harga Beli Manual
                # Jika Keluar -> Gunakan Harga Sistem (Read Only biar akurat)
                if "Masuk" in action_type:
                    cost_input = st.number_input("Harga Beli Satuan (Rp)", min_value=0.0, step=100.0)
                else:
                    st.write(f"Harga Pokok Sistem: **Rp {sys_cost:,.0f}**")
                    cost_input = sys_cost # Pakai harga sistem
            with c_total:
                # Hitung Otomatis Total Rupiah
                total_calc = qty_input * cost_input
                st.metric("Total Nilai (Rp)", f"{total_calc:,.0f}")
            
            # AUTO-FILL DEBIT/KREDIT berdasarkan perhitungan di atas
            if "Masuk" in action_type:
                debit_val = total_calc
                inv_mode = 'IN'
            else:
                credit_val = total_calc
                inv_mode = 'OUT'
            
            note_stok = f"{inv_mode}: {qty_input} x {cost_input:,.0f}"
            
        else:
            # JIKA BUKAN PERSEDIAAN -> Input Manual Biasa
            c1, c2 = st.columns(2)
            with c1: debit_val = st.number_input("Debit (Rp)", min_value=0.0, step=1000.0)
            with c2: credit_val = st.number_input("Kredit (Rp)", min_value=0.0, step=1000.0)

        # Tombol Submit
        if st.form_submit_button("Tambahkan ke Tabel"):
            if debit_val == 0 and credit_val == 0:
                st.error("Nominal tidak boleh nol.")
            elif debit_val > 0 and credit_val > 0:
                st.error("Pilih salah satu: Debit atau Kredit.")
            else:
                # Simpan ke Session
                new_line = {
                    "Kode Akun": selected_code,
                    "Akun": selected_account_str,
                    "Debit": debit_val,
                    "Kredit": credit_val,
                    "Detail Stok": note_stok,
                    # Metadata Hidden
                    "is_inventory": is_inv,
                    "inv_mode": inv_mode,
                    "product_id": prod_id,
                    "qty": qty_input,
                    "unit_cost": cost_input
                }
                st.session_state.journal_lines_manual.append(new_line)
                st.rerun()

    # --- TOMBOL FINAL SAVE ---
    if st.button("💾 SIMPAN TRANSAKSI", type="primary", use_container_width=True):
        save_transaction(entry_type, jurnal_date, description)

def save_transaction(entry_type, t_date, desc):
    lines = st.session_state.journal_lines_manual
    if not lines: return st.error("Data kosong.")
    if abs(sum(x['Debit'] for x in lines) - sum(x['Kredit'] for x in lines)) > 1: return st.error("Jurnal Tidak Seimbang!")

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
            
            # 3. Update Stok Real (Hanya jika Inventory)
            if row['is_inventory'] and row['product_id']:
                pid = row['product_id']
                qty = row['qty']
                cost = row['unit_cost']
                mode = row['inv_mode']
                
                # Cek Stok Lama
                curr = supabase.table("products").select("stock, cost_price").eq("id", pid).execute().data[0]
                old_s = curr.get('stock', 0) or 0
                old_c = curr.get('cost_price', 0) or 0
                
                new_s, new_c = old_s, old_c
                
                if mode == 'IN':
                    new_s = old_s + qty
                    if new_s > 0: new_c = ((old_s * old_c) + (qty * cost)) / new_s
                elif mode == 'OUT':
                    new_s = old_s - qty
                
                # Update DB
                supabase.table("products").update({"stock": new_s, "cost_price": new_c}).eq("id", pid).execute()
                
                # Inventory History
                db_moves.append({
                    "product_id": pid, "movement_date": str(t_date),
                    "movement_type": "RECEIPT" if mode == 'IN' else "ISSUE",
                    "quantity_change": qty if mode == 'IN' else -qty,
                    "unit_cost": cost, "reference_id": f"JURNAL-{jid}"
                })

        supabase.table("journal_lines").insert(db_lines).execute()
        if db_moves: supabase.table("inventory_movements").insert(db_moves).execute()
        
        st.success("Berhasil Disimpan!")
        st.session_state.journal_lines_manual = []
        st.cache_data.clear()
        st.rerun()

    except Exception as e:
        st.error(f"Error: {e}")

if __name__ == "__main__":
    jurnal_umum_form()
