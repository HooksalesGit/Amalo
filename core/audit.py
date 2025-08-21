"""Simple audit log utilities."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, List


@dataclass
class AuditEntry:
    user: str
    field: str
    old_value: Any
    new_value: Any
    timestamp: datetime


class AuditLog:
    """In-memory audit log suitable for tests and small apps."""

    def __init__(self) -> None:
        self.entries: List[AuditEntry] = []

    def record(self, user: str, field: str, old_value: Any, new_value: Any) -> None:
        """Record a change to a field with user and timestamp."""
        self.entries.append(
            AuditEntry(
                user=user,
                field=field,
                old_value=old_value,
                new_value=new_value,
                timestamp=datetime.utcnow(),
            )
        )

    def as_dict(self) -> List[dict]:
        """Return log entries as dictionaries for persistence or inspection."""
        return [
            {
                "user": e.user,
                "field": e.field,
                "old": e.old_value,
                "new": e.new_value,
                "timestamp": e.timestamp.isoformat(),
            }
            for e in self.entries
        ]
