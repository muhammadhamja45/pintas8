# MASTER PROMPT — BOOK 2 MANAGEMENT

Buat sebuah aplikasi web full-stack bernama:

# BOOK 2 MANAGEMENT

Aplikasi ini adalah sistem manajemen **pengajuan, approval, pemeriksaan editor, revisi, dan produksi buku**.

Aplikasi harus dibuat modern, profesional, clean, responsive, maintainable, dan benar-benar functional.

**Jangan membuat mockup, prototype palsu, atau AI slop.**

Semua fitur harus benar-benar terhubung dengan database PostgreSQL dan memiliki workflow yang jelas.

---

# 1. TECHNOLOGY STACK

Gunakan stack berikut dan jangan menambahkan framework yang tidak diperlukan.

## Backend

Gunakan:

* Python
* Flask
* Flask Blueprint
* Flask REST API
* SQLAlchemy
* PostgreSQL
* psycopg2-binary
* Werkzeug
* python-dotenv

## Frontend

Frontend tetap menggunakan Flask.

Gunakan:

* Flask
* Jinja2
* HTML5
* CSS3
* Vanilla JavaScript

**JANGAN menggunakan:**

* React
* Vue
* Angular
* Next.js
* Nuxt
* Svelte
* Node.js sebagai framework frontend
* Bootstrap
* Tailwind CSS
* frontend framework lainnya

Konsep frontend:

```text
Jinja2
+
HTML
+
CSS
+
Vanilla JavaScript
+
Flask API
```

Frontend harus berkomunikasi dengan backend melalui Flask API untuk operasi data.

---

# 2. DATABASE LOCAL

Gunakan PostgreSQL lokal saya.

Database:

```text
book_management
```

Username:

```text
postgres
```

Password:

```text
root
```

Host:

```text
127.0.0.1
```

Port:

```text
5432
```

Gunakan konfigurasi berikut:

```env
SECRET_KEY=dev-secret-key-change-in-production-8f3a9c2e1b

DATABASE_URL=postgresql+psycopg2://postgres:root@127.0.0.1:5432/book_management

UPLOAD_FOLDER=uploads

MAX_CONTENT_LENGTH=52428800

FLASK_ENV=development
```

Buat file:

```text
.env.example
```

dengan konfigurasi tersebut.

Buat juga `.env` untuk development jika environment project memang mengizinkannya, tetapi jangan memasukkan `.env` ke Git.

Tambahkan `.env` ke `.gitignore`.

---

# 3. DATABASE MIGRATION

Database harus memiliki file:

```text
database.sql
```

File ini harus dapat digunakan untuk membuat database schema pada PostgreSQL lain.

Contoh:

```bash
psql -U postgres -d book_management -f database.sql
```

`database.sql` harus berisi:

* CREATE TABLE
* PRIMARY KEY
* FOREIGN KEY
* INDEX
* UNIQUE constraint
* CHECK constraint
* DEFAULT value
* timestamp
* seed roles
* seed book types
* seed development users

Jangan membuat database hanya menggunakan Python.

Database SQL harus berdiri sendiri.

---

# 4. NAMA APLIKASI

Gunakan nama:

```text
BOOK 2 MANAGEMENT
```

Gunakan nama tersebut secara konsisten pada:

* browser title
* navbar
* sidebar
* login page
* dashboard
* README
* metadata
* logo/text branding

Contoh:

```text
Book 2 Management
```

---

# 5. KONSEP UTAMA APLIKASI

Aplikasi mengelola lifecycle buku:

```text
USER REQUEST
      ↓
ADMIN REVIEW
      ↓
ADMIN APPROVAL
      ↓
EDITOR REVIEW
      ↓
┌──────────────────────┐
│ Ada kesalahan?       │
└──────────┬───────────┘
           │
          YES
           ↓
   RETURN TO USER
           ↓
    USER REVISION
           ↓
    EDITOR REVIEW
           ↓
        APPROVED
           ↓
 READY FOR PRODUCTION
           ↓
      PRODUCTION
           ↓
     QUALITY CHECK
           ↓
       COMPLETED
```

