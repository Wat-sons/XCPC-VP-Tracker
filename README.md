# XCPC VP 打卡台

给你（quchen / Wat-sons）打 XCPC 虚拟赛（VP）用的可视化面板。数据全部来自
[XCPC-Solutions](https://github.com/Wat-sons/XCPC-Solutions) 仓库，不手工维护。

**在线版：<https://wat-sons.github.io/XCPC-VP-Tracker/>**

## 它解决什么问题

`XCPC-Solutions` 里的题解是散在 `solutions/CCPC/Regionals/2020/.../D/quchen_D.cpp`
这种目录里的，看的时候不知道：

- 一共收了哪些赛站、每站多少题、我自己过了哪些；
- 哪几场我打过 VP、哪几场还没碰；
- 下一场该打什么；
- 每场比赛去哪打（QOJ / CF Gym / VJudge）。

这个面板把这些摊平成卡片：**每张卡片 = 一场比赛**，当场看进度、点链接开打、勾选标记。

## 功能

| 功能 | 说明 |
|---|---|
| 整场 VP 勾选 | 卡片右侧「已 VP」按钮，标记这场打过了 |
| **CF 自动同步** | 从 Codeforces 抓你的提交，**有 `VIRTUAL` 标记的比赛自动打勾**，AC 过的题自动标「已过」 |
| 单题勾选 | 点题号方块循环切换 **未做 → 已过 → 待复习**；右键直接清空 |
| 自动预勾选 | 仓库里**已有你题解**的题也会自动勾成「已过」 |
| 双进度条 | 顶部同时显示「整场 VP 完成度」和「单题通过度」 |
| 筛选排序 | 按 CCPC/ICPC、区域赛/网络赛/省赛、年份、状态筛选；可按未过题数或完成度排序 |
| 开打入口 | 每张卡片直接给 QOJ / CF Gym / VJudge 链接，以及仓库题解和外链题解的入口 |
| 进度导出导入 | 导出 JSON 备份，换设备时导入恢复 |

**覆盖范围**：160 场（链接表的 72 场 + CF 上打过但链接表没收的 88 场），1344 道题。

## CF 同步是怎么判定"VP 过"的

这是整个项目里最需要说清楚的一件事。CF 的 `user.status` 接口每条提交都带
`author.participantType`，实测取值和含义：

| 值 | 含义 | 算不算 VP |
|---|---|---|
| `VIRTUAL` | 注册了虚拟参赛 | ✅ **算，这是硬证据** |
| `CONTESTANT` | 比赛进行中正式参赛 | ❌ 是打正式赛，不是 VP |
| `PRACTICE` | 比赛结束后的补题 | ❌ **不算**（`relativeTimeSeconds` 会是哨兵值 2147483647） |
| `OUT_OF_COMPETITION` | 打星参赛 | ❌ 不算 |

在 quchen 的两个账号（2266 + 483 条提交）上逐条核对过，结论：

- **40 场有 `VIRTUAL` 标记** → 面板自动打勾
- **68 场是正式参赛** → 面板不勾（那是打比赛，不是 VP）
- **393 场只有 PRACTICE** → 面板不勾，但会在卡片里注明"CF 只有赛后补题记录（不算 VP）"

> 注意：CF 的**排行榜接口不返回 VP 选手**（只返回正式选手），所以不能靠排行榜判断；
> 必须用 `user.status` 里的 `participantType`。

## QOJ 同步

QOJ 是 UOJ 框架，`/api/*` 和公开提交页**都要求登录态**，所以必须用账号密码：

```powershell
$env:QOJ_USER = "quchen"
$env:QOJ_PASS = "你的密码"      # 只用于本次登录，不写入任何文件
python scripts\sync_qoj.py
```

成功会生成 `qoj-progress.json`。**注意**：QOJ 的页面结构属于内部实现，
如果它改版，解析会失效 —— 脚本在解析到 0 条时会明确报警，不会静默成功。

## 进度存在哪

存在**你本机浏览器的 `localStorage`**，不上传任何数据、不需要登录。
好处是随便勾；代价是换浏览器/换设备不同步 —— 用「导出进度 / 导入进度」手动搬。

**优先级**：你手动勾的永远优先。CF 同步来的标记带 `·CF` 角标，
你点一下就会变回手动状态，之后重新同步也不会覆盖你的选择。

清空浏览器数据会丢进度，重要节点建议导出备份。

## 数据是怎么来的

三层数据，各自独立可重跑：

| 文件 | 生成脚本 | 数据来源 |
|---|---|---|
| `data.js` | `scripts/generate_data.py` | XCPC-Solutions 的 `docs/XCPC-Problem-Links.md` + `solutions/` |
| `cf-progress.js` | `scripts/sync_codeforces.py` | Codeforces 公开 API |
| `extra-contests.js` | `scripts/build_extra_contests.py` | CF 上打过但链接表没收的比赛 |

### 完整重建流程

```powershell
# 1. 拉 XCPC-Solutions
git clone --depth 1 git@github.com:Wat-sons/XCPC-Solutions.git D:\path\to\XCPC-Solutions

# 2. 赛站数据
python scripts\generate_data.py --repo "D:\path\to\XCPC-Solutions" --out .

# 3. CF 进度（公开 API，无需登录）
python scripts\sync_codeforces.py

# 4. 补充链接表没收录的比赛
python scripts\build_extra_contests.py

# 5. 打包成页面能直接引入的 .js
python scripts\build_page_data.py
```

### 题目清单的口径

- **实线方块**：该题号在仓库里已有你的题解，或 CF 上已 AC。
- **蓝色边框 + CF 角标**：这条「已过」是 CF 同步来的（仓库里没有题解）。
- **虚线方块**：按该赛站**官方题数**从 A 起补齐的占位题号。

## 目录

```
index.html                  面板本体（单文件，无外部依赖）
data.js                     赛站与题解数据
cf-progress.js              CF 抓取结果
extra-contests.js           CF 补充比赛
vp-data.json / cf-progress.json / extra-contests.json   对应的纯 JSON
scripts/generate_data.py    赛站数据生成
scripts/sync_codeforces.py  CF 同步
scripts/build_extra_contests.py  补充比赛
scripts/build_page_data.py  打包成 .js
scripts/sync_qoj.py         QOJ 同步（需要账号密码）
scripts/_domtest.js         页面逻辑自测
scripts/_probe.js           CF 映射关系排查
scripts/_vpstate.js         检查 seed 后的实际状态
```

## 自测

```powershell
node scripts\_domtest.js     # 页面逻辑：渲染、筛选、勾选、存储
node scripts\_vpstate.js     # CF 同步后实际标了多少场 VP、多少题
node scripts\_probe.js       # CF 比赛与页面卡片的映射是否完整
```

## 已知限制

- 单题进度和 VP 标记都存在本机浏览器，仓库里不会留下记录。
- 普通 CF Round 若你**赛后补题但没注册 VP**，面板不会打勾（这是刻意的，避免误标）。
- QOJ 同步需要密码；QOJ 改版会导致解析失效。
- 补充进来的 68 场"正式参赛"不是 VP，只是为了让你看到自己在 CF 上打过哪些比赛。

