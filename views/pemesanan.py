import streamlit as st
from supabase_client import supabase
from midtrans_client import create_transaction
import os

# --- HERO BANNER FUNCTION ---
def show_hero_section():
    st.markdown("""
        <style>
        .hero-banner {
            background: linear-gradient(135deg, #003366 0%, #00509E 100%);
            padding: 40px;
            border-radius: 20px;
            color: white;
            text-align: center;
            margin-bottom: 30px;
            box-shadow: 0 10px 20px rgba(0,51,102,0.2);
        }
        .hero-banner h1 {
            color: white !important;
            font-size: 2.5rem;
            margin-bottom: 10px;
        }
        .hero-banner p {
            font-size: 1.1rem;
            opacity: 0.9;
        }
        </style>
        
        <div class="hero-banner">
            <h1>Fresh From The Farm 🦞</h1>
            <p>Lobster kualitas ekspor langsung dari tambak budidaya kami ke dapur Anda.</p>
        </div>
    """, unsafe_allow_html=True)

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
    show_hero_section()
    
    products = get_products()
    if "cart" not in st.session_state: st.session_state.cart = {}

    # Grid Layout 3 Kolom
    cols = st.columns(3)
    
    for index, p in enumerate(products):
        with cols[index % 3]:
            # Container dengan border (CSS di app.py akan membuatnya melayang saat di-hover)
            with st.container(border=True):
                # Placeholder image yang lebih bagus
                img_url = p.get("image_url") if p.get("image_url") else "https://images.unsplash.com/photo-1559742811-822873691df8?auto=format&fit=crop&w=500&q=60"
                
                # Menampilkan gambar full width
                st.image(img_url, use_container_width=True)
                
                st.markdown(f"### {p['name']}")
                
                # Badge Stok menggunakan HTML
                stok = p.get('stock', 0)
                color_badge = "#d4edda" if stok > 5 else "#f8d7da"
                text_color = "#155724" if stok > 5 else "#721c24"
                st.markdown(f"""
                    <span style="background-color:{color_badge}; color:{text_color}; padding: 4px 10px; border-radius:12px; font-size:12px; font-weight:bold;">
                        Stok: {stok} Tersedia
                    </span>
                    <div style="height:10px;"></div>
                """, unsafe_allow_html=True)
                
                st.caption(p["description"][:100] + "..." if p["description"] else "Kualitas terbaik.")
                
                st.markdown(f"**Rp {p['price']:,}** / ekor")
                
                # Interactive Section
                c_qty, c_btn = st.columns([1, 2])
                with c_qty:
                    qty = st.number_input("Qty", 0, stok, key=f"q_{p['id']}", label_visibility="collapsed")
                with c_btn:
                    if st.button("🛒 Tambah", key=f"btn_{p['id']}", use_container_width=True):
                        if qty > 0:
                            st.session_state.cart[p["id"]] = {"product": p, "qty": qty}
                            st.toast(f"Berhasil ditambahkan!", icon="✅")
                        else:
                            st.warning("Pilih jumlah dulu")

def show_cart_and_payment():
    cart = st.session_state.get("cart", {})
    if not cart: return

    st.markdown("---")
    st.subheader("🛍️ Checkout Pesanan")
    
    c1, c2 = st.columns([1.5, 1])
    
    with c1:
        with st.container(border=True):
            st.write("##### Keranjang Belanja")
            total = 0
            for item in cart.values():
                sub = item["product"]["price"] * item["qty"]
                total += sub
                st.markdown(f"""
                <div style="display:flex; justify-content:space-between; border-bottom:1px solid #eee; padding:10px 0;">
                    <span><b>{item['product']['name']}</b> (x{item['qty']})</span>
                    <span>Rp {sub:,}</span>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown(f"<h3 style='text-align:right; margin-top:20px; color:#FF6F61;'>Total: Rp {total:,}</h3>", unsafe_allow_html=True)

    with c2:
        with st.container(border=True):
            st.write("##### Informasi Pengiriman")
            address = st.text_area("Alamat Lengkap", placeholder="Jl. Mawar No. 12, Jakarta Selatan...")
            
            st.info("Pembayaran aman via Midtrans (QRIS, GoPay, VA)")
            
            if st.button("💳 Bayar Sekarang", type="primary", use_container_width=True):
                if not address:
                    st.error("Alamat wajib diisi!")
                    return
                
                # Stock Check & Create Order logic (Same as before)
                try:
                    order = create_order(total, address)
                    for item in cart.values():
                        add_order_item(order["id"], item["product"]["id"], item["qty"], item["product"]["price"] * item["qty"])
                    
                    snap_token = create_transaction(order["id"], total)
                    
                    st.components.v1.html(f"""
                    <script src="https://app.sandbox.midtrans.com/snap/snap.js" data-client-key="{os.getenv('MIDTRANS_CLIENT_KEY')}"></script>
                    <button id="pay-btn" style="width:100%; background:#003366; color:white; padding:15px; border:none; border-radius:8px; font-weight:bold; cursor:pointer;">
                        LANJUT KE PEMBAYARAN
                    </button>
                    <script>document.getElementById('pay-btn').onclick = function(){{ snap.pay('{snap_token}'); }};</script>
                    """, height=600)
                except Exception as e:
                    st.error(f"Gagal memproses: {e}")

def main():
    show_products()
    show_cart_and_payment()

if __name__ == "__main__": main()
