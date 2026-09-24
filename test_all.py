#!/usr/bin/env python3
"""mev stdlib-only test paketi: pytest YOK, duz assert. Hizli + izole (tempfile)."""
import io, json, os, sys, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mev as J
import mcp_server as M

Q_CHOICE = {"dept": {"type": "choice", "instructions": "Which team?",
    "criteria": {"billing": "invoices payments refunds fatura ucret iade",
                 "technical": "bugs outages errors bug hata cokme crash"}}}

def test_decide_choice_tr():
    r = J.decide(J.MODEL_ID, "Eylul faturamda iki kez ucret alinmis, iade istiyorum.", Q_CHOICE)
    assert r["model"] == J.MODEL_ID
    assert r["answers"]["dept"]["choice"] == "billing", r["answers"]["dept"]

def test_decide_choice_probs():
    r = J.decide(J.MODEL_ID, "fatura ucret iade", Q_CHOICE)
    a = r["answers"]["dept"]
    assert abs(sum(a["probabilities"].values()) - 1.0) < 0.02, a
    assert 0.0 <= a["confidence"] <= 1.0

def test_decide_noul():
    q = {"c": {"type": "noul", "criteria": {"true": "yes confirm approve", "false": "no cancel reject"}}}
    a = J.decide(J.MODEL_ID, "yes please confirm", q)["answers"]["c"]
    assert 0.0 <= a["noul"] <= 1.0 and a["noul"] > 0.5, a
    assert 0.0 <= a["confidence"] <= 1.0

def test_decide_score():
    q = {"s": {"type": "score", "criteria": ["bad", "good", "excellent"]}}
    a = J.decide(J.MODEL_ID, "excellent service", q)["answers"]["s"]
    assert 0.0 <= a["score"] <= 2.0, a
    assert len(a["probabilities"]) == 3

def test_decide_bos():
    assert J.decide(J.MODEL_ID, "merhaba", {})["answers"] == {}
    try:
        J.decide(J.MODEL_ID, "merhaba", {"q": {"type": "choice", "criteria": {}}})
        assert False, "bos criteria hata vermeli"
    except ValueError:
        pass

def test_decide_tek_label():
    q = {"q": {"type": "choice", "instructions": "tek", "criteria": {"only": "tek secenek"}}}
    a = J.decide(J.MODEL_ID, "tek secenek metni", q)["answers"]["q"]
    assert a["choice"] == "only", a

def test_route_tr():
    assert J.route("fatura iade ve bir")["model"] == "mini-multilingual"

def test_route_en():
    assert J.route("please refund my invoice for march and bill")["model"] == "mini-english"

def test_route_devanagari():
    r = J.route("मुझसे मार्च में दो बार शुल्क लिया गया, कृपया वापस करें।")
    assert r["model"] == "mini-multilingual" and "non-Latin" in r["reason"], r

def test_route_cyrillic():
    r = J.route("Здравствуйте верните деньги")
    assert r["model"] == "mini-multilingual", r

def test_route_ms():
    r = J.route("fatura iade")
    assert isinstance(r["route_ms"], float) and r["route_ms"] < 100, r

def test_sfind_semantic():
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "billing.py"), "w", encoding="utf-8").write("invoice refund billing payment process")
        open(os.path.join(d, "astro.py"), "w", encoding="utf-8").write("galaxy telescope star orbit")
        r = M.tool_sfind({"query": "fatura iade", "root": d, "top_k": 5, "mode": "semantic"})
        assert r["scanned"] >= 2 and r["results"], r
        assert "grep_tahmin_ms" in r and r["grep_tahmin_ms"] >= 0, r
        assert r["results"][0]["path"].endswith("billing.py"), r["results"]

def test_sfind_exact():
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "a.txt"), "w", encoding="utf-8").write("satir bir\nUNIQUE_XYZ_123 burada\nsatir uc\n")
        r = M.tool_sfind({"query": "UNIQUE_XYZ_123", "root": d, "mode": "exact"})
        assert len(r["results"]) == 1, r
        assert any(s.get("line") == 2 and s.get("match", True) for s in r["results"][0]["snippet"]), r

def test_sfind_bos_query():
    with tempfile.TemporaryDirectory() as d:
        try:
            M.tool_sfind({"query": "   ", "root": d})
            assert False
        except ValueError as e:
            assert "query" in str(e).lower()

def test_sfind_kotu_root():
    with tempfile.TemporaryDirectory() as d:
        try:
            M.tool_sfind({"query": "x", "root": os.path.join(d, "yok")})
            assert False
        except ValueError as e:
            assert "root" in str(e).lower()

def test_sfind_regex():
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "a.txt"), "w", encoding="utf-8").write("hata_123 var\nnormal satir\n")
        r = M.tool_sfind({"query": "hata_\\d+", "root": d, "mode": "exact", "use_regex": True})
        assert len(r["results"]) == 1, r
        try:
            M.tool_sfind({"query": "([a-z", "root": d, "mode": "exact", "use_regex": True})
            assert False, "bozuk regex hata vermeli"
        except ValueError:
            pass

def _rpc(req):
    oi, oo = sys.stdin, sys.stdout
    sys.stdin, sys.stdout = io.StringIO(json.dumps(req, ensure_ascii=False) + "\n"), io.StringIO()
    try:
        M.serve()
        out = sys.stdout.getvalue()
    finally:
        sys.stdin, sys.stdout = oi, oo
    return json.loads(out.strip().splitlines()[0])

def test_mcp_initialize():
    r = _rpc({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    assert r["result"]["protocolVersion"] == "2024-11-05", r
    assert r["result"]["serverInfo"]["name"] == M.NAME

def test_mcp_tools_list():
    assert set(M.TOOLS) == {"decide", "sfind", "route"}
    r = _rpc({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    names = {t["name"] for t in r["result"]["tools"]}
    assert names == {"decide", "sfind", "route"}, r
    assert all("inputSchema" in t for t in r["result"]["tools"])

def test_mcp_bilinmeyen_arac():
    r = _rpc({"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "yok_boyle", "arguments": {}}})
    assert r["error"]["code"] == -32602, r

def test_mcp_bilinmeyen_metod():
    r = _rpc({"jsonrpc": "2.0", "id": 6, "method": "foo/bar"})
    assert r["error"]["code"] == -32601, r

def test_mcp_bozuk_json():
    oi, oo = sys.stdin, sys.stdout
    sys.stdin, sys.stdout = io.StringIO("bu json degil\n"), io.StringIO()
    try:
        M.serve()
        out = sys.stdout.getvalue()
    finally:
        sys.stdin, sys.stdout = oi, oo
    r = json.loads(out.strip().splitlines()[0])
    assert r["error"]["code"] == -32700, r

def test_expand_syn():
    assert "invoice" in M._expand(J.toks("fatura")) and "billing" in M._expand(J.toks("fatura"))
    assert M._expand(["xyz_qqq"]) == ["xyz_qqq"]

def test_hiz():
    t0 = time.perf_counter()
    J.decide(J.MODEL_ID, "fatura iade", Q_CHOICE)
    J.route("please refund invoice")
    assert (time.perf_counter() - t0) * 1000 < 100

TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    nf = 0
    for fn in TESTS:
        t0 = time.perf_counter()
        try:
            fn()
            print(f"PASS {fn.__name__} ({(time.perf_counter()-t0)*1000:.1f}ms)")
        except Exception as e:
            nf += 1
            print(f"FAIL {fn.__name__}: {type(e).__name__}: {e}")
    print(f"{len(TESTS)-nf}/{len(TESTS)} gecti")
    sys.exit(1 if nf else 0)
