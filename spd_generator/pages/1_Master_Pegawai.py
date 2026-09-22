import html
import textwrap
import streamlit as st
import streamlit.components.v1 as components

from services.api_service import (
    get_all_pegawai,
    tambah_pegawai,
    update_pegawai,
    hapus_pegawai,
    
    get_all_ppk,
    tambah_ppk,
    update_ppk,
    hapus_ppk,
)


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Master Pegawai",
    page_icon="👥",
    layout="wide"
)


st.title(
    "Master Pegawai"
)

st.caption(
    "Kelola data pegawai yang digunakan "
    "dalam pembuatan Surat Perjalanan Dinas."
)


# ============================================================
# SESSION STATE
# ============================================================

if "pegawai_message" not in st.session_state:
    st.session_state[
        "pegawai_message"
    ] = None


# ============================================================
# HELPER
# ============================================================

def tampilkan_message():

    message = st.session_state.get(
        "pegawai_message"
    )

    if not message:
        return

    tipe = message.get(
        "type"
    )

    text = message.get(
        "text"
    )

    if tipe == "success":
        st.success(text)

    elif tipe == "error":
        st.error(text)

    elif tipe == "warning":
        st.warning(text)

    st.session_state[
        "pegawai_message"
    ] = None


def esc(value):

    return html.escape(
        str(
            value
            if value is not None
            else ""
        )
    )


def format_nip(value):

    if value is None:
        return ""

    return str(value).strip()

# ============================================================
# PANGKAT OTOMATIS
# ============================================================

PANGKAT_PNS = {

    "I/a":
        "Juru Muda",

    "I/b":
        "Juru Muda Tingkat I",

    "I/c":
        "Juru",

    "I/d":
        "Juru Tingkat I",

    "II/a":
        "Pengatur Muda",

    "II/b":
        "Pengatur Muda Tingkat I",

    "II/c":
        "Pengatur",

    "II/d":
        "Pengatur Tingkat I",

    "III/a":
        "Penata Muda",

    "III/b":
        "Penata Muda Tingkat I",

    "III/c":
        "Penata",

    "III/d":
        "Penata Tingkat I",

    "IV/a":
        "Pembina",

    "IV/b":
        "Pembina Tingkat I",

    "IV/c":
        "Pembina Utama Muda",

    "IV/d":
        "Pembina Utama Madya",

    "IV/e":
        "Pembina Utama"

}


def get_pangkat_otomatis(
    status_pegawai,
    gol_ruang
):

    status = str(
        status_pegawai or ""
    ).strip().upper()

    gol = str(
        gol_ruang or ""
    ).strip()

    if status not in ["PNS", "CPNS"]:
        return ""

    return PANGKAT_PNS.get(
        gol,
        ""
    )

def get_bidang_options(pegawai_list):

    bidang_set = {
        str(
            pegawai.get(
                "bidang",
                ""
            )
        ).strip()

        for pegawai in pegawai_list

        if str(
            pegawai.get(
                "bidang",
                ""
            )
        ).strip()
        not in (
            "",
            "-"
        )
    }

    return [
        "-",
        *sorted(bidang_set)
    ]

