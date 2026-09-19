# Book 2 Management

Aplikasi web full-stack untuk mengelola **pengajuan, approval, pemeriksaan editor,
revisi, dan produksi buku** — mulai dari request oleh pengaju, persetujuan berjenjang,
review editor, preview digital (flipbook), hingga buku selesai dicetak oleh tim produksi.

Dibangun dengan Flask + Jinja2 + HTML/CSS/Vanilla JavaScript di atas PostgreSQL.
Tidak menggunakan framework frontend apa pun.

---

## 1. Overview

Sistem ini adalah alat manajemen alur kerja penerbitan buku internal, dengan alur inti:

```
Request → Approval → Editor Review → Dummy/Preview (Flipbook) → Production → Completed
```

- **Request** — pengaju (`USER`) membuat pengajuan buku: data buku, anggota/kontributor,
  materi text, cover, dan file PDF isi buku.
- **Approval** — admin (`ADMIN`, ditampilkan sebagai **Kabag**) memeriksa kelengkapan
  dan menyetujui atau mengembalikannya untuk diperbaiki.
- **Editor Review** — editor memeriksa cover, foto, nama anggota, layout, dan
  kebutuhan cetak lewat checklist; bisa mengembalikan untuk revisi.
- **Dummy/Preview** — begitu PDF sudah diunggah, siapa pun yang berhak melihat request
  (pengaju, admin, editor, produksi) dapat membuka **Digital Flipbook** untuk membaca
  isi buku sebagai pratinjau, tanpa harus membuka file PDF secara terpisah.
- **Production** — setelah editor menyatakan siap produksi, tim produksi mencetak,
  melakukan quality check, lalu menyelesaikan pesanan.

Seluruh perpindahan status divalidasi di backend oleh satu sumber kebenaran:
[app/workflow.py](app/workflow.py). Tahapan tidak dapat dilompati dan setiap transisi
hanya boleh dilakukan oleh role yang berwenang.

---

## 2. Role dan Hak Akses

Role disimpan di database sebagai `USER` / `ADMIN` / `EDITOR` / `PRODUCTION`
(tabel `roles`, lihat [app/models.py](app/models.py)), dan ditampilkan di UI dengan
label yang lebih deskriptif melalui `ROLE_LABELS` di
[app/workflow.py](app/workflow.py):

| Role (DB) | Label di UI | Hak Akses |
|-----------|-------------|-----------|
| `USER` | **Sekjen/Dewan** (Peminta) | Membuat request, mengelola anggota/text/file, upload PDF & cover, submit, mengirim tanggapan revisi, membatalkan draft, mengatur visibilitas Public/Private request miliknya sendiri |
| `ADMIN` | **Kabag** (Admin) | Review & approve/reject/return pengajuan, mengirim ke produksi, kelola user, kelola jenis buku, lihat audit log — memegang seluruh kewenangan `EDITOR` juga |
| `EDITOR` | **Editor** | Mengisi checklist pemeriksaan (cover, foto, nama anggota, layout, spesifikasi cetak), mengembalikan request untuk revisi, menyetujui request hingga siap produksi |
| `PRODUCTION` | **Produksi** | Memulai produksi, melakukan quality check, menyelesaikan order, mencatat riwayat produksi |

RBAC diterapkan di backend melalui dekorator role pada setiap route API maupun
halaman ([app/security.py](app/security.py)). Menyembunyikan menu di frontend
bukan satu-satunya pengaman — memanipulasi URL tetap menghasilkan `403`.

---

## 3. Workflow

```
DRAFT ──submit──▶ SUBMITTED ──▶ ADMIN_REVIEW ──▶ ADMIN_APPROVED ──▶ EDITOR_REVIEW
                                    │                                    │
                                    ▼ (kembalikan)                       ├──▶ EDITOR_APPROVED ──▶ READY_FOR_PRODUCTION ──▶ PRODUCTION
                                  DRAFT                                  │                                                    │
                                                                          ▼ (ada kesalahan)                                   ▼
                                                                  REVISION_REQUIRED                                   QUALITY_CHECK
                                                                          │                                             │        │
                                                                          ▼                                    (lolos) ▼        ▼ (gagal, cetak ulang)
                                                                   USER_REVISION ───▶ EDITOR_REVIEW           COMPLETED   PRODUCTION
```

Status yang digunakan (lihat `ALL_STATUSES` di [app/workflow.py](app/workflow.py)):

