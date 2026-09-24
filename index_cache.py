#!/usr/bin/env python3
"""mev sfind disk cache (.mevidx). stdlib-only. API: load/save/get/put."""
import json, os, zlib
NAME, VER, MAXH = ".mevidx", 1, 4000

def _ip(root):
    return os.path.join(root, NAME)

def _sig(h):
    return zlib.crc32(h.encode("utf-8", "ignore")) & 0xFFFFFFFF

def _rel(root, p):
    return os.path.relpath(p, root).replace(os.sep, "/")

def load(root):
    try:
        with open(_ip(root), "r", encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, dict) and isinstance(d.get("files"), dict):
            return d["files"]
    except (OSError, ValueError):
        pass
    return {}

def save(root, idx, live=None):
    if live is not None:
        for k in list(idx):
            if k not in live:
                del idx[k]
    tmp = _ip(root) + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"v": VER, "files": idx}, f, ensure_ascii=False)
        os.replace(tmp, _ip(root))
    except OSError:
        try:
            os.remove(tmp)
        except OSError:
            pass

def get(idx, root, ap):
    r = _rel(root, ap)
    e = idx.get(r)
    if not isinstance(e, dict):
        return None
    try:
        st = os.stat(ap)
    except OSError:
        idx.pop(r, None)
        return None
    if e.get("m") == st.st_mtime and e.get("s") == st.st_size:
        h = e.get("head", "")
        if isinstance(h, str):
            return h
    return None

def put(idx, root, ap, head):
    r = _rel(root, ap)
    try:
        st = os.stat(ap)
        m, s = st.st_mtime, st.st_size
    except OSError:
        return head
    head = (head or "")[:MAXH]
    idx[r] = {"m": m, "s": s, "sig": _sig(head), "head": head}
    return head
