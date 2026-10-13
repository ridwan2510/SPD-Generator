import io
import re
import zipfile
import importlib

import streamlit as st


# ============================================================
# KONFIGURASI HALAMAN
# ============================================================

st.set_page_config(
    page_title="Download SPD Bulk",
    page_icon="📥",
    layout="wide",
)

st.title("📥 Download SPD Bulk — TTE Kemenag")

st.caption(
    "Ambil dokumen dari daftar TTE yang bisa diakses oleh akun Anda, "
    "pilih rentang nomor, lalu unduh sebagai ZIP."
)

st.warning(
    "Nomor mengikuti urutan baris pada respons daftar TTE, "
    "bukan nomor surat SPD. Hanya dokumen berstatus FINAL yang "
    "diunduh sebagai PDF. Draft/Sedang Proses akan dicatat sebagai dilewati."
)


# ============================================================
# MEMUAT MODUL TTE
# ============================================================

try:
    import services.tte_service as tte_service

    # Muat ulang modul agar halaman memeriksa fungsi yang tersedia
    # pada file tte_service.py yang sedang dimuat oleh Python.
    tte_service = importlib.reload(tte_service)

    ambil_daftar_dokumen_tte = getattr(
        tte_service,
        "ambil_daftar_dokumen_tte",
        None,
    )

    unduh_rentang_dokumen_tte = getattr(
        tte_service,
        "unduh_rentang_dokumen_tte",
        None,
    )

except Exception as exc:
    st.error("Gagal memuat modul layanan TTE.")
    st.exception(exc)
    st.stop()


# ============================================================
# VALIDASI FUNGSI
# ============================================================

fungsi_tidak_tersedia = []

if not callable(
    ambil_daftar_dokumen_tte
):
    fungsi_tidak_tersedia.append(
        "ambil_daftar_dokumen_tte"
    )

if not callable(
    unduh_rentang_dokumen_tte
):
    fungsi_tidak_tersedia.append(
        "unduh_rentang_dokumen_tte"
    )

if fungsi_tidak_tersedia:
    st.error(
        "Fungsi berikut tidak ditemukan di services.tte_service: "
        + ", ".join(fungsi_tidak_tersedia)
    )

    st.markdown("**Informasi diagnosis:**")

    st.code(
        f"Lokasi modul: {tte_service.__file__}\n"
        f"Fungsi yang tidak ditemukan: "
        f"{', '.join(fungsi_tidak_tersedia)}\n"
        f"Nama terkait TTE yang tersedia: "
        f"{[nama for nama in dir(tte_service) if 'tte' in nama.lower() or 'dokumen' in nama.lower()]}"
    )

    st.info(
        "Periksa services/tte_service.py pada GitHub. "
        "Nama fungsi harus sama persis dengan nama yang dipanggil halaman ini. "
        "Jika fungsi memang tidak ada pada modul yang dimuat, "
        "perbaikannya perlu dilakukan di file layanan tersebut."
    )

    st.stop()


# ============================================================
# SESSION STATE
# ============================================================

if "tte_bulk_daftar" not in st.session_state:
    st.session_state["tte_bulk_daftar"] = []

if "tte_bulk_error" not in st.session_state:
    st.session_state["tte_bulk_error"] = None

if "tte_bulk_hasil" not in st.session_state:
    st.session_state["tte_bulk_hasil"] = []

if "tte_bulk_zip" not in st.session_state:
    st.session_state["tte_bulk_zip"] = None

if "tte_bulk_zip_name" not in st.session_state:
    st.session_state["tte_bulk_zip_name"] = "SPD_TTE_bulk.zip"


# ============================================================
# MEMUAT / MEMPERBARUI DAFTAR TTE
# ============================================================

if st.button(
    "🔄 Muat / Perbarui Daftar TTE",
    type="primary",
):
    with st.spinner(
        "Menghubungkan ke TTE Kemenag dan membaca daftar dokumen..."
    ):
        try:
            daftar = ambil_daftar_dokumen_tte()

            if daftar is None:
                daftar = []

            st.session_state["tte_bulk_daftar"] = daftar
            st.session_state["tte_bulk_error"] = None

            # Reset hasil lama ketika daftar diperbarui.
            st.session_state["tte_bulk_hasil"] = []
            st.session_state["tte_bulk_zip"] = None
            st.session_state["tte_bulk_zip_name"] = (
                "SPD_TTE_bulk.zip"
            )

        except Exception as exc:
            st.session_state["tte_bulk_daftar"] = []
            st.session_state["tte_bulk_error"] = str(exc)


