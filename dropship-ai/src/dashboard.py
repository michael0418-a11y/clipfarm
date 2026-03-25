"""
Dropship AI Dashboard — CLI dashboard showing store health,
orders, revenue, and AI agent status.
"""
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "config", ".env"))

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.text import Text
except ImportError:
    print("Install rich: pip install rich")
    sys.exit(1)

from shopify_client import get_products, get_orders

console = Console()


def show_dashboard():
    """Display the main operations dashboard."""
    console.clear()
    console.print(Panel.fit(
        "[bold cyan]DROPSHIP AI[/bold cyan] — Automated Operations Dashboard",
        border_style="cyan",
    ))
    console.print()

    # ── Orders summary ────────────────────────────────────────────
    try:
        orders = get_orders(status="any", limit=50)
        revenue = sum(float(o.get("total_price", 0)) for o in orders)
        unfulfilled = sum(1 for o in orders if o.get("fulfillment_status") != "fulfilled")

        order_table = Table(title="Recent Orders", border_style="green")
        order_table.add_column("Order #", style="bold")
        order_table.add_column("Customer")
        order_table.add_column("Total")
        order_table.add_column("Status")
        order_table.add_column("Date")

        for order in orders[:10]:
            status_color = "green" if order.get("fulfillment_status") == "fulfilled" else "yellow"
            order_table.add_row(
                f"#{order.get('order_number', '?')}",
                order.get("email", "—"),
                f"${order.get('total_price', '0')}",
                f"[{status_color}]{order.get('fulfillment_status', 'unfulfilled')}[/{status_color}]",
                order.get("created_at", "")[:10],
            )

        console.print(order_table)
        console.print(f"\n  Total revenue (last 50 orders): [bold green]${revenue:,.2f}[/bold green]")
        console.print(f"  Unfulfilled orders: [bold yellow]{unfulfilled}[/bold yellow]")

    except Exception as e:
        console.print(f"[yellow]Orders unavailable — configure Shopify API credentials in config/.env[/yellow]")
        console.print(f"  Error: {e}\n")

    # ── Products summary ──────────────────────────────────────────
    try:
        products = get_products(limit=10)
        prod_table = Table(title="\nProduct Catalog (Top 10)", border_style="blue")
        prod_table.add_column("Title", style="bold")
        prod_table.add_column("Price")
        prod_table.add_column("Inventory")
        prod_table.add_column("Status")

        for p in products:
            variant = p["variants"][0] if p.get("variants") else {}
            prod_table.add_row(
                p["title"][:40],
                f"${variant.get('price', '?')}",
                str(variant.get("inventory_quantity", "?")),
                p.get("status", "?"),
            )

        console.print(prod_table)

    except Exception:
        console.print("[yellow]Products unavailable — configure Shopify API credentials[/yellow]\n")

    # ── AI Agents status ──────────────────────────────────────────
    agents_table = Table(title="\nAI Agents", border_style="magenta")
    agents_table.add_column("Agent", style="bold")
    agents_table.add_column("Status")
    agents_table.add_column("Last Run")

    agents = [
        ("Description Rewriter", "Ready", "—"),
        ("Pricing Optimizer", "Ready", "—"),
        ("Trend Monitor", "Ready", "—"),
        ("Customer Service Bot", "Ready", "—"),
        ("Brand Bible Generator", "Ready", "—"),
    ]
    for name, status, last_run in agents:
        agents_table.add_row(name, f"[green]{status}[/green]", last_run)

    console.print(agents_table)
    console.print(f"\n  [dim]{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]")


if __name__ == "__main__":
    show_dashboard()
