#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 extra-contests.json：把 CF 上打过、但链接表没收的比赛补进面板。

名字来源优先级：
  1) _gym_unknown.txt（之前一次性抓好的 43 个 Gym 名字，直接复用，不再打 CF）
  2) 普通 Round 用 contest.standings 现抓（数量少，加节流）

只补 status 为 vp / contest 的比赛；纯 practice 的不补（不是 VP，也没必要进面板）。
"""
import json
import os
import re
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
BASE = r"D:\Claude Code project\projects\XCPC-VP-Tracker"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) xcpc-vp-tracker/1.0"


def load_cached_names():
    """读取 Gim 名字缓存。优先用 _gym_names.txt（gid\\t名字），
    兼容早期的 _gym_unknown.txt（对齐的表格，容易截断，仅作后备）。"""
    names = {}

    p1 = os.path.join(BASE, "_gym_names.txt")
    if os.path.isfile(p1):
        with open(p1, encoding="utf-8") as f:
            for line in f:
                parts = line.rstrip("\n").split("\t", 1)
                if len(parts) == 2 and parts[0].strip().isdigit() and parts[1].strip():
                    names[int(parts[0])] = parts[1].strip()
        return names

    p = os.path.join(BASE, "_gym_unknown.txt")
    if not os.path.isfile(p):
        return names
    with open(p, encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^(\d{5,7})\s+(vp|contest|practice)\s+\S+\s+\d+\s+(.+)$", line.strip())
            if not m:
                continue
            gid, name = int(m.group(1)), m.group(3).strip()
            name = re.sub(r"^Dashboard\s*-\s*", "", name)      # 去掉 CF 页面前缀
            name = re.sub(r"\s*\d{4}-\d{2}-\d{2}\s*$", "", name)  # 去掉日期列
            name = re.sub(r"\s*\(\d+\)$", "", name).strip()
            if not name or name.startswith("(抓取失败"):
                continue
            names[gid] = name
    return names


UA_BROWSER = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "Chrome/120 Safari/537.36")


def gym_name(gid):
    """抓 Gym 比赛页的 <title> 拿真实比赛名（比 contest.standings 轻量得多）。"""
    for attempt in range(3):
        try:
            u = "https://codeforces.com/gym/%d" % gid
            req = urllib.request.Request(u, headers={"User-Agent": UA_BROWSER,
                                                     "Accept-Language": "en"})
            with urllib.request.urlopen(req, timeout=45) as r:
                html = r.read().decode("utf-8", "replace")
            m = re.search(r"<title>(.*?)</title>", html, re.S)
            if m:
                n = re.sub(r"\s+", " ", m.group(1)).strip()
                n = re.sub(r"^Dashboard\s*-\s*", "", n)
                n = re.sub(r"\s*-\s*Codeforces\s*$", "", n).strip()
                if n:
                    return n
        except Exception as e:                                # noqa: BLE001
            print("    gym %d 重试 %d: %s" % (gid, attempt + 1, type(e).__name__))
            time.sleep(3 + attempt * 4)
    return None


def round_name(cid):
    """普通 Round 也没必要调 standings（大赛响应 6~20MB，极慢）。
    直接抓比赛页的 <title>，几十 KB 就够。"""
    for attempt in range(3):
        try:
            u = "https://codeforces.com/contest/%d" % cid
            req = urllib.request.Request(u, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
                "Accept-Language": "en"})
            with urllib.request.urlopen(req, timeout=45) as r:
                html = r.read().decode("utf-8", "replace")
            m = re.search(r"<title>(.*?)</title>", html, re.S)
            if m:
                n = re.sub(r"\s+", " ", m.group(1)).strip()
                return re.sub(r"\s*-\s*Codeforces\s*$", "", n)
        except Exception as e:                                # noqa: BLE001
            print("    重试 %d: %s" % (attempt + 1, type(e).__name__))
            time.sleep(3 + attempt * 4)
    return None


def classify(name, kind):
    """判断比赛类型，返回 (主类别, 全部适用标签)。

    很多比赛是复合的，例如
      "2023 Jiangsu Collegiate Programming Contest, 2023 National Invitational of CCPC (Hunan)"
    同时是省赛和国赛邀请赛；只贴一个标签会丢信息，所以主类别用于筛选、tags 用于展示。
    """
    n = name or ""
    if re.search(r"Div\.\s*\d|Division\s*\d", n):
        return "cf-div", ["cf-div"]
    if re.search(r"Educational", n, re.I):
        return "cf-edu", ["cf-edu"]
    if kind == "round" and re.search(r"Codeforces Round", n, re.I):
        return "cf-round", ["cf-round"]

    tags = []
    if re.search(r"Invitational|邀请", n):
        tags.append("invitational")
    if re.search(r"National", n):
        tags.append("national")
    if re.search(r"Provincial|省", n):
        tags.append("provincial")
    if re.search(r"Online", n, re.I):
        tags.append("online")
    if re.search(r"Collegiate Programming Contest|大学生程序设计", n):
        tags.append("collegiate")

    if not tags:
        tags = ["gym-other"]
    # 主类别取"级别最高"的那个，用于筛选和排序；tags 保留全部
    for pref in ("invitational", "national", "provincial", "online", "collegiate", "gym-other"):
        if pref in tags:
            return pref, tags
    return "gym-other", ["gym-other"]


def main():
    cf = json.load(open(os.path.join(BASE, "cf-progress.json"), encoding="utf-8"))
    page = json.load(open(os.path.join(BASE, "vp-data.json"), encoding="utf-8"))
    cache = load_cached_names()
    print("复用已抓好的 Gym 名字: %d 个" % len(cache))

    known = set()
    for c in page["contests"]:
        for l in c["links"]:
            if l["kind"] == "CF Gym":
                s = l["url"].rstrip("/").split("/")[-1]
                if s.isdigit():
                    known.add(int(s))

    extra = []
    names_dirty = False
    todo = [int(k) for k in cf["contests"]
            if int(k) not in known and cf["contests"][k]["status"] in ("vp", "contest")]
    todo.sort()
    print("需要补入 %d 场（vp + contest）" % len(todo))

    for cid in todo:
        v = cf["contests"][str(cid)]
        is_gym = cid >= 100000
        kind = "gym" if is_gym else "round"
        if is_gym:
            name = cache.get(cid)
            if not name:
                # 缓存没命中就现抓一次（并写回缓存，避免下次再抓）
                name = gym_name(cid)
                if name:
                    cache[cid] = name
                    names_dirty = True
                time.sleep(1.0)
            name = name or ("Codeforces Gym %d" % cid)
        else:
            name = round_name(cid) or ("Codeforces Round %d" % cid)
            time.sleep(2)
        # 统一清洗：CF 标题里的 Dashboard 前缀 / 尾部日期
        name = re.sub(r"^Dashboard\s*-\s*", "", name or "")
        name = re.sub(r"\s*\d{4}-\d{2}-\d{2}\s*$", "", name).strip()
        cat, cats = classify(name, kind)
        extra.append({
            "contestId": cid,
            "kind": kind,
            "name": name,
            "category": cat,
            "categories": cats,
            "status": v["status"],
            "solvedCount": v["solvedCount"],
            "problemCount": v["problemCount"],
            "problems": v["problems"],
            "firstSubmission": v["firstSubmission"],
            "url": ("https://codeforces.com/gym/%d" % cid) if is_gym
                   else ("https://codeforces.com/contest/%d" % cid),
            "inLinksTable": False,
        })
        print("  %-9d %-8s %-14s %-30s %s" % (cid, v["status"], cat, ",".join(cats), name[:52]))

    json.dump({"generatedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "contests": extra},
              open(os.path.join(BASE, "extra-contests.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    # 把现抓到的名字写回缓存，下次不必再打 CF
    if names_dirty:
        with open(os.path.join(BASE, "_gym_names.txt"), "w", encoding="utf-8") as f:
            for k in sorted(cache):
                f.write("%d\t%s\n" % (k, cache[k]))
        print("已写回 Gym 名字缓存 _gym_names.txt（%d 条）" % len(cache))
    vp = sum(1 for e in extra if e["status"] == "vp")
    print("")
    print("补入 %d 场：VP %d / 正式参赛 %d" % (len(extra), vp, len(extra) - vp))


if __name__ == "__main__":
    main()