def render_table(data):

    if not data:
        st.info("Belum ada data pegawai.")
        return

    rows = []

    for index, pegawai in enumerate(
        data,
        start=1
    ):

        status = str(
            pegawai.get(
                "status_pegawai",
                ""
            )
        ).strip()

        row = f"""
        <tr>
            <td class="center">{index}</td>

            <td class="nip">
                {esc(format_nip(pegawai.get("nip")))}
            </td>

            <td class="nama">
                {esc(pegawai.get("nama"))}
            </td>

            <td>
                {esc(pegawai.get("pangkat"))}
            </td>

            <td class="center">
                {esc(pegawai.get("gol_ruang"))}
            </td>

            <td>
                {esc(pegawai.get("jabatan"))}
            </td>

            <td>
                {esc(pegawai.get("bidang"))}
            </td>

            <td>
                {esc(pegawai.get("instansi"))}
            </td>

            <td class="center">
                {esc(status)}
            </td>
        </tr>
        """

        rows.append(row)

    rows_html = "".join(rows)


    table_html = f"""
<!DOCTYPE html>

<html>

<head>

<meta charset="UTF-8">

<style>

    * {{
        box-sizing: border-box;
    }}

    html,
    body {{
        margin: 0;
        padding: 0;

        background: transparent;

        font-family:
            Arial,
            sans-serif;

        color: #111827;
    }}


    /* ===============================================
       SCROLLBAR ATAS
       =============================================== */

    .top-scroll {{
        width: 100%;

        overflow-x: scroll;
        overflow-y: hidden;

        height: 18px;

        margin-bottom: 8px;
    }}

    .top-scroll-content {{
        height: 1px;
        width: 1700px;
    }}


    /* ===============================================
       WRAPPER TABEL
       =============================================== */

    .table-wrapper {{
    width: 100%;

    height: 650px;

    overflow-x: auto;
    overflow-y: auto;

    background: #ffffff;

    border:
        1px solid #d1d5db;

    border-radius: 10px;
    }}


    /* ===============================================
       TABLE
       =============================================== */

    table {{
        width: 1700px;

        border-collapse: collapse;

        background: #ffffff;

        color: #111827;

        font-size: 13px;
    }}


    /* ===============================================
       HEADER
       =============================================== */

    thead th {{
    position: sticky;
    top: 0;
    z-index: 10;

    padding:
        13px 10px;

    text-align:
        left;

    white-space:
        nowrap;

    background:
        #f1f5f9;

    color:
        #0f172a;

    font-weight:
        700;

    border-bottom:
        1px solid #cbd5e1;
    }}


    /* ===============================================
       BODY
       =============================================== */

    tbody td {{
        padding:
            11px 10px;

        vertical-align:
            top;

        background:
            #ffffff;

        color:
            #111827;

        border-bottom:
            1px solid #e5e7eb;
    }}


    tbody tr:nth-child(even) td {{
        background:
            #f8fafc;
    }}


    tbody tr:hover td {{
        background:
            #eef2f7;
    }}


    tbody tr:last-child td {{
        border-bottom:
            none;
    }}


    /* ===============================================
       ALIGNMENT
       =============================================== */

    .center {{
        text-align:
            center;
    }}


    .nip {{
        white-space:
            nowrap;

        font-family:
            Consolas,
            monospace;

        color:
            #111827;
    }}


    .nama {{
        min-width:
            260px;
    }}


    /* ===============================================
       UKURAN KOLOM
       =============================================== */

    th:nth-child(1) {{
        width: 55px;
    }}

    th:nth-child(2) {{
        width: 180px;
    }}

    th:nth-child(3) {{
        width: 280px;
    }}

    th:nth-child(4) {{
        width: 130px;
    }}

    th:nth-child(5) {{
        width: 100px;
    }}

    th:nth-child(6) {{
        width: 300px;
    }}

    th:nth-child(7) {{
        width: 350px;
    }}

    th:nth-child(8) {{
        width: 350px;
    }}

    th:nth-child(9) {{
        width: 120px;
    }}

</style>

</head>


<body>


<div
    id="topScroll"
    class="top-scroll"
>
    <div
        id="topScrollContent"
        class="top-scroll-content"
    >
    </div>
</div>


<div
    id="tableWrapper"
    class="table-wrapper"
>

<table id="pegawaiTable">

<thead>

<tr>

    <th>No</th>

    <th>NIP</th>

    <th>Nama</th>

    <th>Pangkat</th>

    <th>Gol/Ruang</th>

    <th>Jabatan</th>

    <th>Bidang</th>

    <th>Instansi</th>

    <th>Status</th>

</tr>

</thead>


<tbody>

{rows_html}

</tbody>

</table>

</div>


<script>

const topScroll =
    document.getElementById(
        "topScroll"
    );

const topContent =
    document.getElementById(
        "topScrollContent"
    );

const tableWrapper =
    document.getElementById(
        "tableWrapper"
    );

const table =
    document.getElementById(
        "pegawaiTable"
    );


function updateScrollWidth() {{

    topContent.style.width =
        table.scrollWidth + "px";

}}


updateScrollWidth();


let syncingTop = false;
let syncingTable = false;


topScroll.addEventListener(
    "scroll",
    function() {{

        if (syncingTable) {{
            syncingTable = false;
            return;
        }}

        syncingTop = true;

        tableWrapper.scrollLeft =
            topScroll.scrollLeft;

    }}
);


tableWrapper.addEventListener(
    "scroll",
    function() {{

        if (syncingTop) {{
            syncingTop = false;
            return;
        }}

        syncingTable = true;

        topScroll.scrollLeft =
            tableWrapper.scrollLeft;

    }}
);


window.addEventListener(
    "resize",
    updateScrollWidth
);

</script>


</body>

</html>
"""

    components.html(
    table_html,
    height=690,
    scrolling=False
    )


# ============================================================
# LOAD DATA
# ============================================================

tampilkan_message()

try:

    pegawai_list = get_all_pegawai()

    bidang_master = get_bidang_options(
        pegawai_list
    )
    
    ppk_list = get_all_ppk()

except Exception as e:

    st.error(
        "Gagal mengambil data."
    )

    st.code(
        str(e)
    )

    st.stop()


# ============================================================
# TAB
# ============================================================

tab_daftar, tab_tambah, tab_edit, tab_ppk = st.tabs(
    [
        "📋 Daftar Pegawai",
        "➕ Tambah Pegawai",
        "✏️ Edit / Hapus",
        "🤵 Master PPK",
    ]
)


# ============================================================
# TAB DAFTAR PEGAWAI
# ============================================================

