# First-use intake

Use the bundled questionnaire as the default intake for a new or preference-light request. The same first response must open, attach or link the actual `assets/intake-questionnaire/index.html`. If a host cannot expose files inside the Skill directory, copy it to the current workspace as `旅行需求问卷.html` and provide that copy as the artifact. Do not merely say a questionnaire is required, enumerate its fields, replace it with chat questions, or use the host application's native multiple-choice UI.

The questionnaire output or current written brief is the single intake authority. Do not add a decision list, host-native choice widget or improvised questions. Once the brief includes preferences/constraints, draft the compact itinerary proposal in itinerary-discussion.md and resolve remaining optional fields with defaults. The questionnaire's generated request asks for that proposal first; it is not route approval. Start full production only after route approval or an explicit discussion waiver. Do not cite an earlier destination, previous run, saved memory or old project unless the user explicitly requests reuse. Do not proactively explain legacy issues, exclusions or internal workflow.

If the user supplied a complete brief (destination, dates or duration, travelers, rhythm/default permission, interests and constraints), skip the questionnaire and proceed directly to the itinerary proposal. If the brief supplies only destination, dates/duration and travelers, deliver the HTML questionnaire and ask exactly once: `问卷已经附上；如果不需要填写，直接回复“按默认”即可。` A refusal or default permission completes intake; show the proposed route next, without repeating intake questions. It does not approve an unseen itinerary. A destination-only request is also valid without a questionnaire when the user explicitly asks the Agent to choose sensible defaults. Failure to preview local HTML is not permission to replace it with typed fields: provide the file anyway so the user can open it externally.

The only user-facing transport/accommodation note should be: booked transport or accommodation can be supplied as screenshots or text; otherwise those sections remain pending. Do not explain edition boundaries, excluded modules, internal architecture or comparison features unless the user asks.

The public questionnaire contains only core handbook inputs: destination; dates or days; travelers and relationship; broad budget; pace; interests; must-go places; exclusions; food/accessibility/special requirements. It never asks for flight or hotel selection criteria and never triggers commercial recommendations.

Every optional field has a neutral default. Missing optional fields do not block drafting the itinerary proposal. Use mainstream first-visit defaults, label material assumptions and keep unprovided transport or accommodation pending.

Suggested first response:

> 我可以为你制作一份完整的个性化旅行手册，包括每日行程、景点、购物、当地体验、餐饮、准备清单、语言锦囊和旅行贴士，并生成适合手机与电脑查看的网页。
>
> 这是 1–3 分钟的旅行需求问卷，填完后把它生成的提示词发给我即可。如果不想填，直接回复“按默认”，我会先按主流偏好列出每天的行程草案，和你确认方向后再制作完整手册。

Always provide `assets/intake-questionnaire/index.html` or its workspace copy as a clickable artifact unless the questionnaire was explicitly waived or a complete brief already supplied. Do not paste its HTML or a field-by-field substitute into conversation.

## Completion and optional sharing

After a newly generated guide passes handoff, ask once: “手册已完成。需要我帮你上传到云端，让同行人共享 PDF 文档、图片、链接和记账吗？” A decline, deferral or no answer leaves the local handbook complete. Do not repeat the offer. Existing deployment authorization carries forward; do not ask again. For an accepted deployment use [current system](current-system.md), check existing Cloudflare authentication first, and provide a short signup/login path only if needed. Cloud registration and billing are never prerequisites for local completion.

## 功能、限制与数据处理

- 本 Skill 会根据用户提供的信息和公开网络资料生成旅行手册，并可能访问地图、地点官网及图片来源；第三方服务的可用性、条款和数据准确性由相应服务提供方负责。
- 行程、营业时间、票价、预约要求、评分和交通信息可能变化，出发前应再次向官方来源核实；缺少可靠数据时必须省略或使用保守表述。
- 本地版保存于当前浏览器；可选云端版按用户授权共享成员、头像、账目、还款、预约勾选、收藏附件和摄影参考样片。个人行李和行程自定义仍是本地数据，不能声称所有状态均已同步。
- 资源下载仅允许来自公网 HTTPS 地址，并受文件类型、大小和图片有效性校验约束；不得访问本机、局域网、保留地址或包含凭证的 URL。
- 已确认使用 Fake-IP 代理时，可由运行环境显式设置 `TRAVEL_GUIDE_ALLOW_FAKE_IP=1`，仅兼容域名解析到 `198.18.0.0/15` 或 `fdfe:dcba:9876::/48`；默认关闭，不允许直接填写这些 IP，不放开本机或局域网地址。不要为绕过宿主访问拒绝而开启此项。
- 本 Skill 不处理支付、预订或账户凭证，不要求用户提供密码、Cookie、访问令牌或其他认证秘密。
- 本许可和第三方组件声明见 `LICENSE` 与 `THIRD_PARTY_NOTICES.md`；维护说明不得改变第三方许可义务。

云端部署前须按 [访问方式确认](current-system.md#cloud-access-choice) 询问是否设置访问码；本次会话已经明确选择的直接沿用。不要把本地生成授权或云端部署授权解释为同意免码公开。
