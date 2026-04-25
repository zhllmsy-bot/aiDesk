# T4 Memory Backbone 治理补全

- 优先级：`P1`
- 目标：把 memory 从“可写可查”推进到“有治理策略、有检索语义、有生命周期”的正式 backbone

---

## 1. 当前问题

当前 memory 已经不是纯 stub，但仍然不完整：

- `/Users/admin/Desktop/ai-desk/apps/api/api/memory/service.py`
- `/Users/admin/Desktop/ai-desk/apps/api/api/memory/openviking.py`

主要缺口：

1. recall ranking 比较弱，主要按 score/quality 排序。
2. versioning / supersede / decay 还没有。
3. cleanup / retention 没有后台策略。
4. 远端 OpenViking 只做轻量接入，没有可靠错误分类与 fallback policy。
5. memory 与 context assembly 还没闭合。

---

## 2. 技术实施方案

### A. 扩展 memory_records 模型

增加字段：

1. `version`
2. `supersedes_record_id`
3. `stale_at`
4. `retention_policy`
5. `last_recalled_at`
6. `recall_count`

### B. 增加 recall ranking policy

新增策略层：

- `MemoryRankingService`

排序维度：

1. semantic score
2. quality score
3. recency
4. evidence affinity
5. namespace match depth

### C. 增加 write governance policy

新增：

1. duplicate merge
2. supersede older fact
3. decline low-quality noisy writes
4. namespace-specific threshold

### D. 增加 cleanup / maintenance job

新增 maintenance 任务：

1. 标记 stale records
2. 合并 superseded records
3. 清理无效外部引用

### E. OpenViking adapter 加强

补：

1. 网络错误分类
2. retry/backoff
3. partial failure fallback
4. remote write / local DB 双写一致性策略

---

## 3. 验收标准

1. recall 结果排序不再只是简单 score 排序。
2. memory write 支持 version / supersede。
3. maintenance job 能处理 stale / superseded records。
4. OpenViking 不可用时，系统有明确 fallback 与 error surface。

---

## 4. 建议测试

1. 重复写入时 dedup / supersede 生效。
2. recall 在多个 namespace 下排序合理。
3. OpenViking 写失败时，本地记录与错误行为可预期。
4. stale cleanup 不会误删高价值记录。
