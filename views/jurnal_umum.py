import streamlit as st
import pandas as pd
from supabase_client import supabase
from datetime import date

# Akun-akun Persediaan (Sesuaikan dengan Chart of Accounts Anda)
# Pastikan kode akun ini BENAR ada di database Anda
INVENTORY_ACCOUNTS = ['1-1200', '1-1400', '1-1500'] 

@st.cache_data
def get_coa_and_products():
    # Ambil Chart of Accounts
    coa_response = supabase.table("chart_of_accounts").select("account_code, account_name").order("account_code").execute()
    coa_list = coa_response.data
    coa_map = {f"{a['account_code']} - {a['account_name']}": a['account_code'] for a in coa_list}
    coa_options = list(coa_map.keys())

    # Ambil Data Produk (ID, Nama, Akun Persediaan, Stok, Harga Pokok)
    # Penting: Mengambil 'stock' dan 'cost_price' terbaru
    products_response = supabase.table("products").select("id, name, inventory_account_code, cost_price, stock").execute()
    products_list = products_response.data
    
    # Mapping nama produk ke ID untuk dropdown
    product_mapping = {f"{p['name']} (Stok: {p.get('stock', 0)})": p['id'] for p in products_list}
    
    return coa_map, coa_options, products_list, product_mapping

def jurnal_umum_form():
    # Refresh data setiap kali halaman dibuka agar stok selalu update
    coa_map, coa_options, products_list, product_mapping = get_coa_and_products()
    
    if "journal_lines_manual" not in st.session_state:
        st.session_state.journal_lines_manual = []

    with st.form("general_journal_form"):
        st.title("Input Jurnal Umum & Penyesuaian")
        st.subheader("Detail Transaksi")
        
        # Header Jurnal
        col_type, col_date = st.columns([1, 2])
        with col_type:
            entry_type = st.selectbox("Tipe Jurnal", ["REGULAR", "AJP"], help="Pilih REGULAR untuk transaksi harian, AJP untuk penyesuaian akhir bulan.")
        with col_date:
            jurnal_date = st.date_input("Tanggal Transaksi", value=date.today())
            
        description = st.text_area("Deskripsi Jurnal", placeholder="Contoh: Pembelian 50 Bibit Lobster dari Supplier A")

        st.divider()
        st.subheader("Input Baris Jurnal")
        
        # Tabel Preview Jurnal Sementara
        if st.session_state.journal_lines_manual:
            display_df = pd.DataFrame(st.session_state.journal_lines_manual)
            # Tampilkan kolom yang relevan saja
            st.dataframe(display_df[['Akun', 'Debit', 'Kredit', 'Keterangan Tambahan']], use_container_width=True, hide_index=True)
            
            total_debit = display_df['Debit'].sum()
            total_credit = display_df['Kredit'].sum()
            
            st.markdown(f"**Total Debit:** Rp {total_debit:,.0f} | **Total Kredit:** Rp {total_credit:,.0f}")
            if total_debit != total_credit and total_debit > 0:
                st.error(f"⚠️ Tidak Seimbang! Selisih: Rp {abs(total_debit - total_credit):,.0f}")
        
        # --- FORM INPUT BARIS BARU ---
        col1, col2, col3 = st.columns([3, 1.5, 1.5])
        with col1:
            selected_account_name = st.selectbox("Pilih Akun", coa_options, key="new_line_account")
        with col2:
            debit_input = st.number_input("Debit (Rp)", min_value=0.0, step=1000.0, key="new_line_debit")
        with col3:
            credit_input = st.number_input("Kredit (Rp)", min_value=0.0, step=1000.0, key="new_line_credit")

        selected_account_code = coa_map.get(selected_account_name)
        
        # --- LOGIKA DETEKSI PEMBELIAN PERSEDIAAN ---
        is_inventory_purchase = False
        unit_qty = 0
        unit_cost = 0
        selected_product_id = None
        note = ""

        # Syarat: Akun Persediaan dipilih DAN posisi Debit (bertambah)
        if selected_account_code in INVENTORY_ACCOUNTS and debit_input > 0 and credit_input == 0:
            is_inventory_purchase = True
            st.info(f"📦 Terdeteksi Pembelian Persediaan ({selected_account_code}). Harap isi detail barang masuk:")
            
            # Filter produk yang sesuai dengan akun persediaan ini
            # (Misal: Akun 'Persediaan Bibit' hanya menampilkan produk 'Bibit Lobster')
            relevant_products = {k: v for k, v in product_mapping.items() 
                                 if v in [p['id'] for p in products_list if p.get('inventory_account_code') == selected_account_code]}
            
            # Jika tidak ada filter spesifik di data master, tampilkan semua produk
            if not relevant_products:
                relevant_products = product_mapping

            c_inv1, c_inv2, c_inv3 = st.columns(3)
            with c_inv1:
                p_name_key = st.selectbox("Pilih Produk", list(relevant_products.keys()), key="inv_product_select")
                selected_product_id = relevant_products.get(p_name_key)
            with c_inv2:
                unit_qty = st.number_input("Jumlah Unit Masuk (Qty)", min_value=1, step=1, key="inv_qty_input")
            with c_inv3:
                # Harga otomatis dihitung dari Debit / Qty, tapi bisa diedit
                estimated_cost = debit_input / unit_qty if unit_qty > 0 else 0
                unit_cost = st.number_input("Harga Pokok per Unit", min_value=0.0, value=float(estimated_cost), step=100.0, key="inv_cost_input")

            # Validasi Matematika Sederhana
            total_calc = unit_qty * unit_cost
            if abs(total_calc - debit_input) > 100: # Toleransi 100 perak
                st.warning(f"⚠️ Perhatian: Total (Qty x Harga = {total_calc:,.0f}) tidak sama dengan nilai Debit ({debit_input:,.0f}).")
            
            note = f"Beli: {unit_qty} unit @ {unit_cost:,.0f}"

        # Tombol Tambah ke Tabel Sementara
        if st.form_submit_button("Tambahkan Baris"):
            if not selected_account_name:
                st.error("Pilih akun terlebih dahulu."); st.stop()
            if debit_input == 0 and credit_input == 0:
                st.error("Nominal Debit atau Kredit harus diisi."); st.stop()
            if debit_input > 0 and credit_input > 0:
                st.error("Satu baris hanya boleh Debit ATAU Kredit, bukan keduanya."); st.stop()

            new_line = {
                "Kode Akun": selected_account_code,
                "Akun": selected_account_name,
                "Debit": debit_input,
                "Kredit": credit_input,
                "Keterangan Tambahan": note,
                # Metadata Inventory (Hidden)
                "is_inventory": is_inventory_purchase, 
                "product_id": selected_product_id,
                "quantity": unit_qty,
                "unit_cost": unit_cost
            }
            st.session_state.journal_lines_manual.append(new_line)
            st.rerun()

        st.divider()

        # --- TOMBOL FINAL SIMPAN KE DATABASE ---
        if st.form_submit_button("Simpan Jurnal & Update Stok"):
            df_final = pd.DataFrame(st.session_state.journal_lines_manual)
            
            # 1. Validasi Balance
            if df_final.empty:
                st.error("Jurnal masih kosong."); st.stop()
            if df_final['Debit'].sum() != df_final['Kredit'].sum():
                 st.error("Jurnal tidak seimbang (Unbalanced)."); st.stop()
            if not description:
                st.error("Deskripsi wajib diisi."); st.stop()
            
            try:
                # 2. Insert Header Jurnal
                journal_header = supabase.table("journal_entries").insert({
                    "transaction_date": str(jurnal_date),
                    "description": description,
                    "entry_type": entry_type
                }).execute().data[0]
                journal_id = journal_header["id"]

                lines_to_insert = []
                movements_to_insert = []
                
                # 3. Proses Setiap Baris
                for index, row in df_final.iterrows():
                    # Siapkan data untuk tabel journal_lines
                    lines_to_insert.append({
                        "journal_id": journal_id,
                        "account_code": row["Kode Akun"],
                        "debit_amount": row["Debit"],
                        "credit_amount": row["Kredit"],
                    })

                    # --- LOGIKA UPDATE STOK & HARGA RATA-RATA ---
                    if row["is_inventory"] and row["product_id"]:
                        pid = int(row["product_id"])
                        qty_in = int(row["quantity"])
                        cost_in = float(row["unit_cost"])
                        
                        # Ambil data produk terkini dari database (untuk menghindari race condition sederhana)
                        curr_prod_data = supabase.table("products").select("stock, cost_price").eq("id", pid).execute().data
                        if curr_prod_data:
                            curr_prod = curr_prod_data[0]
                            old_stock = curr_prod.get('stock', 0) or 0
                            old_cost = curr_prod.get('cost_price', 0) or 0
                            
                            # A. Hitung Stok Baru
                            new_stock = old_stock + qty_in
                            
                            # B. Hitung Moving Average Cost
                            # Rumus: (Nilai Stok Lama + Nilai Pembelian Baru) / Total Stok Baru
                            if new_stock > 0:
                                total_value = (old_stock * old_cost) + (qty_in * cost_in)
                                new_avg_cost = total_value / new_stock
                            else:
                                new_avg_cost = cost_in # Fallback jika stok 0
                                
                            # C. Update Tabel Products
                            supabase.table("products").update({
                                "cost_price": new_avg_cost,
                                "stock": new_stock
                            }).eq("id", pid).execute()
                            
                            print(f"Update Produk {pid}: Stok {old_stock}->{new_stock}, Cost {old_cost}->{new_avg_cost}")

                        # D. Siapkan data Inventory Movement (Kartu Stok)
                        movements_to_insert.append({
                            "product_id": pid,
                            "movement_date": str(jurnal_date),
                            "movement_type": "RECEIPT",  # Barang Masuk
                            "quantity_change": qty_in,
                            "unit_cost": cost_in,
                            "reference_id": f"JURNAL-{journal_id}",
                        })

                # 4. Eksekusi Insert Database
                supabase.table("journal_lines").insert(lines_to_insert).execute()
                if movements_to_insert:
                    supabase.table("inventory_movements").insert(movements_to_insert).execute()

                st.success(f"✅ Jurnal #{journal_id} berhasil disimpan! Stok produk telah bertambah.")
                
                # Reset Form
                st.session_state.journal_lines_manual = [] 
                st.cache_data.clear() # Hapus cache agar dropdown produk ter-update
                st.rerun()

            except Exception as e:
                st.error(f"Terjadi Kesalahan Database: {e}")

if __name__ == "__main__":
    jurnal_umum_form()
    
