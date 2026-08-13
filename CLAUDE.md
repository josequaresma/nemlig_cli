# CLAUDE.md

AI assistant guidance for this repository. See README.md for project overview and workflow documentation.

## Quick Commands

```bash
just search "cocio"     # Search products
just details 701025     # Product details
just basket             # View basket
just add 701025 2       # Add product
just history            # Order history
```

Requires `NEMLIG_USER` and `NEMLIG_PASS` environment variables.

Remove-from-basket, shopping lists and delivery slots have **no CLI subcommand** —
they exist as `nemlig_cli.py` functions and MCP tools only.

## This repo ships two separate MCP concerns

1. **`server.py`** — the product: a FastMCP server exposing `nemlig_cli` to AI assistants.
2. **Chrome DevTools MCP** (`.mcp.json` + the wrapper scripts) — the dev tool used to
   reverse-engineer the nemlig API.

Don't conflate them: `.mcp.json` in this repo configures the DevTools MCP, not `server.py`.

## The MCP server (`server.py`)

Thin layer over `nemlig_cli.py` — it imports the client and calls the same functions.
**New endpoints go in `nemlig_cli.py`; `server.py` only exposes them.**

Tools: `search_products`, `get_product_details`, `view_basket`, `order_history`,
`list_shopping_lists`, `list_delivery_slots` (read-only) — `add_to_basket`,
`delete_from_cart`, `add_shopping_list` (mutate the live basket) — `set_delivery_time`
(money-relevant; confirm date/window/price with the user first).

Conventions to preserve when editing `server.py`:

- **Never write to stdout** — it is the JSON-RPC channel. `nemlig_cli.Spinner` is
  replaced with a no-op for this reason; `print()` in a tool breaks the transport.
- **Wrap every tool in `@_safe`** and call the client through `_call` so failures become
  `ToolError` messages and 401/403 triggers one re-login + retry.
- **Keep the throttle** (`requests.Session.request` patched to ~2 req/s) — the nemlig API
  is undocumented and unowned.
- **Mutating tools must say so in the docstring** ("MUTATES the family's live basket") —
  that docstring is the only thing making the model ask first.
- **Return compact structured text, never raw JSON** — IDs in brackets, prices in kr.
  Tool output lands in a context window.

Credentials come from `NEMLIG_USER` / `NEMLIG_PASS`. `run_server.sh` (gitignored,
machine-specific) pulls the password from the macOS Keychain (service `nemlig`) and
execs the server. Never log or echo either value.

## Chrome DevTools MCP (API discovery)

Configured via `.mcp.json`. Use for API discovery and debugging.
`chrome-devtools-mcp-wrapper.sh` needs nix; `chrome-devtools-mcp-wrapper-macos.sh` is the
npx/system-Chrome counterpart for machines without it.

**Critical**: MCP calls return large payloads (>25KB). Always run MCP interactions from a sub-agent to avoid context bloat.

**Privacy**: Never record actual personal information (real names, addresses, phone numbers, order IDs). Replace with realistic placeholder values when documenting APIs (e.g., "Anders And", "Vesterbrogade 42", "+4512345678").

Pattern:
1. Sub-agent navigates, records network traffic, performs action
2. Sub-agent returns summary (endpoint, headers, body format)
3. Main context updates documentation or implements code

## Diagrams

Diagrams are stored as `.drawio.svg` files (SVG with embedded draw.io source). Keep them updated when architecture changes.

**To edit**: Open `.drawio.svg` directly in draw.io - the source is embedded.

**To create/update**:
```bash
# Create/edit in draw.io, save as .drawio file, then export:
drawio -x -f svg --embed-diagram -o diagram.drawio.svg diagram.drawio
rm diagram.drawio  # Keep only the .svg
```

Current diagrams:
- `arch_api.drawio.svg` - API architecture (endpoints, auth flow)
- `mcp-workflow.drawio.svg` - MCP workflow for API discovery

## Project Commands

Custom slash commands for this project. **Run both in sub-agents in parallel before every commit.**

- `/drawio-updater` - Audit and update `.drawio.svg` diagrams
- `/privacy-checker` - Scan files for personal data leaks

## Files

- `nemlig_cli.py` - Single-file Python client
- `server.py` - FastMCP server wrapping the client
- `nemlig_api.md` - API documentation (source of truth for endpoints)
- `justfile` - Command shortcuts

## Fork

Fork of `eisbaw/nemlig_cli` (`upstream` remote). Keep fork-specific additions
(`server.py`, the extra endpoints) easy to rebase: additive, and grouped where possible.
