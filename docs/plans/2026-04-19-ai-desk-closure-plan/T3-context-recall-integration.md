# T3 ContextBuilder 接正式 Recall / Query Pipeline

- 优先级：`P1`
- 目标：让 ContextBuilder 不再只吃手工字符串数组，而是接正式数据查询与 recall 结果

---

## 1. 当前问题

当前 `ContextBuilderService` 只是结构化拼装器，不是上下文管线：

- `/Users/admin/Desktop/ai-desk/apps/api/api/context/service.py`

问题在于：

1. 输入还是手工拼出来的字符串数组。
2. 没有 project truth / workflow summary / attempts / memory recall 的标准 query service。
3. 没有 token budget / truncation budget / ranking policy。
4. evidence refs 虽然能挂上，但来源链没正式建成。

---

## 2. 技术实施方案

### A. 定义 context query 层

新增：

1. `ProjectContextQueryService`
2. `RuntimeContextQueryService`
3. `MemoryRecallQueryService`
4. `SecurityContextQueryService`

建议文件：

- `/Users/admin/Desktop/ai-desk/apps/api/api/context/query.py`
- `/Users/admin/Desktop/ai-desk/apps/api/api/context/dependencies.py`

### B. 定义标准输入 DTO

不要再让上游自己拼 `list[str]`，改成 typed records：

1. `TaskCoreRecord`
2. `ProjectFactRecord`
3. `RecentAttemptRecord`
4. `MemoryRecallRecord`
5. `SecurityConstraintRecord`

### C. 为 ContextBuilder 增加 ranking / truncation policy

增加：

1. 每层 block 的优先级排序
2. 按 token/字符预算截断
3. 去重策略
4. evidence-preserving truncation

### D. 形成统一 build path

新增一个 facade：

- `ContextAssemblyService`

负责：

1. 查询 project / runtime / memory / security 数据
2. 排序与去重
3. 调用 `ContextBuilderService`
4. 输出 `ContextBundle`

---

## 3. 验收标准

1. executor dispatch 使用的是正式 context assembly path。
2. ContextBuilder 输入不再主要依赖手工字符串数组。
3. truncation / ranking 可测试、可预测。
4. evidence refs 与每个 block 来源对应。

---

## 4. 建议测试

1. project facts + attempts + memory recall 混合输入时，排序稳定。
2. 长文本被截断但 evidence refs 不丢。
3. 无 recall 命中时仍能生成最小上下文。
4. 相同事实重复输入时去重有效。