# ============================================================
# PESAN ERROR
# ============================================================

if st.session_state.get("tte_bulk_error"):
    st.error(
        st.session_state["tte_bulk_error"]
    )

    st.info(
        "Jika daftar tidak dapat diakses, periksa login dan "
        "konfigurasi [tte] pada Streamlit Secrets. "
        "Jangan membagikan cookie atau token sesi."
    )


# ============================================================
# PRATINJAU DAFTAR DOKUMEN
# ============================================================

daftar = st.session_state.get(
    "tte_bulk_daftar",
    [],
)

if daftar:
    st.success(
        f"Berhasil membaca {len(daftar)} baris dari daftar TTE."
    )

    with st.expander(
        "Pratinjau daftar TTE",
        expanded=True,
    ):
        data_pratinjau = []

        for item in daftar:
            data_pratinjau.append(
                {
                    "No. urut": item.get("nomor", ""),
                    "Waktu": item.get("waktu", ""),
                    "Perihal Dokumen": item.get(
                        "ringkasan",
                        "",
                    ),
                    "Status": item.get("status", ""),
                    "Tombol": item.get(
                        "label_unduh",
                        "",
                    ),
                    "PDF FINAL siap": (
                        "Ya"
                        if (
                            item.get("final")
                            and item.get("tautan_unduh")
                        )
                        else "Tidak"
                    ),
                }
            )

        st.dataframe(
            data_pratinjau,
            use_container_width=True,
            hide_index=True,
        )

    # ========================================================
    # PEMILIHAN RENTANG NOMOR
    # ========================================================

    st.subheader("Pilih rentang dokumen")

    kolom_awal, kolom_akhir = st.columns(2)

    with kolom_awal:
        awal = st.number_input(
            "Nomor awal",
            min_value=1,
            max_value=len(daftar),
            value=1,
            step=1,
            key="tte_bulk_nomor_awal",
        )

    with kolom_akhir:
        akhir = st.number_input(
            "Nomor akhir",
            min_value=1,
            max_value=len(daftar),
            value=min(10, len(daftar)),
            step=1,
            key="tte_bulk_nomor_akhir",
        )

    if awal > akhir:
        st.error(
            "Nomor awal harus lebih kecil atau sama dengan nomor akhir."
        )

    else:
        pilihan = daftar[
            int(awal) - 1:int(akhir)
        ]

        tersedia = sum(
            1
            for item in pilihan
            if (
                item.get("final")
                and item.get("tautan_unduh")
            )
        )

        st.info(
            f"Rentang {int(awal)}–{int(akhir)}: "
            f"{len(pilihan)} baris; "
            f"{tersedia} dokumen FINAL memiliki tautan unduh."
        )

        if tersedia < len(pilihan):
            st.warning(
                "Dokumen Draft/Sedang Proses tidak diunduh karena "
                "tombolnya bukan PDF final. Dokumen FINAL tanpa "
                "tautan yang valid akan dicatat gagal. "
                "Aplikasi tidak menebak URL."
            )

        # ====================================================
        # PROSES DOWNLOAD ZIP
        # ====================================================

        if st.button(
            "📦 Unduh Rentang ke ZIP",
            type="primary",
            disabled=(
                awal > akhir
                or tersedia == 0
            ),
        ):
            arsip = io.BytesIO()
            hasil = []

            progress = st.progress(
                0.0,
                text="Memulai unduhan...",
            )

            try:
                hasil_download = (
                    unduh_rentang_dokumen_tte(
                        pilihan
                    )
                )

                if hasil_download is None:
                    hasil_download = []

            except Exception as exc:
                hasil_download = [
                    {
                        "nomor": item.get("nomor", ""),
                        "sukses": False,
                        "pesan": (
                            f"Login/akses TTE gagal: {exc}"
                        ),
                        "data": None,
                    }
                    for item in pilihan
                ]

            # Normalisasi jumlah hasil supaya setiap dokumen
            # tetap memiliki status meskipun layanan tidak
            # mengembalikan hasil lengkap.
            hasil_normal = []

            for idx, item in enumerate(pilihan):
                if idx < len(hasil_download):
                    unduhan = hasil_download[idx] or {}
                else:
                    unduhan = {
                        "nomor": item.get("nomor", ""),
                        "sukses": False,
                        "pesan": (
                            "Layanan tidak mengembalikan hasil "
                            "untuk dokumen ini."
                        ),
                        "data": None,
                    }

                hasil_normal.append(
                    (
                        item,
                        unduhan,
                    )
                )

            with zipfile.ZipFile(
                arsip,
                "w",
                zipfile.ZIP_DEFLATED,
            ) as zf:

                total = len(hasil_normal)

                for idx, pasangan in enumerate(
                    hasil_normal,
                    start=1,
                ):
                    item, unduhan = pasangan

                    label = str(
                        item.get("ringkasan") or ""
                    )[:180]

                    pesan = str(
                        unduhan.get("pesan") or ""
                    )

                    nomor = item.get(
                        "nomor",
                        idx,
                    )

                    if (
                        unduhan.get("sukses")
                        and unduhan.get("data")
                    ):
                        nama = re.sub(
                            r'[\\/:*?"<>|]+',
                            "_",
                            label,
                        ).strip(" ._")

                        if not nama:
                            nama = f"SPD_{nomor}"

                        try:
                            nomor_file = int(nomor)
                        except (
                            TypeError,
                            ValueError,
                        ):
                            nomor_file = idx

                        nama = (
                            f"{nomor_file:04d}_"
                            f"{nama[:100]}.pdf"
                        )

                        # Hindari nama file ganda dalam ZIP.
                        nama_awal = nama
                        penghitung = 2

                        while nama in zf.namelist():
                            nama = (
                                f"{nama_awal[:-4]}_"
                                f"{penghitung}.pdf"
                            )
                            penghitung += 1

                        zf.writestr(
                            nama,
                            unduhan["data"],
                        )

                        status = "Berhasil"

                    else:
                        status = (
                            "Dilewati"
                            if pesan.startswith("Dilewati:")
                            else "Gagal"
                        )

                    hasil.append(
                        {
                            "nomor": nomor,
                            "ringkasan": label,
                            "status dokumen": item.get(
                                "status",
                                "",
                            ),
                            "hasil": status,
                            "pesan": pesan,
                        }
                    )

                    progress.progress(
                        idx / total,
                        text=(
                            f"Memproses {idx}/{total}"
                        ),
                    )

            st.session_state["tte_bulk_hasil"] = hasil
            st.session_state["tte_bulk_zip"] = (
                arsip.getvalue()
            )
            st.session_state["tte_bulk_zip_name"] = (
                f"SPD_TTE_{int(awal)}-{int(akhir)}.zip"
            )

            st.rerun()


