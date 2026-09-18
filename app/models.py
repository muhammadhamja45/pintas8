"""SQLAlchemy models. The schema of record is database.sql; these mirror it."""
from datetime import date, datetime

from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


def _now():
    return datetime.now()


def _iso(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    return str(value)


class Role(db.Model):
    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=False, unique=True)
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, nullable=False, default=_now)


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30))
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    last_login_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, default=_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=_now, onupdate=_now)

    role = db.relationship("Role", lazy="joined")

    def set_password(self, raw):
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw):
        return check_password_hash(self.password_hash, raw)

    @property
    def role_name(self):
        return self.role.name if self.role else None

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "phone": self.phone,
            "role": self.role_name,
            "role_id": self.role_id,
            "is_active": self.is_active,
            "last_login_at": _iso(self.last_login_at),
            "created_at": _iso(self.created_at),
        }


class BookType(db.Model):
    __tablename__ = "book_types"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False, unique=True)
    description = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=_now, onupdate=_now)

    @property
    def as_option(self):
        """(value, label) pair for the form_select macro."""
        return (self.id, self.name)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "is_active": self.is_active,
            "created_at": _iso(self.created_at),
        }


class BookRequest(db.Model):
    __tablename__ = "book_requests"
    id = db.Column(db.Integer, primary_key=True)
    request_code = db.Column(db.String(30), nullable=False, unique=True)
    title = db.Column(db.String(200), nullable=False)
    book_type_id = db.Column(db.Integer, db.ForeignKey("book_types.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    description = db.Column(db.Text)
    member_count = db.Column(db.Integer, nullable=False, default=0)
    deadline = db.Column(db.Date)
    extra_note = db.Column(db.Text)
    book_size = db.Column(db.String(50))
    paper_type = db.Column(db.String(50))
    print_quantity = db.Column(db.Integer)
    finishing = db.Column(db.String(50))
    printing_note = db.Column(db.Text)
    status = db.Column(db.String(30), nullable=False, default="DRAFT")
    current_assignee_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    revision_count = db.Column(db.Integer, nullable=False, default=0)
    is_public = db.Column(db.Boolean, nullable=False, default=False)
    submitted_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, default=_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=_now, onupdate=_now)

    book_type = db.relationship("BookType", lazy="joined")
    owner = db.relationship("User", foreign_keys=[user_id], lazy="joined")
    assignee = db.relationship("User", foreign_keys=[current_assignee_id])
    members = db.relationship(
        "BookMember", back_populates="request", cascade="all, delete-orphan",
        order_by="BookMember.sort_order", lazy="selectin")
    files = db.relationship(
        "BookFile", back_populates="request", cascade="all, delete-orphan",
        order_by="BookFile.id", lazy="selectin")
    texts = db.relationship(
        "BookText", back_populates="request", cascade="all, delete-orphan",
        lazy="selectin")
    history = db.relationship(
        "RequestStatusHistory", back_populates="request", cascade="all, delete-orphan",
        order_by="RequestStatusHistory.created_at.desc()", lazy="selectin")
    revisions = db.relationship(
        "RequestRevision", back_populates="request", cascade="all, delete-orphan",
        order_by="RequestRevision.revision_number", lazy="selectin")
    checklist = db.relationship(
        "EditorChecklist", back_populates="request", uselist=False,
        cascade="all, delete-orphan", lazy="selectin")
    production_order = db.relationship(
        "ProductionOrder", back_populates="request", uselist=False,
        cascade="all, delete-orphan", lazy="selectin")

    @property
    def pdf_file(self):
        """Most recently uploaded PDF on this request, used as the flipbook source."""
        pdfs = [f for f in self.files if f.mime_type == "application/pdf"]
        return max(pdfs, key=lambda f: f.id) if pdfs else None

    @property
    def cover_file(self):
        """Most recently uploaded cover image, used as the book thumbnail."""
        covers = [f for f in self.files if f.category == "COVER" and f.is_image]
        return max(covers, key=lambda f: f.id) if covers else None

    def to_dict(self, detail=False):
        data = {
            "id": self.id,
            "request_code": self.request_code,
            "title": self.title,
            "book_type_id": self.book_type_id,
            "book_type": self.book_type.name if self.book_type else None,
            "user_id": self.user_id,
            "owner": self.owner.full_name if self.owner else None,
            "status": self.status,
            "member_count": self.member_count,
            "print_quantity": self.print_quantity,
            "book_size": self.book_size,
            "paper_type": self.paper_type,
            "finishing": self.finishing,
            "deadline": _iso(self.deadline),
            "revision_count": self.revision_count,
            "is_public": self.is_public,
            "has_pdf": self.pdf_file is not None,
            "assignee": self.assignee.full_name if self.assignee else None,
            "submitted_at": _iso(self.submitted_at),
            "completed_at": _iso(self.completed_at),
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
        }
        if detail:
            data.update({
                "description": self.description,
                "extra_note": self.extra_note,
                "book_size": self.book_size,
                "paper_type": self.paper_type,
                "print_quantity": self.print_quantity,
                "finishing": self.finishing,
                "printing_note": self.printing_note,
                "owner_email": self.owner.email if self.owner else None,
                "members": [m.to_dict() for m in self.members],
                "files": [f.to_dict() for f in self.files],
                "texts": {t.section: t.content for t in self.texts},
                "history": [h.to_dict() for h in self.history],
                "revisions": [r.to_dict() for r in self.revisions],
                "checklist": self.checklist.to_dict() if self.checklist else None,
                "production_order": (self.production_order.to_dict()
                                     if self.production_order else None),
            })
        return data


class BookMember(db.Model):
    __tablename__ = "book_members"
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey("book_requests.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    position = db.Column(db.String(120))
    note = db.Column(db.Text)
    photo_file_id = db.Column(db.Integer, db.ForeignKey("book_files.id"))
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=_now, onupdate=_now)

    request = db.relationship("BookRequest", back_populates="members")
    photo = db.relationship("BookFile", foreign_keys=[photo_file_id])

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "position": self.position,
            "note": self.note,
            "sort_order": self.sort_order,
            "photo_file_id": self.photo_file_id,
            "photo_url": f"/api/files/{self.photo_file_id}" if self.photo_file_id else None,
        }


