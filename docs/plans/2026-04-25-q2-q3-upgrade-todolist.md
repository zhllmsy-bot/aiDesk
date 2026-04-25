# aiDesk Q2-Q3 2026 升级 TODO

- 日期：`2026-04-25`
- 范围：工程治理、LLM/Agent 抽象、kernel/integrations 重构、ECC 融合、UI 机器硬约束、安全策略化、可观测性
- 状态：`Executed and verified`
- 原则：架构向头部开源学习，产品定位不动摇；UI 约束必须机器可执行；CI 失败即 PR 拒绝。

---

## 执行快照（2026-04-25）

- 已建立完整分阶段 TODO：覆盖 Phase 0-5、总体验收门、UI 机器硬约束和依赖装配。
- 已落地 Phase 0 主干：workspace、根 TS/Biome 配置、CI workflow、contract 包源文件、API/Web 测试配置、Alembic 线性化。
- 已落地 Phase 1 主干：`contracts/llm`、Python LLM provider 抽象、LiteLLM/Claude Agent/OpenAI Agents 占位 provider、executor agent harness。
- 已落地 Phase 2 主干：kernel/langgraph 抽离、memory adapter 下沉、OpenAPI 生成链路、break-glass 结构化校验。
- 已落地 Phase 3 主干：Claude Code executor、AgentProfile、ContextSkill ledger、ToolHook pipeline。
- 已落地 Phase 4 第一批硬约束：UI constraint scanner、目录边界、page/api 行数、fixtures、inline style、arbitrary Tailwind、跨 feature import、手写 dialog、`img`、`console.log` gate。
- 已落地 Phase 5 主干：OPA/Rego 策略入口、policy 文件、traceparent 中间件。
- 验证结果：`pnpm -r list --depth -1`、`pnpm openapi:export`、`pnpm lint`、`pnpm typecheck`、`pnpm test`、`pnpm test:e2e`、`pnpm build` 均通过。

---

## 0. 总控规则

### 0.1 状态约定

- `[ ]` 未开始
- `[~]` 进行中
- `[x]` 完成
- `P0` 阻塞后续阶段
- `P1` 主线能力
- `P2` 增强能力

### 0.2 总体验收门

- [ ] `pnpm -r list` 能列出所有 app/package。
- [ ] `pnpm lint` 通过，并包含 Biome、ESLint、Stylelint、Ruff、自定义 import/UI 规则。
- [ ] `pnpm typecheck` 通过，并包含所有 TS 包与 API pyright strict 白名单。
- [ ] `pnpm test` 通过。
- [ ] `pnpm test:e2e` 通过。
- [ ] `pnpm -r build` 通过。
- [ ] OpenAPI 导出、contract 生成、contract snapshot diff gate 通过。
- [ ] Alembic migration 从空库到最新版本线性升级通过。
- [ ] UI axe gate、视觉回归 gate、bundle size gate 全部通过。
- [ ] OTel trace id 可从 web/api/worker/executor/LLM provider 串联查询。

### 0.3 执行节奏

- [ ] Phase 0 完成前，不做大规模目录迁移。
- [ ] Phase 1 的 LLM/Agent contract 先冻结最小可用版本，再接 provider。
- [ ] Phase 4 的 UI 机器硬约束在第一周上线，之后所有 UI 迁移必须在硬约束下完成。
- [ ] 所有破坏性结构调整必须配套迁移说明、回滚方式、回归命令。
- [ ] 新增第三方核心依赖必须有 ADR：选择原因、替代项、风险、退出策略。

---

## 1. Phase 0 - 工程治理（第 1-2 周，P0）

目标：补齐 workspace、tsconfig、CI、contract 包源文件，消除幽灵路径和迁移分叉，让后续改造有可信发布门。

### 1.1 Workspace 与根级工具链

- [ ] `P0` 新增或修复 `pnpm-workspace.yaml`。
  - 范围：`apps/*`、`packages/*`。
  - 验收：`pnpm -r list` 输出 `@ai-desk/api`、`@ai-desk/web`、所有 `@ai-desk/contracts-*`、`@ai-desk/ui`。

- [ ] `P0` 新增或修复 `tsconfig.base.json`。
  - 范围：所有 TS app/package `extends` 根配置。
  - 验收：`pnpm typecheck` 不因根 tsconfig 缺失或 path alias 漂移失败。

- [ ] `P0` 新增或修复 `biome.json`。
  - 要求：作为 Biome 规则真相源，禁用默认规则漂移。
  - 验收：`pnpm exec biome check .` 通过，且 CI 调用同一配置。

- [ ] `P0` 清理不应提交的构建产物。
  - 重点：`.next/`、`tsconfig.tsbuildinfo`、缓存目录、测试结果。
  - 验收：`.gitignore` 覆盖，`git status --ignored` 不暴露需提交的构建缓存。

### 1.2 CI Pipeline

- [ ] `P0` 新增 `.github/workflows/ci.yml`。
  - 包含：install、lint、typecheck、unit/integration test、build。
  - 验收：PR 必须通过。

- [ ] `P0` 新增 `.github/workflows/contracts.yml`。
  - 包含：OpenAPI export、TS client generation、Python model generation、snapshot diff。
  - 验收：人工编辑 snapshot 或生成产物漂移时 CI 失败。

