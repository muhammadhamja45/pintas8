-- ============================================================
-- BOOK 2 MANAGEMENT - PostgreSQL Schema
-- Usage: psql -U postgres -d book_management_2 -f database.sql
-- ============================================================

DROP TABLE IF EXISTS audit_logs CASCADE;
DROP TABLE IF EXISTS production_history CASCADE;
DROP TABLE IF EXISTS production_orders CASCADE;
DROP TABLE IF EXISTS notifications CASCADE;
DROP TABLE IF EXISTS editor_checklists CASCADE;
DROP TABLE IF EXISTS request_revisions CASCADE;
DROP TABLE IF EXISTS request_status_history CASCADE;
DROP TABLE IF EXISTS book_texts CASCADE;
DROP TABLE IF EXISTS book_files CASCADE;
DROP TABLE IF EXISTS book_members CASCADE;
DROP TABLE IF EXISTS book_requests CASCADE;
DROP TABLE IF EXISTS book_types CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS roles CASCADE;

-- ------------------------------------------------------------
-- roles
-- ------------------------------------------------------------
CREATE TABLE roles (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(20)  NOT NULL UNIQUE
                CHECK (name IN ('USER', 'ADMIN', 'EDITOR', 'PRODUCTION')),
    description VARCHAR(255),
    created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------
-- users
-- ------------------------------------------------------------
CREATE TABLE users (
    id            SERIAL PRIMARY KEY,
    username      VARCHAR(50)  NOT NULL UNIQUE,
    email         VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name     VARCHAR(120) NOT NULL,
    phone         VARCHAR(30),
    role_id       INTEGER      NOT NULL REFERENCES roles(id) ON DELETE RESTRICT,
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    last_login_at TIMESTAMP,
    created_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_role      ON users(role_id);
CREATE INDEX idx_users_email     ON users(email);
CREATE INDEX idx_users_username  ON users(username);
CREATE INDEX idx_users_is_active ON users(is_active);

-- ------------------------------------------------------------
-- book_types
-- ------------------------------------------------------------
CREATE TABLE book_types (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(80) NOT NULL UNIQUE,
    description VARCHAR(255),
    is_active   BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_book_types_is_active ON book_types(is_active);

-- ------------------------------------------------------------
-- book_requests
-- ------------------------------------------------------------
CREATE TABLE book_requests (
    id                SERIAL PRIMARY KEY,
    request_code      VARCHAR(30)  NOT NULL UNIQUE,
    title             VARCHAR(200) NOT NULL,
    book_type_id      INTEGER      NOT NULL REFERENCES book_types(id) ON DELETE RESTRICT,
    user_id           INTEGER      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    description       TEXT,
    member_count      INTEGER      NOT NULL DEFAULT 0 CHECK (member_count >= 0),
    deadline          DATE,
    extra_note        TEXT,
    -- printing requirement
    book_size         VARCHAR(50),
    paper_type        VARCHAR(50),
    print_quantity    INTEGER      CHECK (print_quantity IS NULL OR print_quantity > 0),
    finishing         VARCHAR(50),
    printing_note     TEXT,
    -- workflow
    status            VARCHAR(30)  NOT NULL DEFAULT 'DRAFT'
                      CHECK (status IN (
                          'DRAFT','SUBMITTED','ADMIN_REVIEW','ADMIN_APPROVED',
                          'EDITOR_REVIEW','REVISION_REQUIRED','USER_REVISION',
                          'EDITOR_APPROVED','READY_FOR_PRODUCTION','PRODUCTION',
                          'QUALITY_CHECK','COMPLETED','REJECTED','CANCELLED')),
    current_assignee_id INTEGER    REFERENCES users(id) ON DELETE SET NULL,
    revision_count    INTEGER      NOT NULL DEFAULT 0 CHECK (revision_count >= 0),
    is_public         BOOLEAN      NOT NULL DEFAULT FALSE,
    submitted_at      TIMESTAMP,
    completed_at      TIMESTAMP,
    created_at        TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_requests_user     ON book_requests(user_id);
CREATE INDEX idx_requests_status   ON book_requests(status);
CREATE INDEX idx_requests_type     ON book_requests(book_type_id);
CREATE INDEX idx_requests_created  ON book_requests(created_at);
CREATE INDEX idx_requests_code     ON book_requests(request_code);
CREATE INDEX idx_requests_assignee ON book_requests(current_assignee_id);

-- ------------------------------------------------------------
-- book_members
-- ------------------------------------------------------------
CREATE TABLE book_members (
    id           SERIAL PRIMARY KEY,
    request_id   INTEGER      NOT NULL REFERENCES book_requests(id) ON DELETE CASCADE,
    name         VARCHAR(120) NOT NULL,
    position     VARCHAR(120),
    note         TEXT,
    photo_file_id INTEGER,
    sort_order   INTEGER      NOT NULL DEFAULT 0,
    created_at   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_members_request ON book_members(request_id);

-- ------------------------------------------------------------
-- book_files
-- ------------------------------------------------------------
CREATE TABLE book_files (
    id                SERIAL PRIMARY KEY,
    request_id        INTEGER      NOT NULL REFERENCES book_requests(id) ON DELETE CASCADE,
    uploaded_by       INTEGER      NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    category          VARCHAR(30)  NOT NULL DEFAULT 'SUPPORT'
                      CHECK (category IN ('COVER','MEMBER_PHOTO','DOCUMENTATION','SUPPORT','ATTACHMENT','FINAL')),
    original_filename VARCHAR(255) NOT NULL,
    stored_filename   VARCHAR(255) NOT NULL UNIQUE,
    mime_type         VARCHAR(120) NOT NULL,
    file_size         BIGINT       NOT NULL CHECK (file_size > 0),
    file_path         VARCHAR(500) NOT NULL,
    revision_number   INTEGER      NOT NULL DEFAULT 0,
    created_at        TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_files_request  ON book_files(request_id);
CREATE INDEX idx_files_category ON book_files(category);

ALTER TABLE book_members
    ADD CONSTRAINT fk_members_photo
    FOREIGN KEY (photo_file_id) REFERENCES book_files(id) ON DELETE SET NULL;

-- ------------------------------------------------------------
-- book_texts
-- ------------------------------------------------------------
CREATE TABLE book_texts (
    id          SERIAL PRIMARY KEY,
    request_id  INTEGER     NOT NULL REFERENCES book_requests(id) ON DELETE CASCADE,
    section     VARCHAR(40) NOT NULL
                CHECK (section IN ('KATA_PENGANTAR','DESKRIPSI','BIODATA','ISI_BUKU','CATATAN_LAYOUT','INSTRUKSI_PERCETAKAN')),
    content     TEXT        NOT NULL DEFAULT '',
    created_at  TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_text_section UNIQUE (request_id, section)
);

CREATE INDEX idx_texts_request ON book_texts(request_id);

-- ------------------------------------------------------------
-- request_status_history
-- ------------------------------------------------------------
CREATE TABLE request_status_history (
    id          SERIAL PRIMARY KEY,
    request_id  INTEGER     NOT NULL REFERENCES book_requests(id) ON DELETE CASCADE,
    user_id     INTEGER     REFERENCES users(id) ON DELETE SET NULL,
    old_status  VARCHAR(30),
    new_status  VARCHAR(30) NOT NULL,
    note        TEXT,
    created_at  TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_history_request ON request_status_history(request_id);
CREATE INDEX idx_history_created ON request_status_history(created_at);

-- ------------------------------------------------------------
-- request_revisions
-- ------------------------------------------------------------
CREATE TABLE request_revisions (
    id               SERIAL PRIMARY KEY,
    request_id       INTEGER   NOT NULL REFERENCES book_requests(id) ON DELETE CASCADE,
    revision_number  INTEGER   NOT NULL CHECK (revision_number > 0),
    requested_by     INTEGER   REFERENCES users(id) ON DELETE SET NULL,
    editor_note      TEXT      NOT NULL,
    user_response    TEXT,
    resolved_by      INTEGER   REFERENCES users(id) ON DELETE SET NULL,
    resolved_at      TIMESTAMP,
    created_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_revision_number UNIQUE (request_id, revision_number)
);

CREATE INDEX idx_revisions_request ON request_revisions(request_id);

-- ------------------------------------------------------------
-- editor_checklists
-- ------------------------------------------------------------
CREATE TABLE editor_checklists (
    id                  SERIAL PRIMARY KEY,
    request_id          INTEGER   NOT NULL REFERENCES book_requests(id) ON DELETE CASCADE,
    editor_id           INTEGER   NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    cover_ok            BOOLEAN   NOT NULL DEFAULT FALSE,
    photos_complete     BOOLEAN   NOT NULL DEFAULT FALSE,
    photo_resolution_ok BOOLEAN   NOT NULL DEFAULT FALSE,
    member_names_ok     BOOLEAN   NOT NULL DEFAULT FALSE,
    text_complete       BOOLEAN   NOT NULL DEFAULT FALSE,
    layout_ok           BOOLEAN   NOT NULL DEFAULT FALSE,
    book_size_set       BOOLEAN   NOT NULL DEFAULT FALSE,
    paper_type_set      BOOLEAN   NOT NULL DEFAULT FALSE,
    print_quantity_set  BOOLEAN   NOT NULL DEFAULT FALSE,
    finishing_set       BOOLEAN   NOT NULL DEFAULT FALSE,
    note                TEXT,
    created_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_checklist_request UNIQUE (request_id)
);

CREATE INDEX idx_checklists_request ON editor_checklists(request_id);

-- ------------------------------------------------------------
-- notifications
-- ------------------------------------------------------------
CREATE TABLE notifications (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    request_id  INTEGER      REFERENCES book_requests(id) ON DELETE CASCADE,
    title       VARCHAR(160) NOT NULL,
    message     TEXT         NOT NULL,
    type        VARCHAR(20)  NOT NULL DEFAULT 'INFO'
                CHECK (type IN ('INFO','SUCCESS','WARNING','DANGER')),
    is_read     BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_notif_user    ON notifications(user_id);
CREATE INDEX idx_notif_unread  ON notifications(user_id, is_read);
CREATE INDEX idx_notif_created ON notifications(created_at);

-- ------------------------------------------------------------
-- production_orders
-- ------------------------------------------------------------
CREATE TABLE production_orders (
    id             SERIAL PRIMARY KEY,
    request_id     INTEGER     NOT NULL REFERENCES book_requests(id) ON DELETE CASCADE,
    order_code     VARCHAR(30) NOT NULL UNIQUE,
    assigned_to    INTEGER     REFERENCES users(id) ON DELETE SET NULL,
    status         VARCHAR(30) NOT NULL DEFAULT 'WAITING'
                   CHECK (status IN ('WAITING','IN_PRODUCTION','QUALITY_CHECK','COMPLETED')),
    note           TEXT,
    started_at     TIMESTAMP,
    qc_at          TIMESTAMP,
    completed_at   TIMESTAMP,
    created_at     TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_production_request UNIQUE (request_id)
);

CREATE INDEX idx_production_status ON production_orders(status);

-- ------------------------------------------------------------
-- production_history
-- ------------------------------------------------------------
CREATE TABLE production_history (
    id          SERIAL PRIMARY KEY,
    order_id    INTEGER     NOT NULL REFERENCES production_orders(id) ON DELETE CASCADE,
    user_id     INTEGER     REFERENCES users(id) ON DELETE SET NULL,
    action      VARCHAR(40) NOT NULL,
    old_status  VARCHAR(30),
    new_status  VARCHAR(30),
    note        TEXT,
    created_at  TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_prodhist_order ON production_history(order_id);

-- ------------------------------------------------------------
-- audit_logs
-- ------------------------------------------------------------
CREATE TABLE audit_logs (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER     REFERENCES users(id) ON DELETE SET NULL,
    request_id  INTEGER     REFERENCES book_requests(id) ON DELETE SET NULL,
    action      VARCHAR(40) NOT NULL,
    old_status  VARCHAR(30),
    new_status  VARCHAR(30),
    description TEXT,
    ip_address  VARCHAR(45),
    created_at  TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_user    ON audit_logs(user_id);
CREATE INDEX idx_audit_action  ON audit_logs(action);
CREATE INDEX idx_audit_created ON audit_logs(created_at);

-- ============================================================
-- SEED DATA
-- ============================================================

INSERT INTO roles (name, description) VALUES
    ('USER',       'Pengaju request buku'),
    ('ADMIN',      'Administrator sistem dan approval'),
    ('EDITOR',     'Pemeriksa materi buku'),
    ('PRODUCTION', 'Pelaksana produksi buku');

INSERT INTO book_types (name, description) VALUES
    ('Jurnal',           'Buku jurnal ilmiah atau kegiatan'),
    ('History',          'Buku sejarah organisasi atau kegiatan'),
    ('Majalah',          'Terbitan majalah berkala'),
    ('Dokumentasi',      'Buku dokumentasi kegiatan'),
    ('Laporan',          'Buku laporan kegiatan atau tahunan'),
    ('Referensi',        'Buku referensi atau panduan'),
    ('Lainnya',          'Jenis buku lain di luar kategori');

-- Development users. Password for all seed users: password123
INSERT INTO users (username, email, password_hash, full_name, role_id) VALUES
    ('admin', 'admin@example.com',
     'scrypt:32768:8:1$hPZRaifcoylSXUmi$62c726265172ae726bd2730d48251da62350a5a6b33258eea48649fb36cf12fbb25511b810d15569a8e35ef113dcf4bea2b9f5f8680b2408b0d1cf1d14491247',
     'Administrator', (SELECT id FROM roles WHERE name = 'ADMIN')),
    ('editor', 'editor@example.com',
     'scrypt:32768:8:1$fgLyvNpXZ8jCat7G$55f5c8bbe403250f5d56c2ebe0b9a431042ea39f0f94d0cfb17450abe51788db035cdda2b6054e185bf3abd95d74598d8883ecd37759497af7e82ec308beb93a',
     'Editor Buku', (SELECT id FROM roles WHERE name = 'EDITOR')),
    ('production', 'production@example.com',
     'scrypt:32768:8:1$YnoPZYCHn1t3oW0q$67add44db80d218515be24fc0af1f4a470176217c794a47dc44eb43f09a876586162026cbe8910e4ed826bd913a90f14f335147cbf6494ff0f5295a1977cde72',
     'Tim Produksi', (SELECT id FROM roles WHERE name = 'PRODUCTION')),
    ('user', 'user@example.com',
     'scrypt:32768:8:1$BYQUVHSU0OGngArW$d5059721fe5e0be5add9945dbdd7867201d82cfe007d58358460ccb59d76c308cd24d42f851622b38918bf317d65170ed66083054acf0f1e4dfd2a73b7796297',
     'Pengguna Demo', (SELECT id FROM roles WHERE name = 'USER'));

-- ============================================================
-- PUBLIC BOOK CATALOG (published books shown on the public home page)
-- ============================================================
CREATE TABLE ebook_showcase (
    id               SERIAL PRIMARY KEY,
    external_id      BIGINT,
    title            VARCHAR(255) NOT NULL,
    description      VARCHAR(500),
    cover_image_url  VARCHAR(500),
    source_url       VARCHAR(500),
    page_count       INTEGER,
    category         VARCHAR(100),
    published_at     TIMESTAMP,
    scraped_at       TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ebook_showcase_category      ON ebook_showcase(category);
CREATE INDEX idx_ebook_showcase_published_at  ON ebook_showcase(published_at DESC);

INSERT INTO ebook_showcase (id, external_id, title, description, cover_image_url, source_url, page_count, category, published_at, scraped_at) VALUES
(1,55651467,'Strategi Fiskal Nabi Yusuf | Pelajaran Abadi Untuk Negeri','Strategi Fiskal Nabi Yusuf | Pelajaran Abadi Untuk Negeri&lt;br&gt;&lt;br&gt;Penulis: H. Cucun Ahmad Syamsurijal','https://online.anyflip.com/fhwbw/tmvi/files/shot.jpg?3','http://online.anyflip.com/fhwbw/tmvi/',103,'BUKU PENERBITAN','2026-09-08T05:40:03'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(2,78526205,'Laporan Kinerja DPR RI - Tahun Sidang 2025-2026','Laporan Kinerja DPR RI - Tahun Sidang 2025-2026','https://online.anyflip.com/fhwbw/tjuv/files/shot.jpg?2','http://online.anyflip.com/fhwbw/tjuv/',389,'BUKU PENERBITAN','2026-08-27T00:36:33'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(3,29392248,'Cahaya dan Air Mata Danau Toba - Sebuah Catatan Lamhot Sinaga','Cahaya dan Air Mata Danau Toba - Sebuah Catatan Lamhot Sinaga - 2026','https://online.anyflip.com/fhwbw/sbxs/files/shot.jpg?1','http://online.anyflip.com/fhwbw/sbxs/',159,'BUKU PENERBITAN','2026-08-26T00:02:21'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(4,43603904,'Gedung MPR DPR RI - Sejarah dan Perkembangannya','Gedung MPR DPR RI - Sejarah dan Perkembangannya','https://online.anyflip.com/fhwbw/pgfj/files/shot.jpg?1','http://online.anyflip.com/fhwbw/pgfj/',143,'BUKU PENERBITAN','2026-07-24T12:54:09'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(5,67979248,'Laporan Kinerja 2025 - Inspektorat Utama Setjen DPR RI','Laporan Kinerja 2025 - Inspektorat Utama Setjen DPR RI','https://online.anyflip.com/fhwbw/csdk/files/shot.jpg?1','http://online.anyflip.com/fhwbw/csdk/',76,'BUKU PENERBITAN','2026-07-13T22:28:12'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(6,99592416,'Laporan Kinerja 2025 - Biro Kesekretariatan Pimpinan','Laporan Kinerja 2025 - Biro Kesekretariatan Pimpinan','https://online.anyflip.com/fhwbw/zgso/files/shot.jpg?1','http://online.anyflip.com/fhwbw/zgso/',78,'BUKU PENERBITAN','2026-07-13T22:21:35'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(7,99752414,'Pelayanan Publik - Membahas Konsep dan Cara Menerapkan Pelayanan Publik','Pelayanan Publik - Membahas Konsep dan Cara Menerapkan Pelayanan Publik','https://online.anyflip.com/fhwbw/reyo/files/shot.jpg?1','http://online.anyflip.com/fhwbw/reyo/',212,'BUKU PENERBITAN','2026-07-13T22:13:45'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(8,91980359,'Anotasi KUHAP 2025','Anotasi KUHAP 2025 - Sebuah Catatan Pembahasan dan Penjelasan Komprehensif Komisi III DPR RI','https://online.anyflip.com/fhwbw/ymop/files/shot.jpg?1','http://online.anyflip.com/fhwbw/ymop/',562,'BUKU PENERBITAN','2026-07-13T00:49:40'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(9,53218896,'KETAHANAN EPISTEMIK DI ERA DIGITAL MASYARAKAT KOKOH DI ZAMAN BISING','KETAHANAN EPISTEMIK DI ERA DIGITAL MASYARAKAT KOKOH DI ZAMAN BISING','https://online.anyflip.com/fhwbw/xxbp/files/shot.jpg?2','http://online.anyflip.com/fhwbw/xxbp/',196,'BUKU PENERBITAN','2026-07-03T02:11:45'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(10,30542725,'Mengalir Laksana Air, Berguna Bagi Sebanyak Mungkin Manusia','Mengalir Laksana Air, Berguna Bagi Sebanyak Mungkin Manusia - Mengabdi Lewat Kebijakan Anggaran - H. Syarief Abdullah Alkadrie','https://online.anyflip.com/fhwbw/zhhk/files/shot.jpg?2','http://online.anyflip.com/fhwbw/zhhk/',186,'BUKU PENERBITAN','2026-06-25T00:45:54'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(11,58559125,'Undang-Undang Republik Indonesia Nomor 1 Tahun 2026 Tentang Penyesuaian Pidana - Kinerja Komisi III DPR RI dalam Pembaruan Penyesuaian Pidana','Undang-Undang Republik Indonesia Nomor 1 Tahun 2026 Tentang Penyesuaian Pidana - Kinerja Komisi III DPR RI dalam Pembaruan Penyesuaian Pidana','https://online.anyflip.com/fhwbw/vlaa/files/shot.jpg?1','http://online.anyflip.com/fhwbw/vlaa/',272,'BUKU PENERBITAN','2026-05-19T23:20:53'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(12,99651263,'Undang-Undang Republik Indonesia Nomor 1 Tahun 2023 Tentang Kitab Undang-Undang Hukum Pidana - Kinerja Komisi III DPR RI dalam Pembaruan KUHP','Undang-Undang Republik Indonesia Nomor 1 Tahun 2023 Tentang Kitab Undang-Undang Hukum Pidana - Kinerja Komisi III DPR RI dalam Pembaruan KUHP','https://online.anyflip.com/fhwbw/ijwa/files/shot.jpg?1','http://online.anyflip.com/fhwbw/ijwa/',358,'BUKU PENERBITAN','2026-05-19T23:10:07'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(13,47093838,'Pemberdayaan UMKM Dalam Mendorong UMKM Naik Kelas dan Berdaya Saing','Pemberdayaan UMKM Dalam Mendorong UMKM Naik Kelas dan Berdaya Saing','https://online.anyflip.com/fhwbw/rixh/files/shot.jpg?2','http://online.anyflip.com/fhwbw/rixh/',182,'BUKU PENERBITAN','2026-05-04T03:03:31'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(14,48735585,'Pancasila Di Rumahku - Willy Aditya','Pancasila Di Rumahku - Willy Aditya','https://online.anyflip.com/fhwbw/wjei/files/shot.jpg?1','http://online.anyflip.com/fhwbw/wjei/',192,'BUKU PENERBITAN','2026-03-09T23:38:15'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(15,25414780,'Laporan Kinerja 2025 - Biro Pemberitaan Parlemen','Laporan Kinerja 2025 - Biro Pemberitaan Parlemen','https://online.anyflip.com/fhwbw/jvdx/files/shot.jpg?1','http://online.anyflip.com/fhwbw/jvdx/',124,'BUKU PENERBITAN','2026-04-06T05:23:30'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(16,73237142,'Sepak Terjang DPR Bela Kebijakan Pro Rakyat - Catatan Perjuangan Satgas Lawan Covid-19 Hingga Solusi Polemik Gas Melon','Sepak Terjang DPR Bela Kebijakan Pro Rakyat - Catatan Perjuangan Satgas Lawan Covid-19 Hingga Solusi Polemik Gas Melon','https://online.anyflip.com/fhwbw/ukxa/files/shot.jpg?2','http://online.anyflip.com/fhwbw/ukxa/',118,'BUKU PENERBITAN','2026-03-09T23:30:34'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(17,35020324,'Sejarah Diplomasi DPR RI 1998 - 2025 - Konsistensi Diplomasi Bela Kemerdekaan Palestina','Sejarah Diplomasi DPR RI 1998-2025 - Konsistensi Diplomasi Bela Kemerdekaan Palestina - Mardani Ali Sera (2025)','https://online.anyflip.com/fhwbw/bkyn/files/shot.jpg?2','http://online.anyflip.com/fhwbw/bkyn/',100,'BUKU PENERBITAN','2026-02-10T03:32:37'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(18,85447278,'Menjaga Bumi Tetap Lestari - Kisah Putri Dari Lampung','Menjaga Bumi Tetap Lestari - Kisah Putri Dari Lampung - Putri Zulhas (2025)','https://online.anyflip.com/fhwbw/uell/files/shot.jpg?2','http://online.anyflip.com/fhwbw/uell/',108,'BUKU PENERBITAN','2026-02-10T03:32:12'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(19,72496088,'Koperasi Merah Putih - Jalan Ideologi Menuju Koperasi Pilar Negara','Koperasi Merah Putih - Jalan Ideologi Menuju Koperasi Pilar Negara - Prof. Dr. Drs. H.A.M. Nurdin Halid (2025)','https://online.anyflip.com/fhwbw/sqns/files/shot.jpg?2','http://online.anyflip.com/fhwbw/sqns/',204,'BUKU PENERBITAN','2026-02-10T03:34:01'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(20,64050187,'Dakwah Politik Dan Amanah - Anggaran Untuk Kesejahteraan Bangsa','Dakwah Politik Dan Amanah - Anggaran Untuk Kesejahteraan Bangsa - Jejak Diplomasi Habib Idrus Salim Aljufri, Lc., M.B.A. (2025)','https://online.anyflip.com/fhwbw/sizw/files/shot.jpg?2','http://online.anyflip.com/fhwbw/sizw/',262,'BUKU PENERBITAN','2026-02-10T03:26:49'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(21,46998711,'Laporan Kinerja 2025 - Deputi Bidang Persidangan','Laporan Kinerja 2025 - Deputi Bidang Persidangan','https://online.anyflip.com/fhwbw/sguk/files/shot.jpg?1','http://online.anyflip.com/fhwbw/sguk/',164,'BUKU PENERBITAN','2026-03-09T23:37:10'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(22,97668542,'Laporan Kinerja Tahun 2021 - Biro Kesekretariatan Pimpinan','Laporan Kinerja Tahun 2021 - Biro Kesekretariatan Pimpinan (2021)','https://online.anyflip.com/fhwbw/ntlt/files/shot.jpg?1','http://online.anyflip.com/fhwbw/ntlt/',45,'BUKU PENERBITAN','2026-02-22T23:50:44'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(23,37332702,'Buku Saku Panduan Perilaku Sesuai Core Values BerAKHLAK Setjen DPR RI','Buku Saku Panduan Perilaku Sesuai Core Values BerAKHLAK Setjen DPR RI (2022)','https://online.anyflip.com/fhwbw/wqbz/files/shot.jpg?1','http://online.anyflip.com/fhwbw/wqbz/',28,'BUKU PENERBITAN','2026-02-22T23:46:03'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(24,43116103,'Pedoman Alih Media Arsip DPR RI','Pedoman Alih Media Arsip DPR RI (2025)','https://online.anyflip.com/fhwbw/vzdd/files/shot.jpg?1','http://online.anyflip.com/fhwbw/vzdd/',26,'BUKU PENERBITAN','2026-02-10T03:29:16'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(25,61626859,'Reformasi Organisasi dan Governansi - Strategi Transformasi Menuju Tata Kelola Pemerintahan yang Adaptif dan Akuntabel','Reformasi Organisasi dan Governansi - Strategi Transformasi Menuju Tata Kelola Pemerintahan yang Adaptif dan Akuntabel (2025)','https://online.anyflip.com/fhwbw/uuug/files/shot.jpg?1','http://online.anyflip.com/fhwbw/uuug/',216,'BUKU PENERBITAN','2026-02-10T03:27:26'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(26,51951999,'Laporan Kinerja DPR RI - Tahun Sidang 2024-2025','Laporan Kinerja DPR RI - Tahun Sidang 2024-2025','https://online.anyflip.com/fhwbw/ttvl/files/shot.jpg?1','http://online.anyflip.com/fhwbw/ttvl/',336,'BUKU PENERBITAN','2026-05-19T23:31:15'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(27,49286178,'Strengthening The Indonesian Parliamentary Diplomacy - Fadli Zon','Strengthening The Indonesian Parliamentary Diplomacy - Selected Speeches of Fadli Zon','https://online.anyflip.com/fhwbw/geee/files/shot.jpg?1','http://online.anyflip.com/fhwbw/geee/',370,'BUKU PENERBITAN','2026-02-24T02:25:06'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(28,96683025,'Pancawarsa Badan Keahlian DPR 2020-2025: Memperkuat Titian Dunia Akademik dan Politik','Pancawarsa Badan Keahlian DPR 2020-2025: Memperkuat Titian Dunia Akademik dan Politik (2025)','https://online.anyflip.com/fhwbw/hodn/files/shot.jpg?2','http://online.anyflip.com/fhwbw/hodn/',106,'BUKU PENERBITAN','2026-02-10T03:28:17'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(29,16441059,'Transformasi Penegakan Hukum dan HAM Di Indonesia - Komisi III DPR RI','Transformasi Penegakan Hukum dan HAM Di Indonesia - Komisi III DPR RI Periode Tahun 2019-2024 dalam Sebuah Catatan (2024)','https://online.anyflip.com/fhwbw/mtvk/files/shot.jpg?1','http://online.anyflip.com/fhwbw/mtvk/',354,'BUKU PENERBITAN','2026-02-22T23:42:56'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(30,16016316,'Kinerja Pimpinan Dewan Dilihat Dari Sisi Pemberitaan Media Massa','Kinerja Pimpinan Dewan Dilihat Dari Sisi Pemberitaan Media Massa (2024)','https://online.anyflip.com/fhwbw/muno/files/shot.jpg?1','http://online.anyflip.com/fhwbw/muno/',113,'BUKU PENERBITAN','2026-02-22T23:42:17'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(31,68323299,'KWP Award: Penghargaan Bagi Kerja Nyata Dewan','KWP Award: Penghargaan Bagi Kerja Nyata Dewan (2024)','https://online.anyflip.com/fhwbw/veei/files/shot.jpg?1','http://online.anyflip.com/fhwbw/veei/',122,'BUKU PENERBITAN','2026-02-22T23:51:43'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(32,48355655,'Forum Legislasi - Mengkaji Produk Legislasi Lewat Kacamata Wartawan Parlemen','Forum Legislasi - Mengkaji Produk Legislasi Lewat Kacamata Wartawan Parlemen (2024)','https://online.anyflip.com/fhwbw/yemx/files/shot.jpg?1','http://online.anyflip.com/fhwbw/yemx/',125,'BUKU PENERBITAN','2026-02-22T23:45:33'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(33,27126730,'Laporan Kinerja DPR RI - Tahun Sidang 2023-2024','Laporan Kinerja DPR RI - Tahun Sidang 2023-2024 (2024)','https://online.anyflip.com/fhwbw/bsid/files/shot.jpg?1','http://online.anyflip.com/fhwbw/bsid/',422,'BUKU PENERBITAN','2026-02-23T00:22:16'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(34,78250780,'Laporan Kinerja 2023 - Biro Pemberitaan Parlemen','Laporan Kinerja 2023 - Biro Pemberitaan Parlemen (2023)','https://online.anyflip.com/fhwbw/trmi/files/shot.jpg?1','http://online.anyflip.com/fhwbw/trmi/',88,'BUKU PENERBITAN','2026-02-22T23:44:00'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(35,23189665,'Program Arsip Vital DPR RI','Program Arsip Vital DPR RI (2023)','https://online.anyflip.com/fhwbw/ddyi/files/shot.jpg?1','http://online.anyflip.com/fhwbw/ddyi/',46,'BUKU PENERBITAN','2026-02-10T03:33:07'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(36,37737669,'Antologi Problematik Ranah Pembangunan Sistem Ekonomi dan Hukum Di Negara Republik Indonesia','Antologi Problematik Ranah Pembangunan Sistem Ekonomi dan Hukum Di Negara Republik Indonesia - DR. H. R. Achmad Dimyati Natakusumah, S.H., M.H., M.SI (2022)','https://online.anyflip.com/fhwbw/ywdx/files/shot.jpg?1','http://online.anyflip.com/fhwbw/ywdx/',176,'BUKU PENERBITAN','2026-02-22T23:56:32'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(37,33706586,'Rantau - Kisah Perjalanan Hidup Zulkifli Hasan Menaklukkan Jakarta','Rantau - Kisah Perjalanan Hidup Zulkifli Hasan Menaklukkan Jakarta (2022)','https://online.anyflip.com/fhwbw/vjpx/files/shot.jpg?1','http://online.anyflip.com/fhwbw/vjpx/',384,'BUKU PENERBITAN','2026-02-23T00:00:02'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(38,53545968,'Selayang Pandang Gedung DPR RI','Selayang Pandang Gedung DPR RI - Edisi IV (2022)','https://online.anyflip.com/fhwbw/dzab/files/shot.jpg?1','http://online.anyflip.com/fhwbw/dzab/',98,'BUKU PENERBITAN','2026-02-22T23:56:52'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(39,72854332,'Majalah Auditama Edisi 01 - Reviu Laporan Keuangan Sekretariat Jenderal DPR RI','Majalah Auditama Edisi 01 - Reviu Laporan Keuangan Sekretariat Jenderal DPR RI (2022)','https://online.anyflip.com/fhwbw/zxlk/files/shot.jpg?1','http://online.anyflip.com/fhwbw/zxlk/',40,'BUKU PENERBITAN','2026-02-22T23:50:04'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(40,85225661,'Perdebatan Pasal 33 Dalam Sidang Amandemen UUD 1945','Memuat Salinan Otentik Notulensi Sidang MPR RI 1999-2002 (2022)','https://online.anyflip.com/fhwbw/kqxy/files/shot.jpg?1','http://online.anyflip.com/fhwbw/kqxy/',464,'BUKU PENERBITAN','2026-02-22T23:55:48'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(41,44504136,'Info Judical Review Putusan Mahkamah Konstitusi Atas Pengujian Undang-Undang Terhadap Undang-Undang Dasar 1945','Info Judical Review Putusan Mahkamah Konstitusi Atas Pengujian Undang-Undang Terhadap Undang-Undang Dasar 1945 - Periode Januari - Maret 2022','https://online.anyflip.com/fhwbw/iwgh/files/shot.jpg?1','http://online.anyflip.com/fhwbw/iwgh/',152,'BUKU PENERBITAN','2026-02-22T23:47:02'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(42,76919566,'Laporan Kinerja DPR RI - Tahun Sidang 2021-2022','Laporan Kinerja DPR RI - Tahun Sidang 2021-2022 (2022)','https://online.anyflip.com/fhwbw/zkji/files/shot.jpg?1','http://online.anyflip.com/fhwbw/zkji/',270,'BUKU PENERBITAN','2026-02-23T00:01:39'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(43,87483225,'Laporan Kinerja 2022 - Biro Pemberitaan Parlemen','Laporan Kinerja 2022 - Biro Pemberitaan Parlemen (2022)','https://online.anyflip.com/fhwbw/hryj/files/shot.jpg?1','http://online.anyflip.com/fhwbw/hryj/',111,'BUKU PENERBITAN','2026-02-22T23:44:43'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(44,49359531,'Penyelenggaraan Kearsipan DPR RI','Penyelenggaraan Kearsipan DPR RI - Bagian Arsip Setjen DPR RI (2022)','https://online.anyflip.com/fhwbw/lqhi/files/shot.jpg?1','http://online.anyflip.com/fhwbw/lqhi/',94,'BUKU PENERBITAN','2026-02-22T23:56:11'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(45,14271480,'25 Modus Kecurangan dalam Pengadaan Barang dan Jasa','25 Modus Kecurangan dalam Pengadaan Barang dan Jasa (2022)','https://online.anyflip.com/fhwbw/yqsi/files/shot.jpg?1','http://online.anyflip.com/fhwbw/yqsi/',136,'BUKU PENERBITAN','2026-02-22T23:51:20'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(46,48926482,'Kepentingan Nasional dan Agenda Pembangunan - Menyerap Aspirasi Menciptakan Solusi (Edisi Ke-2)','Kiprah tahun ke-2 Wakil Ketua DPR RI/Korinbang Dr. (H.C.) Rachmat Gobel (2022)','https://online.anyflip.com/fhwbw/cvgr/files/shot.jpg?3','http://online.anyflip.com/fhwbw/cvgr/',439,'BUKU PENERBITAN','2026-02-23T00:00:26'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(47,95856807,'National Interest dan Agenda Pembangunan - Menyerap Aspirasi, Menciptakan Solusi - Dr. (H.C.) Rachmat Gobel','Kiprah Tahun Kedua Wakil Ketua DPR RI Bidang Industri dan Pembangunan Dr. (H.C.) Rachmat Gobel

Tahun 2021','https://online.anyflip.com/fhwbw/pjan/files/shot.jpg?2','http://online.anyflip.com/fhwbw/pjan/',478,'BUKU PENERBITAN','2026-02-24T01:57:07'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(48,82226883,'Menyerap Aspirasi Menciptakan Solusi (Revisi)','Satu tahun kiprah Wakil Ketua DPR RI/Korinbang DR. (H.C.) Rachmat Gobel (2021)','https://online.anyflip.com/fhwbw/rwrp/files/shot.jpg?1','http://online.anyflip.com/fhwbw/rwrp/',476,'BUKU PENERBITAN','2026-02-23T00:00:06'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(49,62588894,'Hope - Harmony & Humanity - M. Azis Syamsuddin','Merakit harapan dalam bingkai harmoni dan kemanusiaan

Tahun 2021','https://online.anyflip.com/fhwbw/mmbp/files/shot.jpg?1','http://online.anyflip.com/fhwbw/mmbp/',330,'BUKU PENERBITAN','2026-02-24T01:56:10'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(50,78914239,'Proses & Teknik Penyusunan Undang-Undang','Proses & Teknik Penyusunan Undang-Undang ( Edisi Ke-3)
Dr. H. M. Azis Syamsuddin, SE., S.H., M.A.F., M.H.

Tahun 2021','https://online.anyflip.com/fhwbw/vgjy/files/shot.jpg?1','http://online.anyflip.com/fhwbw/vgjy/',384,'BUKU PENERBITAN','2026-02-24T01:49:48'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(51,51927059,'Code Of Conduct Enforcement System Of The House Of Representatives Of The Republic Of Indonesia','Code Of Conduct Enforcement System Of The House Of Representatives Of The Republic Of Indonesia (2021)','https://online.anyflip.com/fhwbw/vpsu/files/shot.jpg?1','http://online.anyflip.com/fhwbw/vpsu/',56,'BUKU PENERBITAN','2026-02-22T23:54:58'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(52,54598152,'Seabad Rakyat Indonesia Berparlemen – Sejarah DPR RI','Seabad Rakyat Indonesia Berparlemen – Sejarah DPR RI

Tahun 2021','https://online.anyflip.com/fhwbw/fjkq/files/shot.jpg?1','http://online.anyflip.com/fhwbw/fjkq/',288,'BUKU PENERBITAN','2026-02-24T01:59:08'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(53,78150146,'A Century Of Parliamentary Life In Indonesia','A Century Of Parliamentary Life In Indonesia - History Of The House Of Representatives Of The Republic Of Indonesia (2021)','https://online.anyflip.com/fhwbw/fbje/files/shot.jpg?1','http://online.anyflip.com/fhwbw/fbje/',288,'BUKU PENERBITAN','2026-02-22T23:53:50'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(54,49010079,'A Century Of Parliamentary Life In Indonesia History Of The House Of Representatives Of The Republic Of Indonesia','A Century Of Parliamentary Life In Indonesia History Of The House Of Representatives Of The Republic Of Indonesia','https://online.anyflip.com/fhwbw/pawq/files/shot.jpg?1','http://online.anyflip.com/fhwbw/pawq/',288,'BUKU PENERBITAN','2026-06-23T08:00:50'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(55,51058925,'Tetap Kritis di Masa Krisis','Tetap Kritis di Masa Krisis - Fraksi Partai NasDem (2021)','https://online.anyflip.com/fhwbw/pptm/files/shot.jpg?1','http://online.anyflip.com/fhwbw/pptm/',263,'BUKU PENERBITAN','2026-02-22T23:50:41'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(56,42599934,'Berkarya Di Tengah Pandemi - Satu Tahun Kinerja M. Azis Syamsuddin','Berkarya Di Tengah Pandemi - Satu Tahun Kinerja M. Azis Syamsuddin - Wakil Ketua DPR RI Bidang KORPOLKAM (2020)','https://online.anyflip.com/fhwbw/ukfc/files/shot.jpg?1','http://online.anyflip.com/fhwbw/ukfc/',440,'BUKU PENERBITAN','2026-02-22T23:46:41'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(57,78657663,'Ekonomi Kerakyatan - Dalam Diskusi Dua Generasi','Ekonomi Kerakyatan - Dalam Diskusi Dua Generasi (2020)','https://online.anyflip.com/fhwbw/yvpa/files/shot.jpg?1','http://online.anyflip.com/fhwbw/yvpa/',154,'BUKU PENERBITAN','2026-02-22T23:53:35'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(58,87629037,'Kata Fadli - Catatan-Catatan Kritis dari Senayan','Kata Fadli - Catatan-Catatan Kritis dari Senayan

Tahun 2019','https://online.anyflip.com/fhwbw/smhm/files/shot.jpg?1','http://online.anyflip.com/fhwbw/smhm/',538,'BUKU PENERBITAN','2026-02-24T01:57:32'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(59,54067180,'Gelora Kata-Kata Seputar Demokrasi dan Musuh-Musuhnya - Fahri Hamzah','Kumpulan suara pedas Fahri Hamzah melalui twitter untuk reformasi hukum, demokrasi dan pemberantasan korupsi

Tahun 2019','https://online.anyflip.com/fhwbw/vmbk/files/shot.jpg?1','http://online.anyflip.com/fhwbw/vmbk/',628,'BUKU PENERBITAN','2026-02-24T01:59:13'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(60,52790275,'Daulat Rakyat - Fahri Hamzah','Daulat Rakyat - Fahri Hamzah (2019)','https://online.anyflip.com/fhwbw/wgzw/files/shot.jpg?1','http://online.anyflip.com/fhwbw/wgzw/',244,'BUKU PENERBITAN','2026-02-22T23:53:14'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(61,31112832,'Kendaraan Bermotor Listrik Nasional - Pokok-Pokok Pemikiran','Kendaraan Bermotor Listrik Nasional - Pokok-Pokok Pemikiran
Dr. Agus Hermanto

Tahun 2019','https://online.anyflip.com/fhwbw/kefa/files/shot.jpg?1','http://online.anyflip.com/fhwbw/kefa/',164,'BUKU PENERBITAN','2026-02-24T01:54:57'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(62,15557055,'Dari Senayan Untuk Indonesia - Kumpulan Dialektika Demokrasi & Forum Legislasi 2018-2019','Dari Senayan Untuk Indonesia - Kumpulan Dialektika Demokrasi & Forum Legislasi 2018-2019 (2019)','https://online.anyflip.com/fhwbw/puxg/files/shot.jpg?1','http://online.anyflip.com/fhwbw/puxg/',194,'BUKU PENERBITAN','2026-02-22T23:54:18'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(63,12924886,'Dinamika Dan Peranan DPR RI Dalam Memperbaiki Kehidupan Bernegara Pada Era Reformasi 1998-2018 (Buku Lima)','Dinamika Dan Peranan DPR RI Dalam Memperbaiki Kehidupan Bernegara Pada Era Reformasi 1998-2018 (Buku Lima) (2019)','https://online.anyflip.com/fhwbw/haht/files/shot.jpg?1','http://online.anyflip.com/fhwbw/haht/',460,'BUKU PENERBITAN','2026-02-24T02:05:34'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(64,13454542,'DPR RI Masa Orde Baru: Menguatnya Peran Negara 1967-1997 (Buku Empat)','DPR RI Masa Orde Baru: Menguatnya Peran Negara 1967-1997 (Buku Empat)','https://online.anyflip.com/fhwbw/xytv/files/shot.jpg?2','http://online.anyflip.com/fhwbw/xytv/',616,'BUKU PENERBITAN','2026-02-24T02:05:44'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(65,47142035,'Wajah Baru Parlemen Indonesia 1959-1966 (Buku Tiga)','Wajah Baru Parlemen Indonesia 1959-1966 (Buku Tiga)','https://online.anyflip.com/fhwbw/ivcg/files/shot.jpg?1','http://online.anyflip.com/fhwbw/ivcg/',438,'BUKU PENERBITAN','2026-02-24T02:05:19'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(66,56568263,'Upaya Menyatukan Kembali Republik Indonesia 1950-1960 (Buku Dua)','Upaya Menyatukan Kembali Republik Indonesia 1950-1960 (Buku Dua)','https://online.anyflip.com/fhwbw/vorr/files/shot.jpg?2','http://online.anyflip.com/fhwbw/vorr/',378,'BUKU PENERBITAN','2026-02-24T02:04:50'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(67,45771646,'Dari Volksraad Ke Komite Nasional Indonesia Pusat 1918-1949 (Buku Satu)','Dari Volksraad Ke Komite Nasional Indonesia Pusat 1918-1949 (Buku Satu)

Tahun 2019','https://online.anyflip.com/fhwbw/lctm/files/shot.jpg?1','http://online.anyflip.com/fhwbw/lctm/',468,'BUKU PENERBITAN','2026-02-24T02:05:35'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(68,91880986,'Berpihak Pada Rakyat - Catatan Kinerja Fadli Zon (Buku Tiga)','Berpihak Pada Rakyat - Catatan Kinerja Fadli Zon (2018)','https://online.anyflip.com/fhwbw/pjte/files/shot.jpg?1','http://online.anyflip.com/fhwbw/pjte/',310,'BUKU PENERBITAN','2026-02-23T01:13:08'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(69,75571770,'Berpihak Pada Rakyat - Catatan Kinerja Fadli Zon (Buku Dua)','Berpihak Pada Rakyat - Catatan Kinerja Fadli Zon (2018)','https://online.anyflip.com/fhwbw/wfch/files/shot.jpg?1','http://online.anyflip.com/fhwbw/wfch/',340,'BUKU PENERBITAN','2026-02-23T00:53:03'::timestamp,'2026-09-15T23:35:24.152571'::timestamp),
(70,38388174,'Berpihak Pada Rakyat - Catatan Kinerja Fadli Zon (Buku Satu)','Berpihak Pada Rakyat - Catatan Kinerja Fadli Zon (2018)','https://online.anyflip.com/fhwbw/eekt/files/shot.jpg?1','http://online.anyflip.com/fhwbw/eekt/',416,'BUKU PENERBITAN','2026-02-23T00:25:17'::timestamp,'2026-09-15T23:35:24.152571'::timestamp);

SELECT setval(pg_get_serial_sequence('ebook_showcase', 'id'), (SELECT MAX(id) FROM ebook_showcase));
