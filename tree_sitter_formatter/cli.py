import shutil
import sys
import traceback
from pathlib import Path
from typing import Optional

import typer

from tree_sitter_formatter.formatter import TreeSitterFormatter


def format_callback(file):
    print("do format")
    breakpoint()
    ...


app = typer.Typer()


def _install_config():
    default_config = Path(__file__).parent / "default_tree_sitter_formatter.toml"
    user_config = Path.home() / ".config" / ".tree_sitter_formatter.toml"
    shutil.copy(default_config, user_config)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    file: Optional[Path] = typer.Argument(None),
    dry_run: bool = typer.Option(False),
    should_pdb: bool = typer.Option(False, "--pdb"),
    install_config: bool = typer.Option(False, "--install-config"),
):
    if install_config:
        _install_config()

    if file is None:
        return
    if should_pdb:
        try:
            run(file, dry_run)
        except BaseException:
            import ipdb

            extype, value, tb = sys.exc_info()
            traceback.print_exc()
            ipdb.post_mortem(tb)
    else:
        run(file, dry_run)


def run(file, dry_run):
    formatter = TreeSitterFormatter(file)
    if dry_run:
        formatter.log_highlight()
    else:
        formatter.save()


if __name__ == "__main__":
    app()
