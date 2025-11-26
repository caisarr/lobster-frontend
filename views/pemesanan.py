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
    st.title("Pemesanan Produk")

    if "cart" not in st.session_state: st.session_state.cart = {}

    for p in products:
        with st.container(border=True):
            c1, c2 = st.columns([1, 3])
            with c1:
                if p.get("image_url"): st.image(p["image_url"])
            with c2:
                st.subheader(p['name'])
                st.write(p["description"])
                st.write(f"**Rp {p['price']:,}** | Stok: {p.get('stock', 0)}")
                
                qty = st.number_input(f"Beli {p['name']}", 0, p.get('stock', 0), key=f"q_{p['id']}")
                if st.button("Tambah", key=f"btn_{p['id']}") and qty > 0:
                    st.session_state.cart[p["id"]] = {"product": p, "qty": qty}
                    st.success("Masuk Keranjang")

def show_cart_and_payment():
    cart = st.session_state.get("cart", {})
    if not cart: return

    st.divider()
    st.subheader("Keranjang & Pembayaran")
    total = sum(item["product"]["price"] * item["qty"] for item in cart.values())
    
    for item in cart.values():
        st.write(f"- {item['product']['name']} (x{item['qty']}) : Rp {item['product']['price'] * item['qty']:,}")
    
    st.markdown(f"### Total: Rp {total:,}")
    address = st.text_area("Alamat Pengiriman")

    if st.button("Bayar Sekarang"):
        if not address: st.error("Isi alamat!"); return
        
        # [UPDATE] Validasi Stok Terakhir
        for pid, item in cart.items():
            curr = supabase.table("products").select("stock").eq("id", pid).execute().data[0]
            if curr['stock'] < item['qty']:
                st.error(f"Stok {item['product']['name']} habis/kurang! Sisa: {curr['stock']}")
                return

        # Proses Checkout
        order = create_order(total, address)
        for item in cart.values():
            add_order_item(order["id"], item["product"]["id"], item["qty"], item["product"]["price"] * item["qty"])

        snap_token = create_transaction(order["id"], total)
        
        st.components.v1.html(f"""
        <script src="https://app.sandbox.midtrans.com/snap/snap.js" data-client-key="{os.getenv('MIDTRANS_CLIENT_KEY')}"></script>
        <button id="pay-button" style="background:#3b82f6;color:white;padding:10px;border:none;border-radius:5px;cursor:pointer;">LANJUT BAYAR</button>
        <script>
            document.getElementById('pay-button').onclick = function() {{ snap.pay('{snap_token}'); }};
        </script>
        """, height=100)

def main():
    show_products()
    show_cart_and_payment()

if __name__ == "__main__": main()
