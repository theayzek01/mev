#!/usr/bin/env python3
"""mev MCP: decide + sfind (grep yerine semantik bulucu). stdlib-only, stdio JSON-RPC.
Opencode: {"mcp":{"mev":{"type":"local","command":["python","C:/Users/theay/OneDrive/Desktop/Mev/mcp_server.py"],"enabled":true}}}
Araclar: decide(state,questions) | sfind(query,root,top_k,mode,...) | route(text)
"""
import json, os, re, stat, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mev as J

try:
    import index_cache as IC
    _HAS_IC = True
except ImportError:
    _HAS_IC = False

NAME, VER = "mev", "1.0.0"
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build",
             "target", ".next", ".idea", ".vscode", ".hg", "coverage", ".nyc_output"}
SKIP_EXT = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2", ".ttf", ".eot",
            ".mp3", ".mp4", ".zip", ".tar", ".gz", ".exe", ".dll", ".so", ".pyc", ".onnx",
            ".bin", ".safetensors", ".pdf"}
MAX_KB, MAX_FILES, BUDGET_MS, HEAD = 200, 4000, 1500, 4000

def tool_decide(a):
    if not isinstance(a, dict):
        raise ValueError("arguments object olmali")
    return J.decide(a.get("model", J.MODEL_ID), a.get("state", ""), a.get("questions", {}))

def tool_route(a):
    if not isinstance(a, dict):
        raise ValueError("arguments object olmali")
    return J.route(a.get("text", ""))

