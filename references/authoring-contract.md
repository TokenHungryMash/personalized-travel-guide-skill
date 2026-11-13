# 编写内容前先看字段约定

新工作台保留可读的参考内容，同时附 `content.schema.json`、`editorial-content.schema.json`、照片与地点库计划的 schema，以及带注释的 `authoring-examples.jsonc`。示例片段用于复制字段，不参与构建；真实数据仍是标准 JSON，不含注释。先运行 `python -m pip install -r requirements.txt`。构建和目的地审计使用同一结构检查，不需要联网读取 schema。

## 容易混淆的对应关系

| 字段 | 约定 |
|---|---|
| `areas[].day` | **0 基索引**：0 对应第 1 天，4 对应第 5 天。必须小于 `days.length`。不会猜测并自动减 1，以免把已经正确的日期移错。 |
| `days[].id` | 按顺序 `d1`、`d2`……，用于稳定引用。 |
| `days[].start` | 出发时刻 `HH:MM`，如 `09:00`；不是起点地点 ID。起点由 `stops[0][1]` 指定。 |
| `days[].shopping` | 可直接阅读的购买建议字符串，不是地点 ID 数组；写品类、用途与选择条件，无购物安排可为空。 |
| `days[].periods` | 上午、下午、晚间的实际安排；不是 lead/move/guard 的副本。 |
| `days[].stops` | 每项 `[显示时段, 地点ID, 说明]`；路线顺序以此数组为准。 |
| `schedules.standard` | 键必须恰好等于该日 stops 中的地点 ID，不多不少；对象键顺序无要求。 |
| `route_experiences` | 在 `editorial-content.json` 中，数量和顺序与 `areas` 一致。建议填 `areaId` 明确匹配；`place` 必须属于相应区域的 `ids`。旧工程没有 areaId 时按数组位置匹配。 |
| `area_sections` | 在 `editorial-content.json` 中，以 `areas[].id` 为键；每区为若干 `[小标题, 正文段落, ...]`。写当地空间、历史或生活特色及能看见的具体内容，不能用区域名称、图片或当天行程代替正文。开启新版证据校验时，各区域均须有对应正文，未知区域 ID 会报错。 |
| `identityScope` | 具体场馆默认 `venue`；地点本身就是街区/区域时才填写 `area`。不能为了让图片通过而把具体门店改成区域。 |
| `places[].url` | 是可访问的资料或地图入口，不限定必须官方网站。优先官方；没有官网可用可信资料或按准确名称、城市生成地图搜索链接，并建议标 `urlKind: "map"`。地图搜索不证明营业、预约、票价。 |
| `photoExceptions` | 在 `directory-plan.json` 中记录缺图地点的实际查找结果；不能用统一的“已查找”冒充研究记录。审计的 `pendingPhotoExceptions` 列出未登记 ID，填完真实理由再合并。 |

新建的 `directory-plan.json` 中 `targetRange: null` 与 `diningTargetRange: null` 是待规划值，按 directory-standard.md 的目的地类型/天数填写；不能用当前地点数反推范围。`mealCoverage` 将实际餐窗连到当天 dining 和餐厅分店；它不自动显示到页面，时段与适用条件还要在当天可见提示或候选详情中表达。正式构建检查覆盖，预览允许保留未完成项。图片覆盖默认目标 0.8，缺图使用完整文字卡并说明实际覆盖。

区域和地点 ID 各自唯一；重复区域 ID 会造成专题导航锚点冲突，构建会拒绝。schema 包含正文渲染必需字段，提供但类型错误的可选字段也会报路径。

`place-photos.json` 只写已经选择的图片：`src` 是工作台内文件，`subjectPlaceId` 对应地点 ID，`role` 为 venue/interior/product/area；看图核对主体后才将 `reviewed` 改为 true。候选下载记录留在 `photo-records.json`，见 [照片获取](photo-pipeline.md)。

构建报错会显示字段路径、区域 ID、实际索引与合法范围；摄影检查显示日次、条目、缺失字段、地点对应和重复正文；不以摄影总字数作门槛。


## 实用正文与来源

每个表格行使用 `[标题, 第一段, 第二段, ...]`，渲染器按独立段落显示。portrait 仍为二元数组，正文可用双换行分段。`editorial_sources` 为来源字典，每项含 url、title、checked（YYYY-MM-DD），可附内部 claims 和生效范围。`section_sources` 的值为对象：键是从零开始的行号字符串，值是来源 ID 数组。引用显示在相应正文附近，不能只存进 JSON 或集中堆在章末。

