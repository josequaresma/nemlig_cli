#!/usr/bin/env python3
"""
MCP server wrapping nemlig_cli — search, basket and order history for nemlig.com.

Credentials come from the NEMLIG_USER / NEMLIG_PASS environment variables
(see run_server.sh, which pulls the password from the macOS Keychain).
They are never logged or echoed.

Run: uv run python server.py  (stdio transport)
"""

import functools
import os
import threading
import time

import requests
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

import nemlig_cli
from nemlig_cli import AuthTokens, ProductNotFoundError


class _SilentSpinner:
    """Replaces nemlig_cli.Spinner: stdout is the MCP protocol channel."""

    def __init__(self, message: str = "Loading"):
        pass

    def start(self):
        pass

    def stop(self, final_message: str = None):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


nemlig_cli.Spinner = _SilentSpinner


# --- Polite rate limit: nemlig.com is an undocumented API ---------------------
# Patching Session.request throttles every outbound call, including the ones
# nemlig_cli functions make internally (page settings, login steps).

_MIN_REQUEST_INTERVAL = 0.5  # seconds -> max ~2 requests/sec
_rate_lock = threading.Lock()
_last_request_at = 0.0
_orig_session_request = requests.Session.request


def _throttled_request(self, *args, **kwargs):
    global _last_request_at
    with _rate_lock:
        wait = _MIN_REQUEST_INTERVAL - (time.monotonic() - _last_request_at)
        if wait > 0:
            time.sleep(wait)
        _last_request_at = time.monotonic()
    return _orig_session_request(self, *args, **kwargs)


requests.Session.request = _throttled_request


# --- Auth cache ----------------------------------------------------------------

_TOKEN_MAX_AGE = 270  # bearer tokens expire after ~5 min; refresh proactively
_auth_lock = threading.Lock()
_auth: AuthTokens | None = None
_auth_at = 0.0


def _get_auth(force: bool = False) -> AuthTokens:
    global _auth, _auth_at
    with _auth_lock:
        if force or _auth is None or time.monotonic() - _auth_at > _TOKEN_MAX_AGE:
            username = os.environ.get("NEMLIG_USER")
            password = os.environ.get("NEMLIG_PASS")
            if not username or not password:
                raise RuntimeError(
                    "NEMLIG_USER and NEMLIG_PASS environment variables must be set "
                    "(run_server.sh pulls the password from the macOS Keychain)."
                )
            _auth = nemlig_cli.login(username, password)
            _auth_at = time.monotonic()
        return _auth


def _call(fn, *args, **kwargs):
    """Call a nemlig_cli API function; on 401/403 re-authenticate once and retry."""
    try:
        return fn(_get_auth(), *args, **kwargs)
    except requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else None
        if status in (401, 403):
            return fn(_get_auth(force=True), *args, **kwargs)
        raise


def _safe(fn):
    """Translate API failures into clear ToolErrors instead of raw tracebacks."""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except ToolError:
            raise
        except ProductNotFoundError as e:
            raise ToolError(str(e)) from e
        except RuntimeError as e:
            raise ToolError(str(e)) from e
        except requests.HTTPError as e:
            status = e.response.status_code if e.response is not None else "?"
            url = e.request.url if e.request is not None else "?"
            raise ToolError(
                f"nemlig API returned HTTP {status} for {url} — "
                "the endpoint may have changed from what nemlig_api.md documents."
            ) from e
        except requests.RequestException as e:
            raise ToolError(f"Could not reach nemlig.com: {e}") from e
        except (KeyError, IndexError, TypeError) as e:
            raise ToolError(
                f"Unexpected nemlig API response shape ({type(e).__name__}: {e}) — "
                "the API may have changed from what nemlig_api.md documents."
            ) from e

    return wrapper


# --- Formatting (compact structured text, no raw JSON) --------------------------


