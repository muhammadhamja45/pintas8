import re

from flask import Blueprint, abort, render_template, request, send_file

from ..models import BookRequest, EbookShowcase
from ..security import resolve_upload_path
from ..workflow import ROLE_LABELS

bp = Blueprint("public", __name__)

_USER = ROLE_LABELS["USER"]
_ADMIN = ROLE_LABELS["ADMIN"]

PROCESS_STEPS = [
    ("01", "Request", f"{_USER} mengisi data buku, anggota, materi foto dan text, "
                      "lalu mengirim pengajuan."),
    ("02", f"{_ADMIN} Approval", f"{_ADMIN} memeriksa kelengkapan pengajuan dan menyetujui "
                             "atau mengembalikannya."),
    ("03", "Editor Review", "Editor memeriksa cover, foto, nama anggota, layout, "
                            "dan kebutuhan cetak melalui checklist."),
    ("04", "Revision", f"Bila ada kekurangan, request dikembalikan ke {_USER} dengan "
                       "catatan dan direvisi."),
    ("05", "Production", "Tim produksi mengerjakan pencetakan sesuai spesifikasi "
                         "yang telah disetujui."),
    ("06", "Completed", "Quality check dilakukan, buku selesai, dan seluruh riwayat "
                        "tersimpan."),
]

FEATURES = [
    ("Book Request", "Pengajuan buku lengkap dengan jenis, anggota, deadline, "
                     "dan kebutuhan cetak."),
    ("Approval Workflow", f"Alur persetujuan bertingkat dari {_ADMIN.lower()} hingga siap produksi."),
    ("Editor Review", "Checklist pemeriksaan editor yang tersimpan pada setiap request."),
    ("Revision Management", "Setiap putaran revisi dicatat lengkap dengan catatan "
                            f"editor dan tanggapan {_USER.lower()}."),
    ("File Management", "Upload cover, foto anggota, dokumentasi, dan lampiran "
                        "dengan validasi keamanan."),
    ("Notification", "Pemberitahuan internal setiap kali status request berpindah."),
    ("Audit History", "Timeline status dan audit log aktivitas untuk penelusuran."),
    ("Production Tracking", "Pemantauan produksi mulai dari antrean hingga selesai."),
]

HOME_FEATURES = [
    ("Pengajuan Buku",
     "Ajukan buku baru dengan data lengkap: jenis, anggota, tenggat, dan spesifikasi cetak."),
    ("Persetujuan Pengajuan",
     "Alur persetujuan berjenjang memastikan setiap buku diperiksa sebelum masuk produksi."),
    ("Pemeriksaan dan Review Editor",
     "Checklist editor menjaga cover, isi, dan kesiapan cetak tetap sesuai standar."),
    ("Manajemen Revisi",
     "Setiap catatan revisi dan tanggapan tersimpan sebagai riwayat, tanpa menimpa data lama."),
    ("Monitoring Produksi",
     "Pantau antrean, quality check, dan penyelesaian produksi dalam satu tampilan."),
    ("Riwayat dan Dokumentasi",
     "Seluruh perubahan status dan berkas tercatat untuk penelusuran dan audit."),
]

SHOWCASE_TOPICS = [
    ("legislasi-hukum", "Legislasi & Hukum",
     "Undang-undang, anotasi, putusan, dan kajian hukum.",
     r"undang-undang|kuhap|kuhp|legislasi|anotasi|judical|hukum|putusan|pidana|konstitusi"),
    ("panduan-referensi", "Panduan & Referensi",
     "Panduan, pedoman, dan referensi kerja.",
     r"panduan|pedoman|buku saku|proses|teknik|modus|code of conduct|info|majalah"),
    ("laporan-kinerja", "Laporan & Kinerja",
     "Laporan tahunan, capaian kinerja, dan evaluasi program.",
     r"laporan|kinerja|auditama"),
    ("sejarah-arsip", "Sejarah & Arsip",
     "Sejarah parlemen, gedung, arsip, dan warisan institusi.",
     r"sejarah|arsip|gedung|parlemen|volksraad|orde baru|pancawarsa|seabad|century|diplomasi"),
    ("kebijakan-publik", "Kebijakan Publik",
     "Kebijakan, anggaran, ekonomi, dan pembangunan.",
     r"kebijakan|pelayanan publik|umkm|ekonomi|fiskal|koperasi|pembangunan|anggaran|pajak|listrik|kesejahteraan|pengadaan"),
    ("politik-demokrasi", "Politik & Demokrasi",
     "Demokrasi, politik, dan perjalanan wakil rakyat.",
     r"demokrasi|politik|dpr|senayan|suara|kiprah|fraksi|pemilu|pancasila|rakyat"),
]

