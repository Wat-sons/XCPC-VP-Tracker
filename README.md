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
| 单题勾选 | 点题号方块循环切换 **未做 → 已过 → 待复习**；右键直接清空 |
| 自动预勾选 | 首次打开时，仓库里**已有你题解**的题会自动勾成「已过」（例如绵阳站 D/G/J/K/L） |
| 双进度条 | 顶部同时显示「整场 VP 完成度」和「单题通过度」 |
| 筛选排序 | 按 CCPC/ICPC、区域赛/网络赛、年份、状态筛选；可按未过题数或完成度排序 |
| 开打入口 | 每张卡片直接给 QOJ / CF Gym / VJudge 链接，以及仓库题解和外链题解的入口 |
| 进度导出导入 | 导出 JSON 备份，换设备时导入恢复 |

**覆盖范围**：72 场比赛（区域赛 + 网络赛，2020–2025），905 道题。

## 进度存在哪

存在**你本机浏览器的 `localStorage`**，不上传任何数据、不需要登录。
好处是随便勾；代价是换浏览器/换设备不同步 —— 用「导出进度 / 导入进度」手动搬。

清空浏览器数据会丢进度，重要节点建议导出备份。

## 数据是怎么来的

`data.js` 由 `scripts/generate_data.py` 生成，读两个来源：

1. `docs/XCPC-Problem-Links.md` —— 各赛站的 QOJ / CF Gym / VJudge 链接和官方题数；
2. `solutions/<CCPC|ICPC>/Regionals/<年>/<赛站>/<题号>/` —— 你已收录的题解。

### 重新生成

先把 XCPC-Solutions 拉到本地，然后：

```powershell
# 拉最新仓库（浅克隆够用）
git clone --depth 1 git@github.com:Wat-sons/XCPC-Solutions.git D:\path\to\XCPC-Solutions

# 重新生成 data.js / vp-data.json
python scripts\generate_data.py --repo "D:\path\to\XCPC-Solutions" --out .
```

新增了赛站或题解之后跑一次，面板就更新了。

### 题目清单的口径

- **实线方块**：该题号在仓库里已有你的题解。
- **虚线方块**：按该赛站**官方题数**从 A 起补齐的占位题号（仓库里还没收录）。
  官方题数取自链接表，所以某站标 12 题时不会冒出 S 题这种不存在的题号。

## 目录

```
index.html              面板本体（单文件，无外部依赖）
data.js                 生成的数据（window.XCPC_DATA）
vp-data.json            同一份数据的纯 JSON，便于其它工具消费
scripts/generate_data.py 数据生成器
scripts/_domtest.js     用最小 DOM 模拟跑一遍页面逻辑的自测脚本
```

## 自测

```powershell
node scripts\_domtest.js
```

会真实执行 `index.html` 里的脚本，检查渲染卡片数、题目总数一致性、筛选、
勾选行为、localStorage 落盘、导入导出按钮是否可用。

## 已知限制

- 单题进度和 VP 标记都只在本机浏览器，仓库里不会留下记录。
- 虚线占位题号是按官方题数推算的，不代表该位置一定是那道题。
- `2025_ICPC_Asia-East_Online_II` 在链接表里没有对应行，是直接从仓库题解目录反推出来的卡片。
