#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_candidates.py — 小红书对标拆解·数据聚合脚本

把 opencli 抓回来的「账号主页列表」+ 逐篇「笔记详情」自动聚合成
评分脚本 topic_scorer.py 需要的 candidates.json。

用法：
    python build_candidates.py --user user_raw.json --out candidates.json [--followers 800] [--opencli /path/to/opencli]

参数：
    --user      opencli `xiaohongshu user <id> -f json` 的输出文件（笔记列表，含完整 URL）
    --out       输出 candidates.json 的路径
    --followers 账号粉丝数。opencli 的 user/note 都不返回粉丝数，需从主页 WebFetch
                或人工填入；缺省填 None（脚本仍能做账号内横向比较）
    --opencli   opencli 可执行路径。默认 "opencli"（依赖 PATH）。
                ⚠️ Windows 上若用原生 Python 跑且 PATH 不含 npm 全局路径，
                需显式传入，例如：
                --opencli "C:/Users/<user>/AppData/Roaming/npm/opencli.cmd"

重要限制（opencli v1.8.x）：
    - `note` 命令【必须传完整签名 URL】（含 xsec_token），不能只传 note_id。
    - `user` 命令只返回笔记列表 + 每篇点赞数，不返回粉丝数 / 收藏 / 评论；
      收藏与评论需逐篇调 `note` 补充。

依赖：opencli 可用（默认 PATH，或经 --opencli 指定），且 profile 已连接。
"""
import json
import subprocess
import sys
import os


def extract_json_array(text):
    """从 opencli 的混合输出（含 node warning / update 提示）里截取 JSON 数组。"""
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except Exception:
        return None


def _to_int(v):
    try:
        return int(str(v).replace(",", "").strip().strip("'").strip('"') or 0)
    except Exception:
        return 0


def _parse_yaml_fields(raw):
    """opencli 在 Windows 子进程（.cmd）环境下可能输出 YAML 而非 JSON：
    '- field: likes\\n  value: '538'' —— 用正则提取。"""
    import re

    out = {}
    lines = raw.splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"^\s*-\s*field:\s*(\w+)\s*$", line)
        if not m:
            continue
        key = m.group(1)
        if i + 1 < len(lines):
            vm = re.match(r"^\s*value:\s*(.*)$", lines[i + 1])
            if vm:
                val = vm.group(1).strip().strip("'").strip('"')
                if key in ("likes", "collects", "comments"):
                    out[key] = _to_int(val)
    return out


def parse_note_fields(raw):
    """opencli note 输出可能是 JSON（[{field,value}...]）或 YAML
    （- field: ..\\n  value: ..）。两种都兼容，提取互动数据。"""
    arr = extract_json_array(raw)
    if arr:
        out = {}
        for item in arr:
            if not isinstance(item, dict):
                continue
            f = item.get("field")
            v = item.get("value")
            if f in ("likes", "collects", "comments"):
                out[f] = _to_int(v)
        if any(k in out for k in ("likes", "collects", "comments")):
            return out
    # fallback: JSON 没解析到有效字段时，试 YAML
    return _parse_yaml_fields(raw)


def main():
    args = sys.argv[1:]
    user_path = None
    out_path = "candidates.json"
    followers = None
    opencli_bin = "opencli"
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("--user", "-u"):
            user_path = args[i + 1]
            i += 2
        elif a in ("--out", "-o"):
            out_path = args[i + 1]
            i += 2
        elif a in ("--followers", "-f"):
            followers = args[i + 1]
            i += 2
        elif a in ("--opencli",):
            opencli_bin = args[i + 1]
            i += 2
        else:
            i += 1

    if not user_path or not os.path.exists(user_path):
        print(
            "用法: python build_candidates.py --user user_raw.json --out candidates.json "
            "[--followers 800] [--opencli /path/to/opencli]"
        )
        sys.exit(1)

    if followers is not None:
        try:
            followers = int(followers)
        except Exception:
            followers = None

    with open(user_path, encoding="utf-8") as f:
        notes = json.load(f)

    print(f"账号笔记数: {len(notes)}，开始逐篇调 note 拿收藏/评论...\n")

    candidates = []
    for idx, n in enumerate(notes, 1):
        title = n.get("title", "")
        note_id = n.get("id", "")
        likes = int(str(n.get("likes", 0)).replace(",", "") or 0)
        url = n.get("url", "")
        collects = None
        comments = None

        if url:
            try:
                proc = subprocess.run(
                    [opencli_bin, "xiaohongshu", "note", url, "-f", "json"],
                    capture_output=True,
                    encoding="utf-8",
                    errors="ignore",
                    timeout=120,
                )
                fields = parse_note_fields(proc.stdout)
                collects = fields.get("collects")
                comments = fields.get("comments")
                if "likes" in fields:
                    likes = fields["likes"]
            except Exception as e:
                print(f"  ! [{idx}] note 调用失败 {note_id}: {e}", file=sys.stderr)

        collects = collects if collects is not None else 0
        comments = comments if comments is not None else 0
        candidates.append(
            {
                "title": title,
                "likes": likes,
                "collects": collects,
                "comments": comments,
                "followers": followers,
                "note_id": note_id,
            }
        )
        print(
            f"  [{idx:2d}/{len(notes)}] {title[:22]:<22} 赞{likes:>4} 藏{collects:>4} 评{comments:>4}"
        )

    out_dir = os.path.dirname(os.path.abspath(out_path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(candidates, f, ensure_ascii=False, indent=2)

    print(
        f"\n✅ 已生成 {out_path}（{len(candidates)} 条，followers={followers}）"
    )


if __name__ == "__main__":
    main()
