#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 XCPC-Solutions 仓库生成 VP 打卡面板所需的数据。

数据来源（全部读取自仓库，不手工维护）：
  1. docs/XCPC-Problem-Links.md  -> 各赛站的 QOJ / CF Gym / VJudge 链接、官方题数
  2. solutions/<CCPC|ICPC>/Regionals/<年>/<赛站>/<题号>/  -> 已收录的题解

输出：
  data.js   （供 index.html 直接 <script> 引入，避免 file:// 下的 CORS 限制）
  vp-data.json（同一份数据的纯 JSON，便于其它工具消费）

用法：
  python generate_data.py --repo "D:\\path\\to\\XCPC-Solutions" --out "D:\\path\\to\\XCPC-VP-Tracker"
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta

# 中文城市名 -> 目录里的英文拼写（含常见变体）
CITY_ALIASES = {
    "威海": ["weihai"],
    "绵阳": ["mianyang"],
    "秦皇岛": ["qinhuangdao"],
    "长春": ["changchun"],
    "广州": ["guangzhou"],
    "桂林": ["guilin"],
    "哈尔滨": ["harbin"],
    "深圳": ["shenzhen"],
    "济南": ["jinan"],
    "郑州": ["zhengzhou"],
    "重庆": ["chongqing"],
    "澳门": ["macau", "macao"],
    "南京": ["nanjing"],
    "上海": ["shanghai"],
    "沈阳": ["shenyang"],
    "银川": ["yinchuan"],
    "昆明": ["kunming"],
    "杭州": ["hangzhou"],
    "香港": ["hongkong"],
    "西安": ["xian", "xian"],
    "合肥": ["hefei"],
    "成都": ["chengdu"],
    "武汉": ["wuhan"],
    "北京": ["beijing"],
    "南昌": ["nanchang"],
    "福州": ["fuzhou"],
    "青岛": ["qingdao"],
    "太原": ["taiyuan"],
}

LINK_HOSTS = (
    ("qoj.ac", "QOJ"),
    ("codeforces.com", "CF Gym"),
    ("vjudge.net", "VJudge"),
    ("acmore.cc", "acmore"),
    ("hdu", "HDU"),
)

TOTAL_RE = re.compile(r"^(\d{1,2})$")


def norm(s: str) -> str:
    """归一化：小写、只留字母数字、去掉常见后缀，便于模糊匹配。"""
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9]", "", s)
    for suf in ("regional", "site", "regionals", "contest"):
        if s.endswith(suf) and len(s) > len(suf):
            s = s[: -len(suf)]
    return s


def contains_cjk(s: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in s or "")


def split_site(raw: str):
    """把 '威海站 / Weihai Site'、'Jinan 济南'、'CCPC Online 2020 / 第六届…' 三种写法都拆成 (中文名, 英文名)。

    返回的 nameCn 既可能是地名（威海），也可能是整场比赛的名字（第八届 CCPC 网络预选赛），
    前端用「含不含中文」来区分要不要加"站"字。
    """
    raw = (raw or "").strip()
    if "/" in raw:
        a, b = raw.split("/", 1)
    else:
        a, b = raw, ""
    a, b = a.strip(), b.strip()

    if not b:
        # 没有斜杠：可能是 'Jinan 济南'（英文在前、中文在后）
        m = re.match(r"^([A-Za-z][A-Za-z'’\. \-]*?)\s+([\u4e00-\u9fff].*)$", a)
        if m:
            a, b = m.group(2), m.group(1)
        else:
            b = ""

    # 反转的写法：'Jinan 济南' 被拆进 a 里，或 'Jinan 济南 / ...' 中文在后
    if a and not contains_cjk(a) and contains_cjk(b):
        a, b = b, a

    cn = re.sub(r"站+$", "", a).strip()
    en = re.sub(r"\s*(Site|Regional|Regionals)\s*$", "", b, flags=re.I).strip()
    return cn, en


def site_aliases(cn: str, en: str):
    out = []
    if cn:
        out.append(norm(cn))
        for a in CITY_ALIASES.get(cn, []):
            out.append(norm(a))
    if en:
        out.append(norm(en))
    return [a for a in dict.fromkeys(out) if a]


def parse_links(cell: str):
    """从表格单元格里抽出所有链接，标注来源。"""
    links = []
    for m in re.finditer(r"\[([^\]]*)\]\((https?://[^)\s]+)\)", cell):
        label, url = m.group(1).strip(), m.group(2).strip()
        kind = "其它"
        low = url.lower()
        for host, name in LINK_HOSTS:
            if host in low:
                kind = name
                break
        links.append({"label": label or kind, "url": url, "kind": kind})
    return links