```
DRAFT · SUBMITTED · ADMIN_REVIEW · ADMIN_APPROVED · EDITOR_REVIEW
REVISION_REQUIRED · USER_REVISION · EDITOR_APPROVED · READY_FOR_PRODUCTION
PRODUCTION · QUALITY_CHECK · COMPLETED · REJECTED · CANCELLED
```

Ringkasan tahapan:

1. **Membuat request** — pengaju mengisi data buku (judul, jenis, deadline, anggota,
   spesifikasi cetak) dalam status `DRAFT`, bisa diedit bebas selama belum di-submit.
2. **Upload PDF & cover** — pengaju mengunggah file PDF isi buku dan gambar cover
   lewat `POST /api/requests/<id>/files`. File PDF terbaru pada request otomatis
   menjadi sumber flipbook (`BookRequest.pdf_file`), cover terbaru menjadi thumbnail
   (`BookRequest.cover_file`).
3. **Submit** — status berpindah ke `SUBMITTED`, request tidak lagi bisa diedit bebas
   oleh pengaju.
4. **Approval (Admin/Kabag)** — admin memindahkan ke `ADMIN_REVIEW`, lalu
   `ADMIN_APPROVED` (atau `REJECTED`, atau dikembalikan ke `DRAFT` untuk diperbaiki).
5. **Editor Review** — admin meneruskan ke `EDITOR_REVIEW`. Editor mengisi checklist
   pemeriksaan (`editor_checklists`) lalu memilih `EDITOR_APPROVED` atau
   `REVISION_REQUIRED`.
6. **Revision jika diperlukan** — pada `REVISION_REQUIRED`, pengaju memberi
   tanggapan (`USER_REVISION`), setiap putaran tersimpan sebagai baris baru di
   `request_revisions` lengkap dengan catatan editor dan tanggapan pengaju, lalu
   kembali ke `EDITOR_REVIEW`.
7. **Preview** — pada status `EDITOR_APPROVED` ke atas (lihat
   `PUBLIC_ELIGIBLE_STATUSES`), request boleh ditampilkan public dan dibaca lewat
   flipbook — sebelum status ini pun, PDF tetap bisa dibuka sebagai flipbook secara
   internal oleh pengaju, admin, editor, dan produksi dari halaman detail request.
8. **Ready for Production → Production** — editor menandai `READY_FOR_PRODUCTION`,
   admin mengirimkannya ke tim produksi (`PRODUCTION`).
9. **Quality Check → Completed** — tim produksi melakukan `QUALITY_CHECK`; jika lolos
   menjadi `COMPLETED`, jika gagal kembali ke `PRODUCTION` untuk dicetak ulang.

Setiap perpindahan status tercatat di `request_status_history` dan memicu
notifikasi ke pihak terkait.

---

## 4. Digital Flipbook

PDF adalah **sumber utama** isi buku. Pengaju cukup mengunggah PDF + cover, sistem
yang mengubahnya menjadi tampilan buku digital yang bisa dibalik halamannya
(page-flip) — flipbook dipakai untuk **preview/baca digital**, bukan pengganti file
PDF asli (file PDF asli tetap tersimpan utuh dan bisa diunduh).

```text
Upload PDF + Cover
        ↓
PDF diproses (pdf.js merender tiap halaman ke <canvas> → gambar JPEG)
        ↓
Kumpulan gambar halaman
        ↓
StPageFlip (page-flip@2.0.7) memuat gambar & mengaktifkan animasi flip
        ↓
Digital Flipbook (ditampilkan dalam modal)
```

Implementasi: [app/static/js/flipbook.js](app/static/js/flipbook.js), dijelaskan
lebih detail di [app/static/js/flipbook.md](app/static/js/flipbook.md).

- **pdf.js** (`pdfjsLib`, via CDN cloudflare) merender setiap halaman PDF secara
  berurutan menjadi data URL gambar (`canvas.toDataURL("image/jpeg", 0.85)`) agar
  urutan halaman terjaga.
- **StPageFlip** (`St.PageFlip`, paket npm `page-flip`) memuat kumpulan gambar
  tersebut (`flip.loadFromImages(images)`) dan menghasilkan animasi buka-halaman
  seperti buku fisik, dengan `size: "stretch"` agar menyesuaikan ukuran modal.
- Dipicu lewat fungsi global `App.openFlipbook(pdfUrl, title)`, yang membuka
  `App.modal` (mode `large`) berisi stage flipbook.