TOPIC_FALLBACK = (
    "penerbitan-umum",
    "Penerbitan Umum",
    "Biografi, catatan perjalanan, dan terbitan umum lainnya.",
)

_TOPIC_RULES = [
    (slug, label, re.compile(pattern, re.I))
    for slug, label, _description, pattern in SHOWCASE_TOPICS
]
_TOPIC_DESCRIPTIONS = {slug: description
                       for slug, _label, description, _pattern in SHOWCASE_TOPICS}
_TOPIC_DESCRIPTIONS[TOPIC_FALLBACK[0]] = TOPIC_FALLBACK[2]
_AUTHOR_RE = re.compile(r"(?:Penulis|Penyusun|Author)\s*:\s*([^\n\r<]+)", re.I)


def _clean_showcase_text(value):
    """Scraped descriptions carry raw HTML-entity artifacts (e.g. '&lt;br&gt;');
    strip them so the catalog shows plain text instead of literal tags."""
    if not value:
        return ""
    return value.replace("&lt;br&gt;", " ").strip()


def _showcase_topic(book):
    title = book.title or ""
    for slug, label, pattern in _TOPIC_RULES:
        if pattern.search(title):
            return slug, label
    return TOPIC_FALLBACK[0], TOPIC_FALLBACK[1]


def _showcase_author(book):
    match = _AUTHOR_RE.search(book.description or "")
    if match:
        return match.group(1).strip()
    return "Sekretariat Jenderal DPR RI"


def _showcase_summary(book, topic_label):
    title = (book.title or "").strip()
    description = _clean_showcase_text(book.description)
    if description.lower() == title.lower():
        description = ""
    elif description.lower().startswith(title.lower()):
        description = description[len(title):].strip(" -–—|")
    if description:
        description = re.sub(r"(?:Penulis|Penyusun|Author)\s*:.*$", "",
                             description, flags=re.I).strip(" -–—|")
        description = re.sub(r"(?:[-–—]\s*)?(?:19|20)\d{2}\s*$", "",
                             description).strip(" -–—|")
    if len(description) < 24 and "|" in title:
        description = title.split("|", 1)[1].strip(" -–—|")
    if len(description) < 24:
        pages = f"{book.page_count} halaman" if book.page_count else "koleksi digital"
        description = (f"Terbitan {topic_label.lower()} dalam koleksi "
                       f"Digital Book DPR RI, {pages}.")
    return description


def _showcase_card(book):
    topic_slug, topic_label = _showcase_topic(book)
    return {
        "id": book.id,
        "title": book.title,
        "author": _showcase_author(book),
        "topic": topic_label,
        "topic_slug": topic_slug,
        "description": _showcase_summary(book, topic_label),
        "cover_url": book.cover_image_url,
        "source_url": book.source_url,
        "page_count": book.page_count,
        "year": book.published_at.year if book.published_at else None,
    }


def _catalog_books():
    books = EbookShowcase.query.order_by(
        EbookShowcase.published_at.desc().nullslast(),
        EbookShowcase.id.desc()).all()
    return [_showcase_card(book) for book in books]


def _topic_index(books):
    grouped = {}
    for book in books:
        grouped.setdefault(book["topic_slug"], []).append(book)
    topics = []
    entries = [(slug, label, _TOPIC_DESCRIPTIONS[slug])
               for slug, label, _description, _pattern in SHOWCASE_TOPICS]
    entries.append((TOPIC_FALLBACK[0], TOPIC_FALLBACK[1], TOPIC_FALLBACK[2]))
    for slug, label, description in entries:
        items = grouped.get(slug, [])
        if not items:
            continue
        topics.append({
            "slug": slug,
            "label": label,
            "description": description,
            "count": len(items),
            "covers": [item["cover_url"] for item in items[:3] if item["cover_url"]],
        })
    topics.sort(key=lambda topic: topic["count"], reverse=True)
    return topics


