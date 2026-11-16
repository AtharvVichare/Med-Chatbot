"""
Agent Event Bus for Aarogya-Drishti AI-Native Hospital Management System.
Coordinates inter-agent communication, workflow state machine, task delegation,
event persistence, and human escalation workflows.
"""

import uuid
import json
import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Callable
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.app.db.models import AgentEventLog
from backend.app.db.session import SessionLocal

logger = logging.getLogger("AgentEventBus")

class AgentEventBus:
    _subscribers: Dict[str, List[Callable]] = {}
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AgentEventBus, cls).__new__(cls)
            cls._instance._subscribers = {}
        return cls._instance

    @classmethod
    def subscribe(cls, event_type: str, handler: Callable):
        """Registers an asynchronous or synchronous agent event handler."""
        if event_type not in cls._subscribers:
            cls._subscribers[event_type] = []
        cls._subscribers[event_type].append(handler)
        logger.info(f"Subscribed handler {handler.__name__} to event {event_type}")

    @classmethod
    def emit(
        cls,
        source_agent: str,
        event_type: str,
        payload: Dict[str, Any],
        target_agent: Optional[str] = None,
        requires_human_approval: bool = False,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Emits an inter-agent event, records it in the database audit log,
        and invokes registered handlers or routes to target agent.
        """
        event_id = f"EVT-{uuid.uuid4().hex[:10].upper()}"
        now_utc = datetime.now(timezone.utc)
        payload_str = json.dumps(payload, default=str)

        should_close_db = False
        if db is None:
            db = SessionLocal()
            should_close_db = True

        try:
            status = "pending_approval" if requires_human_approval else "completed"
            event_log = AgentEventLog(
                event_id=event_id,
                timestamp=now_utc,
                source_agent=source_agent,
                target_agent=target_agent,
                event_type=event_type,
                payload_json=payload_str,
                status=status,
                requires_human_approval=requires_human_approval,
                approval_status="pending" if requires_human_approval else "auto_authorized"
            )
            db.add(event_log)
            db.commit()

            result = {
                "event_id": event_id,
                "timestamp": now_utc.isoformat(),
                "source_agent": source_agent,
                "target_agent": target_agent,
                "event_type": event_type,
                "status": status,
                "requires_human_approval": requires_human_approval,
                "payload": payload
            }

            # Invoke subscribers if any
            handlers = cls._subscribers.get(event_type, [])
            for handler in handlers:
                try:
                    handler(result)
                except Exception as ex:
                    logger.error(f"Error executing handler {handler.__name__} on {event_type}: {ex}")

            logger.info(f"[EVENT_BUS] {source_agent} -> {target_agent or 'BROADCAST'}: {event_type} ({event_id}) [{status}]")
            return result

        except Exception as e:
            logger.error(f"Failed to emit event {event_type} from {source_agent}: {e}")
            db.rollback()
            return {
                "event_id": event_id,
                "status": "failed",
                "error": str(e)
            }
        finally:
            if should_close_db:
                db.close()

    @classmethod
    def get_recent_events(cls, limit: int = 50, db: Optional[Session] = None) -> List[Dict[str, Any]]:
        """Retrieves recent multi-agent events for the Management activity feed."""
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True

        try:
            events = db.scalars(
                select(AgentEventLog)
                .order_by(AgentEventLog.timestamp.desc())
                .limit(limit)
            ).all()

            results = []
            for ev in events:
                try:
                    payload = json.loads(ev.payload_json)
                except Exception:
                    payload = ev.payload_json

                results.append({
                    "event_id": ev.event_id,
                    "timestamp": ev.timestamp.isoformat() if ev.timestamp else None,
                    "source_agent": ev.source_agent,
                    "target_agent": ev.target_agent,
                    "event_type": ev.event_type,
                    "payload": payload,
                    "status": ev.status,
                    "requires_human_approval": ev.requires_human_approval,
                    "approval_status": ev.approval_status,
                    "resolution_notes": ev.resolution_notes
                })
            return results
        finally:
            if should_close:
                db.close()

    @classmethod
    def resolve_escalation(
        cls,
        event_id: str,
        action: str,  # "approve" or "reject"
        resolution_notes: str,
        user_id: str,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """Resolves a human approval escalation."""
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True

        try:
            event = db.scalar(select(AgentEventLog).where(AgentEventLog.event_id == event_id))
            if not event:
                raise ValueError(f"Event {event_id} not found")

            event.approval_status = "approved" if action == "approve" else "rejected"
            event.status = "completed" if action == "approve" else "rejected"
            event.resolution_notes = f"{action.upper()} by {user_id}: {resolution_notes}"
            db.commit()

            return {
                "event_id": event.event_id,
                "status": event.status,
                "approval_status": event.approval_status,
                "resolution_notes": event.resolution_notes
            }
        finally:
            if should_close:
                db.close()

event_bus = AgentEventBus()
