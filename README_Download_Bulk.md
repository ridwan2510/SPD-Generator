# Download SPD Bulk — TTE Kemenag

Menu baru `3_Download_SPD_Bulk.py` membaca daftar dokumen melalui endpoint DataTables JSON:
`/satker/dokumen/naskah/data_index` dengan `type=unggah`.

## Cara kerja
- Login menggunakan konfigurasi akun TTE yang sudah ada pada Streamlit Secrets.
- Membaca daftar JSON dan menampilkan urutan, waktu, perihal, status, serta label tombol unduh.
- Nomor rentang mengikuti baris respons daftar TTE, bukan nomor surat SPD.
- Hanya baris dengan label tombol/status FINAL dan tautan `href` yang dikirim server yang dicoba diunduh sebagai PDF.
- Draft/Sedang Proses dicatat sebagai `Dilewati`, karena tautan pada baris tersebut bukan PDF FINAL.
- Hasil PDF yang berhasil diunduh dikemas ke ZIP; status berhasil/dilewati/gagal ditampilkan terpisah.

## Catatan
Jalur unduh tidak dibuat berdasarkan `path_signed_dokumen`; aplikasi memakai tautan aktual dari kolom `unduh` untuk menghindari menebak URL. Endpoint memerlukan sesi login yang sah. Uji langsung di lingkungan pengguna tetap diperlukan karena respons TTE bisa berubah atau akses bisa dibatasi.