def _fmt_product(p: dict) -> str:
    brand = f" ({p['Brand']})" if p.get("Brand") else ""
    unit = ""
    if p.get("UnitPriceCalc"):
        unit = f" ({p['UnitPriceCalc']:.2f} {p.get('UnitPriceLabel', '')})".rstrip()
    stock = "in stock" if p.get("Availability", {}).get("IsAvailableInStock") else "OUT OF STOCK"
    desc = f" — {p['Description']}" if p.get("Description") else ""
    return f"[{p.get('Id')}] {p.get('Name')}{brand} — {p.get('Price', 0):.2f} kr{unit}{desc} [{stock}]"


def _fmt_basket_line(ln: dict) -> str:
    brand = f" ({ln['Brand']})" if ln.get("Brand") else ""
    return (
        f"[{ln.get('Id')}] {ln.get('Name')}{brand} "
        f"x{ln.get('Quantity', 0)} @ {ln.get('ItemPrice', 0):.2f} kr = {ln.get('Price', 0):.2f} kr"
    )


def _fmt_basket(basket: dict) -> str:
    lines = basket.get("Lines", [])
    if not lines:
        return "Basket is empty."
    out = [f"Basket ({len(lines)} lines):"]
    out += [_fmt_basket_line(ln) for ln in lines]
    total = sum(ln.get("Price", 0) for ln in lines)
    out.append(f"Total: {total:.2f} kr")
    return "\n".join(out)


# --- MCP tools ------------------------------------------------------------------

mcp = FastMCP("nemlig")


@mcp.tool
@_safe
def search_products(query: str, limit: int = 10) -> str:
    """Search nemlig.com for products. Returns one line per product:
    [product_id] name (brand) — price (unit price) — description [stock status]."""
    products = _call(nemlig_cli.search_products, query, limit=limit)
    if not products:
        return f"No products found for '{query}'."
    return "\n".join(_fmt_product(p) for p in products)


@mcp.tool
@_safe
def get_product_details(product_id: str) -> str:
    """Get detailed information for a nemlig.com product by its product ID
    (description, price, unit price, contents, nutrition, availability)."""
    product = _call(nemlig_cli.get_product_details, product_id)
    return nemlig_cli.format_product_details(product)


@mcp.tool
@_safe
def view_basket() -> str:
    """View the current nemlig.com basket: one line per item with product ID,
    name, quantity, unit price and line total, plus the basket total."""
    return _fmt_basket(_call(nemlig_cli.get_basket))


@mcp.tool
@_safe
def add_to_basket(product_id: str, quantity: int = 1) -> str:
    """Add a product to the nemlig.com basket. MUTATES the family's live basket
    on nemlig.com — only call when the user has asked for this specific product.
    Returns the added line and the new basket total."""
    result = _call(nemlig_cli.add_to_basket, product_id, quantity)
    lines = result.get("Lines", [])
    total = sum(ln.get("Price", 0) for ln in lines)
    added = next((ln for ln in lines if ln.get("Id") == product_id), None)
    added_str = _fmt_basket_line(added) if added else f"Product {product_id} added."
    return f"Added: {added_str}\nBasket total: {total:.2f} kr ({len(lines)} lines)"


@mcp.tool
@_safe
def order_history(limit: int = 10, order_id: int | None = None) -> str:
    """List recent nemlig.com orders (order ID, date, total, status, delivery
    window). Pass order_id to get that order's full line items instead."""
    if order_id is not None:
        history = _call(
            nemlig_cli.get_order_history, skip=0, take=nemlig_cli.MAX_ORDER_HISTORY_LOOKUP
        )
        order = next((o for o in history.get("Orders", []) if o.get("Id") == order_id), None)
        if order is None:
            raise ToolError(
                f"Order {order_id} not found in the last "
                f"{nemlig_cli.MAX_ORDER_HISTORY_LOOKUP} orders."
            )
        details = _call(nemlig_cli.get_order_details, order_id)
        return nemlig_cli.format_order_details(order, details.get("Lines", []))

    history = _call(nemlig_cli.get_order_history, skip=0, take=limit)
    orders = history.get("Orders", [])
    if not orders:
        return "No orders found."
    out = [f"Order history ({len(orders)} shown, {history.get('NumberOfPages', 1)} pages total):"]
    out += [nemlig_cli.format_order_summary(o).strip() for o in orders]
    return "\n".join(out)


if __name__ == "__main__":
    mcp.run()