def parse_markdown_tables(md_path: str):
    """把 XCPC-Problem-Links.md 里的所有表格解析成条目列表。"""
    with open(md_path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    entries = []
    section = ""
    category = "regional"  # regional | online
    year = ""

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("## "):
            section = stripped[3:].strip()
            if "Online" in section or "网络" in section:
                category = "online"
            else:
                category = "regional"
            m = re.search(r"(20\d{2})", section)
            year = m.group(1) if m else ""
            continue

        if not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) < 4:
            continue
        if set(cells[0]) <= set("-: "):  # 分隔行
            continue
        if cells[0] in ("年份", "Year"):
            continue

        row_year = cells[0].strip()
        site_raw = cells[1].strip()
        total_raw = cells[2].strip()
        link_cell = "|".join(cells[3:])

        if not re.fullmatch(r"20\d{2}", row_year):
            continue

        # 「未见 QOJ 收录 EC Online」这类行是"这场没有收录"的备注，不是赛站，不进面板
        if "未见" in site_raw or "未见" in link_cell:
            continue
        # 题数栏是「—」说明连题目清单都没有，同样跳过
        if TOTAL_RE.match(total_raw) is None and total_raw.strip() in ("—", "-", "–"):
            continue

        cn, en = split_site(site_raw)
        total = int(total_raw) if TOTAL_RE.match(total_raw) else None

        # 分类推断：网络赛 / 区域赛
        row_category = category
        if any(k in site_raw or k in section for k in ("Online", "网络", "预选")):
            row_category = "online"

        # 归属赛事：section 里出现 CCPC 就是 CCPC，否则看 ICPC
        if "CCPC" in section:
            contest_series = "CCPC"
        elif "ICPC" in section:
            contest_series = "ICPC"
        else:
            contest_series = "ICPC" if "ICPC" in site_raw else "CCPC"

        entries.append(
            {
                "year": int(row_year),
                "category": row_category,
                "series": contest_series,
                "nameCn": cn,
                "nameEn": en,
                "siteRaw": site_raw,
                # 表格原文里带「站」字的才是地名（威海站 / Weihai Site），
                # 不带的是整场比赛的名字（第八届 CCPC 网络预选赛），前端据此决定要不要补"站"
                "isSite": ("站" in site_raw) or bool(re.search(r"\bSite\b", site_raw, re.I)),
                "section": section,
                "totalProblems": total,
                "links": parse_links(link_cell),
                "note": re.sub(r"\[[^\]]*\]\([^)]*\)", "", link_cell).strip(" ·；;，,"),
            }
        )

    return entries


def scan_solution_dirs(repo_root: str):
    """扫描 solutions/，返回 {相对目录: {year, series, letter: {cpp, md}}}。"""
    sol_root = os.path.join(repo_root, "solutions")
    found = {}
    if not os.path.isdir(sol_root):
        return found

    for series in ("CCPC", "ICPC"):
        base = os.path.join(sol_root, series, "Regionals")
        if not os.path.isdir(base):
            continue
        for year_name in sorted(os.listdir(base)):
            year_dir = os.path.join(base, year_name)
            if not os.path.isdir(year_dir):
                continue
            for contest_name in sorted(os.listdir(year_dir)):
                cdir = os.path.join(year_dir, contest_name)
                if not os.path.isdir(cdir):
                    continue
                rel = os.path.relpath(cdir, repo_root).replace("\\", "/")
                problems = {}
                for letter in sorted(os.listdir(cdir)):
                    ldir = os.path.join(cdir, letter)
                    if not (os.path.isdir(ldir) and re.fullmatch(r"[A-Z]", letter)):
                        continue
                    info = {"cpp": [], "md": []}
                    for fn in sorted(os.listdir(ldir)):
                        if fn.lower().endswith(".cpp"):
                            info["cpp"].append(fn)
                        elif fn.lower().endswith(".md"):
                            info["md"].append(fn)
                    problems[letter] = info
                has_editorial = os.path.isfile(os.path.join(cdir, "editorial.md"))
                found[rel] = {
                    "year": int(year_name) if re.fullmatch(r"20\d{2}", year_name) else None,
                    "series": series,
                    "dirName": contest_name,
                    "problems": problems,
                    "hasEditorial": has_editorial,
                }
    return found


