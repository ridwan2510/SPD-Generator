import io
from typing import Optional, Tuple

import requests
import streamlit as st
from bs4 import BeautifulSoup


# ============================================================
# KONFIGURASI DASAR TTE
# ============================================================

TTE_BASE_URL = "https://tte.kemenag.go.id"
DEFAULT_TIMEOUT = 60


# ============================================================
# HELPER SECRETS
# ============================================================

def _get_secret(
    name: str,
    default: Optional[str] = None,
) -> Optional[str]:
    """
    Membaca konfigurasi dari:

    [tte]
    email = "..."
    password = "..."

    pemaraf_id = "30703"

    penandatangan_1_id = "374"
    penandatangan_1_anchors = "^"

    penandatangan_2_id = "44"
    penandatangan_2_anchors = "$,#,*"
    """

    try:
        value = st.secrets["tte"].get(
            name,
            default,
        )

        if value is None:
            return default

        return str(value).strip()

    except Exception:
        return default


# ============================================================
# SESSION
# ============================================================

def _buat_session() -> requests.Session:
    """
    Membuat session HTTP agar cookie login TTE
    tetap digunakan selama seluruh proses.
    """

    session = requests.Session()

    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/120 Safari/537.36"
            ),
            "Accept-Language": (
                "id-ID,id;q=0.9,"
                "en-US;q=0.8,en;q=0.7"
            ),
        }
    )

    return session


# ============================================================
# CSRF TOKEN
# ============================================================

