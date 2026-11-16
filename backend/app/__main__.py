"""CLI entry point for the food market data pipeline."""

import typer


app = typer.Typer(no_args_is_help=True)


@app.callback()
def main() -> None:
    """Collect and validate food industry market data."""


@app.command()
def status() -> None:
    """Show the current implementation stage."""
    typer.echo("source investigation")


if __name__ == "__main__":
    app()
