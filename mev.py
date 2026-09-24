#!/usr/bin/env python3
"""
mev: ultra-küçük lokal karar motoru (stdlib only)
API: POST /api/alpha/decisions  body={model, state, questions} -> {model, answers, usage}
Tipler: choice | noul | score (metin üretmeden tip'li karar + olasılık)
Kullanım:
  python mev.py demo
  python mev.py serve --port 8013
  python mev.py bench
"""
import json, math, os, re, sys, time, unicodedata
from http.server import BaseHTTPRequestHandler, HTTPServer

TOKEN_RE = re.compile(r"[\w]+", re.UNICODE)
MODEL_ID = "local/mev-1.0"
# Laya'dan alınan fikirler (ağırlıksız, stdlib ile): non-autoregressive tek-pas skorlama,
# sub-ms Router (script+function-word), metin üretimi yok, sıcaklığa göre kalibrasyon.

def norm(s):
    s = unicodedata.normalize("NFKC", s).casefold()
    return "".join(c for c in s if unicodedata.category(c)[0] != "M")

def toks(s):
    return TOKEN_RE.findall(norm(s))

def chargrams(s, n=3):
    s = norm(s).replace(" ", "")
    return [s[i:i+n] for i in range(max(0, len(s)-n+1))] if len(s) >= n else [s]

# --- Damıtma öğrencisi (Laya öğretmen soft-labels, hash-lineer, opsiyonel) ---
_DIST = None
_DIST_BUCKETS = 16384

def _hbucket(tok):
    h = 2166136261
    for ch in tok:
        h ^= ord(ch)
        h = (h * 16777619) & 0xFFFFFFFF
    return h % _DIST_BUCKETS

def _dist():
    global _DIST
    if _DIST is None:
        try:
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "distilled_tasks.json"), encoding="utf-8") as f:
                _DIST = json.load(f)
            if not isinstance(_DIST, dict) or _DIST.get("buckets", _DIST_BUCKETS) != _DIST_BUCKETS:
                _DIST = {}
        except (OSError, ValueError):
            _DIST = {}
    return _DIST

def _match_task(qtype, criteria):
    try:
        labs = set(criteria.keys()) if qtype == "choice" else {"true", "false"}
        best, bs = None, 0.0
        for tid, t in _dist().get("tasks", {}).items():
            if t.get("type") != qtype:
                continue
            tl = set(t.get("labels", []))
            if qtype == "noul":
                j = 1.0 if set(criteria.keys()) == {"true", "false"} else 0.0
            else:
                j = len(labs & tl) / max(1, len(labs | tl))
            if j >= 0.6 and j > bs:
                best, bs = (tid, t), j
        return best
    except Exception:
        return None

def _student_logits(t, st):
    W = t.get("W", {})
    tf = {}
    for tok in st:
        b = _hbucket(tok)
        tf[b] = tf.get(b, 0) + 1
    if _dist().get("bigram"):
        for a, b in zip(st, st[1:]):
            h = _hbucket(a + " " + b)
            tf[h] = tf.get(h, 0) + 1
    out = {}
    for lab, vec in W.items():
        s = 0.0
        for b, w in vec:
            c = tf.get(b)
            if c:
                s += w * c
        out[lab] = s
    return out

# --- Laya-tipi Router: <0.5ms, bağımlılıksız ---
def script_of(s):
    lat = dev = arb = cjk = cyl = 0
    letters = 0
    for c in s:
        o = ord(c)
        if c.isalpha():
            letters += 1
            if 0x400 <= o <= 0x4FF: cyl += 1
            elif 0x600 <= o <= 0x6FF or 0x750 <= o <= 0x77F: arb += 1
            elif 0x900 <= o <= 0x97F: dev += 1
            elif o >= 0x4E00: cjk += 1
            else: lat += 1
    return {"latin": lat, "cyrillic": cyl, "arabic": arb, "devanagari": dev, "cjk": cjk, "letters": letters}

FUNC = {"tr": {"ve", "bir", "için", "değil", "fatura", "ücret", "iade"},
        "en": {"the", "please", "refund", "invoice", "and", "for"},
        "de": {"und", "bitte", "konto", "rechnung", "für"},
        "fr": {"le", "la", "remboursement", "facture", "pour"},
        "es": {"que", "por", "favor", "cuenta", "reembolso"}}

def route(state_text):
    t0 = time.perf_counter()
    sc = script_of(state_text)
    n = max(1, sc["letters"])
    ws = set(toks(state_text))
    if sc["devanagari"]/n > 0.2 or sc["arabic"]/n > 0.2 or sc["cjk"]/n > 0.2 or sc["cyrillic"]/n > 0.2:
        script = max(sc, key=lambda k: sc[k] if k != "letters" else -1)
        return {"model": "mini-multilingual", "reason": f"non-Latin script ({script})",
                "route_ms": round((time.perf_counter()-t0)*1000, 3)}
    scores = {l: len(ws & w) for l, w in FUNC.items()}
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return {"model": "mini-english", "reason": "default: kısa Latin metinde sinyal yok",
                "route_ms": round((time.perf_counter()-t0)*1000, 3)}
    if best == "en":
        return {"model": "mini-english", "reason": "Latin + English function words",
                "route_ms": round((time.perf_counter()-t0)*1000, 3)}
    return {"model": "mini-multilingual", "reason": f"Latin ama dil '{best}' görünüyor",
            "route_ms": round((time.perf_counter()-t0)*1000, 3)}

