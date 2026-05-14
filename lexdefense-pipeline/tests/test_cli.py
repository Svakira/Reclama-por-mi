from pathlib import Path

from typer.testing import CliRunner

from lexdefense.cli import app


def test_cli_app_exists() -> None:
    assert app is not None


def test_ingest_command_accepts_named_options(tmp_path: Path) -> None:
    runner = CliRunner()
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "run"
    input_dir.mkdir()
    (input_dir / "demanda.txt").write_text("HECHO 1. Existe una poliza 123.", encoding="utf-8")

    result = runner.invoke(app, ["ingest", "--input", str(input_dir), "--out", str(output_dir)])

    assert result.exit_code == 0, result.stdout
