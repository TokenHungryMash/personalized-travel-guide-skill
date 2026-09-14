# Product UI contract

Read for shared UI/runtime maintenance or an affected component repair. Ordinary destination builds reuse the bundled implementation; they do not reimplement these specifications. For restore/new-build map selection see [current system](current-system.md) and [online maps](online-map-workflow.md).

- 体验类卡片采用紧凑的信息密度：限制封面高度，收紧标题、正文与信息区间距；不得向用户展示“官方品牌图”“非实景”等内部素材分类提示，素材来源与类型保留在清单和审计数据中。
- 预约与确认默认按“必须 / 建议 / 随缘”优先级展示，不再提供含义模糊的“按顺序”切换。
- 手机预约条目必须让标题独占第一行，优先级、勾选状态与展开按钮位于第二行各自独立网格区域；不得把优先级标签与“已处理”复选框放在同一网格单元或用绝对定位叠放。
- 预约状态文字必须跟随复选框：未勾选显示“待处理”，勾选后才显示“已处理”；本地恢复与云端推送状态后都要调用同一同步函数更新文字和无障碍标签。
- 有真实固定时刻、预约入场、接送或离境节点时，在封面下方用 `time_anchors` 生成最多四张紧凑的“出行时间锚点”卡；没有可靠锚点时省略，不用普通景点时间凑数。
- 记账内的汇率换算放在记账页最顶部，作为默认折叠的小栏；展开后将“原币金额”和“换算结果”排成上下两行，汇率设置压缩为一行。旅行成员与正式记账内容从它下方开始。
- 汇率换算每次打开手册时默认使用“目的地当地货币 → CNY”；历史手动选择不得覆盖这个初始组合。巴厘岛为 `IDR → CNY`，日本为 `JPY → CNY`。用户改选币种后，本次页面内正常按新组合换算。
- 汇率按币种对保存缓存；仅可恢复与当前币种对一致的数值，无有效汇率时显示待填写。点击刷新必须实际请求汇率服务，失败时保留同币种对的缓存或手动输入，不得把缓存重绘冒充实时刷新。
- 记账分摊成员按钮使用“勾选框＋头像（无头像则姓名首字）＋姓名”的单行紧凑布局；姓名不得被挤到按钮外或逐字竖排。结算关系同时显示付款双方的小头像，不用固定设备数量描述云端同步。
- 旅行模式的日期导航在行程、路线图、摄影与记账各页都持续显示；手机全屏模式不得因宿主安全区或页面顶距产生大块无用途留白。
- 每个景点卡片的“＋”用于添加链接、PDF、门票或票据图片；上传前允许填写自定义按钮名称，保存后还要提供简洁的“编辑 / 删除”操作。保存成功后必须在该卡片操作区立即生成有名称的附件按钮。点击图片或 PDF 按钮时在页面内直接预览，点击网页链接时直接打开链接；编辑名称后卡片按钮立即更新，删除附件后对应按钮同步消失。默认单个附件上限为 20 MB，前端提示与服务端校验必须一致。
- 景点模块不显示“本次探索”之类重复摘要，购物模块不显示“这次怎么逛”之类长篇总览；餐饮模块顶部使用“本次餐厅”概览。数据来自 `dining_plan`，按日期列出餐次、餐厅、品类、每人预算与行程提示；有数据时显示、无数据时省略。组件必须使用原生 `<details>` 且默认折叠，不写 `open`；展开后提供前往预约清单的入口。
- 行程未配置 `journey_phases` 时，模块标题下直接显示每日行程卡，不再重复输出 `ITINERARY / N 天行程`；只有确实存在多段旅程分区时才显示分段标题。
- 手机封面的英文副标题必须在封面卡片内完整显示；中文主标题可保持大字号，但英文行在 `560px` 以下使用视口自适应字号、较小左缩进和紧凑字距，不得依赖裁切隐藏溢出。

## Trip Mode

Compact stop actions reduce button padding, not text legibility: use 36px-high map/link/attachment buttons with 13px labels and a 36px square plus control. The day heading is 22px and the collapsed backup heading is 17px. Apply the shared rules at every viewport, with sufficient specificity to override legacy theme rules; do not shrink action labels to 9–10px.

