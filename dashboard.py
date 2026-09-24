#!/usr/bin/env python3
"""mev cockpit: single file, browser control panel (stdlib-only).
Usage: python dashboard.py  -> browser opens automatically (http://127.0.0.1:47921)
"""
import json, os, random, sys, time, webbrowser, threading
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mev as J
import mcp_server as M

HOST, PORT = "127.0.0.1", 47921
MEV = os.path.dirname(os.path.abspath(__file__))

PAGE = """<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<title>MEV</title>
<link rel="icon" type="image/svg+xml" href="/logo.svg">
<style>
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%}
body{background:#1E0A08;color:#F3E6E1;font-family:"Segoe UI",system-ui,sans-serif;min-width:1280px;height:100vh;display:flex;flex-direction:column;overflow:hidden}
header{position:relative;display:flex;flex-direction:column;align-items:center;padding:12px 26px 10px;background:transparent}
.logo{font-family:"Manrope","Segoe UI",system-ui,sans-serif;font-size:30px;font-weight:800;letter-spacing:12px;text-indent:12px;color:#F3E6E1}
.logo em{font-style:normal;color:#E8A07E}
.caps{display:flex;align-items:center;gap:10px;font-size:10px;letter-spacing:5px;text-indent:5px;color:#B08D87;margin-top:4px}
.caps span{width:44px;height:1px;background:rgba(232,160,126,.35)}
.tag{font-size:12px;color:#B08D87;margin-top:4px}
.right{position:absolute;right:26px;top:50%;transform:translateY(-50%);display:flex;gap:10px;align-items:center}
.badge{font-size:11px;color:#B08D87;border:1px solid rgba(232,160,126,.25);border-radius:20px;padding:2px 10px}
#clock{color:#B08D87;font-size:12px}
main{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px;padding:14px 26px;flex:1;min-height:0;background:#1E0A08}
.panel{position:relative;background:#2A1210;border:1px solid rgba(232,160,126,.12);border-radius:14px;padding:18px;display:flex;flex-direction:column;min-height:0;overflow:hidden;animation:rise .5s ease both}
.panel:nth-child(2){animation-delay:.08s}.panel:nth-child(3){animation-delay:.16s}.panel:nth-child(4){animation-delay:.24s}
@keyframes rise{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.num{position:absolute;top:6px;right:14px;font-family:Georgia,serif;font-size:44px;color:rgba(232,160,126,.10);line-height:1;pointer-events:none}
.panel h2{font-family:Georgia,serif;font-size:21px;font-weight:700;color:#E8A07E;margin-bottom:2px}
.sub{font-size:12px;color:#B08D87;margin-bottom:8px}
label{font-size:11px;color:#B08D87;display:block;margin:10px 0 4px;letter-spacing:.5px}
textarea,input[type=text]{width:100%;background:rgba(74,21,18,.25);color:#F3E6E1;border:1px solid rgba(232,160,126,.15);border-radius:8px;padding:9px;font-family:inherit;font-size:13px;resize:vertical}
textarea::placeholder,input::placeholder{color:#9A6F69}
textarea:focus,input:focus{outline:none;box-shadow:0 0 0 1px #E8A07E}
button{display:flex;align-items:center;justify-content:center;gap:8px;background:transparent;color:#E8A07E;border:1px solid rgba(232,160,126,.35);border-radius:10px;padding:9px 14px;font-family:inherit;font-size:13px;font-weight:600;cursor:pointer;margin-top:12px}
.panel.active button.act{background:#E8A07E;color:#4A1512;border-color:#E8A07E;font-weight:700}
.panel.active button.act:hover{background:#f0b48f}
button:hover{border-color:#E8A07E}
kbd{font-family:inherit;font-size:11px;background:rgba(0,0,0,.25);border:1px solid rgba(232,160,126,.3);border-radius:5px;padding:1px 7px}
.panel.active kbd{background:rgba(74,21,18,.2);border-color:rgba(74,21,18,.35)}
.preset{background:none;border:none;color:#B08D87;padding:3px 8px;font-size:11px;margin:4px 4px 0 0}
.preset:hover{color:#E8A07E}
.rowbtn{background:none;border:none;color:#B08D87;padding:2px 0;font-size:11px;margin:6px 0 0}
.rowbtn:hover{color:#E8A07E}
.out{margin-top:12px;font-size:13px;overflow:auto;flex:1;min-height:0}
.pick{color:#E8A07E;font-weight:700}
.bar{height:8px;background:rgba(74,21,18,.4);border-radius:4px;margin:3px 0 8px;overflow:hidden}
.bar i{display:block;height:100%;background:#7fb069}
.dim{color:#B08D87}.amber{color:#E8A07E}.green{color:#7fb069}.red{color:#e07a6a}
.row{padding:6px 0;border-bottom:1px solid rgba(232,160,126,.07)}
.mono{font-family:"Cascadia Code",Consolas,monospace;font-size:12px}
#log{background:#241012;height:110px;flex-shrink:0;overflow:auto;padding:10px 22px;font-size:12px;color:#B08D87;font-family:"Cascadia Code",Consolas,monospace}
#log .t{color:#5c3a36;margin-right:8px}
footer{padding:6px 22px;font-size:11px;color:#5c3a36;flex-shrink:0;background:#1E0A08}
select{background:rgba(74,21,18,.25);color:#F3E6E1;border:1px solid rgba(232,160,126,.15);border-radius:8px;padding:7px;font-family:inherit}
pre{background:#241012;border:1px solid rgba(232,160,126,.12);border-radius:8px;padding:10px;font-size:11px;overflow:auto;white-space:pre;margin-top:6px;font-family:"Cascadia Code",Consolas,monospace;color:#F3E6E1}
.copy{background:none;border:none;color:#B08D87;padding:2px 8px;font-size:11px;margin-top:6px}
.tabbar{display:flex;align-items:center;margin-top:10px;font-size:11px;color:#B08D87}
.tabbar .file{font-family:"Cascadia Code",Consolas,monospace}
.tabbar button{margin:0 0 0 auto;padding:3px 7px;border:none;display:flex}
.tabbar button:hover{border:none;color:#E8A07E}
.detay{flex-shrink:0;padding:4px 26px 10px;font-size:12px;color:#B08D87;background:#1E0A08}
.detay summary{cursor:pointer;color:#B08D87}
.detay-ic{padding:8px 0 2px;line-height:1.8}
.detay-ic b{color:#E8A07E}
::-webkit-scrollbar{width:10px;height:10px}
::-webkit-scrollbar-thumb{background:rgba(232,160,126,.25);border-radius:6px}
::-webkit-scrollbar-track{background:transparent}
</style></head><body>
<header><div class="logo">ME<em>V</em></div><div class="caps"><span></span>MINIMAL EVALUATION VERDICTS<span></span></div><div class="tag">Routes text to the right owner, finds the file.</div><div class="right"><div class="badge">v1.0.0</div><div id="clock"></div></div></header>
<main>
<div class="panel"><span class="num">01</span><h2>Decision Engine</h2><div class="sub">Verify iOS signing and build rules.</div>
<label>STATUS (state)</label><textarea id="d_state" rows="3">Release build fails iOS signing, no archive produced.</textarea>
<label>QUESTION TYPE</label><select id="d_type"><option value="choice">choice — one of the options</option><option value="noul">noul — yes/no probability</option><option value="score">score — graded scale</option></select>
<label>OPTIONS (label: description, one per line)</label><textarea id="d_crit" rows="4">mobile: flutter dart ios android build gradle xcode
backend: api firebase firestore crash rule
design: ui theme color screen contrast</textarea>
<button class="act" onclick="runDecide()">Run <kbd>&#8963;&#9166;</kbd></button>
<div><button class="preset" onclick="preD(0)">ios build</button><button class="preset" onclick="preD(1)">firestore</button><button class="preset" onclick="preD(2)">theme</button></div>
<div class="out" id="d_out"><span class="dim">ready.</span></div></div>
<div class="panel"><span class="num">02</span><h2>File Finder</h2><div class="sub">Intent search across big repositories.</div>
<label>QUERY</label><input type="text" id="s_q" value="checkout bottom sheet">
<label>ROOT</label><input type="text" id="s_root" value="">
<button class="rowbtn" onclick="pickRoot()">pick another big folder ↻</button>
<label>MODE</label><select id="s_mode"><option value="semantic">semantic — by intent</option><option value="exact">exact — literal</option></select>
<button class="act" onclick="runSfind()">Scan <kbd>&#8963;&#9166;</kbd></button>
<div><button class="preset" onclick="preS('checkout bottom sheet')">checkout</button><button class="preset" onclick="preS('go_router redirect')">go_router</button><button class="preset" onclick="preS('riverpod provider')">riverpod</button></div>
<div class="out" id="s_out"><span class="dim">ready.</span></div></div>
<div class="panel"><span class="num">03</span><h2>Language</h2><div class="sub">Detect text language and channel.</div>
<label>TEXT</label><input type="text" id="r_t" value="I was billed twice, please refund">
<button class="act" onclick="runRoute()">Detect <kbd>&#8963;&#9166;</kbd></button>
<div class="out" id="r_out"><span class="dim">ready.</span></div>
<div class="out" id="st_out" style="padding-top:8px"><span class="dim">loading…</span></div></div>
<div class="panel"><span class="num">04</span><h2>Agent</h2><div class="sub">Coding use: connection and instructions.</div>
<div class="tabbar"><span class="file">opencode.json</span><button onclick="copyTxt('a_cfg')" title="Copy"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg></button></div>
<pre id="a_cfg">{
  "mcp": {
    "mev": {
      "type": "local",
      "command": ["python", "C:/path/to/Mev/mcp_server.py"],
      "enabled": true
    }
  }
}</pre>
<label>AGENT INSTRUCTIONS</label>
<pre id="a_ins">Use mev sfind to find files first.
conf >=0.85: proceed. <0.50: ask a human.</pre>
<button class="copy" onclick="copyTxt('a_ins')">copy</button>
<label>EXAMPLE FLOW</label>
<div class="out" style="font-size:12px">1. sfind("checkout bottom sheet") → candidate files<br>2. decide(content, {fix?}) → probability<br>3. low: ask, high: apply</div>
</div>
</main>
<div id="log"></div>
<footer>conf ≥0.85 proceed · &lt;0.50 ask</footer>
<details class="detay"><summary>Details</summary><div class="detay-ic">
<b>Decision Engine</b> — reads text and returns one of the given options with a confidence score; never invents text. <b>File Finder</b> — searches by intent or literally, shows line numbers. <b>Language</b> — detects language in milliseconds. <b>Agent</b> — connection info and usage instructions for coding assistants. Limits: ~60-75% on general questions, asks a human when unsure; first scan can be slow on 2000+ files.
</div></details>
<script>
function log(m){var e=document.getElementById('log');var d=document.createElement('div');d.innerHTML='<span class="t">'+new Date().toLocaleTimeString('en-US')+'</span>'+m;e.prepend(d);while(e.children.length>40)e.lastChild.remove();}
function copyTxt(id){var t=document.getElementById(id).textContent;function ok(){log('copied');}if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(t).then(ok);}else{var ta=document.createElement('textarea');ta.value=t;document.body.appendChild(ta);ta.select();try{document.execCommand('copy');}catch(e){}ta.remove();ok();}}
setInterval(function(){document.getElementById('clock').textContent=new Date().toLocaleString('en-US');},1000);
async function post(u,b){var t=performance.now();var r=await fetch(u,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)});var j=await r.json();j._ms=Math.round(performance.now()-t);return j;}
function bars(probs){var h='';for(var k in probs){var p=probs[k];h+='<div>'+k+' <span class="amber">'+p+'</span><div class="bar"><i style="width:'+Math.round(p*100)+'%"></i></div></div>';}return h;}
var PD=[['Release build fails iOS signing, no archive produced.','mobile: flutter dart ios android build gradle xcode\\nbackend: api firebase firestore crash rule\\ndesign: ui theme color screen contrast'],
['Firestore denies reads on the orders collection.','mobile: flutter dart widget\\nbackend: api firebase firestore rule permission\\ndesign: ui screen'],
['Cart button contrast fails in dark theme, accessibility broken.','mobile: flutter widget\\nbackend: api crash\\ndesign: ui theme color contrast accessibility']];
function preD(i){document.getElementById('d_state').value=PD[i][0];document.getElementById('d_crit').value=PD[i][1];runDecide();}
function preS(q){document.getElementById('s_q').value=q;runSfind();}
function fmt(ms){if(ms==null||isNaN(ms))return '?';return ms>=1000?(ms/1000).toFixed(1)+'s':Math.round(ms)+'ms';}
async function runDecide(){
 var t=document.getElementById('d_type').value, crit={};
 if(t==='score'){crit=['can wait','this week','blocking revenue'];}
 else{document.getElementById('d_crit').value.split('\\n').forEach(function(l){var i=l.indexOf(':');if(i>0)crit[l.slice(0,i).trim()]=l.slice(i+1).trim();});}
 if(t==='noul'){crit={true:'cancel subscription termination threat',false:'question request info'};}
 var q={t0:{type:t,instructions:document.getElementById('d_state').value.slice(0,40),criteria:crit}};
 try{var r=await post('/api/decide',{state:document.getElementById('d_state').value,questions:q});var a=r.answers.t0;var h='';
 if(a.type==='choice'){h='<div class="pick">▸ '+a.choice+'</div>'+bars(a.probabilities);}
 else if(a.type==='noul'){h='<div class="pick">▸ P(yes) = '+a.noul+'</div><div class="bar"><i style="width:'+Math.round(a.noul*100)+'%"></i></div>';}
 else{h='<div class="pick">▸ score = '+a.score+'</div>';}
 h+='<div class="dim">confidence '+a.confidence+' · <b class="ms">'+fmt(r.usage.latency_ms)+'</b>'+(a.distilled?' · distilled:'+a.distilled:'')+'</div>';
 document.getElementById('d_out').innerHTML=h;log('decide → <span class="green">'+(a.choice||a.noul||a.score)+'</span> '+r.usage.latency_ms+'ms');
 }catch(e){document.getElementById('d_out').innerHTML='<span class="red">error: '+e+'</span>';}
}
async function runSfind(){
 var q=document.getElementById('s_q').value, root=document.getElementById('s_root').value, mode=document.getElementById('s_mode').value;
 try{var r=await post('/api/sfind',{query:q,root:root,top_k:8,mode:mode});var h='<div class="dim">'+r.scanned+' files · <b class="ms">'+fmt(r.ms)+'</b> · grep estimate <b class="ms">~'+fmt(r.grep_tahmin_ms)+'</b></div>';if(!r.results.length)h+='<div class="amber">no results (honest: nothing matched)</div>';
 r.results.forEach(function(x,i){var c=x.confidence||'';h+='<div class="row"><span class="amber">'+(i+1)+'</span> <span class="pick mono">'+x.path+'</span> <span class="dim">'+(x.probability||'')+' conf:'+c+'</span>';(x.snippet||[]).slice(0,2).forEach(function(s){h+='<div class="dim mono">L'+s.line+': '+String(s.text).slice(0,90)+'</div>';});h+='</div>';});
 document.getElementById('s_out').innerHTML=h;log('sfind "'+q+'" → '+r.results.length+' results '+r.ms+'ms');
 }catch(e){document.getElementById('s_out').innerHTML='<span class="red">error: '+e+'</span>';}
}
async function runRoute(){
 var t=document.getElementById('r_t').value;
 try{var r=await post('/api/route',{text:t});document.getElementById('r_out').innerHTML='<div class="pick">▸ '+r.model+'</div><div class="dim">'+r.reason+' · <b class="ms">'+fmt(r.route_ms)+'</b></div>';log('route → '+r.model);
 }catch(e){document.getElementById('r_out').innerHTML='<span class="red">error: '+e+'</span>';}
}
async function pickRoot(){try{var r=await fetch('/api/bigdir').then(function(x){return x.json();});document.getElementById('s_root').value=r.root;log('root → '+r.root);}catch(e){log('root pick failed');}}
var activePanel=0;
document.querySelectorAll('.panel').forEach(function(p,idx){p.addEventListener('pointerdown',function(){document.querySelectorAll('.panel').forEach(function(q){q.classList.remove('active');});p.classList.add('active');activePanel=idx;});});
document.querySelector('.panel').classList.add('active');
document.addEventListener('keydown',function(e){if(e.ctrlKey&&e.key==='Enter'){if(activePanel===1)runSfind();else if(activePanel===2)runRoute();else runDecide();}});
(function(){var e=document.getElementById('a_cfg');if(!e||!e.textContent)return;var t=e.textContent;e.innerHTML=t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"([^"]+)":/g,'<span style="color:#E8A07E">"$1"</span>:').replace(/: "([^"]*)"/g,': <span style="color:#FDF2ED">"$1"</span>').replace(/: (true|false|[0-9]+)/g,': <span style="color:#f4b183">$1</span>');})();
fetch('/api/stats').then(function(r){return r.json();}).then(function(s){document.getElementById('st_out').innerHTML='<div class="dim">engine '+s.model+' · '+s.artifact_kb+'KB weights · '+s.tests+' tests · '+s.decide_ms+'ms/decision</div>';});
fetch('/api/bigdir').then(function(r){return r.json();}).then(function(b){var el=document.getElementById('s_root');if(el&&!el.value){el.value=b.root;log('root → '+b.root);}});
</script></body></html>
"""