---

# 6. ROLE

Aplikasi memiliki 4 role:

```text
USER
ADMIN
EDITOR
PRODUCTION
```

Gunakan Role-Based Access Control atau RBAC.

Setiap role mempunyai permission berbeda.

Backend/API wajib melakukan authorization.

Jangan hanya menyembunyikan menu dari frontend.

User tidak boleh mengakses endpoint Admin dengan memanipulasi URL.

Editor tidak boleh menjalankan fungsi Admin.

Production tidak boleh mengubah request User.

---

# 7. PUBLIC HOME PAGE

Saat membuka:

```text
http://localhost:5000/
```

user harus melihat **Public Home / Landing Page**.

Jangan langsung diarahkan ke dashboard.

Home tidak membutuhkan login.

Struktur:

```text
HOME
 ↓
LOGIN
 ↓
DASHBOARD BERDASARKAN ROLE
```

---

# 8. PUBLIC NAVBAR

Home memiliki navbar modern:

```text
┌──────────────────────────────────────────────────────────────┐
│ 📘 BOOK 2 MANAGEMENT     Home   Tentang   Alur   Fitur Login│
└──────────────────────────────────────────────────────────────┘
```

Navbar:

* modern
* clean
* professional
* responsive
* sticky jika sesuai
* mobile friendly

Menu:

```text
Home
Tentang
Alur Proses
Fitur
Login
```

Button:

```text
Login
```

Jika user sudah login, ubah menjadi:

```text
Dashboard
Logout
```

Pada mobile gunakan hamburger menu dengan Vanilla JavaScript.

---

# 9. PUBLIC HOME HERO

Hero:

```text
BOOK 2 MANAGEMENT

Kelola Pengajuan dan Produksi Buku
dalam Satu Sistem Terintegrasi.

Mulai dari request, approval, pemeriksaan editor,
revisi, hingga proses produksi buku.
```

CTA:

```text
Ajukan Buku
Lihat Alur
```

Jika user belum login dan klik:

```text
Ajukan Buku
```

redirect ke:

```text
/login
```

---

# 10. HOME PROCESS

Tampilkan workflow:

```text
01 Request
↓
02 Admin Approval
↓
03 Editor Review
↓
04 Revision
↓
05 Production
↓
06 Completed
```

Setiap tahap memiliki deskripsi singkat.

---

# 11. HOME FEATURES

Tampilkan:

```text
Book Request
Approval Workflow
Editor Review
Revision Management
File Management
Notification
Audit History
Production Tracking
```

---

# 12. DESIGN SYSTEM

Base color aplikasi:

# BLUE

Gunakan warna utama biru.

Design direction:

* professional
* corporate
* clean
* modern
* minimal
* elegant
* responsive

Warna dasar:

```text
Primary       → Blue
Dark          → Deep Blue
Background    → White / Light Gray
Text          → Dark Gray
Border        → Light Gray
Success       → Green
Warning       → Amber
Danger        → Red
```

Jangan menggunakan gradient berlebihan.

Jangan menggunakan:

* glassmorphism berlebihan
* animasi berlebihan
* rounded card berlebihan
* shadow berlebihan
* warna-warni tidak perlu
* UI yang terlihat seperti template AI

---

# 13. LOGIN

URL:

```text
/login
```

Form:

```text
Username / Email
Password
Remember Me
Login
```

Tambahkan:

* show/hide password
* validation
* error handling
* loading state
* logout

Password harus menggunakan hashing.

Gunakan Werkzeug password hashing.

Jangan pernah menyimpan password plaintext.

Setelah login redirect berdasarkan role:

```text
USER
→ /user/dashboard

ADMIN
→ /admin/dashboard

EDITOR
→ /editor/dashboard

PRODUCTION
→ /production/dashboard
```

---

# 14. DASHBOARD LAYOUT

Semua halaman setelah login menggunakan layout:

