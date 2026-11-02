# app/services/audit_helper.py
import uuid
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.system import AuditLog


async def record_audit_event(
    db: AsyncSession,
    actor_user_id: Optional[uuid.UUID],
    action_type: str,
    entity_name: str,
    entity_id: Optional[uuid.UUID] = None,
    previous_state: Optional[Dict[str, Any]] = None,
    new_state: Optional[Dict[str, Any]] = None,
    operation_result: str = "SUCCESS",
    details: Optional[Dict[str, Any]] = None,
    client_ip: Optional[str] = None,
) -> AuditLog:
    """
    Append-only audit logger compliant with ADM-AU-BR-001 through ADM-AU-BR-015.
    Never logs passwords or secrets (ADM-AU-BR-012).
    """
    audit_entry = AuditLog(
        actor_user_id=actor_user_id,
        action_type=action_type,
        entity_name=entity_name,
        entity_id=entity_id,
        previous_state=previous_state,
        new_state=new_state,
        operation_result=operation_result,
        details=details,
        client_ip=client_ip,
    )
    db.add(audit_entry)
    await db.flush()
    return audit_entry