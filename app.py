import streamlit as st
import extra_streamlit_components as stx  # Library Baru
from supabase import create_client, Client
from dotenv import load_dotenv
import os
import pandas as pd
import time

# Load Env
load_dotenv()
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# Sidebar Shared
st.sidebar.image("assets/lobster.png", width=200)
st.sidebar.markdown("Dibuat oleh Kelompok 13")

# --- COOKIE MANAGER SETUP (FITUR BARU) ---
# Fungsi ini untuk menginisialisasi manajer cookies
@st.cache_resource(experimental_allow_widgets=True)
def get_cookie_manager():
    return stx.CookieManager()

cookie_manager = get_cookie_manager()

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
    except:
        pass
    
    # Hapus Session & Cookies
    st.session_state.user_email = None
    st.session_state.user_role = None
    
    # Hapus cookie dari browser
    cookie_manager.delete("sb_token")
    cookie_manager.delete("user_role")
    
    st.rerun()

# --- FUNGSI CEK SESI OTOMATIS (AUTO LOGIN) ---
def check_session():
    # Jika session state kosong, coba cari di cookie
    if "user_email" not in st.session_state or st.session_state.user_email is None:
        token = cookie_manager.get("sb_token")
        role = cookie_manager.get("user_role")
        
        if token and role:
            try:
                # Validasi token ke Supabase
                user = supabase.auth.get_user(token)
                if user:
                    # Jika valid, restore session
                    st.session_state.user_email = user.user.email
                    st.session_state.user_role = role
                    st.toast("Sesi dipulihkan!", icon="🔄")
            except Exception as e:
                # Jika token kadaluarsa/invalid, hapus cookie
                # cookie_manager.delete("sb_token")
                pass

# --- BUYER APP (PEMBELI) ---
def buyer_app():
    pg = st.navigation({
        "Menu": [
            st.Page("views/Tentang_kami.py", title="Tentang Kami", icon=":material/info:"),
            st.Page("views/info_produk.py", title="Produk", icon=":material/inventory_2:"),
            st.Page("views/pemesanan.py", title="Pemesanan", icon=":material/shopping_cart:", default=True),
        ]
    })
    pg.run()

# --- SELLER APP (PENJUAL) ---
def dashboard_page():
    st.title("Dashboard Penjual 🦞")
    try:
        orders = supabase.table("orders").select("total_amount, status").execute().data
        df_ord = pd.DataFrame(orders)
        
        omset = 0
        pending = 0
        if not df_ord.empty:
            omset = df_ord[df_ord['status']=='settle']['total_amount'].sum()
            pending = len(df_ord[df_ord['status']=='pending'])
        
        products = supabase.table("products").select("name, stock").lt("stock", 10).execute().data
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Omset", f"Rp {omset:,.0f}")
        c2.metric("Order Pending", f"{pending}")
        c3.metric("Stok Kritis", f"{len(products) if products else 0} Item")
        
        st.divider()
        if products:
            st.warning("⚠️ Stok Menipis (<10 Unit)")
            st.dataframe(products, use_container_width=True)
            
    except Exception as e:
        st.error(f"Gagal memuat dashboard: {e}")

def seller_app(user_email):
    pg = st.navigation({
        "Utama": [
            st.Page(dashboard_page, title="Dashboard", icon=":material/dashboard:", default=True)
        ],
        "Akuntansi": [
            st.Page("views/jurnal_umum.py", title="Jurnal & AJP", icon=":material/edit_document:"),
            st.Page("views/laporan_keuangan.py", title="Laporan Keuangan", icon=":material/analytics:"),
        ]
    })
    pg.run()

# --- MAIN SCREEN (LOGIN / REGISTER) ---
def auth_screen():
    st.title("Akses Lobster ID")
    
    action = st.selectbox("Pilih Tindakan", ["Masuk", "Buat Akun"])
    role = st.radio("Masuk Sebagai:", ["Pembeli", "Penjual"])
    
    with st.form("auth_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button(action)
    
    if submit:
        if action == "Buat Akun":
            user = sign_up(email, password)
            if user and user.user:
                st.success("Akun berhasil dibuat! Silakan cek email lalu Login.")
        
        elif action == "Masuk":
            session = sign_in(email, password)
            if session and session.user:
                # 1. Set Session State
                st.session_state.user_email = session.user.email
                st.session_state.user_role = role
                
                # 2. SIMPAN COOKIES (Agar tahan refresh)
                # Token disimpan selama 7 hari
                cookie_manager.set("sb_token", session.session.access_token, expires_at=None) 
                cookie_manager.set("user_role", role, expires_at=None)
                
                st.success(f"Login Berhasil! Mengalihkan...")
                time.sleep(1) # Beri waktu cookie tersimpan
                st.rerun()

# --- ENTRY POINT ---
# 1. Jalankan pengecekan cookie di awal aplikasi
check_session()

if "user_email" not in st.session_state:
    st.session_state.user_email = None

if st.session_state.user_email:
    # Logika Pengarah Halaman
    if st.session_state.user_role == "Penjual":
        if st.session_state.user_email == "c4isar@gmail.com": 
            seller_app(st.session_state.user_email)
        else:
            st.error("Akses Ditolak. Akun ini tidak terdaftar sebagai Penjual/Admin.")
            if st.button("Logout"):
                sign_out()
    else:
        buyer_app()
    
    with st.sidebar:
        st.divider()
        # Gunakan callback sign_out untuk membersihkan cookie juga
        if st.button("Logout"):
            sign_out()
else:
    auth_screen()