# TR/EN mini sozluk: TR sorgu -> EN icerik eslesmesi icin. Dar kapsamli harita,
# genel ceviri degil; Laya'nin 322M encoder'inin yerini tutmaz.
SYN = {"fatura": ["invoice", "billing"], "iade": ["refund"], "odeme": ["payment", "pay"],
       "ucret": ["charge", "fee"], "hata": ["bug", "error"], "cokme": ["crash", "outage"],
       "giris": ["login"], "sifre": ["password"], "kullanici": ["user"], "dosya": ["file"],
       "arama": ["search"], "karar": ["decision"], "skor": ["score"], "motoru": ["engine", "model"],
       "ödeme": ["payment", "pay"], "ücret": ["charge", "fee"], "şifre": ["password"],
       "invoice": ["fatura"], "refund": ["iade"], "payment": ["odeme", "ödeme"], "bug": ["hata"],
       "login": ["giris", "giriş"], "search": ["arama"], "decision": ["karar"], "billing": ["fatura"],
       "abonelik": ["subscription"], "taksit": ["installment"], "indirim": ["discount", "coupon"],
       "sepet": ["cart", "basket", "checkout"], "makbuz": ["receipt"],
       "subscription": ["abonelik"], "checkout": ["sepet", "odeme", "ödeme"], "receipt": ["makbuz"],
       "giriş": ["login", "signin"], "oturum": ["session"],
       "kayit": ["register", "signup", "record"], "kayıt": ["register", "signup", "record"],
       "sifirlama": ["reset", "password"], "sıfırlama": ["reset", "password"],
       "yetki": ["permission", "auth", "role"], "rol": ["role"], "izin": ["permission"],
       "cikis": ["logout", "exit", "signout"], "çıkış": ["logout", "exit", "signout"],
       "hesap": ["account"], "dogrulama": ["verification", "auth"], "doğrulama": ["verification", "auth"],
       "password": ["sifre", "şifre"], "auth": ["yetki", "dogrulama", "doğrulama", "giris", "giriş"],
       "session": ["oturum"], "logout": ["cikis", "çıkış"], "register": ["kayit", "kayıt"],
       "user": ["kullanici", "hesap"],
       "arayuz": ["ui", "frontend", "interface"], "arayüz": ["ui", "frontend", "interface"],
       "ekran": ["screen", "display", "view"], "sayfa": ["page"],
       "buton": ["button"], "dugme": ["button"], "düğme": ["button"],
       "menu": ["menu", "nav"], "menü": ["menu", "nav"],
       "tema": ["theme"], "mobil": ["mobile", "responsive"],
       "button": ["buton", "dugme", "düğme"], "frontend": ["arayuz", "arayüz"],
       "sunucu": ["server"], "istek": ["request"], "yanit": ["response"], "yanıt": ["response"],
       "jeton": ["token"], "anahtar": ["key", "apikey"], "sorgu": ["query"],
       "onbellek": ["cache"], "önbellek": ["cache"],
       "server": ["sunucu"], "request": ["istek"], "response": ["yanit", "yanıt"],
       "token": ["jeton"], "cache": ["onbellek", "önbellek"],
       "veritabani": ["database"], "veritabanı": ["database"], "tablo": ["table"],
       "sutun": ["column"], "sütun": ["column"], "satir": ["row"], "satır": ["row"],
       "yedek": ["backup"], "dizin": ["index", "directory"],
       "goc": ["migration"], "göç": ["migration"], "database": ["veritabani", "veritabanı"],
       "çökme": ["crash", "outage"], "istisna": ["exception", "error"],
       "gunluk": ["log", "logging"], "günlük": ["log", "logging"],
       "kesinti": ["outage", "downtime"], "uyari": ["warning", "alert"], "uyarı": ["warning", "alert"],
       "error": ["hata"], "exception": ["istisna"], "log": ["gunluk", "günlük"], "crash": ["cokme", "çökme"],
       "klasor": ["folder", "directory"], "klasör": ["folder", "directory"],
       "yukleme": ["upload"], "yükleme": ["upload"], "indirme": ["download"], "filtre": ["filter"],
       "file": ["dosya"], "upload": ["yukleme", "yükleme"], "download": ["indirme"], "filter": ["filtre"],
       "eposta": ["email", "mail"], "posta": ["mail", "email"],
       "bulten": ["newsletter"], "bülten": ["newsletter"],
       "bildirim": ["notification"], "davet": ["invite", "invitation"], "şablon": ["template"],
       "email": ["eposta", "posta"], "notification": ["bildirim"],
       "birim": ["unit"], "entegrasyon": ["integration"], "kapsam": ["coverage"],
       "derleme": ["build"], "taklit": ["mock"], "iddia": ["assert"],
       "testing": ["test"], "coverage": ["kapsam"], "mock": ["taklit"], "assert": ["iddia"],
       "surum": ["release", "version"], "sürüm": ["release", "version"],
       "dagitim": ["deploy", "deployment"], "dağıtım": ["deploy", "deployment"],
       "altyapi": ["infra", "infrastructure"], "altyapı": ["infra", "infrastructure"],
       "bulut": ["cloud"], "kapsayici": ["container"], "kapsayıcı": ["container"],
       "deploy": ["dagitim", "dağıtım"], "docker": ["kapsayici", "kapsayıcı", "container"],
       # SYN v2: Laya ogretmenden madencilik (emin+dogru bildigi durumlarin tokenlari)
       "faturasında": ["invoice", "billing"], "tahsilat": ["charge", "payment"],
       "iadesi": ["refund"], "çift": ["duplicate", "double"], "double": ["çift", "duplicate"],
       "duplicate": ["çift", "double"],
       "şifremi": ["password"], "hesabıma": ["account"], "unuttum": ["forgot", "password"],
       "parola": ["password"], "forgot": ["unuttum", "sifre", "şifre"],
       "yenileme": ["refresh", "renew"], "uzatma": ["extend", "extension"],
       "kullanıcı": ["user"], "refresh": ["yenileme"], "extend": ["uzatma"],
       "kargo": ["parcel", "cargo", "tracking"], "takip": ["tracking"], "kurye": ["courier"],
       "ekranı": ["screen"], "gösterir": ["shows", "display"], "tracking": ["takip", "kargo"],
       "tarayıcıda": ["browser"], "beyaz": ["blank", "white"], "uygulama": ["app", "application"],
       "browser": ["tarayıcıda"], "blank": ["beyaz", "bos"], "app": ["uygulama"],
       "özellik": ["feature"], "talebim": ["request"], "feature": ["özellik"],
       "cancel": ["iptal", "cikis", "çıkış"], "iptal": ["cancel"],
       "merhaba": ["hello", "hi"], "teşekkürler": ["thanks", "thank"],
       "fiyat": ["price", "pricing"], "teklif": ["quote", "offer"]}