```text
┌──────────────────────────────────────────────────────────────┐
│ TOP NAVBAR                                                   │
├───────────────────┬──────────────────────────────────────────┤
│                   │                                          │
│ SIDEBAR           │             MAIN CONTENT                 │
│                   │                                          │
│ Dashboard         │                                          │
│ Requests          │                                          │
│ Notifications     │                                          │
│ History           │                                          │
│ Profile           │                                          │
│                   │                                          │
│ Logout            │                                          │
│                   │                                          │
└───────────────────┴──────────────────────────────────────────┘
```

Gunakan layout yang konsisten untuk semua role.

---

# 15. MODERN SIDEBAR

Sidebar harus:

* modern
* profesional
* clean
* dark blue / deep blue
* responsive
* sticky
* collapsible
* icon + text
* active state
* hover state

Contoh:

```text
┌─────────────────────────┐
│ 📘 BOOK 2 MANAGEMENT    │
├─────────────────────────┤
│                         │
│ ▣ Dashboard             │
│                         │
│ 📚 Request Buku         │
│                         │
│ 🔔 Notifikasi       3   │
│                         │
│ 🕘 History              │
│                         │
│ 👤 Profile              │
│                         │
├─────────────────────────┤
│ ⚙ Settings              │
│ 🚪 Logout               │
└─────────────────────────┘
```

Sidebar dapat di-collapse pada desktop.

Pada mobile menjadi drawer.

Gunakan Vanilla JavaScript.

---

# 16. TOP NAVBAR DASHBOARD

Top navbar:

```text
┌──────────────────────────────────────────────────────────────┐
│ ☰   Dashboard                         🔔 3   👤 User ▼      │
└──────────────────────────────────────────────────────────────┘
```

Berisi:

* hamburger
* breadcrumb/page title
* notification
* unread count
* profile dropdown

Profile dropdown:

```text
My Profile
Account
Logout
```

---

# 17. USER SIDEBAR

User:

```text
Dashboard

Request Buku
Request Saya
Revision

Notifications

History

Profile
Logout
```

---

# 18. ADMIN SIDEBAR

Admin:

```text
Dashboard

Incoming Requests
Approval
Editor Queue
Production Queue

All Books

Users
Book Types

History
Audit Log

Notifications

Profile
Logout
```

---

# 19. EDITOR SIDEBAR

Editor:

```text
Dashboard

Review Queue
In Review
Revision
Ready for Production

History

Notifications

Profile
Logout
```

---

# 20. PRODUCTION SIDEBAR

Production:

```text
Dashboard

Production Queue
In Production
Quality Check
Completed

History

Notifications

Profile
Logout
```

---

# 21. USER DASHBOARD

User dashboard menampilkan:

```text
Total Request
Pending
Revision
In Progress
Completed
```

Tambahkan:

* recent requests
* status
* notifications
* activity timeline

Semua angka harus berasal dari PostgreSQL.

Jangan menggunakan angka fake/hardcoded.

---

# 22. USER CREATE BOOK REQUEST

User dapat membuat request buku.

Form:

```text
Judul Buku
Jenis Buku
Nama Anggota
Jumlah Anggota
Deskripsi
Deadline
Catatan Tambahan
```

Book type:

```text
Jurnal
History
Majalah
Buku Laporan
Buku Dokumentasi
Buku Referensi
Lainnya
```

Book type dapat dikelola Admin.

---

# 23. MEMBER MANAGEMENT

User dapat menambahkan beberapa anggota.

Contoh:

```text
Anggota #1
Nama
Foto

Anggota #2
Nama
Foto

+ Tambah Anggota
```

User dapat:

* add member
* edit member
* delete member sebelum request final submitted

Setelah request masuk proses approval, perubahan harus mengikuti workflow.

---

# 24. BOOK MATERIAL

User dapat memasukkan:

### Foto

```text
Cover
Foto Anggota
Foto Dokumentasi
Foto Pendukung
```

### Text

