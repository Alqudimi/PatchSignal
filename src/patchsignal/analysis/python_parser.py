"""Safe, syntax-only Python repository parser."""

from __future__ import annotations

import ast
from pathlib import Path

from patchsignal.models import Relation, Symbol


def parse_python_file(path: Path, root: Path) -> tuple[list[Symbol], list[Relation]]:
    """Return symbols and import relations; malformed files are skipped by the caller."""
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    relative = path.relative_to(root).as_posix()
    symbols: list[Symbol] = []
    relations: list[Relation] = []

    class Visitor(ast.NodeVisitor):
        scope: list[str] = []

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            name = ".".join([*self.scope, node.name])
            symbols.append(Symbol(name, relative, "class", node.lineno, not node.name.startswith("_")))
            self.scope.append(node.name)
            self.generic_visit(node)
            self.scope.pop()

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            name = ".".join([*self.scope, node.name])
            symbols.append(Symbol(name, relative, "function", node.lineno, not node.name.startswith("_")))
            self.scope.append(node.name)
            self.generic_visit(node)
            self.scope.pop()

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self.visit_FunctionDef(node)  # type: ignore[arg-type]

        def visit_Import(self, node: ast.Import) -> None:
            for alias in node.names:
                relations.append(Relation(relative, alias.name, "imports", relative))

        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
            if node.module:
                relations.append(Relation(relative, node.module, "imports", relative))

    Visitor().visit(tree)
    return symbols, relations