- Dipakai di dua tempat:
  - [public/home.html](app/templates/public/home.html) — tombol pada kartu buku
    public di halaman Home.
  - [dash/request_detail.html](app/templates/dash/request_detail.html) — tombol
    "Baca Flipbook" pada halaman detail request (tersedia untuk siapa pun yang
    berhak melihat request tersebut, terlepas dari status Public/Private-nya).

---

## 5. Public vs Private

Setiap `book_requests` punya kolom `is_public` (default `false`, hanya pemilik
request yang bisa mengubahnya lewat `PUT /api/requests/<id>/visibility`).

Syarat sebuah request bisa dijadikan **Public**:

- Sudah memiliki file PDF (`pdf_file`), dan
- Statusnya berada di `PUBLIC_ELIGIBLE_STATUSES`: `EDITOR_APPROVED`,
  `READY_FOR_PRODUCTION`, `PRODUCTION`, `QUALITY_CHECK`, atau `COMPLETED` —
  artinya sudah lolos pemeriksaan editor.

Selama **Private** (default), file PDF/cover request hanya bisa diakses lewat
`GET /api/files/<id>` yang mensyaratkan login dan hak akses atas request tersebut.

Setelah **Public**, dua endpoint publik tanpa login membuka file tersebut:

```
GET /books/<request_id>/pdf
GET /books/<request_id>/cover
```

dan requst tersebut otomatis muncul di seksi **"Buku dari Sekjen/Dewan"** pada
halaman Home ([public/home.html](app/templates/public/home.html)), sebagai kartu
yang langsung membuka Flipbook saat diklik.

Halaman Home juga punya seksi terpisah **"Katalog Buku Terbit"**, yang bersumber
dari tabel `ebook_showcase` (katalog e-book penerbit yang sudah ada, hanya
ditampilkan/dibaca, bukan hasil dari alur request) — kartu di seksi ini mengarah
keluar ke `source_url` masing-masing, bukan ke Flipbook internal.

---

## 6. Database

14 tabel dengan foreign key dan index (schema lengkap: [database.sql](database.sql),
model SQLAlchemy: [app/models.py](app/models.py)):

| Tabel | Fungsi |
|-------|--------|
| `roles` | Daftar role (`USER`, `ADMIN`, `EDITOR`, `PRODUCTION`) |
| `users` | Akun pengguna, password ter-hash, relasi ke `roles` |
| `book_types` | Jenis buku yang bisa diajukan (Jurnal, History, Majalah, dst) |
| `book_requests` | Data inti pengajuan buku: judul, spesifikasi cetak, status, `is_public`, pemilik |
| `book_members` | Daftar anggota/kontributor pada sebuah request |
| `book_files` | Metadata file (cover, foto anggota, dokumentasi, PDF isi buku, file final) — file fisik ada di `uploads/` |
| `book_texts` | Materi text per section (kata pengantar, deskripsi, biodata, isi buku, dst) |
| `request_status_history` | Riwayat setiap perpindahan status request (tidak bisa dihapus user) |
| `request_revisions` | Satu baris per putaran revisi, berisi catatan editor & tanggapan pengaju (tidak menimpa data lama) |
| `editor_checklists` | Checklist pemeriksaan editor per request |
| `notifications` | Notifikasi internal per user, terkait perpindahan status request |
| `production_orders` | Order produksi per request (status, penanggung jawab, tanggal mulai/QC/selesai) |
| `production_history` | Riwayat aksi pada setiap order produksi |
| `audit_logs` | Log audit aktivitas (aksi, perubahan status, aktor, IP) |
| `ebook_showcase` | Katalog e-book penerbit yang sudah terbit, ditampilkan read-only di Home (bukan hasil alur request) |

Catatan penting:

- **Revisi tidak menimpa data lama.** Setiap putaran revisi menjadi satu baris
  `request_revisions` tersendiri.
- **History tidak dapat dihapus user.** Setiap perpindahan status tercatat pada
  `request_status_history`.
- **File fisik disimpan di `uploads/`**, database hanya menyimpan metadata
  (`original_filename`, `stored_filename`, `mime_type`, `file_size`, `file_path`).
- **Statistik dashboard dihitung langsung dari database**, bukan angka statis.

---

## 7. Technology Stack

