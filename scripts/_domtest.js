/**
 * 用最小 DOM 模拟真实执行 index.html 里的脚本，
 * 验证渲染结果、筛选、勾选、导入导出是否真的能跑，而不是"看着对"。
 */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const ROOT = "D:\\Claude Code project\\projects\\XCPC-VP-Tracker";
const html = fs.readFileSync(path.join(ROOT, "index.html"), "utf8");
const dataJs = fs.readFileSync(path.join(ROOT, "data.js"), "utf8");

/* ---------- 抓出内联脚本 ---------- */
const m = html.match(/<script>\s*\(function\(\)\{([\s\S]*?)\}\)\(\);\s*<\/script>/);
if (!m) throw new Error("没抓到内联脚本");
const appSrc = "(function(){" + m[1] + "})();";

/* ---------- 最小 DOM ---------- */
const report = [];
function log(s) { report.push(s); }

class El {
  constructor(id, tag) {
    this.id = id || ""; this.tagName = (tag || "div").toUpperCase();
    this.dataset = {}; this.style = {}; this.children = []; this.attrs = {};
    this._text = ""; this._html = ""; this.value = "";
    this.classList = {
      _s: new Set(),
      add: (...c) => c.forEach(x => this.classList._s.add(x)),
      remove: (...c) => c.forEach(x => this.classList._s.delete(x)),
      contains: (c) => this.classList._s.has(c),
      toggle: (c, on) => { const has = this.classList._s.has(c); const want = on === undefined ? !has : !!on;
        if (want) this.classList._s.add(c); else this.classList._s.delete(c); return want; }
    };
    this.listeners = {};
  }
  set textContent(v) { this._text = String(v); }
  get textContent() { return this._text; }
  set innerHTML(v) { this._html = String(v); }
  get innerHTML() { return this._html; }
  addEventListener(t, fn) { (this.listeners[t] = this.listeners[t] || []).push(fn); }
  removeEventListener() {}
  appendChild(c) { this.children.push(c); return c; }
  removeChild(c) { this.children = this.children.filter(x => x !== c); }
  remove() {}
  click() { (this.listeners.click || []).forEach(fn => fn({ target: this, preventDefault(){} })); }
  focus() {}
  setAttribute(k, v) { this.attrs[k] = v; }
  getAttribute(k) { return this.attrs[k]; }
  closest() { return null; }
  contains() { return false; }
  querySelector(sel) {
    // 展开区里的元素：返回一个能撑住链式调用的桩
    const stub = new El("stub-" + sel);
    stub.querySelector = () => new El("stub-inner");
    return stub;
  }
  querySelectorAll() { return []; }
}

const nodes = {};
function getEl(id) {
  if (!nodes[id]) nodes[id] = new El(id);
  return nodes[id];
}

const store = {};
const localStorage = {
  getItem: (k) => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); },
  removeItem: (k) => { delete store[k]; }
};

let createdTag = null;
const document = {
  getElementById: getEl,
  createElement: (tag) => { createdTag = tag; const e = new El("", tag); return e; },
  body: new El("body"),
  title: "",
  addEventListener() {}
};

