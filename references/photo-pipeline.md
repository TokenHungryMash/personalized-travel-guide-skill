# 图片清单下载与身份核对

批量图片先保存为 UTF-8 JSON 清单，命令行只传清单路径。不把整批网址或含网址的程序拼进 PowerShell、`python -c` 或其他命令参数，避免 Windows 命令长度限制。已有图片直链用下方下载入口；需要 Commons 检索时用本文后面的 `fetch_photos.py --plan`。

## 已有图片直链

将已找到的候选保存为 `download-plan.json`，以下为字段示例，替换为真实地址后执行：

```json
[
  {"id":"museum-front","placeId":"museum","url":"https://images.example.com/museum.jpg","page":"https://museum.example.com/visit","caption":"待核对的建筑主体"}
]
```

```powershell
python "$skill/scripts/download_photos.py" "$workbench" --plan "$workbench/download-plan.json"
```

`id` 是唯一且适合文件名的候选标识，`placeId` 对应实际地点；`url` 为图片直链，`page` 为来源页。脚本串行读取清单，验证完整图片、记录实际尺寸，写入 `media/photo-candidates/` 和 `photo-download-records.json`，不改原图尺寸或自动登记为审核通过。它与 Commons 脚本共用工作台锁、限流及失败退避；403 停止，超时有限重试，失败保存进度。重新执行同一清单会跳过哈希一致的完整下载；换源时修改清单 URL，保留旧记录。下载失败不等于当地没有照片，不自动生成图片例外。

一般 HTTPS 来源不要求邮箱；下载 Wikimedia 图片仍需下方真实联系信息配置。下载完成后同样核对主体、来源许可、署名和展示尺寸，再选入地点库或大图；`reviewed:false` 不能由下载成功自动改成通过。

## Commons 检索

`scripts/fetch_photos.py` 从 Wikimedia Commons 实际检索，取得来源页、作者和许可等元信息；可下载少量候选。它不把标题命中、下载成功或相似街景当成地点身份已经核对，也不改写 `place-photos.json`、`edition-photos.json` 或成品 HTML。

## 配置与运行

使用工作台已有 Python 环境和 Pillow。仅使用此 Commons 获取脚本时，联网前须配置**操作者本人真实可联系的邮箱或 HTTPS 联系页**：设置 `JOURNAL_MEDIA_CONTACT`，或传 `--contact`。脚本不会提供默认邮箱，也不会冒用浏览器 UA；联系值会随 User-Agent 发给 Wikimedia。这是该脚本的配置要求，不是制作手册的前置条件；没有配置时可直接改用官方图库或其他可用来源，不为此阻塞整份手册。脚本只能检查格式及明显占位符，无法证明联系方式归属。请勿照抄别人的地址。

以下 PowerShell 示例中 `$skill` 是技能根目录，`$workbench` 是工作副本绝对路径；`sensoji` 必须是该工作副本 `content.json` 的实际地点 ID。先在环境变量中配置真实联系方式，再运行：

```powershell
python "$skill/scripts/fetch_photos.py" "$workbench" --place-id 'sensoji' --query "Senso-ji Asakusa Tokyo" --limit 3
```

确认需要这些候选后，在相同命令末尾加 `--download`：

```powershell
python "$skill/scripts/fetch_photos.py" "$workbench" --place-id 'sensoji' --query "Senso-ji Asakusa Tokyo" --limit 3 --download
```

默认只检索元信息；加 `--download` 才会下载候选。`--limit` 只能为 1–3；默认请求宽度 `--width 2400`，可在 64–4096 内选择。API 可能返回更大的标准缩略图，最终 `width/height` 以下载文件实际解码尺寸为准，不能拿请求尺寸作质量验收。

先小批下载并检查可访问性、实际像素和构图，再安排封面与摄影大页。打不开、主体不符或尺寸不足时改选可用来源，不能用放大像素、重复照片或删除质量门槛填空。地点库确实没有可靠照片时，按地点库规范保留带完整实用信息的文字卡并记录查找结果；这不能替代封面和摄影大页所需的合格大图。更换来源后重新核对主体与署名，不沿用旧图的审核结论。

若已人工选定 Commons 文件，可用 `--file-title "File:来源页中的完整文件名.jpg"` 替代 `--query`。批量地点用 `--plan photo-plan.json`，文件是如下列表；每项只允许 `query` 或 `fileTitle` 其中一个。脚本逐项串行执行，一旦网络失败便停止，不会继续刷后面的地点。

```json
[
  {"placeId": "sensoji", "query": "Senso-ji Asakusa Tokyo"},
  {"placeId": "ueno-park", "query": "Ueno Park Tokyo"}
]
```

直接重跑同一命令即可使用缓存并跳过已完成且 SHA-256 一致的有效图片；`--refresh` 重新请求元信息，保留本地图片和人工核对记录。原文件版本或缩略图 URL 改变会产生新候选，必须重新实看，不能继承旧候选的身份结论。

## 限流、文件与失败记录

