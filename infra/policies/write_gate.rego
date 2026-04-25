package ai_desk.write_gate

default allow := true

deny contains "manual approval required for write execution" if {
  input.permission.require_manual_approval_for_write
  count(input.workspace.writable_paths) > 0
  not input.permission.break_glass_reason
}
