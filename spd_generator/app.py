import streamlit as st

st.set_page_config(
    page_title="Generator SPD",
    page_icon="📄",
    layout="wide"
)

st.title("Generator Surat Perjalanan Dinas")

st.write("""
Aplikasi untuk mengelola master pegawai,
membuat SPD, mengisi template Word,
dan menyimpan riwayat perjalanan dinas.
""")