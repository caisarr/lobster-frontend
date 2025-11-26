import streamlit as st
import pandas as pd
from supabase_client import supabase
from datetime import date

# Akun-akun Persediaan yang memerlukan pencatatan unit
INVENTORY_ACCOUNTS = ['1-1200', '1-1400', '1-1500'] 

@st.cache_data
def get_coa_and_products():
    coa_response = supabase.table("chart_of_accounts").select("account_code, account_name").order("account_code").execute()
    coa_list = coa_response.data
    coa_map = {f"{a['account_code']} - {a['account_name']}": a['account_code'] for a in coa_list}
    coa_options = list(coa_map.keys())

    # Ambil Produk Inventori (termasuk Cost Price & Stock saat ini)
    products_response = supabase.table("products").select("id, name, inventory_account_code, cost_price, stock").in_("inventory_account_code", INVENTORY_ACCOUNTS).execute()
    products_list = products_response.data
    
    product_mapping = {f"{p['name']} (Akun: {p['inventory_account_code']})": p['id'] for p in products_list}
    
    return coa_map, coa_options, products_list, product_mapping

def jurnal_umum_form():
    coa_map, coa_options, products_list, product_mapping = get_coa_and_products()
    
    if "journal_lines_manual" not in st.session_state:
        st.session_state.journal_lines_manual = []

    with st.form("general_journal_form"):
        st.title("Jurnal Umum & Penyesuaian")
        st.subheader("Detail Transaksi")
        
        # [UPDATE] Tambahan Pilihan Tipe Jurnal
        col_type, col_date = st.columns([1, 2])
        with col_type:
            entry_type = st.selectbox("Tipe Jurnal", ["REGULAR", "AJP"], help="Pilih AJP untuk jurnal penyesuaian akhir periode.")
        with col_date:
            jurnal_date = st.date_input("Tanggal Transaksi", value=date.today())
            
        description = st.text_area("Deskripsi Jurnal", placeholder="Contoh: Pembelian Stok / Penyesuaian Sewa")

        st.subheader("Baris Jurnal")
        
        # Tampilkan tabel preview
        if st.session_state.journal_lines_manual:
            display_df = pd.DataFrame(st.session_state.journal_lines_manual)
            st.dataframe(display_df[['Akun', 'Debit', 'Kredit']], use_container_width=True, hide_index=True)
            
            total_debit = display_df['Debit'].sum()
            total_credit = display_df['Kredit'].sum()
            
            st.markdown(f"**Total Debit:** Rp {total_debit:,.0f} | **Total Kredit:** Rp {total_credit:,.0f}")
            if total_debit != total_credit and total_debit > 0:
                st.error(f"Selisih: Rp {abs(total_debit - total_credit):,.0f}")
        
        # Input Baris Baru
        col1, col2, col3 = st.columns(3)
        with col1:
            selected_account_name = st.selectbox("Akun", coa_options, key="new_line_account")
        with col2:
            debit_input = st.number_input("Debit", min_value=0.0, step=1.0, key="new_line_debit")
        with col3:
            credit_input = st.number_input("Kredit", min_value=0.0, step=1.0, key="new_line_credit")

        selected_account_code = coa_map.get(selected_account_name)
        
        # Logika Input Inventori
        is_inventory_purchase = False
        unit_qty = 0
        unit_cost = 0
        selected_product_name = None

        if selected_account_code in INVENTORY_ACCOUNTS and debit_input > 0 and credit_input == 0:
            is_inventory_purchase = True
            st.markdown("---")
            st.info("📦 Terdeteksi Pembelian Persediaan. Silakan lengkapi data unit.")
            
            relevant_product_keys = [k for k, v in product_mapping.items() 
                                     if v in [p['id'] for p in products_list if p['inventory_account_code'] == selected_account_code]]
            
            c_inv1, c_inv2, c_inv3 = st.columns(3)
            with c_inv1:
                selected_product_name = st.selectbox("Pilih Varian Produk", relevant_product_keys, key="inv_product")
            with c_inv2:
                unit_qty = st.number_input("Jumlah Unit Masuk", min_value=1, step=1, key="inv_qty")
            with c_inv3:
                unit_cost = st.number_input("Harga Pokok Satuan", min_value=0.01, step=1.0, key="inv_cost")

            calculated_cost = unit_qty * unit_cost
            if abs(calculated_cost - debit_input) > 0.01:
                st.warning(f"Total Biaya Unit (Rp {calculated_cost:,.0f}) TIDAK cocok dengan Debit (Rp {debit_input:,.0f}).")

        # Tombol Tambah Baris
        if st.form_submit_button("Tambahkan Baris"):
            if not selected_account_name or (debit_input == 0 and credit_input == 0):
                st.error("Data tidak lengkap."); st.stop()
            if debit_input > 0 and credit_input > 0:
                st.error("Isi Debit atau Kredit saja."); st.stop()
            
            if is_inventory_purchase:
                if abs((unit_qty * unit_cost) - debit_input) > 0.01:
                    st.error("Perhitungan Unit x Harga tidak sesuai dengan Debit."); st.stop()

            new_line = {
                "Kode Akun": selected_account_code,
                "Akun": selected_account_name,
                "Debit": debit_input,
                "Kredit": credit_input,
                "is_inventory": is_inventory_purchase, 
                "product_id": product_mapping.get(selected_product_name) if is_inventory_purchase else None,
                "quantity": unit_qty if is_inventory_purchase else None,
                "unit_cost": unit_cost if is_inventory_purchase else None,
            }
            st.session_state.journal_lines_manual.append(new_line)
            st.rerun()

        st.divider()

        # Tombol Simpan Jurnal
        if st.form_submit_button("Simpan Jurnal"):
            df_final = pd.DataFrame(st.session_state.journal_lines_manual)
            
            if df_final.empty or df_final['Debit'].sum() != df_final['Kredit'].sum() or df_final['Debit'].sum() == 0:
                 st.error("Jurnal harus seimbang dan tidak boleh kosong."); st.stop()
            if not description:
                st.error("Deskripsi wajib diisi."); st.stop()
            
            try:
                # 1. Header Jurnal (dengan ENTRY_TYPE)
                journal_header = supabase.table("journal_entries").insert({
                    "transaction_date": str(jurnal_date),
                    "description": description,
                    "entry_type": entry_type 
                }).execute().data[0]
                journal_id = journal_header["id"]

                lines_to_insert = []
                movements_to_insert = []
                
                for index, row in df_final.iterrows():
                    lines_to_insert.append({
                        "journal_id": journal_id,
                        "account_code": row["Kode Akun"],
                        "debit_amount": row["Debit"],
                        "credit_amount": row["Kredit"],
                    })

                    # 2. Inventory Logic (MOVING AVERAGE)
                    if row["is_inventory"]:
                        pid = int(row["product_id"])
                        qty_in = int(row["quantity"])
                        cost_in = float(row["unit_cost"])
                        
                        # Ambil data lama
                        curr_prod = next((p for p in products_list if p['id'] == pid), None)
                        if curr_prod:
                            old_stock = curr_prod.get('stock', 0) or 0
                            old_cost = curr_prod.get('cost_price', 0) or 0
                            
                            # Hitung Rata-rata Baru
                            new_stock = old_stock + qty_in
                            if new_stock > 0:
                                new_avg_cost = ((old_stock * old_cost) + (qty_in * cost_in)) / new_stock
                            else:
                                new_avg_cost = cost_in
                                
                            # Update Master Data Produk
                            supabase.table("products").update({
                                "cost_price": new_avg_cost,
                                "stock": new_stock
                            }).eq("id", pid).execute()

                        movements_to_insert.append({
                            "product_id": pid,
                            "movement_date": str(jurnal_date),
                            "movement_type": "RECEIPT", 
                            "quantity_change": qty_in,
                            "unit_cost": cost_in,
                            "reference_id": f"JURNAL-{journal_id}",
                        })

                supabase.table("journal_lines").insert(lines_to_insert).execute()
                if movements_to_insert:
                    supabase.table("inventory_movements").insert(movements_to_insert).execute()

                st.success(f"Jurnal {entry_type} (ID: {journal_id}) Berhasil Disimpan!")
                st.session_state.journal_lines_manual = [] 
                st.cache_data.clear() 
                st.rerun()

            except Exception as e:
                st.error(f"Pencatatan Gagal: {e}")

if __name__ == "__main__":
    jurnal_umum_form()
