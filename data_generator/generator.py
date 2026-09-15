"""
generator.py — CLI entry point for the Commerce360 synthetic data generator.

This module wires the CLI arguments to the per-entity generators.
The actual generation logic lives in data_generator/entities/.

Implemented in Phase 3. This module defines the CLI contract now so that:
  1. 'make generate-small' is a valid target that gives a clear error message.
  2. The CLI interface is agreed before implementation begins.
  3. Unit tests can verify argument parsing independently of generation logic.

Usage:
    python -m data_generator.generator --help
    python -m data_generator.generator --tier small --seed 42 --output-dir data/generated/small --format json
"""

import sys
import click


VALID_TIERS = ("small", "medium", "large")
VALID_FORMATS = ("json", "csv", "parquet")


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
        python -m data_generator.generator \\
            --tier small \\
            --seed 42 \\
            --output-dir data/generated/small \\
            --format json
    """
    if tier == "large":
        click.echo(
            "ERROR: 'large' tier requires explicit approval. "
            "Set --tier to 'small' or 'medium' for dev work.",
            err=True,
        )
        sys.exit(1)

    # Phase 3 will implement the entity generators.
    # This stub exits with a clear message rather than silently doing nothing.
    click.echo(
        f"[Phase 3 not yet implemented]\n"
        f"  tier={tier}, seed={seed}, output_dir={output_dir}, "
        f"format={output_format}, entities={entities}\n"
        f"  Generator implementation begins in Phase 3."
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
