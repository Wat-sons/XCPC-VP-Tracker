/**
 * 直接检查页面 seed 后写入 localStorage 的状态：到底标记了多少场 VP、来自哪里。
 */
const fs = require("fs");
const vm = require("vm");
const BASE = "D:\\Claude Code project\\projects\\XCPC-VP-Tracker";
const html = fs.readFileSync(BASE + "\\index.html", "utf8");
const appSrc = "(function(){" + html.match(/<script>\s*\(function\(\)\{([\s\S]*?)\}\)\(\);\s*<\/script>/)[1] + "})();";

class El {
  constructor(id) {
    this.id = id || ""; this.dataset = {}; this.style = {}; this.children = [];
    this._text = ""; this._html = ""; this.value = "";
    this.classList = { _s: new Set(), add(){}, remove(){}, contains(){ return false; }, toggle(){ return false; } };
    this.listeners = {};
  }
  set textContent(v){ this._text = String(v); } get textContent(){ return this._text; }
  set innerHTML(v){ this._html = String(v); if (this.id === "list") El._listHtml = String(v); }
  get innerHTML(){ return this._html; }
  addEventListener(t, fn){ (this.listeners[t] = this.listeners[t] || []).push(fn); }
  appendChild(c){ this.children.push(c); return c; }
  remove(){} click(){} focus(){} setAttribute(){} getAttribute(){ return null; }
  closest(){ return null; } contains(){ return false; }
  querySelector(){ const s = new El("stub"); s.querySelector = () => new El("s2"); return s; }
  querySelectorAll(){ return []; }
}
const nodes = {};
const getEl = id => (nodes[id] = nodes[id] || new El(id));
const store = {};
const sandbox = {
  window: {}, console,
  document: { getElementById: getEl, createElement: t => new El(t), body: new El("body"), title: "", addEventListener(){} },
  localStorage: { getItem: k => (k in store ? store[k] : null),
                  setItem: (k, v) => { store[k] = String(v); }, removeItem: k => { delete store[k]; } },
  Blob: function(){}, URL: { createObjectURL: () => "x", revokeObjectURL(){} },
  FileReader: function(){}, setTimeout, clearTimeout, confirm: () => true, alert(){},
  Date, JSON, Math, Object, Array, String, Number, Boolean, RegExp, Error, parseInt, parseFloat, isNaN
};
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
["vp-data.json", "cf-progress.json", "extra-contests.json"].forEach(f => {
  const key = { "vp-data.json": "XCPC_DATA", "cf-progress.json": "CF_PROGRESS", "extra-contests.json": "EXTRA_CONTESTS" }[f];
  vm.runInContext("window." + key + " = " + fs.readFileSync(BASE + "\\" + f, "utf8") + ";", sandbox);
});
vm.runInContext(appSrc, sandbox, { filename: "app.js" });

const saved = JSON.parse(store["xcpc-vp-tracker-v2"] || "{}");
const vp = saved.vp || {};
const prob = saved.prob || {};
const onIds = Object.keys(vp).filter(k => vp[k] && vp[k].on);
const onCf = onIds.filter(k => vp[k].src === "cf");
const onMe = onIds.filter(k => vp[k].src === "me");

const CF = sandbox.window.CF_PROGRESS.contests;
const cfVp = Object.keys(CF).filter(k => CF[k].status === "vp");

const out = [];
out.push("localStorage 里 S.vp 条目 = " + Object.keys(vp).length);
out.push("  标记为 on 的 = " + onIds.length + "（其中 src=cf 的 " + onCf.length + "，src=me 的 " + onMe.length + "）");
out.push("CF 判定 VP 的场次 = " + cfVp.length);
out.push("S.prob 条目 = " + Object.keys(prob).length +
         " / 其中 src=cf 的 = " + Object.values(prob).filter(v => v && v.src === "cf").length);
out.push("");
out.push("顶上统计文本: 赛站=" + nodes["s-contest"].textContent +
         " 已VP=" + nodes["s-vp"].textContent +
         " 进行中=" + nodes["s-doing"].textContent +
         " 题=" + nodes["s-prob"].textContent +
         " 已过=" + nodes["s-solved"].textContent +
         " (" + nodes["s-pct2"].textContent + ")");
fs.writeFileSync(BASE + "\\_vpstate.txt", out.join("\n"), "utf8");
console.log(out.join("\n"));