FILE_CATEGORIES = ["COVER", "MEMBER_PHOTO", "DOCUMENTATION", "SUPPORT", "ATTACHMENT", "FINAL"]


class BookFile(db.Model):
    __tablename__ = "book_files"
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey("book_requests.id"), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    category = db.Column(db.String(30), nullable=False, default="SUPPORT")
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False, unique=True)
    mime_type = db.Column(db.String(120), nullable=False)
    file_size = db.Column(db.BigInteger, nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    revision_number = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=_now)

    request = db.relationship("BookRequest", back_populates="files")
    uploader = db.relationship("User", foreign_keys=[uploaded_by], lazy="joined")

    @property
    def is_image(self):
        return bool(self.mime_type) and self.mime_type.startswith("image/")

    def to_dict(self):
        return {
            "id": self.id,
            "request_id": self.request_id,
            "category": self.category,
            "original_filename": self.original_filename,
            "mime_type": self.mime_type,
            "file_size": self.file_size,
            "is_image": self.is_image,
            "revision_number": self.revision_number,
            "uploaded_by": self.uploader.full_name if self.uploader else None,
            "url": f"/api/files/{self.id}",
            "created_at": _iso(self.created_at),
        }


TEXT_SECTIONS = [
    ("KATA_PENGANTAR", "Kata Pengantar"),
    ("DESKRIPSI", "Deskripsi"),
    ("BIODATA", "Biodata"),
    ("ISI_BUKU", "Isi Buku"),
    ("CATATAN_LAYOUT", "Catatan Layout"),
    ("INSTRUKSI_PERCETAKAN", "Instruksi Percetakan"),
]


