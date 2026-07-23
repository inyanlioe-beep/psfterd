# Rencana Implementasi: Ekstraktor Schema PeopleSoft & Visualisasi ERD Offline

Dokumen ini berisi rencana teknis untuk menambahkan script ekstraksi metadata database PeopleSoft dan fitur upload file JSON ke dalam aplikasi web ERD Explorer agar visualisasi ERD dapat dilakukan secara mandiri (offline).

## Deskripsi Fitur

1. **Script Ekstraksi Metadata (`peoplesoft_extractor.py`)**:
   - Sebuah file Python standalone yang dirancang untuk dijalankan di server database PeopleSoft (Oracle, MS SQL Server, PostgreSQL, atau SQLite).
   - Menghubungkan secara dinamis menggunakan driver DB yang tersedia (`oracledb`, `pyodbc`, `psycopg2`, dll.).
   - Menyediakan interface CLI interaktif untuk mencari record/tabel (berdasarkan nama/wildcard) dari tabel sistem `PSRECDEFN`.
   - Mengizinkan pengguna memilih beberapa tabel sekaligus (multiselect menggunakan nomor indeks, range, atau opsi 'all').
   - Mengekstrak struktur kolom, tipe data, panjang, kunci primer (primary keys), deskripsi, relasi parent-child, dan prompt tables dari `PSRECDEFN`, `PSRECFIELD`, dan `PSDBFIELD`.
   - Menyimpan seluruh metadata ke dalam file JSON terformat (misalnya `peoplesoft_export.json`).

2. **Fitur Upload JSON & Rendering ERD Offline pada Web**:
   - Menambahkan tombol "Upload JSON" di header dan area "Actions" sidebar.
   - Menambahkan fitur **Drag-and-Drop** di atas kanvas Cytoscape untuk mengunggah file JSON dengan efek visual transparan blur yang modern.
   - Menangani pembacaan JSON secara instan di sisi klien (frontend).
   - Mengaktifkan **Offline / Uploaded JSON Mode** di mana status badge berubah warna menjadi ungu (`Offline (Uploaded JSON)`) dan semua komponen UI (pencarian lokal, detail sidebar, relasi, layout) berjalan berdasarkan data JSON tanpa perlu koneksi ke database backend Flask.
   - Melakukan kalkulasi relasi antartabel secara dinamis di frontend menggunakan logika relasi PeopleSoft (Parent-Child, Prompt Table, Key-Join).

---

## Rencana Perubahan Kode

### 1. Script Ekstraktor (Server Database)
#### [NEW] [peoplesoft_extractor.py](file:///d:/project/psfterd/peoplesoft_extractor.py)
- Implementasi script Python CLI interaktif.
- Pilihan koneksi database (Oracle, SQL Server, PostgreSQL, SQLite).
- Logika query interaktif untuk `PSRECDEFN` & `PSRECFIELD`.
- Output file JSON yang kompatibel dengan format web.

---

### 2. Frontend & Dashboard Web
#### [MODIFY] [index.html](file:///d:/project/psfterd/templates/index.html)
- Menambahkan tombol **Upload JSON** dengan ikon `lucide-upload` di header sebelah tombol database settings.
- Menambahkan elemen `<input type="file" id="uploadJsonInput" accept=".json">` tersembunyi.
- Menambahkan div overlay `#dragOverlay` di dalam `.canvas-panel` untuk feedback visual ketika user melakukan drag-and-drop file JSON.

#### [MODIFY] [style.css](file:///d:/project/psfterd/static/css/style.css)
- Menambahkan gaya untuk `#dragOverlay` (tampilan blueprint glassmorphic dengan tulisan "Drop JSON here to generate ERD").
- Menambahkan gaya indikator status koneksi khusus untuk mode offline/upload (warna ungu/violet).
- Transisi halus untuk input upload dan efek seret file.

#### [MODIFY] [erd.js](file:///d:/project/psfterd/static/js/erd.js)
- Menambahkan listener event click pada tombol upload, dragover, dragleave, dan drop pada kanvas.
- Mengimplementasikan parser JSON di sisi klien:
  - Membaca file JSON, menyimpannya ke state `uploadedRecords` (Map).
  - Mengubah mode ke `isUploadedMode = true`.
  - Memasukkan semua record hasil upload ke `activeRecords` untuk langsung merender diagram ERD.
  - Memperbarui badge status database.
- Memodifikasi method `addTableToWorkspace`, `updateRelationships`, `list_records` (pencarian lokal), dan `exportSql` agar otomatis mengambil data dari `uploadedRecords` secara lokal jika sedang dalam `isUploadedMode`, alih-alih melakukan fetch API ke backend database Flask.
- Menulis ulang kalkulasi relasi parent-child, prompt table, dan key-join langsung di JS agar kompatibel dengan data offline.

---

## Rencana Verifikasi

### Manual Verification
1. **Verifikasi Script Ekstraktor**:
   - Jalankan `peoplesoft_extractor.py` secara lokal dan pilih SQLite Mock Database (karena kita memiliki file `peoplesoft_mock.db` di project).
   - Cari kata kunci `JOB`, pilih tabel 1, 2, dan 3.
   - Ekspor ke `peoplesoft_export.json` dan pastikan file JSON terbuat dengan struktur kolom lengkap.
2. **Verifikasi Upload di Web**:
   - Buka aplikasi web (jalankan `run.bat`).
   - Seret (drag and drop) file JSON hasil ekstraksi ke kanvas web explorer.
   - Pastikan overlay drag muncul dan ERD langsung ter-render dengan benar setelah file di-drop.
   - Klik salah satu tabel, pastikan detail kolom dan primary keys (PK) tampil di sidebar kanan.
   - Coba hapus tabel dan cari kembali melalui search bar di kiri (pencarian lokal data upload).
   - Coba generate SQL DDL dan pastikan bekerja dengan sukses pada mode upload ini.
