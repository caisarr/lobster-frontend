import re

import streamlit as st
import requests  


WEBHOOK_URL = "https://connect.pabbly.com/workflow/sendwebhookdata/IjU3NjYwNTY4MDYzMDA0MzU1MjZjNTUzMDUxMzci_pc"


def is_valid_email(email):
    #email patter, biar ke detect
    email_pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(email_pattern, email) is not None


def saran_form():
    with st.form("saran_form"):
        name = st.text_input("Nama Anda")
        email = st.text_input("Email")
        message = st.text_area("Saran untuk Peningkatan")
        submit_button = st.form_submit_button("Kirim")
    if submit_button:
         if not WEBHOOK_URL:
            st.error("Email service is not set up. Please try again later.", icon="📧")
            st.stop()

         if not name:
            st.error("Masukkan nama anda.", icon="🧑")
            st.stop()

         if not email:
            st.error("Masukkan email anda.", icon="📨")
            st.stop()

         if not is_valid_email(email):
            st.error("Tolong masukkan Email yang Valid.", icon="📧")
            st.stop()

         if not message:
            st.error("Tuliskan Saran anda.", icon="💬")
            st.stop()

        # Webhook
    
         data = {"email": email, "name": name, "message": message}
         response = requests.post(WEBHOOK_URL, json=data)

         if response.status_code == 200:
            st.success("Your message has been sent successfully! 🎉", icon="🚀")
         else:
            st.error("There was an error sending your message.", icon="😨")
