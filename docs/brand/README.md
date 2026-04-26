# 品牌与界面基线

本文件把 `ai-desk` 的品牌观感和 `@ai-desk/ui` token 绑定起来，避免后续页面再次回到“亮黄方块 + 随意间距 + 自建卡片”的状态。

## 目标气质

- 面向 B 端运行控制与审批场景，不做营销页语气
- 观感应偏克制、稳重、可审计，而不是高饱和炫技
- 重点信息靠层级、密度和状态色表达，不靠大面积装饰

## 品牌色

来源：[`packages/ui/src/tokens.css`](/Users/admin/Desktop/ai-desk/packages/ui/src/tokens.css:1)

- 主背景 `--color-surface`: `rgb(16 17 15)`
- 次级背景 `--color-surface-subtle`: `rgb(23 24 20)`
- 文本 `--color-fg`: `rgb(244 241 234)`
- 次级文本 `--color-fg-muted`: `rgb(158 154 145)`
- 强调色 `--color-accent`: `rgb(205 158 78)`
- 危险色 `--color-destructive`: `rgb(239 106 91)`
- 成功色 `--color-success`: `rgb(99 195 131)`
- 信息色 `--color-info`: `rgb(122 183 217)`

约束：

- 强调色只用于焦点、关键按钮、品牌标记和少量高优先级数值
- 不允许整页只剩一种黄调或紫蓝调
- 审批、风险、失败等语义必须优先用状态色，而不是再造新颜色

## 字体与间距

- 展示和正文统一使用 `Inter / IBM Plex Sans / Segoe UI`
- 采用 8-point grid，对应 `--space-1..--space-16`
- 卡片圆角默认不超过 `--radius-md`
- 焦点态统一使用 `--ring`

## 组件约束

- 页面外壳必须走 `PageLayout + Sidebar + PageHeader`
- 审批与审计内容必须优先使用 `Card / DescriptionList / StatCard / SegmentedControl`
- 搜索和筛选必须使用 `SearchInput` 与 `SegmentedControl`
- 不允许在业务代码重新定义品牌色、阴影、圆角、间距

## 可见产物

- 审批中心截图：[`docs/media/approval-center.png`](/Users/admin/Desktop/ai-desk/docs/media/approval-center.png)
- 产品导览 GIF：[`docs/media/ai-desk-tour.gif`](/Users/admin/Desktop/ai-desk/docs/media/ai-desk-tour.gif)
- 可运行组件库：`pnpm storybook:ui`

## 维护原则

- 先改 token，再改 primitive，再改业务页面
- 任何品牌调整都必须同步更新本文件与 `tokens.css`
- 若新页面无法复用现有 primitive，先补 UI 包，再进入业务层
