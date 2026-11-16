"""Action engine: the ONLY component allowed to execute intents.

Deterministic and permission-checked (plan §6.5): validates the intent, its
actor (token scope), and the target registry before running a handler. The
LLM sits strictly upstream. Handlers create rows + activity + events exactly
like the REST routers do.
"""
from sqlalchemy.orm import Session

from ..deps import bump_revision, log_activity, publish_event
from ..models import Note, Task, User


class ActionError(Exception):
    pass


# What each scope may execute (mirrors devices.py / security.py scopes).
PERMISSIONS = {
    "create_task": {"user", "capture", "sync", "automation"},
    "create_note": {"user", "capture", "sync", "automation"},
}


def execute_intent(db: Session, user: User, intent: dict, source: str = "voice") -> dict:
    """Run a validated intent for `user`; returns the created row's payload."""
    action = intent.get("action")
    if action not in PERMISSIONS:
        raise ActionError(f"unknown action: {action}")

    scope = getattr(user, "_token_scope", "user")
    granted = {scope} if scope == "user" else {s for s in scope.split(",") if s}
    if not granted.intersection(PERMISSIONS[action]):
        raise ActionError(f"scope '{scope}' may not execute {action}")

    title = intent["title"].strip()
    description = intent.get("description")

    if action == "create_task":
        task = Task(
            title=title,
            description=(description or None),
            owner_id=user.id,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        log_activity(db, user_id=user.id, action="task.created", detail=f"[ai:{source}] {task.title}")
        publish_event("TASK_CREATED", user.id, {"task_id": task.id, "title": task.title, "source": f"ai:{source}"})
        db.commit()
        return {"kind": "task", "id": task.id, "title": task.title, "revision": task.revision}

    if action == "create_note":
        note = Note(
            title=title,
            content=(description or title),
            owner_id=user.id,
        )
        db.add(note)
        db.commit()
        db.refresh(note)
        log_activity(db, user_id=user.id, action="note.created", detail=f"[ai:{source}] {note.title}")
        publish_event("NOTE_CREATED", user.id, {"note_id": note.id, "title": note.title, "source": f"ai:{source}"})
        db.commit()
        return {"kind": "note", "id": note.id, "title": note.title, "revision": note.revision}

    raise ActionError(f"no handler for action: {action}")  # unreachable; kept for safety
