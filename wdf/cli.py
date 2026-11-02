from __future__ import annotations

from pathlib import Path

import typer

from wdf.config import load_settings
from wdf.dashboard_export import export_dashboard
from wdf.pipeline import run_detection, run_evaluation, run_forecast, run_generate, run_repro, run_validation


app = typer.Typer(no_args_is_help=True, help="Synthetic workforce planning generator and validator.")


@app.command()
def generate(
    scale: str = typer.Option("starter", help="Dataset scale: starter or full."),
    seed: int | None = typer.Option(None, help="Random seed; defaults to config/default.yaml."),
    out: Path = typer.Option(Path("output/starter"), help="Output directory."),
) -> None:
    actual_seed = load_settings().seed if seed is None else seed
    result = run_generate(out, scale, actual_seed)
    typer.echo(f"Generated {len(result['manifest']['files'])} artifacts in {out}")
    typer.echo(f"Validation: {result['validation']['status']}")
    if result["validation"]["status"] != "PASS":
        raise typer.Exit(code=1)


@app.command()
def validate(input: Path = typer.Option(Path("output/starter"), help="Generated dataset directory.")) -> None:
    report = run_validation(input)
    typer.echo(f"Validation: {report['status']}; errors={len(report['errors'])}; warnings={len(report['warnings'])}")
    if report["errors"]:
        for error in report["errors"]:
            typer.echo(error, err=True)
    if report["status"] != "PASS":
        raise typer.Exit(code=1)


@app.command()
def detect(input: Path = typer.Option(Path("output/starter"), help="Generated dataset directory.")) -> None:
    rows = run_detection(input)
    typer.echo(f"Detected {len(rows)} anomalies")


@app.command()
def evaluate(input: Path = typer.Option(Path("output/starter"), help="Generated dataset directory.")) -> None:
    result = run_evaluation(input)
    typer.echo(f"Evaluation completed for seed {result['seed']} and held-out seed {result['held_out_seed']['seed']}")


@app.command()
def forecast(input: Path = typer.Option(Path("output/starter"), help="Generated dataset directory.")) -> None:
    result = run_forecast(input)
    typer.echo(
        f"Role and project/role forecast complete for "
        f"{result['forecast_weeks']} future ISO weeks"
    )


@app.command()
def repro(
    scale: str = typer.Option("starter", help="Dataset scale: starter or full."),
    seed: int | None = typer.Option(None, help="Random seed; defaults to config/default.yaml."),
    out: Path = typer.Option(Path("output"), help="Report/output directory."),
) -> None:
    actual_seed = load_settings().seed if seed is None else seed
    report = run_repro(out, scale, actual_seed)
    typer.echo(f"Reproducibility: {report['status']} ({report['file_count']} files)")
    if report["status"] != "PASS":
        raise typer.Exit(code=1)


@app.command("export-dashboard")
def export_dashboard_command(
    input: Path = typer.Option(Path("output/starter"), help="Generated dataset directory."),
) -> None:
    report = export_dashboard(input)
    typer.echo(
        f"Exported {len(report['files'])} aggregated dashboard files "
        f"({report['bytes']} bytes) to dashboard/public/data"
    )
    for name, digest in report["sha256"].items():
        typer.echo(f"{name}: {digest}")


if __name__ == "__main__":
    app()