def _expand(qt):
    out = list(qt)
    for t in qt:
        out += SYN.get(t, [])
    return out

MAX_LINE, MAX_QUERY, MAX_DEPTH, MAX_DIRS = 1000000, 4000, 25, 2000

def _is_within(p_real, base_real):
    try:
        return os.path.commonpath([os.path.normcase(p_real), os.path.normcase(base_real)]) == os.path.normcase(base_real)
    except ValueError:
        return False

def _glob_tr(p):
    i, n, r = 0, len(p), ""
    while i < n:
        if p[i:i + 3] == "**/":
            r += "(?:.*/)?"
            i += 3
        elif p[i:i + 2] == "**":
            r += ".*"
            i += 2
        elif p[i] == "*":
            r += "[^/]*"
            i += 1
        elif p[i] == "?":
            r += "[^/]"
            i += 1
        elif p[i] == "[":
            j = p.find("]", i + 1)
            r += (p[i:j + 1] if j > 0 else "\\[")
            i = (j + 1 if j > 0 else i + 1)
        else:
            r += re.escape(p[i])
            i += 1
    return r

def _load_ignore(d, base, rules):
    try:
        with open(os.path.join(d, ".gitignore"), "r", encoding="utf-8", errors="ignore") as f:
            raw = f.read(65536).splitlines()[:500]
    except OSError:
        return
    for ln in raw:
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        neg = s.startswith("!")
        if neg:
            s = s[1:].strip()
        if s.startswith("\\#") or s.startswith("\\!"):
            s = s[1:]
        if not s or s == "/":
            continue
        donly = s.endswith("/")
        s = s[:-1] if donly else s
        s = s.strip("/")
        if not s:
            continue
        anch = s.startswith("/") or "/" in s
        s = s.lstrip("/")
        if "**" in s or anch or donly:
            try:
                rx = re.compile("^" + _glob_tr(s) + "(?:/.*)?$")
            except re.error:
                continue
            rules.append((base, neg, True, rx, None))
        else:
            import fnmatch
            rules.append((base, neg, False, None, s))

def _ignored(rules, rel, is_dir):
    import fnmatch
    bn = rel.rsplit("/", 1)[-1]
    hit = None
    for b, neg, is_rx, rx, pat in rules:
        if b and not (rel == b or rel.startswith(b + "/")):
            continue
        sub = rel[len(b) + 1:] if b else rel
        ok = bool(rx.match(sub)) if is_rx else fnmatch.fnmatchcase(bn, pat)
        if ok:
            hit = not neg
    return hit is True

def _files(root, t0):
    out, seen = [], {os.path.realpath(root)}
    stack, ndir = [(root, 0)], 0
    while stack and len(out) < MAX_FILES:
        if (time.perf_counter() - t0) * 1000 > BUDGET_MS:
            break
        if len(stack) > MAX_DIRS or ndir > MAX_DIRS:
            break
        d, dep = stack.pop()
        if dep > MAX_DEPTH:
            continue
        rules = []
        chain, tmp = [], d
        while True:
            chain.append(tmp)
            if os.path.realpath(tmp) == os.path.realpath(root):
                break
            par = os.path.dirname(tmp)
            if par == tmp:
                break
            tmp = par
        for anc in reversed(chain):
            r = os.path.relpath(anc, root).replace(os.sep, "/")
            _load_ignore(anc, "" if r == "." else r, rules)
        try:
            with os.scandir(d) as it:
                ents = list(it)
        except OSError:
            continue
        for e in ents:
            if (time.perf_counter() - t0) * 1000 > BUDGET_MS:
                break
            if len(out) >= MAX_FILES:
                break
            try:
                nm = e.name
                if e.is_symlink():
                    continue
                is_dir = e.is_dir(follow_symlinks=False)
                rel = os.path.relpath(e.path, root).replace(os.sep, "/")
                if nm in SKIP_DIRS or rel == ".git" or rel.startswith(".git/"):
                    continue
                if nm.startswith(".") and nm != ".gitignore":
                    continue
                if not is_dir and os.path.splitext(nm)[1].lower() in SKIP_EXT:
                    continue
                if _ignored(rules, rel, is_dir):
                    continue
                if is_dir:
                    try:
                        rp = os.path.realpath(e.path)
                    except OSError:
                        continue
                    if rp in seen or not _is_within(rp, os.path.realpath(root)):
                        continue
                    seen.add(rp)
                    ndir += 1
                    stack.append((e.path, dep + 1))
                elif e.is_file(follow_symlinks=False):
                    try:
                        st = e.stat(follow_symlinks=False)
                        if not stat.S_ISREG(st.st_mode) or st.st_size > MAX_KB * 1024:
                            continue
                    except OSError:
                        continue
                    if nm == ".gitignore":
                        continue
                    out.append(e.path)
            except OSError:
                continue
    return out