def _ambil_csrf_token(
    session: requests.Session,
    url: str,
) -> str:
    """
    Membuka halaman TTE lalu mengambil input:

        <input name="_token" value="...">
    """

    response = session.get(
        url,
        timeout=DEFAULT_TIMEOUT,
        allow_redirects=True,
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    token_input = soup.find(
        "input",
        {"name": "_token"},
    )

    if not token_input:

        raise RuntimeError(
            "Token CSRF tidak ditemukan pada halaman:\n"
            f"{url}"
        )

    token = token_input.get(
        "value"
    )

    if not token:

        raise RuntimeError(
            "Token CSRF ditemukan tetapi nilainya kosong:\n"
            f"{url}"
        )

    return str(token).strip()


# ============================================================
# VALIDASI RESPONSE
# ============================================================

def _cek_response(
    response: requests.Response,
    proses: str,
) -> None:
    """
    Mengecek apakah request HTTP gagal.
    """

    try:

        response.raise_for_status()

    except requests.RequestException as exc:

        raise RuntimeError(
            f"{proses} gagal. "
            f"HTTP {response.status_code}. "
            f"{exc}"
        ) from exc


# ============================================================
# LOGIN TTE
# ============================================================

def _login_tte(
    session: requests.Session,
) -> None:
    """
    Login otomatis menggunakan akun ADMIN SATKER.
    """

    email = _get_secret(
        "email"
    )

    password = _get_secret(
        "password"
    )

    if not email or not password:

        raise RuntimeError(
            "Konfigurasi login TTE belum lengkap.\n\n"
            "Tambahkan email dan password pada "
            "[tte] di Streamlit Secrets."
        )

    login_url = (
        f"{TTE_BASE_URL}/login"
    )

    token_login = _ambil_csrf_token(
        session,
        login_url,
    )

    response = session.post(
        login_url,
        data={
            "_token": token_login,
            "login_as": "ADMIN",
            "email": email,
            "password": password,
        },
        timeout=DEFAULT_TIMEOUT,
        allow_redirects=True,
    )

    _cek_response(
        response,
        "Login TTE",
    )

    final_url = str(
        response.url
    ).rstrip("/")

    login_url_normalized = (
        login_url.rstrip("/")
    )

    response_text = (
        response.text
        or ""
    ).lower()

    # Jika setelah login masih berada di halaman login,
    # maka kemungkinan login gagal.
    if (
        final_url == login_url_normalized
        and
        "logout" not in response_text
    ):

        raise RuntimeError(
            "Login TTE gagal. "
            "Periksa email dan password TTE."
        )


# ============================================================
# PARSE ANCHOR
# ============================================================

def _parse_anchors(
    value: Optional[str],
) -> list[str]:
    """
    Contoh:

        "^"
        -> ["^"]

        "$,#,*"
        -> ["$", "#", "*"]
    """

    if not value:
        return []

    return [
        item.strip()
        for item in str(value).split(",")
        if item.strip()
    ]


# ============================================================
# TAMBAH PEMARAF
# ============================================================

def _tambah_pemaraf(
    session: requests.Session,
    pemaraf_id: str,
) -> None:
    """
    Menambahkan pemaraf pada Step 2.
    """

    step_two_url = (
        f"{TTE_BASE_URL}"
        "/satker/dokumen/naskah/"
        "create_step_two"
    )

    token = _ambil_csrf_token(
        session,
        step_two_url,
    )

    store_url = (
        f"{TTE_BASE_URL}"
        "/satker/dokumen/naskah/"
        "pemaraf/store"
    )

    response = session.post(
        store_url,
        data={
            "_token": token,
            "pegawai_id": pemaraf_id,
        },
        timeout=DEFAULT_TIMEOUT,
        allow_redirects=True,
    )

    _cek_response(
        response,
        "Menambahkan pemaraf",
    )


# ============================================================
# TAMBAH PENANDATANGAN
# ============================================================

def _tambah_penandatangan(
    session: requests.Session,
    pegawai_id: str,
    anchors: list[str],
    nama_proses: str,
) -> None:
    """
    Menambahkan seorang penandatangan beserta
    satu atau beberapa anchor.
    """

    if not pegawai_id:

        raise RuntimeError(
            f"{nama_proses}: pegawai_id kosong."
        )

    if not anchors:

        raise RuntimeError(
            f"{nama_proses}: anchor belum dikonfigurasi."
        )

    step_three_url = (
        f"{TTE_BASE_URL}"
        "/satker/dokumen/naskah/"
        "create_step_three"
    )

    token = _ambil_csrf_token(
        session,
        step_three_url,
    )

    store_url = (
        f"{TTE_BASE_URL}"
        "/satker/dokumen/naskah/"
        "penandatangan/store"
    )

    data = [
        (
            "_token",
            token,
        ),
        (
            "pegawai_id",
            pegawai_id,
        ),
    ]

    for anchor in anchors:

        data.append(
            (
                "anchor[]",
                anchor,
            )
        )

    response = session.post(
        store_url,
        data=data,
        timeout=DEFAULT_TIMEOUT,
        allow_redirects=True,
    )

    _cek_response(
        response,
        nama_proses,
    )


# ============================================================
# FINALISASI
# ============================================================

def _finalisasi_tte(
    session: requests.Session,
) -> None:
    """
    Menyelesaikan proses pengajuan dokumen.
    """

    step_three_url = (
        f"{TTE_BASE_URL}"
        "/satker/dokumen/naskah/"
        "create_step_three"
    )

    token = _ambil_csrf_token(
        session,
        step_three_url,
    )

    selesai_url = (
        f"{TTE_BASE_URL}"
        "/satker/dokumen/naskah/"
        "selesai"
    )

    response = session.post(
        selesai_url,
        data={
            "_token": token,
        },
        timeout=DEFAULT_TIMEOUT,
        allow_redirects=True,
    )

    _cek_response(
        response,
        "Finalisasi pengajuan TTE",
    )


# ============================================================
# FUNGSI UTAMA
# ============================================================

def ajukan_ke_tte(
    pdf_bytes: bytes,
    filename: str,
    perihal_dokumen: str,
    *,
    pemaraf_id: Optional[str] = None,
    penandatangan_1_id: Optional[str] = None,
    penandatangan_2_id: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Mengajukan satu dokumen PDF ke TTE Kemenag.

    Alur:

    1. Login ADMIN SATKER
    2. Upload PDF
    3. Tambah Pemaraf
    4. Tambah Penandatangan 1
    5. Tambah Penandatangan 2
    6. Finalisasi

    Return:
        (True, pesan)
        (False, pesan)
    """

    # ========================================================
    # VALIDASI PDF
    # ========================================================

    if not pdf_bytes:

        return (
            False,
            "File PDF kosong.",
        )

    filename = str(
        filename
        or "SPD.pdf"
    ).strip()

    if not filename.lower().endswith(
        ".pdf"
    ):

        filename = (
            f"{filename}.pdf"
        )

    perihal_dokumen = str(
        perihal_dokumen
        or ""
    ).strip()

    if not perihal_dokumen:

        return (
            False,
            "Perihal dokumen TTE belum diisi.",
        )

    # ========================================================
    # KONFIGURASI PEMARAF
    # ========================================================

    pemaraf_id = str(
        pemaraf_id
        or
        _get_secret(
            "pemaraf_id"
        )
        or
        ""
    ).strip()

    if not pemaraf_id:

        return (
            False,
            "pemaraf_id belum dikonfigurasi.",
        )

    # ========================================================
    # KONFIGURASI PENANDATANGAN 1
    # ========================================================

    penandatangan_1_id = str(
        penandatangan_1_id
        or
        _get_secret(
            "penandatangan_1_id"
        )
        or
        ""
    ).strip()

    penandatangan_1_anchors = (
        _parse_anchors(
            _get_secret(
                "penandatangan_1_anchors",
                "^",
            )
        )
    )

    if not penandatangan_1_id:

        return (
            False,
            (
                "penandatangan_1_id "
                "belum dikonfigurasi."
            ),
        )

    # ========================================================
    # KONFIGURASI PENANDATANGAN 2
    # ========================================================

    penandatangan_2_id = str(
        penandatangan_2_id
        or
        _get_secret(
            "penandatangan_2_id"
        )
        or
        ""
    ).strip()

    penandatangan_2_anchors = (
        _parse_anchors(
            _get_secret(
                "penandatangan_2_anchors",
                "$,#,*",
            )
        )
    )

    if not penandatangan_2_id:

        return (
            False,
            (
                "penandatangan_2_id "
                "belum dikonfigurasi."
            ),
        )

    # ========================================================
    # SESSION
    # ========================================================

    session = _buat_session()

    try:

        # ====================================================
        # 1. LOGIN
        # ====================================================

        _login_tte(
            session
        )

        # ====================================================
        # 2. UPLOAD PDF
        # ====================================================

        upload_page_url = (
            f"{TTE_BASE_URL}"
            "/satker/dokumen/naskah/"
            "index/unggah"
        )

        token_upload = (
            _ambil_csrf_token(
                session,
                upload_page_url,
            )
        )

        upload_store_url = (
            f"{TTE_BASE_URL}"
            "/satker/dokumen/naskah/"
            "store"
        )

        response_upload = session.post(
            upload_store_url,
            data={
                "_token":
                    token_upload,

                "jenis_dokumen_id":
                    "2",

                "perihal_dokumen":
                    perihal_dokumen,

                "tipe_kertas":
                    "P",
            },
            files={
                "path_dokumen": (
                    filename,
                    io.BytesIO(
                        pdf_bytes
                    ),
                    "application/pdf",
                )
            },
            timeout=DEFAULT_TIMEOUT,
            allow_redirects=True,
        )

        _cek_response(
            response_upload,
            "Upload dokumen",
        )

        # ====================================================
        # 3. PEMARAF
        # M. FATHURROHIM, S.Ag
        # ID 30703
        # ====================================================

        _tambah_pemaraf(
            session=session,
            pemaraf_id=pemaraf_id,
        )

        # ====================================================
        # 4. PENANDATANGAN 1
        #
        # H. SAIFUL MUJAB, M.A
        # ID 374
        # Anchor ^
        # ====================================================

        _tambah_penandatangan(
            session=session,
            pegawai_id=
                penandatangan_1_id,
            anchors=
                penandatangan_1_anchors,
            nama_proses=(
                "Menambahkan "
                "Penandatangan 1"
            ),
        )

        # ====================================================
        # 5. PENANDATANGAN 2
        #
        # H. IMAM BUCHORI, S.Ag, M.Si.
        # ID 44
        # Anchor $, #, *
        # ====================================================

        _tambah_penandatangan(
            session=session,
            pegawai_id=
                penandatangan_2_id,
            anchors=
                penandatangan_2_anchors,
            nama_proses=(
                "Menambahkan "
                "Penandatangan 2"
            ),
        )

        # ====================================================
        # 6. FINALISASI
        # ====================================================

        _finalisasi_tte(
            session
        )

        return (
            True,
            (
                "Dokumen berhasil diajukan "
                "ke TTE Kemenag."
            ),
        )

    # ========================================================
    # ERROR HANDLING
    # ========================================================

    except requests.Timeout:

        return (
            False,
            (
                "Koneksi ke TTE Kemenag "
                "mengalami timeout."
            ),
        )

    except requests.ConnectionError as exc:

        return (
            False,
            (
                "Tidak dapat terhubung ke "
                "TTE Kemenag.\n\n"
                f"{exc}"
            ),
        )

    except requests.HTTPError as exc:

        return (
            False,
            (
                "Terjadi HTTP Error saat "
                "mengakses TTE Kemenag.\n\n"
                f"{exc}"
            ),
        )

    except Exception as exc:

        return (
            False,
            str(exc),
        )

    finally:

        session.close()


# ============================================================
# AJUKAN DARI FILE PATH
# ============================================================

def ajukan_file_ke_tte(
    pdf_path: str,
    perihal_dokumen: str,
    *,
    filename: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Mengirim PDF berdasarkan lokasi/path file.

    Digunakan oleh pages/2_Buat_SPD.py.
    """

    from pathlib import Path

    path = Path(
        pdf_path
    )

    if not path.exists():

        return (
            False,
            (
                "File PDF tidak ditemukan:\n"
                f"{pdf_path}"
            ),
        )

    if path.suffix.lower() != ".pdf":

        return (
            False,
            (
                "File yang dikirim ke TTE "
                "harus berformat PDF."
            ),
        )

    try:

        with path.open(
            "rb"
        ) as file_pdf:

            pdf_bytes = (
                file_pdf.read()
            )

    except Exception as exc:

        return (
            False,
            (
                "Gagal membaca file PDF.\n\n"
                f"{exc}"
            ),
        )

    filename_final = (
        filename
        or
        path.name
    )

    return ajukan_ke_tte(
        pdf_bytes=
            pdf_bytes,

        filename=
            filename_final,

        perihal_dokumen=
            perihal_dokumen,
    )