class BookText(db.Model):
    __tablename__ = "book_texts"
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey("book_requests.id"), nullable=False)
    section = db.Column(db.String(40), nullable=False)
    content = db.Column(db.Text, nullable=False, default="")
    created_at = db.Column(db.DateTime, nullable=False, default=_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=_now, onupdate=_now)

    request = db.relationship("BookRequest", back_populates="texts")


class RequestStatusHistory(db.Model):
    __tablename__ = "request_status_history"
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey("book_requests.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    old_status = db.Column(db.String(30))
    new_status = db.Column(db.String(30), nullable=False)
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=_now)

    request = db.relationship("BookRequest", back_populates="history")
    actor = db.relationship("User", lazy="joined")

    def to_dict(self):
        return {
            "id": self.id,
            "request_id": self.request_id,
            "request_code": self.request.request_code if self.request else None,
            "title": self.request.title if self.request else None,
            "old_status": self.old_status,
            "new_status": self.new_status,
            "note": self.note,
            "actor": self.actor.full_name if self.actor else "Sistem",
            "actor_role": self.actor.role_name if self.actor else None,
            "created_at": _iso(self.created_at),
        }


class RequestRevision(db.Model):
    __tablename__ = "request_revisions"
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey("book_requests.id"), nullable=False)
    revision_number = db.Column(db.Integer, nullable=False)
    requested_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    editor_note = db.Column(db.Text, nullable=False)
    user_response = db.Column(db.Text)
    resolved_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    resolved_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, default=_now)

    request = db.relationship("BookRequest", back_populates="revisions")
    requester = db.relationship("User", foreign_keys=[requested_by], lazy="joined")
    resolver = db.relationship("User", foreign_keys=[resolved_by], lazy="joined")

    def to_dict(self):
        return {
            "id": self.id,
            "request_id": self.request_id,
            "revision_number": self.revision_number,
            "editor_note": self.editor_note,
            "user_response": self.user_response,
            "requested_by": self.requester.full_name if self.requester else None,
            "resolved_by": self.resolver.full_name if self.resolver else None,
            "resolved_at": _iso(self.resolved_at),
            "created_at": _iso(self.created_at),
        }


CHECKLIST_FIELDS = [
    ("cover_ok", "Cover sudah benar"),
    ("photos_complete", "Foto lengkap"),
    ("photo_resolution_ok", "Resolusi foto cukup"),
    ("member_names_ok", "Nama anggota benar"),
    ("text_complete", "Text lengkap"),
    ("layout_ok", "Layout sesuai"),
    ("book_size_set", "Ukuran buku ditentukan"),
    ("paper_type_set", "Jenis kertas ditentukan"),
    ("print_quantity_set", "Jumlah cetak ditentukan"),
    ("finishing_set", "Finishing ditentukan"),
]


class EditorChecklist(db.Model):
    __tablename__ = "editor_checklists"
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey("book_requests.id"), nullable=False)
    editor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    cover_ok = db.Column(db.Boolean, nullable=False, default=False)
    photos_complete = db.Column(db.Boolean, nullable=False, default=False)
    photo_resolution_ok = db.Column(db.Boolean, nullable=False, default=False)
    member_names_ok = db.Column(db.Boolean, nullable=False, default=False)
    text_complete = db.Column(db.Boolean, nullable=False, default=False)
    layout_ok = db.Column(db.Boolean, nullable=False, default=False)
    book_size_set = db.Column(db.Boolean, nullable=False, default=False)
    paper_type_set = db.Column(db.Boolean, nullable=False, default=False)
    print_quantity_set = db.Column(db.Boolean, nullable=False, default=False)
    finishing_set = db.Column(db.Boolean, nullable=False, default=False)
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=_now, onupdate=_now)

    request = db.relationship("BookRequest", back_populates="checklist")
    editor = db.relationship("User", lazy="joined")

    @property
    def all_checked(self):
        return all(getattr(self, field) for field, _ in CHECKLIST_FIELDS)

    def to_dict(self):
        data = {field: getattr(self, field) for field, _ in CHECKLIST_FIELDS}
        data.update({
            "id": self.id,
            "note": self.note,
            "editor": self.editor.full_name if self.editor else None,
            "all_checked": self.all_checked,
            "updated_at": _iso(self.updated_at),
        })
        return data