def _head(p):
    try:
        st = os.lstat(p)
        if not stat.S_ISREG(st.st_mode) or st.st_size > MAX_KB * 1024:
            return ""
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(HEAD)
    except (OSError, ValueError, UnicodeError):
        return ""

def _snippet(head, qtoks, exact=None, ctx=1, cap=5):
    lines = head.splitlines()
    if not lines:
        return []
    if exact is not None:
        if isinstance(exact, str):
            ndl, rx = exact.casefold(), None
        else:
            ndl, rx = None, exact
        hits = []
        for i, l in enumerate(lines):
            ok = rx.search(l) is not None if rx else ndl in l.casefold()
            if ok:
                hits.append(i)
                if len(hits) == 2:
                    break
        if not hits:
            hits = [i for i, l in enumerate(lines) if l.strip()][:1]
    else:
        qset = set(qtoks) if qtoks else set()
        scored = []
        for i, l in enumerate(lines):
            s = l.strip()
            if not s:
                continue
            ls = J.norm(l)
            h = sum(1 for t in qset if t and t in ls)
            if h == 0:
                continue
            scored.append((h * 2.0 + min(1.0, h * 10.0 / max(20, len(ls))) - i * 0.001, i))
        scored.sort(key=lambda x: -x[0])
        hits = [i for _, i in scored[:2]]
        if not hits:
            hits = [i for i, l in enumerate(lines) if l.strip()][:1]
    want = set()
    for h in hits:
        for dd in range(-ctx, ctx + 1):
            j = h + dd
            if 0 <= j < len(lines) and lines[j].strip():
                want.add(j)
    return [{"line": j + 1, "text": lines[j].strip()[:160]} for j in sorted(want)[:cap]]

def _sfind_temp(qt, routing):
    n = len(qt)
    t = 1.25 if n <= 3 else (0.70 if n >= 8 else 0.90)
    if (routing or {}).get("model") == "mini-multilingual":
        t += 0.20
    return t

def _sfind_conf(probs):
    out = []
    for i, p in enumerate(probs):
        nxt = probs[i + 1] if i + 1 < len(probs) else 0.0
        m = p - nxt if p > nxt else 0.0
        out.append(round(min(0.99, 0.5 * p + 0.5 * (0.5 + m)), 4))
    if len(probs) > 1 and probs[0] - probs[1] < 0.05:
        out[0] = round(min(out[0], 0.35), 4)
    if len(probs) == 1 and probs[0] > 0.9:
        out[0] = round(min(out[0], 0.65), 4)
    return out

def _resolve_root(a):
    raw = a.get("root") or os.getcwd()
    if not isinstance(raw, str) or not raw.strip() or len(raw) > 4096 or "\x00" in raw:
        raise ValueError("root gecersiz")
    real = os.path.realpath(os.path.abspath(raw.strip()))
    if not os.path.isdir(real):
        raise ValueError("root bulunamadi")
    return real

