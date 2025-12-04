import streamlit as st
from forms.saran import saran_form

st.title("") # Kosongkan title default

# --- HERO SECTION ABOUT ---
st.markdown("""
<style>
    .about-header {
        text-align: center;
        padding: 50px 20px;
        background-color: #fff;
        border-radius: 20px;
        margin-bottom: 30px;
    }
    .about-header h1 { color: #FF6F61; font-size: 3rem; }
    .about-header p { font-size: 1.2rem; color: #555; }
</style>
<div class="about-header">
    <h1>Tentang Lobster ID</h1>
    <p>Membawa Kualitas Laut Terbaik Sejak 2023</p>
</div>
""", unsafe_allow_html=True)

# --- CONTENT SECTION ---
c1, c2 = st.columns([1, 1], gap="large")

with c1:
    st.image("assets/lobster1.png", width=300)

with c2:
    st.markdown("### Dedikasi Kami")
    st.write("""
    Lobster ID adalah pionir dalam penyediaan lobster air tawar dan laut berkualitas premium di Indonesia. 
    Kami bekerja sama langsung dengan petambak lokal untuk memastikan:
    """)
    
    # Custom List
    st.markdown("""
    <ul style="list-style-type: none; padding: 0;">
        <li style="margin-bottom: 10px;">✅ <b>Bibit Unggul</b>: Dipilih melalui seleksi genetik ketat.</li>
        <li style="margin-bottom: 10px;">✅ <b>Pakan Organik</b>: Tanpa bahan kimia berbahaya.</li>
        <li style="margin-bottom: 10px;">✅ <b>Pengiriman Cepat</b>: Garansi hidup sampai tujuan.</li>
    </ul>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    @st.dialog("Saran & Masukan")
    def show_saran_modal():
        saran_form()
        
    if st.button("✉️ Hubungi Kami / Beri Saran", use_container_width=True):
        show_saran_modal()

# --- STATS SECTION ---
st.write("")
st.write("")
col_a, col_b, col_c = st.columns(3)
col_a.metric("Pelanggan Puas", "1,200+")
col_b.metric("Mitra Petambak", "50+")
col_c.metric("Kota Jangkauan", "34 Kota")
