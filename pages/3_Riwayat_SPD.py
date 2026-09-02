import streamlit as st
from database import get_riwayat_spd


st.title(
    "Riwayat SPD"
)

data = get_riwayat_spd()

if len(data) == 0:

    st.info(
        "Belum ada SPD yang tersimpan."
    )

else:

    st.dataframe(
        data,
        use_container_width=True,
        hide_index=True
    )