with tab_daftar:

    # ========================================================
    # FILTER
    # ========================================================

    col1, col2, col3 = st.columns(
        [2, 1, 1]
    )

    with col1:
        keyword = st.text_input(
            "Cari pegawai",
            placeholder=(
                "Cari NIP, nama, jabatan, "
                "bidang atau instansi..."
            ),
            key="search_pegawai"
        )

    # ========================================================
    # STATUS YANG BENAR-BENAR ADA DI DATA
    # ========================================================

    status_options_filter = sorted({
        str(
            p.get(
                "status_pegawai",
                ""
            )
        ).strip()

        for p in pegawai_list

        if str(
            p.get(
                "status_pegawai",
                ""
            )
        ).strip()
    })

    with col2:
        status_filter = st.selectbox(
            "Status",
            [
                "Semua",
                *status_options_filter
            ],
            key="filter_status"
        )

    # ========================================================
    # DAFTAR BIDANG
    # ========================================================

    bidang_options = sorted({
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
not in (
    "",
    "-"
)
    })

    with col3:
        bidang_filter = st.selectbox(
            "Bidang",
            [
                "Semua",
                *bidang_options
            ],
            key="filter_bidang"
        )

    # ========================================================
    # FILTER DATA
    # ========================================================

    filtered = []

    keyword_lower = (
        keyword
        .strip()
        .lower()
    )

    for pegawai in pegawai_list:

        # ====================================================
        # SEARCH
        # ====================================================

        if keyword_lower:

            gabungan = " ".join([
                str(
                    pegawai.get(
                        "nip",
                        ""
                    )
                ),

                str(
                    pegawai.get(
                        "nama",
                        ""
                    )
                ),

                str(
                    pegawai.get(
                        "pangkat",
                        ""
                    )
                ),

                str(
                    pegawai.get(
                        "gol_ruang",
                        ""
                    )
                ),

                str(
                    pegawai.get(
                        "jabatan",
                        ""
                    )
                ),

                str(
                    pegawai.get(
                        "bidang",
                        ""
                    )
                ),

                str(
                    pegawai.get(
                        "instansi",
                        ""
                    )
                )
            ]).lower()

            if (
                keyword_lower
                not in gabungan
            ):
                continue

        # ====================================================
        # STATUS
        # ====================================================

        if (
            status_filter
            != "Semua"
        ):

            status_pegawai = str(
                pegawai.get(
                    "status_pegawai",
                    ""
                )
            ).strip()

            if (
                status_pegawai
                != status_filter
            ):
                continue

        # ====================================================
        # BIDANG
        # ====================================================

        if (
            bidang_filter
            != "Semua"
        ):

            bidang_pegawai = str(
                pegawai.get(
                    "bidang",
                    ""
                )
            ).strip()

            if (
                bidang_pegawai
                != bidang_filter
            ):
                continue

        filtered.append(
            pegawai
        )

    # ========================================================
    # SUMMARY
    # ========================================================

    total = len(
        pegawai_list
    )

    total_pns = sum(
        1
        for p in pegawai_list
        if str(
            p.get(
                "status_pegawai",
                ""
            )
        ).strip().upper()
        == "PNS"
    )

    total_pppk = sum(
        1
        for p in pegawai_list
        if str(
            p.get(
                "status_pegawai",
                ""
            )
        ).strip().upper()
        in (
            "PPPK",
            "PPPK PARUH WAKTU"
        )
    )

    total_cpns = sum(
        1
        for p in pegawai_list
        if str(
            p.get(
                "status_pegawai",
                ""
            )
        ).strip().upper()
        == "CPNS"
    )

    m1, m2, m3, m4 = st.columns(
        4
    )

    m1.metric(
        "Total Pegawai",
        total
    )

    m2.metric(
        "PNS",
        total_pns
    )

    m3.metric(
        "PPPK",
        total_pppk
    )

    m4.metric(
        "CPNS",
        total_cpns
    )

    st.divider()

    # ========================================================
    # INFO + REFRESH
    # ========================================================

    col_info, col_refresh = st.columns(
        [5, 1]
    )

    with col_info:
        st.caption(
            f"Menampilkan "
            f"{len(filtered)} "
            f"dari {total} pegawai."
        )

    with col_refresh:

        if st.button(
            "🔄 Refresh Data",
            key="refresh_pegawai",
            use_container_width=True
        ):
            get_all_pegawai.clear()
            st.rerun()

    # ========================================================
    # TABLE
    #
    # PENTING:
    # Tetap berada di dalam with tab_daftar
    # ========================================================

    render_table(
        filtered
    )


# ============================================================
# TAB TAMBAH PEGAWAI
# ============================================================

