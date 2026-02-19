"""
Audit log helper — NOT an HTTP middleware, but a utility function called
explicitly by admin router handlers after performing any state-changing operation.

Why not a real HTTP middleware?
  - HTTP middleware doesn't have access to the request body (consumed by FastAPI)
  - We need structured data (action, target_type, target_id, details)
  - Explicit calls in each admin endpoint give us full control and zero magic

Usage in admin routers:
    from app.middleware.audit_middleware import log_admin_action

    @router.put("/users/{user_id}/ban")
    def ban_user(user_id: str, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
        # ... do the ban ...
        log_admin_action(db, admin_id=str(admin.id), action="BAN_USER",
                         target_type="user", target_id=user_id,
                         details={"reason": "Cheating"})
"""
from sqlalchemy.orm import Session
from typing import Optional
from app.models.audit_log import AuditLog


def log_admin_action(
    db: Session,
    admin_id: str,
    action: str,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    details: Optional[dict] = None,
) -> AuditLog:
    """
    Insert an immutable audit log record.

    Args:
        db: database session
        admin_id: UUID string of the admin performing the action
        action: string constant like "BAN_USER", "CREDIT_COINS", "SETTLE_MATCH"
        target_type: entity type affected ("user", "room", "wallet", "league", "match")
        target_id: UUID string of the affected entity
        details: optional dict with extra context (amounts, reasons, before/after values)

    Returns the created AuditLog record.
    """
    log = AuditLog(
        admin_id=admin_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=details,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log
