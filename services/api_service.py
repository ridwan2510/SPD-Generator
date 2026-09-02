import requests
import streamlit as st


# ============================================================
# CONFIG
# ============================================================

API_URL = st.secrets["api"]["url"]
API_KEY = st.secrets["api"]["key"]


# ============================================================
# GENERIC GET
# ============================================================

def api_get(
    action,
    params=None
):

    request_params = {
        "action": action,
        "api_key": API_KEY
    }

    if params:
        request_params.update(
            params
        )

    try:

        response = requests.get(
            API_URL,
            params=request_params,
            timeout=30
        )

        response.raise_for_status()

    except requests.RequestException as e:

        raise RuntimeError(
            "Gagal menghubungi API Google Apps Script: "
            f"{e}"
        )

    try:

        result = response.json()

    except ValueError:

        raise RuntimeError(
            "Response API bukan JSON yang valid."
        )

    if not result.get(
        "success",
        False
    ):

        raise RuntimeError(
            result.get(
                "message",
                "API gagal memproses permintaan."
            )
        )

    return result.get(
        "data"
    )


# ============================================================
# GENERIC POST
# ============================================================

def api_post(
    action,
    data=None
):

    payload = {
        "action": action,
        "api_key": API_KEY,
        "data": data or {}
    }

    try:

        response = requests.post(
            API_URL,
            json=payload,
            timeout=30
        )

        response.raise_for_status()

    except requests.RequestException as e:

        raise RuntimeError(
            "Gagal menghubungi API Google Apps Script: "
            f"{e}"
        )

    try:

        result = response.json()

    except ValueError:

        raise RuntimeError(
            "Response API bukan JSON yang valid."
        )

    if not result.get(
        "success",
        False
    ):

        raise RuntimeError(
            result.get(
                "message",
                "API gagal memproses permintaan."
            )
        )

    return result


# ============================================================
# GET ALL PEGAWAI
# ============================================================

@st.cache_data(
    ttl=60,
    show_spinner=False
)
def get_all_pegawai():

    data = api_get(
        "pegawai.list"
    )

    if not data:
        return []

    # Normalisasi agar ID konsisten
    hasil = []

    for item in data:

        pegawai = dict(item)

        pegawai["id"] = str(
            pegawai.get(
                "id",
                ""
            )
        ).strip()

        pegawai["nip"] = str(
            pegawai.get(
                "nip",
                ""
            )
        ).strip()

        hasil.append(
            pegawai
        )

    return hasil


# ============================================================
# GET PEGAWAI BY ID
# ============================================================

def get_pegawai_by_id(
    pegawai_id
):

    return api_get(
        "pegawai.get",
        {
            "id": pegawai_id
        }
    )


# ============================================================
# TAMBAH PEGAWAI
# ============================================================

def tambah_pegawai(
    nip,
    nama,
    pangkat,
    gol_ruang,
    jabatan,
    bidang,
    instansi,
    status_pegawai="Aktif"
):

    result = api_post(
        "pegawai.create",
        {
            "nip":
                str(nip).strip(),

            "nama":
                str(nama).strip(),

            "pangkat":
                str(pangkat).strip(),

            "gol_ruang":
                str(
                    gol_ruang
                ).strip(),

            "jabatan":
                str(
                    jabatan
                ).strip(),

            "bidang":
                str(
                    bidang
                ).strip(),

            "instansi":
                str(
                    instansi
                ).strip(),

            "status_pegawai":
                str(
                    status_pegawai
                ).strip()
        }
    )

    # Data berubah, hapus cache
    get_all_pegawai.clear()

    return result


# ============================================================
# UPDATE PEGAWAI
# ============================================================

def update_pegawai(
    pegawai_id,
    nip,
    nama,
    pangkat,
    gol_ruang,
    jabatan,
    bidang,
    instansi,
    status_pegawai
):

    result = api_post(
        "pegawai.update",
        {
            "id":
                pegawai_id,

            "nip":
                str(nip).strip(),

            "nama":
                str(nama).strip(),

            "pangkat":
                str(pangkat).strip(),

            "gol_ruang":
                str(
                    gol_ruang
                ).strip(),

            "jabatan":
                str(
                    jabatan
                ).strip(),

            "bidang":
                str(
                    bidang
                ).strip(),

            "instansi":
                str(
                    instansi
                ).strip(),

            "status_pegawai":
                str(
                    status_pegawai
                ).strip()
        }
    )

    get_all_pegawai.clear()

    return result


# ============================================================
# HAPUS PEGAWAI
# ============================================================

