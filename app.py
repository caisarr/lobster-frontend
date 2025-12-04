import streamlit as st
import extra_streamlit_components as stx
from supabase import create_client, Client
from dotenv import load_dotenv
import os
import pandas as pd
import time

# --- 1. CONFIG PAGE (Wajib paling atas) ---
st.set_page_config(
    page_title="Lobster ID - Premium Seafood",
    page_icon="🦞",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load Env
load_dotenv()
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# --- 2. ADVANCED CSS (Hiasan HTML/CSS) ---
def inject_custom_css():
    st.markdown("""
    <style>
        /* Import Font Keren */
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
        
        :root {
            --primary-color: #FF6F61; /* Coral Lobster */
            --secondary-color: #003366; /* Deep Sea Blue */
            --bg-color: #F4F7F6;
        }

        html, body, [class*="css"] {
            font-family: 'Poppins', sans-serif;
            background-color: var(--bg-color);
            color: #333;
        }
        
        /* Hapus Header Bawaan Streamlit yang mengganggu */
        header[data-testid="stHeader"] {
            background-color: rgba(255,255,255,0.8);
            backdrop-filter: blur(10px);
        }

        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background-color: #ffffff;
            border-right: 1px solid #eaeaea;
        }
        
        /* --- STYLING TOMBOL --- */
        .stButton > button {
            background: linear-gradient(90deg, #FF6F61 0%, #ff8a75 100%);
            color: white;
            border: none;
            border-radius: 50px; /* Tombol bulat */
            padding: 12px 28px;
            font-weight: 600;
            box-shadow: 0 4px 15px rgba(255, 111, 97, 0.3);
            transition: all 0.3s ease;
        }
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(255, 111, 97, 0.5);
            background: linear-gradient(90deg, #ff8a75 0%, #FF6F61 100%);
        }
        
        /* --- STYLING CARD (Produk & Dashboard) --- */
        /* Target container yang memiliki border */
        div[data-testid="stVerticalBlock"] > div[style*="border"] {
            background: white;
            border: 1px solid rgba(0,0,0,0.05) !important;
            border-radius: 16px !important;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.02);
            transition: all 0.3s ease;
        }
        
        /* Efek Hover Keren (Kartu Mengambang) */
        div[data-testid="stVerticalBlock"] > div[style*="border"]:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
            border-color: var(--primary-color) !important;
        }

        /* --- INPUT FIELDS --- */
        .stTextInput input, .stNumberInput input {
            border-radius: 10px;
            border: 1px solid #ddd;
            padding: 10px;
        }
        .stTextInput input:focus {
            border-color: var(--primary-color);
            box-shadow: 0 0 0 2px rgba(255, 111, 97, 0.2);
        }

        /* --- METRIC CARD (Dashboard) --- */
        [data-testid="stMetricValue"] {
            font-size: 28px;
            font-weight: 700;
            color: var(--secondary-color);
        }
        
        /* Custom Footer */
        .custom-footer {
            text-align: center;
            padding: 40px 0;
            margin-top: 50px;
            color: #888;
            border-top: 1px solid #eee;
            font-size: 0.9em;
        }
    </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# --- SIDEBAR LOGO ---
with st.sidebar:
    # Menggunakan HTML untuk logo agar lebih rapi
    st.markdown("""
        <div style="text-align: center; margin-bottom: 20px;">
            <img src="https://cdn-icons-png.flaticon.com/512/3063/3063822.png" width="80" style="margin-bottom:10px;">
            <h2 style="margin:0; color:#003366;">Lobster ID</h2>
            <p style="font-size:12px; color:gray;">Premium Quality Seafood</p>
        </div>
    """, unsafe_allow_html=True)

# --- COOKIE MANAGER ---
cookie_manager = stx.CookieManager()

# --- AUTH LOGIC (Sama seperti sebelumnya) ---
def sign_up(email, password):
    try: return supabase.auth.sign_up({"email": email, "password": password})
    except Exception as e: st.error(f"Error: {e}"); return None

def sign_in(email, password):
    try: return supabase.auth.sign_in_with_password({"email": email, "password": password})
    except Exception as e: st.error(f"Error: {e}"); return None

def sign_out():
    supabase.auth.sign_out()
    st.session_state.user_email = None; st.session_state.user_role = None
    try: cookie_manager.delete("sb_token"); cookie_manager.delete("user_role")
    except: pass
    st.rerun()

def check_session():
    if "user_email" not in st.session_state or not st.session_state.user_email:
        try:
            token = cookie_manager.get("sb_token"); role = cookie_manager.get("user_role")
            if token and role:
                user = supabase.auth.get_user(token)
                if user:
                    st.session_state.user_email = user.user.email
                    st.session_state.user_role = role
        except: pass

# --- UI COMPONENTS ---

def buyer_app():
    # Navigasi Modern
    pg = st.navigation({
        "Menu Utama": [
            st.Page("views/pemesanan.py", title="Katalog Produk", icon=":material/storefront:", default=True),
            st.Page("views/info_produk.py", title="Tentang Lobster", icon=":material/water_drop:"),
            st.Page("views/Tentang_kami.py", title="Hubungi Kami", icon=":material/support_agent:"),
        ]
    })
    pg.run()

def dashboard_page():
    st.markdown("""
        <h1 style='color:#003366;'>Dashboard Penjual 📈</h1>
        <p>Ringkasan performa penjualan dan stok gudang.</p>
        <hr>
    """, unsafe_allow_html=True)
    
    try:
        orders = supabase.table("orders").select("total_amount, status").execute().data
        df_ord = pd.DataFrame(orders)
        
        omset = df_ord[df_ord['status']=='settle']['total_amount'].sum() if not df_ord.empty else 0
        pending = len(df_ord[df_ord['status']=='pending']) if not df_ord.empty else 0
        products = supabase.table("products").select("name, stock").lt("stock", 10).execute().data
        
        c1, c2, c3 = st.columns(3)
        with c1:
            with st.container(border=True):
                st.metric("💰 Total Pendapatan", f"Rp {omset:,.0f}")
        with c2:
            with st.container(border=True):
                st.metric("⏳ Menunggu Proses", f"{pending} Pesanan")
        with c3:
            with st.container(border=True):
                st.metric("📦 Stok Menipis", f"{len(products) if products else 0} SKU", delta_color="inverse")
        
        st.markdown("<br>", unsafe_allow_html=True)
        if products:
            st.warning("⚠️ Perhatian: Stok produk berikut hampir habis!")
            st.dataframe(pd.DataFrame(products), use_container_width=True, hide_index=True)
            
    except Exception as e: st.error(f"Error: {e}")

def seller_app(user_email):
    pg = st.navigation({
        "Admin Area": [
            st.Page(dashboard_page, title="Dashboard", icon=":material/dashboard:", default=True),
            st.Page("views/jurnal_umum.py", title="Input Jurnal", icon=":material/receipt_long:"),
            st.Page("views/laporan_keuangan.py", title="Laporan Keuangan", icon=":material/analytics:"),
        ]
    })
    pg.run()

def auth_screen():
    st.write("")
    st.write("")
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Card Login dengan HTML hiasan
        with st.container(border=True):
            st.markdown("""
                <div style="text-align:center; padding: 20px 0;">
                    <h1 style="color:#FF6F61; margin-bottom:0;">Welcome Back!</h1>
                    <p style="color:gray;">Masuk untuk mengakses layanan Lobster ID</p>
                </div>
            """, unsafe_allow_html=True)
            
            action = st.radio("", ["Masuk", "Daftar"], horizontal=True, label_visibility="collapsed")
            role = st.selectbox("Role", ["Pembeli", "Penjual"])
            
            with st.form("login_form"):
                email = st.text_input("Email Address", placeholder="name@example.com")
                password = st.text_input("Password", type="password")
                st.markdown("<br>", unsafe_allow_html=True)
                
                # Dynamic Button Label
                label = "🚀 Masuk Sekarang" if action == "Masuk" else "✨ Daftar Akun Baru"
                submit = st.form_submit_button(label, use_container_width=True)
            
            if submit:
                # Logic auth tetap sama
                if action == "Daftar":
                    user = sign_up(email, password)
                    if user and user.user: st.success("Akun dibuat! Silakan Login.")
                else:
                    session = sign_in(email, password)
                    if session and session.user:
                        st.session_state.user_email = session.user.email
                        st.session_state.user_role = role
                        try:
                            cookie_manager.set("sb_token", session.session.access_token)
                            cookie_manager.set("user_role", role)
                        except: pass
                        st.toast("Berhasil masuk!", icon="🎉"); time.sleep(1); st.rerun()

# --- RUN APP ---
check_session()

if not st.session_state.get("user_email"):
    auth_screen()
else:
    # Sidebar User Info yang rapi
    with st.sidebar:
        st.markdown(f"""
            <div style="background:#f0f2f6; padding:15px; border-radius:10px; margin-bottom:20px;">
                <small>Login sebagai:</small><br>
                <b>{st.session_state.user_email}</b><br>
                <span style="color:#FF6F61;">{st.session_state.user_role}</span>
            </div>
        """, unsafe_allow_html=True)
        if st.button("🚪 Logout", use_container_width=True): sign_out()

    if st.session_state.user_role == "Penjual":
        if st.session_state.user_email == "c4isar@gmail.com": seller_app(st.session_state.user_email)
        else: st.error("Akses Ditolak."); st.button("Kembali", on_click=sign_out)
    else:
        buyer_app()

    # Footer Global
    st.markdown("""
        <div class="custom-footer">
            &copy; 2025 Lobster ID Team. All Rights Reserved.<br>
            Made with ❤️ using Streamlit & Supabase
        </div>
    """, unsafe_allow_html=True)
