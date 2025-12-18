def jurnal_umum_form():
    inject_journal_css()
    coa_options, coa_map, prod_options = get_master_data()
    
    if "journal_lines_manual" not in st.session_state:
        st.session_state.journal_lines_manual = []

    # --- 1. HEADER ---
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
        with c3: description = st.text_input("Keterangan", placeholder="Contoh: Pembayaran Gaji Karyawan")

    # --- 3. INPUT DINAMIS ---
    st.write("")
    st.markdown("##### ➕ Tambah Rincian Akun")
    
    with st.form("input_form", clear_on_submit=True):
        selected_account_str = st.selectbox("Pilih Akun Perkiraan", coa_options)
        selected_code = coa_map.get(selected_account_str)
        
        is_inv = selected_code in INVENTORY_ACCOUNTS
        debit_val = 0.0; credit_val = 0.0
        qty_input = 0; cost_input = 0.0
        prod_id = None; inv_mode = None; note_stok = ""

        if selected_account_str != "--- Pilih Akun ---":
            if is_inv:
                st.info(f"📦 Mode Stok Aktif: {selected_account_str}")
                col_act, col_prod = st.columns([1, 2])
                with col_act: 
                    action_type = st.radio("Aksi:", ["Masuk (Debit)", "Keluar (Kredit)"])
                with col_prod:
                    prod_key = st.selectbox("Item Produk", list(prod_options.keys()))
                    prod_data = prod_options[prod_key] if prod_key else {}
                    prod_id = prod_data.get('id')
                    sys_cost = prod_data.get('cost_price', 0) or 0
                
                c1, c2, c3 = st.columns(3)
                with c1: 
                    # Menambahkan key unik agar Qty reset saat produk ganti
                    qty_input = st.number_input("Qty", min_value=1, step=1, key=f"qty_{prod_id}")
                with c2: 
                    # Menambahkan key unik agar Harga reset mengikuti HPP produk yang dipilih
                    cost_val = float(sys_cost)
                    cost_input = st.number_input(
                        "Harga Satuan", 
                        min_value=0.0, 
                        value=cost_val, 
                        key=f"cost_{prod_id}_{action_type}"
                    )
                    if "Keluar" in action_type: st.caption(f"HPP Sistem: Rp {sys_cost:,.0f}")
                with c3: 
                    total = qty_input * cost_input
                    st.metric("Subtotal", f"Rp {total:,.0f}")
                
                if "Masuk" in action_type: 
                    debit_val = total; inv_mode = 'IN'
                else: 
                    credit_val = total; inv_mode = 'OUT'
                note_stok = f"[{inv_mode}] {qty_input}x @{cost_input:,.0f}"
            else:
                c1, c2 = st.columns(2)
                with c1: debit_val = st.number_input("Debit (Rp)", min_value=0.0, step=1000.0, key=f"deb_{selected_code}")
                with c2: credit_val = st.number_input("Kredit (Rp)", min_value=0.0, step=1000.0, key=f"cre_{selected_code}")

        submitted = st.form_submit_button("Tambahkan Baris Akun", use_container_width=True)
        
        # Logika simpan ke preview hanya berjalan saat tombol diklik (bukan saat pilih akun)
        if submitted:
            if selected_account_str == "--- Pilih Akun ---": 
                st.error("Pilih akun terlebih dahulu!")
            elif debit_val == 0 and credit_val == 0: 
                st.error("Nominal harus diisi!")
            else:
                st.session_state.journal_lines_manual.append({
                    "Kode Akun": selected_code, "Akun": selected_account_str,
                    "Debit": int(debit_val), "Kredit": int(credit_val),
                    "Detail Stok": note_stok, "is_inventory": is_inv,
                    "inv_mode": inv_mode, "product_id": prod_id,
                    "qty": int(qty_input), "unit_cost": cost_input 
                })
                st.rerun()

    # --- 4. PREVIEW & STATUS (Tetap Sama) ---
    if st.session_state.journal_lines_manual:
        df_view = pd.DataFrame(st.session_state.journal_lines_manual)
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
        
        css_class = "status-ok" if balance == 0 else "status-err"
        msg = "✅ BALANCE" if balance == 0 else f"⚠️ SELISIH: Rp {abs(balance):,.0f}"
        
        st.markdown(f"""
            <div class="balance-status {css_class}">
                <div style="display:flex; justify-content:space-between; padding:0 20px;">
                    <span>Total Debit: Rp {d_tot:,.0f}</span>
                    <span>{msg}</span>
                    <span>Total Kredit: Rp {c_tot:,.0f}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

        st.write("")
        c_del, c_save = st.columns([1, 4])
        if c_del.button("❌ Hapus Data"):
            st.session_state.journal_lines_manual = []
            st.rerun()
        if c_save.button("💾 SIMPAN TRANSAKSI KE DATABASE", type="primary", use_container_width=True, disabled=(balance!=0)):
            save_transaction(entry_type, jurnal_date, description)