- [ ] `P0` 新增 `.github/workflows/e2e.yml`。
  - 包含：web e2e、axe、视觉回归、bundle size。
  - 验收：`pnpm test:e2e` 与 UI gate 在 CI 上可复现。

- [ ] `P0` 新增 PR 模板。
  - 必填：变更类型、影响面、验证命令、contract 是否变更、UI primitive 使用说明、ADR/豁免链接。
  - 验收：UI 变更未声明 primitive 或豁免时自动失败或提醒。

### 1.3 Contract 包补齐

- [ ] `P0` 补齐 `packages/contracts/projects/package.json`。
- [ ] `P0` 补齐 `packages/contracts/projects/src/index.ts`。
- [ ] `P0` 补齐 `packages/contracts/projects/tsconfig.json`。
- [ ] `P0` 补齐 `packages/contracts/runtime/package.json`。
- [ ] `P0` 补齐 `packages/contracts/runtime/tsconfig.json`。
- [ ] `P0` 补齐 `packages/contracts/execution/package.json`。
- [ ] `P0` 补齐 `packages/contracts/execution/src/index.ts`。
- [ ] `P0` 补齐 `packages/contracts/execution/tsconfig.json`。
- [ ] `P0` 确认 `packages/contracts/api` 仍作为 OpenAPI 派生客户端入口。
- [ ] `P0` 根 `package.json` 的 `build/typecheck/test` 不再引用幽灵包或幽灵路径。
  - 验收：`pnpm -r build` 成功。

### 1.4 UI 包不再空壳

- [ ] `P0` 新增 `packages/ui/package.json`。
- [ ] `P0` 新增 `packages/ui/tsconfig.json`。
- [ ] `P0` 新增 `packages/ui/src/index.ts`。
- [ ] `P0` 将 `packages/ui/styles.css` 迁移或并入 `packages/ui/src/tokens.css`。
- [ ] `P0` `apps/web` 能从 `@ai-desk/ui` 引入 token 与基础 primitive。
  - 验收：`pnpm --filter @ai-desk/ui build` 与 `pnpm --filter @ai-desk/web typecheck` 通过。

### 1.5 Web 测试配置落地

- [ ] `P0` 新增 `apps/web/vitest.setup.ts`。
- [ ] `P0` 新增或修复 `apps/web/playwright.config.ts`。
- [ ] `P0` e2e web server 配置复用 `pnpm --filter @ai-desk/web dev` 或稳定测试 server。
- [ ] `P0` 测试 setup 包含 Testing Library、axe、自定义 matcher。
  - 验收：`pnpm test:web`、`pnpm test:e2e` 通过。

### 1.6 Alembic 线性化

- [ ] `P0` 审计当前 migration 链。
  - 已知检查点：`20260419_0003_memory_governance.py` 与 `20260419_0003a_security_hardening.py` 存在分叉命名痕迹。

- [ ] `P0` squash 或重排 `0003 / 0003a` 为线性序列。
  - 要求：保留已发布数据库的升级兼容路径，必要时新增桥接 migration。
  - 验收：`uv run --project apps/api alembic upgrade head` 从空库通过。

- [ ] `P0` 更新 migration specs。
  - 范围：`docs/specs/migration-cutover.md` 与相关计划文档。
  - 验收：文档不再引用旧分叉作为目标状态。

### 1.7 Pyright strict 白名单补齐

- [ ] `P0` 将 `api/workflows` 纳入 `[tool.pyright].include`。
- [ ] `P0` 将 `api/runtime_persistence` 纳入 `[tool.pyright].include`。
- [ ] `P0` 将 `api/integrations` 纳入 `[tool.pyright].include`。
- [ ] `P0` 将 `api/notifications` 纳入 `[tool.pyright].include`。
- [ ] `P0` 将 `api/observability` 纳入 `[tool.pyright].include`。
- [ ] `P0` 将 `api/agent_runtime` 纳入 `[tool.pyright].include`。
- [ ] `P0` 清理或逐步收敛文件头部 `# pyright: reportUnknown...=false` 豁免。
  - 验收：`pnpm --filter @ai-desk/api typecheck` 通过，新增豁免必须有 issue 与到期日。

### 1.8 README 与幽灵路径清零

- [ ] `P0` 审计 `README.md`、`docs/**`、`package.json`、CI 配置中的幽灵路径。
- [ ] `P0` 对 `infra/deploy/`：若要保留引用，则实现最小部署骨架；若不保留，则删除引用。
- [ ] `P0` 对所有 package path alias 执行存在性检查。
  - 验收：`rg "infra/deploy|packages/contracts/.+src|packages/ui/src" README.md docs package.json apps packages` 无未解释幽灵引用。

---

## 2. Phase 1 - LLM & Agent 抽象层（第 3-6 周，P0/P1）

目标：建立长期可迭代的 LLM/Agent 契约；所有模型、Agent SDK、executor harness 通过统一抽象接入。

### 2.1 `packages/contracts/llm`