def hapus_pegawai(
    pegawai_id
):

    result = api_post(
        "pegawai.delete",
        {
            "id":
                pegawai_id
        }
    )

    get_all_pegawai.clear()

    return result


# ============================================================
# GET KEPALA KANWIL
# ============================================================

def get_kepala():

    pegawai_list = get_all_pegawai()

    for pegawai in pegawai_list:

        jabatan = str(
            pegawai.get(
                "jabatan",
                ""
            )
        ).strip().lower()

        status = str(
            pegawai.get(
                "status_pegawai",
                ""
            )
        ).strip().lower()

        if (
            jabatan ==
            "kepala kanwil"
            and
            status ==
            "aktif"
        ):

            return pegawai

    return None


# ============================================================
# GET BIDANG
# ============================================================

def get_all_bidang():

        pegawai_list = get_all_pegawai()

        bidang = {
        str(
            p.get(
                "bidang",
                ""
            )
        ).strip()

        for p in pegawai_list

        if str(
            p.get(
                "bidang",
                ""
            )
        ).strip()
    }

        return sorted(
            bidang
    )
        
# ============================================================
# PPK
# ============================================================

@st.cache_data(
    ttl=60,
    show_spinner=False
)
def get_all_ppk():

    data = api_get(
        "ppk.list"
    )

    if not data:
        return []

    hasil = []

    for item in data:

        ppk = dict(item)

        ppk["id"] = str(
            ppk.get(
                "id",
                ""
            )
        ).strip()

        ppk["ppk_id"] = str(
            ppk.get(
                "ppk_id",
                ppk.get(
                    "id",
                    ""
                )
            )
        ).strip()

        ppk["pegawai_id"] = str(
            ppk.get(
                "pegawai_id",
                ""
            )
        ).strip()

        ppk["bidang"] = str(
            ppk.get(
                "bidang",
                ""
            )
        ).strip()

        ppk["aktif"] = int(
            ppk.get(
                "aktif",
                0
            )
            or 0
        )

        hasil.append(
            ppk
        )

    return hasil


def get_ppk_by_id(
    ppk_id
):

    return api_get(
        "ppk.get",
        {
            "id": ppk_id
        }
    )


def get_ppk_by_bidang(
    bidang
):

    data = api_get(
        "ppk.byBidang",
        {
            "bidang": str(
                bidang
            ).strip()
        }
    )

    if not data:
        return None

    ppk = dict(data)

    ppk["id"] = str(
        ppk.get(
            "id",
            ""
        )
    ).strip()

    ppk["ppk_id"] = str(
        ppk.get(
            "ppk_id",
            ppk.get(
                "id",
                ""
            )
        )
    ).strip()

    ppk["pegawai_id"] = str(
        ppk.get(
            "pegawai_id",
            ""
        )
    ).strip()

    ppk["bidang"] = str(
        ppk.get(
            "bidang",
            ""
        )
    ).strip()

    ppk["aktif"] = int(
        ppk.get(
            "aktif",
            0
        )
        or 0
    )

    return ppk


def tambah_ppk(
    pegawai_id,
    bidang,
    aktif=1,
    tanggal_mulai="",
    tanggal_selesai=""
):

    result = api_post(
        "ppk.create",
        {
            "pegawai_id":
                str(
                    pegawai_id
                ).strip(),

            "bidang":
                str(
                    bidang
                ).strip(),

            "aktif":
                int(
                    aktif
                ),

            "tanggal_mulai":
                str(
                    tanggal_mulai
                    or ""
                ).strip(),

            "tanggal_selesai":
                str(
                    tanggal_selesai
                    or ""
                ).strip(),
        }
    )

    get_all_ppk.clear()

    return result


def update_ppk(
    ppk_id,
    pegawai_id,
    bidang,
    aktif,
    tanggal_mulai="",
    tanggal_selesai=""
):

    result = api_post(
        "ppk.update",
        {
            "id":
                str(
                    ppk_id
                ).strip(),

            "pegawai_id":
                str(
                    pegawai_id
                ).strip(),

            "bidang":
                str(
                    bidang
                ).strip(),

            "aktif":
                int(
                    aktif
                ),

            "tanggal_mulai":
                str(
                    tanggal_mulai
                    or ""
                ).strip(),

            "tanggal_selesai":
                str(
                    tanggal_selesai
                    or ""
                ).strip(),
        }
    )

    get_all_ppk.clear()

    return result


def hapus_ppk(
    ppk_id
):

    result = api_post(
        "ppk.delete",
        {
            "id":
                str(
                    ppk_id
                ).strip()
        }
    )

    get_all_ppk.clear()

    return result