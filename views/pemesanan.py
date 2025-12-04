import streamlit as st
from supabase_client import supabase
from midtrans_client import create_transaction
import os

def get_products():
    return supabase.table("products").select("*").execute().data

def create_order(total, address):
    return supabase.table("orders").insert({
        "total_amount": total, "address": address, "status": "pending"
    }).execute().data[0]

def add_order_item(order_id, product_id, quantity, sub_total):
    supabase.table("order_items").insert({
        "order_id": order_id, "product_id": product_id, "quantity": quantity, "sub_total": sub_total
    }).execute()

def show_products():
    products = get_products()
    
    st.title("🦞 Katalog Lobster")
    st.markdown("Pilih lobster berkualitas premium langsung dari tambak kami.")
    st.write("---")

    if "cart" not in st.session_state: st.session_state.cart = {}

    # --- LAYOUT GRID (3 Kolom) ---
    cols = st.columns(3)
    
    for index, p in enumerate(products):
        # Memasukkan produk ke kolom secara bergantian
        with cols[index % 3]:
            with st.container(border=True):
                # Tampilkan Gambar (Placeholder jika kosong)
                if p.get("image_url"):
                    st.image(p["image_url"], use_container_width=True)
                else:
                    st.image("https://via.placeholder.com/300x200?text=Lobster+Image", use_container_width=True)
                
                # Info Produk
                st.markdown(f"#### {p['name']}")
                st.caption(p["description"] if p["description"] else "Deskripsi tidak tersedia.")
                
                # Harga & Stok
                c1, c2 = st.columns([2, 1])
                c1.markdown(f"**Rp {p['price']:,}**", unsafe_allow_html=True)
                c2.caption(f"Stok: {p.get('stock', 0)}")
                
                # Input Quantity & Tombol Beli
                qty = st.number_input("Jumlah", 0, p.get('stock', 0), key=f"q_{p['id']}", label_visibility="collapsed")
                
                if st.button("🛒 Masuk Keranjang", key=f"btn_{p['id']}", use_container_width=True):
                    if qty > 0:
                        st.session_state.cart[p["id"]] = {"product": p, "qty": qty}
                        st.toast(f"{p['name']} berhasil ditambahkan!", icon="✅")
                    else:
                        st.warning("Minimal pembelian 1 ekor")

def show_cart_and_payment():
    cart = st.session_state.get("cart", {})
    
    # Jangan tampilkan apa-apa jika keranjang kosong
    if not cart: return

    st.write("")
    st.write("---")
    st.subheader("🛍️ Keranjang & Pembayaran")
    
    col_cart, col_pay = st.columns([1.5, 1])
    
    # Kolom Kiri: Rincian Keranjang
    with col_cart:
        with st.container(border=True):
            st.write("**Rincian Pesanan**")
            total = 0
            for item in cart.values():
                subtotal = item["product"]["price"] * item["qty"]
                total += subtotal
                st.write(f"- **{item['product']['name']}** (x{item['qty']})")
                st.caption(f"  Rp {item['product']['price']:,} x {item['qty']} = Rp {subtotal:,}")
            
            st.divider()
            st.markdown(f"### Total: Rp {total:,}")

    # Kolom Kanan: Form Alamat & Bayar
    with col_pay:
        with st.container(border=True):
            st.write("**Informasi Pengiriman**")
            address = st.text_area("Alamat Lengkap", height=100, placeholder="Jalan, Nomor Rumah, Kota...")
            
            if st.button("💳 Bayar Sekarang", use_container_width=True, type="primary"):
                if not address: 
                    st.error("Mohon isi alamat pengiriman!")
                    return
                
                # Validasi Stok
                for pid, item in cart.items():
                    curr = supabase.table("products").select("stock").eq("id", pid).execute().data[0]
                    if curr['stock'] < item['qty']:
                        st.error(f"Stok {item['product']['name']} habis/kurang! Sisa: {curr['stock']}")
                        return

                # Proses Transaksi
                try:
                    order = create_order(total, address)
                    for item in cart.values():
                        add_order_item(order["id"], item["product"]["id"], item["qty"], item["product"]["price"] * item["qty"])

                    snap_token = create_transaction(order["id"], total)
                    
                    # Pop-up Midtrans
                    st.components.v1.html(f"""
                    <script src="https://app.sandbox.midtrans.com/snap/snap.js" data-client-key="{os.getenv('MIDTRANS_CLIENT_KEY')}"></script>
                    <div style="text-align: center; margin-top: 20px;">
                        <button id="pay-button" style="background:#FF6F61;color:white;padding:12px 24px;border:none;border-radius:8px;cursor:pointer;font-weight:bold;">
                            LANJUTKAN PEMBAYARAN
                        </button>
                    </div>
                    <script>
                        document.getElementById('pay-button').onclick = function() {{ snap.pay('{snap_token}'); }};
                    </script>
                    """, height=600, scrolling=True)
                    
                except Exception as e:
                    st.error(f"Terjadi kesalahan transaksi: {e}")

def main():
    show_products()
    show_cart_and_payment()

if __name__ == "__main__": main()