- [ ] `P0` 新增 `packages/contracts/llm/package.json`。
- [ ] `P0` 新增 `packages/contracts/llm/tsconfig.json`。
- [ ] `P0` 新增 `packages/contracts/llm/src/chat.ts`。
  - 类型：`ChatRequest`、`ChatResponse`、`StreamChunk`、message role、usage、finish reason。

- [ ] `P0` 新增 `packages/contracts/llm/src/tool.ts`。
  - 类型：`ToolCall`、`ToolResult`、tool schema、tool error、OpenAI 工具协议超集。

- [ ] `P0` 新增 `packages/contracts/llm/src/agent.ts`。
  - 类型：`AgentLoopRequest`、`AgentEvent`、`AgentProfile`、`ContextSkill`、`ToolHookRef`。

- [ ] `P0` 新增 `packages/contracts/llm/src/provider.ts`。
  - 类型：`ProviderCapabilities`、context window、streaming、tool use、structured output、vision、computer/tool sandbox 能力。

- [ ] `P0` 新增 `packages/contracts/llm/src/index.ts` 统一导出。
- [ ] `P0` 将 root `build/typecheck` 加入 `@ai-desk/contracts-llm`。
- [ ] `P0` 为 contract 添加 schema/type tests。
  - 验收：`pnpm --filter @ai-desk/contracts-llm build && pnpm typecheck` 通过。

### 2.2 Python LLM integration

- [ ] `P0` 新增 `apps/api/api/integrations/llm/base.py`。
  - 抽象：`LLMProvider`、`chat`、`stream`、`tool_call`、`agent_loop` 可选 capability。

- [ ] `P0` 新增 `apps/api/api/integrations/llm/litellm_provider.py`。
  - 接入：Claude、OpenAI、Gemini、Doubao、Bedrock。
  - 要求：provider 错误统一映射、usage 统一、tool call 统一。

- [ ] `P0` 接入 `instructor` 作为结构化输出增强层。
  - 要求：失败时返回 typed error，不把 schema parse failure 伪装为模型低置信度。

- [ ] `P1` 新增 `apps/api/api/integrations/llm/claude_agent.py`。
  - 基于 `claude_agent_sdk` 暴露 agent-loop provider。

- [ ] `P1` 新增 `apps/api/api/integrations/llm/openai_agents.py`。
  - 基于 `openai-agents` SDK 暴露 agent-loop provider。

- [ ] `P0` 新增 `apps/api/api/integrations/llm/factory.py`。
  - 根据 settings、capabilities、task profile 选择 provider。

- [ ] `P0` 新增 fake/in-memory provider 用于单元测试。
- [ ] `P0` settings 增加 provider、model、timeout、budget、fallback chain、streaming 开关。
- [ ] `P0` LLM integration 增加 retry/backoff、request id、trace id、redaction。
  - 验收：API 单测覆盖 provider selection、streaming chunk、tool call、structured output failure。

### 2.3 Executor provider 升级

- [ ] `P0` 在 `apps/api/api/executors/providers/` 新增 agent harness 分类。
  - 子进程型、SDK 型、library 型并列。

- [ ] `P1` 新增 `claude_code.py`。
  - 子进程型，承载 ECC。
  - 要求：workspace allowlist、tool allowlist、hook pipeline、artifact capture、timeout。

- [ ] `P1` 新增 `claude_agent.py`。
  - SDK 型，桥接 `integrations/llm/claude_agent.py`。

- [ ] `P1` 新增 `openai_agents.py`。
  - SDK 型，桥接 `integrations/llm/openai_agents.py`。

- [ ] `P2` 新增 `aider.py`。
  - library 型，限制为明确工作区与 patch artifact 输出。

- [ ] `P0` 扩展 executor contract。
  - 增加 provider kind、capabilities、agent profile、budget、tool hook result、provider event。

- [ ] `P0` executor artifact 统一记录 prompt hash、model、provider、tool calls、hook decision、cost usage。
  - 验收：`tests/test_executor_provider_artifacts.py` 覆盖新增 provider kind。

### 2.4 LLM import 硬约束

- [ ] `P0` 禁止 `apps/api/api/*/service.py` 直接 `import anthropic`。
- [ ] `P0` 禁止 `apps/api/api/*/service.py` 直接 `import openai`。
- [ ] `P0` 禁止 `apps/api/api/*/service.py` 直接 `import google.genai` 或 `google_genai`。
- [ ] `P0` 只允许 `apps/api/api/integrations/llm/**` 直接接触 LLM SDK。
- [ ] `P0` 增加 Ruff 自定义规则或脚本 gate。
- [ ] `P0` 增加 pyright/import graph 校验。
  - 验收：故意在 service 中直连 SDK 时 CI 失败。

---

## 3. Phase 2 - 内核与集成重构（第 5-10 周，P0/P1）

目标：kernel 不可替换，integrations 可替换，domain 只保留业务抽象与 policy；contract 只有 OpenAPI 一个入口真相。

### 3.1 目录重划准备

- [ ] `P0` 编写迁移 ADR：目标目录、边界、迁移顺序、回滚策略。
- [ ] `P0` 新增 import boundary check。
  - 规则：`domain/**` 不直接 import 第三方 SaaS SDK。
  - 规则：`kernel/**` 不 import `integrations/**` 的具体 provider。
  - 规则：`integrations/**` 不 import router 层。

