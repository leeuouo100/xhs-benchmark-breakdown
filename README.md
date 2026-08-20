# 小红书对标拆解专家 · xhs-benchmark-breakdown

一个 WorkBuddy / Claude 类 Agent 的 skill，用于**系统化拆解小红书对标账号与爆款笔记**，把"火不火"从感觉变成可量化、可复制的方法论。

## 功能

- **量化评分**：爆款指数公式 `(赞 + 藏×1.5 + 评×3) / max(粉丝,100)`，自动标注「低粉爆款 / 高收藏 / 高互动」。
- **深度账号画像**：人设三板斧、内容模式（垂直 vs 多元）、全量笔记结构化分析。
- **爆款笔记拆解**：开头钩子库、内容结构模型、11 种标题公式、评论区「下一步内容机会」。
- **行动路线图**：P0 / P1 / P2 可执行清单 + 三阶段路线图（P0 = 5 分钟能拍的，P1 = 24h 互动钩子，P2 = 月度转型方向）。

## 四步工作流

```
1. 量化找爆款  →  2. 深度拆账号/笔记  →  3. 提炼可复制公式  →  4. 行动路线图
```

## 安装

```bash
# 方式一：克隆到 WorkBuddy skills 目录
git clone https://github.com/leeuouo100/xhs-benchmark-breakdown.git ~/.workbuddy/skills/xhs-benchmark-breakdown

# 方式二：手动复制 SKILL.md + reference/ + templates/ + scripts/ 到 skills 目录
```

## 用法

在对话中用以下任意说法触发：

- "拆一下这个对标账号：<链接>"
- "拆这条爆款笔记：<链接>"
- "找找 XX 赛道的低粉爆款"
- "把这篇爆款结构改成我的原创稿"
- 或直接点名："用 xhs-benchmark-breakdown 拆解"

如果手里还没有数据，skill 会先按数据获取 SOP 帮你把账号 / 笔记 / 评论 / 视频抓下来，再进入拆解。

## 数据获取（没数据时）

拆解依赖真实数据。本 skill 提供基于 **opencli + 本机 Chrome** 的数据获取 SOP（详见 `reference/xhs-data-collection.md`），覆盖：

1. 抓取账号主页（粉丝数 + 公开笔记列表）
2. 抓取单篇笔记详情（赞 / 藏 / 评 / 标题 / 正文）
3. 抓取评论区（用户需求信号）
4. 下载视频 + 抽帧 + Whisper 转写口播
5. 整理成 `candidates.json` 喂给评分脚本

> 抓取依赖你本机已登录的浏览器，skill 不存储凭证、不模拟登录。

## 目录结构

```
xhs-benchmark-breakdown/
├── SKILL.md                        # 主入口：四步工作流与路由表
├── reference/
│   ├── xhs-breakdown-knowledge.md   # 钩子库/结构模型/标题公式/人设三板斧/藏赞比三档
│   └── xhs-data-collection.md       # 数据获取 SOP（opencli 抓取账号/笔记/评论/视频，含已知坑）
├── templates/
│   ├── account_deep_breakdown.md    # 账号深度拆解模板
│   ├── viral_note_breakdown.md      # 单篇爆款拆解模板
│   └── action_roadmap.md            # 行动路线图模板
└── scripts/
    ├── topic_scorer.py              # 爆款指数评分脚本（支持粉丝数缺失）
    └── build_candidates.py          # 一键聚合：user列表 + 批量note → candidates.json
```

## 边界

- 不凭空爬取小红书、不存储账号凭证；如用户尚无数据，按 SOP 用 opencli 辅助抓取（依赖本机已登录浏览器）。
- 不编造后台指标（阅读量 / 转化率 / 商业合作数据等），无法确认的信息明确标注。
- **粉丝数无法从 opencli 获取**（user/note 都不返回，WebFetch 主页常触发安全验证）；缺失时评分脚本标「粉丝未知」并用 100 作占位分母做账号内横向比较，不会误标「低粉爆款」。
- **Windows 注意**：Python 脚本里调用 opencli 需传绝对路径（如 `C:/Users/<user>/AppData/Roaming/npm/opencli.cmd`），且脚本内文件路径用 `D:/...` 而非 `/d/...`；opencli stdout 含非 UTF-8 字节需用 `errors="ignore"` 解码；`.cmd` 子进程可能输出 YAML 而非 JSON（解析需双兼容）。详见 `reference/xhs-data-collection.md` 第 8 节「已知坑」。

## 致谢

方法综合自公开的小红书拆解方法论；评分脚本改编自 SkillHub 的 `xhs-viral-rewrite` skill。
