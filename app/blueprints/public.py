from flask import Blueprint, abort, render_template, request, send_file

from ..models import BookRequest, BookType, EbookShowcase
from ..security import resolve_upload_path

bp = Blueprint("public", __name__)

PROCESS_STEPS = [
    ("01", "Request", "User mengisi data buku, anggota, materi foto dan text, "
                      "lalu mengirim pengajuan."),
    ("02", "Admin Approval", "Admin memeriksa kelengkapan pengajuan dan menyetujui "
                             "atau mengembalikannya."),
    ("03", "Editor Review", "Editor memeriksa cover, foto, nama anggota, layout, "
                            "dan kebutuhan cetak melalui checklist."),
    ("04", "Revision", "Bila ada kekurangan, request dikembalikan ke user dengan "
                       "catatan dan direvisi."),
    ("05", "Production", "Tim produksi mengerjakan pencetakan sesuai spesifikasi "
                         "yang telah disetujui."),
    ("06", "Completed", "Quality check dilakukan, buku selesai, dan seluruh riwayat "
                        "tersimpan."),
]

FEATURES = [
    ("Book Request", "Pengajuan buku lengkap dengan jenis, anggota, deadline, "
                     "dan kebutuhan cetak."),
    ("Approval Workflow", "Alur persetujuan bertingkat dari admin hingga siap produksi."),
    ("Editor Review", "Checklist pemeriksaan editor yang tersimpan pada setiap request."),
    ("Revision Management", "Setiap putaran revisi dicatat lengkap dengan catatan "
                            "editor dan tanggapan user."),
    ("File Management", "Upload cover, foto anggota, dokumentasi, dan lampiran "
                        "dengan validasi keamanan."),
    ("Notification", "Pemberitahuan internal setiap kali status request berpindah."),
    ("Audit History", "Timeline status dan audit log aktivitas untuk penelusuran."),
    ("Production Tracking", "Pemantauan produksi mulai dari antrean hingga selesai."),
]


def _clean_showcase_text(value):
    """Scraped descriptions carry raw HTML-entity artifacts (e.g. '&lt;br&gt;');
    strip them so the catalog shows plain text instead of literal tags."""
    if not value:
        return ""
    return value.replace("&lt;br&gt;", " ").strip()

@bp.get("/")
def home():
    page = request.args.get("page", 1, type=int)
    catalog = EbookShowcase.query.order_by(EbookShowcase.published_at.desc()) \
        .paginate(page=page, per_page=12, error_out=False)
    for book in catalog.items:
        book.display_description = _clean_showcase_text(book.description)
    public_requests = (BookRequest.query.filter_by(is_public=True)
                       .order_by(BookRequest.updated_at.desc()).limit(40).all())
    user_books = [r for r in public_requests if r.pdf_file][:12]
    return render_template("public/home.html", steps=PROCESS_STEPS, features=FEATURES,
                           book_types=BookType.query.filter_by(is_active=True)
                           .order_by(BookType.name).all(), catalog=catalog,
                           user_books=user_books, page="home")


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