def _validate_sfind(a):
    if not isinstance(a, dict):
        raise ValueError("arguments object olmali")
    q = a.get("query", "")
    if not isinstance(q, str) or not q.strip() or len(q) > MAX_QUERY:
        raise ValueError("query 1..4000 karakter string olmali")
    tk = a.get("top_k", 8)
    if isinstance(tk, bool):
        raise ValueError("top_k integer olmali")
    if isinstance(tk, str):
        if not tk.strip().isdigit():
            raise ValueError("top_k integer olmali")
        tk = int(tk.strip())
    if isinstance(tk, float):
        if not tk.is_integer():
            raise ValueError("top_k integer olmali")
        tk = int(tk)
    if not isinstance(tk, int):
        raise ValueError("top_k integer olmali")
    mode = a.get("mode", "semantic")
    if not isinstance(mode, str) or mode.lower() not in ("semantic", "exact"):
        raise ValueError("mode semantic|exact olmali")
    inc = a.get("include", "")
    if inc is None:
        inc = ""
    if not isinstance(inc, str) or len(inc) > 256 or "\x00" in inc:
        raise ValueError("include string olmali")
    try:
        context = int(a.get("context", 0))
    except (TypeError, ValueError):
        raise ValueError("context 0-3 arasi olmali")
    return q.strip(), max(1, min(25, tk)), mode.lower(), inc.lower(), max(0, min(3, context)), \
        bool(a.get("use_regex", False)), bool(a.get("case_sensitive", False)), bool(a.get("index", True))

EXACT_PER_FILE = 10

def _grep_tahmin(paths, query, t0):
    # Dürüst tahmin: ilk 12 dosyada GERÇEK birebir tarama ölç, dosya sayısına ölçekle.
    k = min(12, len(paths))
    if k == 0:
        return 0.0
    ndl = query.casefold()
    dt, n = 0.0, 0
    for p in paths[:k]:
        if (time.perf_counter() - t0) * 1000 > BUDGET_MS:
            break
        a = time.perf_counter()
        try:
            st = os.lstat(p)
            if not stat.S_ISREG(st.st_mode):
                continue
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                txt = f.read(MAX_KB * 1024)
            _ = ndl in txt.casefold()
        except (OSError, ValueError, UnicodeError):
            continue
        dt += (time.perf_counter() - a) * 1000
        n += 1
    return round(dt / max(n, 1) * len(paths), 1)

def _read_lines(p, t0):
    try:
        st = os.lstat(p)
        if not stat.S_ISREG(st.st_mode) or st.st_size > MAX_KB * 1024:
            return []
        out = []
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            for i, raw in enumerate(f, start=1):
                if i % 100 == 0 and (time.perf_counter() - t0) * 1000 > BUDGET_MS:
                    break
                out.append(raw.rstrip("\n")[:500])
                if len(out) > 20000:
                    break
        return out
    except (OSError, ValueError, UnicodeError):
        return []