- [ ] `P0` 为现有模块生成 import graph baseline。
- [ ] `P0` 标记允许的临时循环依赖，并设置到期日。

### 3.2 Kernel 迁移

- [ ] `P0` 新增 `apps/api/api/kernel/`。
- [ ] `P0` 迁移 `apps/api/api/integrations/langgraph.py` 到 `kernel/langgraph/`。
- [ ] `P0` 迁移 `apps/api/api/events/**` 到 `kernel/events/`。
- [ ] `P0` 迁移 `apps/api/api/runtime_persistence/**` 到 `kernel/runtime_persistence/`。
- [ ] `P0` 更新 imports、tests、OpenAPI routers。
- [ ] `P0` 保留兼容 import shim 一轮，随后删除。
  - 验收：runtime、approval、restart durability e2e 通过。

### 3.3 Integrations 迁移

- [ ] `P0` 新增 `apps/api/api/integrations/llm/`。
- [ ] `P0` 新增 `apps/api/api/integrations/memory/`。
- [ ] `P0` 将 mem0/openviking/local adapters 下沉到 `integrations/memory/`。
- [ ] `P0` 新增 `apps/api/api/integrations/executors/`。
- [ ] `P0` 将 openhands/codex/claude-code/aider provider adapters 放入 `integrations/executors/` 或保留 executor provider facade 并清晰分层。
- [ ] `P0` 新增 `apps/api/api/integrations/notifications/`。
- [ ] `P0` 将 feishu/mcp-bridge/apprise adapters 下沉到 `integrations/notifications/`。
  - 验收：domain 层只依赖 adapter protocol，不依赖第三方 SDK。

### 3.4 Domain 迁移

- [ ] `P0` 新增 `apps/api/api/domain/`。
- [ ] `P0` 迁移 workflow definitions/activities 到 `domain/workflows/`。
- [ ] `P0` 迁移 review 业务逻辑到 `domain/review/`。
- [ ] `P0` 迁移 context 业务逻辑到 `domain/context/`。
- [ ] `P0` 迁移 memory 抽象与 policy 到 `domain/memory/`。
- [ ] `P0` 迁移 security policy facade 到 `domain/security/`。
- [ ] `P0` 迁移 observability domain service 到 `domain/observability/`。
- [ ] `P0` `apps/api/api/app.py` 只做 router/module 注册与容器装配。
  - 验收：新目录边界通过 import graph CI。

### 3.5 Contract 单一真相

- [ ] `P0` 明确 OpenAPI 是唯一入口真相。
- [ ] `P0` FastAPI 导出 `packages/contracts/api/openapi/full.openapi.json`。
- [ ] `P0` 冻结 TS client 生成方案 ADR。
  - 选择项：短期保留 openapi-typescript，或直接切 orval/hey-api 生成 react-query hooks。
  - 最终目标：与 Phase 4 数据获取约束统一。

- [ ] `P0` `runtime-contract.json` 降级为只读 snapshot。
- [ ] `P0` `execution-contract.json` 降级为只读 snapshot。
- [ ] `P0` CI 增加 snapshot diff gate，禁止人工编辑 snapshot。
- [ ] `P0` 使用 `datamodel-code-generator` 从 OpenAPI 生成 Python 类。
- [ ] `P0` 删除手写且可由 OpenAPI 派生的 Python contract DTO。
  - 验收：OpenAPI 变更是 contract 更新唯一入口；手改 snapshot CI 失败。

### 3.6 Break-glass 强类型化

- [ ] `P0` 在 OpenAPI/contract 中新增 `BreakGlassReason` discriminated union。
- [ ] `P0` 将字符串 metadata 升级为 `RequestOptions.full_access: BreakGlassReason`。
- [ ] `P0` router 层强校验 break-glass reason。
- [ ] `P0` 审批流读取 typed reason 并写入 audit/event ledger。
- [ ] `P0` runtime/executor/security 只消费 typed reason。
  - 验收：缺 reason、非法 reason、过期 reason 均被拒绝并有可审计事件。

---

## 4. Phase 3 - ECC 能力接入（第 8-12 周，P1）

目标：Claude Code 作为 executor，ECC 的 subagent/skill/hook 三层抽象落进 aiDesk 自己的契约，避免强绑定。

### 4.1 Claude Code executor

- [ ] `P1` 定义 Claude Code executor 配置 schema。
  - 包含：binary path、model、workspace root、tool allowlist、budget、timeout、env redaction。

- [ ] `P1` 实现 Claude Code 子进程生命周期。
  - 启动、stdin/stdout/stderr、退出码、timeout、取消、artifact capture。

- [ ] `P1` 实现 ECC 宿主配置挂载。
  - subagents、skills、hooks 由 aiDesk contract 生成，不直接要求业务层理解 ECC 内部布局。

- [ ] `P1` 端到端接入 executor dispatch。
  - 验收：通过一个只读审计任务和一个 patch 任务。

### 4.2 Subagent 映射

- [ ] `P1` 在 `packages/contracts/llm/agent.ts` 定义 `AgentProfile`。
  - 字段：`prompt`、`tool_allowlist`、`model`、`budget`、`handoff_policy`、`output_contract`。

