import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.style import Style
from rich.syntax import Syntax
from tree_sitter_languages import get_language, get_parser

from tree_sitter_formatter import standard_config


@dataclass
class Formatter:
    cmd: str
    suffix: str = ""
    mode: str = "inplace"


def format(formatter: "Formatter", code: str):
    file = tempfile.NamedTemporaryFile(prefix="codeformat", suffix=formatter.suffix)
    file.write(code.encode())
    file.seek(0)

    cmd = " ".join([*formatter.cmd.split(), file.name])

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
    )
    if proc.wait() == 0:
        if formatter.mode == "inplace":
            return Path(file.name).read_text()
        if formatter.mode == "stdout":
            return proc.stdout.read().decode()
    else:
        import ipdb

        ipdb.breakpoint()


class TreeSitterFormatter:
    def __init__(self, file):

        self.console = Console()
        self.file = Path(file)
        self.suffix = self.file.suffix.replace(".", "")
        self.config = standard_config.load("tree_sitter_formatter")

        self.content = self.file.read_text()
        self.language = get_language(self.config["languages"][self.suffix])
        self.query = self.language.query(self.config["queries"][self.suffix])
        self.parser = get_parser(self.config["languages"][self.suffix])
        self.formatters = {
            name: Formatter(**formatter)
            for name, formatter in self.config["formatters"].items()
        }

        self.format()

    def __rich_repr__(self):
        self.console.print(self.syntax)

    def get_text_from_capture(self, capture):
        content = self.content.split("\n")
        capture = capture[0]
        rows = content[capture.start_point[0] + 1 : capture.end_point[0]]
        rows[0] = rows[0][capture.start_point[1] :]
        rows[-1] = rows[-1][capture.end_point[1] :]
        return "\n".join(rows)

    def format_capture(self, capture):
        content = self.content.split("\n")
        formatter = self.formatters.get(capture[1].replace("format_", ""))
        capture = capture[0]

        formatted = format(
            formatter,
            "\n".join(content[capture.start_point[0] + 1 : capture.end_point[0]]),
        )
        formatted = formatted.strip("\n")

        del content[capture.start_point[0] + 1 : capture.end_point[0]]

        content.insert(capture.start_point[0] + 1, formatted)

        self.content = "\n".join(content)

    def format(self):
        for i in range(len(self.query.captures(self.tree.root_node))):
            capture = self.query.captures(self.tree.root_node)[i]
            if capture[1].startswith("format"):
                self.format_capture(capture)

    @property
    def syntax(self):

        syntax = Syntax(self.content, "markdown", line_numbers=True)
        style = Style(bgcolor="deep_pink4")

        for i in range(len(self.query.captures(self.tree.root_node))):
            capture = self.query.captures(self.tree.root_node)[i]
            if capture[1].startswith("format"):
                self.highlight(
                    syntax,
                    capture[0],
                    style,
                    self.formatters[capture[1].replace("format_", "")],
                )

        return syntax

    def highlight(self, syntax, capture, style, formatter):
        start = capture.start_point
        start = (start[0] + 1, start[1])
        end = capture.end_point
        end = (end[0] + 1, end[1])

        syntax.stylize_range(style, start, end)

        code = syntax.code.split("\n")
        comment_start = (start[0], len(code[start[0] - 1]))
        code[start[0] - 1] = code[start[0] - 1] + f"       ■ {formatter.cmd}"
        comment_end = (start[0], len(code[start[0] - 1]))
        syntax.code = "\n".join(code)
        comment_style = Style(color="deep_pink4", italic=True, bgcolor="grey15")
        syntax.stylize_range(comment_style, comment_start, comment_end)

    def log_highlight(self):
        self.console.print(self.syntax)

    def save(self):
        # self.format()
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

        return self.query.captures(self.tree.root_node)
        node = self.tree.root_node
        captures = []
        for formatter in self.formatters:
            captures.extend(
                [
                    capture
                    for capture in formatter.query.captures(node)
                    if capture[1] == "format"
                ]
            )

        captures = [self.add_formatter(capture) for capture in captures]

        return captures
