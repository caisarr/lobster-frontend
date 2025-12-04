import streamlit as st
import extra_streamlit_components as stx
from supabase import create_client, Client
from dotenv import load_dotenv
import os
import pandas as pd
import time

# --- SETUP PAGE CONFIG (Wajib di baris pertama) ---
st.set_page_config(page_title="Lobster ID", page_icon="🦞", layout="wide")

# Load Env
load_dotenv()
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# --- UTILS: CUSTOM CSS (Global Styling) ---
def inject_custom_css():
    st.markdown("""
    <style>
        /* Import Google Font */
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Poppins', sans-serif;
        }
        
        /* Background & Sidebar */
        .stApp { background-color: #F8F9FA; }
        [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #e0e0e0; }

        /* Tombol Utama - Merah Lobster */
        .stButton > button {
            background-color: #FF6F61; 
            color: white; border: none; border-radius: 8px;
            padding: 10px 24px; font-weight: 600;
            transition: all 0.3s ease;
        }
        .stButton > button:hover {
            background-color: #e65b50; box-shadow: 0 4px 6px rgba(0,0,0,0.1); color: white;
        }

        /* Metrics di Dashboard */
        [data-testid="stMetricValue"] { font-size: 24px; color: #FF6F61; }
        
        /* Card Style */
        div[data-testid="stVerticalBlock"] > div[style*="border"] {
            background-color: white;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        }
    </style>
    """, unsafe_allow_html=True)

# Panggil CSS
inject_custom_css()

# --- SIDEBAR ---
with st.sidebar:
    # Logo & Info
    st.image("assets/lobster.png", width=150)
    st.markdown("### Lobster ID")
    st.caption("Suplier Lobster Premium")
    st.write("---")

# --- COOKIE MANAGER ---
cookie_manager = stx.CookieManager()

# --- AUTH FUNCTIONS ---
def sign_up(email, password):
    try:
        user = supabase.auth.sign_up({"email": email, "password": password})
        return user
    except Exception as e:
        st.error(f"Pendaftaran Gagal: {e}")
        return None

def sign_in(email, password):
    try:
        session = supabase.auth.sign_in_with_password({"email": email, "password": password})
        return session
    except Exception as e:
        st.error(f"Login Gagal: {e}")
        return None

def sign_out():
    try:
        supabase.auth.sign_out()
    except: pass
    
    st.session_state.user_email = None
    st.session_state.user_role = None
    try:
        cookie_manager.delete("sb_token")
        cookie_manager.delete("user_role")
    except: pass
    st.rerun()

def check_session():
    if "user_email" not in st.session_state or st.session_state.user_email is None:
        try:
            token = cookie_manager.get("sb_token")
            role = cookie_manager.get("user_role")
            if token and role:
                user = supabase.auth.get_user(token)
                if user:
                    st.session_state.user_email = user.user.email
                    st.session_state.user_role = role
        except: pass

# --- APP PAGES ---

# 1. BUYER APP
def buyer_app():
    pg = st.navigation({
        "Menu Utama": [
            st.Page("views/pemesanan.py", title="Belanja Lobster", icon=":material/shopping_cart:", default=True),
            st.Page("views/info_produk.py", title="Info Produk", icon=":material/inventory_2:"),
            st.Page("views/Tentang_kami.py", title="Tentang Kami", icon=":material/info:"),
        ]
    })
    pg.run()

