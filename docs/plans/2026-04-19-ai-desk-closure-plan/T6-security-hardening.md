# T6 Security / Secret / Isolation 硬化

- 优先级：`P1`
- 目标：把当前基础安全 gate 补到“团队可长期使用”的水平

---

## 1. 当前问题

当前安全面仍偏轻量：

- `/Users/admin/Desktop/ai-desk/apps/api/api/security/service.py`

问题包括：

1. `SecretBroker` 还是进程内 dict。
2. 没有 project / tenant 级 secret scope。
3. 没有 workspace isolation enforcement。
4. 没有 network egress policy。
5. 没有 artifact provenance 签名或完整性校验策略。

---

## 2. 技术实施方案

### A. Secret broker 持久化与作用域化

新增：

1. `secrets` 表或接正式 secret provider
2. `project_id / scope / expires_at / created_by`
3. audit log

### B. Workspace policy enforcement

在 dispatch 前增加：

1. writable path 归属校验
2. workspace root ownership 校验
3. cross-project path deny

### C. Command / tool policy 细化

从 prefix allow/deny 升级为结构化 policy：

1. command family
2. network required
3. write required
4. approval class

### D. Artifact provenance integrity

增加：

1. artifact manifest hash
2. producer metadata normalization
3. provenance completeness check

### E. 安全事件审计

把以下行为落 audit log：

1. secret resolve
2. approval gate hit
3. blocked command
4. write execution grant

---

## 3. 验收标准

1. secret 不再只存在内存中。
2. 不同 project 的 workspace / secret scope 隔离生效。
3. blocked command / approval gate / secret resolve 有审计记录。
4. artifact provenance 有基本完整性校验。

---

## 4. 建议测试

1. 跨项目 workspace 路径被拒绝。
2. secret 过期后不可用。
3. blocked command 被拒绝且写入审计。
4. provenance 不完整的 artifact 不能注册成功。