const sandbox = {
  window: {}, document, localStorage, console,
  Blob: function (parts) { this.parts = parts; },
  URL: { createObjectURL: () => "blob:x", revokeObjectURL() {} },
  FileReader: function () {},
  setTimeout, clearTimeout,
  confirm: () => true, alert: (s) => log("ALERT " + s),
  Date, JSON, Math, Object, Array, String, Number, Boolean, RegExp, Error, parseInt, parseFloat, isNaN
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;

/* data.js 先注入 */
vm.createContext(sandbox);
vm.runInContext(dataJs, sandbox, { filename: "data.js" });
log("data.js 载入: contests=" + sandbox.XCPC_DATA.contests.length);

/* 跑应用脚本 */
let crashed = null;
try {
  vm.runInContext(appSrc, sandbox, { filename: "app.js" });
} catch (e) {
  crashed = e;
}
if (crashed) {
  log("!! 脚本执行抛错: " + crashed.message + "\n" + (crashed.stack || "").split("\n").slice(0, 4).join("\n"));
} else {
  log("脚本执行: 无异常");
}

/* ---------- 断言 ---------- */
const list = nodes["list"];
function header() {
  return ["s-contest", "s-vp", "s-doing", "s-prob", "s-solved", "s-pct", "s-pct2"]
    .map(k => k.replace("s-", "") + "=" + (nodes[k] ? nodes[k].textContent : "?")).join("  ");
}
log("顶部统计: " + header());

function setFilter(id, v) { const e = nodes[id]; e.value = v; (e.listeners.input || []).forEach(f => f({ target: e })); }
function cardCount() { return (list.innerHTML.match(/class="card/g) || []).length; }
function chipCount() {
  return (list.innerHTML.match(/class="p state-/g) || []).length +
         (list.innerHTML.match(/class="p unknown"/g) || []).length;
}

log("初始渲染卡片数 = " + cardCount());
log("初始渲染方块数 = " + chipCount());
log("卡片里出现 '已 VP' 按钮 = " + (list.innerHTML.match(/data-act="vp"/g) || []).length);
log("卡片里出现源码链接 = " + (list.innerHTML.match(/blob\/main\/solutions/g) || []).length);

/* 数据本身的一致性：顶部统计应等于逐场累加 */
const D = sandbox.XCPC_DATA;
let expProb = 0, expSolved = 0;
D.contests.forEach(c => { expProb += c.problems.length; expSolved += c.problems.filter(p => p.solved).length; });
log("逐场累加: 题数=" + expProb + " 已收录=" + expSolved +
    "  → 与顶部统计一致: " + (String(expProb) === nodes["s-prob"].textContent && String(expSolved) === nodes["s-solved"].textContent));

/* 筛选 */
setFilter("q", "南京");   const byCn = cardCount();
setFilter("q", "Nanjing"); const byEn = cardCount();
setFilter("q", "2020");    const byYear = cardCount();
log("搜索 南京=" + byCn + "  Nanjing=" + byEn + "  (中文/英文都应 > 0)");
setFilter("q", "guilin");  log("搜索 guilin=" + cardCount());

setFilter("q", "");
setFilter("f-series", "CCPC"); log("筛选 CCPC = " + cardCount());
setFilter("f-series", "ICPC"); log("筛选 ICPC = " + cardCount());
setFilter("f-series", "");
setFilter("f-cat", "online"); log("筛选 网络赛 = " + cardCount());
setFilter("f-cat", ""); 
setFilter("f-year", "2020"); log("筛选 2020 年 = " + cardCount());
setFilter("f-year", "");
setFilter("f-status", "has"); log("筛选 有题解 = " + cardCount());
setFilter("f-status", "");
setFilter("f-sort", "unsolved"); log("按未过题数排序: 首张卡片 = " + ((list.innerHTML.match(/class="title">([^<]*)/) || [])[1] || "?"));
setFilter("f-sort", "year");

/* 交互：勾整场 VP */
const beforeVp = nodes["s-vp"].textContent;
const vpBtns = list.innerHTML.match(/data-id="(c\d+)"/g) || [];
const firstId = (list.innerHTML.match(/class="card[^"]*" data-id="(c\d+)"/) || [])[1];
getEl("list").listeners.click.forEach(fn => {});
// 直接驱动：模拟点击第一张卡片的 VP 按钮
(function () {
  const card = new El(); card.dataset.id = firstId;
  const btn = new El(); btn.dataset.act = "vp"; btn.closest = () => card;
  const ev = { target: btn, preventDefault() {} };
  const fake = { closest: (sel) => (sel.indexOf("vp") >= 0 ? btn : null) };
  // 走真实监听器
  (list.listeners.click || []).forEach(fn => fn({ target: { closest: (sel) => {
      if (sel === ".p") return null;
      if (sel.indexOf("vp") >= 0) return { closest: () => card };
      return null;
    }, preventDefault(){} } }));
})();
log("点击 VP: " + beforeVp + " → " + nodes["s-vp"].textContent + "（应 +1）");

/* 单题勾选 */
const pid = D.contests.find(c => c.problems.length).id;
const beforeSolved = nodes["s-solved"].textContent;
(function () {
  const chip = new El(); chip.dataset.c = pid; chip.dataset.p = D.contests[0].problems[0].id;
  chip.classList.add("p");
  chip.querySelector = () => new El("mk");
  chip.closest = () => new El("card");
  (list.listeners.click || []).forEach(fn => fn({ target: { closest: (sel) => (sel === ".p" ? chip : null) }, preventDefault(){} }));
})();
log("点击题目方块后 已过题 = " + beforeSolved + " → " + nodes["s-solved"].textContent);

/* localStorage 是否落盘 */
const saved = store["xcpc-vp-tracker-v1"];
log("localStorage 写入 = " + (saved ? "是 (" + saved.length + " 字节)" : "否"));
if (saved) {
  const o = JSON.parse(saved);
  log("  种子题数 seeded = " + (o.seeded || []).length + "，prob 条目 = " + Object.keys(o.prob || {}).length + "，vp 条目 = " + Object.keys(o.vp || {}).length);
}

/* 导出 */
try {
  getEl("b-export").click();
  log("导出按钮: 正常（" + createdTag + "）");
} catch (e) { log("导出按钮抛错: " + e.message); }
try {
  getEl("b-expand").click();
  log("展开全部: 卡片 open 数 = " + (list.innerHTML.match(/card open/g) || []).length);
} catch (e) { log("展开全部抛错: " + e.message); }
try {
  getEl("b-collapse").click();
  log("收起全部: 卡片 open 数 = " + (list.innerHTML.match(/card open/g) || []).length);
} catch (e) { log("收起全部抛错: " + e.message); }

/* 中文是否正常（不该出现乱码替换字符） */
log("渲染结果含 U+FFFD 替换字符 = " + (list.innerHTML.indexOf("\uFFFD") >= 0));
log("样例标题: " + (list.innerHTML.match(/class="title">([^<]*)/) || [])[1]);

fs.writeFileSync(path.join(ROOT, "_domtest.txt"), report.join("\n"), "utf8");
console.log("OK lines=" + report.length);
