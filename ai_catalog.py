#!/usr/bin/env python3
"""AI coding-assistant capability catalog.

Scans the local Claude config on startup for Skills, MCP servers, Agents, and
Plugins, then serves a single-page web app to browse/search them.

Usage:  python3 ai_catalog.py [--port 8765] [--no-open]
"""
import argparse
import json
import os
import re
import shutil
import stat
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOME = os.path.expanduser("~")
CLAUDE = os.path.join(HOME, ".claude")
DEFAULT_INSTALL_DIR = os.path.join(HOME, ".local", "bin")


def install(dest_dir):
    """Copy this script to a local bin dir as executable `ai-catalog`."""
    src = os.path.abspath(__file__)
    dest_dir = os.path.expanduser(dest_dir)
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, "ai-catalog")
    if os.path.abspath(dest) == src:
        raise SystemExit("Source and destination are the same file.")
    shutil.copyfile(src, dest)
    mode = os.stat(dest).st_mode
    os.chmod(dest, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"Installed to {dest}")
    if dest_dir not in os.environ.get("PATH", "").split(os.pathsep):
        print(f"Add to PATH:  export PATH=\"{dest_dir}:$PATH\"")
    return dest


def _frontmatter(path):
    """Return (name, description) from a Markdown YAML frontmatter block."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read(8000)
    except OSError:
        return None, None
    m = re.match(r"\s*---\s*\n(.*?)\n---", text, re.S)
    block = m.group(1) if m else text
    name = desc = None
    # description can be quoted and span until the next `key:` line
    # folded/literal block scalar: `description: >` then indented lines
    bm = re.search(r"^description:\s*[>|][-+]?\s*\n((?:[ \t]+.*\n?)+)", block, re.M)
    if bm:
        desc = re.sub(r"\s+", " ", bm.group(1)).strip()
    else:
        dm = re.search(r'^description:\s*(?:"(.*?)"|(.+?))\s*$', block, re.M | re.S)
        if dm:
            desc = (dm.group(1) or dm.group(2) or "").strip()
            desc = re.sub(r"\s+", " ", desc)
            # stop a greedy unquoted match at the next frontmatter key
            desc = re.split(r"\s+[a-z_]+:\s", desc)[0].strip()
    nm = re.search(r"^name:\s*(.+?)\s*$", block, re.M)
    if nm:
        name = nm.group(1).strip().strip('"')
    return name, desc


def scan_skills():
    out, seen = [], set()
    roots = [
        (os.path.join(CLAUDE, "skills"), "user"),
        (os.path.join(CLAUDE, "plugins"), "plugin"),
    ]
    for root, source in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, _dirs, files in os.walk(root):
            if "SKILL.md" not in files:
                continue
            path = os.path.join(dirpath, "SKILL.md")
            name, desc = _frontmatter(path)
            name = name or os.path.basename(dirpath)
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append({"name": name, "description": desc or "", "source": source})
    return sorted(out, key=lambda x: x["name"].lower())


def scan_agents():
    out, seen = [], set()
    roots = [os.path.join(CLAUDE, "agents"), os.path.join(CLAUDE, "plugins")]
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, _dirs, files in os.walk(root):
            if os.path.basename(dirpath) != "agents":
                continue
            for f in files:
                if not f.endswith(".md"):
                    continue
                name, desc = _frontmatter(os.path.join(dirpath, f))
                name = name or f[:-3]
                key = name.lower()
                if key in seen:
                    continue
                seen.add(key)
                out.append({"name": name, "description": desc or ""})
    return sorted(out, key=lambda x: x["name"].lower())


def scan_plugins():
    path = os.path.join(CLAUDE, "plugins", "installed_plugins.json")
    out = []
    try:
        data = json.load(open(path))
    except (OSError, ValueError):
        return out
    for key, entries in (data.get("plugins") or {}).items():
        name, _, market = key.partition("@")
        inst = entries[0] if isinstance(entries, list) and entries else {}
        out.append({
            "name": name,
            "description": f"marketplace: {market or 'unknown'}"
            + (f" · v{inst['version']}" if inst.get("version") else ""),
            "scope": inst.get("scope", ""),
        })
    return sorted(out, key=lambda x: x["name"].lower())


def scan_mcp():
    out = []
    try:
        data = json.load(open(os.path.join(HOME, ".claude.json")))
    except (OSError, ValueError):
        return out
    for name, cfg in (data.get("mcpServers") or {}).items():
        if not isinstance(cfg, dict):
            continue
        if cfg.get("command"):
            desc = "stdio: " + cfg["command"]
        elif cfg.get("url"):
            desc = f"{cfg.get('type', 'remote')}: {cfg['url']}"
        else:
            desc = cfg.get("type", "configured")
        out.append({"name": name, "description": desc})
    return sorted(out, key=lambda x: x["name"].lower())


def build_catalog():
    return {
        "agents": scan_agents(),
        "skills": scan_skills(),
        "mcp": scan_mcp(),
        "plugins": scan_plugins(),
    }


PAGE = """<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>AI Assistant Catalog</title><style>
*{box-sizing:border-box}body{margin:0;font:15px/1.5 system-ui,sans-serif;
background:#0f1115;color:#e6e6e6}
header{padding:24px 20px 12px;border-bottom:1px solid #23262d}
h1{margin:0 0 4px;font-size:22px}.sub{color:#8b93a1;font-size:13px}
.bar{position:sticky;top:0;background:#0f1115;padding:14px 20px;
border-bottom:1px solid #23262d;z-index:5}
input{width:100%;padding:10px 12px;border-radius:8px;border:1px solid #2c313a;
background:#171a20;color:#e6e6e6;font-size:15px}
.tabs{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}
.tab{padding:6px 12px;border-radius:20px;border:1px solid #2c313a;background:#171a20;
color:#c7ccd4;cursor:pointer;font-size:13px}
.tab.on{background:#3b82f6;border-color:#3b82f6;color:#fff}
.grid{display:grid;gap:12px;padding:20px;
grid-template-columns:repeat(auto-fill,minmax(300px,1fr))}
.card{background:#171a20;border:1px solid #23262d;border-radius:10px;padding:14px}
.card h3{margin:0 0 6px;font-size:15px;word-break:break-word}
.card p{margin:0;color:#9aa2b1;font-size:13px}
.pill{display:inline-block;font-size:10px;text-transform:uppercase;letter-spacing:.5px;
padding:2px 7px;border-radius:6px;margin-bottom:8px;font-weight:600}
.t-agents{background:#7c3aed33;color:#c4b5fd}.t-skills{background:#059f6933;color:#6ee7b7}
.t-mcp{background:#2563eb33;color:#93c5fd}.t-plugins{background:#d9770633;color:#fcd34d}
.empty{padding:40px;text-align:center;color:#8b93a1}
</style></head><body>
<header><h1>AI Coding Assistant Catalog</h1>
<div class=sub id=meta>scanning…</div></header>
<div class=bar><input id=q placeholder="Search name or description…" autofocus>
<div class=tabs id=tabs></div></div>
<div class=grid id=grid></div>
<script>
let DATA={},cur="all",q="";
const TABS=[["all","All"],["agents","Agents"],["skills","Skills"],
["mcp","MCP Servers"],["plugins","Plugins"]];
function items(){let a=[];for(const k of["agents","skills","mcp","plugins"])
(DATA[k]||[]).forEach(x=>a.push({...x,_t:k}));return a;}
function render(){
const all=items();
document.getElementById("meta").textContent=
`${all.length} items · ${(DATA.agents||[]).length} agents · `+
`${(DATA.skills||[]).length} skills · ${(DATA.mcp||[]).length} MCP · `+
`${(DATA.plugins||[]).length} plugins`;
const tb=document.getElementById("tabs");tb.innerHTML="";
for(const[k,label]of TABS){const n=k=="all"?all.length:(DATA[k]||[]).length;
const b=document.createElement("div");b.className="tab"+(cur==k?" on":"");
b.textContent=`${label} (${n})`;b.onclick=()=>{cur=k;render();};tb.appendChild(b);}
let rows=all.filter(x=>cur=="all"||x._t==cur);
if(q){const s=q.toLowerCase();rows=rows.filter(x=>
(x.name||"").toLowerCase().includes(s)||
(x.description||"").toLowerCase().includes(s));}
const g=document.getElementById("grid");
if(!rows.length){g.innerHTML='<div class=empty>No matches.</div>';return;}
g.innerHTML=rows.map(x=>`<div class=card>
<span class="pill t-${x._t}">${x._t=="mcp"?"MCP":x._t.slice(0,-1)}</span>
<h3>${esc(x.name)}</h3><p>${esc(x.description||"—")}</p></div>`).join("");
}
function esc(s){return(s||"").replace(/[&<>]/g,c=>
({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));}
document.getElementById("q").addEventListener("input",e=>{q=e.target.value;render();});
fetch("/api/data").then(r=>r.json()).then(d=>{DATA=d;render();});
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, body, ctype):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/api/data"):
            self._send(json.dumps(build_catalog()).encode(), "application/json")
        else:
            self._send(PAGE.encode(), "text/html; charset=utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-open", action="store_true")
    ap.add_argument("--install", nargs="?", const=DEFAULT_INSTALL_DIR,
                    metavar="DIR",
                    help=f"copy this script to DIR (default {DEFAULT_INSTALL_DIR}) "
                         "as executable `ai-catalog`, then exit")
    args = ap.parse_args()

    if args.install:
        install(args.install)
        return

    cat = build_catalog()
    print("Scanned {agents} agents, {skills} skills, {mcp} MCP servers, "
          "{plugins} plugins.".format(**{k: len(v) for k, v in cat.items()}))
    url = f"http://localhost:{args.port}"
    print(f"Serving {url}  (Ctrl-C to stop)")
    if not args.no_open:
        webbrowser.open(url)
    try:
        ThreadingHTTPServer(("localhost", args.port), Handler).serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
