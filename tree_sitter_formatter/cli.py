import subprocess
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.style import Style
from rich.syntax import Syntax
from tree_sitter_languages import get_language, get_parser

formatters = {
    "python": {
        "cmd": "black",
        "mode": "inplace",
    },
    "bash": {
        "cmd": "/usr/bin/cat",
        "mode": "stdout",
    },
    "sql": {
        "cmd": "sqlformat --reindent --keywords upper --identifiers lower -a",
        "mode": "stdout",
    },
    "yaml": {
        "cmd": "yq -yi ''",
        "mode": "inplace",
    },
}


def format(formatter: str, mode: str, code: str):
    file = tempfile.NamedTemporaryFile(prefix="codeformat")
    file.write(code.encode())
    file.seek(0)

    cmd = ([*formatter.split(), file.name],)

    proc = subprocess.Popen(
        " ".join([*formatter.split(), file.name]),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
    )
    if proc.wait() == 0:
        if mode == "inplace":
            return Path(file.name).read_text()
        if mode == "stdout":
            return proc.stdout.read().decode()
        # return file.file.read().decode()


class TreeSitterFormatter:
    def __init__(self, file):

        self.console = Console()
        self.file = Path(file)
        self.content = self.file.read_text()
        self.language = get_language("markdown")
        self.parser = get_parser("markdown")

        # self.query = self.language.query(self.query_str)
        self.queries = {
            language: self.make_query(language) for language in formatters.keys()
        }

    def __rich_repr__(self):
        self.console.print(self.syntax)

    def make_query(self, language):

        return self.language.query(
            f"""
        (fenced_code_block
        (info_string) @info (#eq? @info "{language}")
        (code_fence_content) @python
        ) @block
        """
        )

    def format_capture(self, capture, language):
        content = self.content.split("\n")

        formatted = format(
            formatters[language]["cmd"],
            formatters[language]["mode"],
            "\n".join(content[capture.start_point[0] + 1 : capture.end_point[0]]),
        )
        formatted = formatted.strip("\n")

        del content[capture.start_point[0] + 1 : capture.end_point[0]]

        content.insert(capture.start_point[0] + 1, formatted)

        self.content = "\n".join(content)

    def format(self):
        for capture in self.captures:
            if capture[2] in formatters.keys():
                self.format_capture(capture[0], capture[2])
    @property
    def syntax(self):
        self.format()

        syntax = Syntax(self.content, "markdown", line_numbers=True)
        style = Style(bgcolor="deep_pink4")

        for capture in self.captures:
            if capture[2] in formatters.keys():
                self.highlight(syntax, capture[0], style, capture[2])

        return syntax

    def highlight(self, syntax, capture, style, lang):
        start = capture.start_point
        start = (start[0] + 1, start[1])
        end = capture.end_point
        end = (end[0] + 1, end[1])

        syntax.stylize_range(style, start, end)

        code = syntax.code.split("\n")
        comment_start = (start[0], len(code[start[0] - 1]))
        code[start[0] - 1] = code[start[0] - 1] + f"       ■ {formatters[lang]}"
        comment_end = (start[0], len(code[start[0] - 1]))
        syntax.code = "\n".join(code)
        comment_style = Style(color="deep_pink4", italic=True, bgcolor="grey15")
        syntax.stylize_range(comment_style, comment_start, comment_end)

    def log_highlight(self):
        self.console.print(self.syntax)

    def save(self):
        self.format()
        self.file.write_text(self.content)

    def add_formatter(self, capture_obj):
        capture = capture_obj[0]
        lang = (
            self.content.split("\n")[capture.start_point[0]].replace("```", "").strip()
        )
        # capture.start_point = (capture.start_point[0] + 1, capture.start_point[1])
        # capture.end_point = (capture.end_point[0] + 1, capture.end_point[1])
        capture_obj = (*capture_obj, lang)
        return capture_obj

    @property
    def tree(self):
        return self.parser.parse(self.content.encode())

    @property
    def captures(self):
        node = self.tree.root_node
        captures = []
        for name, query in self.queries.items():
            captures.extend(
                [
                    capture
                    for capture in self.queries[name].captures(node)
                    if capture[1] == "block"
                ]
            )

        captures = [self.add_formatter(capture) for capture in captures]

        return captures


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