def tool_sfind(a):
    t0 = time.perf_counter()
    query, top_k, mode, inc, context, use_regex, case_sensitive, use_index = _validate_sfind(a)
    root = _resolve_root(a)
    routing = J.route(query)
    paths = [p for p in _files(root, t0) if (not inc or inc in os.path.basename(p).lower())]
    scanned = len(paths)
    g_ms = _grep_tahmin(paths, query, t0)
    res = []
    idx = IC.load(root) if (use_index and _HAS_IC) else None
    if mode == "exact":
        if use_regex:
            try:
                rx = re.compile(query, 0 if case_sensitive else re.IGNORECASE)
            except re.error as e:
                raise ValueError(f"gecersiz regex: {e}")
            ndl = None
        else:
            rx = None
            ndl = query if case_sensitive else query.casefold()
        TOTAL_CAP, shown, timed_out = top_k * EXACT_PER_FILE, 0, False
        for p in paths:
            if (time.perf_counter() - t0) * 1000 > BUDGET_MS or shown >= TOTAL_CAP:
                timed_out = (time.perf_counter() - t0) * 1000 > BUDGET_MS
                break
            lines = _read_lines(p, t0)
            if not lines:
                continue
            midx, total = [], 0
            for i, line in enumerate(lines, start=1):
                hit = rx.search(line) is not None if rx else (ndl in line if case_sensitive else ndl in line.casefold())
                if hit:
                    total += 1
                    if len(midx) < EXACT_PER_FILE:
                        midx.append(i)
            if not midx:
                continue
            want = {}
            for mm in midx:
                for j in range(max(1, mm - context), min(len(lines), mm + context) + 1):
                    want.setdefault(j, j in midx)
            sn = [{"line": j, "text": lines[j - 1][:160], "match": want[j]} for j in sorted(want)]
            res.append({"path": os.path.relpath(p, root), "matches": len(midx),
                        "total_matches": total, "truncated": total > len(midx), "snippet": sn})
            shown += len(midx)
            if len(res) >= top_k:
                break
        ms = round((time.perf_counter() - t0) * 1000, 1)
        return {"query": query, "mode": "exact", "routing": routing, "scanned": scanned,
                "results": res, "ms": ms, "grep_tahmin_ms": g_ms, "timed_out": timed_out,
                "flags": {"use_regex": use_regex, "case_sensitive": case_sensitive, "context": context}}
    qt = _expand(J.toks(query))
    qset = set(qt)
    qg = set(J.chargrams(query))
    pre = []
    for p in paths:
        rel = os.path.relpath(p, root).replace(os.sep, "/")
        pt = J.toks(rel.replace("/", " ").replace(".", " ").replace("_", " ").replace("-", " "))
        base = os.path.basename(rel).lower()
        hit = any(len(q) >= 3 and q in base for q in qset)
        alpha = 1.4 if hit else 0.5
        ps = len(set(pt) & qset) * alpha + (0.8 if hit else 0.0)
        if ps > 0 or len(pre) < 400:
            pre.append((ps, p, rel))
    pre.sort(key=lambda x: -x[0])
    cands = pre[:120]
    heads = []
    for s, p, r in cands:
        h = IC.get(idx, root, p) if idx is not None else None
        if h is None:
            h = _head(p)
            if idx is not None:
                IC.put(idx, root, p, h)
        heads.append((s, p, r, h))
    if idx is not None:
        IC.save(root, idx, {r for _, _, r in cands})
    docs = [J.toks(h) for _, _, _, h in heads] + [qt]
    idf = J.idf_map(docs)
    scored = []
    for (s, p, r, h), dt in zip(heads, docs):
        lg = J.sim(qt, dt, idf, set(qg), set(J.chargrams(h[:2000])))
        score = round(float(s + lg), 4)
        if score > 0:
            scored.append((score, p, r, h))
    scored.sort(key=lambda x: -x[0])
    top = scored[:top_k]
    ms = round((time.perf_counter() - t0) * 1000, 1)
    if not top:
        fb = sorted(heads, key=lambda x: -x[0])[:min(top_k, 3)]
        n = max(1, len(fb))
        for s, p, r, h in fb:
            res.append({"path": r, "score": 0.0, "probability": round(1.0 / n, 4),
                        "confidence": 0.09, "snippet": _snippet(h, qt), "best_effort": True})
        return {"query": query, "mode": "semantic", "routing": routing, "scanned": scanned,
                "results": res, "ms": ms, "grep_tahmin_ms": g_ms, "best_effort": True}
    temp = _sfind_temp(qt, routing)
    probs = J.softmax([s for s, _, _, _ in top], temp=temp) if top else []
    confs = _sfind_conf(probs)
    for i, (s, p, r, h) in enumerate(top):
        res.append({"path": r, "score": s, "probability": round(float(probs[i]), 4),
                    "confidence": confs[i], "snippet": _snippet(h, qt)})
    return {"query": query, "mode": "semantic", "routing": routing, "scanned": scanned,
            "results": res, "ms": ms, "grep_tahmin_ms": g_ms, "temp": round(temp, 2)}