For current-system restore/UI/runtime changes, [current system](current-system.md) is authoritative. Older one-page Trip Mode and hand-drawn examples are compatibility references only; do not regress to them.

Trip Mode has one phone-first vertical interface on every viewport; desktop centers the same narrow panel for recording and parity. On desktop its panel must stay at or below 490px wide and must never expand into a wide dashboard; on mobile it may use the full viewport width. It is generated from one injected per-day JSON payload, never destination-specific constants or DOM guesswork. Keep these behaviors together:

- compact day tabs and stop cards with practical notes and transfer context; omit the removed generic daily overview strip. Keep only place-specific reservation or hard-deadline information in the authored note;
- self-contained daily shopping guidance: write where to browse on this route, what to prioritize and why, a realistic time allowance, useful brand/category choices, comparison order, purchase/fit/returns/tax-refund cautions and luggage handling in two or three short paragraphs. Do not reduce it to a generic sentence or send users to souvenirs/the shopping chapter; Trip Mode shopping cards have no jump button. Use existing verified shop records, not another research pass. On non-shopping days explain the choice and the suitable later shopping day without forcing a store;
- every Trip Mode stop has a compact plus control that opens a ticket vault for that exact stop. It accepts ordinary web or Xiaohongshu share text/links plus PDF/image ticket, price-note and receipt files; list, preview/open, rename and delete saved items. Local exports keep these on the current device and state that boundary; when the user explicitly requests cloud sharing, persist both metadata and file bytes in bound Cloudflare storage, label the vault “云端共享”, and verify upload/read/delete without leaving test data;
- every Xiaohongshu action must preserve the exact place keyword. On mobile, prefer the Xiaohongshu app deep link (or the host mini-tool API when available); on desktop or when app launch is unavailable, retain a working Xiaohongshu web-search fallback rather than a dead button;
- the Trip Mode accounting view includes a collapsible exchange-rate calculator with online reference-rate refresh and manual fallback. It does not rewrite ledger records; the displayed source date is not a live market quote;
- keep Trip Mode dense enough for active travel: short header/day tabs, restrained section gaps, compact stop cards and actions, and readable tap targets. Avoid repeated warning boxes or oversized vertical padding that push the next stop below the viewport;
- a separate “备选方案” card below the day's introduction and before the route, collapsed by default. Reuse each day's authored `fallback` in one or two short paragraphs; do not invent venues or initiate extra research;
- geographic basemaps with numbered stops based on verified coordinates, plus Google/Apple navigation with Google as the first-use default; the screenshot map workflow defines the default new-build implementation;
- exact-place Xiaohongshu and map actions on stop cards, with no generic bottom Xiaohongshu button;
- an expanded photography card with two or three route-specific shooting moments;
- reference-photo upload stored locally as Data URLs in local editions and in bound Cloudflare attachment storage in shared editions; shared uploads, previews, per-photo deletion and clear-all must be visible to every handbook user. Keep large tappable previews and full-screen viewing in both modes.
- on the phone reading shell, every “回到目录” action opens the chapter directory instead of navigating to the obsolete continuous-page `#contents` anchor; desktop may keep ordinary anchor navigation.

New destination builds embed reviewed local street-map screenshots for every day. Only an explicit online-map request selects on-demand online basemaps and an offline route-list fallback. Exact snapshot restoration keeps its embedded maps. Neither path performs extra destination research. If coordinates are unavailable, fix the source place record rather than drawing false geography. Do not retain Bali shopping constants, Blob object-URL previews or duplicate map components.


贴士每条必须显式提供 priority（必须/建议/随缘），按实际约束分级，不设比例，不靠标题猜测，不默认全部建议。单图画廊必须占满图片容器，不保留多图布局的半幅空白；在手机与桌面实际测量并查看截图，品牌图保留 contain 规则。离线交付默认单文件 HTML，内嵌图片、街道地图、CSS 和 JS；优先提供自包含 HTML 的打开/下载链接；网页预览链接须验证完整资源可加载，不能单独附上散装 index。说明双击可用普通浏览器打开，无需解压。
