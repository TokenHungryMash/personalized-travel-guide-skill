# 当前引擎：跨城市保留的体验

默认 `create_workbench.py` 复制 `assets/destination-reference` 的实际代码。冻结福冈样刊只供 `--sample` 复原，不能覆盖当前引擎。维护时同步本地工作包与已安装包，并校对文件哈希；不把东京或其他用户旅程作为默认内容复制进技能。

## 摄影与城市配置

`edition-renderer.py` 使用统一的 `overprint-edition` 类。样式以渲染器的 `cssfiles` 为唯一加载清单；当前末段依次为 `magazine-polish.css → photo-overprint.css → reader-density.css → mobile-travel.css → travel-alternatives.css → editorial-premium.css → travel-interior.css → impeccable-editorial.css → impeccable-interior.css → travel-reference.css`。前面的目录、记账、字体与上传样式仍须保留。历史更新中某一层“最后加载”只表示当时位置，不能据此覆盖或打乱当前清单。

`edition.json` 配置 `cover / coverLine / coverNote / coverCredit / coverPosition / coverPositionMobile / coverMood`。都市默认真实夜景；其他主题选图填 `coverMoodReason` 说明。裁切根据照片主体逐端检查；照片身份、来源与许可仍记在 `edition-photos.json`。不得给其他城市沿用东京照片、地名或国家。长城市英文会缩放，但仍需实看。中文城市大字、浅色正文与彩色叠印优先保证可读。

卷首与编后记使用 `editorTitle / experienceLead / closingPhoto / closingWords / closingCopy`，不改渲染器中的目的地常量。每个 `areas[]` 必须有对应的 `editorial-content.json.route_experiences[]`，字段为 `tone / words / title / copy / extra / place / label`；照片大页和体验按实际路线分布，不能机械只选两个地点。`tone` 选 blue、cream、amber、lime 并按照片对比度取舍。`validate_edition.py` 在构建时检查覆盖及引用，不能用 zip 静默漏掉后半部分。

## 阅读、旅行工具与数据

- `reader-context.js` 在 `app.js` 之后、`motion.js` 之前加载。左侧始终提供全书目录；右侧随大章节切换为日期、街区、餐饮分类、贴士主题或地点筛选。动态生成的锚点支持刷新和直接打开；关闭弹层返回阅读位置。
- 手机行程正文底部固定日期。最多 7 天直接呈现全部日期；更多天改为明确的日期选择器与前后日按钮，禁止固定写死六列。页末显示下一天与区域，最后一天继续到美食 `#food`，不能跳回已阅读的街区章；不自动跳日。弹层出现时隐藏外层底栏，底部留安全区域。
- `member-avatars.js` 在 `ledger-ui.js` 和 `app.js` 之前加载。成员上传 JPG/PNG/WebP，压缩为 128px JPEG，应用到成员、分摊和结算。`memberAvatars` 为可选字段，旧备份仍可导入；新备份带头像，存储失败保留原图。见 [记账契约](ledger-contract.md)。
- `travel-alternatives.js` 在 `app.js` 前加载。「当天提醒与备选」统一为默认收起的入口，收起显示方案数量，展开先读当天 `guard`，再按需展开各个备选；只有提醒时仍可使用。`content.json.days[].alternatives` 使用实际当天路线编写，详情返回与切日行为见 [旅行工具规范](travel-tools.md)。查看提醒和备选不改变当前日、路线、账目或用户笔记。
- `reader_reference.py` 渲染正文准备清单与语言卡；`travel-reference.js` 在 `travel-alternatives.js` 后、`app.js` 前加载。旅行速查的用餐、语言及准备兼容页复用正文 DOM；当天行程只显示用餐和语言入口，移除副本中的重复 ID；在 `#travel-reference-dialog` 中打开，保留下层工具、日次、展开项和滚动位置。勾选与语言输入共用同页状态；语言按场景组织会话、词语、回答，非英语目的地可在当地语言和备用英语间切换；英语目的地只显示一套英语，填写对象按实际语言保存。现有四个主工具的数量与职责不变。
- 地图查询、币种、语言取自 `edition` 与地点数据。已有工程保留原存储键和备份标识，新建工作台才生成独立键。

脚本按渲染器实际顺序内嵌：`map-layout.js → map-ui.js → schedule.js → ledger-model.js → member-avatars.js → ledger-demo.js → ledger-ui.js → travel-alternatives.js → travel-reference.js → app.js → reader-context.js → motion.js → vendor/gsap.min.js → art.js → impeccable-interior.js`。样式与脚本的完整列表从代码核对，不能只复制功能名称对应的一个文件。笔记共用是杂志与四个旅行工具在同一页面内使用同一状态；持久化在当前浏览器，不提供多人、云端或跨标签页实时同步。

## 章节与实质正文

默认章节 ID 顺序为 `orientation → neighbourhoods → itinerary → food → culture → shopping → fieldnotes → prepare → directory → tools`。先介绍目的地，再深入街区，第三章进入每日行程。章节编号、页面目录、弹层目录及动态导航一致；调整顺序后复核锚点直达与最后一天的后续入口。全程路线总览及 `#journey-overview` 放在行程章，城市开头只保留必要跳转。

