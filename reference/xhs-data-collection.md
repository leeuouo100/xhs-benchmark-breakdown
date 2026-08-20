# 数据获取 SOP（小红书）

本 skill 本身不做"凭空爬取"，但提供基于本机 **opencli + Chrome** 的数据获取流程，让你能稳定拿到拆解所需的账号 / 笔记 / 评论 / 视频数据，再喂给评分脚本与拆解模板。下面的命令都是已在 **Windows + Git Bash + 原生 Python** 环境下**实跑验证**过的真实写法（不是凭空写的）。

> ⚠️ **关键结论先说**：opencli 的 `user` / `note` 命令**都不返回粉丝数**；`user` 只给笔记列表+点赞+URL，`note` 才给收藏/评论。粉丝数只能从主页 WebFetch 碰运气（常触发安全验证，不可靠），缺失时按"粉丝未知"处理即可，不影响账号内横向比较。

---

## 0. 前置条件

1. **opencli** 已安装（`npm install -g @jackwener/opencli`），含 `xiaohongshu` 子命令：`user` / `note` / `comments` / `download` / `search` / `feed`。
2. 本机 **Chrome 已登录小红书账号**，opencli 通过浏览器桥接抓取（无需另外输密码）。
3. **确认 profile 已连接**（不同机器 profile id 不同，不要写死）：
   ```bash
   opencli profile list
   # 找状态为 connected 的那一行，记下它的 id
   opencli profile use <profile_id>
   ```
4. 音频处理依赖 **ffmpeg**；口播转写依赖 **openai-whisper**（建议装进 Python venv，不要全局装）。
5. **Windows 专用**：在 Python 脚本里调用 opencli 时，要传 opencli 的**绝对路径**（如 `C:/Users/<user>/AppData/Roaming/npm/opencli.cmd`），原生 Windows Python 在 PATH 里找不到它；且脚本内的文件路径要用 `D:/...` 格式，不要用 Git Bash 的 `/d/...`。

---

## 1. 找对标账号（search，可选）

如果你还没有目标账号的 user_id，先用搜索发现：

```bash
opencli xiaohongshu search "松果挂件" -f json --window background
```

- 返回笔记列表，每条含 `user_id` / 笔记 `url` / 标题 / 点赞。
- 从中挑一个账号，取其 user_id 进入第 2 步。

---

## 2. 抓取账号主页（拿笔记列表 + 点赞 + 完整 URL）

```bash
opencli xiaohongshu user <user_id> -f json --window background > user_raw.json
```

- `<user_id>` 取自主页 URL：`https://www.xiaohongshu.com/user/profile/<user_id>`
- **实际返回**：公开笔记列表，每条含 `id` / `title` / `type` / `likes` / `cover` / **`url`（完整签名 URL，含 xsec_token）**。
- **不包含**：粉丝数、获赞总数、收藏、评论（这是常见误解，已核实）。
- 粉丝数无法从本命令获取；如需，可用 WebFetch 主页尝试，但常触发安全验证，不可靠——缺失就标"粉丝未知"。

---

## 3. 抓取单篇笔记详情（必须传完整签名 URL）

```bash
opencli xiaohongshu note "<note_url>" -f json --window background
```

- **必须传完整 URL**（含 `xsec_token`），**不能只传 note_id**——opencli v1.8.x 已强制要求签名 URL，否则报 `requires a full signed URL`。
- `note_url` 直接取自第 2 步 `user` 列表里的 `url` 字段。
- **实际返回**：`title` / `author` / `content` / **`likes` / `collects` / `comments`** / `tags`。
- 用这个拿到每篇笔记的**收藏与评论**（user 列表里没有）。
- ⚠️ **在 Python 子进程里调 `.cmd` 时，URL 里的 `&xsec_source` 会被 Windows cmd 当成命令分隔符**，导致整个 `-f json` 参数失效、opencli 退化返回 **YAML**（`- field: ... \n  value: ...`）而非 JSON。**真正的修复**：调用时必须 `shell=True` 且把 URL 用**双引号包裹**（见 `scripts/build_candidates.py` 的 `run_note`），强制 cmd 不拆参、`-f json` 生效，opencli 返回 JSON（最稳）。即便退化为 YAML，解析时也需 JSON/YAML 双兼容，且 YAML 分支要去单/双引号（见下方坑 8）。

---

## 4. 抓取评论区（需求信号）

```bash
opencli xiaohongshu comments "<note_url>" -f json --window background > comments.json
```

