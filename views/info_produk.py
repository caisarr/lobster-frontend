import streamlit as st
from pathlib import Path

import streamlit as st  # pip install streamlit
from PIL import Image  # pip install pillow

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
- Ukuran tepat dan seragam


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
    product_image = Image.open(ASSETS_DIR / "produkk.png")
    st.image(product_image, width=500)


# --- FEATURES ---
st.write("")
st.write("---")
st.subheader("Bagaimana Lobster Kami Dirawat")
features = {
    "1.jpg": [
        "Air Steril dan Terkontrol
Lobster kami hidup di air yang di monitor ketat dengan sistem filterisasi terbaik. Sehingga lobster hidup dengan sehat dan bebas stres.
",
        
    ],
    "2.jpg": [
        "Pakan Berkualiatas Tinggi
​Semua lobster kami, mulai dari bibit hingga dewasa diberi pakan berkualitas premium dengan persentase protein yang sesuai standar (>35%).
",

    ],
    "3.jpg": [
        Vitamin Wajib untuk Daya Tahan
Selain pakan utama, kami rutin memberikan vitamin berupa Vitamin C dan E yang dicampur ke pakan.l"
        
    ],
}
for image, description in features.items():
    image = Image.open(ASSETS_DIR / image)
    st.write("")
    left_col, right_col = st.columns(2)
    left_col.image(image, use_container_width=True)
    right_col.write(f"**{description[0]}**")
    right_col.write(description[1])