```text
Kata Pengantar
Deskripsi
Biodata
Isi Buku
Catatan Layout
Instruksi Percetakan
```

---

# 25. FILE UPLOAD

File disimpan di:

```text
uploads/
```

Database hanya menyimpan metadata.

Metadata:

```text
id
request_id
uploaded_by
original_filename
stored_filename
mime_type
file_size
file_path
created_at
```

Maksimal upload:

```text
52428800 bytes
```

sesuai:

```env
MAX_CONTENT_LENGTH=52428800
```

Validasi:

* extension
* MIME type
* size
* secure filename
* path traversal protection

---

# 26. REQUEST DETAIL

Halaman detail:

```text
/requests/<id>
```

Tampilkan:

```text
Request Information
Book Information
Members
Files
Text
Printing Requirements
Notes
Current Status
Current Assignee
Timeline
Revision History
```

---

# 27. STATUS

Gunakan status:

```text
DRAFT
SUBMITTED
ADMIN_REVIEW
ADMIN_APPROVED
EDITOR_REVIEW
REVISION_REQUIRED
USER_REVISION
EDITOR_APPROVED
READY_FOR_PRODUCTION
PRODUCTION
QUALITY_CHECK
COMPLETED
REJECTED
CANCELLED
```

Status harus berasal dari backend/database.

---

# 28. STATE MACHINE

Workflow normal:

```text
DRAFT
 ↓
SUBMITTED
 ↓
ADMIN_REVIEW
 ↓
ADMIN_APPROVED
 ↓
EDITOR_REVIEW
 ↓
EDITOR_APPROVED
 ↓
READY_FOR_PRODUCTION
 ↓
PRODUCTION
 ↓
QUALITY_CHECK
 ↓
COMPLETED
```

Workflow revisi:

```text
EDITOR_REVIEW
 ↓
REVISION_REQUIRED
 ↓
USER_REVISION
 ↓
EDITOR_REVIEW
```

Workflow tidak boleh dilompati.

Contoh:

User tidak boleh:

```text
SUBMITTED → COMPLETED
```

Editor tidak boleh:

```text
EDITOR_REVIEW → COMPLETED
```

Production tidak boleh:

```text
EDITOR_REVIEW → PRODUCTION
```

Semua transition harus divalidasi backend.

---

# 29. ADMIN APPROVAL

Admin mendapatkan notification ketika User submit request.

Admin dapat:

```text
Approve
Reject
Return
```

Untuk Reject dan Return:

**Note wajib diisi.**

Approve:

```text
ADMIN_REVIEW
↓
ADMIN_APPROVED
↓
EDITOR_REVIEW
```

Editor mendapatkan notification.

---

# 30. EDITOR REVIEW

Editor memeriksa:

```text
Judul
Jenis Buku
Anggota
Foto
Text
Attachment
Layout
Printing Requirement
```

Editor memiliki checklist:

```text
[ ] Cover sudah benar
[ ] Foto lengkap
[ ] Resolusi foto cukup
[ ] Nama anggota benar
[ ] Text lengkap
[ ] Layout sesuai
[ ] Ukuran buku ditentukan
[ ] Jenis kertas ditentukan
[ ] Jumlah cetak ditentukan
[ ] Finishing ditentukan
```

Checklist disimpan di database.

---

# 31. EDITOR RETURN TO USER

Jika ada kesalahan:

```text
RETURN TO USER
```

Editor wajib memberikan note.

Contoh:

```text
Foto anggota nomor 4 belum tersedia.
Mohon upload foto dengan resolusi yang lebih baik.
```

Status:

```text
REVISION_REQUIRED
```

User mendapatkan notification.

---

# 32. REVISION MANAGEMENT

User dapat memperbaiki:

```text
Data
Text
Foto
File
Printing Requirement
```

Setiap revision harus disimpan.

Jangan overwrite history lama.

Contoh:

```text
Revision #1

Editor:
Foto anggota nomor 4 kurang jelas.

User:
Upload foto baru.

Revision #2

Editor:
Text halaman 5 perlu diperbaiki.

User:
Text diperbaiki.
```