# ============================================================
# MENAMPILKAN HASIL UNDUHAN
# ============================================================

hasil = st.session_state.get(
    "tte_bulk_hasil",
    [],
)

if hasil:
    berhasil = sum(
        1
        for item in hasil
        if item.get("hasil") == "Berhasil"
    )

    dilewati = sum(
        1
        for item in hasil
        if item.get("hasil") == "Dilewati"
    )

    gagal = (
        len(hasil)
        - berhasil
        - dilewati
    )

    st.divider()
    st.subheader("Hasil unduhan")

    kolom_total, kolom_berhasil, kolom_dilewati, kolom_gagal = (
        st.columns(4)
    )

    kolom_total.metric(
        "Total",
        len(hasil),
    )

    kolom_berhasil.metric(
        "Berhasil",
        berhasil,
    )

    kolom_dilewati.metric(
        "Dilewati",
        dilewati,
    )

    kolom_gagal.metric(
        "Gagal",
        gagal,
    )

    st.dataframe(
        hasil,
        use_container_width=True,
        hide_index=True,
    )

    if st.session_state.get("tte_bulk_zip"):
        st.download_button(
            "⬇️ Download ZIP hasil",
            data=st.session_state["tte_bulk_zip"],
            file_name=st.session_state.get(
                "tte_bulk_zip_name",
                "SPD_TTE_bulk.zip",
            ),
            mime="application/zip",
            type="primary",
        )
