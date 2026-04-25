# Executor Provider Bridges

- 状态：`Working Draft (v0.4, 2026-04-23)`
- 仓库：`/Users/admin/Desktop/ai-desk`

## 目标

冻结 `ai-desk` 与底层 executor provider 的桥接边界，避免在 platform 层继续扩出第二套 runtime 协议。

## 当前 Provider

1. `codex`
2. `openhands`

## 代码落点

- `/Users/admin/Desktop/ai-desk/apps/api/api/executors/provider_contracts.py`
- `/Users/admin/Desktop/ai-desk/apps/api/api/executors/providers/codex.py`
- `/Users/admin/Desktop/ai-desk/apps/api/api/executors/providers/openhands.py`

## Codex Bridge

请求模型：

- `CodexProviderRequest`
- `CodexThreadRequest`
- `CodexTurnRequest`

响应模型：

- `CodexProviderResponse`
- `CodexTurnResult`
- `CodexCompletedItem`

错误模型：

- `CodexProviderError`

桥接约束：

- transport 仅允许 `stdio` 或 `websocket`
- provider timeout / transport failure / sandbox denial / cancelled / partial execution 都映射到 `FailureCategory`
- verification artifact 必须输出结构化结果，不再只有 verify command 名单

产物要求：

- transcript artifact: `artifacts/codex/transcript.md`
- changed-files artifact: `artifacts/codex/changed-files.json`
- verification artifact: `artifacts/codex/verification.json`

## OpenHands Bridge

响应模型：

- `OpenHandsProviderResponse`
- `OpenHandsVerificationItem`

错误模型：

- `OpenHandsProviderError`

桥接约束：

- runtime 通过官方 `Workspace` 抽象执行，不再依赖私有 `/api/execute`
- provider 只负责 `ExecutorInputBundle -> Workspace command bundle -> ExecutorResultBundle` 的 mapping
- partial execution 必须映射到 `FailureCategory.PARTIAL_EXECUTION`

产物要求：

- session log artifact: `artifacts/openhands/session.log`
- verification artifact: `artifacts/openhands/verification.json`
- workspace output artifact: `artifacts/openhands/workspace-output.json`

## 失败语义

统一失败分类：

1. `transport_failure`
2. `provider_timeout`
3. `sandbox_denial`
4. `verification_failure`
5. `partial_execution`
6. `provider_error`
7. `cancelled`

## 当前冻结结论

- `ai-desk` 保留 provider adapter 与 review/runtime 绑定
- sandbox/runtime/graph/memory 主能力优先复用上游 OSS
- provider bridge 只允许增长 schema，不允许继续增长私有 runtime 语义