---

# 33. HISTORY / TIMELINE

Setiap perubahan request dicatat.

Contoh:

```text
15 Sep 2026 09:10
User membuat request
SUBMITTED

15 Sep 2026 09:30
Admin melakukan approval
ADMIN_APPROVED

15 Sep 2026 10:00
Editor mulai review
EDITOR_REVIEW

15 Sep 2026 11:00
Editor meminta revisi
REVISION_REQUIRED

Note:
Foto anggota nomor 3 belum tersedia.
```

History tidak boleh dihapus User.

Admin dapat melihat seluruh history.

---

# 34. EDITOR FINAL APPROVAL

Jika semua data benar:

Editor klik:

```text
APPROVE & READY FOR PRODUCTION
```

Status:

```text
EDITOR_APPROVED
↓
READY_FOR_PRODUCTION
```

Admin menerima notification.

---

# 35. ADMIN PRODUCTION QUEUE

Admin melihat:

```text
READY_FOR_PRODUCTION
```

Admin dapat melihat:

```text
Book Detail
User
Members
Files
Text
Editor Checklist
Revision History
Notes
```

Admin kemudian mengirimkan request ke Production.

Status:

```text
READY_FOR_PRODUCTION
↓
PRODUCTION
```

Production menerima notification.

---

# 36. PRODUCTION DASHBOARD

Production dashboard:

```text
Waiting
In Production
Quality Check
Completed
```

Production dapat melihat:

```text
Judul
Jenis Buku
User
Jumlah Cetak
Ukuran
Jenis Kertas
Finishing
File Final
Catatan
```

---

# 37. PRODUCTION WORKFLOW

```text
READY_FOR_PRODUCTION
↓
PRODUCTION
↓
QUALITY_CHECK
↓
COMPLETED
```

Production action:

```text
Start Production
Quality Check
Complete
```

Setiap action dicatat.

---

# 38. NOTIFICATION SYSTEM

Implementasikan notification internal.

Table:

```text
notifications
```

Field:

```text
id
user_id
request_id
title
message
type
is_read
created_at
```

Notification:

### User

```text
Request Anda telah disetujui Admin.
```

### Editor

```text
Request baru menunggu pemeriksaan.
```

### User

```text
Request dikembalikan Editor untuk revisi.
```

### Admin

```text
Editor telah menyelesaikan pemeriksaan.
Request siap diproduksi.
```

### Production

```text
Buku baru masuk ke production queue.
```

Navbar:

```text
🔔 3
```

Klik notification membuka dropdown.

---

# 39. SEARCH & FILTER

Admin, Editor, Production memiliki:

```text
Search
Filter
Sort
Pagination
```

Search berdasarkan:

```text
Request ID
Judul Buku
Nama User
```

Filter:

```text
Status
Jenis Buku
Tanggal
User
```

Pagination harus dilakukan server-side jika data besar.

---

# 40. ADMIN USER MANAGEMENT

Admin dapat:

```text
View Users
Create User
Edit User
Deactivate User
Assign Role
```

Role:

```text
USER
ADMIN
EDITOR
PRODUCTION
```

User biasa tidak dapat mengubah role sendiri.

---

# 41. BOOK TYPE MANAGEMENT

Admin dapat:

```text
Create
Edit
Activate
Deactivate
```

Book types:

```text
Jurnal
History
Majalah
Dokumentasi
Laporan
Referensi
```

---

# 42. AUDIT LOG

Catat aktivitas:

```text
LOGIN
LOGOUT
CREATE_REQUEST
UPDATE_REQUEST
UPLOAD_FILE
DELETE_FILE
SUBMIT_REQUEST
APPROVE_REQUEST
REJECT_REQUEST
RETURN_REQUEST
START_REVIEW
REQUEST_REVISION
SUBMIT_REVISION
EDITOR_APPROVE
START_PRODUCTION
QUALITY_CHECK
COMPLETE_PRODUCTION
```