def match_dirs(entries, dirs):
    """把表格条目匹配到实际存在的题解目录。"""
    # 建立 别名 -> [目录] 索引
    index = {}
    for rel, meta in dirs.items():
        keys = {norm(meta["dirName"])}
        for city, aliases in CITY_ALIASES.items():
            if any(norm(a) in norm(meta["dirName"]) for a in aliases):
                keys.add(norm(city))
                for a in aliases:
                    keys.add(norm(a))
        for k in keys:
            if k:
                index.setdefault(k, []).append(rel)

    for e in entries:
        cands = []
        for alias in site_aliases(e["nameCn"], e["nameEn"]):
            for rel in index.get(alias, []):
                if rel not in cands:
                    cands.append(rel)
        # 限定年份 + 系列
        narrowed = [
            r
            for r in cands
            if dirs[r]["year"] == e["year"] and dirs[r]["series"] == e["series"]
        ]
        if not narrowed:
            narrowed = [r for r in cands if dirs[r]["year"] == e["year"]]
        e["solutionDir"] = narrowed[0] if len(narrowed) == 1 else (narrowed[0] if narrowed else None)
        e["_matchCandidates"] = narrowed
    return entries


def build_problems(entry, dirs):
    """生成题目列表：已收录的字母 + 从 A 起补齐官方题数的占位字母。"""
    problems = []
    sol = dirs.get(entry["solutionDir"]) if entry.get("solutionDir") else None

    if sol:
        for letter in sorted(sol["problems"].keys()):
            info = sol["problems"][letter]
            header = info["md"][0] if info["md"] else None
            problems.append(
                {
                    "id": letter,
                    "solved": True,
                    "cpp": info["cpp"],
                    "md": info["md"],
                    "note": header,
                    "unknown": False,
                }
            )

    total = entry.get("totalProblems")
    if total and len(problems) < total:
        # 已收录的题不足以覆盖官方题数：从 A 开始填补空缺字母，
        # 而不是接在最后一个字母后面，否则会冒出 S 题这种不存在的题号。
        have = {p["id"] for p in problems}
        for code in range(ord("A"), ord("Z") + 1):
            if len(problems) >= total:
                break
            letter = chr(code)
            if letter in have:
                continue
            problems.append(
                {
                    "id": letter,
                    "solved": False,
                    "cpp": [],
                    "md": [],
                    "note": None,
                    "unknown": True,
                }
            )
        problems.sort(key=lambda p: p["id"])
    return problems