with tab_tambah:

    st.subheader(
        "Tambah Pegawai"
    )

    st.caption(
        "Masukkan data pegawai baru."
    )

    # ========================================================
    # TIDAK MENGGUNAKAN st.form()
    #
    # Supaya Status/Golongan melakukan rerun dan pangkat
    # langsung berubah.
    # ========================================================

    col1, col2 = st.columns(
        2
    )

    # ========================================================
    # KOLOM KIRI
    # ========================================================

    with col1:

        nip_baru = st.text_input(
            "NIP *",
            placeholder=(
                "Contoh: "
                "198001012005011001"
            ),
            key="tambah_nip"
        )

        nama_baru = st.text_input(
            "Nama *",
            key="tambah_nama"
        )

        status_baru = st.selectbox(
            "Status Pegawai *",
            [
                "PNS",
                "PPPK",
                "CPNS",
                "PPPK PARUH WAKTU",
                "-"
            ],
            key="tambah_status"
        )

        # ====================================================
        # GOLONGAN
        # ====================================================

        if status_baru in ["PNS", "CPNS"]:

            gol_baru = st.selectbox(
                "Golongan / Ruang *",
                [
                    "-",
                    "I/a",
                    "I/b",
                    "I/c",
                    "I/d",
                    "II/a",
                    "II/b",
                    "II/c",
                    "II/d",
                    "III/a",
                    "III/b",
                    "III/c",
                    "III/d",
                    "IV/a",
                    "IV/b",
                    "IV/c",
                    "IV/d",
                    "IV/e",
                ],
                key="tambah_gol_pns"
            )
            
        elif status_baru == "CPNS":
        
                    gol_baru = st.selectbox(
                        "Golongan / Ruang *",
                        [
                            "-",
                            "I/a",
                            "I/b",
                            "I/c",
                            "I/d",
                            "II/a",
                            "II/b",
                            "II/c",
                            "II/d",
                            "III/a",
                            "III/b",
                            "III/c",
                            "III/d",
                            "IV/a",
                            "IV/b",
                            "IV/c",
                            "IV/d",
                            "IV/e",
                        ],
                        key="tambah_gol_cpns"
                    )

        elif status_baru == "-":

            gol_baru = "-"

            st.text_input(
            "Golongan / Ruang",
            value="-",
            disabled=True,
            key="tambah_gol_luar"
            )
        
        else:

            gol_baru = st.text_input(
                "Golongan / Ruang",
                placeholder=(
                    "Contoh PPPK: "
                    "V, VII, IX"
                ),
                key="tambah_gol_non_pns"
            )

        # ====================================================
        # PANGKAT OTOMATIS
        # ====================================================

        pangkat_baru = get_pangkat_otomatis(
                status_baru,
                gol_baru
        )

        st.text_input(
            "Pangkat",
            value=(
                pangkat_baru
                if pangkat_baru
                else "-"
            ),
            disabled=True,
        )

    # ========================================================
    # KOLOM KANAN
    # ========================================================

    with col2:

        jabatan_baru = st.text_input(
            "Jabatan",
            key="tambah_jabatan"
        )

        bidang_baru = st.selectbox(
    "Bidang",
    options=bidang_master,
    index=0,
    key="tambah_bidang"
)

        instansi_baru = st.text_input(
            "Instansi",
            value=(
                "Kanwil Kementerian Agama "
                "Provinsi Jawa Tengah"
            ),
            key="tambah_instansi"
        )

    st.write("")

    # ========================================================
    # SIMPAN
    # ========================================================

    if st.button(
        "💾 Simpan Pegawai",
        type="primary",
        use_container_width=True,
        key="btn_tambah_pegawai"
    ):

        error = []

        nip_clean = (
            nip_baru
            .strip()
        )

        nama_clean = (
            nama_baru
            .strip()
        )

        if not nip_clean:

            error.append(
                "NIP wajib diisi."
            )

        if not nama_clean:

            error.append(
                "Nama wajib diisi."
            )

        if (
            nip_clean
            and
            not nip_clean.isdigit()
        ):

            error.append(
                "NIP hanya boleh "
                "berisi angka."
            )

        if (
            status_baru == "PNS"
            and
            gol_baru == "-"
            ):

            error.append(
                "Golongan / Ruang PNS "
                "wajib dipilih."
            )


        if error:

            for item in error:
                st.error(item)

        else:

            try:

                with st.spinner(
                    "Menyimpan pegawai..."
                ):

                    tambah_pegawai(
                        nip=nip_clean,
                        nama=nama_clean,
                        pangkat=pangkat_baru,
                        gol_ruang=gol_baru,
                        jabatan=jabatan_baru,
                        bidang=bidang_baru,
                        instansi=instansi_baru,
                        status_pegawai=status_baru
                    )

                get_all_pegawai.clear()

                st.session_state[
                    "pegawai_message"
                ] = {
                    "type": "success",
                    "text": (
                        "Pegawai berhasil "
                        "ditambahkan."
                    )
                }

                # ============================================
                # RESET INPUT TAMBAH
                # ============================================

                for key in [
                    "tambah_nip",
                    "tambah_nama",
                    "tambah_jabatan",
                    "tambah_bidang"
                ]:
                    if key in st.session_state:
                        del st.session_state[key]

                st.rerun()

            except Exception as e:

                st.error(
                    "Gagal menambahkan pegawai."
                )

                st.code(
                    str(e)
                )


# ============================================================
# TAB EDIT / HAPUS
# ============================================================