# 2. SELLER DASHBOARD (Dipercantik)
def dashboard_page():
    st.title("Dashboard Penjual 📊")
    st.markdown("Pantau performa bisnis Lobster ID secara real-time.")
    st.write("---")
    
    try:
        orders = supabase.table("orders").select("total_amount, status").execute().data
        df_ord = pd.DataFrame(orders)
        
        omset = 0; pending = 0
        if not df_ord.empty:
            omset = df_ord[df_ord['status']=='settle']['total_amount'].sum()
            pending = len(df_ord[df_ord['status']=='pending'])
        
        products = supabase.table("products").select("name, stock").lt("stock", 10).execute().data
        
        # UI Metrics Modern
        c1, c2, c3 = st.columns(3)
        with c1:
            with st.container(border=True):
                st.metric("Total Omset", f"Rp {omset:,.0f}", delta="Settled Orders")
        with c2:
            with st.container(border=True):
                st.metric("Order Pending", f"{pending}", delta="Perlu Proses", delta_color="inverse")
        with c3:
            with st.container(border=True):
                st.metric("Stok Kritis", f"{len(products) if products else 0} Item", delta="Segera Restock", delta_color="inverse")
        
        st.write("")
        if products:
            st.warning("⚠️ Stok Menipis (<10 Unit)")
            st.dataframe(pd.DataFrame(products), use_container_width=True)
            
    except Exception as e:
        st.error(f"Gagal memuat dashboard: {e}")

def seller_app(user_email):
    pg = st.navigation({
        "Utama": [
            st.Page(dashboard_page, title="Dashboard", icon=":material/dashboard:", default=True)
        ],
        "Keuangan": [
            st.Page("views/jurnal_umum.py", title="Jurnal Umum", icon=":material/edit_document:"),
            st.Page("views/laporan_keuangan.py", title="Laporan Keuangan", icon=":material/analytics:"),
        ]
    })
    pg.run()

# 3. AUTH SCREEN (Dipercantik)
def auth_screen():
    st.write("")
    st.write("")
    
    # Layout Tengah
    c1, c2, c3 = st.columns([1, 1.5, 1])
    
    with c2:
        with st.container(border=True):
            st.markdown("<h2 style='text-align: center; color: #2C3E50;'>Lobster ID</h2>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: gray;'>Masuk untuk mengelola pesanan atau berbelanja.</p>", unsafe_allow_html=True)
            
            action = st.selectbox("Pilih Tindakan", ["Masuk", "Buat Akun"], label_visibility="collapsed")
            role = st.radio("Sebagai:", ["Pembeli", "Penjual"], horizontal=True)
            
            st.write("---")
            with st.form("auth_form"):
                email = st.text_input("Email", placeholder="nama@email.com")
                password = st.text_input("Password", type="password", placeholder="********")
                st.write("")
                
                btn_text = "🚀 Masuk Sekarang" if action == "Masuk" else "✨ Daftar Akun"
                submit = st.form_submit_button(btn_text, use_container_width=True)
            
            if submit:
                if action == "Buat Akun":
                    user = sign_up(email, password)
                    if user and user.user:
                        st.success("Akun dibuat! Silakan Login.")
                
                elif action == "Masuk":
                    session = sign_in(email, password)
                    if session and session.user:
                        st.session_state.user_email = session.user.email
                        st.session_state.user_role = role
                        try:
                            cookie_manager.set("sb_token", session.session.access_token, expires_at=None) 
                            cookie_manager.set("user_role", role, expires_at=None)
                        except: pass

                        st.toast("Login Berhasil!", icon="🎉")
                        time.sleep(1) 
                        st.rerun()

# --- ENTRY POINT ---
check_session()

if "user_email" not in st.session_state:
    st.session_state.user_email = None

if st.session_state.user_email:
    # Sidebar User Info
    st.sidebar.write(f"👤 **{st.session_state.user_email}**")
    st.sidebar.caption(f"Role: {st.session_state.user_role}")
    if st.sidebar.button("Logout", use_container_width=True):
        sign_out()
        
    # Routing
    if st.session_state.user_role == "Penjual":
        if st.session_state.user_email == "c4isar@gmail.com": 
            seller_app(st.session_state.user_email)
        else:
            st.error("Akses Ditolak. Anda bukan Admin.")
            if st.button("Logout"): sign_out()
    else:
        buyer_app()
else:
    auth_screen()