def textify(state):
    if isinstance(state, str): return state
    if isinstance(state, dict):
        parts = []
        for k, v in state.items():
            parts.append(str(k) + " " + textify(v))
        return " ".join(parts)
    if isinstance(state, (list, tuple)): return " ".join(textify(x) for x in state)
    return str(state)

def idf_map(docs):
    # docs: list[list[str]] -> token->idf
    df = {}
    for d in docs:
        for t in set(d):
            df[t] = df.get(t, 0) + 1
    n = max(1, len(docs))
    return {t: math.log((1 + n) / (1 + c)) + 1.0 for t, c in df.items()}

def sim(state_t, opt_t, idf, state_c=None, opt_c=None):
    # kelime overlap (ağır) + char-3gram overlap (çok dilli, çekimli diller için)
    if not state_t or not opt_t: return 0.0
    sset = set(state_t)
    score = sum(idf.get(t, 1.0) * (1 + state_t.count(t) * 0.15) for t in set(opt_t) if t in sset)
    w = score / (1 + 0.08 * math.log1p(len(opt_t)))
    if state_c is not None and opt_c is not None and opt_c:
        cs, co = set(state_c), set(opt_c)
        inter = len(cs & co)
        c = inter / max(1, len(co))  # 0..1
        return 0.72 * w + 0.28 * c * 3.0
    return w

def softmax(xs, temp=0.9):
    if temp <= 0: temp = 0.9
    m = max(xs)
    ex = [math.exp((x - m) / temp) for x in xs]
    s = sum(ex) or 1.0
    return [e / s for e in ex]

def decide_one(qtype, st, sc, criteria, instructions="", temp=0.9):
    # st: önceden tokenize edilmiş state (tek-pas), sc: char-3gram'ları
    ins = " " + (instructions or "")
    if qtype == "choice":
        labels = list(criteria.keys())
        if not labels:
            raise ValueError("criteria bos olamaz")
        descs = [str(criteria[k]) + ins for k in labels]
        dtoks = [toks(d) for d in descs]
        dgrams = [chargrams(d) for d in descs]
        idf = idf_map(dtoks + [st])
        logits = [sim(st, dt, idf, sc, dg) for dt, dg in zip(dtoks, dgrams)]
        m = _match_task("choice", criteria)
        tid = None
        if m is not None:
            tid, t = m
            sw = _student_logits(t, st)
            beta = float(t.get("beta", 0.0))
            logits = [b + beta * sw.get(l, 0.0) for b, l in zip(logits, labels)]
            temp = float(t.get("temp", temp))
        if max(logits) == 0:  # Laya'nın çöküş hatasına düşme: uniform + düşük güven
            p = [1.0 / len(labels)] * len(labels)
            return {"type": "choice", "choice": labels[0],
                    "probabilities": {l: round(float(x), 4) for l, x in zip(labels, p)},
                    "confidence": 0.09, "distilled": tid}
        p = softmax(logits, temp=temp)
        order = sorted(range(len(labels)), key=lambda i: -p[i])
        if len(p) == 1:
            conf = round(float(p[0]), 4)
        else:
            conf = round(min(0.99, 0.5 * p[order[0]] + 0.5 * (0.5 + max(0.0, p[order[0]] - p[order[1]]))), 4)
        return {"type": "choice", "choice": labels[order[0]],
                "probabilities": {l: round(float(x), 4) for l, x in zip(labels, p)},
                "confidence": conf, "distilled": tid}
    if qtype == "noul":
        td = str(criteria.get("true", "yes")) + ins
        fd = str(criteria.get("false", "no")) + ins
        tt, ft = toks(td), toks(fd)
        idf = idf_map([tt, ft, st])
        lt = sim(st, tt, idf, sc, chargrams(td))
        lf = sim(st, ft, idf, sc, chargrams(fd))
        m = _match_task("noul", criteria)
        tid = None
        if m is not None:
            tid, t = m
            sw = _student_logits(t, st)
            lt = lt + float(t.get("beta", 0.0)) * sw.get("true", 0.0)
        if lt == 0 and lf == 0 and tid is None:
            return {"type": "noul", "noul": 0.5, "confidence": 0.09, "distilled": None}
        if lt == 0 and lf == 0:
            return {"type": "noul", "noul": 0.5, "confidence": 0.09, "distilled": tid}
        py = round(float(softmax([lf, lt], temp=temp)[1]), 4)
        return {"type": "noul", "noul": py, "confidence": round(abs(py - 0.5) * 1.8 * 0.9 + 0.09, 4),
                "distilled": tid}
    if qtype == "score":
        levels = list(criteria)
        if not levels:
            raise ValueError("criteria bos olamaz")
        n = len(levels)
        ltoks = [toks(str(l) + ins) for l in levels]
        lgrams = [chargrams(str(l) + ins) for l in levels]
        idf = idf_map(ltoks + [st])
        logits = [sim(st, lt, idf, sc, lg) for lt, lg in zip(ltoks, lgrams)]
        p = [1.0 / n] * n if max(logits) == 0 else softmax(logits, temp=min(temp, 0.7))
        return {"type": "score", "score": round(float(sum(i * x for i, x in enumerate(p))), 4),
                "probabilities": [round(float(x), 4) for x in p],
                "confidence": round(float(max(p)), 4), "distilled": None}
    raise ValueError("unknown type: " + str(qtype))