with tab_edit:

    st.subheader(
        "Edit / Hapus Pegawai"
    )

    if not pegawai_list:

        st.info(
            "Belum ada data pegawai."
        )

    else:

        # ====================================================
        # PILIH PEGAWAI
        # ====================================================

        pegawai_map = {
            (
                f"{p.get('nama', '')} "
                f"- "
                f"{format_nip(p.get('nip'))}"
            ): p
            for p in pegawai_list
        }

        selected_label = st.selectbox(
            "Pilih Pegawai",
            options=list(
                pegawai_map.keys()
            ),
            key="select_edit_pegawai"
        )

        selected = (
            pegawai_map[
                selected_label
            ]
        )

        selected_id = str(
            selected.get(
                "id",
                ""
            )
            or ""
        ).strip()

        st.caption(
            f"ID Pegawai: {selected_id}"
        )

        # ====================================================
        # DATA LAMA
        # ====================================================

        status_sekarang = str(
            selected.get(
                "status_pegawai",
                ""
            )
            or ""
        ).strip()

        gol_sekarang = str(
            selected.get(
                "gol_ruang",
                ""
            )
            or ""
        ).strip()

        pangkat_sekarang = str(
            selected.get(
                "pangkat",
                ""
            )
            or ""
        ).strip()

        bidang_sekarang = str(
            selected.get(
                "bidang",
                ""
            )
            or ""
        ).strip()

        instansi_sekarang = str(
            selected.get(
                "instansi",
                ""
            )
            or ""
        ).strip()

        jabatan_sekarang = str(
            selected.get(
                "jabatan",
                ""
            )
            or ""
        ).strip()

        if not bidang_sekarang:
            bidang_sekarang = "-"

        # ====================================================
        # STATUS OPTIONS
        # ====================================================

        status_options = [
            "PNS",
            "PPPK",
            "CPNS",
            "PPPK PARUH WAKTU",
            "-"
        ]

        if (
            status_sekarang
            and
            status_sekarang not in status_options
        ):
            status_options.insert(
                0,
                status_sekarang
            )

        status_index = (
            status_options.index(
                status_sekarang
            )
            if status_sekarang in status_options
            else 0
        )

        # ====================================================
        # KOLOM EDIT
        # ====================================================

        col1, col2 = st.columns(
            2
        )

        # ====================================================
        # KOLOM KIRI
        # ====================================================

        with col1:

            edit_nip = st.text_input(
                "NIP *",
                value=format_nip(
                    selected.get(
                        "nip"
                    )
                ),
                key=(
                    f"edit_nip_{selected_id}"
                )
            )

            edit_nama = st.text_input(
                "Nama *",
                value=str(
                    selected.get(
                        "nama",
                        ""
                    )
                    or ""
                ),
                key=(
                    f"edit_nama_{selected_id}"
                )
            )

            edit_status = st.selectbox(
                "Status Pegawai *",
                options=status_options,
                index=status_index,
                key=(
                    f"edit_status_{selected_id}"
                )
            )

            # ================================================
            # GOLONGAN / RUANG
            # ================================================

            if edit_status in [
                "PNS",
                "CPNS"
            ]:

                gol_options = [
                    "-",
                    "I/a",
                    "I/b",
                    "I/c",
                    "I/d",
                    "II/a",
                    "II/b",
                    "II/c",
                    "II/d",
                    "III/a",
                    "III/b",
                    "III/c",
                    "III/d",
                    "IV/a",
                    "IV/b",
                    "IV/c",
                    "IV/d",
                    "IV/e"
                ]

                if (
                    gol_sekarang
                    and
                    gol_sekarang not in gol_options
                ):
                    gol_options.insert(
                        1,
                        gol_sekarang
                    )

                gol_index = (
                    gol_options.index(
                        gol_sekarang
                    )
                    if gol_sekarang in gol_options
                    else 0
                )

                edit_gol = st.selectbox(
                    "Golongan / Ruang *",
                    options=gol_options,
                    index=gol_index,
                    key=(
                        f"edit_gol_asn_"
                        f"{selected_id}"
                    )
                )

                # ============================================
                # PANGKAT OTOMATIS PNS / CPNS
                # ============================================

                edit_pangkat = (
                    get_pangkat_otomatis(
                        edit_status,
                        edit_gol
                    )
                )

                st.text_input(
                    "Pangkat",
                    value=(
                        edit_pangkat
                        if edit_pangkat
                        else "-"
                    ),
                    disabled=True,
                    key=(
                        f"edit_pangkat_preview_"
                        f"{selected_id}_"
                        f"{edit_status}"
                    )
                )

            else:

                # ============================================
                # PPPK / PPPK PARUH WAKTU / EKSTERNAL
                # Golongan dan pangkat tidak memakai mapping PNS.
                # ============================================

                edit_gol = st.text_input(
                    "Golongan / Ruang",
                    value=gol_sekarang,
                    placeholder=(
                        "Contoh PPPK: V, VII, IX"
                    ),
                    key=(
                        f"edit_gol_nonpns_"
                        f"{selected_id}"
                    )
                )

                edit_pangkat = st.text_input(
                    "Pangkat",
                    value=(
                        pangkat_sekarang
                        if pangkat_sekarang
                        else "-"
                    ),
                    key=(
                        f"edit_pangkat_nonpns_"
                        f"{selected_id}_"
                        f"{edit_status}"
                    )
                )

        # ====================================================
        # KOLOM KANAN
        # ====================================================

        with col2:

            edit_jabatan = st.text_input(
                "Jabatan",
                value=jabatan_sekarang,
                key=(
                    f"edit_jabatan_"
                    f"{selected_id}"
                )
            )

            # ================================================
            # BIDANG
            # ================================================

            edit_bidang_options = (
                bidang_master.copy()
            )

            if (
                bidang_sekarang
                not in edit_bidang_options
            ):
                edit_bidang_options.append(
                    bidang_sekarang
                )

            # Pastikan "-" hanya satu kali dan di posisi pertama.
            edit_bidang_options = [
                "-"
            ] + sorted({
                str(bidang).strip()
                for bidang in edit_bidang_options
                if (
                    str(bidang).strip()
                    and
                    str(bidang).strip() != "-"
                )
            })

            bidang_index = (
                edit_bidang_options.index(
                    bidang_sekarang
                )
                if bidang_sekarang in edit_bidang_options
                else 0
            )

            edit_bidang = st.selectbox(
                "Bidang",
                options=edit_bidang_options,
                index=bidang_index,
                key=(
                    f"edit_bidang_"
                    f"{selected_id}"
                )
            )

            edit_instansi = st.text_input(
                "Instansi",
                value=instansi_sekarang,
                key=(
                    f"edit_instansi_"
                    f"{selected_id}"
                )
            )

        # ====================================================
        # BUTTON UPDATE
        # ====================================================

        st.write("")

        if st.button(
            "💾 Simpan Perubahan",
            type="primary",
            use_container_width=True,
            key=(
                f"btn_update_pegawai_"
                f"{selected_id}"
            )
        ):

            error = []

            edit_nip_clean = (
                edit_nip.strip()
            )

            edit_nama_clean = (
                edit_nama.strip()
            )

            edit_pangkat_clean = str(
                edit_pangkat or ""
            ).strip()

            edit_gol_clean = str(
                edit_gol or ""
            ).strip()

            # ================================================
            # VALIDASI
            # ================================================

            if not edit_nip_clean:

                error.append(
                    "NIP wajib diisi."
                )

            if not edit_nama_clean:

                error.append(
                    "Nama wajib diisi."
                )

            if (
                edit_nip_clean
                and
                not edit_nip_clean.isdigit()
            ):

                error.append(
                    "NIP hanya boleh "
                    "berisi angka."
                )

            if (
                edit_status in [
                    "PNS",
                    "CPNS"
                ]
                and
                edit_gol_clean in [
                    "",
                    "-"
                ]
            ):

                error.append(
                    "Golongan / Ruang "
                    f"{edit_status} wajib dipilih."
                )

            # ================================================
            # TAMPILKAN ERROR
            # ================================================

            if error:

                for item in error:
                    st.error(
                        item
                    )

            else:

                try:

                    with st.spinner(
                        "Memperbarui pegawai..."
                    ):

                        update_pegawai(
                            pegawai_id=selected_id,
                            nip=edit_nip_clean,
                            nama=edit_nama_clean,
                            pangkat=edit_pangkat_clean,
                            gol_ruang=edit_gol_clean,
                            jabatan=edit_jabatan.strip(),
                            bidang=edit_bidang,
                            instansi=edit_instansi.strip(),
                            status_pegawai=edit_status
                        )

                    get_all_pegawai.clear()

                    st.session_state[
                        "pegawai_message"
                    ] = {
                        "type": "success",
                        "text": (
                            "Data pegawai berhasil "
                            "diperbarui."
                        )
                    }

                    st.rerun()

                except Exception as e:

                    st.error(
                        "Gagal memperbarui pegawai."
                    )

                    st.code(
                        str(e)
                    )

        # ====================================================
        # HAPUS PEGAWAI
        # ====================================================

        st.divider()

        st.subheader(
            "Hapus Pegawai"
        )

        st.warning(
            "Penghapusan bersifat permanen. "
            "Pastikan pegawai yang dipilih "
            "sudah benar."
        )

        konfirmasi = st.checkbox(
            (
                "Saya yakin ingin menghapus "
                f"{selected.get('nama', '')}"
            ),
            key=(
                f"confirm_delete_"
                f"{selected_id}"
            )
        )

        if st.button(
            "🗑️ Hapus Pegawai",
            disabled=not konfirmasi,
            use_container_width=True,
            key=(
                f"btn_delete_pegawai_"
                f"{selected_id}"
            )
        ):

            try:

                with st.spinner(
                    "Menghapus pegawai..."
                ):

                    hapus_pegawai(
                        selected_id
                    )

                get_all_pegawai.clear()

                st.session_state[
                    "pegawai_message"
                ] = {
                    "type": "success",
                    "text": (
                        "Pegawai berhasil "
                        "dihapus."
                    )
                }

                st.rerun()

            except Exception as e:

                st.error(
                    "Gagal menghapus pegawai."
                )

                st.code(
                    str(e)
                )

                