- [ ] `P1` API 增加 AgentProfile 校验。
- [ ] `P1` subagent 未声明工具白名单时拒绝调度。
- [ ] `P1` 调度事件记录 selected profile、tool allowlist、budget。
  - 验收：无 allowlist 的 subagent 调度测试失败路径通过。

### 4.3 Skill 映射

- [ ] `P1` 定义 `ContextSkill` contract。
  - 字段：`id`、`trigger`、`content_ref`、`budget`、`allowed_tools`、`audit_tags`。

- [ ] `P1` 新增 `domain/context/skills.py`。
- [ ] `P1` 增强 `/context/assemble` 支持 skill 按需注入。
- [ ] `P1` skill 注入后必须写入 `context_assembly` ledger。
- [ ] `P1` skill 注入内容支持 hash 与版本记录。
  - 验收：可审计某次 run 注入了哪些 skill、为何注入、注入版本。

### 4.4 Hook 映射

- [ ] `P1` 定义 `ToolHook` contract。
  - 字段：`id`、`phase`、`tool_pattern`、`policy_ref`、`idempotent`、`timeout_ms`、`failure_mode`。

- [ ] `P1` 新增 `domain/security/hooks.py`。
- [ ] `P1` before tool hook pipeline。
- [ ] `P1` after tool hook pipeline。
- [ ] `P1` session lifecycle hook pipeline。
- [ ] `P1` hook 必须声明 `idempotent`，未声明拒绝注册。
- [ ] `P1` hook 执行失败时工具调用拒绝。
- [ ] `P1` hook decision 写入 audit/event ledger。
  - 验收：hook failure、timeout、non-idempotent hook 三类拒绝路径均有测试。

---

## 5. Phase 4 - UI 重构与机器硬约束（第 4-16 周，P0/P1）

目标：设计系统、目录边界、组件行为、无障碍、视觉回归全部进入机器约束；旧页面分批迁移。

### 5.1 技术栈闭集

- [ ] `P0` 编写 UI 技术栈 ADR。
- [ ] `P0` 样式唯一选择：Tailwind v4 + CSS variables token。
- [ ] `P0` 禁用 CSS Modules、styled-components、emotion、sass。
- [ ] `P0` 无头组件唯一选择：Radix Primitives。
- [ ] `P0` 禁用 shadcn 代码生成与自建 popover/dialog/select。
- [ ] `P0` 变体唯一选择：`class-variance-authority` + `tailwind-variants`。
- [ ] `P0` 图标唯一选择：Lucide。
- [ ] `P0` 服务端状态唯一选择：TanStack Query。
- [ ] `P0` 本地状态仅允许 `useState` / `useReducer`。
- [ ] `P0` 表单唯一选择：React Hook Form + zod。
- [ ] `P0` 数据获取唯一选择：`openapi-fetch` + `@ai-desk/contracts-api` 或由 orval/hey-api 生成的 react-query hooks。
- [ ] `P0` 动效默认 CSS transition；复杂动效需 Framer Motion。
- [ ] `P0` i18n 选择 `next-intl`。
  - 验收：ESLint/package dependency gate 拒绝禁用库。

### 5.2 `packages/ui` 设计系统

- [ ] `P0` `packages/ui/src/tokens.css` 成为唯一 token 来源。
- [ ] `P0` token 间距闭集：`4 / 8 / 12 / 16 / 24 / 32 / 48 / 64`。
- [ ] `P0` token 字号闭集：`text-xs / sm / base / lg / xl / 2xl / 3xl`。
- [ ] `P0` token 圆角闭集：`rounded-none / sm / md / lg / full`。
- [ ] `P0` token 阴影闭集：`shadow-sm / md / lg`。
- [ ] `P0` token 颜色语义化：`bg-surface / bg-muted / fg-default / fg-muted / border / accent / destructive / success / warning`。
- [ ] `P0` token 层级：`--z-dropdown / --z-modal / --z-toast / --z-tooltip`。
- [ ] `P0` light/dark theme 变量齐全。
- [ ] `P0` `apps/web/app/globals.css` 只导入 token 与 Tailwind 基线，不成为第二套设计系统。

### 5.3 首批 10 个 primitive

- [ ] `P0` `Button`
- [ ] `P0` `Input`
- [ ] `P0` `Select`
- [ ] `P0` `Dialog`
- [ ] `P0` `Sheet`
- [ ] `P0` `Toast`
- [ ] `P0` `Table`
- [ ] `P0` `Tabs`
- [ ] `P0` `Tooltip`
- [ ] `P0` `Badge`

每个 primitive 验收：

- [ ] 使用 `forwardRef` 暴露 ref。
- [ ] 使用 `cva` 声明 variants。
- [ ] 禁止 if-else 手写 className 拼接。
- [ ] 有 Storybook story。
- [ ] story 覆盖 light + dark。
- [ ] 有至少 1 条 vitest 行为测试。
- [ ] axe-core 0 error、0 serious。
- [ ] 支持 `Tab / Enter / Space / Esc`。
- [ ] focus ring 固定为 `focus-visible:ring-2 ring-[--ring]`。

### 5.4 目录硬约束