def decide(model, state, questions):
    if not isinstance(questions, dict):
        raise ValueError("questions object olmali")
    t0 = time.perf_counter()
    s = textify(state)
    r = route(s)  # Laya Router fikri: önce dil/script, sonra skor
    temp = 1.1 if r["model"] == "mini-multilingual" else 0.9  # çok dilli = daha temkinli
    st, sc = toks(s), chargrams(s)  # TEK-PAS: state bir kez tokenize edilir
    answers = {qid: decide_one(q.get("type"), st, sc, q.get("criteria", {}),
                               q.get("instructions", ""), temp)
               for qid, q in questions.items()}
    dt = (time.perf_counter() - t0) * 1000
    return {"model": MODEL_ID, "answers": answers, "routing": r,
            "usage": {"input_tokens": max(1, len(s.split())), "output_tokens": 0,
                      "cost": 0.0, "latency_ms": round(dt, 3)}}

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers()
        self.wfile.write(b)
    def do_POST(self):
        if self.path.rstrip("/") not in ("/api/alpha/decisions", "/api/alpha/decisions/systemone",
                                         "/v1/systemone", "/api/v1/systemone"):
            self._send({"error": "not found"}, 404)
            return
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0 or n > 1000000:
            self._send({"error": "Content-Length 1..1000000 olmali"}, 400)
            return
        try:
            raw = self.rfile.read(n)
            try:
                body = json.loads(raw)
            except ValueError:
                self._send({"error": "bozuk JSON"}, 400)
                return
            if not isinstance(body, dict):
                self._send({"error": "body object olmali"}, 400)
                return
            try:
                out = decide(body.get("model", MODEL_ID), body.get("state", ""), body.get("questions", {}))
            except (ValueError, TypeError, KeyError) as e:
                self._send({"error": str(e)[:200]}, 422)
                return
            out["id"] = "local-" + str(int(time.time() * 1000))
            out["provider"] = "local"
            self._send(out)
        except Exception as e:
            self._send({"error": str(e)[:200]}, 500)

def demo():
    qs = {"department": {"type": "choice", "instructions": "Which team should handle this?",
                         "criteria": {"billing": "invoices payments refunds fatura ücret iade",
                                      "technical": "bugs outages errors bug hata çökme",
                                      "other": "everything else"}}}
    for text in ["Eylül faturamda iki kez Pro ücreti alınmış, iade istiyorum.",
                 "Hi, we were billed twice for March. Please refund.",
                 "मुझसे मार्च में दो बार शुल्क लिया गया, कृपया वापस करें।",
                 "La aplicación se cierra cada vez que abro la configuración."]:
        r = decide(MODEL_ID, text, qs)
        a = r["answers"]["department"]
        print(f"{text[:45]:45} -> {a['choice']} conf={a['confidence']} via {r['routing']['model']} ({r['routing']['reason']})")

def bench():
    import timeit
    state = "Checkout'ta Öde'ye basınca ekran beyaz kalıyor, iki tarayıcıda denedim."
    qs = {"team": {"type": "choice", "instructions": "Hangi ekip?",
                   "criteria": {"payments": "ödeme kasa fatura", "frontend": "ekran render tarayıcı",
                                "account": "giriş yetki profil"}}}
    f = lambda: decide(MODEL_ID, state, qs)
    f()
    n = 1000
    dt = timeit.timeit(f, number=n) / n * 1000
    print(f"ortalama latency: {dt:.3f} ms/op | {n} çağrı | tek dosya, bağımlılık yok")
    print("API (300-800ms) ile kıyas: ~%.0fx daha düşük gecikme" % (500 / max(dt, 0.01)))
    print(json.dumps(f(), ensure_ascii=False))

if __name__ == "__main__":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass
    cmd = sys.argv[1] if len(sys.argv) > 1 else "demo"
    if cmd == "serve":
        port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8013
        print(f"mev dinliyor: http://127.0.0.1:{port}/api/alpha/decisions")
        HTTPServer(("127.0.0.1", port), H).serve_forever()
    elif cmd == "bench": bench()
    else: demo()
