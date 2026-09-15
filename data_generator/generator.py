"""
generator.py — CLI entry point for the Commerce360 synthetic data generator.

This module wires the CLI arguments to the per-entity generators.
The actual generation logic lives in data_generator/entities/.

Usage:
    python -m data_generator.generator --help
    python -m data_generator.generator --tier small --seed 42 --output-dir data/generated/small --format json
"""

import sys
import click
from pathlib import Path

from .entities.customers import CustomerGenerator
from .entities.products import ProductGenerator
from .entities.campaigns import CampaignGenerator
from .entities.inventory import InventoryGenerator
from .entities.orders import OrderGenerator
from .entities.order_items import OrderItemGenerator
from .entities.clickstream import ClickstreamGenerator


VALID_TIERS = ("small", "medium", "large")
VALID_FORMATS = ("json", "csv", "parquet")

# Tier configurations: (customers, products, campaigns, inventory, orders, order_items, clicks)
# We use order_items multiplier: 3x orders roughly
TIER_COUNTS = {
    "small": {
        "customers": 1000,
        "products": 100,
        "campaigns": 5,
        "inventory": 200,
        "orders": 5000,
        "order_items": 15000,
        "clickstream_events": 50000,
    },
    "medium": {
        "customers": 10000,
        "products": 500,
        "campaigns": 20,
        "inventory": 1000,
        "orders": 50000,
        "order_items": 150000,
        "clickstream_events": 500000,
    },
    "large": {
        "customers": 100000,
        "products": 2000,
        "campaigns": 50,
        "inventory": 5000,
        "orders": 500000,
        "order_items": 1500000,
        "clickstream_events": 5000000,
    },
}


def export_dataframe(df, entity_name: str, output_dir: Path, output_format: str):
    """Export pandas DataFrame to the requested format."""
    out_path = output_dir / f"{entity_name}.{output_format}"
    
    if output_format == "json":
        df.to_json(out_path, orient="records", lines=True, date_format="iso")
    elif output_format == "csv":
        df.to_csv(out_path, index=False)
    elif output_format == "parquet":
        df.to_parquet(out_path, index=False)
    
    click.echo(f"  -> Exported {len(df)} rows to {out_path}")


@click.command()
@click.option(
    "--tier",
    type=click.Choice(VALID_TIERS, case_sensitive=False),
    default="small",
    show_default=True,
    help="Data volume tier. 'large' requires explicit approval.",
)
@click.option(
    "--seed",
    type=int,
    default=42,
    show_default=True,
    help="Random seed for reproducible generation.",
)
@click.option(
    "--output-dir",
    required=True,
    help="Local directory to write generated files.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(VALID_FORMATS, case_sensitive=False),
    default="json",
    show_default=True,
    help="Output file format.",
)
@click.option(
    "--entities",
    default="all",
    show_default=True,
    help="Comma-separated entity names to generate, or 'all'.",
)
def main(tier: str, seed: int, output_dir: str, output_format: str, entities: str):
    """
    Generate synthetic Commerce360 data for all configured entities.

    \b
    Example:
        python -m data_generator.generator \
            --tier small \
            --seed 42 \
            --output-dir data/generated/small \
            --format json
    """
    if tier == "large":
        click.echo(
            "ERROR: 'large' tier requires explicit approval. "
            "Set --tier to 'small' or 'medium' for dev work.",
            err=True,
        )
        sys.exit(1)

    out_dir_path = Path(output_dir)
    out_dir_path.mkdir(parents=True, exist_ok=True)
    
    counts = TIER_COUNTS[tier]
    
    click.echo(f"Starting Commerce360 Data Generator (Tier: {tier}, Seed: {seed})")
    
    # 1. Independent Entities
    click.echo("Generating Customers...")
    customers_df = CustomerGenerator(seed).generate(counts["customers"])
    export_dataframe(customers_df, "customers", out_dir_path, output_format)
    customer_ids = customers_df["customer_id"].tolist()
    
    click.echo("Generating Products...")
    products_df = ProductGenerator(seed).generate(counts["products"])
    export_dataframe(products_df, "products", out_dir_path, output_format)
    product_ids = products_df["product_id"].tolist()
    
    click.echo("Generating Campaigns...")
    campaigns_df = CampaignGenerator(seed).generate(counts["campaigns"])
    export_dataframe(campaigns_df, "campaigns", out_dir_path, output_format)
    campaign_ids = campaigns_df["campaign_id"].tolist()
    
    # 2. Dependent Entities
    click.echo("Generating Inventory...")
    inventory_df = InventoryGenerator(seed).generate(counts["inventory"], product_ids=product_ids)
    export_dataframe(inventory_df, "inventory", out_dir_path, output_format)
    
    click.echo("Generating Orders...")
    orders_df = OrderGenerator(seed).generate(counts["orders"], customer_ids=customer_ids, campaign_ids=campaign_ids)
    export_dataframe(orders_df, "orders", out_dir_path, output_format)
    
    click.echo("Generating Order Items...")
    order_items_df = OrderItemGenerator(seed).generate(counts["order_items"], orders=orders_df, products=products_df)
    export_dataframe(order_items_df, "order_items", out_dir_path, output_format)
    
    # We should also update orders dataframe amounts based on items, but for now we skip complex back-population
    # as this is synthetic load testing data, and the orders are already generated and valid.
    
    click.echo("Generating Clickstream Events...")
    clickstream_df = ClickstreamGenerator(seed).generate(counts["clickstream_events"], customer_ids=customer_ids, product_ids=product_ids)
    export_dataframe(clickstream_df, "clickstream_events", out_dir_path, output_format)

    click.echo(f"Successfully generated all {tier} tier data to {out_dir_path}")

if __name__ == "__main__":
    main()
