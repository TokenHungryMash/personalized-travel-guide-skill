# 离线地图：有证据才降级

新制作固定先尝试原 MapLibre/OpenFreeMap 街道截图，每天一张总览。先探测一页；失败后仅做一次针对原因、且获准的修复重试。明确权限拒绝立即停止，不换工具绕过。保存真实失败日志、时间、原因和当前逐日路线指纹，不为速度直接降级。

原方案确实无法完成后，使用简化离线地理总览，不再提供在线地图作为降级。已成功的日期保留原截图，只替换失败日期。无需再次询问是否接受已约定的降级方式；交付时说明哪些天使用了简化图。历史在线手册保持兼容，但不是新制作的恢复路线。

## 简化图要求

- 每天一张，全部地点名、访问编号和顺序箭头；相近地点用引线避让标签，绝不能移动坐标。
- 用同一投影和统一比例呈现已核实坐标，北向上；背景只留淡色河流、海岸或少量主干道。使用合法取得的真实地理数据及署名，不凭印象画轮廓。缺地理数据时保留待处理，不用空白背景冒充已完成的本方案。
- 优先复用当前旅行合法缓存；必要时只取覆盖路线的最小区域，缩小过大请求，遵从 fetch-recovery 的网络权限和限次。不要下载整座城市或反复轮换服务。
- 可用 scripts/render_route_overview.py 离线绘制本地 OSM XML 中的水系；它只生成预览，不自动导入、不自动通过审核。无水系的区域需用真实主干道/边界补充，不编造。地点名必须完整；布局放不下时调整画幅，不删地点或改坐标。
- 图注必须写“简化地理总览，非街道导航图”；箭头仅表示访问顺序。图片与地点名离线可见，外部导航链接不属于在线地图降级。

## 导入和证据

沿用 map_delivery=screenshots 和 route_screenshots 图片组件，但简化图记录 kind=offline_overview，不得伪造浏览器 ready/tiles_loaded。

先目视检查实际图片（含手机宽度下的可读性），再建立 qa/offline-overview/manifest.json：

每个 maps 项包含 day（1起）、image（工作区内图片相对路径）、sha256、capture_fingerprint（由 _route_screenshots.day_fingerprint 计算）、visual_reviewed=true、review_note（真实观察）、background_file（真实地理数据相对路径）、background_sha256、source_url（真实来源）、attribution，以及 attempts 数组。每次 attempt 包含 status=failed 或 denied、reason、checked_at、log_file（非空真实失败记录相对路径）、log_sha256。日志内容必须来自真实尝试，不得生成假失败。一次权限拒绝无需重试；普通失败按前述限次规则修复。

运行 python scripts/import_route_overviews.py <workbench> <manifest.json>。导入验证图片、背景、失败日志与路线绑定，再写 owning research/itinerary.json。之后正常 recompile/render/export/QA，不手改最终 HTML 或编译产物。路线变化、图片变化或证据丢失会重新阻塞；简化图不豁免地图查看器及离线导出验证。
