package ai_desk.execution

default allow := true

deny contains "workspace root outside allowlist" if {
  not startswith(input.workspace.root_path, input.permission.workspace_allowlist[_])
}

deny contains "manual approval required for write execution" if {
  input.permission.require_manual_approval_for_write
  count(input.workspace.writable_paths) > 0
  not input.permission.break_glass_reason
}

deny contains sprintf("blocked command: %s", [command]) if {
  command := input.commands[_]
  prefix := input.permission.command_denylist[_]
  startswith(command, prefix)
}
