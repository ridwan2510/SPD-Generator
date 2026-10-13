import io
import re
import zipfile
from pathlib import Path
import streamlit as st

from services.tte_service import ambil_daftar_dokumen_tte, unduh_rentang_dokumen_tte

st.set_page_config(page_title="Download SPD Bulk", page_icon="📥", layout="wide")
st.title("📥 Download SPD Bulk — TTE Kemenag")
st.caption("Ambil dokumen dari daftar TTE yang bisa diakses oleh akun Anda, pilih rentang nomor, lalu unduh sebagai ZIP.")
st.warning("Nomor mengikuti urutan baris pada respons daftar TTE, bukan nomor surat SPD. Hanya dokumen berstatus FINAL yang diunduh sebagai PDF; Draft/Sedang Proses akan dicatat sebagai dilewati.")

if st.button("🔄 Muat / Perbarui Daftar TTE", type="primary"):
    with st.spinner("Menghubungkan ke TTE Kemenag dan membaca daftar dokumen..."):
        try:
            daftar = ambil_daftar_dokumen_tte()
            st.session_state["tte_bulk_daftar"] = daftar
            st.session_state["tte_bulk_error"] = None
        except Exception as exc:
            st.session_state["tte_bulk_daftar"] = []
            st.session_state["tte_bulk_error"] = str(exc)

if st.session_state.get("tte_bulk_error"):
    st.error(st.session_state["tte_bulk_error"])
    st.info("Jika endpoint JSON tidak dapat diakses, periksa login dan konfigurasi [tte] pada Streamlit Secrets. Jangan membagikan cookie atau token sesi.")

daftar = st.session_state.get("tte_bulk_daftar", [])
if daftar:
    st.success(f"Berhasil membaca {len(daftar)} baris dari daftar TTE.")
    with st.expander("Pratinjau daftar TTE", expanded=True):
        st.dataframe([
            {"No. urut": x["nomor"], "Waktu": x.get("waktu", ""), "Perihal Dokumen": x["ringkasan"], "Status": x.get("status", ""), "Tombol": x.get("label_unduh", ""), "PDF FINAL siap": "Ya" if x.get("final") and x.get("tautan_unduh") else "Tidak"}
            for x in daftar
        ], use_container_width=True, hide_index=True)

    c1, c2 = st.columns(2)
    with c1:
        awal = st.number_input("Nomor awal", min_value=1, max_value=len(daftar), value=1, step=1)
    with c2:
        akhir = st.number_input("Nomor akhir", min_value=1, max_value=len(daftar), value=min(10, len(daftar)), step=1)

    if awal > akhir:
        st.error("Nomor awal harus lebih kecil atau sama dengan nomor akhir.")
    else:
        pilihan = daftar[int(awal)-1:int(akhir)]
        tersedia = sum(1 for x in pilihan if x.get("final") and x.get("tautan_unduh"))
        st.info(f"Rentang {int(awal)}–{int(akhir)}: {len(pilihan)} baris; {tersedia} dokumen FINAL memiliki tautan unduh.")
        if tersedia < len(pilihan):
            st.warning("Dokumen Draft/Sedang Proses tidak diunduh karena tombolnya bukan PDF final. Dokumen FINAL tanpa tautan yang valid akan dicatat gagal; aplikasi tidak menebak URL.")

        if st.button("📦 Unduh Rentang ke ZIP", type="primary", disabled=(awal > akhir or tersedia == 0)):
            arsip = io.BytesIO()
            hasil = []
            progress = st.progress(0.0, text="Memulai unduhan...")
            try:
                hasil_download = unduh_rentang_dokumen_tte(pilihan)
            except Exception as exc:
                hasil_download = [
                    {"nomor": item["nomor"], "sukses": False, "pesan": f"Login/akses TTE gagal: {exc}", "data": None}
                    for item in pilihan
                ]
            with zipfile.ZipFile(arsip, "w", zipfile.ZIP_DEFLATED) as zf:
                for idx, (item, unduhan) in enumerate(zip(pilihan, hasil_download), start=1):
                    label = item["ringkasan"][:180]
                    if unduhan["sukses"] and unduhan.get("data"):
                        nama = re.sub(r'[\\/:*?"<>|]+', "_", label).strip(" ._") or f"SPD_{item['nomor']}"
                        nama = f"{int(item['nomor']):04d}_{nama[:100]}.pdf"
                        zf.writestr(nama, unduhan["data"])
                        status = "Berhasil"
                    else:
                        status = "Dilewati" if str(unduhan["pesan"]).startswith("Dilewati:") else "Gagal"
                    hasil.append({"nomor": item["nomor"], "ringkasan": label, "status dokumen": item.get("status", ""), "hasil": status, "pesan": unduhan["pesan"]})
                    progress.progress(idx / len(pilihan), text=f"Memproses {idx}/{len(pilihan)}")
            st.session_state["tte_bulk_hasil"] = hasil
            st.session_state["tte_bulk_zip"] = arsip.getvalue()
            st.session_state["tte_bulk_zip_name"] = f"SPD_TTE_{int(awal)}-{int(akhir)}.zip"
            st.rerun()

hasil = st.session_state.get("tte_bulk_hasil", [])
if hasil:
    berhasil = sum(1 for x in hasil if x["hasil"] == "Berhasil")
    dilewati = sum(1 for x in hasil if x["hasil"] == "Dilewati")
    gagal = len(hasil) - berhasil - dilewati
    st.subheader("Hasil unduhan")
    a, b, c, d = st.columns(4)
    a.metric("Total", len(hasil))
    b.metric("Berhasil", berhasil)
    c.metric("Dilewati", dilewati)
    d.metric("Gagal", gagal)
    st.dataframe(hasil, use_container_width=True, hide_index=True)
    if st.session_state.get("tte_bulk_zip"):
        st.download_button("⬇️ Download ZIP hasil", data=st.session_state["tte_bulk_zip"], file_name=st.session_state.get("tte_bulk_zip_name", "SPD_TTE_bulk.zip"), mime="application/zip", type="primary")