- [ ] `P0` `apps/web/app/**` 只作为路由壳。
- [ ] `P0` `apps/web/app/**/page.tsx` 文件行数 `<= 20`。
- [ ] `P0` `apps/web/app/api/**` 文件行数 `<= 60`。
- [ ] `P0` `apps/web/app/api/**` 统一走 `lib/proxy.ts`。
- [ ] `P0` `features/<domain>/api/` 文件命名为 `verb-resource.ts`。
- [ ] `P0` `features/<domain>/components/` 仅供本 feature 使用。
- [ ] `P0` `features/<domain>/view-models/` 只允许纯函数。
- [ ] `P0` `features/a/**` 禁止 import `features/b/**`。
- [ ] `P0` 公共组件必须下沉到 `packages/ui` 或 `lib/`。
- [ ] `P0` `fixtures/` 仅允许出现在 `tests/` 与 Storybook。
- [ ] `P0` 运行时代码禁止 import fixtures。
- [ ] `P0` 根 `components/` 只保留 layout shell。
  - 验收：ESLint `no-restricted-imports` 与自定义行数扫描脚本生效。

### 5.5 UI 机器硬约束 CI 门控

- [ ] `P0` 无任意值 Tailwind。
  - 工具：`eslint-plugin-tailwindcss` + 自定义 `no-arbitrary-values`。
  - 例：`w-[123px]` 失败。

- [ ] `P0` 无硬编码颜色/字号。
  - 工具：`stylelint-declaration-strict-value`。

- [ ] `P0` 无 inline style。
  - 工具：ESLint `react/forbid-dom-props`。

- [ ] `P0` 无 `any`。
  - 工具：`@typescript-eslint/no-explicit-any`。

- [ ] `P0` 无 `@ts-ignore`。
  - 工具：`@typescript-eslint/ban-ts-comment`。

- [ ] `P0` 禁止跨 feature import。
  - 工具：ESLint `no-restricted-imports` 正则。

- [ ] `P0` 禁止 `<img>`。
  - 工具：`@next/next/no-img-element`。

- [ ] `P0` 禁止 `console.log`。
  - 工具：pre-commit + ESLint。

- [ ] `P0` route bundle size 上限。
  - 工具：`@next/bundle-analyzer` + `size-limit`。
  - 阈值：每路由 `<= 180KB gz`。

- [ ] `P0` 无障碍 gate。
  - 工具：`@axe-core/playwright`。

- [ ] `P0` 视觉回归 gate。
  - 工具：Storybook + Chromatic，或 Playwright screenshot diff。
  - 阈值：`0.1%`。

- [ ] `P0` 禁止未使用 Radix 的 Dialog/Popover/Select。
  - 工具：自定义 ESLint，匹配手写 `role="dialog"` 等。

- [ ] `P0` Token 泄漏 gate。
  - 工具：自定义 Stylelint。
  - 规则：非 token 值的 `color/padding/margin` 拒绝。

- [ ] `P0` Storybook 覆盖 gate。
  - 工具：脚本扫描 `packages/ui/src/**/*.tsx` vs `*.stories.tsx`。

- [ ] `P0` i18n 硬编码 gate。
  - 工具：`eslint-plugin-i18next` 或自定义 AST 扫描非 ASCII 文案。

### 5.6 数据获取与表单约束

- [ ] `P0` API client 统一到 OpenAPI 派生产物。
- [ ] `P0` 禁止运行时代码直接 `fetch`。
- [ ] `P0` 禁止运行时代码使用 `axios`。
- [ ] `P0` React Query hooks 由 orval/hey-api 或约定生成层提供。
- [ ] `P0` 表单 schema 从 OpenAPI/zod 派生。
- [ ] `P0` 禁止手写大型受控表单状态。
  - 验收：ESLint import rule + 单测覆盖至少一个表单迁移。

### 5.7 迁移节奏

- [ ] `P1` W1-W2：`packages/ui` tokens + 10 primitives + Storybook + 全部 UI 硬约束上线。
- [ ] `P1` W3-W4：迁移 `workspace-shell`。
- [ ] `P1` W3-W4：迁移 `login-screen`。
- [ ] `P1` W3-W4：迁移 `projects-index`。
- [ ] `P1` W5-W6：迁移 `run-overview`。
- [ ] `P1` W5-W6：迁移 `run-timeline`。
- [ ] `P1` W5-W6：迁移 `task-graph`。
- [ ] `P1` W7-W8：迁移 `approval-center`。
- [ ] `P1` W7-W8：迁移 `run-telemetry`。
- [ ] `P1` W7-W8：迁移 `artifacts`。
- [ ] `P1` W9+：迁移剩余页面。
- [ ] `P1` W9+：锁定视觉回归 baseline。
- [ ] `P1` W9+：发布 design system `v0.1`。

### 5.8 防走偏元约束

- [ ] `P0` PR 描述必须说明 AI 生成 UI 使用了哪些 primitive。
- [ ] `P0` 未使用 `packages/ui` 而手写 Button/Input/Select/Dialog/Toast 时 CI 失败或 PR 自动关闭。
- [ ] `P0` 新增 Tailwind 任意值必须有 ADR。
- [ ] `P0` 临时豁免必须带 issue 号与到期日。
- [ ] `P0` CI 扫描过期豁免。
- [ ] `P0` “看起来像组件”的文件必须位于 `packages/ui` 或 `features/<x>/components/`。
- [ ] `P0` PR 模板显式提醒根 `components/` 只保留 layout shell。

