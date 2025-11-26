import streamlit as st
from pathlib import Path
from PIL import Image

# --- PATH SETTINGS ---
THIS_DIR = Path(__file__).parent if "__file__" in locals() else Path.cwd()
ASSETS_DIR = THIS_DIR / "assets"

# --- GENERAL SETTINGS ---
CONTACT_EMAIL = "caisarmaldinianwar@gmail.com"
PRODUCT_NAME = "Lobster ID"
PRODUCT_TAGLINE = "Suplier Lobster favoritmu!"
PRODUCT_DESCRIPTION = """
Kelebihan dari Lobster Kami:

- Berasal dari indukan terpilih dengan kualitas tinggi
- Potensi pertumbuhan cepat
- Dikembangkan di tambak yang steril
- Ukuran tepat dan seragam


**Apa lagi yang harus diragukan? disini kami hanya menjual kualitas terbaik!**
"""

# --- MAIN SECTION ---
st.header(PRODUCT_NAME)
st.subheader(PRODUCT_TAGLINE)
left_col, right_col = st.columns((2, 1))
with left_col:
    st.text("")
    st.write(PRODUCT_DESCRIPTION)
with right_col:
    # Pastikan file 'produkk.png' ada di folder 'assets'
    product_image = Image.open(ASSETS_DIR / "produkk.png")
    st.image(product_image, width=500)

# --- FEATURES ---
st.write("")
st.write("---")
st.subheader("Bagaimana Lobster Kami Dirawat")

# DIPERBAIKI: Setiap fitur sekarang memiliki 2 elemen: [Judul, Deskripsi]
features = {
    "1.jpg": [
        "Air Steril dan Terkontrol",  # description[0] - Akan ditampilkan tebal/sebagai judul
        "Lobster kami hidup di air yang dimonitor ketat dengan sistem filterisasi terbaik. Sehingga lobster hidup dengan sehat dan bebas stres."  # description[1] - Akan ditampilkan sebagai teks biasa
    ],
    "2.jpg": [
        "Pakan Berkualiatas Tinggi",
        "Semua lobster kami, mulai dari bibit hingga dewasa diberi pakan berkualitas premium dengan persentase protein yang sesuai standar (>35%)."
    ],
    "3.jpg": [
        "Vitamin Wajib untuk Daya Tahan",
        "Selain pakan utama, kami rutin memberikan vitamin berupa Vitamin C dan E yang dicampur ke pakan."
    ],
}

for image, description in features.items():
    # Pastikan file gambar (1.jpg, 2.jpg, 3.jpg) ada di folder 'assets'
    image = Image.open(ASSETS_DIR / image)
    st.write("")
    left_col, right_col = st.columns(2)
    left_col.image(image, use_container_width=True)
    
    # Akses description[0] untuk judul (dibuat tebal)
    right_col.write(f"**{description[0]}**")
    
    # Akses description[1] untuk deskripsi (teks biasa)
    right_col.write(description[1])
