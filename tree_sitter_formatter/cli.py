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


@app.callback(invoke_without_command=True)
def main(
    file: Optional[Path] = typer.Argument(...),
    dry_run: bool = typer.Option(False),
    should_pdb: bool = typer.Option(False, "--pdb"),
):
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