Table:

```text
audit_logs
```

Field:

```text
id
user_id
request_id
action
old_status
new_status
description
ip_address
created_at
```

Admin dapat melihat Audit Log.

---

# 43. API

Gunakan Flask REST API.

## Authentication

```http
POST /api/auth/login
POST /api/auth/logout
GET /api/auth/me
```

## User Request

```http
GET /api/requests
POST /api/requests
GET /api/requests/<id>
PUT /api/requests/<id>
POST /api/requests/<id>/submit
POST /api/requests/<id>/revision
```

## Admin

```http
GET /api/admin/requests
GET /api/admin/requests/<id>
POST /api/admin/requests/<id>/approve
POST /api/admin/requests/<id>/reject
POST /api/admin/requests/<id>/return
```

## Editor

```http
GET /api/editor/requests
GET /api/editor/requests/<id>
POST /api/editor/requests/<id>/review
POST /api/editor/requests/<id>/return
POST /api/editor/requests/<id>/approve
```

## Production

```http
GET /api/production/orders
GET /api/production/orders/<id>
POST /api/production/orders/<id>/start
POST /api/production/orders/<id>/quality-check
POST /api/production/orders/<id>/complete
```

## Notification

```http
GET /api/notifications
POST /api/notifications/<id>/read
POST /api/notifications/read-all
```

---

# 44. API RESPONSE

Success:

```json
{
    "success": true,
    "message": "Request berhasil disetujui",
    "data": {}
}
```

Error:

```json
{
    "success": false,
    "message": "Anda tidak memiliki akses",
    "errors": []
}
```

Gunakan HTTP status code yang benar.

---

# 45. DATABASE TABLES

Minimal tabel:

```text
roles
users
book_types
book_requests
book_members
book_files
book_texts
request_status_history
request_revisions
editor_checklists
notifications
production_orders
production_history
audit_logs
```

Gunakan relationship PostgreSQL yang benar.

Gunakan foreign key.

Gunakan index untuk field yang sering dicari.

Tambahkan:

```text
created_at
updated_at
```

pada tabel yang relevan.

---

# 46. SECURITY

Implementasikan:

* password hashing
* authentication
* authorization
* RBAC
* CSRF protection
* SQL injection protection
* XSS protection
* input validation
* secure file upload
* MIME validation
* file size validation
* filename sanitization
* path traversal protection
* secure file download

Jangan hardcode credential di source code.

Gunakan:

```env
SECRET_KEY
DATABASE_URL
UPLOAD_FOLDER
MAX_CONTENT_LENGTH
FLASK_ENV
```

---

# 47. ERROR HANDLING

Handle:

```text
400 Bad Request
401 Unauthorized
403 Forbidden
404 Not Found
409 Conflict
413 File Too Large
422 Validation Error
500 Internal Server Error
```

API harus mengembalikan JSON.

Frontend menampilkan pesan yang mudah dipahami.

---

# 48. REUSABLE UI COMPONENTS

Buat komponen yang reusable:

```text
Sidebar
TopNavbar
Breadcrumb
StatCard
StatusBadge
DataTable
Pagination
Modal
ConfirmationModal
NotificationDropdown
Timeline
FileUploader
FilePreview
FormInput
Select
Textarea
Alert
Toast
EmptyState
LoadingState
```

Jangan menduplikasi kode HTML/CSS/JS yang sama pada setiap halaman.

Gunakan Jinja template inheritance.

Contoh:

```text
base.html
```

untuk layout utama.

---

# 49. RESPONSIVE

Harus berjalan dengan baik pada:

```text
Desktop
Laptop
Tablet
Mobile
```

Desktop:

```text
Sidebar
+
Top Navbar
+
Main Content
```

Mobile:

```text
Top Navbar
+
Hamburger
+
Sidebar Drawer
+
Main Content
```

Table harus responsive.

Jangan membuat halaman rusak pada layar kecil.

---

# 50. UI STATE