| `section_sources` 章节键 | 对应正文 |
|---|---|
| `portrait`、`stays`、`culture`、`shopping` | 同名数组的每一行。 |
| `notes:<主题>` | `notes` 中该主题数组的每一行。 |
| `food_types`、`snacks` | 菜式与小吃数组的每一行；讲食材、口味、吃法的事实也须绑定来源。 |
| `areas:<区域ID>` | `area_sections[区域ID]` 的每一行；如 `areas:ueno` 的 `"0"` 对应上野正文第一小节。 |
| `experiences:<区域ID>` | 对应 `route_experiences` 条目的 `title/copy/extra`，作为一个组合条目使用行号 `"0"`。新条目填写 `areaId` 后按该 ID 绑定；含外部事实时加来源，纯原创建议可按下文登记 editorial_advice。旧工程无 areaId 的兼容索引不作为新稿写法。 |

新版工作台设置 edition.editorialEvidenceVersion=1；构建会拒绝缺正文、缺来源、未知引用与无效核查日期。该检查只说明引用完整，不证明事实正确或实用，仍须按 [实用内容编写契约](practical-editorial-standard.md) 场景试读，并完成 [营业日历核对](opening-and-calendar.md)。

只有纯粹基于本次路线的原创取舍或工具操作建议、没有外部事实时，可用 `editorial_advice: {章节键: {行号: 判定理由}}` 明确标记，无需附无关链接。事实与建议混写仍须引用真实来源；人工验收不能用此字段给未查证事实豁免。

## 章节职责与阅读顺序

默认顺序为认识目的地 → 街区与当地生活 → 每日行程 → 美食 → 文化 → 购物 → 实用贴士 → 行前准备 → 地点库 → 随身工具。章节号、正文目录与弹层目录由同一顺序生成。路线总览图及其 `journey-overview` 锚点属于每日行程，城市开篇可以链接过去，不在开篇展开日次安排。

`portrait` 介绍目的地本身，`stays` 解释住宿区域的交通、环境与适合人群；两者去掉旅行日标签后仍应有用。`area_sections` 是实际可阅读的地区介绍；`route_experiences` 是该区域内的体验旁栏，两者避免重复。路线关联放短注或跳转，时刻、串联顺序、雨天改线集中到行程。美食、文化与购物先介绍对象及选择依据，再给操作条件，不能每项都从“第几天去”写起。

按 [实用内容编写契约](practical-editorial-standard.md) 和 [旅行编辑语言](travel-editorial-voice.md) 逐章试读；段落数量与长度由信息决定，不用统一三段排比充数。营业、休馆、预约、最后入场等限制保留并按 [营业与日历核对](opening-and-calendar.md) 匹配真实日期；日期未知时仍保留受影响日次、触发条件和处理方式。

## 完整新刊的构建门槛

新工作台启用 `contentCompletenessVersion=1`。城市、住宿、文化、购物或区域正文检查是否缺失，实用性通过固定职责问题和实际阅读验收，不按字数放行；区域旁栏不得复用整段通用描述。完整语言至少覆盖点餐、交通、住宿、购物、参观与求助六种实际场景，每种包含会话、常备词与回答；构建下限为4句、8词、2条回答，正常编写仍按内容规范约4–5句、10–18词展开。纯词汇地名场景可另加。英语与非英语采用相同覆盖标准。门槛只排除明显未完成稿，不能为凑数复制近义句或泛化提醒；正文深度与试读答案遵循实用内容编写契约。

## 餐饮、准备与语言字段

餐厅与分店复用地点库中的稳定地点标识，一店一主分类；`restaurant_groups[].items[].sources` 引用 `editorial_sources` 的来源 ID，支持该分店的菜单、营业与推荐事实。`content.json.days[].dining` 是当天候选的地点 ID 数组，不改变 `stops` 或把餐厅自动加入已批准路线。它引用同一条餐厅与地点资料，不复制第二套菜单、地址或营业时间。市场、夜市作为区域资料，不能充当具体餐厅记录。四类推荐及核实范围见 [内容与功能](content-and-functions.md)。

`editorial-content.json.preparation` 优先于旧 `checklist`，格式为阶段数组，每阶段含 `title` 与 `items`。每个任务为 `{id, title, detail, priority, sources}`：