class Notification(db.Model):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    request_id = db.Column(db.Integer, db.ForeignKey("book_requests.id"))
    title = db.Column(db.String(160), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(20), nullable=False, default="INFO")
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=_now)

    def to_dict(self):
        return {
            "id": self.id,
            "request_id": self.request_id,
            "title": self.title,
            "message": self.message,
            "type": self.type,
            "is_read": self.is_read,
            "created_at": _iso(self.created_at),
        }


class ProductionOrder(db.Model):
    __tablename__ = "production_orders"
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey("book_requests.id"), nullable=False)
    order_code = db.Column(db.String(30), nullable=False, unique=True)
    assigned_to = db.Column(db.Integer, db.ForeignKey("users.id"))
    status = db.Column(db.String(30), nullable=False, default="WAITING")
    note = db.Column(db.Text)
    started_at = db.Column(db.DateTime)
    qc_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, default=_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=_now, onupdate=_now)

    request = db.relationship("BookRequest", back_populates="production_order")
    operator = db.relationship("User", lazy="joined")
    entries = db.relationship(
        "ProductionHistory", back_populates="order", cascade="all, delete-orphan",
        order_by="ProductionHistory.created_at.desc()", lazy="selectin")

    def to_dict(self):
        return {
            "id": self.id,
            "request_id": self.request_id,
            "order_code": self.order_code,
            "status": self.status,
            "note": self.note,
            "assigned_to": self.operator.full_name if self.operator else None,
            "started_at": _iso(self.started_at),
            "qc_at": _iso(self.qc_at),
            "completed_at": _iso(self.completed_at),
            "created_at": _iso(self.created_at),
            "entries": [e.to_dict() for e in self.entries],
        }


class ProductionHistory(db.Model):
    __tablename__ = "production_history"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("production_orders.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    action = db.Column(db.String(40), nullable=False)
    old_status = db.Column(db.String(30))
    new_status = db.Column(db.String(30))
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=_now)

    order = db.relationship("ProductionOrder", back_populates="entries")
    actor = db.relationship("User", lazy="joined")

    def to_dict(self):
        return {
            "id": self.id,
            "action": self.action,
            "old_status": self.old_status,
            "new_status": self.new_status,
            "note": self.note,
            "actor": self.actor.full_name if self.actor else None,
            "created_at": _iso(self.created_at),
        }


class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    request_id = db.Column(db.Integer, db.ForeignKey("book_requests.id"))
    action = db.Column(db.String(40), nullable=False)
    old_status = db.Column(db.String(30))
    new_status = db.Column(db.String(30))
    description = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, nullable=False, default=_now)

    actor = db.relationship("User", lazy="joined")

    def to_dict(self):
        return {
            "id": self.id,
            "action": self.action,
            "old_status": self.old_status,
            "new_status": self.new_status,
            "description": self.description,
            "ip_address": self.ip_address,
            "request_id": self.request_id,
            "actor": self.actor.full_name if self.actor else "Sistem",
            "actor_role": self.actor.role_name if self.actor else None,
            "created_at": _iso(self.created_at),
        }


class EbookShowcase(db.Model):
    """Published books shown as a public catalog on the home page.

    Read-only display data (no user-facing CRUD): sourced from the
    publisher's existing e-book catalog.
    """
    __tablename__ = "ebook_showcase"
    id = db.Column(db.Integer, primary_key=True)
    external_id = db.Column(db.BigInteger)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(500))
    cover_image_url = db.Column(db.String(500))
    source_url = db.Column(db.String(500))
    page_count = db.Column(db.Integer)
    category = db.Column(db.String(100))
    published_at = db.Column(db.DateTime)
    scraped_at = db.Column(db.DateTime, nullable=False, default=_now)