- 单工作台只允许一个获取进程；所有 HTTP 请求串行，正常请求之间至少隔 1 秒。
- 对 429、500/502/503/504、临时连接失败及 API `ratelimited/maxlag/readonly` 最多重试 3 次，基本退避为 2、4、8 秒。`Retry-After` 支持秒数和 HTTP 日期，实际等待取更长者；`maxlag` 至少等 5 秒。请求带 `maxlag=5`。403 等永久错误立即停止，不换域名、代理或 UA 绕过。
- `Retry-After` 超过 60 秒时保存冷却截止时间并退出。以后重跑也遵守该截止时间；`--refresh` 不会清掉它。不要删 `.photo-cache/network-state.json` 来绕过限流。
- `.photo-cache/` 保留 API 响应及取得时间；`photo-records.json` 每完成一次检索或下载即原子保存。图片先完整接收、用 Pillow 验证并解码，再用同目录临时文件和原子替换写入 `media/photo-candidates/`。失败不会安装 HTML 错误页或半张图片。
- 续跑粒度是“已完成的 API 请求/完整图片”，并非 HTTP Range 字节续传。被中断的单张图片会重新下载。单次响应上限 50 MiB，API JSON 上限 4 MiB；超限停止并记录错误，可改选较小缩略图。
- `no_results` 只表示本次查询没有返回候选；`failed/interrupted` 表示没有完成检索，不能登记成“已找过但无图”。找到候选也不等于有可用识别图。搜索成功、下载失败时保留成功检索记录和候选的 `downloadStatus: failed`。

## 输出格式与进入成品的步骤

`photo-records.json` 的顶层为 `schemaVersion: 1`、`searches: []`、`candidates: []`：

- `searches[]` 含 `searchId/placeId/query/fileTitle/status/checkedAt/candidateIds/fromCache`，可追溯实际查询与缓存时间。`lastError` 保存失败原因。
- `candidates[]` 含 `candidateId/placeId/fileTitle/page/author/license/licenseUrl/source/originalUrl/caption/credit`，以及 `commonsSha1`、元信息检查时间和缺失字段列表。成功下载后还有 `src/width/height/sha256/bytes`。`originalWidth/Height` 来自原图元信息，`apiWidth/Height` 来自缩略图元信息，`requestedWidth` 只是请求值。
- 新候选必定是 `reviewed: false`、`identityStatus: "unreviewed"`、`subjectPlaceId: null`、`role: null`。`placeId` 只表示“为哪个地点检索”，不是对照片主体的断言。作者、许可缺失时留空并列在 `missingMetadata`，不造出“已授权”结论。

只有完成下列人工核对后，才把候选登记到正式地点图片表：

1. 打开本地 `src` **实际看图**，对照 `page` 来源页与目标地点。核对建筑、店名、门面或产品主体、分店、城市与拍摄位置；街区氛围图不能冒充具体门店。检查像素与构图是否适合展示。标题和搜索词只能作为线索。
2. 回来源页补齐 `fileTitle/page/author/license/licenseUrl` 等缺项，核对许可条款、署名要求；Commons 上存在图片不代表任意使用方式都已获许可。写准确的中文 `caption`，不要沿用机器提取的模糊描述。
3. 在该候选中记录 `reviewed: true`、`identityStatus: "reviewed"`、`subjectPlaceId: 目标地点ID`、`role`（`venue/interior/product/area`）、`reviewedAt`、实际核对者 `reviewedBy` 和具体 `reviewNote`。只有地点本身 `identityScope: "area"` 才可使用 `role: "area"`。
4. 将这个已确认候选的 `src/page/caption/source/fileTitle/author/license/licenseUrl/credit/subjectPlaceId/reviewed/role` 等字段复制到 `place-photos.json[目标地点ID]`，同时保留 `candidateId/sha256/reviewedAt/reviewedBy/reviewNote` 便于追溯。不要复制仍是 `false/null` 的待审核字段来凑覆盖率。随后执行 `audit_directory.py`，再生成媒体核对拼图并实看成品。
5. 若实看候选不对题，记录具体拒绝原因；继续换查询或转官方来源。确实没有可用识别图时，用完整文字卡并在 `directory-plan.json.photoExceptions` 写入对应地点的实际检索结论。脚本不会自动替你新增这种例外。

## 测试与接口依据

运行 `python -m unittest discover -s scripts -p test_fetch_photos.py -v`。测试使用模拟网络，覆盖重试次数、两类 Retry-After、HTTP 200 maxlag、冷却跨进程续跑、403 停止、缓存恢复、截断下载、原子失败与未审核状态；不需要也不使用真实邮箱发网络请求。

实现核对依据（2026-11-12）：[Wikimedia User-Agent policy](https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_User-Agent_Policy) 要求描述性客户端名称与操作者联系方式；[API etiquette](https://www.mediawiki.org/wiki/API:Etiquette) 要求串行请求并尊重限流；[Search API](https://www.mediawiki.org/wiki/API:Search) 支持以 search generator 检索 File 命名空间；[Imageinfo API](https://www.mediawiki.org/wiki/API:Imageinfo) 提供来源 URL、尺寸与 HTML 格式的 extmetadata，说明缩略图实际宽度可能大于请求值；[maxlag 文档](https://www.mediawiki.org/wiki/Manual:Maxlag_parameter) 说明 HTTP 200 错误体、Retry-After 以及至少 5 秒的等待要求。