# ============================================================
# TAB MASTER PPK
# ============================================================

with tab_ppk:

    st.subheader(
        "Master Pejabat Pembuat Komitmen"
    )

    st.caption(
        "Tetapkan pegawai sebagai Pejabat Pembuat Komitmen "
        "berdasarkan bidang."
    )


    # ========================================================
    # INFORMASI PPK AKTIF
    # ========================================================

    ppk_aktif = [
        ppk
        for ppk in ppk_list
        if int(
            ppk.get(
                "aktif",
                0
            )
            or 0
        ) == 1
    ]


    col_metric1, col_metric2 = st.columns(
        2
    )

    with col_metric1:

        st.metric(
            "Total PPK",
            len(ppk_list)
        )

    with col_metric2:

        st.metric(
            "PPK Aktif",
            len(ppk_aktif)
        )


    st.divider()


    # ========================================================
    # TAMBAH / TETAPKAN PPK
    # ========================================================

    st.markdown(
        "### Tambah / Tetapkan PPK"
    )


    # ========================================================
    # PEGAWAI YANG DAPAT DIPILIH
    # ========================================================

    pegawai_options = {}

    for pegawai in pegawai_list:

        pegawai_id = str(
            pegawai.get(
                "id",
                ""
            )
        ).strip()

        nama = str(
            pegawai.get(
                "nama",
                ""
            )
        ).strip()

        nip = str(
            pegawai.get(
                "nip",
                ""
            )
        ).strip()

        bidang = str(
            pegawai.get(
                "bidang",
                ""
            )
        ).strip()

        if not pegawai_id:
            continue

        label = (
            f"{nama} | NIP {nip}"
        )

        if bidang not in (
            "",
            "-"
        ):

            label += (
                f" | {bidang}"
            )

        pegawai_options[
            label
        ] = pegawai


    if not pegawai_options:

        st.warning(
            "Belum ada data pegawai "
            "yang dapat dipilih."
        )

    else:

        col1, col2 = st.columns(
            2
        )


        # ====================================================
        # KOLOM KIRI
        # ====================================================

        with col1:

            selected_pegawai_label = (
                st.selectbox(
                    "Pegawai PPK *",
                    options=list(
                        pegawai_options.keys()
                    ),
                    key="ppk_pegawai_baru"
                )
            )


            selected_pegawai = (
                pegawai_options[
                    selected_pegawai_label
                ]
            )
            
            tanggal_mulai_ppk = (
                        st.date_input(
                            "Tanggal Mulai",
                            key=
                                "ppk_tanggal_mulai_baru"
                        )
                    )

            pakai_tanggal_selesai = (
                                        st.checkbox(
                                            "Tetapkan tanggal selesai",
                                            value=False,
                                            key=
                                                "ppk_pakai_tanggal_selesai"
                                        )
                                    )
                        
            aktif_ppk_baru = (
                            st.checkbox(
                                "PPK Aktif",
                                value=True,
                                key="ppk_aktif_baru"
                            )
                        )

        # ====================================================
        # KOLOM KANAN
        # ====================================================

        with col2:

            bidang_pegawai = str(
                selected_pegawai.get(
                    "bidang",
                    ""
                )
            ).strip()


            # Pastikan bidang pegawai tersedia
            # di pilihan bidang.
            pilihan_bidang_ppk = [
                bidang
                for bidang in bidang_master
                if bidang != "-"
            ]


            if (
                bidang_pegawai
                and
                bidang_pegawai != "-"
                and
                bidang_pegawai
                not in pilihan_bidang_ppk
            ):

                pilihan_bidang_ppk.append(
                    bidang_pegawai
                )


            pilihan_bidang_ppk = sorted(
                pilihan_bidang_ppk
            )


            if pilihan_bidang_ppk:

                if (
                    bidang_pegawai
                    in pilihan_bidang_ppk
                ):

                    index_bidang = (
                        pilihan_bidang_ppk.index(
                            bidang_pegawai
                        )
                    )

                else:

                    index_bidang = 0


                bidang_ppk_baru = st.selectbox(
                    "Untuk Bidang *",
                    options=
                        pilihan_bidang_ppk,
                    index=
                        index_bidang,
                    key="ppk_bidang_baru"
                )

            else:

                bidang_ppk_baru = ""

                st.warning(
                    "Belum ada data bidang."
                )


            


            if pakai_tanggal_selesai:

                tanggal_selesai_ppk = (
                    st.date_input(
                        "Tanggal Selesai",
                        key=
                            "ppk_tanggal_selesai_baru"
                    )
                )

            else:

                tanggal_selesai_ppk = None


            


        # ====================================================
        # SIMPAN
        # ====================================================

        if st.button(
            "💾 Simpan PPK",
            type="primary",
            use_container_width=True,
            key="btn_simpan_ppk"
        ):

            try:

                if not bidang_ppk_baru:

                    st.warning(
                        "Bidang wajib dipilih."
                    )

                else:

                    pegawai_id = str(
                        selected_pegawai.get(
                            "id",
                            ""
                        )
                    ).strip()


                    tanggal_mulai_value = (
                        tanggal_mulai_ppk.strftime(
                            "%Y-%m-%d"
                        )
                        if tanggal_mulai_ppk
                        else ""
                    )


                    tanggal_selesai_value = (
                        tanggal_selesai_ppk.strftime(
                            "%Y-%m-%d"
                        )
                        if tanggal_selesai_ppk
                        else ""
                    )


                    tambah_ppk(
                        pegawai_id=
                            pegawai_id,

                        bidang=
                            bidang_ppk_baru,

                        aktif=
                            1
                            if aktif_ppk_baru
                            else 0,

                        tanggal_mulai=
                            tanggal_mulai_value,

                        tanggal_selesai=
                            tanggal_selesai_value
                    )


                    st.session_state[
                        "pegawai_message"
                    ] = {
                        "type":
                            "success",

                        "text":
                            "PPK berhasil "
                            "ditambahkan."
                    }


                    st.rerun()

            except Exception as e:

                st.error(
                    "Gagal menyimpan PPK."
                )

                st.code(
                    str(e)
                )


    # ========================================================
    # DAFTAR PPK
    # ========================================================

    st.divider()

    st.markdown(
        "### Daftar PPK"
    )


    if not ppk_list:

        st.info(
            "Belum ada data PPK."
        )

    else:

        for ppk in ppk_list:

            ppk_id = str(
                ppk.get(
                    "id",
                    ""
                )
            ).strip()

            nama = str(
                ppk.get(
                    "nama",
                    "-"
                )
            ).strip()

            nip = str(
                ppk.get(
                    "nip",
                    "-"
                )
            ).strip()

            bidang = str(
                ppk.get(
                    "bidang",
                    "-"
                )
            ).strip()

            aktif = int(
                ppk.get(
                    "aktif",
                    0
                )
                or 0
            )

            tanggal_mulai = str(
                ppk.get(
                    "tanggal_mulai",
                    ""
                )
            ).strip()

            tanggal_selesai = str(
                ppk.get(
                    "tanggal_selesai",
                    ""
                )
            ).strip()


            status_text = (
                "🟢 Aktif"
                if aktif == 1
                else "⚪ Tidak Aktif"
            )


            with st.expander(
                f"{nama} — {bidang} — {status_text}"
            ):

                col_info1, col_info2 = (
                    st.columns(
                        2
                    )
                )


                with col_info1:

                    st.write(
                        f"**Nama:** {nama}"
                    )

                    st.write(
                        f"**NIP:** {nip}"
                    )

                    st.write(
                        f"**Bidang:** {bidang}"
                    )


                with col_info2:

                    st.write(
                        f"**Status:** "
                        f"{'Aktif' if aktif == 1 else 'Tidak Aktif'}"
                    )

                    st.write(
                        f"**Tanggal Mulai:** "
                        f"{tanggal_mulai or '-'}"
                    )

                    st.write(
                        f"**Tanggal Selesai:** "
                        f"{tanggal_selesai or '-'}"
                    )


                st.divider()


                # ============================================
                # EDIT PPK
                # ============================================

                st.markdown(
                    "**Edit PPK**"
                )


                edit_pegawai_options = {}

                for pegawai in pegawai_list:

                    pegawai_id = str(
                        pegawai.get(
                            "id",
                            ""
                        )
                    ).strip()

                    pegawai_nama = str(
                        pegawai.get(
                            "nama",
                            ""
                        )
                    ).strip()

                    pegawai_nip = str(
                        pegawai.get(
                            "nip",
                            ""
                        )
                    ).strip()

                    label = (
                        f"{pegawai_nama} | "
                        f"NIP {pegawai_nip}"
                    )

                    edit_pegawai_options[
                        label
                    ] = pegawai


                current_pegawai_id = str(
                    ppk.get(
                        "pegawai_id",
                        ""
                    )
                ).strip()


                current_label = None

                for (
                    label,
                    pegawai
                ) in edit_pegawai_options.items():

                    if str(
                        pegawai.get(
                            "id",
                            ""
                        )
                    ).strip() == (
                        current_pegawai_id
                    ):

                        current_label = label

                        break


                edit_labels = list(
                    edit_pegawai_options.keys()
                )


                if (
                    current_label
                    in edit_labels
                ):

                    edit_index = (
                        edit_labels.index(
                            current_label
                        )
                    )

                else:

                    edit_index = 0


                edit_col1, edit_col2 = (
                    st.columns(
                        2
                    )
                )


                with edit_col1:

                    edit_pegawai_label = (
                        st.selectbox(
                            "Pegawai",
                            options=
                                edit_labels,
                            index=
                                edit_index,
                            key=
                                f"edit_ppk_pegawai_{ppk_id}"
                        )
                    )


                    edit_pegawai = (
                        edit_pegawai_options[
                            edit_pegawai_label
                        ]
                    )


                    edit_bidang_options = [
                        item
                        for item
                        in bidang_master
                        if item != "-"
                    ]


                    if (
                        bidang
                        and
                        bidang != "-"
                        and
                        bidang
                        not in edit_bidang_options
                    ):

                        edit_bidang_options.append(
                            bidang
                        )


                    edit_bidang_options = sorted(
                        edit_bidang_options
                    )


                    if (
                        bidang
                        in edit_bidang_options
                    ):

                        edit_bidang_index = (
                            edit_bidang_options.index(
                                bidang
                            )
                        )

                    else:

                        edit_bidang_index = 0


                    edit_bidang = (
                        st.selectbox(
                            "Bidang",
                            options=
                                edit_bidang_options,
                            index=
                                edit_bidang_index,
                            key=
                                f"edit_ppk_bidang_{ppk_id}"
                        )
                    )


                with edit_col2:

                    edit_aktif = (
                        st.checkbox(
                            "Aktif",
                            value=
                                aktif == 1,
                            key=
                                f"edit_ppk_aktif_{ppk_id}"
                        )
                    )


                    edit_tanggal_mulai = (
                        st.text_input(
                            "Tanggal Mulai",
                            value=
                                tanggal_mulai,
                            placeholder=
                                "YYYY-MM-DD",
                            key=
                                f"edit_ppk_mulai_{ppk_id}"
                        )
                    )


                    edit_tanggal_selesai = (
                        st.text_input(
                            "Tanggal Selesai",
                            value=
                                tanggal_selesai,
                            placeholder=
                                "YYYY-MM-DD",
                            key=
                                f"edit_ppk_selesai_{ppk_id}"
                        )
                    )


                col_update, col_delete = (
                    st.columns(
                        [3, 1]
                    )
                )


                with col_update:

                    if st.button(
                        "💾 Simpan Perubahan PPK",
                        type="primary",
                        use_container_width=True,
                        key=
                            f"btn_update_ppk_{ppk_id}"
                    ):

                        try:

                            update_ppk(
                                ppk_id=
                                    ppk_id,

                                pegawai_id=
                                    str(
                                        edit_pegawai.get(
                                            "id",
                                            ""
                                        )
                                    ).strip(),

                                bidang=
                                    edit_bidang,

                                aktif=
                                    1
                                    if edit_aktif
                                    else 0,

                                tanggal_mulai=
                                    edit_tanggal_mulai,

                                tanggal_selesai=
                                    edit_tanggal_selesai
                            )


                            st.session_state[
                                "pegawai_message"
                            ] = {
                                "type":
                                    "success",

                                "text":
                                    "Data PPK berhasil "
                                    "diperbarui."
                            }


                            st.rerun()

                        except Exception as e:

                            st.error(
                                "Gagal memperbarui PPK."
                            )

                            st.code(
                                str(e)
                            )


                with col_delete:

                    if st.button(
                        "🗑️ Hapus",
                        type="secondary",
                        use_container_width=True,
                        key=
                            f"btn_delete_ppk_{ppk_id}"
                    ):

                        try:

                            hapus_ppk(
                                ppk_id
                            )


                            st.session_state[
                                "pegawai_message"
                            ] = {
                                "type":
                                    "success",

                                "text":
                                    "Data PPK berhasil "
                                    "dihapus."
                            }


                            st.rerun()

                        except Exception as e:

                            st.error(
                                "Gagal menghapus PPK."
                            )

                            st.code(
                                str(e)
                            )