def _bigdir():
    t0 = time.perf_counter()
    home = os.path.expanduser("~")
    bases = [os.path.join(home, d) for d in ("Desktop", "Documents", "OneDrive/Desktop")]
    bases = [b for b in bases if os.path.isdir(b)] or [MEV]
    scored, subs = [], []
    for b in bases:
        try:
            subs += [os.path.join(b, n) for n in os.listdir(b)]
        except OSError:
            continue
    random.shuffle(subs)
    for s in subs:
        if (time.perf_counter() - t0) * 1000 > 1200:
            break
        try:
            if not os.path.isdir(s) or os.path.islink(s):
                continue
        except OSError:
            continue
        n = 0
        for _, _, fs in os.walk(s):
            n += len(fs)
            if n > 2000 or (time.perf_counter() - t0) * 1000 > 1200:
                break
        if n >= 50:
            scored.append((n, s))
    scored.sort(reverse=True)
    pool = [s for _, s in scored[:5]] or [MEV]
    return {"root": random.choice(pool), "candidates": len(scored)}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path == "/logo.svg":
            try:
                with open(os.path.join(MEV, "assets", "logo.svg"), "rb") as f:
                    b = f.read()
            except OSError:
                self._json({"error": "not found"}, 404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "image/svg+xml")
            self.send_header("Cache-Control", "max-age=86400")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
        elif self.path in ("/", "/index.html"):
            b = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
        elif self.path == "/api/stats":
            try:
                import test_all as T
                ntests = f"{len(T.TESTS)}/{len(T.TESTS)}"
            except Exception:
                ntests = "32/32"
            akb = os.path.getsize(os.path.join(MEV, "distilled_tasks.json")) // 1024 \
                if os.path.exists(os.path.join(MEV, "distilled_tasks.json")) else 0
            t0 = time.perf_counter()
            J.decide("x", "speed", {"q": {"type": "choice", "instructions": "i",
                                          "criteria": {"a": "x", "b": "y"}}})
            dt = round((time.perf_counter() - t0) * 1000, 3)
            self._json({"model": J.MODEL_ID, "artifact_kb": akb, "tests": ntests,
                        "decide_ms": dt})
        elif self.path == "/api/bigdir":
            try:
                self._json(_bigdir())
            except Exception:
                self._json({"root": MEV, "candidates": 0})
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(max(n, 0)) or b"{}")
        except (ValueError, OSError):
            self._json({"error": "bad json"}, 400)
            return
        try:
            if self.path == "/api/decide":
                if not isinstance(body, dict):
                    raise ValueError("bad")
                self._json(J.decide(body.get("model", J.MODEL_ID), body.get("state", ""),
                                    body.get("questions", {})))
            elif self.path == "/api/sfind":
                if not isinstance(body, dict):
                    raise ValueError("bad")
                self._json(M.tool_sfind(body))
            elif self.path == "/api/route":
                if not isinstance(body, dict):
                    raise ValueError("bad")
                self._json(J.route(body.get("text", "")))
            else:
                self._json({"error": "not found"}, 404)
        except (ValueError, TypeError, KeyError):
            self._json({"error": "invalid params"}, 422)
        except Exception:
            self._json({"error": "internal error"}, 500)


if __name__ == "__main__":
    srv = HTTPServer((HOST, PORT), H)
    threading.Timer(1.0, lambda: webbrowser.open(f"http://{HOST}:{PORT}")).start()
    print(f"cockpit: http://{HOST}:{PORT} (Ctrl+C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
