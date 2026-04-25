# Project Improvement Drive Modes

- 状态：`Working Draft (v1.0, 2026-04-20)`
- 作用域：`project.improvement` runtime workflow 驱动策略

## 1. 模式定义

`project.improvement` 支持两类驱动模式：

1. `self_driven`（默认）
2. `external_requirement`

触发字段：`metadata.drive_mode`

## 2. Self-Driven（默认）

目标：在无外部明确需求时，让 ai-desk 自主完成“评估 -> 执行 -> 再评估”的持续迭代。

默认规则：

- `drive_mode` 缺失时默认 `self_driven`
- `loop_iterations` 默认 `2`，取值钳制到 `1..5`
- `evaluation_pattern=project_maturity_audit.three_pass`

每轮任务骨架：

1. `loop-N-survey` (`auditor`)
2. `loop-N-counter-argument` (`reviewer`)
3. `loop-N-roadmap` (`planner`)
4. `loop-N-execution` (`decomposition`)
5. `loop-N-review` (`reviewer`)

跨轮依赖：

- `loop-(N+1)-survey` depends_on `loop-N-review`

## 3. External Requirement

目标：当需求明确时，以需求闭环为主，不强制多轮自驱动迭代。

默认任务序列：

1. `req-clarify` (`planner`)
2. `req-execution` (`decomposition`)
3. `req-review` (`reviewer`)

附加字段：

- `evaluation_pattern=external_requirement.delivery`

## 4. 兼容性

- 若调用方显式传入 `tasks`，runtime 不覆盖任务定义。
- 本规格只定义默认 task injection 策略，不改变现有状态机与持久化模型。

## 5. 验收标准

1. 两种驱动模式都可通过 `metadata.drive_mode` 选择。
2. 默认路径必须是 `self_driven`。
3. `self_driven` 支持可控轮次且依赖关系正确。
4. `external_requirement` 路径保持简洁交付链路。
5. 单元测试覆盖默认、边界值和显式 task 覆盖。
