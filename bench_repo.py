#!/usr/bin/env python3
"""bench_repo.py: sentetik monorepo benchmark (sadece stdlib).
Kullanim: python bench_repo.py --sizes 100 500 2000 --query "fatura iade"
"""
import argparse, os, random, shutil, sys, tempfile, time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mcp_server as M

MAX_FILES, BUDGET_MS, HEAD = M.MAX_FILES, M.BUDGET_MS, M.HEAD
SEED_TR = ["arama motoru", "önbellek performansı", "dosya sistemi", "eşzamanlı işlem", "bütçe aşımı algısı"]
SEED_EN = ["search index", "cache performance", "file system", "concurrent task", "budget exceeded"]
FILL_TR = "Bu dosya sentetik içerik içerir. Ölçüm ve değerlendirme için üretildi. "
FILL_EN = "This file holds synthetic content for benchmarking purposes. "

def gen_repo(base, n, depth, seed, plant_q, n_plant=10):
    rnd = random.Random(seed)
    exts = [".py", ".py", ".js", ".js", ".md", ".md"]
    planted = []
    base.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        d = base
        for _ in range(rnd.randint(1, depth)):
            d = d / f"dir{rnd.randint(0, 15)}"
        d.mkdir(parents=True, exist_ok=True)
        ext = rnd.choice(exts)
        p = d / f"f{i:05d}{ext}"
        tr = rnd.random() < 0.5
        head = rnd.choice(SEED_TR if tr else SEED_EN)
        fill = (FILL_TR if tr else FILL_EN) * rnd.randint(5, 40)
        body = f"{head}\n{fill}\n"
        if ext == ".py":
            body = f"# {head}\n" + body + f"\ndef fn_{i}():\n    return {i}\n"
        elif ext == ".js":
            body = f"// {head}\n" + body + f"\nfunction fn{i}(){{return {i};}}\n"
        else:
            body = f"# {head}\n\n" + body
        if i < n_plant:
            body += f"\n{plant_q} NEEDLE_{i} {plant_q}\n"
            planted.append(str(p.resolve()))
        p.write_text(body[:HEAD + 500], encoding="utf-8")
    return planted

def run_once(q, root, k, mode):
    t0 = time.perf_counter()
    res = M.tool_sfind({"query": q, "root": root, "top_k": k, "mode": mode})
    dt = (time.perf_counter() - t0) * 1000.0
    return dt, res

def eval_case(n, depth, seed, top_k, query):
    tmp = Path(tempfile.mkdtemp(prefix=f"bench_{n}_"))
    try:
        planted = gen_repo(tmp, n, depth, seed, query)
        pset = {os.path.basename(p) for p in planted}
        rows = []
        for label, mode in [("cold_semantic", "semantic"), ("warm_semantic", "semantic"), ("exact", "exact")]:
            dt, res = run_once(query, str(tmp), top_k, mode)
            paths = [r.get("path", "") for r in (res.get("results") or [])]
            hit = sum(1 for x in paths if os.path.basename(x) in pset or x in {os.path.relpath(p, str(tmp)).replace(os.sep, "/") for p in planted})
            rows.append((n, label, dt, len(paths), hit / max(1, len(planted)), dt > BUDGET_MS, n / max(dt, 1e-6)))
        return rows
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", nargs="+", type=int, default=[100, 500, 2000])
    ap.add_argument("--depth", type=int, default=4)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument("--query", type=str, default="bütçe aşımı")
    a = ap.parse_args()
    rows = []
    for n in a.sizes:
        rows += eval_case(n, a.depth, a.seed, a.top_k, a.query)
    print(f"{'N':>6} | {'cagri':<13} | {'sure_ms':>9} | {'bulunan':>7} | {'recall':>6} | {'asim':>4} | {'dosya/ms':>8}")
    print("-" * 70)
    for n, label, dt, found, rec, over, thr in rows:
        print(f"{n:6d} | {label:<13} | {dt:9.1f} | {found:7d} | {rec:6.2f} | {'EVET' if over else 'yok':>4} | {thr:8.2f}")
    print(f"\nBUTCE={BUDGET_MS}ms MAX_FILES={MAX_FILES} HEAD={HEAD} query={a.query!r}")

if __name__ == "__main__":
    main()
