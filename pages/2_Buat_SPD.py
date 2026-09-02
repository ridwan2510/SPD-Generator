import os
import re
import zipfile
import random
import time
import uuid
from io import BytesIO
from datetime import date

import streamlit as st

from services.api_service import (
    get_all_pegawai,
    get_ppk_by_bidang,
)

from services.document_service import (
    generate_document,
    format_tanggal_indonesia,
    convert_docx_to_pdf,
)

from services.preview_service import (
    show_pdf,
)

from services.tte_service import (
    ajukan_file_ke_tte,
)


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Buat SPD",
    page_icon="📄",
    layout="wide",
)

st.title("Buat Surat Perjalanan Dinas")
st.caption(
    "Pilih satu atau beberapa pegawai dari bidang mana pun. "
    "Data perjalanan cukup diisi satu kali; PPK mengikuti bidang masing-masing pegawai."
)


# ============================================================
# PATH PROJECT
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

TEMPLATE_PATH = os.path.join(
    BASE_DIR,
    "templates",
    "SPD_template.docx",
)

OUTPUT_BASE_DIR = os.path.join(
    BASE_DIR,
    "output",
)

os.makedirs(
    OUTPUT_BASE_DIR,
    exist_ok=True,
)

# ============================================================
# FOLDER OUTPUT KHUSUS PER SESSION
# ============================================================
# Setiap pengguna/sesi mendapat folder output berbeda supaya
# file PDF/DOCX tidak saling menimpa saat dipakai bersamaan.

if "spd_session_id" not in st.session_state:
    st.session_state["spd_session_id"] = uuid.uuid4().hex

SESSION_OUTPUT_DIR = os.path.join(
    OUTPUT_BASE_DIR,
    st.session_state["spd_session_id"],
)

os.makedirs(
    SESSION_OUTPUT_DIR,
    exist_ok=True,
)

# Alias agar kode lama tetap memakai OUTPUT_DIR.
OUTPUT_DIR = SESSION_OUTPUT_DIR


# ============================================================
# SESSION STATE
# ============================================================

if "nomor_surat" not in st.session_state:
    st.session_state["nomor_surat"] = ""

if "spd_preview_pdf" not in st.session_state:
    st.session_state["spd_preview_pdf"] = None

if "spd_preview_docx" not in st.session_state:
    st.session_state["spd_preview_docx"] = None

if "hasil_pdf_spd" not in st.session_state:
    st.session_state["hasil_pdf_spd"] = []

if "zip_spd_bytes" not in st.session_state:
    st.session_state["zip_spd_bytes"] = None

if "zip_spd_filename" not in st.session_state:
    st.session_state["zip_spd_filename"] = None

if "hasil_tte_spd" not in st.session_state:
    st.session_state["hasil_tte_spd"] = []


# ============================================================
# HELPER
# ============================================================