每区 `area_sections[区域ID]` 的小标题、正文段落和来源实际渲染在区域大图之后；`route_experiences` 作为体验旁栏，不能替代整区介绍。空间、文化、街道和生活特色独立于日次成立，住宿区域也须独立解释选择依据。美食的 `food_types`、`snacks` 展示菜式与小吃本身，不用餐厅顺路说明代替。

`editorial_evidence.py` 校验来源绑定；渲染器就近显示 `areas:<区域ID>`、`experiences:<区域ID>`、`food_types` 和 `snacks` 引用，具体行号与字段见 [编写约定](authoring-contract.md)。新稿开启 `edition.editorialEvidenceVersion=1`；旧工程区域正文回退只用于兼容，不能作为新城市省略内容的方式。来源完整不等于事实、写作与日期安排已通过审阅。

页面深色目录与浅色弹层目录分别设定文字颜色，避免浅色弹层继承深色目录的淡绿文字。目录说明小字与各自实际背景的对比度至少 4.5:1，计算样式 `opacity` 为 1；桌面和手机都验收。正文保留大图与色彩叠印，信息层次不依赖把说明文字降到难以阅读的亮度。

## 检查复制出来的工程

新城市构建与日常修订均按 [交付检查范围](release-verification.md) 选择检查。引擎改动先确认工作副本和技能源文件一致；涉及脚手架复制、模块加载或跨城市字段时，再用默认模板创建隔离工作台验证。只迁入已核实内容与素材，不用旧工程代码覆盖新引擎，不把测试内容写回模板。纯文档修订无需重建手册或重跑全部浏览器检查。

## 动效连接检查

`art.js` 必须命中当前 `.ink-scene`，不能只保留旧福冈 class。默认启用封面分层入场、摄影展开、图片与叠字轻微错向位移；减少动态效果或主动关闭时恢复静态。分别在 no-preference 与 reduce 下测试，不能只用减少动态效果的截图验收动效。保留用户主动关闭的选择，新工程不继承其他城市开关。

视觉研究参考：[Codrops ImageExpansionTypography](https://github.com/codrops/ImageExpansionTypography)、[ScrollingLettersAnimation](https://github.com/codrops/ScrollingLettersAnimation)。动画编排由本地代码实现，GSAP 从 `vendor/gsap.min.js` 内嵌，不依赖在线 CDN；不复制参考项目的图片或字体。

## 编辑版式与摄影比例

`editorial-premium.css` 提供深墨绿目录、暖纸色攻略、带编号的章节题头、集中展示的当天信息和手机日期底栏，后接当前内页与 Impeccable 层。综合使用版式、字体与 UI 细节规范，而不把整页改版等同于 hover 特效。摄影展示参考 [SUITCASE](https://suitcasemag.com/)，字体/网格交互研究参考 [Codrops 字体实验](https://github.com/codrops/OnScrollTypographyAnimations) 与 [网格交互](https://github.com/codrops/GridItemHoverEffect)；保留本刊福冈叠印方向，只借鉴方法，不复制网站内容或资产。

正文摄影默认桌面约 1.65:1、手机约 4:5，根据构图调整。桌面正文大图展示宽度不超过原图宽度与 1800px 版式上限；该上限不用于首屏封面。源图必须先通过 [大图质量门槛](release-verification.md#大图质量门槛)，仅缩小 CSS 不能让仍作为大图引用的低像素源通过。需要手机独立构图时记录 `edition-photos.json.mobileSrc`，同样满足对应位置的源图门槛、内嵌离线并核对具体主体。叠字按摄影容器字号缩放，不能跟随超宽视口放大到图片之外。

收尾专用 `.journal-finale`，禁止复用旧 `.magazine-afterword` 的两栏/max-width 规则。验收检查照片位于文案上方、宽高比、文字对比度，至少包含 2560px 宽屏和 320/390px 手机。图片支持 picture 后同时测试真实滚动动效及关闭状态，不只检查图片是否加载。

回归命令：`node scripts/check_editorial_layout.cjs <工作台>`，记录当前构建哈希，在 2560/1440/768/414/390/375/320 宽度逐页检查目录、行程、摄影、收尾。

内页由 `travel-interior.css` 及后续 Impeccable 层共同处理；`ledger-demo.js` 在 `ledger-ui.js` 之前加载。内页规范和演示数据契约见 [旅行工具](travel-tools.md)、[记账](ledger-contract.md)。默认模板和实际工作副本都需接入，不能只修改东京专用工程。

视觉组合采用 Impeccable 编辑排版方法、GSAP 离线动效与 UI/UX Pro Max 操作规范，相关实现已随工程打包；制作不要求额外联网安装这些设计技能。保留福冈大图、色彩叠印、动态导航、手机日期栏、头像与成员管理。关闭动效和系统减少动态效果时静态内容完整可读。
