#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小红书爆款指数评分脚本（xhs-benchmark-breakdown 配套）

用法：
    python topic_scorer.py --input candidates.json

candidates.json 格式（数组）：
    [
      {"title": "标题", "likes": 910, "collects": 1259, "comments": 12, "followers": null},
      ...
    ]

字段说明：
    likes/collects/comments : 互动数据（整数）
    followers               : 粉丝数。未知时填 null，
                              脚本用 100 作占位分母（仅在账号内做横向比较），
                              且不误标「低粉爆款」（粉丝未知无法判定低粉）。

爆款指数口径：
    爆款指数 = (赞 + 藏×1.5 + 评×3) / max(粉丝, 100)
    越高代表「单位粉丝的互动产出」越强。
"""

import json
import argparse
import sys


def load_candidates(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "notes" in data:
        data = data["notes"]
    return data


def score_note(n):
    likes = float(n.get("likes") or 0)
    collects = float(n.get("collects") or 0)
    comments = float(n.get("comments") or 0)

    raw_followers = n.get("followers")
    followers_known = isinstance(raw_followers, (int, float)) and raw_followers > 0
    followers = float(raw_followers) if followers_known else None

    engagement = likes + collects * 1.5 + comments * 3.0
    denominator = followers if followers_known else 100.0
    viral_index = engagement / max(denominator, 100.0)
    collect_ratio = collects / max(likes, 1.0)

    return {
        "title": n.get("title", "(无标题)"),
        "followers": int(followers) if followers_known else None,
        "followers_known": followers_known,
        "likes": int(likes),
        "collects": int(collects),
        "comments": int(comments),
        "viral_index": round(viral_index, 2),
        "collect_ratio": round(collect_ratio, 2),
        "tags": tag_note(followers_known, followers, viral_index, collect_ratio, comments),
    }


def tag_note(known, followers, viral_index, collect_ratio, comments):
    tags = []
    if known and followers < 5000 and viral_index > 0.5:
        tags.append("低粉爆款")
    if not known:
        tags.append("粉丝未知")
    if collect_ratio >= 1.0:
        tags.append("高收藏")
    if comments >= 50:
        tags.append("高互动")
    return "、".join(tags) if tags else "常规"


def main():
    ap = argparse.ArgumentParser(description="小红书爆款指数评分")
    ap.add_argument("--input", "-i", required=True, help="candidates.json 路径")
    ap.add_argument("--top", type=int, default=999, help="只显示前 N 条")
    args = ap.parse_args()

    notes = load_candidates(args.input)
    scored = [score_note(n) for n in notes]
    scored.sort(key=lambda s: s["viral_index"], reverse=True)

    print(f"{'#':<4}{'标题':<26}{'粉丝':>8}{'赞':>7}{'藏':>7}{'评':>7}{'爆款指数':>10}{'藏赞比':>8}  标签")
    print("-" * 92)
    for i, s in enumerate(scored[: args.top], 1):
        title = s["title"][:24]
        followers = s["followers"] if s["followers_known"] else "?"
        print(
            f"{i:<4}{title:<26}{followers:>8}{s['likes']:>7}{s['collects']:>7}"
            f"{s['comments']:>7}{s['viral_index']:>10}{s['collect_ratio']:>8}  {s['tags']}"
        )
    print()
    print(f"共 {len(scored)} 条候选，已按爆款指数降序排列。")
    print("爆款指数 = (赞 + 藏×1.5 + 评×3) / max(粉丝,100)；粉丝未知时分母取 100 且仅做账号内横向比较。")


if __name__ == "__main__":
    main()