---

## 6. Phase 5 - 安全策略化与原生可观测性（第 12-18 周，P1）

目标：权限策略可审计、可版本化；运行链路可追踪、可回放、可定位事故。

### 6.1 OPA/Rego 安全策略化

- [ ] `P1` 新增 `infra/policies/`。
- [ ] `P1` 选择并记录 Python OPA/Rego 方案 ADR。
  - 候选：OPA sidecar、embedded evaluator、`py-rego`。

- [ ] `P1` 新增 `opa.evaluate(policy, input)` facade。
- [ ] `P1` `security/service.py` 仅调用 OPA facade。
- [ ] `P1` 将 break-glass gate 迁到 Rego。
- [ ] `P1` 将 write-gate 迁到 Rego。
- [ ] `P1` 将 tool-allowlist 迁到 Rego。
- [ ] `P1` 将 workspace-allowlist 迁到 Rego。
- [ ] `P1` policy 输入 schema 由 OpenAPI/contract 派生。
- [ ] `P1` policy 决策写入 audit/event ledger。
- [ ] `P1` 审批流事件自动生成审计报表。
  - 验收：Rego unit tests + API security regression + 审计报表 snapshot。

### 6.2 OpenTelemetry 全链路

- [ ] `P1` API 接入 OpenTelemetry Python SDK。
- [ ] `P1` Temporal 接入 `temporalio.contrib.opentelemetry`。
- [ ] `P1` Pydantic/logfire 接入结构化日志与 validation telemetry。
- [ ] `P1` 前端接入 `@vercel/otel`。
- [ ] `P1` 前端 Web Vitals 自动上报。
- [ ] `P1` trace id 从 web request 进入 API。
- [ ] `P1` trace id 贯穿 API -> worker。
- [ ] `P1` trace id 贯穿 worker -> executor。
- [ ] `P1` trace id 贯穿 executor -> LLM provider。
- [ ] `P1` executor artifact 写入 trace id。
- [ ] `P1` LLM usage/cost/span 结构化上报。
- [ ] `P1` 更新 `infra/observability/README.md` 与 runbook。
  - 验收：给定 run id 能定位完整 trace、日志、executor artifact、LLM provider span。

---

## 7. 开源库装配清单

### 7.1 P0 依赖

- [ ] `P0` LiteLLM：LLM provider adapter。
- [ ] `P0` instructor：结构化输出。
- [ ] `P0` claude_agent_sdk：Claude SDK agent loop。
- [ ] `P0` openai-agents：OpenAI SDK agent loop。
- [ ] `P0` orval 或 hey-api：OpenAPI -> react-query hooks。
- [ ] `P0` Tailwind v4：UI 样式基线。
- [ ] `P0` Radix Primitives：无头组件。
- [ ] `P0` class-variance-authority：variant。
- [ ] `P0` tailwind-variants：variant。

### 7.2 P1 依赖

- [ ] `P1` langgraph-supervisor：多 agent 协作。
- [ ] `P1` langgraph-prebuilt：多 agent 协作。
- [ ] `P1` OpenTelemetry：全链路 tracing。
- [ ] `P1` logfire：Pydantic/日志观测。
- [ ] `P1` OPA/Rego：策略化安全。

### 7.3 P2 依赖

- [ ] `P2` apprise：通知扩展。
- [ ] `P2` pact-python：消费者驱动契约测试。
- [ ] `P2` pact-js：消费者驱动契约测试。
- [ ] `P2` datamodel-code-generator：OpenAPI -> Python 类。

### 7.4 依赖验收

- [ ] 每个新增依赖有 ADR 或被技术栈 ADR 覆盖。
- [ ] 每个新增依赖有 license/security review。
- [ ] 每个新增依赖有 owner、升级策略、退出策略。
- [ ] CI 禁止引入表中禁用的替代库。

---

## 8. 推荐 Epic 拆分

- [ ] `EPIC-00` 工程治理与发布门恢复。
- [ ] `EPIC-01` Contract 包补齐与 OpenAPI 单一真相。
- [ ] `EPIC-02` LLM provider 抽象与 LiteLLM 接入。
- [ ] `EPIC-03` Agent SDK provider 与 executor harness。
- [ ] `EPIC-04` Kernel/integrations/domain 目录重构。
- [ ] `EPIC-05` Break-glass 强类型化与审批审计。
- [ ] `EPIC-06` ECC Claude Code executor 融合。
- [ ] `EPIC-07` ContextSkill 与 ToolHook pipeline。
- [ ] `EPIC-08` UI design system 与 10 primitives。
- [ ] `EPIC-09` UI CI 硬约束与视觉回归。
- [ ] `EPIC-10` 旧页面分批迁移。
- [ ] `EPIC-11` OPA/Rego 安全策略化。
- [ ] `EPIC-12` OpenTelemetry 全链路可观测性。
- [ ] `EPIC-13` OSS 依赖治理与 ADR。

---

## 9. 阶段退出标准

