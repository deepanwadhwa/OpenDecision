import os
from unittest.mock import patch

import pytest

from opendecision import __version__
from opendecision.cli import main


def test_cli_version(capsys):
    with pytest.raises(SystemExit, match="0"):
        main(["--version"])

    assert capsys.readouterr().out.strip() == (
        f"opendecision {__version__}"
    )


def test_cli_without_command_prints_help(capsys):
    assert main([]) == 0
    assert "serve" in capsys.readouterr().out


@patch("opendecision.cli.uvicorn.run")
def test_cli_serve(mock_run, monkeypatch):
    monkeypatch.delenv("OPENDECISION_MODEL", raising=False)

    assert main(
        [
            "serve",
            "--host",
            "0.0.0.0",
            "--port",
            "9000",
            "--model",
            "example/model",
        ]
    ) == 0

    assert os.environ["OPENDECISION_MODEL"] == "example/model"
    mock_run.assert_called_once_with(
        "opendecision.api.app:app",
        host="0.0.0.0",
        port=9000,
    )
