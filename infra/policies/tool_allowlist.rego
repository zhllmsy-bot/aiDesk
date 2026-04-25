package ai_desk.tool_allowlist

default allow := true

deny contains sprintf("blocked command: %s", [command]) if {
  command := input.commands[_]
  prefix := input.permission.command_denylist[_]
  startswith(command, prefix)
}

deny contains sprintf("command outside allowlist: %s", [command]) if {
  count(input.permission.command_allowlist) > 0
  command := input.commands[_]
  not startswith(command, input.permission.command_allowlist[_])
}