TOOLS = {
    "decide": ("Tip uretmeden karar ver (choice/noul/score + olasilik).",
               {"type": "object", "properties": {
                   "state": {"description": "Metin veya JSON durum"},
                   "questions": {"type": "object", "description": "{id:{type,instructions,criteria}}"},
                   "model": {"type": "string"}}, "required": ["state", "questions"]}),
    "sfind": ("Devasa repoda niyetle dosya bul (grep yerine). mode=semantic|exact.",
              {"type": "object", "properties": {
                  "query": {"type": "string", "description": "Dogal dil niyet veya exact string/regex"},
                  "root": {"type": "string", "description": "Arama koku (varsayilan cwd)"},
                  "top_k": {"type": "integer", "default": 8},
                  "mode": {"type": "string", "enum": ["semantic", "exact"], "default": "semantic"},
                  "include": {"type": "string", "description": "Dosya adi filtresi, orn .py"},
                  "use_regex": {"type": "boolean", "default": False, "description": "exact: query regex sayilir"},
                  "case_sensitive": {"type": "boolean", "default": False, "description": "exact: buyuk/kucuk harf duyarli"},
                  "context": {"type": "integer", "default": 0, "minimum": 0, "maximum": 3, "description": "exact: baglam satiri"},
                  "index": {"type": "boolean", "default": True, "description": "semantic: .mevidx disk cache kullan"}},
               "required": ["query"]}),
    "route": ("Dili/scripti <0.5ms'de tespit et.",
              {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}),
}
FN = {"decide": tool_decide, "sfind": tool_sfind, "route": tool_route}

def _ok(i, r):
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": i, "result": r}, ensure_ascii=False) + "\n")
    sys.stdout.flush()

def _err(i, c, m):
    m = "gecersiz parametre" if c == -32602 else ("parse hatasi" if c == -32700 else "ic hata") \
        if c in (-32602, -32700, -32603) else str(m)[:200]
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": i, "error": {"code": c, "message": m}}, ensure_ascii=False) + "\n")
    sys.stdout.flush()

def serve():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    for line in sys.stdin:
        if len(line) > MAX_LINE + 8192:
            continue
        line = line.strip()
        if not line:
            continue
        try:
            m = json.loads(line)
        except json.JSONDecodeError:
            _err(None, -32700, "")
            continue
        if not isinstance(m, dict):
            _err(None, -32600, "gecersiz istek")
            continue
        i, meth, p = m.get("id"), m.get("method", ""), m.get("params")
        if p is None:
            p = {}
        if not isinstance(p, dict) or not isinstance(meth, str):
            if m.get("id") is None:
                continue
            _err(m.get("id"), -32602, "")
            continue
        nid = None if i is None or isinstance(i, bool) or not isinstance(i, (str, int)) else i
        is_notif = i is None
        if meth == "initialize":
            if is_notif:
                continue
            _ok(nid, {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}},
                    "serverInfo": {"name": NAME, "version": VER}})
        elif meth in ("notifications/initialized", "notifications/cancelled"):
            continue
        elif meth == "tools/list":
            if is_notif:
                continue
            _ok(nid, {"tools": [{"name": n, "description": d, "inputSchema": s} for n, (d, s) in TOOLS.items()]})
        elif meth == "tools/call":
            if is_notif:
                continue
            name, args = p.get("name", ""), p.get("arguments") if "arguments" in p else {}
            if args is None:
                args = {}
            try:
                if not isinstance(name, str) or name not in FN:
                    _err(nid, -32602, "")
                    continue
                out = FN[name](args)
                _ok(nid, {"content": [{"type": "text", "text": json.dumps(out, ensure_ascii=False)}]})
            except (KeyError, ValueError, TypeError):
                _err(nid, -32602, "")
            except Exception:
                _err(nid, -32603, "")
        elif meth == "ping":
            if is_notif:
                continue
            _ok(nid, {})
        else:
            if not is_notif:
                _err(nid, -32601, "bilinmeyen metod")

if __name__ == "__main__":
    serve()
