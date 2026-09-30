/** 给源码打临时探针：逐卡片打印 cfForContest 的结果，定位为什么 5 场没种上。 */
const fs = require("fs");
const vm = require("vm");
const BASE = "D:\\Claude Code project\\projects\\XCPC-VP-Tracker";
let src = fs.readFileSync(BASE + "\\index.html", "utf8")
  .match(/<script>\s*\(function\(\)\{([\s\S]*?)\}\)\(\);\s*<\/script>/)[1];

// 探针 1：在 seed 之后 dump 出所有可匹配到 CF VP 的卡片及其判定
src = src.replace("  if(changed) save();\n}", `  if(changed) save();
  // ---- PROBE ----
  var _probe = [];
  CONTESTS.forEach(function(c){
    var cf = cfForContest(c);
    if(cf && cf.status === "vp"){
      _probe.push({id:c.id, cf:c.cfId||"via-links", name:(c.nameEn||c.nameCn||"").slice(0,24),
                   vpRaw:JSON.stringify(S.vp[c.id]), on:vpVal(c.id).on});
    }
  });
  window.__PROBE = _probe;
  // 反查：CF VP 的 contestId 里，哪些没有任何卡片能匹配到
  var _reach = {};
  CONTESTS.forEach(function(c){
    var cf = cfForContest(c);
    if(cf && cf.status === "vp") _reach[String(cf.contestId)] = c.id;
  });
  window.__MISS = Object.keys(CF.contests)
    .filter(function(k){ return CF.contests[k].status === "vp" && !_reach[k]; })
    .map(function(k){ return {cfId:k, info:CF.contests[k]}; });
  window.__REACH = _reach;
  // 专项：这几张卡片 cfForContest 到底返回了什么
  window.__DETAIL = ["c033","c038","c042","c068"].map(function(id){
    var c = CONTESTS.filter(function(x){ return x.id === id; })[0];
    if(!c) return {id:id, err:"卡片不存在"};
    var cf = cfForContest(c);
    return {
      id: id, name: c.nameEn || c.nameCn, cfId: c.cfId || null,
      links: (c.links||[]).map(function(l){ return l.kind + "=" + l.url; }),
      got: cf ? {contestId: cf.contestId, status: cf.status} : null
    };
  });
}`);
const appSrc = "(function(){" + src + "})();";

class El {
  constructor(id){ this.id=id||""; this.dataset={}; this.style={}; this.children=[]; this._text=""; this._html=""; this.value="";
    this.classList={_s:new Set(),add(){},remove(){},contains(){return false},toggle(){return false}}; this.listeners={}; }
  set textContent(v){this._text=String(v)} get textContent(){return this._text}
  set innerHTML(v){this._html=String(v)} get innerHTML(){return this._html}
  addEventListener(){} appendChild(c){this.children.push(c);return c} remove(){} click(){} focus(){}
  setAttribute(){} getAttribute(){return null} closest(){return null} contains(){return false}
  querySelector(){const s=new El("stub");s.querySelector=()=>new El("s2");return s} querySelectorAll(){return []}
}
const nodes={}; const getEl=id=>(nodes[id]=nodes[id]||new El(id)); const store={};
const sandbox={ window:{}, console,
  document:{getElementById:getEl,createElement:t=>new El(t),body:new El("body"),title:"",addEventListener(){}},
  localStorage:{getItem:k=>(k in store?store[k]:null),setItem:(k,v)=>{store[k]=String(v)},removeItem:k=>{delete store[k]}},
  Blob:function(){},URL:{createObjectURL:()=>"x",revokeObjectURL(){}},FileReader:function(){},
  setTimeout,clearTimeout,confirm:()=>true,alert(){},Date,JSON,Math,Object,Array,String,Number,Boolean,RegExp,Error,parseInt,parseFloat,isNaN };
sandbox.globalThis=sandbox; vm.createContext(sandbox);
["vp-data.json","cf-progress.json","extra-contests.json"].forEach(f=>{
  const key={"vp-data.json":"XCPC_DATA","cf-progress.json":"CF_PROGRESS","extra-contests.json":"EXTRA_CONTESTS"}[f];
  vm.runInContext("window."+key+" = "+fs.readFileSync(BASE+"\\"+f,"utf8")+";",sandbox);
});
vm.runInContext(appSrc, sandbox, {filename:"app.js"});

const probe = sandbox.window.__PROBE || [];
const miss = sandbox.window.__MISS || [];
const reach = sandbox.window.__REACH || {};
const out = [];
out.push("可匹配到 CF VP 的卡片数 = " + probe.length + "（期望 40）");
out.push("");
out.push("=== 匹配不到的 " + miss.length + " 个 CF VP 场次 ===");
miss.forEach(m => {
  out.push("  " + m.cfId + "  " + m.info.kind + "  已过=" + m.info.solvedCount + "/" + m.info.problemCount +
           "  首次=" + m.info.firstSubmission);
  // 页面上有哪些卡片带这个 contestId 的链接
  const cards = sandbox.window.XCPC_DATA.contests.filter(c =>
    (c.links || []).some(l => String(l.url || "").indexOf("/" + m.cfId) >= 0) || String(c.cfId) === m.cfId);
  out.push("     页面上带该 id 的卡片: " + (cards.length ? cards.map(c => c.id + "(" + (c.nameEn || c.nameCn) + ")").join(", ") : "无"));
});
out.push("");
out.push("=== 已匹配上的 " + Object.keys(reach).length + " 个 ===");
Object.keys(reach).slice(0, 45).forEach(k => out.push("  " + k + " -> " + reach[k]));
out.push("");
out.push("=== 专项：卡片 -> cfForContest 结果 ===");
(sandbox.window.__DETAIL || []).forEach(d => {
  out.push("  " + d.id + "  " + (d.name || "") + "  cfId=" + d.cfId);
  out.push("     links: " + (d.links || []).join(" | "));
  out.push("     got  : " + JSON.stringify(d.got));
});
fs.writeFileSync(BASE + "\\_probe.txt", out.join("\n"), "utf8");
console.log(out.slice(-16).join("\n"));