def _featured_books(books, limit=6):
    featured = []
    seen_topics = set()
    for book in books:
        if book["topic_slug"] in seen_topics:
            continue
        featured.append(book)
        seen_topics.add(book["topic_slug"])
        if len(featured) == limit:
            return featured
    featured_ids = {book["id"] for book in featured}
    for book in books:
        if book["id"] in featured_ids:
            continue
        featured.append(book)
        if len(featured) == limit:
            break
    return featured


def _paginate(items, page, per_page):
    per_page = max(1, per_page)
    pages = max(1, (len(items) + per_page - 1) // per_page)
    page = max(1, min(page, pages))
    start = (page - 1) * per_page
    page_numbers = []
    for number in range(1, pages + 1):
        if number in (1, pages) or abs(number - page) <= 2:
            page_numbers.append(number)
        elif page_numbers and page_numbers[-1] is not None:
            page_numbers.append(None)
    return {
        "items": items[start:start + per_page],
        "page": page,
        "pages": pages,
        "total": len(items),
        "has_prev": page > 1,
        "has_next": page < pages,
        "prev_num": page - 1,
        "next_num": page + 1,
        "page_numbers": page_numbers,
    }


@bp.get("/")
def home():
    books = _catalog_books()
    public_requests = (BookRequest.query.filter_by(is_public=True)
                       .order_by(BookRequest.updated_at.desc()).limit(40).all())
    user_books = [book for book in public_requests if book.pdf_file][:12]
    featured = _featured_books(books)
    return render_template(
        "public/home.html",
        steps=PROCESS_STEPS,
        features=HOME_FEATURES,
        user_books=user_books,
        featured_books=featured,
        hero_books=featured[:5],
        topics=_topic_index(books),
        showcase_total=len(books),
        page="home",
    )


@bp.get("/catalog")
def catalog():
    books = _catalog_books()
    topics = _topic_index(books)
    active_slug = request.args.get("category", "").strip()
    active_topic = next((topic for topic in topics if topic["slug"] == active_slug), None)
    filtered = ([book for book in books if book["topic_slug"] == active_slug]
                if active_topic else books)
    catalog_page = _paginate(filtered, request.args.get("page", 1, type=int), 16)
    return render_template(
        "public/catalog.html",
        books=catalog_page["items"],
        catalog=catalog_page,
        topics=topics,
        active_category=active_topic["slug"] if active_topic else "",
        active_topic=active_topic,
        showcase_total=len(books),
        page="catalog",
    )


@bp.get("/books/<int:request_id>/pdf")
def public_book_pdf(request_id):
    """Serve a user-uploaded book PDF, but only once its owner made it public."""
    book_request = BookRequest.query.get(request_id)
    if book_request is None or not book_request.is_public or book_request.pdf_file is None:
        abort(404, description="Buku tidak ditemukan.")
    path = resolve_upload_path(book_request.pdf_file.file_path)
    return send_file(path, mimetype="application/pdf", as_attachment=False)


@bp.get("/books/<int:request_id>/cover")
def public_book_cover(request_id):
    """Serve a user-uploaded book cover, but only once its owner made it public."""
    book_request = BookRequest.query.get(request_id)
    if book_request is None or not book_request.is_public or book_request.cover_file is None:
        abort(404, description="Cover tidak ditemukan.")
    path = resolve_upload_path(book_request.cover_file.file_path)
    return send_file(path, mimetype=book_request.cover_file.mime_type, as_attachment=False)


@bp.get("/about")
def about():
    return render_template("public/about.html", page="about")


@bp.get("/workflow")
def workflow_page():
    return render_template("public/workflow.html", steps=PROCESS_STEPS, page="workflow")


@bp.get("/features")
def features():
    return render_template("public/features.html", features=FEATURES, page="features")
