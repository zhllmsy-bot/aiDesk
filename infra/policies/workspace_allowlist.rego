package ai_desk.workspace_allowlist

default allow := true

deny contains "workspace root outside allowlist" if {
  not startswith(input.workspace.root_path, input.permission.workspace_allowlist[_])
}
