import os
import shutil
import subprocess
import streamlit as st


def convert_docx_to_pdf(docx_path, pdf_path):
    """
    Convert DOCX ke PDF menggunakan LibreOffice headless.
    Bisa digunakan di Linux / Streamlit Community Cloud.
    """

    if not os.path.exists(docx_path):
        raise FileNotFoundError(
            f"File Word tidak ditemukan: {docx_path}"
        )

    output_dir = os.path.dirname(pdf_path)

    if not output_dir:
        output_dir = "."

    os.makedirs(
        output_dir,
        exist_ok=True
    )

    # Cari executable LibreOffice
    libreoffice = (
        shutil.which("libreoffice")
        or shutil.which("soffice")
    )

    if not libreoffice:
        raise RuntimeError(
            "LibreOffice tidak ditemukan."
        )

    result = subprocess.run(
        [
            libreoffice,
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            output_dir,
            docx_path
        ],
        capture_output=True,
        text=True,
        timeout=120
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Gagal convert DOCX ke PDF.\n"
            f"{result.stderr}"
        )

    # LibreOffice membuat nama berdasarkan
    # nama DOCX.
    generated_pdf = os.path.join(
        output_dir,
        (
            os.path.splitext(
                os.path.basename(docx_path)
            )[0]
            + ".pdf"
        )
    )

    if not os.path.exists(generated_pdf):
        raise FileNotFoundError(
            "LibreOffice selesai tetapi "
            "file PDF tidak ditemukan."
        )

    # Jika nama tujuan berbeda
    if os.path.abspath(
        generated_pdf
    ) != os.path.abspath(
        pdf_path
    ):

        if os.path.exists(pdf_path):
            os.remove(pdf_path)

        os.replace(
            generated_pdf,
            pdf_path
        )

    return pdf_path


def show_pdf(pdf_path, height=900):
    """
    Preview PDF di Streamlit.
    """

    if not pdf_path:
        st.info(
            "Belum ada PDF untuk ditampilkan."
        )
        return

    if not os.path.exists(pdf_path):
        st.error(
            "File PDF tidak ditemukan."
        )
        return

    try:

        st.pdf(
            pdf_path,
            height=height
        )

    except Exception as e:

        st.error(
            f"Gagal menampilkan PDF: {e}"
        )