def safe_filename(text):
    """Membuat teks aman untuk nama file."""

    text = str(text or "").strip()

    text = re.sub(
        r'[\\/:*?"<>|]',
        "",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.replace(
        " ",
        "_",
    )


# ============================================================
# KONFIGURASI TTE KHUSUS PD PONTREN
# ============================================================

BIDANG_TTE_PD_PONTREN = (
    "Pendidikan Diniyah dan Pondok Pesantren"
)

# Delay acak antar pengajuan dokumen TTE.
# Tidak diterapkan setelah dokumen terakhir.
TTE_DELAY_MIN_DETIK = 4
TTE_DELAY_MAX_DETIK = 7

# Lock global agar hanya satu batch pengajuan TTE berjalan
# pada satu waktu di instance aplikasi yang sama.
TTE_LOCK_PATH = os.path.join(
    OUTPUT_BASE_DIR,
    ".tte_global.lock",
)

# Lock dianggap stale jika tertinggal lebih dari 30 menit.
TTE_LOCK_MAX_AGE_SECONDS = 30 * 60


def normalisasi_nama_bidang(text):
    """Normalisasi nama bidang untuk pembandingan."""
    nilai = str(text or "").strip().casefold()

    nilai = re.sub(
        r"\s+",
        " ",
        nilai,
    )

    # Tetap menerima data lama yang memakai awalan "Bidang ".
    if nilai.startswith("bidang "):
        nilai = nilai[7:].strip()

    return nilai


def bidang_boleh_tte(bidang):
    """TTE pada aplikasi ini hanya untuk PD Pontren."""
    return (
        normalisasi_nama_bidang(bidang)
        ==
        normalisasi_nama_bidang(
            BIDANG_TTE_PD_PONTREN
        )
    )


def _hapus_lock_tte_kedaluwarsa():
    """Menghapus lock yang tertinggal akibat proses berhenti/crash."""
    if not os.path.exists(TTE_LOCK_PATH):
        return

    try:
        umur_lock = time.time() - os.path.getmtime(
            TTE_LOCK_PATH
        )

        if umur_lock > TTE_LOCK_MAX_AGE_SECONDS:
            os.remove(TTE_LOCK_PATH)

    except Exception:
        pass


def coba_kunci_tte():
    """
    Mencoba mengambil lock TTE secara atomik.

    Return:
        (True, owner_token) jika berhasil.
        (False, pesan) jika sedang dipakai pengguna lain.
    """

    _hapus_lock_tte_kedaluwarsa()

    owner_token = (
        f"{st.session_state.get('spd_session_id', '-')}"
        f"|{time.time()}"
    )

    try:
        fd = os.open(
            TTE_LOCK_PATH,
            os.O_CREAT | os.O_EXCL | os.O_WRONLY,
        )

        with os.fdopen(
            fd,
            "w",
            encoding="utf-8",
        ) as file_lock:
            file_lock.write(owner_token)

        return True, owner_token

    except FileExistsError:
        return (
            False,
            (
                "Pengajuan TTE sedang diproses oleh pengguna lain. "
                "Silakan tunggu sampai proses tersebut selesai "
                "kemudian coba kembali."
            ),
        )

    except Exception as e:
        return (
            False,
            f"Gagal membuat penguncian proses TTE: {e}",
        )


def lepas_kunci_tte(owner_token):
    """Melepas lock hanya jika lock tersebut milik sesi ini."""
    try:
        if not os.path.exists(TTE_LOCK_PATH):
            return

        with open(
            TTE_LOCK_PATH,
            "r",
            encoding="utf-8",
        ) as file_lock:
            isi_lock = file_lock.read().strip()

        if isi_lock == str(owner_token).strip():
            os.remove(TTE_LOCK_PATH)

    except Exception:
        pass


def get_pangkat_golongan(pegawai):
    pangkat = str(
        pegawai.get("pangkat") or ""
    ).strip()

    golongan = str(
        pegawai.get("gol_ruang") or ""
    ).strip()

    if pangkat and pangkat != "-" and golongan and golongan != "-":
        return f"{pangkat} / {golongan}"

    if pangkat and pangkat != "-":
        return pangkat

    if golongan and golongan != "-":
        return golongan

    return ""


def get_jabatan_instansi(pegawai):
    jabatan = str(
        pegawai.get("jabatan") or ""
    ).strip()

    instansi = str(
        pegawai.get("instansi") or ""
    ).strip()

    if jabatan and jabatan != "-" and instansi and instansi != "-":
        return f"{jabatan} / {instansi}"

    if jabatan and jabatan != "-":
        return jabatan

    if instansi and instansi != "-":
        return instansi

    return ""


def cari_kepala_kanwil(pegawai_list):
    """Mencari Kepala Kanwil dari master pegawai."""

    # Prioritas exact match.
    for pegawai in pegawai_list:
        jabatan = str(
            pegawai.get("jabatan") or ""
        ).strip().lower()

        if jabatan == "kepala kanwil":
            return pegawai

    # Fallback untuk data jabatan yang lebih panjang.
    for pegawai in pegawai_list:
        jabatan = str(
            pegawai.get("jabatan") or ""
        ).strip().lower()

        if "kepala kanwil" in jabatan:
            return pegawai

    return None


def isi_nomor_surat_otomatis():
    tanggal = st.session_state.get(
        "tanggal_dikeluarkan",
        date.today(),
    )

    bulan = f"{tanggal.month:02d}"
    tahun = tanggal.year

    st.session_state["nomor_surat"] = (
        "Kw.11.3/4/PP.00.7/"
        f"{bulan}/{tahun}"
    )


def buat_zip_pdf(file_pdf_list):
    buffer = BytesIO()

    with zipfile.ZipFile(
        buffer,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
    ) as zip_file:
        for item in file_pdf_list:
            pdf_path = item["path"]
            filename = item["filename"]

            if os.path.exists(pdf_path):
                zip_file.write(
                    pdf_path,
                    arcname=filename,
                )

    buffer.seek(0)
    return buffer.getvalue()


def format_label_pegawai(pegawai):
    nama = str(
        pegawai.get("nama") or ""
    ).strip()

    nip = str(
        pegawai.get("nip") or ""
    ).strip()

    bidang = str(
        pegawai.get("bidang") or ""
    ).strip()

    if not bidang:
        bidang = "-"

    return f"{nama} | NIP {nip} | {bidang}"


# ============================================================
# LOAD MASTER DATA
# ============================================================

try:
    pegawai_list = get_all_pegawai()

except Exception as e:
    st.error("Gagal mengambil data pegawai.")
    st.code(str(e))
    st.stop()


if not pegawai_list:
    st.warning(
        "Belum ada data pegawai. "
        "Silakan isi Master Pegawai terlebih dahulu."
    )
    st.stop()


kepala = cari_kepala_kanwil(
    pegawai_list
)

if not kepala:
    st.warning(
        "Data Kepala Kanwil belum ditemukan."
    )
    st.info(
        "Pastikan pada Master Pegawai terdapat pegawai "
        "dengan jabatan `Kepala Kanwil`."
    )
    st.stop()


# ============================================================
# MAPPING SEMUA PEGAWAI
# ============================================================

pegawai_by_id = {
    str(pegawai.get("id") or "").strip(): pegawai
    for pegawai in pegawai_list
    if str(pegawai.get("id") or "").strip()
}


# ============================================================
# LAYOUT UTAMA - PERTAHANKAN DESAIN LAMA
# ============================================================

col_form, col_preview = st.columns(
    [1, 1.30],
    gap="large",
)


# ============================================================
# FORM KIRI
# ============================================================

with col_form:
    # ========================================================
    # 1. PEGAWAI
    # ========================================================

    st.subheader("1. Pegawai")

    st.caption(
        "Pegawai dapat dipilih lintas bidang. "
        "PPK akan ditentukan otomatis dari bidang masing-masing pegawai."
    )

    pegawai_id_terpilih = st.multiselect(
        "Pegawai yang Melaksanakan Perjalanan Dinas",
        options=list(pegawai_by_id.keys()),
        format_func=lambda pegawai_id: format_label_pegawai(
            pegawai_by_id[pegawai_id]
        ),
        key="pegawai_spd_multi",
        placeholder="Pilih satu atau beberapa pegawai",
    )

    pegawai_terpilih = [
        pegawai_by_id[pegawai_id]
        for pegawai_id in pegawai_id_terpilih
    ]

    if pegawai_terpilih:
        st.success(
            f"{len(pegawai_terpilih)} pegawai dipilih."
        )

        with st.expander(
            "Lihat Pegawai Terpilih",
            expanded=False,
        ):
            for nomor, item in enumerate(
                pegawai_terpilih,
                start=1,
            ):
                nama = str(
                    item.get("nama") or "-"
                )

                nip = str(
                    item.get("nip") or "-"
                )

                bidang = str(
                    item.get("bidang") or "-"
                )

                jabatan = str(
                    item.get("jabatan") or "-"
                )

                st.markdown(
                    f"""
**{nomor}. {nama}**

NIP: `{nip}`  
Bidang: `{bidang}`  
Pangkat/Gol: `{get_pangkat_golongan(item) or '-'}`  
Jabatan: `{jabatan}`
"""
                )

                if nomor < len(pegawai_terpilih):
                    st.divider()

    else:
        st.info(
            "Silakan pilih minimal satu pegawai."
        )


    # ========================================================
    # 2. PPK PER BIDANG
    # ========================================================

    st.divider()
    st.subheader("2. Pejabat Pembuat Komitmen")
    st.caption(
        "PPK ditentukan otomatis berdasarkan bidang "
        "masing-masing pegawai yang dipilih."
    )

    bidang_pegawai_terpilih = []
    pegawai_tanpa_bidang = []

    for pegawai in pegawai_terpilih:
        bidang = str(
            pegawai.get("bidang") or ""
        ).strip()

        if bidang and bidang != "-":
            if bidang not in bidang_pegawai_terpilih:
                bidang_pegawai_terpilih.append(
                    bidang
                )
        else:
            pegawai_tanpa_bidang.append(
                str(
                    pegawai.get("nama") or "-"
                )
            )

    bidang_pegawai_terpilih = sorted(
        bidang_pegawai_terpilih
    )

    ppk_by_bidang = {}
    ppk_error = []

    for bidang in bidang_pegawai_terpilih:
        try:
            data_ppk = get_ppk_by_bidang(
                bidang
            )

            if data_ppk:
                ppk_by_bidang[bidang] = data_ppk
            else:
                ppk_error.append(
                    f"Belum ada PPK aktif untuk bidang: {bidang}"
                )

        except Exception as e:
            ppk_error.append(
                f"Gagal mengambil PPK untuk bidang {bidang}: {e}"
            )

    if not pegawai_terpilih:
        st.info(
            "Pilih pegawai terlebih dahulu."
        )

    else:
        if pegawai_tanpa_bidang:
            st.warning(
                "Pegawai berikut belum memiliki bidang: "
                + ", ".join(pegawai_tanpa_bidang)
            )

        for bidang in bidang_pegawai_terpilih:
            ppk_item = ppk_by_bidang.get(
                bidang
            )

            if not ppk_item:
                st.warning(
                    f"⚠️ {bidang} — PPK aktif belum tersedia."
                )
                continue

            nama_ppk = str(
                ppk_item.get("nama") or ""
            )

            nip_ppk = str(
                ppk_item.get("nip") or ""
            )

            with st.container(
                border=True
            ):
                st.markdown(
                    f"**{bidang}**"
                )
                st.write(
                    nama_ppk
                )
                st.caption(
                    f"NIP {nip_ppk}"
                )


    # ========================================================
    # 3. KEPALA KANWIL
    # ========================================================

    st.divider()
    st.subheader("3. Kepala Kanwil")

    col_kepala1, col_kepala2 = st.columns(2)

    with col_kepala1:
        st.text_input(
            "Nama Kepala Kanwil",
            value=str(
                kepala.get("nama") or ""
            ),
            disabled=True,
            key="spd_nama_kepala",
        )

    with col_kepala2:
        st.text_input(
            "NIP Kepala Kanwil",
            value=str(
                kepala.get("nip") or ""
            ),
            disabled=True,
            key="spd_nip_kepala",
        )


    # ========================================================
    # 4. DATA PERJALANAN DINAS
    # ========================================================

    st.divider()
    st.subheader("4. Data Perjalanan Dinas")

    tanggal_dikeluarkan = st.date_input(
        "Tanggal Dikeluarkan",
        value=date.today(),
        key="tanggal_dikeluarkan",
    )

    col_nomor, col_auto = st.columns(
        [4, 1]
    )

    with col_nomor:
        nomor_surat = st.text_input(
            "Nomor Surat",
            key="nomor_surat",
            placeholder=(
                "Contoh: "
                "Kw.11.3/4/PP.00.7/09/2026"
            ),
        )

    with col_auto:
        st.write("")
        st.write("")

        st.button(
            "Isi Otomatis",
            on_click=isi_nomor_surat_otomatis,
            use_container_width=True,
            key="btn_nomor_otomatis",
        )

    tingkat_biaya = st.text_input(
        "Tingkat Biaya Perjalanan Dinas",
        placeholder="Contoh: C",
        key="tingkat_biaya_spd",
    )

    maksud_perjalanan = st.text_area(
        "Maksud Perjalanan Dinas",
        placeholder="Tuliskan maksud perjalanan dinas...",
        height=120,
        key="maksud_perjalanan_spd",
    )

    alat_angkut = st.text_input(
        "Alat Angkut",
        value="Kendaraan Dinas",
        key="alat_angkut_spd",
    )

    tempat_berangkat = st.text_input(
        "Tempat Berangkat",
        value="Kota Semarang",
        key="tempat_berangkat_spd",
    )

    col_tgl1, col_tgl2 = st.columns(2)

    with col_tgl1:
        tanggal_berangkat = st.date_input(
            "Tanggal Berangkat",
            value=date.today(),
            key="tanggal_berangkat_spd",
        )

    with col_tgl2:
        tanggal_kembali = st.date_input(
            "Tanggal Kembali",
            value=date.today(),
            key="tanggal_kembali_spd",
        )

    tempat_dikeluarkan = st.text_input(
        "Tempat Dikeluarkan",
        value="Semarang",
        key="tempat_dikeluarkan_spd",
    )


    # ========================================================
    # 5. TUJUAN PERJALANAN
    # ========================================================

    st.divider()
    st.subheader("5. Tujuan Perjalanan")

    jumlah_tujuan = st.number_input(
        "Banyaknya Tempat Tujuan",
        min_value=1,
        max_value=10,
        value=1,
        step=1,
        key="jumlah_tujuan_spd",
    )

    tujuan_list = []

    for i in range(
        int(jumlah_tujuan)
    ):
        with st.container(
            border=True
        ):
            st.markdown(
                f"#### Tujuan {i + 1}"
            )

            tujuan = st.text_input(
                "Tempat Tujuan",
                key=f"tujuan_{i}",
                placeholder="Contoh: Kota Salatiga",
            )

            col_tiba, col_keluar = st.columns(2)

            with col_tiba:
                tanggal_tiba = st.date_input(
                    "Tanggal Tiba",
                    value=(
                        tanggal_berangkat
                        if i == 0
                        else tanggal_berangkat
                    ),
                    key=f"tanggal_tiba_{i}",
                )

            with col_keluar:
                tanggal_berangkat_tujuan = st.date_input(
                    "Tanggal Berangkat dari Tempat Ini",
                    value=(
                        tanggal_kembali
                        if i == int(jumlah_tujuan) - 1
                        else tanggal_berangkat
                    ),
                    key=f"tanggal_berangkat_tujuan_{i}",
                )

            tujuan_list.append(
                {
                    "tujuan": tujuan,
                    "tanggal_tiba": tanggal_tiba,
                    "tanggal_berangkat": tanggal_berangkat_tujuan,
                }
            )


    # ========================================================
    # LAMA PERJALANAN
    # ========================================================

    lama_perjalanan = (
        tanggal_kembali
        - tanggal_berangkat
    ).days + 1

    lama_perjalanan_teks = (
        f"{lama_perjalanan} hari"
        if lama_perjalanan > 0
        else ""
    )

    # Key dibuat mengikuti tanggal agar nilai widget selalu diperbarui
    # ketika Tanggal Berangkat / Tanggal Kembali berubah.
    st.text_input(
        "Lama Perjalanan Dinas",
        value=lama_perjalanan_teks,
        disabled=True,
        key=(
            "lama_perjalanan_spd_"
            f"{tanggal_berangkat.isoformat()}_"
            f"{tanggal_kembali.isoformat()}"
        ),
    )


    # ========================================================
    # VALIDASI
    # ========================================================

    error_list = []

    if not pegawai_terpilih:
        error_list.append(
            "Minimal satu pegawai harus dipilih."
        )

    if pegawai_tanpa_bidang:
        error_list.append(
            "Semua pegawai yang dipilih harus memiliki bidang. "
            "Pegawai tanpa bidang: "
            + ", ".join(pegawai_tanpa_bidang)
        )

    if ppk_error:
        error_list.extend(
            ppk_error
        )

    if not nomor_surat.strip():
        error_list.append(
            "Nomor Surat belum diisi."
        )

    if not tingkat_biaya.strip():
        error_list.append(
            "Tingkat biaya perjalanan dinas belum diisi."
        )

    if not maksud_perjalanan.strip():
        error_list.append(
            "Maksud perjalanan dinas belum diisi."
        )

    if lama_perjalanan <= 0:
        error_list.append(
            "Tanggal kembali tidak boleh lebih awal dari tanggal berangkat."
        )

    for index, item in enumerate(
        tujuan_list,
        start=1,
    ):
        if not str(
            item["tujuan"]
        ).strip():
            error_list.append(
                f"Tujuan {index} belum diisi."
            )

        if item["tanggal_tiba"] < tanggal_berangkat:
            error_list.append(
                f"Tanggal tiba tujuan {index} lebih awal dari tanggal berangkat."
            )

        if item["tanggal_berangkat"] < item["tanggal_tiba"]:
            error_list.append(
                f"Tanggal berangkat dari tujuan {index} lebih awal dari tanggal tiba."
            )

        if item["tanggal_berangkat"] > tanggal_kembali:
            error_list.append(
                f"Tanggal berangkat dari tujuan {index} melewati tanggal kembali SPD."
            )


    # ========================================================
    # TUJUAN UTAMA
    # ========================================================

    tujuan_utama = ""

    if tujuan_list:
        tujuan_utama = tujuan_list[0][
            "tujuan"
        ]


    # ========================================================
    # REPLACEMENTS DASAR
    # ========================================================

    replacements_dasar = {
        "${nomorsurat}": nomor_surat,
        "${tingkatbiayaperjalanandinas}": tingkat_biaya,
        "${maksudperjalanandinas}": maksud_perjalanan,
        "${maksud perjalanan dinas}": maksud_perjalanan,
        "${alatangkut}": alat_angkut,
        "${tempatberangkat}": tempat_berangkat,
        "${tempatujuan}": tujuan_utama,
        "${lamanyaperjalanandinas}": (
            f"{lama_perjalanan} hari"
            if lama_perjalanan > 0
            else ""
        ),
        "${tanggalberangkat}": format_tanggal_indonesia(
            tanggal_berangkat
        ),
        "${tanggalkembali}": format_tanggal_indonesia(
            tanggal_kembali
        ),
        "${tempatdikeluarkan}": tempat_dikeluarkan,
        "${tanggaldikeluarkan}": format_tanggal_indonesia(
            tanggal_dikeluarkan
        ),
        "${namakepala}": str(
            kepala.get("nama") or ""
        ),
        "${nipkepala}": str(
            kepala.get("nip") or ""
        ),
    }


    # ========================================================
    # KOSONGKAN PLACEHOLDER RUTE
    # ========================================================

    for nomor_rute in range(
        1,
        12,
    ):
        replacements_dasar[
            f"${{rute{nomor_rute}_tiba}}"
        ] = ""

        replacements_dasar[
            f"${{rute{nomor_rute}_tanggal_tiba}}"
        ] = ""

        replacements_dasar[
            f"${{rute{nomor_rute}_dari}}"
        ] = ""

        replacements_dasar[
            f"${{rute{nomor_rute}_ke}}"
        ] = ""

        replacements_dasar[
            f"${{rute{nomor_rute}_tanggal_berangkat}}"
        ] = ""


    # ========================================================
    # RUTE AWAL + RUTE TUJUAN
    # ========================================================

    if tujuan_list:
        replacements_dasar[
            "${rute1_dari}"
        ] = tempat_berangkat

        replacements_dasar[
            "${rute1_ke}"
        ] = tujuan_list[0][
            "tujuan"
        ]

        replacements_dasar[
            "${rute1_tanggal_berangkat}"
        ] = format_tanggal_indonesia(
            tanggal_berangkat
        )

        for index, tujuan_item in enumerate(
            tujuan_list
        ):
            nomor_rute = index + 2

            replacements_dasar[
                f"${{rute{nomor_rute}_tiba}}"
            ] = tujuan_item[
                "tujuan"
            ]

            replacements_dasar[
                f"${{rute{nomor_rute}_tanggal_tiba}}"
            ] = format_tanggal_indonesia(
                tujuan_item[
                    "tanggal_tiba"
                ]
            )

            replacements_dasar[
                f"${{rute{nomor_rute}_dari}}"
            ] = tujuan_item[
                "tujuan"
            ]

            if index + 1 < len(tujuan_list):
                tujuan_berikutnya = tujuan_list[
                    index + 1
                ]["tujuan"]
            else:
                tujuan_berikutnya = tempat_berangkat

            replacements_dasar[
                f"${{rute{nomor_rute}_ke}}"
            ] = tujuan_berikutnya

            replacements_dasar[
                f"${{rute{nomor_rute}_tanggal_berangkat}}"
            ] = format_tanggal_indonesia(
                tujuan_item[
                    "tanggal_berangkat"
                ]
            )

    replacements_dasar[
        "${tiba_kembali}"
    ] = tempat_berangkat

    replacements_dasar[
        "${tanggal_tiba_kembali}"
    ] = format_tanggal_indonesia(
        tanggal_kembali
    )


    # ========================================================
    # REPLACEMENTS PER PEGAWAI
    # ========================================================

    def buat_replacements_pegawai(
        data_pegawai
    ):
        replacements = replacements_dasar.copy()

        replacements[
            "${nama}"
        ] = str(
            data_pegawai.get("nama") or ""
        )

        replacements[
            "${nip}"
        ] = str(
            data_pegawai.get("nip") or ""
        )

        replacements[
            "${pangkatgolongan}"
        ] = get_pangkat_golongan(
            data_pegawai
        )

        replacements[
            "${jabataninstansi}"
        ] = get_jabatan_instansi(
            data_pegawai
        )

        bidang_pegawai = str(
            data_pegawai.get("bidang") or ""
        ).strip()

        ppk_pegawai = ppk_by_bidang.get(
            bidang_pegawai
        )

        if ppk_pegawai:
            replacements[
                "${namappk}"
            ] = str(
                ppk_pegawai.get("nama") or ""
            )

            replacements[
                "${nipppk}"
            ] = str(
                ppk_pegawai.get("nip") or ""
            )

        else:
            replacements[
                "${namappk}"
            ] = ""

            replacements[
                "${nipppk}"
            ] = ""

        return replacements


    # ========================================================
    # BUTTON
    # ========================================================

    st.divider()

    col_btn1, col_btn2 = st.columns(2)

    with col_btn1:
        preview_btn = st.button(
            "Preview SPD",
            use_container_width=True,
            key="preview_spd",
        )

    with col_btn2:
        generate_btn = st.button(
            "Generate Semua SPD",
            type="primary",
            use_container_width=True,
            key="generate_spd",
        )


# ============================================================
# PREVIEW KANAN
# ============================================================

with col_preview:
    st.subheader("Preview Dokumen")

    st.caption(
        "Preview menggunakan pegawai pertama "
        "dari daftar pegawai yang dipilih."
    )

    if preview_btn:
        if error_list:
            for error in error_list:
                st.error(error)

        elif not os.path.exists(
            TEMPLATE_PATH
        ):
            st.error(
                "Template SPD tidak ditemukan."
            )
            st.code(
                TEMPLATE_PATH
            )

        else:
            try:
                pegawai_preview = pegawai_terpilih[0]

                replacements_preview = buat_replacements_pegawai(
                    pegawai_preview
                )

                preview_docx = os.path.join(
                    OUTPUT_DIR,
                    "SPD_preview.docx",
                )

                preview_pdf = os.path.join(
                    OUTPUT_DIR,
                    "SPD_preview.pdf",
                )

                generate_document(
                    TEMPLATE_PATH,
                    preview_docx,
                    replacements_preview,
                )

                convert_docx_to_pdf(
                    preview_docx,
                    preview_pdf,
                )

                st.session_state[
                    "spd_preview_docx"
                ] = preview_docx

                st.session_state[
                    "spd_preview_pdf"
                ] = preview_pdf

                st.success(
                    "Preview dibuat untuk "
                    f"{pegawai_preview.get('nama', '')}."
                )

            except Exception as e:
                st.error(
                    "Gagal membuat preview."
                )
                st.code(
                    str(e)
                )

    preview_pdf_session = st.session_state.get(
        "spd_preview_pdf"
    )

    if (
        preview_pdf_session
        and os.path.exists(preview_pdf_session)
    ):
        show_pdf(
            preview_pdf_session,
            height=1000,
        )

    else:
        st.info(
            "Pilih pegawai, isi data SPD, "
            "kemudian klik **Preview SPD**."
        )


# ============================================================
# GENERATE SEMUA SPD
# ============================================================

if generate_btn:
    if error_list:
        for error in error_list:
            st.error(error)

    elif not os.path.exists(
        TEMPLATE_PATH
    ):
        st.error(
            "Template SPD tidak ditemukan."
        )

    else:
        hasil_pdf = []
        berhasil = 0
        gagal = []

        progress = st.progress(
            0,
            text="Memulai pembuatan SPD...",
        )

        total = len(
            pegawai_terpilih
        )

        for index, pegawai in enumerate(
            pegawai_terpilih,
            start=1,
        ):
            try:
                progress.progress(
                    (index - 1) / total,
                    text=(
                        "Membuat SPD "
                        f"{pegawai.get('nama', '')}..."
                    ),
                )

                replacements = buat_replacements_pegawai(
                    pegawai
                )

                nama_file_pegawai = safe_filename(
                    pegawai.get("nama") or "Pegawai"
                )

                nama_file_tujuan = safe_filename(
                    tujuan_utama or "Tujuan"
                )

                nama_file = (
                    f"SPD_{nama_file_pegawai}_"
                    f"{nama_file_tujuan}"
                )

                output_docx = os.path.join(
                    OUTPUT_DIR,
                    f"{nama_file}.docx",
                )

                output_pdf = os.path.join(
                    OUTPUT_DIR,
                    f"{nama_file}.pdf",
                )

                generate_document(
                    TEMPLATE_PATH,
                    output_docx,
                    replacements,
                )

                convert_docx_to_pdf(
                    output_docx,
                    output_pdf,
                )

                try:
                    if os.path.exists(output_docx):
                        os.remove(output_docx)
                except Exception:
                    pass

                hasil_pdf.append(
                    {
                        "pegawai_id": str(
                            pegawai.get("id") or ""
                        ),
                        "nama": pegawai.get("nama") or "",
                        "nip": pegawai.get("nip") or "",
                        "bidang": pegawai.get("bidang") or "",
                        "path": output_pdf,
                        "filename": f"{nama_file}.pdf",
                    }
                )

                berhasil += 1

            except Exception as e:
                gagal.append(
                    {
                        "nama": pegawai.get("nama") or "-",
                        "error": str(e),
                    }
                )

        progress.progress(
            1.0,
            text="Proses SPD selesai.",
        )

        st.session_state[
            "hasil_pdf_spd"
        ] = hasil_pdf

        if hasil_pdf:
            zip_bytes = buat_zip_pdf(
                hasil_pdf
            )

            nama_tujuan_zip = safe_filename(
                tujuan_utama or "Tujuan"
            )

            zip_filename = (
                f"SPD_{nama_tujuan_zip}.zip"
            )

            st.session_state[
                "zip_spd_bytes"
            ] = zip_bytes

            st.session_state[
                "zip_spd_filename"
            ] = zip_filename

            st.session_state[
                "spd_preview_pdf"
            ] = hasil_pdf[0]["path"]

        if berhasil:
            st.success(
                f"{berhasil} SPD berhasil dibuat."
            )

        if gagal:
            st.warning(
                f"{len(gagal)} SPD gagal dibuat."
            )

            for item in gagal:
                st.error(
                    f"{item['nama']}: {item['error']}"
                )


# ============================================================
# HASIL GENERATE
# ============================================================

hasil_pdf_session = st.session_state.get(
    "hasil_pdf_spd",
    [],
)

if hasil_pdf_session:
    st.divider()
    st.subheader("Hasil SPD")

    for item in hasil_pdf_session:
        if not os.path.exists(
            item["path"]
        ):
            continue

        with open(
            item["path"],
            "rb",
        ) as file_pdf:
            pdf_bytes = file_pdf.read()

        col_nama, col_download = st.columns(
            [3, 1]
        )

        with col_nama:
            st.markdown(
                f"**{item['nama']}**  \n"
                f"NIP: `{item['nip']}`  \n"
                f"Bidang: `{item.get('bidang') or '-'}`"
            )

        with col_download:
            st.download_button(
                "Download PDF",
                data=pdf_bytes,
                file_name=item["filename"],
                mime="application/pdf",
                use_container_width=True,
                key=(
                    "download_pdf_"
                    f"{item['pegawai_id']}"
                ),
            )


# ============================================================
# PENGAJUAN TTE KEMENAG - KHUSUS PD PONTREN
# ============================================================

if hasil_pdf_session:

    hasil_pdf_tte = [
        item
        for item in hasil_pdf_session
        if bidang_boleh_tte(
            item.get("bidang")
        )
        and os.path.exists(
            item.get("path") or ""
        )
    ]

    st.divider()
    st.subheader(
        "✍️ Pengajuan TTE Kemenag - PD Pontren"
    )

    if not hasil_pdf_tte:

        st.info(
            "Pengajuan TTE dari aplikasi ini hanya tersedia "
            "untuk SPD pegawai Bidang Pendidikan Diniyah "
            "dan Pondok Pesantren."
        )

    else:

        st.caption(
            "Hanya dokumen SPD pegawai Bidang Pendidikan "
            "Diniyah dan Pondok Pesantren yang akan dikirim. "
            "Dokumen dari bidang lain tidak ikut diajukan. "
            "Pengajuan TTE dibuat satu antrean agar beberapa "
            "pengguna tidak mengirim dengan akun SATKER yang "
            "sama secara bersamaan."
        )

        st.success(
            f"{len(hasil_pdf_tte)} dokumen SPD PD Pontren "
            "siap diajukan ke TTE Kemenag."
        )

        with st.expander(
            "Lihat dokumen yang akan diajukan",
            expanded=False,
        ):

            for nomor, item in enumerate(
                hasil_pdf_tte,
                start=1,
            ):

                st.markdown(
                    f"**{nomor}. {item.get('nama') or '-'}**  \n"
                    f"NIP: `{item.get('nip') or '-'}`  \n"
                    f"Bidang: `{item.get('bidang') or '-'}`  \n"
                    f"File: `{item.get('filename') or '-'}'"
                )

                if nomor < len(
                    hasil_pdf_tte
                ):
                    st.divider()

        perihal_tte = st.text_input(
            "Perihal Dokumen TTE",
            value="Surat Perjalanan Dinas",
            help=(
                "Nama pegawai akan ditambahkan otomatis "
                "pada bagian akhir perihal."
            ),
            key="perihal_tte_pd_pontren",
        )

        konfirmasi_tte = st.checkbox(
            (
                "Saya sudah memeriksa dokumen dan yakin "
                "akan mengajukan seluruh SPD PD Pontren "
                "di atas ke TTE Kemenag."
            ),
            key="konfirmasi_tte_pd_pontren",
        )

        if st.button(
            "✍️ Ajukan Semua PD Pontren ke TTE Kemenag",
            type="primary",
            use_container_width=True,
            disabled=not konfirmasi_tte,
            key="btn_ajukan_semua_tte_pd_pontren",
        ):

            if not str(
                perihal_tte or ""
            ).strip():

                st.error(
                    "Perihal Dokumen TTE wajib diisi."
                )

            else:

                lock_berhasil, lock_info = coba_kunci_tte()

                if not lock_berhasil:

                    st.warning(
                        lock_info
                    )

                else:

                    owner_token_tte = lock_info

                    try:

                        total_tte = len(
                            hasil_pdf_tte
                        )

                        berhasil_tte = 0
                        gagal_tte = 0
                        hasil_tte = []

                        progress_tte = st.progress(
                            0,
                            text=(
                                "Menyiapkan pengajuan "
                                "TTE Kemenag..."
                            ),
                        )

                        status_tte = st.empty()

                        for index, item in enumerate(
                            hasil_pdf_tte,
                            start=1,
                        ):

                            nama_tte = str(
                                item.get("nama") or "Pegawai"
                            ).strip()

                            pdf_path_tte = str(
                                item.get("path") or ""
                            ).strip()

                            filename_tte = str(
                                item.get("filename")
                                or f"SPD_{safe_filename(nama_tte)}.pdf"
                            ).strip()

                            perihal_final_tte = (
                                f"{str(perihal_tte).strip()} "
                                f"- {nama_tte}"
                            )

                            status_tte.info(
                                "Mengajukan SPD ke TTE: "
                                f"{nama_tte} "
                                f"({index}/{total_tte})"
                            )

                            try:

                                sukses_tte, pesan_tte = (
                                    ajukan_file_ke_tte(
                                        pdf_path=pdf_path_tte,
                                        perihal_dokumen=
                                            perihal_final_tte,
                                        filename=filename_tte,
                                    )
                                )

                            except Exception as e:

                                sukses_tte = False
                                pesan_tte = str(e)

                            if sukses_tte:
                                berhasil_tte += 1
                            else:
                                gagal_tte += 1

                            hasil_tte.append(
                                {
                                    "pegawai_id":
                                        item.get("pegawai_id"),
                                    "nama":
                                        nama_tte,
                                    "nip":
                                        item.get("nip"),
                                    "bidang":
                                        item.get("bidang"),
                                    "filename":
                                        filename_tte,
                                    "sukses":
                                        sukses_tte,
                                    "pesan":
                                        pesan_tte,
                                }
                            )

                            progress_tte.progress(
                                index / total_tte,
                                text=(
                                    f"Pengajuan TTE "
                                    f"{index}/{total_tte}"
                                ),
                            )

                            # ==================================
                            # DELAY ACAK ANTAR DOKUMEN
                            # ==================================
                            if index < total_tte:

                                delay_tte = random.randint(
                                    TTE_DELAY_MIN_DETIK,
                                    TTE_DELAY_MAX_DETIK,
                                )

                                status_tte.info(
                                    f"{nama_tte} selesai diproses. "
                                    f"Menunggu {delay_tte} detik "
                                    "sebelum dokumen berikutnya..."
                                )

                                time.sleep(
                                    delay_tte
                                )

                        status_tte.empty()

                        st.session_state[
                            "hasil_tte_spd"
                        ] = hasil_tte

                        if gagal_tte == 0:

                            st.success(
                                "Semua dokumen berhasil "
                                "diajukan ke TTE Kemenag. "
                                f"Total: {berhasil_tte} dokumen."
                            )

                        else:

                            st.warning(
                                "Pengajuan TTE selesai. "
                                f"{berhasil_tte} berhasil, "
                                f"{gagal_tte} gagal."
                            )

                    finally:

                        lepas_kunci_tte(
                            owner_token_tte
                        )



# ============================================================
# HASIL PENGAJUAN TTE
# ============================================================

hasil_tte_session = st.session_state.get(
    "hasil_tte_spd",
    [],
)

if hasil_tte_session:

    with st.expander(
        "Status Pengajuan TTE Terakhir",
        expanded=True,
    ):

        for item in hasil_tte_session:

            nama_tte = (
                item.get("nama")
                or "-"
            )

            pesan_tte = (
                item.get("pesan")
                or "-"
            )

            if item.get("sukses"):

                st.success(
                    f"✅ {nama_tte}: "
                    f"{pesan_tte}"
                )

            else:

                st.error(
                    f"❌ {nama_tte}: "
                    f"{pesan_tte}"
                )


# ============================================================
# DOWNLOAD ZIP
# ============================================================

zip_bytes_session = st.session_state.get(
    "zip_spd_bytes"
)

zip_filename_session = st.session_state.get(
    "zip_spd_filename"
)

if (
    zip_bytes_session
    and zip_filename_session
):
    st.download_button(
        "📦 Download Semua SPD (ZIP)",
        data=zip_bytes_session,
        file_name=zip_filename_session,
        mime="application/zip",
        type="primary",
        use_container_width=True,
        key="download_zip_spd",
    )
