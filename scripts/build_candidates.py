#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_candidates.py —— 一键把 opencli 抓取的账号主页 JSON 聚合成 candidates.json

输入：opencli `user <user_id> -f json` 保存的文件（JSON 数组，每条含 id/title/likes/url）
输出：candidates.json（数组，每条含 title/likes/collects/comments/followers）

已修复的 Windows 真实坑（实跑 2 个账号、多轮验证）：
  1. opencli 子进程需传绝对路径（Windows 原生 Python 的 PATH 不含 npm 全局路径）→ --opencli 参数
  2. 输出目录可能不存在 → os.makedirs(exist_ok=True)
  3. 原生 Windows Python 不认 /d/... Git Bash 路径 → 调用方用 D:/... 格式
  4. opencli stdout 含非 UTF-8 字节（中文环境）→ encoding="utf-8", errors="ignore"
  5. 【关键】opencli .cmd 子进程里，URL 的 &xsec_source 会被 Windows cmd 当作命令分隔符，
     导致 -f json 失效、opencli 退化返回 YAML → 必须用 shell=True 且把 URL 用双引号包裹，
     确保 cmd 不拆参、-f json 生效，opencli 返回 JSON（最稳）。
  6. YAML 退化分支的正则没去引号 → value: '1309' 带单引号 int() 失败变 0；
     已对 value 同时 strip 单/双引号兜底（即使退化到 YAML 也能解析）。
  7. user 命令不返回 收藏/评论 → 必须逐篇调 note 补；note 必须传完整签名 URL（不能用 note_id）
  8. 粉丝数 opencli 不返回 → followers 统一填 null，交由 topic_scorer.py 处理

用法：
    python build_candidates.py \
        --user "D:/path/user_raw.json" \
        --out "D:/path/candidates.json" \
        --opencli "C:/Users/leeway/AppData/Roaming/npm/opencli.cmd"
"""

import json
import subprocess
import argparse
import os
import re
import sys


def extract_json_array(raw):
    """从混合输出中提取第一个 JSON 数组。"""
    s = raw.find("[")
    e = raw.rfind("]")
    if s != -1 and e != -1 and e > s:
        try:
            return json.loads(raw[s : e + 1])
        except Exception:
            return None
    return None


def parse_yaml_fields(raw):
    """opencli 默认 YAML 输出：'- field: likes\\n  value: 123'。"""
    out = {}
    pat = re.compile(
        r"-\s*field:\s*(\w+)\s*\n\s*value:\s*(.+?)(?=\n\s*-\s*field:|\Z)", re.S
    )
    for m in pat.finditer(raw):
        f = m.group(1).strip()
        v = m.group(2).strip().strip('"').strip("'")  # 去单/双引号兜底
        out[f] = v
    return out


def clean_int(v):
    try:
        return int(str(v).replace(",", "").strip().strip("'").strip('"') or 0)
    except Exception:
        return 0


def parse_note_fields(raw):
    """优先按 JSON 解析，失败退化为 YAML。"""
    arr = extract_json_array(raw)
    if arr:
        out = {}
        for item in arr:
            if not isinstance(item, dict):
                continue
            f = item.get("field")
            v = item.get("value")
            if f in ("likes", "collects", "comments"):
                out[f] = clean_int(v)
        if out:
            return out
    # 退化 YAML
    y = parse_yaml_fields(raw)
    return {f: clean_int(y.get(f, 0)) for f in ("likes", "collects", "comments")}


def run_note(opencli_bin, url):
    """调 opencli note。URL 必须双引号包裹 + shell=True，否则 Windows cmd 把 & 拆参。"""
    try:
        cmd = f'"{opencli_bin}" xiaohongshu note "{url}" -f json'
        proc = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            encoding="utf-8",
            errors="ignore",
            timeout=120,
        )
        raw = proc.stdout or ""
    except Exception as e:
        print(f"  [warn] 调用失败: {e}", file=sys.stderr)
        return {}
    return parse_note_fields(raw)


def main():
    ap = argparse.ArgumentParser(description="聚合 opencli 抓取数据为 candidates.json")
    ap.add_argument("--user", required=True, help="opencli user 命令保存的 JSON 文件")
    ap.add_argument("--out", required=True, help="输出 candidates.json（建议 Windows 路径 D:/...）")
    ap.add_argument(
        "--opencli",
        default="opencli",
        help="opencli 可执行绝对路径；Windows 用 .../npm/opencli.cmd",
    )
    args = ap.parse_args()

    with open(args.user, "r", encoding="utf-8", errors="ignore") as f:
        notes = json.load(f)

    results = []
    for i, n in enumerate(notes, 1):
        url = n.get("url")
        title = n.get("title", "(无标题)")
        likes = clean_int(n.get("likes", 0))
        print(f"[{i}/{len(notes)}] 抓取《{title[:18]}》…", file=sys.stderr)
        fields = run_note(args.opencli, url) if url else {}
        results.append(
            {
                "title": title,
                "likes": likes,
                "collects": fields.get("collects", 0),
                "comments": fields.get("comments", 0),
                "followers": None,
            }
        )

    out_dir = os.path.dirname(args.out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"已生成 {args.out}，共 {len(results)} 条。", file=sys.stderr)


if __name__ == "__main__":
    main()
