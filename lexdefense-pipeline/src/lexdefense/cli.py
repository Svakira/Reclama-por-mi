from pathlib import Path

import typer

from lexdefense.pipeline.orchestrator import PipelineOrchestrator


app = typer.Typer(help="LexDefense Pipeline CLI")
orchestrator = PipelineOrchestrator()


@app.command()
def ingest(
    input: Path = typer.Option(..., exists=True, file_okay=False, dir_okay=True),
    out: Path = typer.Option(..., file_okay=False, dir_okay=True),
):
    orchestrator.ingest(input, out)
    typer.echo(f"Ingested files into {out}")


@app.command("build-case")
def build_case(
    run: Path = typer.Option(..., exists=True, file_okay=False, dir_okay=True),
    client_role: str = typer.Option(...),
):
    orchestrator.build_case(run, client_role)
    typer.echo(f"Built case schema in {run}")


@app.command("generate-matrix")
def generate_matrix(run: Path = typer.Option(..., exists=True, file_okay=False, dir_okay=True)):
    orchestrator.generate_matrix(run)
    typer.echo(f"Generated matrices in {run}")


@app.command()
def draft(run: Path = typer.Option(..., exists=True, file_okay=False, dir_okay=True)):
    orchestrator.draft(run)
    typer.echo(f"Generated draft in {run}")


@app.command()
def audit(run: Path = typer.Option(..., exists=True, file_okay=False, dir_okay=True)):
    orchestrator.audit(run)
    typer.echo(f"Generated audit in {run}")


@app.command()
def export(
    run: Path = typer.Option(..., exists=True, file_okay=False, dir_okay=True),
    format: str = typer.Option("md"),
):
    status = orchestrator.export(run, format)
    typer.echo(status)


if __name__ == "__main__":
    app()