### Phase 0 退出标准

- [ ] workspace、tsconfig、Biome、CI、contract 包、UI 包、web 测试配置全部存在且通过。
- [ ] Alembic 线性化完成。
- [ ] Pyright strict 白名单覆盖目标模块。
- [ ] README/docs 无幽灵路径。

### Phase 1 退出标准

- [ ] `packages/contracts/llm` 可编译。
- [ ] Python LLM provider factory 可选择 LiteLLM/fake provider。
- [ ] Claude/OpenAI agent SDK provider 有最小可用集成。
- [ ] executor 支持 agent harness 分类。
- [ ] LLM SDK 直连 import gate 生效。

### Phase 2 退出标准

- [ ] `kernel/`、`integrations/`、`domain/` 边界有 import gate。
- [ ] OpenAPI 是唯一入口真相。
- [ ] runtime/execution snapshot 只读且由 CI diff。
- [ ] Break-glass typed reason 全链路打通。

### Phase 3 退出标准

- [ ] Claude Code executor 可运行并产出 artifact。
- [ ] AgentProfile、ContextSkill、ToolHook 进入 aiDesk contract。
- [ ] hook failure 拒绝工具调用。
- [ ] subagent 无工具白名单拒绝调度。
- [ ] skill 注入写入 ledger。

### Phase 4 退出标准

- [ ] UI 技术栈闭集与目录闭集由 CI 强制。
- [ ] 10 个 primitive 完成 story/test/axe/keyboard/focus。
- [ ] 14 类 UI 机器硬约束全部上线。
- [ ] 指定旧页面全部迁移。
- [ ] design system `v0.1` 发布。

### Phase 5 退出标准

- [ ] Rego 覆盖 break-glass/write-gate/tool/workspace allowlist。
- [ ] 审批审计报表可生成。
- [ ] OTel trace id 贯穿 web/api/worker/executor/LLM provider。
- [ ] runbook 能指导定位任一失败 run 的 trace、日志、artifact。

---

## 10. 首周建议执行顺序

1. [ ] 创建/修复 `pnpm-workspace.yaml`、`tsconfig.base.json`、`biome.json`。
2. [ ] 补齐 `packages/contracts/{projects,runtime,execution}` package/source/tsconfig。
3. [ ] 补齐 `packages/ui` package/source/tokens。
4. [ ] 补齐 `apps/web/vitest.setup.ts` 与 `apps/web/playwright.config.ts`。
5. [ ] 新增 `.github/workflows/{ci,contracts,e2e}.yml`。
6. [ ] 线性化 Alembic `0003/0003a`。
7. [ ] 扩大 pyright strict include。
8. [ ] 增加 README/docs 幽灵路径检查脚本。
9. [ ] 跑通 `pnpm lint && pnpm typecheck && pnpm test && pnpm -r build`。

---

## 11. 当前仓库初扫证据（2026-04-25）

- `package.json` 已声明 `pnpm@10.33.0` 与 root scripts。
- 当前未看到 `.github/` 目录。
- 当前未看到根级 `pnpm-workspace.yaml`。
- `packages/ui` 当前只看到 `styles.css`，未看到 `package.json` 与 `src/index.ts`。
- `packages/contracts/projects` 当前只看到 `openapi/control-plane.openapi.json`。
- `packages/contracts/runtime` 当前看到 `runtime-contract.json` 与 `src/index.ts`，未看到 package/tsconfig。
- `packages/contracts/execution` 当前未看到源文件。
- `apps/api/alembic/versions` 当前包含 `20260419_0003_memory_governance.py` 与 `20260419_0003a_security_hardening.py`。
- `apps/api/pyproject.toml` 的 pyright include 当前未覆盖 `workflows/runtime_persistence/integrations/notifications/observability/agent_runtime` 全量目标。
- `apps/web/vitest.config.ts` 引用 `./vitest.setup.ts`，需确认 setup 文件存在并纳入提交。
- `apps/web/package.json` 有 `test:e2e` 指向 `playwright.config.ts`，需确认配置文件存在并纳入提交。

---

## 12. 项目本地学习需要并入升级

- [ ] `P0` runtime start path 增加 `workflow_run_id` 长度前置校验或短 ID 规范化。
  - 来源：`.learnings/ERRORS.md#ERR-20260424-001`。
  - 验收：超长 run id 返回 4xx typed validation error，不再进入数据库后 500。

- [ ] `P1` runtime 监控与 smoke check 支持 localhost/DB 不可达时的降级证据链。
  - 来源：`.learnings/ERRORS.md#ERR-20260424-002`。
  - 降级证据：session JSONL、目标仓库 diff、文件修改时间、构建/typecheck artifact。
  - 验收：本地 TCP 受限时，监控状态明确标记 `local_runtime_unreachable`，并继续给出 repo-local 证据。

- [ ] `P1` ad hoc maintenance scripts 统一处理 enum/string read model 差异。
  - 来源：`.learnings/ERRORS.md#ERR-20260424-003`。
  - 建议：提供 `status_value = getattr(status, "value", status)` 这类小 helper，或避免脚本直接分支 enum 实例。
  - 验收：新增维护脚本不因 read model status shape 差异失败。