- 返回评论数组，每条含 `author` / `text` / `likes` / `time` / `is_reply`。
- 评论区是「下一步内容机会」的核心来源（用户问了什么、想要什么）。

---

## 5. 下载视频 + 抽帧 + 转写口播（拆解画面与文案用）

```bash
# 5.1 下载视频与封面
opencli xiaohongshu download "<note_url>" --output ./video -f json --window background

# 5.2 提取音频（中文口播 → mp3）
ffmpeg -i video/<note_id>_1.mp4 -vn -c:a libmp3lame -q:a 2 audio.mp3 -y

# 5.3 Whisper 转写口播文案
whisper audio.mp3 --model base --language Chinese --output_format txt --output_dir .

# 5.4 抽帧看画面（每 2 秒一帧）
ffmpeg -i video/<note_id>_1.mp4 -vf fps=0.5 frames/f_%03d.jpg -y
```

> Whisper 对中文口播识别有误差，转写文本需人工校准；无声视频（纯 BGM + 字幕）则跳过 5.2 / 5.3，直接看抽帧 + 笔记正文即可。

---

## 6. 一键聚合 candidates.json（推荐，替代手动整理）

手动逐篇整理容易出错且慢。用脚本自动吃 `user` 列表 + 批量调 `note`：

```bash
python scripts/build_candidates.py \
  --user user_raw.json \
  --out candidates.json \
  --opencli "C:/Users/<user>/AppData/Roaming/npm/opencli.cmd"
  # --followers 800   # 可选：若你通过其他途径知道了粉丝数，填这里；缺省为 None（标注"粉丝未知"）
```

- 脚本会对每篇笔记调用 `note <url>` 拿 `collects` / `comments`，输出标准 `candidates.json`。
- 已内置处理：opencli 绝对路径、Windows 路径、`errors="ignore"` 解码、JSON/YAML 双格式兼容。
- 跑完直接用 `topic_scorer.py --input candidates.json` 评分。

---

## 7. 手动整理 candidates.json（脚本不可用时的兜底）

把同一账号下的候选笔记整理成 JSON 数组，每条一行：

```json
[
  {"title":"油柑配咖啡","likes":538,"collects":341,"comments":169,"followers":null},
  {"title":"本命电脑","likes":505,"collects":203,"comments":56,"followers":null}
]
```

- `followers` 用第 2 步能拿到的粉丝基数；**拿不到就填 `null`**（评分脚本会标"粉丝未知"、用 100 作占位分母做账号内横向比较，不会误标"低粉爆款"）。
- 缺某项数据时填 `0`；脚本仍能做账号内横向比较。

然后用评分脚本跑：

```bash
python scripts/topic_scorer.py --input candidates.json
```

---

## 8. 已知坑（实跑验证发现的真实问题）

1. **`user` 不返回粉丝数 / 收藏 / 评论**，只给点赞 + URL。粉丝数只能 WebFetch（常失败）。
2. **`note` 必须传完整签名 URL**（含 `xsec_token`），不能只传 note_id。
3. **Python 子进程找不到 opencli** → 必须传 opencli 绝对路径（Windows 用 `opencli.cmd`）。
4. **原生 Windows Python 不认 `/d/...` 路径** → 用 `D:/...` 格式。
5. **opencli stdout 含非 UTF-8 字节** → `text=True` 解码崩溃，改用 `encoding="utf-8", errors="ignore"`。
6. **`.cmd` 在子进程下输出 YAML 而非 JSON**（URL 里的 `&` 被 cmd 拆裂，`-f json` 失效）→ 解析需 JSON/YAML 双兼容。
7. **评分脚本粉丝缺失会误标"低粉爆款"** → 已修正：粉丝未知时标"粉丝未知"且不误标低粉爆款。
8. **YAML 退化分支的正则没去引号** → `value: '1309'` 带单引号，`int("'1309'")` 失败被 catch 成 0，收藏/评论全盘为 0。修复：解析时对 value 同时 `strip('"').strip("'")`（`clean_int`）。此坑与坑 6 同源：只有彻底修好 `&` 拆参让 opencli 走 JSON 分支，才能根除；YAML 兜底只是双保险。

---

## 9. 边界与合规

- 抓取依赖你本机**已登录的浏览器**，skill 不存储任何账号凭证、不模拟登录。
- 小红书有反爬与频率限制，批量抓取请控制节奏、遵守平台规则与 robots 政策。
- 无法从公开接口拿到的数据（阅读量、转化率、商业合作数据等）**绝不编造**，明确标注缺失。
- 抓取到的数据仅用于你自己的对标分析与创作参考，注意平台原创与合规要求。
