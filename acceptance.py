#!/usr/bin/env python3
"""acceptance.py: 300 dosyalik sahte monorepo kabul testi (stdlib-only).
Kullanim: python acceptance.py
Beklenen: 5 sorguda first-rank isabet (exit 0), degilse exit 1."""
import os, random, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
from pathlib import Path
import mcp_server as M

random.seed(42)
root = Path(tempfile.mkdtemp(prefix="monorepo-demo-"))
pinned = {
    "services/payments/refund_service.py": "# odeme iade akisi: iade onayi ve muhasebe fisi olusturur",
    "services/payments/charge.py": "def charge_credit_card(card, tutar): # kredi karti tahsilat",
    "services/payments/invoice_generator.py": "# fatura PDF olusturma backend servisi",
    "services/auth/token_refresh.py": "# kullanici giris token yenileme ve oturum uzatma",
    "services/auth/rate_limit.py": "# login rate limiting: 5 deneme sonrasi bloklama",
    "web/frontend/components/CargoTrack.tsx": "// kargo takip ekrani bileseni, kurye durumu gosterir",
    "infra/db/migration_runner.sh": "# veritabani migration calistirici, hata logu buraya",
    "docs/odeme-iade.md": "# Odeme iade politikasi ve muhasebe kurallari",
}
counts = {"services/payments": 80, "services/auth": 70, "web/frontend": 70,
          "infra": 40, "docs": 40}
pools = {
    "services/payments": (["refund_worker", "pos_callback", "invoice_batch", "taksit", "komisyon"], ".py",
                          "# {n} odeme servisi - tahsilat/iade akisini yonetir / handles {n} payment flow"),
    "services/auth": (["session", "oauth", "sifre_sifirlama", "mfa", "oturum"], ".py",
                      "# {n} auth servisi - giris ve yetki kontrolu / auth flow for {n}"),
    "web/frontend": (["Sepet", "OdemeIade", "FaturaPDF", "GirisFormu", "SiparisListe"], ".tsx",
                     "// {n} frontend bileseni - kullanici ekrani / renders {n} view"),
    "infra": (["deploy", "k8s_manifest", "ci_pipe", "terraform_mod", "yedekleme"], ".yaml",
              "# {n} altyapi configi - dagitim ve izleme / infra config {n}"),
    "docs": (["runbook", "auth-mimari", "kurulum", "sss", "sozlesme"], ".md",
             "# {n} dokumani - kurulum ve isletim notlari / doc for {n}"),
}
for d, n in counts.items():
    (Path(root) / d / "components").mkdir(parents=True, exist_ok=True)
    (Path(root) / d / "db").mkdir(parents=True, exist_ok=True)
    names, ext, tpl = pools[d]
    for i in range(n):
        name = f"{names[i % len(names)]}_{i:02d}{ext}"
        p = Path(root) / d / name
        if d == "web/frontend" and i % 2 == 0:
            p = Path(root) / d / f"components/{names[i % len(names)]}_{i:02d}{ext}"
        p.write_text(tpl.format(n=p.stem) + "\n", encoding="utf-8")
for rel, content in pinned.items():
    p = Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content + "\n", encoding="utf-8")
total = sum(1 for _ in Path(root).rglob("*") if _.is_file())
print(f"repo: {root} dosyalar: {total}")

queries = [
    ("odeme iade akisi nerede?", "semantic", "services/payments/refund_service.py"),
    ("kullanici giris token yenileme nasil yapiliyor?", "semantic", "services/auth/token_refresh.py"),
    ("kargo takip ekrani hangi componentte?", "semantic", "web/frontend/components/CargoTrack.tsx"),
    ("where is rate limiting implemented for login?", "semantic", "services/auth/rate_limit.py"),
    ("def charge_credit_card", "exact", "services/payments/charge.py"),
]
hit = 0
for q, mode, exp in queries:
    r = M.tool_sfind({"query": q, "root": str(root), "top_k": 5, "mode": mode})
    top1 = r["results"][0]["path"].replace("\\", "/") if r["results"] else "(bos)"
    ok = top1 == exp
    hit += ok
    c = r["results"][0].get("confidence", "-") if r["results"] else "-"
    print(f"{'HIT ' if ok else 'MISS'} {q[:42]:42} -> {top1} conf={c} ms={r['ms']}")
print(f"{hit}/{len(queries)} first-rank isabet")
import shutil
shutil.rmtree(root, ignore_errors=True)
sys.exit(0 if hit == len(queries) else 1)