def synth_entries_for_stray(dirs, used_dirs, used_keys):
    """仓库里存在、但链接表里没有对应行的赛站（例如网络赛 II），也要出现在面板上。

    used_keys 是链接表里已出现的 (年份, 系列, 归一化站名) 集合，
    用于识别"这场其实就是上面某一场"的情况，避免你重复打卡。
    """
    dup_map = {}
    for rel, meta in dirs.items():
        base = meta["dirName"]
        keys = {norm(base)}
        for city, aliases in CITY_ALIASES.items():
            if any(norm(a) in norm(base) for a in aliases):
                keys.add(norm(city))
        hit = None
        for k in keys:
            if k and (meta["year"], meta["series"], k) in used_keys:
                hit = k
                break
        if hit:
            dup_map[rel] = hit

    out = []
    for rel, meta in sorted(dirs.items()):
        if rel in used_dirs:
            continue
        base = meta["dirName"]
        # 2025_ICPC_Asia-East_Online_II -> ICPC / Asia-East Online II
        parts = base.split("_")
        main = [p for p in parts if not re.fullmatch(r"20\d{2}", p) and p.upper() != "ICPC" and p.upper() != "CCPC"]
        main = [p for p in main if p.lower() not in ("regional", "regionals", "site", "example")]
        en = " ".join(main) or base
        if "example" in base.lower():
            continue  # 模板示例，不放进面板
        out.append(
            {
                "year": meta["year"],
                "category": "online" if "online" in base.lower() else "regional",
                "series": meta["series"],
                "nameCn": None,
                "nameEn": en,
                "siteRaw": base,
                "section": "仓库中已有题解（链接表未收录）",
                "isSite": False,
                # 链接表里已经有同一场比赛时，指向那一条，面板上提示避免重复打卡
                "dupOf": dup_map.get(rel),
                "totalProblems": None,
                "links": [],
                "note": "",
                "solutionDir": rel,
            }
        )
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="XCPC-Solutions 本地仓库路径")
    ap.add_argument("--out", required=True, help="输出目录（VP 面板项目）")
    ap.add_argument(
        "--raw-base",
        default="https://github.com/Wat-sons/XCPC-Solutions/blob/main",
        help="源码链接前缀",
    )
    args = ap.parse_args()

    md_path = os.path.join(args.repo, "docs", "XCPC-Problem-Links.md")
    if not os.path.isfile(md_path):
        print("找不到 " + md_path, file=sys.stderr)
        return 1

    entries = parse_markdown_tables(md_path)
    dirs = scan_solution_dirs(args.repo)
    match_dirs(entries, dirs)

    # 表格里已用掉的目录
    used = {e["solutionDir"] for e in entries if e.get("solutionDir")}
    # 表格里出现过的 (年份, 系列, 归一化地名)，用于识别重复场次
    used_keys = set()
    for e in entries:
        for k in site_aliases(e.get("nameCn"), e.get("nameEn")):
            used_keys.add((e["year"], e["series"], k))
    entries += synth_entries_for_stray(dirs, used, used_keys)

    contests = []
    for i, e in enumerate(entries):
        sol = dirs.get(e["solutionDir"]) if e.get("solutionDir") else None
        problems = build_problems(e, dirs)
        solved = sum(1 for p in problems if p["solved"])
        note = (e.get("note") or "").strip()
        # 链接被抽走后剩下的只是分隔符和空壳（"例如 。"），一并清理
        note = re.sub(r"例如\s*[。.；;]?", "", note)
        note = re.sub(r"\s+", " ", note).strip(" /；;，,、。.")
        # 表格里链接之外剩下的往往只是分隔符，清掉免得显示成垃圾
        if not re.search(r"[\w\u4e00-\u9fff]", note):
            note = ""
        if e.get("dupOf"):
            # 链接表里已经有同一场比赛，提示一下，别两边重复打卡
            note = ("⚠️ 这一场在链接表里已经有一张卡片了（同一场比赛的另一种叫法），"
                    "打卡请认准其中一张，别两边都勾。" + ("　" + note if note else ""))
        contests.append(
            {
                "id": "c%03d" % i,
                "year": e["year"],
                "category": e["category"],
                "series": e["series"],
                "nameCn": e["nameCn"],
                "nameEn": e["nameEn"],
                "siteRaw": e["siteRaw"],
                "isSite": e.get("isSite", False),
                "dupOf": e.get("dupOf"),
                "section": e["section"],
                "totalProblems": e["totalProblems"],
                "problemCount": len(problems),
                "solvedCount": solved,
                "links": e["links"],
                "note": note,
                "solutionDir": e["solutionDir"],
                "repoUrl": (args.raw_base + "/" + e["solutionDir"]) if e["solutionDir"] else None,
                "hasEditorial": bool(sol and sol["hasEditorial"]),
                "problems": problems,
            }
        )

    # 排序：年份升序、系列（CCPC 在前）、赛站名
    contests.sort(key=lambda c: (c["year"], 0 if c["series"] == "CCPC" else 1, c["nameEn"] or c["nameCn"]))

    unmatched = [c["siteRaw"] for c in contests if not c["solutionDir"]]
    used_now = {c["solutionDir"] for c in contests if c["solutionDir"]}
    stray = [rel for rel in dirs if rel not in used_now]

    tz = timezone(timedelta(hours=8))
    data = {
        "meta": {
            "generatedAt": datetime.now(tz).isoformat(timespec="seconds"),
            "source": "https://github.com/Wat-sons/XCPC-Solutions",
            "rawBase": args.raw_base,
            "contestCount": len(contests),
            "regionalCount": sum(1 for c in contests if c["category"] == "regional"),
            "onlineCount": sum(1 for c in contests if c["category"] == "online"),
            "totalProblems": sum(c["problemCount"] for c in contests),
            "totalSolved": sum(c["solvedCount"] for c in contests),
            "withSolutions": sum(1 for c in contests if c["solutionDir"]),
            "unmatchedSites": unmatched,
            "straySolutionDirs": stray,
        },
        "contests": contests,
    }

    os.makedirs(args.out, exist_ok=True)
    js = "window.XCPC_DATA = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n"
    with open(os.path.join(args.out, "data.js"), "w", encoding="utf-8") as f:
        f.write(js)
    with open(os.path.join(args.out, "vp-data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    print("赛站条目   : %d（区域赛 %d / 网络赛 %d）" % (len(contests), data["meta"]["regionalCount"], data["meta"]["onlineCount"]))
    print("已有题解   : %d 个赛站" % data["meta"]["withSolutions"])
    print("题目总数   : %d（已收录 %d）" % (data["meta"]["totalProblems"], data["meta"]["totalSolved"]))
    print("未匹配赛站 : %d %s" % (len(unmatched), unmatched if unmatched else ""))
    print("孤立目录   : %d %s" % (len(stray), stray if stray else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
