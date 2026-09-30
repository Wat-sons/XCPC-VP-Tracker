#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 QOJ 抓取"已通过的题目"，生成进度文件。

QOJ 是 UOJ 框架：/api/* 需要登录态，公开页面也会跳登录，
因此必须以某个账号登录后抓自己的提交。凭据从环境变量读取，不落盘：

    $env:QOJ_USER = "quchen"
    $env:QOJ_PASS = "你的密码"
    python scripts\\sync_qoj.py

流程：
  1) 用账号密码换到登录 cookie（UOJ 登录是普通表单 POST）
  2) 遍历 /submissions?submitter=<user> 分页，解析出
     contestId / 题号 / verdict
  3) 只保留 Accepted，输出 qoj-progress.json

注意：QOJ 的页面结构属于内部实现，若改版解析会失效；
脚本会把解析到的条数打印出来，条数为 0 时会明确报警而不是静默成功。
"""

import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import http.cookiejar

sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_URL = "https://qoj.ac"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) xcpc-vp-tracker/1.0"


def make_opener():
    cj = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))


def get(op, path, timeout=60):
    req = urllib.request.Request(BASE_URL + path, headers={"User-Agent": UA})
    with op.open(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace"), r.geturl()


def post(op, path, fields, timeout=60):
    data = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(BASE_URL + path, data=data, headers={
        "User-Agent": UA,
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": BASE_URL + path,
    })
    with op.open(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace"), r.geturl()


def login(op, user, pwd):
    html, _ = get(op, "/login")
    # UOJ 表单里通常带 _token（CSRF）
    m = re.search(r'name="_token"\s+value="([^"]+)"', html)
    fields = {"_token": m.group(1) if m else "",
              "username": user, "password": pwd,
              "remember": "on"}
    html2, url2 = post(op, "/login", fields)
    if "/login" in url2:
        return False, "登录后仍停在 /login（账号密码可能不对，或表单字段变了）"
    return True, url2


def parse_submissions(html):
    """从提交列表页解析出 (submissionId, contestId, problemId, verdict)。"""
    rows = []
    # UOJ 提交行里含有 /contest/<cid>/problem/<pid> 与 /submission/<sid>
    for m in re.finditer(
            r'href="/submission/(\d+)"[\s\S]{0,900}?'
            r'(?:/contest/(\d+)/problem/([A-Za-z0-9_]+)|/problem/([A-Za-z0-9_]+))'
            r'([\s\S]{0,900}?)</tr>', html):
        sid, cid, pid1, pid2, tail = m.groups()
        verdict = "Accepted" if re.search(r'Accepted|status-accepted', tail) else "Other"
        rows.append({"submissionId": int(sid), "contestId": int(cid) if cid else None,
                     "problemId": pid1 or pid2, "verdict": verdict})
    return rows


def main():
    user = os.environ.get("QOJ_USER")
    pwd = os.environ.get("QOJ_PASS")
    if not user or not pwd:
        print("请先设置环境变量 QOJ_USER / QOJ_PASS")
        return 2

    op = make_opener()
    ok, info = login(op, user, pwd)
    print("登录: %s  (%s)" % ("成功" if ok else "失败", info))
    if not ok:
        return 1

    # 确认登录态
    html, _ = get(op, "/user/profile/%s" % user)
    if "Please" in html and "login" in html and len(html) < 5000:
        print("警告：个人主页仍像登录页，可能没登上")

    all_rows, page = [], 1
    while page <= 40:
        html, _ = get(op, "/submissions?submitter=%s&page=%d" % (urllib.parse.quote(user), page))
        rows = parse_submissions(html)
        print("  第 %d 页解析到 %d 条" % (page, len(rows)))
        if not rows:
            break
        all_rows.extend(rows)
        page += 1
        time.sleep(1)

    if not all_rows:
        print("")
        print("!! 一条都没解析到。QOJ 的页面结构可能变了，或登录没生效。")
        print("!! 请把这一页 HTML 存下来给我，我按实际结构调整解析。")
        return 1

    # 去重
    seen, uniq = set(), []
    for r in all_rows:
        k = r["submissionId"]
        if k in seen:
            continue
        seen.add(k)
        uniq.append(r)

    by_contest = {}
    for r in uniq:
        if r["contestId"] is None:
            continue
        c = by_contest.setdefault(r["contestId"], {"problems": {}, "accepted": 0})
        p = c["problems"].setdefault(r["problemId"], {"ok": False, "tries": 0})
        p["tries"] += 1
        if r["verdict"] == "Accepted":
            p["ok"] = True
    for c in by_contest.values():
        c["accepted"] = sum(1 for v in c["problems"].values() if v["ok"])

    payload = {
        "source": "qoj",
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "user": user,
        "summary": {"submissions": len(uniq), "contests": len(by_contest)},
        "contests": {str(k): v for k, v in by_contest.items()},
    }
    with open(os.path.join(BASE, "qoj-progress.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print("完成：%d 条提交，覆盖 %d 场比赛" % (len(uniq), len(by_contest)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
