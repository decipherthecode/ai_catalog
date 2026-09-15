# AI Coding Assistant Catalog

Scan your local Claude configuration for Skills, MCP servers, Agents, and
Plugins, then browse and search everything in a single-page web app.

- Zero dependencies — Python 3 standard library only.
- Local-only — binds to `localhost`, reads your config, sends nothing out.
- Dual mode — run it as a standalone script or as a Claude Code plugin.

## Install

You need Python 3.8+ (`python3 --version`). Clone the repository:

```bash
git clone https://github.com/decipherthecode/ai-catalog.git
cd ai-catalog
```

### Optional: install to your PATH

Copy the script to a local bin directory as an executable named `ai-catalog`:

```bash
python3 ai_catalog.py --install
```

This installs to `~/.local/bin/ai-catalog` by default (pass a directory to
override, e.g. `--install ~/bin`). If that directory is not on your `PATH`,
the command prints the `export` line to add. Once it is on your `PATH` you can
run `ai-catalog` from anywhere.

## Run

From the cloned directory:

```bash
python3 ai_catalog.py
```

This scans your config, starts a server on `http://localhost:8765`, and opens
it in your browser.

If you installed it to your PATH:

```bash
ai-catalog
```

### Options

| Flag | Description |
|------|-------------|
| `--port PORT` | Serve on a different port (default `8765`). |
| `--no-open` | Do not open a browser automatically. |
| `--install [DIR]` | Copy the script to `DIR` (default `~/.local/bin`) as executable `ai-catalog`, then exit. |

Press `Ctrl-C` to stop the server.

## What it scans

| Category | Source |
|----------|--------|
| Agents | `~/.claude/agents/` and installed plugins |
| Skills | `~/.claude/skills/` and installed plugins |
| MCP Servers | `~/.claude.json` |
| Plugins | `~/.claude/plugins/installed_plugins.json` |

## License

MIT
