# Nemlig.com CLI - Grocery Shopping
# Credentials are loaded from .env file automatically
# Create .env from .env.example: cp .env.example .env

set dotenv-load

# Show available commands
default:
    @just --list

# Start interactive mode
nemlig:
    uv run python nemlig_cli.py

# Search for products on nemlig.com
search QUERY:
    #!/usr/bin/env bash
    set -euo pipefail
    if [ -z "${NEMLIG_USER:-}" ] || [ -z "${NEMLIG_PASS:-}" ]; then
        echo "Error: Set NEMLIG_USER and NEMLIG_PASS environment variables"
        exit 1
    fi
    echo '> uv run python nemlig_cli.py -u "$NEMLIG_USER" -p "***" search "{{QUERY}}"'
    uv run python nemlig_cli.py -u "$NEMLIG_USER" -p "$NEMLIG_PASS" search "{{QUERY}}"

# Show detailed product information
details PRODUCT_ID:
    #!/usr/bin/env bash
    set -euo pipefail
    if [ -z "${NEMLIG_USER:-}" ] || [ -z "${NEMLIG_PASS:-}" ]; then
        echo "Error: Set NEMLIG_USER and NEMLIG_PASS environment variables"
        exit 1
    fi
    echo '> uv run python nemlig_cli.py -u "$NEMLIG_USER" -p "***" details "{{PRODUCT_ID}}"'
    uv run python nemlig_cli.py -u "$NEMLIG_USER" -p "$NEMLIG_PASS" details "{{PRODUCT_ID}}"

# Show current shopping basket
basket:
    #!/usr/bin/env bash
    set -euo pipefail
    if [ -z "${NEMLIG_USER:-}" ] || [ -z "${NEMLIG_PASS:-}" ]; then
        echo "Error: Set NEMLIG_USER and NEMLIG_PASS environment variables"
        exit 1
    fi
    echo '> uv run python nemlig_cli.py -u "$NEMLIG_USER" -p "***" basket'
    uv run python nemlig_cli.py -u "$NEMLIG_USER" -p "$NEMLIG_PASS" basket

# Add product to basket (use product ID from search results)
add PRODUCT_ID QUANTITY="1":
    #!/usr/bin/env bash
    set -euo pipefail
    if [ -z "${NEMLIG_USER:-}" ] || [ -z "${NEMLIG_PASS:-}" ]; then
        echo "Error: Set NEMLIG_USER and NEMLIG_PASS environment variables"
        exit 1
    fi
    echo '> uv run python nemlig_cli.py -u "$NEMLIG_USER" -p "***" add "{{PRODUCT_ID}}" --quantity "{{QUANTITY}}"'
    uv run python nemlig_cli.py -u "$NEMLIG_USER" -p "$NEMLIG_PASS" add "{{PRODUCT_ID}}" --quantity "{{QUANTITY}}"

# Show order history (optionally with ORDER_ID for details)
history ORDER_ID="":
    #!/usr/bin/env bash
    set -euo pipefail
    if [ -z "${NEMLIG_USER:-}" ] || [ -z "${NEMLIG_PASS:-}" ]; then
        echo "Error: Set NEMLIG_USER and NEMLIG_PASS environment variables"
        exit 1
    fi
    if [ -z "{{ORDER_ID}}" ]; then
        echo '> uv run python nemlig_cli.py -u "$NEMLIG_USER" -p "***" history'
        uv run python nemlig_cli.py -u "$NEMLIG_USER" -p "$NEMLIG_PASS" history
    else
        echo '> uv run python nemlig_cli.py -u "$NEMLIG_USER" -p "***" history "{{ORDER_ID}}"'
        uv run python nemlig_cli.py -u "$NEMLIG_USER" -p "$NEMLIG_PASS" history "{{ORDER_ID}}"
    fi

# Show grocery list with budget status
list:
    uv run python nemlig_cli.py list

# Add product to grocery list (accepts product ID or search term)
list-add QUERY QUANTITY="1":
    #!/usr/bin/env bash
    set -euo pipefail
    if [ -z "${NEMLIG_USER:-}" ] || [ -z "${NEMLIG_PASS:-}" ]; then
        echo "Error: Set NEMLIG_USER and NEMLIG_PASS environment variables"
        exit 1
    fi
    uv run python nemlig_cli.py -u "$NEMLIG_USER" -p "$NEMLIG_PASS" list add "{{QUERY}}" --quantity "{{QUANTITY}}"

# Remove product from grocery list
list-remove PRODUCT_ID:
    uv run python nemlig_cli.py list remove "{{PRODUCT_ID}}"

# Clear all items from grocery list
list-clear:
    uv run python nemlig_cli.py list clear

# Show or set grocery list budget
list-budget AMOUNT="":
    #!/usr/bin/env bash
    set -euo pipefail
    if [ -z "{{AMOUNT}}" ]; then
        uv run python nemlig_cli.py list budget
    else
        uv run python nemlig_cli.py list budget "{{AMOUNT}}"
    fi

# Sync grocery list to nemlig basket
list-sync:
    #!/usr/bin/env bash
    set -euo pipefail
    if [ -z "${NEMLIG_USER:-}" ] || [ -z "${NEMLIG_PASS:-}" ]; then
        echo "Error: Set NEMLIG_USER and NEMLIG_PASS environment variables"
        exit 1
    fi
    echo '> uv run python nemlig_cli.py -u "$NEMLIG_USER" -p "***" list sync'
    uv run python nemlig_cli.py -u "$NEMLIG_USER" -p "$NEMLIG_PASS" list sync

# 🤖 AI meal planner - build grocery list from recipes
plan:
    uv run python nemlig_cli.py plan

# 📋 Import recipes from Google Form/Sheet
import SPREADSHEET_ID="":
    #!/usr/bin/env bash
    set -euo pipefail
    if [ -z "{{SPREADSHEET_ID}}" ]; then
        uv run python nemlig_cli.py import
    else
        uv run python nemlig_cli.py import "{{SPREADSHEET_ID}}"
    fi

# Setup Google Sheets integration
import-setup:
    uv run python nemlig_cli.py import --setup

# 📷 Scan fridge with camera (barcode + AI detection)
scan:
    uv run python nemlig_cli.py scan

# 🧊 Show fridge inventory
fridge:
    uv run python nemlig_cli.py fridge

# 🧊 Clear fridge inventory
fridge-clear:
    uv run python nemlig_cli.py fridge clear

# 🤖 AI suggestions based on fridge contents
fridge-suggest:
    uv run python nemlig_cli.py fridge suggest
