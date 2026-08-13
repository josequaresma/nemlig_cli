# Nemlig.com CLI + MCP server

Command-line interface **and MCP server** for [nemlig.com](https://www.nemlig.com) Danish online grocery store. Single-file Python implementation using `requests` for HTTP and `argparse` for CLI parsing, plus a [FastMCP](https://github.com/jlowin/fastmcp) server (`server.py`) that exposes the same client to AI assistants.

Fork of [eisbaw/nemlig_cli](https://github.com/eisbaw/nemlig_cli), adding the MCP server and several API endpoints (see [Additions in this fork](#additions-in-this-fork)).

## Features

- Product search and details
- Shopping basket management (view, add, remove items)
- Saved shopping lists (favoritter) — list them, add a whole list to the basket
- Delivery time slots — list available slots, reserve one
- Order history viewing
- MCP server exposing all of the above as tools

### Additions in this fork

| Addition | `nemlig_cli.py` functions | CLI | MCP |
|---|---|---|---|
| MCP server (`server.py`) | — | — | ✅ |
| Remove from basket | `remove_from_basket` | — | `delete_from_cart` |
| Shopping lists | `get_shopping_lists`, `add_shopping_list_to_basket` | — | `list_shopping_lists`, `add_shopping_list` |
| Delivery slots | `get_delivery_days`, `update_delivery_time` | — | `list_delivery_slots`, `set_delivery_time` |

The new endpoints are library + MCP only — they have no `argparse` subcommand yet. Call them from Python, or through the MCP server.

## Requirements

- Python >= 3.11
- [uv](https://github.com/astral-sh/uv) package manager
- Credentials for nemlig.com account

```bash
# Set credentials as environment variables
export NEMLIG_USER="your@email.com"
export NEMLIG_PASS="yourpassword"
```

### Optional features

Search, basket, shopping lists, delivery slots, order history and the MCP server
need nothing beyond the core dependencies (`requests`, `fastmcp`). The remaining
features pull in heavier dependencies and are installed as extras:

| Extra | Enables | Commands |
|-------|---------|----------|
| `ai` | AI meal planning | `plan` |
| `sheets` | Google Forms/Sheets recipe import | `import` |
| `scanner` | Barcode and produce scanning | `scan`, `fridge` |
| `all` | Everything above | |

```bash
uv sync --extra all          # or: --extra ai --extra scanner
```

## Usage

All commands are available via the justfile:

```bash
just search "cocio"              # Search products
just details 701025              # Product details
just basket                      # View basket
just add 701025 2                # Add product (quantity optional)
just history                     # Order history
just history 12345678            # Order details
```

Direct execution:

```bash
uv run python nemlig_cli.py -u "$NEMLIG_USER" -p "$NEMLIG_PASS" search "milk"
```

## MCP server

`server.py` wraps the client's core functions as an MCP server (stdio transport, [FastMCP](https://github.com/jlowin/fastmcp)), so an AI assistant can search, manage the basket and book delivery slots directly.

```bash
NEMLIG_USER=... NEMLIG_PASS=... uv run python server.py
```

`fastmcp` is a core dependency (not an extra), so a plain `uv sync` is enough to run the server.

### Tools

| Tool | Read/write | Description |
|---|---|---|
| `search_products(query, limit=10)` | read | One line per product: `[id] name (brand) — price (unit price) — description [stock]` |
| `get_product_details(product_id)` | read | Description, price, unit price, contents, nutrition, availability |
| `view_basket()` | read | One line per basket item plus the total |
| `order_history(limit=10, order_id=None)` | read | Recent orders, or one order's line items |
| `list_shopping_lists()` | read | Saved lists: ID, name, product count, total |
| `list_delivery_slots(days=8)` | read | Bookable slots per day: ID, window, price; marks the selected slot and flex (`uden opsyn`) slots |
| `add_to_basket(product_id, quantity=1)` | **write** | Adds to the live basket |
| `delete_from_cart(product_id)` | **write** | Removes a product line from the live basket |
| `add_shopping_list(list_name_or_id)` | **write** | Adds every product from a saved list (name is case-insensitive) |
| `set_delivery_time(timeslot_id)` | **money** | Reserves a delivery slot for ~20 min; final at checkout — confirm date/window/price with the user first |

Write tools operate on the account's real basket. Their docstrings say so, so the model asks before mutating.

### Behaviour worth knowing

- **Auth caching** — logs in once and reuses the bearer token for ~4.5 min (tokens expire around 5 min); a 401/403 triggers one re-login and retry.
- **Rate limiting** — `requests.Session.request` is patched to a max of ~2 requests/sec, throttling every call including the internal login steps. nemlig.com's API is undocumented; be polite.
- **Silent spinner** — `nemlig_cli.Spinner` is replaced with a no-op so nothing animated can reach stdout, which is the JSON-RPC channel under stdio transport.
- **Errors** — API failures become clear `ToolError` messages ("the endpoint may have changed from what nemlig_api.md documents") instead of raw tracebacks.
- **Output** — compact structured text with IDs in brackets, never raw JSON, to keep responses small in the model's context.

### Registering with an MCP client

Credentials must reach the server as environment variables without landing in a config file. The pattern used here is a small launcher script that pulls the password from the OS keychain (macOS example, gitignored as machine-specific):

```sh
#!/bin/sh
# run_server.sh
export NEMLIG_USER="your@email.com"
NEMLIG_PASS="$(security find-generic-password -s nemlig -w)" || exit 1
export NEMLIG_PASS
exec uv run --directory /path/to/nemlig_cli python server.py
```

Store the password once with:

```bash
security add-generic-password -a your@email.com -s nemlig -w
```

Then point the client at the launcher — e.g. in a consuming project's `.mcp.json`:

```json
{
  "mcpServers": {
    "nemlig": {
      "type": "stdio",
      "command": "/path/to/nemlig_cli/run_server.sh",
      "args": [],
      "env": {}
    }
  }
}
```

Note that this repo's own `.mcp.json` configures the **Chrome DevTools** MCP used for API discovery (see the development workflow below) — not this server.

## Architecture

**Single file design**: All client logic in `nemlig_cli.py` - a straightforward requests-based client. `server.py` is a thin MCP layer on top: it imports `nemlig_cli` and calls the same functions, adding auth caching, throttling and output formatting. New endpoints go in `nemlig_cli.py`; `server.py` only exposes them.

![API Architecture](arch_api.drawio.svg)

**Authentication**: 3-step flow (XSRF token -> Bearer token -> Login). Returns `AuthTokens` dataclass passed to all API functions.

**Dual API endpoints**: Main site API (`nemlig.com/webapi/*`) for auth and basket operations; separate search gateway (`webapi.prod.knl.nemlig.it`) for product search.

**Endpoints used by the fork's additions**:

| Operation | Endpoint |
|---|---|
| Remove from basket | `POST /webapi/basket/AddToBasket` with `quantity: 0`, `AffectPartialQuantity: true` (no dedicated delete endpoint exists) |
| Shopping lists | `GET /webapi/ShoppingList/GetShoppingLists` |
| Add list to basket | `POST /webapi/basket/addShoppingListToBasket` |
| Delivery days/slots | `GET /webapi/v2/Delivery/GetDeliveryDays` |
| Reserve slot | `POST /webapi/Delivery/TryUpdateDeliveryTime?timeslotId=…` (empty body) |

Slot `Availability` is `0` when bookable; `Type` is `0` for a personal delivery and `1` for flex/`uden opsyn` (unattended).

See `nemlig_api.md` for complete API documentation including request/response schemas.

---

## Development Workflow: API Discovery with Chrome DevTools MCP

This project was built by having Claude Code control a real browser to observe and document the nemlig.com API. The technique generalizes to any web application where you need to reverse-engineer an undocumented API.

### Overview

The workflow enables an AI assistant to control a real browser, observe network traffic, and document API behavior - then implement a client based on the documented findings.

![MCP Workflow](mcp-workflow.drawio.svg)

### Self-Contained MCP Setup

The Chrome DevTools MCP integration is fully self-contained:

- `.mcp.json` - MCP server configuration pointing to the wrapper script
- `chrome-devtools-mcp-wrapper.sh` - Nix-shell wrapper ensuring reproducible environment with:
  - Pinned nixpkgs (nixos-25.05) for reproducibility
  - Node.js 22 and Chromium from nix
  - Project-local Chrome profile (`.chrome-profile/`) to avoid tainting global settings
  - Pinned `chrome-devtools-mcp` version (0.10.1)

No global installation required - the wrapper script handles everything.

On machines without nix, `chrome-devtools-mcp-wrapper-macos.sh` is the drop-in counterpart: same pinned `chrome-devtools-mcp` version and same project-local profile, but run via `npx` against the system Google Chrome.

### API Discovery Process

**Phase 1: Network Traffic Capture**

Human operator directs Claude to:

1. **Open target page** with network recording enabled
2. **Perform the operation** being documented (login, search, add to cart, etc.)
3. **List network requests** to see all HTTP traffic
4. **Get request details** for interesting endpoints (headers, body, response)

Example session:
```
Human: Open nemlig.com and enable network recording. Then login with test credentials and show me the network traffic.

Claude: [Uses Chrome DevTools MCP to navigate, perform login, capture traffic]
        [Lists network requests, identifies auth flow]
        [Documents the 3-step auth: AntiForgery -> Token -> login]
```

**Phase 2: Documentation**

Claude analyzes captured traffic and documents:
- Request URLs, methods, headers
- Request/response body structure
- Authentication requirements
- Parameter meanings

This builds up `nemlig_api.md` incrementally.

**Phase 3: Implementation**

Based on the documented API:
1. Claude implements Python functions matching documented endpoints
2. Human tests implementation against real site
3. Debug issues using Chrome DevTools MCP as grounding (compare browser vs client behavior)

### Context Management

**Important**: MCP tool calls return large responses (>25KB for page snapshots/network dumps). To manage context window size:

- Run all MCP interactions from a **sub-agent** (Task tool with explore or general-purpose agent)
- Sub-agent summarizes findings and returns only relevant info
- Main conversation stays focused on implementation

Example pattern:
```
Human: Document the basket API

Claude: [Spawns sub-agent to handle MCP interactions]

Sub-agent: [Opens page, enables recording, adds item to basket]
           [Captures AddToBasket request/response]
           [Returns summary: endpoint, headers, body format, response structure]

Claude: [Updates nemlig_api.md with documented endpoint]
```

### Debugging with Browser Grounding

When the Python client behaves differently than expected:

1. Perform same operation in browser via MCP
2. Compare exact request headers/body
3. Identify missing headers, wrong parameter format, etc.
4. Fix client implementation

This provides a reliable reference for expected API behavior.

### File Structure

```
nemlig-cli/
├── .mcp.json                             # Chrome DevTools MCP config (API discovery)
├── chrome-devtools-mcp-wrapper.sh        # Nix-shell wrapper for the DevTools MCP
├── chrome-devtools-mcp-wrapper-macos.sh  # macOS/npx counterpart (system Chrome)
├── .chrome-profile/                      # Local browser profile (gitignored)
├── arch_api.drawio.svg                   # API architecture diagram
├── mcp-workflow.drawio.svg               # MCP workflow diagram
├── nemlig_api.md                         # API documentation (built via workflow)
├── nemlig_cli.py                         # Python client implementation
├── server.py                             # FastMCP server wrapping the client
├── run_server.sh                         # Launcher w/ keychain credentials (gitignored)
├── .env.example                          # Credential template for the CLI/justfile
├── justfile                              # Command shortcuts
├── pyproject.toml                        # Python project config
└── CLAUDE.md                             # AI assistant instructions
```

## License

MIT
