from tests.test_security_hardening import (
    test_approval_gate_hit_audited,
    test_audit_log_query_filters,
    test_blocked_command_audited,
    test_classify_command_approval_classes,
    test_classify_command_families,
    test_compute_provenance_hash_deterministic,
    test_secret_broker_disabled_raises,
    test_secret_broker_expired_secret_rejected,
    test_secret_broker_in_memory_basic,
    test_secret_broker_in_memory_with_audit,
    test_secret_broker_unknown_key_raises,
    test_validate_provenance_integrity_catches_executor_mismatch,
    test_validate_provenance_integrity_catches_missing_fields,
    test_validate_provenance_integrity_passes_for_valid,
    test_workspace_isolation_allows_valid_paths,
    test_workspace_isolation_blocks_cross_project_path,
    test_workspace_isolation_blocks_path_outside_allowlist,
    test_workspace_isolation_violation_audited,
    test_write_execution_grant_audited,
)

test_secret_broker_in_memory_basic()
print("test_secret_broker_in_memory_basic: PASS")

test_secret_broker_in_memory_with_audit()
print("test_secret_broker_in_memory_with_audit: PASS")

test_secret_broker_expired_secret_rejected()
print("test_secret_broker_expired_secret_rejected: PASS")

test_workspace_isolation_blocks_cross_project_path()
print("test_workspace_isolation_blocks_cross_project_path: PASS")

test_workspace_isolation_blocks_path_outside_allowlist()
print("test_workspace_isolation_blocks_path_outside_allowlist: PASS")

test_workspace_isolation_allows_valid_paths()
print("test_workspace_isolation_allows_valid_paths: PASS")

test_classify_command_families()
print("test_classify_command_families: PASS")

test_classify_command_approval_classes()
print("test_classify_command_approval_classes: PASS")

test_blocked_command_audited()
print("test_blocked_command_audited: PASS")

test_approval_gate_hit_audited()
print("test_approval_gate_hit_audited: PASS")

test_write_execution_grant_audited()
print("test_write_execution_grant_audited: PASS")

test_workspace_isolation_violation_audited()
print("test_workspace_isolation_violation_audited: PASS")

test_compute_provenance_hash_deterministic()
print("test_compute_provenance_hash_deterministic: PASS")

test_validate_provenance_integrity_catches_missing_fields()
print("test_validate_provenance_integrity_catches_missing_fields: PASS")

test_validate_provenance_integrity_catches_executor_mismatch()
print("test_validate_provenance_integrity_catches_executor_mismatch: PASS")

test_validate_provenance_integrity_passes_for_valid()
print("test_validate_provenance_integrity_passes_for_valid: PASS")

test_audit_log_query_filters()
print("test_audit_log_query_filters: PASS")

test_secret_broker_disabled_raises()
print("test_secret_broker_disabled_raises: PASS")

test_secret_broker_unknown_key_raises()
print("test_secret_broker_unknown_key_raises: PASS")

print("ALL TESTS PASSED")
