# Executor Contract

- 状态：`Working Draft (v0.3, 2026-04-19)`

## 当前已落地 contract（代码已实现）

1. executor request envelope（`ExecutorInputBundle`）
2. result envelope（`ExecutorResultBundle` + `FailureInfo` + `VerificationResult`）
3. artifact/evidence/provenance schema
4. approval/attempt/review view models
5. provider error 分类（transport/timeout/sandbox/partial）

## 已接入 provider

1. `codex`
2. `openhands`

## 仍待冻结主题

1. provider 级 timeout/retry/cancel 统一策略
2. verify command 执行来源一致性（真实执行 vs transcript 推断）
3. sandbox/approval contract 的跨 provider 统一粒度

## 对应代码落点

- `apps/api/api/executors/contracts.py`
- `apps/api/api/executors/provider_contracts.py`
- `apps/api/api/executors/providers/codex.py`
- `apps/api/api/executors/providers/openhands.py`
- `docs/specs/executor-provider-bridges.md`
