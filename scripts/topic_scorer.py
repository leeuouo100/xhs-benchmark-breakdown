#!/usr/bin/env python3
"""小红书低粉爆款选题评分脚本。

输入：JSON 数组，每条含 title, likes, collects, comments, followers
输出：按「爆款指数」降序排列的清单，并标注标签。

设计口径（与 reference/xhs-viral-knowledge.md 一致）：
  爆款指数 = (赞 + 藏×1.5 + 评×3) / max(粉丝, 100)
  评论权重最高（代表讨论/传播），收藏次之（代表收藏价值）。
  专门识别「低粉高互动」的潜力内容。
"""
import argparse
import json
import sys


def score_note(n: dict) -> dict:
    likes = float(n.get("likes", 0) or 0)
    collects = float(n.get("collects", 0) or 0)
    comments = float(n.get("comments", 0) or 0)
    followers = float(n.get("followers", 0) or 0)

    engagement = likes + collects * 1.5 + comments * 3.0
    viral_index = engagement / max(followers, 100.0)
    collect_ratio = collects / max(likes, 1.0)

    return {
        "title": n.get("title", "(无标题)"),
        "followers": int(followers),
        "likes": int(likes),
        "collects": int(collects),
        "comments": int(comments),
        "viral_index": round(viral_index, 2),
        "collect_ratio": round(collect_ratio, 2),
        "tags": tag_note(followers, viral_index, collect_ratio, comments),
    }


def tag_note(followers: float, viral_index: float, collect_ratio: float, comments: float) -> str:
    tags = []
    if followers < 5000 and viral_index > 0.5:
        tags.append("低粉爆款")
    if collect_ratio >= 1.0:
        tags.append("高收藏")
    if comments >= 50:
        tags.append("高互动")
    return "、".join(tags) if tags else "常规"


def main() -> None:
    p = argparse.ArgumentParser(description="小红书低粉爆款选题评分")
    p.add_argument("--input", required=True, help="候选笔记 JSON 文件路径")
    p.add_argument("--top", type=int, default=0, help="只输出前 N 条（0=全部）")
    args = p.parse_args()

    try:
        with open(args.input, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"读取输入失败: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(data, list):
        print("输入必须是 JSON 数组", file=sys.stderr)
        sys.exit(1)

    scored = [score_note(n) for n in data]
    scored.sort(key=lambda x: x["viral_index"], reverse=True)
    if args.top > 0:
        scored = scored[: args.top]

    header = f"{'排名':<4}{'标题':<26}{'粉丝':>8}{'赞':>7}{'藏':>7}{'评':>7}{'爆款指数':>10}{'收藏比':>8}  标签"
    print(header)
    print("-" * 100)
    for i, s in enumerate(scored, 1):
        title = s["title"][:24]
        print(f"{i:<4}{title:<26}{s['followers']:>8}{s['likes']:>7}{s['collects']:>7}{s['comments']:>7}{s['viral_index']:>10}{s['collect_ratio']:>8}  {s['tags']}")

    print()
    print(f"共 {len(scored)} 条候选，已按爆款指数降序排列。")
    print("爆款指数 = (赞 + 藏×1.5 + 评×3) / max(粉丝,100)，越高代表单位粉丝的互动产出越强。")


if __name__ == "__main__":
    main()
