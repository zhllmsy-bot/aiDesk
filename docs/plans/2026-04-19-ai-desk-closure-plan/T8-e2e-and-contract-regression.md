# T8 端到端集成测试与契约回归

- 优先级：`P2`
- 目标：让前面 7 个任务的结果真正被验证，而不是停留在单点单测

---

## 1. 当前问题

目前测试主要是单元级与局部 API 级：

- `/Users/admin/Desktop/ai-desk/apps/api/tests/test_runtime_lane.py`
- `/Users/admin/Desktop/ai-desk/apps/api/tests/test_be3.py`

还缺：

1. Temporal start path 的端到端验证
2. review durability 的重启后验证
3. live executor / live memory 可选联调验证
4. contract snapshot 回归

---

## 2. 技术实施方案

### A. 增加分层测试集

1. `unit`
2. `integration`
3. `e2e`
4. `live-smoke`

### B. 增加关键 E2E 场景

1. runtime run start -> task execute -> timeline/graph/attempt/review 可读
2. approval required -> resolve -> resume -> complete
3. memory write -> recall -> context assembly -> dispatch
4. app 重启后 review/runtime data 仍可读

### C. 增加 contract snapshot

覆盖：

1. runtime contract
2. execution contract
3. review API response
4. openapi export

### D. 增加 live smoke profile

通过环境变量控制，仅在本地或 staging 跑：

1. Temporal live smoke
2. Codex live smoke
3. OpenHands live smoke
4. OpenViking live smoke

---

## 3. 验收标准

1. 至少有 2 到 3 条跨模块 E2E 路径可跑通。
2. contract 变化会触发 snapshot 差异。
3. live smoke 可独立启用。

---

## 4. 建议测试

1. `/runtime/runs/start` 驱动的全链路测试。
2. approval signal 恢复测试。
3. review durability 重启恢复测试。
4. contracts / openapi snapshot 回归测试。