| Lapisan | Teknologi |
|---------|-----------|
| Backend | Python, Flask, Flask Blueprint, Flask REST API |
| ORM | SQLAlchemy, Flask-SQLAlchemy |
| Database | PostgreSQL (psycopg2-binary) |
| Frontend | Jinja2, HTML5, CSS3, Vanilla JavaScript |
| PDF rendering | [pdf.js](https://mozilla.github.io/pdf.js/) (`pdfjsLib`, via CDN) — merender halaman PDF ke canvas/gambar |
| Flipbook | [StPageFlip](https://github.com/Nodlik/StPageFlip) (paket `page-flip`, via CDN) — animasi page-flip dari kumpulan gambar |
| Keamanan | Werkzeug password hashing (scrypt), session auth, CSRF token |
| Konfigurasi | python-dotenv |
| Testing | pytest |

Tidak menggunakan Tailwind CSS, Gunicorn, maupun Docker — lihat
[requirements.txt](requirements.txt) untuk daftar dependency Python lengkap.

---

## 8. Installation & Configuration

### 1. Clone project

```bash
git clone <repo-url>
cd pintas_8
```

### 2. Virtual environment

```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS/Linux
```

### 3. Install requirements

```bash
pip install -r requirements.txt
```

### 4. Buat database

```sql
CREATE DATABASE book_management_2;
```

```bash
psql -U postgres -d book_management_2 -f database.sql
```

File `database.sql` berisi seluruh `CREATE TABLE`, primary key, foreign key, index,
unique constraint, check constraint, default value, timestamp, serta seed data
untuk roles, book types, dan development users.

### 5. Konfigurasi `.env`

Salin dari `.env.example`, lalu sesuaikan (contoh nilai development, **jangan pakai
nilai ini di production**):

```env
SECRET_KEY=dev-secret-key-change-in-production
DATABASE_URL=postgresql+psycopg2://<user>:<password>@127.0.0.1:5432/book_management_2
UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH=52428800
FLASK_ENV=development
```

File `.env` tidak diikutkan ke Git.

### 6. Jalankan

```bash
python run.py
```

| Halaman | URL |
|---------|-----|
| Home (publik) | http://127.0.0.1:5000/ |
| Login | http://127.0.0.1:5000/login |

---

## Akun Development

Hanya untuk local development. Password disimpan di database sebagai hash
(Werkzeug scrypt), bukan plaintext.

| Email | Username | Role | Password |
|-------|----------|------|----------|
| admin@example.com | admin | ADMIN (Kabag) | password123 |
| editor@example.com | editor | EDITOR | password123 |
| production@example.com | production | PRODUCTION | password123 |
| user@example.com | user | USER (Sekjen/Dewan) | password123 |

Setelah login, pengguna diarahkan ke dashboard sesuai rolenya:

```
USER       → /user/dashboard
ADMIN      → /admin/dashboard
EDITOR     → /editor/dashboard
PRODUCTION → /production/dashboard
```

---

## Struktur Proyek

```
pintas_8/
├── app/
│   ├── __init__.py          application factory, error handler, Jinja context
│   ├── config.py            konfigurasi dari .env
│   ├── extensions.py        instance SQLAlchemy
│   ├── models.py            14 model SQLAlchemy (termasuk EbookShowcase)
│   ├── workflow.py          state machine (satu sumber kebenaran transisi)
│   ├── security.py          session auth, RBAC, CSRF, validasi upload
│   ├── services.py          service layer: transisi, notifikasi, audit, query
│   ├── blueprints/
│   │   ├── public.py        home (public books + ebook showcase), tentang, alur, fitur
│   │   ├── auth.py          halaman login/logout
│   │   ├── dashboard.py     seluruh halaman setelah login
│   │   ├── api_auth.py      /api/auth
│   │   ├── api_requests.py  /api/requests (+ member, text, file, visibility)
│   │   ├── api_admin.py     /api/admin
│   │   ├── api_editor.py    /api/editor
│   │   ├── api_production.py /api/production
│   │   └── api_misc.py      notifikasi, history, statistik
│   ├── templates/           Jinja2 (base, komponen, publik, dashboard)
│   └── static/
│       ├── style.css, app.js, list.js
│       └── flipbook.js      render PDF → gambar (pdf.js) → StPageFlip
├── tests/                   pytest: auth, RBAC, workflow, file, halaman
├── uploads/                 file fisik (metadata di database)
├── database.sql             schema + seed PostgreSQL
├── requirements.txt
├── .env / .env.example
├── run.py
└── README.md
```

Arsitektur:

```
Browser → Jinja2 / Vanilla JS (+ pdf.js/StPageFlip untuk flipbook) → Flask Routes
        → Flask REST API → Service Layer → SQLAlchemy → PostgreSQL
```

---

## REST API

Seluruh respons berbentuk JSON.

Sukses:

```json
{ "success": true, "message": "Request berhasil disetujui", "data": {} }
```

Gagal:

```json
{ "success": false, "message": "Anda tidak memiliki akses", "errors": [] }
```

### Authentication

```http
POST   /api/auth/login
POST   /api/auth/logout
GET    /api/auth/me
PUT    /api/auth/me
```

### User Request

```http
GET    /api/requests
POST   /api/requests
GET    /api/requests/<id>
PUT    /api/requests/<id>
POST   /api/requests/<id>/submit
POST   /api/requests/<id>/revision
PUT    /api/requests/<id>/visibility
POST   /api/requests/<id>/cancel
POST   /api/requests/<id>/members
PUT    /api/requests/<id>/members/<member_id>
DELETE /api/requests/<id>/members/<member_id>
PUT    /api/requests/<id>/texts
POST   /api/requests/<id>/files
DELETE /api/requests/<id>/files/<file_id>
GET    /api/files/<file_id>
```

### Admin

```http
GET    /api/admin/requests
GET    /api/admin/requests/<id>
POST   /api/admin/requests/<id>/review
POST   /api/admin/requests/<id>/approve
POST   /api/admin/requests/<id>/reject
POST   /api/admin/requests/<id>/return
POST   /api/admin/requests/<id>/send-to-production
GET    /api/admin/users
POST   /api/admin/users
PUT    /api/admin/users/<id>
POST   /api/admin/users/<id>/toggle
GET    /api/admin/book-types
POST   /api/admin/book-types
PUT    /api/admin/book-types/<id>
POST   /api/admin/book-types/<id>/toggle
GET    /api/admin/audit-logs
```

### Editor

```http
GET    /api/editor/requests
GET    /api/editor/requests/<id>
POST   /api/editor/requests/<id>/review
POST   /api/editor/requests/<id>/return
POST   /api/editor/requests/<id>/approve
```

### Production

```http
GET    /api/production/orders
GET    /api/production/orders/<id>
POST   /api/production/orders/<id>/start
POST   /api/production/orders/<id>/quality-check
POST   /api/production/orders/<id>/complete
POST   /api/production/orders/<id>/reject-qc
```

### Notification & lain-lain

```http
GET    /api/notifications
POST   /api/notifications/<id>/read
POST   /api/notifications/read-all
GET    /api/history
GET    /api/stats
GET    /api/book-types
```

### Public (tanpa login)

```http
GET    /                          halaman Home (public books + ebook showcase)
GET    /about
GET    /workflow
GET    /features
GET    /books/<request_id>/pdf    hanya jika request is_public
GET    /books/<request_id>/cover  hanya jika request is_public
```

HTTP status yang digunakan: `400`, `401`, `403`, `404`, `409`, `413`, `422`, `500`.

---

## Keamanan

- Password di-hash dengan Werkzeug (scrypt), tidak pernah disimpan plaintext
- Autentikasi berbasis session dengan cookie `HttpOnly` dan `SameSite=Lax`
- Otorisasi RBAC di backend pada seluruh endpoint
- CSRF token divalidasi pada setiap request non-GET
- SQL injection dicegah melalui query parameterisasi SQLAlchemy
- XSS dicegah lewat auto-escape Jinja2 dan escaping eksplisit di JavaScript
- Upload file divalidasi: ekstensi, MIME type, ukuran, `secure_filename`,
  serta proteksi path traversal
- Download file hanya dapat diakses pengguna yang berhak atas request terkait;
  file baru bisa diakses publik tanpa login setelah pemiliknya menandainya
  `is_public` dan statusnya sudah lolos review editor
- Kredensial tidak di-hardcode, seluruhnya dibaca dari `.env`

---

## Testing

```bash
python -m pytest
```

Test menggunakan database terpisah `book_management_2_test` yang dibuat ulang
dari `database.sql` setiap kali dijalankan, sehingga data pengembangan tidak
tersentuh.

Cakupan:

| Berkas | Isi |
|--------|-----|
| `tests/test_auth.py` | login valid/invalid, logout, hashing password |
| `tests/test_authorization.py` | user/editor/production tidak dapat mengakses endpoint admin, dan sebaliknya |
| `tests/test_workflow.py` | alur penuh request → completed, dua putaran revisi, penolakan transisi ilegal, kewajiban alasan pada reject/return, notifikasi antar role |
| `tests/test_files.py` | upload valid, ekstensi ditolak, MIME tidak cocok, file kosong, path traversal, hak akses download |
| `tests/test_pages.py` | seluruh halaman setiap role ter-render |
