# Book 2 Management

Aplikasi web full-stack untuk mengelola **pengajuan, approval, pemeriksaan editor,
revisi, dan produksi buku**.

Dibangun dengan Flask + Jinja2 + HTML/CSS/Vanilla JavaScript di atas PostgreSQL.
Tidak menggunakan framework frontend apa pun.

---

## Stack

| Lapisan | Teknologi |
|---------|-----------|
| Backend | Python, Flask, Flask Blueprint, Flask REST API |
| ORM | SQLAlchemy, Flask-SQLAlchemy |
| Database | PostgreSQL (psycopg2-binary) |
| Frontend | Jinja2, HTML5, CSS3, Vanilla JavaScript |
| Keamanan | Werkzeug password hashing, session auth, CSRF token |
| Konfigurasi | python-dotenv |

---

## Alur Aplikasi

```
USER REQUEST → ADMIN REVIEW → ADMIN APPROVAL → EDITOR REVIEW
                                                    ↓
                                            ada kesalahan?
                                                    ↓ ya
                                     RETURN TO USER → USER REVISION
                                                    ↓
                                             EDITOR REVIEW
                                                    ↓ tidak
                                   READY FOR PRODUCTION → PRODUCTION
                                                    ↓
                                      QUALITY CHECK → COMPLETED
```

Status yang digunakan:

```
DRAFT · SUBMITTED · ADMIN_REVIEW · ADMIN_APPROVED · EDITOR_REVIEW
REVISION_REQUIRED · USER_REVISION · EDITOR_APPROVED · READY_FOR_PRODUCTION
PRODUCTION · QUALITY_CHECK · COMPLETED · REJECTED · CANCELLED
```

Seluruh perpindahan status divalidasi backend pada
[app/workflow.py](app/workflow.py). Tahapan tidak dapat dilompati dan setiap
transisi hanya boleh dilakukan role yang berwenang.

---

## Setup

### 1. Buat database

```sql
CREATE DATABASE book_management_2;
```

### 2. Import schema

```bash
psql -U postgres -d book_management_2 -f database.sql
```

File `database.sql` berisi seluruh `CREATE TABLE`, primary key, foreign key,
index, unique constraint, check constraint, default value, timestamp, serta seed
data untuk roles, book types, dan development users.

### 3. Konfigurasi `.env`

```env
SECRET_KEY=dev-secret-key-change-in-production-8f3a9c2e1b
DATABASE_URL=postgresql+psycopg2://postgres:root@127.0.0.1:5432/book_management_2
UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH=52428800
FLASK_ENV=development
```

Salin dari `.env.example`. File `.env` tidak diikutkan ke Git.

### 4. Install dependency

```bash
pip install -r requirements.txt
```

### 5. Jalankan

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
| admin@example.com | admin | ADMIN | password123 |
| editor@example.com | editor | EDITOR | password123 |
| production@example.com | production | PRODUCTION | password123 |
| user@example.com | user | USER | password123 |

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
│   ├── models.py            14 model SQLAlchemy
│   ├── workflow.py          state machine (satu sumber kebenaran transisi)
│   ├── security.py          session auth, RBAC, CSRF, validasi upload
│   ├── services.py          service layer: transisi, notifikasi, audit, query
│   ├── blueprints/
│   │   ├── public.py        home, tentang, alur, fitur
│   │   ├── auth.py          halaman login/logout
│   │   ├── dashboard.py     seluruh halaman setelah login
│   │   ├── api_auth.py      /api/auth
│   │   ├── api_requests.py  /api/requests (+ member, text, file)
│   │   ├── api_admin.py     /api/admin
│   │   ├── api_editor.py    /api/editor
│   │   ├── api_production.py /api/production
│   │   └── api_misc.py      notifikasi, history, statistik
│   ├── templates/           Jinja2 (base, komponen, publik, dashboard)
│   └── static/              style.css, app.js, list.js
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
Browser → Jinja2 / Vanilla JS → Flask Routes → Flask REST API
        → Service Layer → SQLAlchemy → PostgreSQL
```

---

## Peran dan Hak Akses

| Role | Kewenangan |
|------|-----------|
| **USER** | Membuat request, mengelola anggota/text/file, submit, mengirim revisi, membatalkan draft |
| **ADMIN** | Review, approve, reject, return, kirim ke produksi, kelola user dan jenis buku, lihat audit log |
| **EDITOR** | Mengisi checklist pemeriksaan, mengembalikan request untuk revisi, menyetujui hingga siap produksi |
| **PRODUCTION** | Memulai produksi, quality check, menyelesaikan order, mengunggah file final |

RBAC diterapkan di backend melalui dekorator `@role_required` pada setiap route
API maupun halaman. Menyembunyikan menu di frontend tidak dijadikan satu-satunya
pengaman: memanipulasi URL tetap menghasilkan `403`.

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

HTTP status yang digunakan: `400`, `401`, `403`, `404`, `409`, `413`, `422`, `500`.

---

## Database

14 tabel dengan foreign key dan index:

```
roles · users · book_types · book_requests · book_members · book_files
book_texts · request_status_history · request_revisions · editor_checklists
notifications · production_orders · production_history · audit_logs
```

Catatan penting:

- **Revisi tidak menimpa data lama.** Setiap putaran revisi menjadi satu baris
  `request_revisions` tersendiri, lengkap dengan catatan editor dan tanggapan user.
- **History tidak dapat dihapus user.** Setiap perpindahan status tercatat pada
  `request_status_history`.
- **File fisik disimpan di `uploads/`**, database hanya menyimpan metadata
  (`original_filename`, `stored_filename`, `mime_type`, `file_size`, `file_path`).
- **Statistik dashboard dihitung langsung dari database**, bukan angka statis.

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
- Download file hanya dapat diakses pengguna yang berhak atas request terkait
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
