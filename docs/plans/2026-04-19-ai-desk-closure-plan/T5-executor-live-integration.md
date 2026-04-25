# T5 Executor Live Integration 收口

- 优先级：`P1`
- 目标：把 executor 从“真实 transport 已接入”推进到“真实执行结果可验证、契约稳定、失败语义清晰”

---

## 1. 当前问题

当前 Codex / OpenHands 已经不是纯 stub，但还有明显缺口：

- `/Users/admin/Desktop/ai-desk/apps/api/api/executors/providers/codex.py`
- `/Users/admin/Desktop/ai-desk/apps/api/api/executors/providers/openhands.py`
- `/Users/admin/Desktop/ai-desk/apps/api/api/executors/transports.py`

主要问题：

1. Codex verification 还是从 transcript 推断，不是真正的 verification artifact。
2. OpenHands `/api/execute` 协议是假定桥接协议，真实服务契约仍需联调确认。
3. executor 输出缺少稳定的 transcript / command / file diff artifact 抽取。
4. timeout / cancellation / retry 映射还不完整。

---

## 2. 技术实施方案

### A. 明确 provider bridge contract

为 Codex / OpenHands 各自补正式桥接协议文档和 DTO：

1. request schema
2. response schema
3. error schema
4. timeout / cancellation 语义

建议文件：

- `/Users/admin/Desktop/ai-desk/apps/api/api/executors/provider_contracts.py`
- `docs/specs/executor-provider-bridges.md`

### B. 完善 artifact 抽取

Codex：

1. transcript artifact
2. changed-files artifact
3. verification artifact

OpenHands：

1. session log artifact
2. verification artifact
3. workspace output artifact

### C. 完善 failure mapping

统一映射：

1. transport failure
2. provider timeout
3. sandbox denial
4. verification failure
5. partial execution

### D. 增加 live smoke tests

通过环境变量启用：

1. Codex live smoke
2. OpenHands live smoke

默认 CI 不强制，但本地 runbook 必须可执行。

### E. 接 runtime dispatch 闭环

后续要把 runtime task execution 与 executor dispatch 主路径真正打通，而不是仅并行存在。

---

## 3. 验收标准

1. Codex / OpenHands provider contract 有稳定 DTO。
2. verification 不再主要靠 transcript 推断。
3. live smoke 可在本地独立运行。
4. 常见失败类型能被正确映射到 contract。

---

## 4. 建议测试

1. provider 返回 timeout / 4xx / 5xx 时映射正确。
2. verification artifact 缺失时不会伪装成 passed。
3. Codex/OpenHands live smoke 在配置完依赖后能跑通。
4. 产出的 artifact / provenance / evidence 可被 review API 消费。
