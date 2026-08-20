# 数据获取 SOP（小红书）

本 skill 本身不做"凭空爬取"，但提供基于本机 **opencli + Chrome** 的数据获取流程，让你能稳定拿到拆解所需的账号 / 笔记 / 评论 / 视频数据，再喂给评分脚本与拆解模板。下面的命令都是已在 Windows + Git Bash 环境下验证过的真实写法。

---

## 0. 前置条件

1. **opencli** 已安装，且含 `xiaohongshu` 子命令（`opencli xiaohongshu --help` 可见 download / note / user / comments）。
2. 本机 **Chrome 已登录小红书账号**，opencli 通过浏览器桥接抓取（无需另外输密码）。
3. **确认 profile 已连接**（不同机器 profile id 不同，不要写死）：
   ```bash
   opencli profile list
   # 找状态为 connected 的那一行，记下它的 id
   opencli profile use <profile_id>
   ```
4. 音频处理依赖 **ffmpeg**；口播转写依赖 **openai-whisper**（建议装进 Python venv，不要全局装）。

---

## 1. 抓取账号主页（拿粉丝数 + 公开笔记列表）

```bash
opencli xiaohongshu user <user_id> -f json --window background
```

- `<user_id>` 取自主页 URL：`https://www.xiaohongshu.com/user/profile/<user_id>`
- 输出含：粉丝数、获赞与收藏总数、公开笔记列表（每条带标题 / 点赞数 / 封面）。
- 用这个拿到「粉丝基数」和「该账号全部候选笔记」。

---

## 2. 抓取单篇笔记详情（拿赞 / 藏 / 评 + 标题 + 正文）

```bash
# 用 note_id
opencli xiaohongshu note <note_id> -f json --window background

# 或用完整笔记 URL
opencli xiaohongshu note "<note_url>" -f json --window background
```

- `<note_id>` 取自首页 URL 的 `.../explore/<note_id>?xsec_token=...`
- 输出含：标题、正文、点赞 / 收藏 / 评论数、标签、发布时间。

---

## 3. 抓取评论区（拿用户需求信号）

```bash
opencli xiaohongshu comments "<note_url>" -f json --window background
```

- 评论区是「下一步内容机会」的核心来源（用户问了什么、想要什么材料 / 成品 / 教程）。

---

## 4. 下载视频 + 抽帧 + 转写口播（拆解画面与文案用）

```bash
# 4.1 下载视频与封面（会生成 video/<note_id>_1.mp4）
opencli xiaohongshu download "<note_url>" --output ./video -f json --window background

# 4.2 提取音频（中文口播 → mp3）
ffmpeg -i video/<note_id>_1.mp4 -vn -c:a libmp3lame -q:a 2 audio.mp3 -y

# 4.3 Whisper 转写口播文案
whisper audio.mp3 --model base --language Chinese --output_format txt --output_dir .

# 4.4 抽帧看画面（每 2 秒一帧，用于逐帧视觉拆解）
ffmpeg -i video/<note_id>_1.mp4 -vf fps=0.5 frames/f_%03d.jpg -y
```

> 提示：Whisper 对中文口播识别有误差，转写文本需人工校准；无声视频（纯 BGM + 字幕）则跳过 4.2 / 4.3，直接看抽帧 + 笔记正文即可。

---

## 5. 整理成 candidates.json（喂给评分脚本）

把同一账号下的候选笔记，整理成一个 JSON 数组，每条一行：

```json
[
  {"title":"绿了",   "likes":910, "collects":1259, "comments":12, "followers":800},
  {"title":"蜂蜜",   "likes":45,  "collects":30,   "comments":3,  "followers":800},
  {"title":"花艺",   "likes":120, "collects":200,  "comments":5,  "followers":800}
]
```

- `followers` 用第 1 步拿到的账号粉丝基数（同一账号下的笔记复用同一个值）。
- 缺某项数据时填 `0`；脚本仍能做「账号内横向比较」，只是爆款指数绝对值会偏低，需结合粉丝基数解读。

然后用评分脚本跑：

```bash
python scripts/topic_scorer.py --input candidates.json
```

---

## 6. 边界与合规

- 抓取依赖你本机**已登录的浏览器**，skill 不存储任何账号凭证、不模拟登录。
- 小红书有反爬与频率限制，批量抓取请控制节奏、遵守平台规则与 robots 政策。
- 无法从公开接口拿到的数据（阅读量、转化率、商业合作数据等）**绝不编造**，明确标注缺失。
- 抓取到的数据仅用于你自己的对标分析与创作参考，注意平台原创与合规要求。