| 字段 | 编写与兼容约定 |
|---|---|
| `id` | 表达任务身份，不表达显示顺序；新任务使用稳定的 `prep-*` 标识，不按数组位置编号。原有任务保留旧标识与原勾选语义；当前东京升级保留 `c0` 至 `c11`，其他工程按各自已有对应关系迁移。不能把旧 ID 重新分配给不同任务。 |
| `title`、`detail` | 标题给明确任务，detail 说明操作、适用条件与怎样算完成；不要只重复标题。 |
| `priority` | 仅用 `必须`、`建议`、`按需`。必须项也要说明适用范围，不能把不明国籍、证件或旅程条件的任务写成人人必办。 |
| `sources` | 来源 ID 数组，引用 `editorial_sources`；法规、办理和预订事实由相应来源支持，不因任务可勾选而免于核实。 |

没有新结构的旧工程继续兼容 `checklist`；迁移后以新准备任务为主，不在两处维护不同清单。来源与适用条件独立于勾选状态，用户勾选不等于系统认证。

`phrases` 保持分组对象，新句使用 `{id, local, zh, roman, english, note?, input?, subjectFrom?}`。`id` 稳定；`local` 可直接出示，`zh` 是准确中文，`roman` 为适用的读音辅助，`english` 在非英语目的地必填，是可独立使用的英语，不能把读音填进英语。`note` 只补充使用条件。`words` 的常备词与回答使用 `{local, zh, roman, english}`；以“常备 · 分类名”区分词典分组，其余为回答。旧 `[local, zh]` 继续兼容；新编及本轮语言升级应补成完整对象。

新工作台启用 `edition.readerReferenceVersion=2`，构建要求场景映射，非英语目的地还须完整备用英语；旧版标记仍兼容，升级时不能降低标记绕过缺失内容。`languageScenes` 是场景入口数组，每项为 `{id, label, phrases?, glossary?, replies?}`。后三项引用原分组全名，至少一项存在；无该类内容时省略该字段，不用空字符串或空数组。每个会话、常备词、回答分组须恰好归属一个场景，场景 ID 唯一，引用分组不得为空。存在此配置时，校验要求被引用的非英语行都有明确 `english`；英语目的地仅使用 `local` 英语内容，可省略重复 `english`；不显示重复英语切换或第二套表单。没有该字段的旧工程仍可打开，升级时显式整理映射，不能默默丢弃未映射组。

英语目的地（`edition.lang` 为 `en` 或 `en-*`）直接使用如下结构，不复制备用翻译字段再留空：句子 `{"id":"dining-bill","local":"Could we have the bill, please?","zh":"请结账。"}`；词或回答 `{"local":"Service included","zh":"已含服务费"}`。英语填写项的选项用 `{value,label}`，没有第二套输入。为兼容旧稿，构建仅在内存中忽略英语目的地这些未使用的空字符串字段，不修改原稿；非英语目的地的备用英语仍须齐全。此兼容不自动翻译，也不豁免错误类型。

填写型句子使用 `input: {key, label, required, options: [{value, label, english}], placeholder, englishLabel, englishPlaceholder?}`。`key` 稳定，`value` 用于当地表达，`english` 是对应的英语值；选项名称帮助中文读者选择。占位提示不能作为真实内容出示。非英语目的地的预设选项同时填写当地语言和英语；用户自行填写的两种语言分别保存，不能把当地文字直接当英语。过敏食材设为必填，当前出示语言对应的具体食材未填写时阻止展示，不默认某种过敏。英语目的地只提供 `label/value/placeholder` 和一套英语输入，可省略 `english/englishLabel/englishPlaceholder`。原本机键 `phrase:<id>:<key>` 不变；仅非英语目的地的备用英语另用 `phrase:<id>:<key>:english`，旧备份导入不产生虚假的英语食材。

需要复用同一食材等信息的后续句可加 `subjectFrom: <带input的句子ID>`，共享源输入与持久化键，不复制另一份事实。目标必须存在且带 `input`，不得自引用，也不得同时设置本句 `input`。后续句同样检查当前语言的必填值，再出示具体对象与完整句。

静态正文是准备与语言的唯一渲染来源；旅行模式内置速查复用其 DOM 并清除重复 ID，不能另写会漂移的内容。场景、语种和查询类型可分别切换，正文与速查的输入即时同步；返回保持原工具、日次、焦点和滚动位置。新增结构同步 schema、渲染器与旧备份兼容，不以能显示为全部验收。内容与数量取舍见 [内容与功能](content-and-functions.md)。
