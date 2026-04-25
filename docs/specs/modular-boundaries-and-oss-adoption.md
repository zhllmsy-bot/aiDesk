# 模块边界与 OSS 采用策略

更新时间：2026-04-22

## 目标

`ai-desk` 后续演进按“模块化单体（modular monolith）”推进，不再按零散 lane 或临时接线方式扩展。

原则：

- 通用基础设施优先采用 GitHub 上热门、持续维护的开源项目
- 业务差异化能力只保留在 `ai-desk` 自身模块中
- 每个模块自带 `router / service / repository / models / contracts / integrations`
- 模块之间只通过显式 contract 或 application service 调用，不直接跨模块抓内部实现

## 当前问题

当前仓库已经有包级目录，但边界仍未真正收紧，主要问题包括：

- `workflows/definitions/base.py` 同时处理 workflow 状态流转、审批、context 组装、executor dispatch
- `executors/dependencies.py` 直接组装 memory / review / security / context，多模块 wiring 聚集在 execution 包
- `health/router.py` 通过 `memory/openviking.py` 里的 `OpenHandsHealthProbe` 检查 OpenHands，可见 integration 放置错误
- `workflows/dependencies.py` 直接在 runtime 容器里拼 Feishu adapter，通知集成没有独立 integration boundary
- `runtime_full_access_enabled` 是全局配置开关，安全策略和执行策略被进程级状态短路

这些都说明当前更像“分目录的耦合系统”，还不是“按模块构建的系统”。

## 模块划分

建议以业务能力为主，而不是以技术组件为主，目标结构如下：

```text
apps/api/api/modules/
  control_plane/
  runtime/
  execution/
  memory/
  review/
  notifications/
  integrations/
    temporal/
    langgraph/
    openhands/
    mem0/
    feishu/
```

说明：

- `control_plane`：项目、迭代、成员、计划、认证关系
- `runtime`：workflow run、task、attempt、claim、event、projector、recovery
- `execution`：任务派发、provider 选择、执行输入输出 contract
- `memory`：记忆写入、召回、namespace、ranking、governance
- `review`：approval、artifact、evidence、attempt summary
- `notifications`：统一通知领域，不关心具体 Feishu/Slack/provider
- `integrations/*`：所有外部系统接入统一收口，不允许散落在领域模块内部

## OSS 采用策略

以下能力不再建议长期自写。

### 1. Durable orchestration

保留 `Temporal` 作为主调度与 durable runtime。

- GitHub：`temporalio/sdk-python`
- 官方文档：`https://docs.temporal.io/`

理由：

- 这是当前 `ai-desk` 已经接入且最接近最佳实践的一层
- workflow / activities / workers / task queue / retry / signal / event history 语义不值得自研替代

### 2. Agent graph durability

采用 `LangGraph` 官方持久化路径，不再维护手工 checkpoint save/resume 方案。

- GitHub：`langchain-ai/langgraph`
- 官方文档：`https://docs.langchain.com/oss/python/langgraph/durable-execution`

建议：

- 使用官方 checkpointer
- 优先接 `Postgres` 持久化方案
- 将 graph durability 责任交还给 LangGraph，不再由 `RuntimeGraphService` 自行拼 checkpoint state

### 3. Execution runtime / sandbox

采用 `OpenHands` 官方 runtime 架构，不再长期维护自定义 `/api/execute` 桥接协议。

- GitHub：`OpenHands/OpenHands`
- 官方文档：`https://docs.openhands.dev/openhands/usage/architecture/runtime`

建议：

- 直接对齐 OpenHands 的 sandboxed Docker runtime
- 对齐其 client-server runtime 协议与容器镜像管理方式
- 权限、挂载、overlay、plugin、port 暴露等语义以 OpenHands 为准

### 4. Memory backbone

默认推荐采用 `Mem0` 作为外部记忆层；如果未来确实需要“始终可见的 agent core memory block”，再评估 `Letta`。

- GitHub：`mem0ai/mem0`
- 文档：`https://docs.mem0.ai/core-concepts/memory-types`

备选：

- GitHub：`letta-ai/letta`
- 文档：`https://docs.letta.com/guides/core-concepts/memory/memory-blocks`

选择原则：

- `Mem0` 更适合作为“记忆基础设施层”
- `Letta` 更适合作为“带 agent-visible core memory 的 agent 平台”
- `ai-desk` 已经自带 control plane 和 runtime，因此优先 `Mem0`，避免与 Letta 平台能力重叠

## P0

### P0-1 Runtime 模块化收口

- `runtime` 只负责 workflow/task/attempt/claim/event/projector/recovery
- `execution` 不再直接拼 runtime 依赖
- `app.py` 只做 router 注册与模块 wiring

验收：

- `workflow`、`projector`、`recovery` 代码不再从 `execution` / `memory` / `review` 直接抓实现

### P0-2 用官方 LangGraph durability 替代手工 checkpoint

- 下线手工 checkpoint state 结构
- 改用官方 checkpointer + Postgres

验收：

- interrupt / resume / replay 不再依赖自定义 checkpoint dict

### P0-3 用官方 OpenHands runtime 替代自定义 `/api/execute`

- 删除私有 OpenHands bridge DTO
- 对齐 OpenHands runtime 协议与 sandbox 能力

验收：

- 执行器集成只保留 adapter 层，不再自定义 runtime 协议

### P0-4 取消全局 `full access`

- 禁止进程级全局全权限模式作为默认路径
- 改成单次 run 显式 capability grant

验收：

- 安全默认值回到 least privilege
- 测试环境与开发环境不因 `.env.local` 互相污染

## P1

### P1-1 Memory 切到 Mem0

- `memory` 领域保留 namespace / evidence / governance policy
- 真正的 recall / persist / layered memory 交给 `Mem0`

### P1-2 Integration 统一收口

- `OpenHandsHealthProbe` 从 `memory/openviking.py` 挪出
- `Feishu` 接入从 runtime container wiring 中抽离到 `integrations/feishu`
- 所有第三方 health probe 统一归 `integrations/*`

### P1-3 Review 保持自有

`approval / artifact / evidence / attempt summary` 继续由 `ai-desk` 自己持有，不外包。

原因：

- 这是 `ai-desk` 的差异化控制面
- 通用 OSS 很少直接提供与你当前控制面完全匹配的 review surface

## 明确约束

后续新增能力时，禁止以下做法：

- 在已有模块里顺手塞第三方 integration probe
- 在 `dependencies.py` 里横向拼接多个领域服务作为默认写法
- 在 workflow base class 中继续堆 context/security/execution/review 逻辑
- 为通用基础设施继续自研第二套协议

后续新增能力时，必须先回答两个问题：

1. 这是业务模块，还是第三方 integration？
2. 这块能力是否已经有成熟热门 GitHub OSS，可直接采用？

