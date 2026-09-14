# 开源旅行手册 Skill 3.0

**推荐在 Codex 中使用本 Skill，并选择 GPT 5.6 SOL 或能力更强的模型。WorkBuddy 的适配与测试暂时仍需改进，目前仅供尝试，存在流程卡住、停止推进或无法完成生成的风险。**

根据旅行需求生成可在手机与电脑查看的八模块网页手册：每日行程、景点、购物、当地体验、餐饮、行前准备、语言和旅行贴士。

本项目只有一套生成标准。支持主题切换、每日路线、旅行模式、调整行程、记账和清单。航班与酒店仅整理用户提供的预订事实，未提供时保持待确认。

## 使用

1. 下载完整仓库或发布 ZIP，将文件夹放入支持本地 Skill 的 Agent 的技能目录。
2. 安装后首次调用该 Skill，Agent 应立即打开或附上 `assets/intake-questionnaire/index.html`；也可以说：`使用 $build-personalized-travel-guide-open-source 开始制作旅行手册。`
3. 提交问卷后，Agent 先给逐日行程草案。回复确认后才开始生成完整网页；只有明确说“不要讨论，直接生成”时才跳过草案确认。

需要 Python 3.10+、Pillow，以及 Agent 提供的联网研究能力。不同宿主的工具和浏览器权限可能不同。Windows 找不到运行时时，可将 `TRAVEL_GUIDE_PYTHON` 指向已有且包含 Pillow 的 Python 可执行文件。脚本从本 Skill 根目录执行，内容生成在独立工作目录。

```text
python scripts/start_build.py <workbench> --destination Fukuoka --country Japan --start-date 2026-11-04 --days 6 --itinerary-approved --user-statement "按这版做"
python scripts/advance_build.py <workbench>
```

控制器提示下一步；Agent 完成研究与源数据后编译、下载图片、渲染并检查。最终交付 `check_handoff.py` 输出并验收通过的自包含离线 HTML；工作目录的 `index.html` 依赖同目录资源，仅供完整工作目录内预览，不能单独分享。

## 地图与图片

新生成的手机／离线地图优先使用真实道路底图截图、完整地点名称和行程顺序连线。制图阶段在获准的浏览器中联网加载底图，逐张核对后可导入正文与旅行模式，或用 `scripts/pack_phone_maps.cjs` 生成带完整名单和放大查看器的单文件地图。手机查看内嵌图片无需地图 CDN 或 WebGL。连线不是实际导航路线；桌面离线测试与手机实测须分别记录。明确要求交互地图或维护现有在线手册时保留在线方案，详见 `references/screenshot-map-workflow.md`。

餐厅、景点和纪念品在兴趣、路线与预算适合时优先主流且有代表性的选择，并同步检查资料与图片可得性。纪念品先查官方具体商品，再按需查一个可靠的同商品来源；记录查找结果后才可降级为无图卡片，不能因为图片可选就跳过查找。图片必须对应真实地点或准确标注为关联品牌素材，保留来源说明。图片预览用于实际核对，文件能下载不代表主体正确。Google 评分查不到可以省略，不编造动态开放时间与价格。

## 模板与隐私

当前模板是中性组件框架，不附带个人订单、目的地实拍照片、字体文件或地图缓存。旧版兼容模板保留公开的巴厘岛编辑示例，不能作为新目的地事实来源。用户生成的数据和图片不属于本项目示例。

问卷默认存储在本机浏览器。共享部署为可选功能，需要用户授权并配置自己的 Cloudflare 资源。发布前会询问是否设置访问码保护隐私，已有明确选择则沿用；共享后的账目与附件按部署方式保存，不应再视为仅本地数据。

## 检查与开发

以下是维护检查，不是安装前置条件；宿主要求的安全审查仍需执行。Python 测试用 `python -m unittest discover -s scripts -p "test_*.py"` 统一运行，不要逐个裸跑需要参数的辅助脚本。PowerShell 启动器受策略限制时使用已验证的 Python 直接运行，不绕过执行策略。历史目的地浏览器测试不随 ZIP 分发；路线几何测试使用合成图片，不依赖旧目的地素材。

```text
python scripts/audit_skill_consistency.py
python scripts/test_content_integrity.py
python scripts/test_public_release.py
node scripts/test_online_route_map.cjs
node scripts/test_cloud_currencies.cjs
```

自动检查不能代替图片主体核实或浏览器交互检查。检查记录必须对应实际输出；浏览器不可用时只能交付明确标注的预览。

## 在其他 Agent 中冷启动测试

DeepSeek 等宿主需要提供联网检索、文件读写和 Python 执行能力；完整验收还需要图片查看与浏览器交互能力。单纯对话模型不能独立执行整条流程。先运行 `scripts/runtime_preflight.py` 检查环境。核心流程不依赖 Codex 工具名称；Windows 的 `travel.ps1` 是可选启动器，默认沿用初始化时的 Python，可用 `TRAVEL_GUIDE_PYTHON` 显式覆盖。

建议使用新解压的 Skill 和空工作目录，在新会话中发送：

> 请读取并使用 build-personalized-travel-guide-open-source，冷启动生成福冈 2026-11-04 至 2026-11-09 的完整旅行手册，2 名成人，主流预算，兴趣为美食、购物、城市漫游、夜生活、动漫与游戏文化。无需讨论路线，直接生成；不搜索或推荐航班和酒店，未提供订单就保持待确认。使用全新工作目录，不读取或复用之前的福冈手册和测试数据。请实际检索并核对来源、图片主体与坐标，按 Skill 完成渲染和验收。记录失败命令、实际错误和修复方式；缺少浏览器或其他能力时如实标记未验收，不伪造通过记录。最后报告输出目录、耗时、check_handoff 结果及剩余问题。

先关注流程能否走通，再人工复核路线、图片和地图。`research_status.py` 在研究尚未完成时返回 2 并打印下一批任务，不应因此反复重试初始化。

## 许可

自有代码与文档采用 [MIT License](LICENSE)，允许按许可证使用、修改和分发。第三方组件保留原许可证，详见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。后续获取的图片和地图不自动获得 MIT 授权。
