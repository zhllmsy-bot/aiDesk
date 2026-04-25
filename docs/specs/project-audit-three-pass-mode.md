# Project Audit Three-Pass Mode

- 状态：`Working Draft (v1.0, 2026-04-20)`
- 作用域：`project.audit` runtime workflow 默认执行模式

## 1. 目标

将 `project-maturity-audit` 的三段式评估范式固化为 ai-desk 的默认项目评估模式，确保评估流程可复用、可追踪、可审计，而不是依赖单次 prompt 风格。

## 2. 默认流程

当 `workflow_name=project.audit` 且启动请求未显式提供 `tasks` 时，系统自动注入以下任务序列：

1. `audit-survey` (`auditor`)
2. `audit-counter-argument` (`reviewer`)
3. `audit-roadmap` (`planner`)

依赖关系：

- `audit-counter-argument` depends_on `audit-survey`
- `audit-roadmap` depends_on `audit-counter-argument`

## 3. 三段语义定义

### 3.1 Survey

- 目标：建立证据地图并区分已实现/仅文档/推断项
- 输出重心：系统身份判断、闭环初判、事实证据索引
- 风险：禁止把文档当成交付证明

### 3.2 Counter-argument

- 目标：强制二次怀疑，反驳第一轮乐观解读
- 输出重心：伪闭环、脆弱资产、最先失效点
- 风险：避免“看起来完整”的叙事偏差

### 3.3 Roadmap

- 目标：把前两段分析转成执行优先级
- 输出重心：P0/P1/P2 收口项与验收标准
- 风险：避免 feature wish-list，优先闭环能力

## 4. Runtime 约定

- `metadata.audit_mode` 默认写入 `three_pass`
- 保留显式自定义 `tasks` 的能力：
  - 若调用方传入 `tasks`，runtime 不覆盖任务定义
- timeline / graph / attempts 仍沿用统一 runtime 读模型

## 5. 验收标准

1. `project.audit` 默认任务固定为三段顺序。
2. 自定义 `tasks` 启动时保持向后兼容。
3. README 与 spec 明确记录该模式为默认评估模式。
4. 单元测试覆盖默认注入与显式覆盖路径。

## 6. 与 `project.improvement` 的关系

`project.improvement` 复用本三段范式作为 `self_driven` 模式的每轮评估骨架：

- 每轮顺序：`survey -> counter-argument -> roadmap -> execution -> review`
- 用于实现“自驱动评估 + 执行 + 再评估”的迭代闭环
- 当 `drive_mode=external_requirement` 时，切换到需求驱动交付序列
