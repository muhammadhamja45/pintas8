"""Workflow state machine. Single source of truth for legal status transitions."""

DRAFT = "DRAFT"
SUBMITTED = "SUBMITTED"
ADMIN_REVIEW = "ADMIN_REVIEW"
ADMIN_APPROVED = "ADMIN_APPROVED"
EDITOR_REVIEW = "EDITOR_REVIEW"
REVISION_REQUIRED = "REVISION_REQUIRED"
USER_REVISION = "USER_REVISION"
EDITOR_APPROVED = "EDITOR_APPROVED"
READY_FOR_PRODUCTION = "READY_FOR_PRODUCTION"
PRODUCTION = "PRODUCTION"
QUALITY_CHECK = "QUALITY_CHECK"
COMPLETED = "COMPLETED"
REJECTED = "REJECTED"
CANCELLED = "CANCELLED"

ALL_STATUSES = [
    DRAFT, SUBMITTED, ADMIN_REVIEW, ADMIN_APPROVED, EDITOR_REVIEW,
    REVISION_REQUIRED, USER_REVISION, EDITOR_APPROVED, READY_FOR_PRODUCTION,
    PRODUCTION, QUALITY_CHECK, COMPLETED, REJECTED, CANCELLED,
]

STATUS_LABELS = {
    DRAFT: "Draft",
    SUBMITTED: "Submitted",
    ADMIN_REVIEW: "Kabag Review",
    ADMIN_APPROVED: "Kabag Approved",
    EDITOR_REVIEW: "Editor Review",
    REVISION_REQUIRED: "Revision Required",
    USER_REVISION: "Sekjen/Dewan Revision",
    EDITOR_APPROVED: "Editor Approved",
    READY_FOR_PRODUCTION: "Ready for Production",
    PRODUCTION: "Production",
    QUALITY_CHECK: "Quality Check",
    COMPLETED: "Completed",
    REJECTED: "Rejected",
    CANCELLED: "Cancelled",
}

# Role identifiers stay ADMIN/USER/etc internally (auth, DB, workflow logic);
# this only maps them to the display name shown in the UI.
ROLE_LABELS = {
    "ADMIN": "Kabag",
    "USER": "Sekjen/Dewan",
    "EDITOR": "Editor",
    "PRODUCTION": "Produksi",
}

# Badge colour class per status, used by the status_badge macro.
STATUS_TONES = {
    DRAFT: "muted",
    SUBMITTED: "info",
    ADMIN_REVIEW: "info",
    ADMIN_APPROVED: "info",
    EDITOR_REVIEW: "info",
    REVISION_REQUIRED: "warning",
    USER_REVISION: "warning",
    EDITOR_APPROVED: "success",
    READY_FOR_PRODUCTION: "success",
    PRODUCTION: "info",
    QUALITY_CHECK: "info",
    COMPLETED: "success",
    REJECTED: "danger",
    CANCELLED: "muted",
}

# (from -> to) : role allowed to perform the transition.
TRANSITIONS = {
    (DRAFT, SUBMITTED): "USER",
    (DRAFT, CANCELLED): "USER",
    (SUBMITTED, ADMIN_REVIEW): "ADMIN",
    (SUBMITTED, CANCELLED): "USER",
    (ADMIN_REVIEW, ADMIN_APPROVED): "ADMIN",
    (ADMIN_REVIEW, REJECTED): "ADMIN",
    (ADMIN_REVIEW, DRAFT): "ADMIN",            # return to user for fixes
    (ADMIN_APPROVED, EDITOR_REVIEW): "ADMIN",
    (EDITOR_REVIEW, REVISION_REQUIRED): "EDITOR",
    (EDITOR_REVIEW, EDITOR_APPROVED): "EDITOR",
    (REVISION_REQUIRED, USER_REVISION): "USER",
    (USER_REVISION, EDITOR_REVIEW): "USER",
    (EDITOR_APPROVED, READY_FOR_PRODUCTION): "EDITOR",
    (READY_FOR_PRODUCTION, PRODUCTION): "ADMIN",
    (PRODUCTION, QUALITY_CHECK): "PRODUCTION",
    (QUALITY_CHECK, COMPLETED): "PRODUCTION",
    (QUALITY_CHECK, PRODUCTION): "PRODUCTION",  # QC failed, back to the press
}

# Statuses the owning user may still edit request content in.
USER_EDITABLE = {DRAFT, REVISION_REQUIRED, USER_REVISION}

# Statuses reached only after an editor has approved the request.
PUBLIC_ELIGIBLE_STATUSES = {EDITOR_APPROVED, READY_FOR_PRODUCTION, PRODUCTION,
                            QUALITY_CHECK, COMPLETED}


def can_transition(old, new, role):
    """True when `role` is allowed to move a request from `old` to `new`.

    ADMIN also holds every EDITOR transition.
    """
    required = TRANSITIONS.get((old, new))
    return required == role or (role == "ADMIN" and required == "EDITOR")


def allowed_targets(status, role):
    return [to for (frm, to), r in TRANSITIONS.items() if frm == status and r == role]


class WorkflowError(Exception):
    """Illegal status transition."""

    def __init__(self, old, new, role):
        self.old, self.new, self.role = old, new, role
        super().__init__(
            f"Transisi {STATUS_LABELS.get(old, old)} -> {STATUS_LABELS.get(new, new)} "
            f"tidak diizinkan untuk role {role}."
        )
