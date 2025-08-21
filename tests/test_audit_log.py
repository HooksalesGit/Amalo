import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from core.audit import AuditLog


def test_audit_log_records_user_field_and_timestamp():
    log = AuditLog()
    log.record("alice", "income", 100, 200)
    assert len(log.entries) == 1
    entry = log.entries[0]
    assert entry.user == "alice"
    assert entry.field == "income"
    assert entry.old_value == 100
    assert entry.new_value == 200
    assert entry.timestamp is not None