Setiap request API harus mempunyai:

### Loading

```text
Loading...
```

### Empty

```text
Belum ada data.
```

### Error

```text
Data gagal dimuat.
Coba lagi.
```

### Success

```text
Request berhasil disubmit.
```

---

# 51. CONFIRMATION

Action penting harus menggunakan confirmation:

```text
Approve
Reject
Return
Delete
Complete Production
```

Untuk Reject/Return:

```text
Alasan wajib diisi.
```

Contoh:

```text
Alasan:

[____________________________]

Cancel
Confirm
```

---

# 52. NO AI SLOP

Jangan membuat:

* fake statistics
* fake dashboard
* fake activity
* lorem ipsum
* fake request
* dummy button
* dummy API
* status palsu
* chart dekoratif tanpa data
* UI terlalu ramai
* gradient berlebihan
* animasi berlebihan
* kode duplikat
* dependency tidak diperlukan

Semua dashboard harus mengambil data asli dari PostgreSQL.

Semua tombol harus mempunyai fungsi nyata.

Semua approval harus benar-benar mengubah status di database.

Semua revision harus tersimpan.

Semua activity harus masuk history/audit log.

---

# 53. PROJECT FILES

Hasil akhir minimal:

```text
book-2-management/
│
├── app/
├── uploads/
├── tests/
│
├── database.sql
├── requirements.txt
├── .env
├── .env.example
├── .gitignore
├── README.md
└── run.py
```

---

# 54. REQUIREMENTS.TXT

Minimal dependency yang diperlukan:

```text
Flask
SQLAlchemy
Flask-SQLAlchemy
psycopg2-binary
python-dotenv
```

Tambahkan dependency hanya jika memang dibutuhkan.

Jangan menambahkan dependency frontend.

---

# 55. RUN APPLICATION

Setelah setup:

```bash
python run.py
```

Aplikasi berjalan pada:

```text
http://127.0.0.1:5000
```

Home:

```text
http://127.0.0.1:5000/
```

Login:

```text
http://127.0.0.1:5000/login
```

---

# 56. DATABASE SETUP

README harus menjelaskan:

### 1. Create database

```sql
CREATE DATABASE book_management;
```

### 2. Import database

```bash
psql -U postgres -d book_management -f database.sql
```

### 3. Configure `.env`

```env
SECRET_KEY=dev-secret-key-change-in-production-8f3a9c2e1b

DATABASE_URL=postgresql+psycopg2://postgres:root@127.0.0.1:5432/book_management

UPLOAD_FOLDER=uploads

MAX_CONTENT_LENGTH=52428800

FLASK_ENV=development
```

### 4. Install

```bash
pip install -r requirements.txt
```

### 5. Run

```bash
python run.py
```

---

# 57. DEVELOPMENT USERS

Sediakan seed user:

```text
admin@example.com
editor@example.com
production@example.com
user@example.com
```

Role:

```text
admin@example.com
→ ADMIN

editor@example.com
→ EDITOR

production@example.com
→ PRODUCTION

user@example.com
→ USER
```

Password development harus disimpan dalam database sebagai hash.

Jangan menyimpan plaintext password.

Dokumentasikan credential testing pada README khusus untuk local development.

---

# 58. TESTING

Buat test untuk:

## Authentication

```text
Valid Login
Invalid Login
Logout
```

## Authorization

```text
User cannot access Admin
User cannot access Editor
Editor cannot access Admin
Production cannot access Admin
```

## Workflow

Test:

```text
Create Request
↓
Submit
↓
Admin Approve
↓
Editor Review
↓
Editor Return
↓
User Revision
↓
Editor Review
↓
Editor Approve
↓
Ready Production
↓
Production
↓
Quality Check
↓
Completed
```

Pastikan illegal status transition ditolak.

---

# 59. FINAL WORKFLOW

Aplikasi final harus memiliki:

```text
PUBLIC
│
├── Home
├── About
├── Workflow
├── Features
└── Login
       │
       ├── USER
       │   ├── Dashboard
       │   ├── Create Book Request
       │   ├── My Requests
       │   ├── Revision
       │   ├── Notifications
       │   ├── History
       │   └── Profile
       │
       ├── ADMIN
       │   ├── Dashboard
       │   ├── Incoming Requests
       │   ├── Approval
       │   ├── Editor Queue
       │   ├── Production Queue
       │   ├── All Books
       │   ├── Users
       │   ├── Book Types
       │   ├── History
       │   ├── Audit Log
       │   └── Notifications
       │
       ├── EDITOR
       │   ├── Dashboard
       │   ├── Review Queue
       │   ├── Review Detail
       │   ├── Revision
       │   ├── Ready for Production
       │   ├── History
       │   └── Notifications
       │
       └── PRODUCTION
           ├── Dashboard
           ├── Production Queue
           ├── In Production
           ├── Quality Check
           ├── Completed
           ├── History
           └── Notifications
```

---

# 60. DEVELOPMENT PRIORITY

Implementasikan dengan urutan:

```text
1. PostgreSQL Database Schema
2. database.sql
3. SQLAlchemy Models
4. Flask Application Factory
5. Blueprint
6. Authentication
7. RBAC
8. Workflow / State Machine
9. User Book Request
10. File Upload
11. Admin Approval
12. Editor Review
13. Revision System
14. History
15. Notification
16. Production
17. API
18. Dashboard
19. Public Home
20. Navbar
21. Sidebar
22. Responsive UI
23. Security
24. Testing
25. README
```

Jangan membuat UI terlebih dahulu lalu baru memikirkan database.

Pastikan:

```text
Database
↓
Model
↓
Service
↓
API
↓
Frontend
```

sudah mempunyai hubungan yang jelas.

---

# 61. FINAL ARCHITECTURE

Gunakan architecture:

```text
Browser
   ↓
Jinja2 / Vanilla JS
   ↓
Flask Routes
   ↓
Flask REST API
   ↓
Service Layer
   ↓
SQLAlchemy
   ↓
PostgreSQL
```

File upload:

```text
Browser
   ↓
Flask API
   ↓
File Validation
   ↓
uploads/
   +
PostgreSQL metadata
```

Workflow:

```text
User
 ↓
Request
 ↓
State Machine
 ↓
Database
 ↓
Notification
 ↓
Next Role
```

---

# 62. FINAL REQUIREMENT

Hasil akhir harus menjadi aplikasi **BOOK 2 MANAGEMENT** yang benar-benar functional.

Gunakan hanya:

```text
Python
Flask
Jinja2
HTML
CSS
Vanilla JavaScript
SQLAlchemy
PostgreSQL
```

Tidak menggunakan frontend framework.

Gunakan PostgreSQL lokal:

```text
postgresql+psycopg2://postgres:root@127.0.0.1:5432/book_management
```

Gunakan:

```text
UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH=52428800
```

Sediakan:

```text
database.sql
requirements.txt
.env.example
.gitignore
README.md
run.py
```

Website harus mempunyai:

```text
PUBLIC HOME
↓
LOGIN
↓
ROLE BASED DASHBOARD
↓
USER REQUEST
↓
ADMIN APPROVAL
↓
EDITOR REVIEW
↓
REVISION
↓
EDITOR APPROVAL
↓
READY FOR PRODUCTION
↓
PRODUCTION
↓
QUALITY CHECK
↓
COMPLETED
```

**Jangan mengubah business workflow tersebut.**

Semua proses harus memiliki:

```text
Authentication
Authorization
Validation
Database persistence
Notification
History
Audit Log
```

UI harus modern, profesional, clean, responsive, dengan **blue sebagai warna utama**, modern **sidebar + top navbar**, tetapi tetap sederhana dan tidak berlebihan.

Aplikasi harus terasa seperti **aplikasi operasional internal perusahaan/instansi yang benar-benar digunakan**, bukan mockup, template, atau hasil generate AI yang tidak memiliki business logic.
