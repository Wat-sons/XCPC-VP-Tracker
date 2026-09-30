#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把各种 JSON 数据打包成页面能直接 <script> 引入的 .js（避免 file:// 下的 CORS 限制）。

  vp-data.json        -> data.js          (window.XCPC_DATA)
  cf-progress.json    -> cf-progress.js   (window.CF_PROGRESS)
  extra-contests.json -> extra-contests.js(window.EXTRA_CONTESTS)

用法：python build_page_data.py
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

JOBS = [
    ("vp-data.json", "data.js", "XCPC_DATA"),
    ("cf-progress.json", "cf-progress.js", "CF_PROGRESS"),
    ("extra-contests.json", "extra-contests.js", "EXTRA_CONTESTS"),
]


def main():
    ok = 0
    for src, dst, var in JOBS:
        sp = os.path.join(BASE, src)
        if not os.path.isfile(sp):
            print("跳过（不存在）: %s" % src)
            continue
        with open(sp, encoding="utf-8") as f:
            data = json.load(f)
        text = "window.%s = %s;\n" % (var, json.dumps(data, ensure_ascii=False, indent=1))
        with open(os.path.join(BASE, dst), "w", encoding="utf-8") as f:
            f.write(text)
        n = ""
        if isinstance(data, dict) and "contests" in data:
            n = " (%d 条)" % (len(data["contests"]) if isinstance(data["contests"], (list, dict)) else 0)
        print("%-22s -> %-20s window.%s%s" % (src, dst, var, n))
        ok += 1
    print("完成 %d 个" % ok)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
