"""Python AST analyzer for codebase analysis.

This module contains the PythonCodeAnalyzer (AST NodeVisitor) class,
function/class extraction, complexity analysis, call graph building,
and the CodeGraph class for dependency analysis.
"""

import ast
from typing import Any, Dict, List, Optional, Union

from aura_cli.core.logger import get_logger

logger = get_logger(__name__)


class PythonCodeAnalyzer(ast.NodeVisitor):
    """Analyse Python code and extract detailed AST information."""

    def __init__(self):
        """Initialise an empty code graph."""
        self.functions: List[Dict[str, Any]] = []
        self.classes: List[Dict[str, Any]] = []
        self.imports: List[Dict[str, Any]] = []
        self.variables: List[Dict[str, Any]] = []
        self.calls: List[Dict[str, Any]] = []  # Function calls for call graph
        self._current_scope: List[str] = []  # Track current class/function scope
        self._complexity_stack: List[int] = [0]  # Track cyclomatic complexity

    def _get_docstring(self, node: ast.AST) -> Optional[str]:
        """Extract docstring from a node."""
        if isinstance(
            node, (ast.AsyncFunctionDef, ast.FunctionDef, ast.ClassDef, ast.Module)
        ):
            return ast.get_docstring(node)
        return None

    def _get_decorators(
        self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef]
    ) -> List[str]:
        """Extract decorator names from a node."""
        decorators = []
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                decorators.append(decorator.id)
            elif isinstance(decorator, ast.Attribute):
                decorators.append(f"{self._get_full_attr_name(decorator)}")
            elif isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Name):
                    decorators.append(f"{decorator.func.id}(...)")
                elif isinstance(decorator.func, ast.Attribute):
                    decorators.append(
                        f"{self._get_full_attr_name(decorator.func)}(...)"
                    )
        return decorators

    def _get_full_attr_name(self, node: ast.Attribute) -> str:
        """Get the full name from an attribute (e.g., 'module.submodule.func')."""
        parts = []
        current: Any = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))

    def _get_function_args(
        self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]
    ) -> Dict[str, Any]:
        """Extract function arguments with types if available."""
        args_info: Dict[str, Any] = {
            "positional": [],
            "keyword_only": [],
            "defaults_count": len(node.args.defaults),
            "has_varargs": node.args.vararg is not None,
            "has_kwargs": node.args.kwarg is not None,
        }

        for arg in node.args.args:
            arg_info = {"name": arg.arg}
            if arg.annotation:
                try:
                    arg_info["type"] = ast.unparse(arg.annotation)
                except Exception:
                    arg_info["type"] = "Any"
            args_info["positional"].append(arg_info)

        for arg in node.args.kwonlyargs:
            arg_info = {"name": arg.arg}
            if arg.annotation:
                try:
                    arg_info["type"] = ast.unparse(arg.annotation)
                except Exception:
                    arg_info["type"] = "Any"
            args_info["keyword_only"].append(arg_info)

        return args_info

    def _get_return_type(
        self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]
    ) -> Optional[str]:
        """Extract return type annotation if available."""
        if node.returns:
            try:
                return ast.unparse(node.returns)
            except Exception:
                return "Any"
        return None

    def _calculate_complexity(self, node: ast.AST) -> int:
        """
        Calculate cyclomatic complexity for a function/method.
        Complexity = 1 + (if + elif + for + while + and + or + except + with + assert + ternary)
        """
        complexity = 1

        for child in ast.walk(node):
            if isinstance(
                child,
                (
                    ast.If,
                    ast.For,
                    ast.While,
                    ast.ExceptHandler,
                    ast.With,
                    ast.Assert,
                    ast.comprehension,
                ),
            ):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, ast.IfExp):
                complexity += 1

        return complexity

    def _get_class_bases(self, node: ast.ClassDef) -> List[str]:
        """Extract base class names."""
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(self._get_full_attr_name(base))
            elif isinstance(base, ast.Subscript):
                try:
                    bases.append(ast.unparse(base))
                except Exception:
                    bases.append("Generic")
        return bases

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit function definition node."""
        self._visit_function(node, is_async=False)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Visit async function definition node."""
        self._visit_function(node, is_async=True)
        self.generic_visit(node)

    def _visit_function(
        self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef], is_async: bool
    ):
        """Process function definition node."""
        scope = ".".join(self._current_scope) if self._current_scope else None

        func_info: Dict[str, Any] = {
            "name": node.name,
            "line": node.lineno,
            "end_line": getattr(node, "end_lineno", node.lineno),
            "is_async": is_async,
            "is_method": len(self._current_scope) > 0
            and self._current_scope[-1].startswith("class:"),
            "scope": scope,
            "decorators": self._get_decorators(node),
            "docstring": self._get_docstring(node),
            "args": self._get_function_args(node),
            "return_type": self._get_return_type(node),
            "complexity": self._calculate_complexity(node),
        }

        if func_info["is_method"]:
            if node.name.startswith("__") and node.name.endswith("__"):
                func_info["method_type"] = "dunder"
            elif node.name.startswith("_"):
                func_info["method_type"] = "private"
            elif "staticmethod" in func_info["decorators"]:
                func_info["method_type"] = "static"
            elif "classmethod" in func_info["decorators"]:
                func_info["method_type"] = "classmethod"
            elif "property" in func_info["decorators"]:
                func_info["method_type"] = "property"
            else:
                func_info["method_type"] = "instance"

        self.functions.append(func_info)

        self._current_scope.append(f"func:{node.name}")
        for child in ast.iter_child_nodes(node):
            self.visit(child)
        self._current_scope.pop()

    def visit_ClassDef(self, node: ast.ClassDef):
        """Process class definition node."""
        scope = ".".join(self._current_scope) if self._current_scope else None

        class_info: Dict[str, Any] = {
            "name": node.name,
            "line": node.lineno,
            "end_line": getattr(node, "end_lineno", node.lineno),
            "scope": scope,
            "bases": self._get_class_bases(node),
            "decorators": self._get_decorators(node),
            "docstring": self._get_docstring(node),
            "methods": [],
            "class_variables": [],
        }

        self.classes.append(class_info)

        self._current_scope.append(f"class:{node.name}")

        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.visit(child)
                class_info["methods"].append(child.name)
            elif isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Name):
                        class_info["class_variables"].append(target.id)
                self.visit(child)
            else:
                self.visit(child)

        self._current_scope.pop()

    def visit_Import(self, node: ast.Import):
        """Visit import statement node."""
        for alias in node.names:
            self.imports.append(
                {
                    "type": "import",
                    "module": alias.name,
                    "alias": alias.asname,
                    "line": node.lineno,
                }
            )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Visit from-import statement node."""
        module = node.module if node.module else ""
        for alias in node.names:
            self.imports.append(
                {
                    "type": "from_import",
                    "module": module,
                    "name": alias.name,
                    "alias": alias.asname,
                    "line": node.lineno,
                    "level": node.level,  # For relative imports
                }
            )
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        """Visit assignment statement node."""
        if not self._current_scope:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    var_info = {
                        "name": target.id,
                        "line": node.lineno,
                        "is_constant": target.id.isupper(),
                    }
                    try:
                        if isinstance(node.value, ast.Constant):
                            var_info["value_type"] = type(node.value.value).__name__
                        elif isinstance(node.value, ast.List):
                            var_info["value_type"] = "list"
                        elif isinstance(node.value, ast.Dict):
                            var_info["value_type"] = "dict"
                        elif isinstance(node.value, ast.Set):
                            var_info["value_type"] = "set"
                        elif isinstance(node.value, ast.Tuple):
                            var_info["value_type"] = "tuple"
                        elif isinstance(node.value, ast.Call) and isinstance(
                            node.value.func, ast.Name
                        ):
                            var_info["value_type"] = f"{node.value.func.id}()"
                    except Exception as _e:
                        logger.debug(f"Ignorado: {_e}")
                    self.variables.append(var_info)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        """Track function calls for call graph analysis."""
        call_info = {
            "line": node.lineno,
            "scope": ".".join(self._current_scope) if self._current_scope else None,
        }

        if isinstance(node.func, ast.Name):
            call_info["name"] = node.func.id
            call_info["type"] = "direct"
        elif isinstance(node.func, ast.Attribute):
            call_info["name"] = self._get_full_attr_name(node.func)
            call_info["type"] = "attribute"
        else:
            call_info["name"] = "<dynamic>"
            call_info["type"] = "dynamic"

        self.calls.append(call_info)
        self.generic_visit(node)


def analyze_python_ast(file_content: str, detailed: bool = True) -> Dict[str, Any]:
    """Analyse Python file content and return AST data."""
    try:
        tree = ast.parse(file_content)
        analyzer = PythonCodeAnalyzer()
        analyzer.visit(tree)

        if detailed:
            total_complexity = sum(f.get("complexity", 1) for f in analyzer.functions)
            avg_complexity = (
                total_complexity / len(analyzer.functions) if analyzer.functions else 0
            )
            high_complexity_funcs = [
                f["name"] for f in analyzer.functions if f.get("complexity", 0) > 10
            ]

            return {
                "functions": analyzer.functions,
                "classes": analyzer.classes,
                "imports": analyzer.imports,
                "variables": analyzer.variables,
                "calls": analyzer.calls,
                "metrics": {
                    "total_functions": len(analyzer.functions),
                    "total_classes": len(analyzer.classes),
                    "total_imports": len(analyzer.imports),
                    "total_complexity": total_complexity,
                    "avg_complexity": round(avg_complexity, 2),
                    "high_complexity_functions": high_complexity_funcs,
                    "has_type_hints": any(
                        f.get("return_type")
                        or any(
                            a.get("type")
                            for a in f.get("args", {}).get("positional", [])
                        )
                        for f in analyzer.functions
                    ),
                    "documented_functions": len(
                        [f for f in analyzer.functions if f.get("docstring")]
                    ),
                    "documented_classes": len(
                        [c for c in analyzer.classes if c.get("docstring")]
                    ),
                },
            }
        else:
            return {
                "functions": [f["name"] for f in analyzer.functions],
                "classes": [c["name"] for c in analyzer.classes],
                "imports": [
                    i.get("module", "")
                    + ("." + i.get("name", "") if i.get("name") else "")
                    for i in analyzer.imports
                ],
                "variables": [v["name"] for v in analyzer.variables],
            }
    except SyntaxError as e:
        logger.warning(f"Erro de sintaxe ao analisar AST: {e}")
        return {"error": f"SyntaxError: {e}"}
    except Exception as e:
        logger.error(f"Erro inesperado ao analisar AST: {e}")
        return {"error": f"Unexpected error: {e}"}


class CodeGraph:
    """Code graph for dependency analysis and call graphs."""

    def __init__(self):
        """Initialise an empty code graph."""
        self.nodes: Dict[str, Dict[str, Any]] = {}  # node_id -> node_data
        self.edges: List[Dict[str, Any]] = []  # list of edges with metadata
        self.files: Dict[str, Dict[str, Any]] = {}  # file_path -> file_analysis

    def add_file(self, file_path: str, ast_data: Dict[str, Any]):
        """Add an analysed file to the graph."""
        self.files[file_path] = ast_data
        for cls in ast_data.get("classes", []):
            node_id = f"{file_path}::{cls['name']}"
            self.nodes[node_id] = {
                "type": "class",
                "name": cls["name"],
                "file": file_path,
                "line": cls.get("line"),
                "docstring": cls.get("docstring"),
                "bases": cls.get("bases", []),
                "methods": cls.get("methods", []),
            }
            for base in cls.get("bases", []):
                self.edges.append(
                    {
                        "source": node_id,
                        "target": f"*::{base}",  # Wildcard - need to resolve later
                        "type": "inherits",
                        "file": file_path,
                    }
                )
        for func in ast_data.get("functions", []):
            scope = func.get("scope", "")
            if scope and scope.startswith("class:"):
                class_name = scope.split(":")[1].split(".")[0]
                node_id = f"{file_path}::{class_name}.{func['name']}"
            else:
                node_id = f"{file_path}::{func['name']}"

            self.nodes[node_id] = {
                "type": "function" if not func.get("is_method") else "method",
                "name": func["name"],
                "file": file_path,
                "line": func.get("line"),
                "docstring": func.get("docstring"),
                "complexity": func.get("complexity", 1),
                "is_async": func.get("is_async", False),
                "args": func.get("args", {}),
                "return_type": func.get("return_type"),
            }
        for call in ast_data.get("calls", []):
            caller_scope = call.get("scope", "")
            if caller_scope:
                parts = caller_scope.split(".")
                # Extract caller's own name for edge labelling (used below in caller_id)
                _caller_own = parts[-1].split(":")[1] if ":" in parts[-1] else parts[-1]
                for scope_part in reversed(parts):
                    if scope_part.startswith("func:"):
                        caller_func = scope_part.split(":")[1]
                        caller_id = f"{file_path}::*{caller_func}"  # Wildcard match
                        break
                    elif scope_part.startswith("class:"):
                        class_name = scope_part.split(":")[1]
                        caller_id = f"{file_path}::{class_name}"
                        break
                else:
                    caller_id = f"{file_path}::<module>"
            else:
                caller_id = f"{file_path}::<module>"

            self.edges.append(
                {
                    "source": caller_id,
                    "target": f"*::{call['name']}",  # Will be resolved later
                    "type": "calls",
                    "line": call.get("line"),
                    "file": file_path,
                }
            )
        for imp in ast_data.get("imports", []):
            module = imp.get("module", "")
            name = imp.get("name", "")
            full_import = f"{module}.{name}" if name else module

            self.edges.append(
                {
                    "source": f"{file_path}::<module>",
                    "target": full_import,
                    "type": "imports",
                    "line": imp.get("line"),
                    "file": file_path,
                }
            )

    def resolve_edges(self):
        """Resolve wildcard targets in edges to actual node IDs."""
        name_to_nodes: Dict[str, List[str]] = {}
        for node_id, node_data in self.nodes.items():
            name = node_data["name"]
            if name not in name_to_nodes:
                name_to_nodes[name] = []
            name_to_nodes[name].append(node_id)
        resolved_edges = []
        for edge in self.edges:
            target = edge["target"]
            if target.startswith("*::"):
                target_name = target[3:]  # Remove "*::"
                if "." in target_name:
                    parts = target_name.split(".")
                    target_name = parts[-1]  # Just use the final name

                if target_name in name_to_nodes:
                    for resolved_target in name_to_nodes[target_name]:
                        new_edge = edge.copy()
                        new_edge["target"] = resolved_target
                        new_edge["resolved"] = True
                        resolved_edges.append(new_edge)
                else:
                    edge["resolved"] = False
                    resolved_edges.append(edge)
            else:
                edge["resolved"] = True
                resolved_edges.append(edge)

        self.edges = resolved_edges

    def find_callers(self, function_name: str) -> List[Dict[str, Any]]:
        """Find all functions that call a given function."""
        results = []
        for edge in self.edges:
            if edge["type"] == "calls":
                target = edge["target"]
                if (
                    target.endswith(f"::{function_name}")
                    or target == f"*::{function_name}"
                ):
                    source_node = self.nodes.get(edge["source"], {})
                    results.append(
                        {
                            "caller": edge["source"],
                            "caller_name": source_node.get("name", edge["source"]),
                            "file": edge.get("file"),
                            "line": edge.get("line"),
                        }
                    )
        return results

    def find_callees(self, function_name: str) -> List[Dict[str, Any]]:
        """Find all functions called by a given function."""
        results = []
        for edge in self.edges:
            if edge["type"] == "calls":
                source = edge["source"]
                if (
                    source.endswith(f"::{function_name}")
                    or f".{function_name}" in source
                ):
                    target_node = self.nodes.get(edge["target"], {})
                    results.append(
                        {
                            "callee": edge["target"],
                            "callee_name": target_node.get("name", edge["target"]),
                            "line": edge.get("line"),
                        }
                    )
        return results

    def find_subclasses(self, class_name: str) -> List[Dict[str, Any]]:
        """Find all classes that inherit from a given class."""
        results = []
        for edge in self.edges:
            if edge["type"] == "inherits":
                target = edge["target"]
                if target.endswith(f"::{class_name}") or target == f"*::{class_name}":
                    source_node = self.nodes.get(edge["source"], {})
                    results.append(
                        {
                            "subclass": edge["source"],
                            "subclass_name": source_node.get("name"),
                            "file": edge.get("file"),
                        }
                    )
        return results

    def find_usages(self, symbol_name: str) -> Dict[str, List[Dict[str, Any]]]:
        """Find all usages of a symbol (calls, inheritance, imports)."""
        return {
            "calls": self.find_callers(symbol_name),
            "subclasses": self.find_subclasses(symbol_name),
            "imports": [
                {"file": e["file"], "line": e.get("line")}
                for e in self.edges
                if e["type"] == "imports" and symbol_name in e["target"]
            ],
        }

    def get_impact_analysis(
        self, symbol_name: str, max_depth: int = 3
    ) -> Dict[str, Any]:
        """
        Analyze the potential impact of changing a symbol.
        Returns a tree of affected symbols.
        """
        affected: Dict[str, Any] = {"direct": [], "indirect": []}
        visited = set()

        def trace_impact(name: str, depth: int):
            """Trace impact of changes."""
            if depth > max_depth or name in visited:
                return
            visited.add(name)

            callers = self.find_callers(name)
            for caller in callers:
                caller_name = caller.get("caller_name", "")
                if depth == 1:
                    affected["direct"].append(caller)
                else:
                    affected["indirect"].append(caller)
                trace_impact(caller_name, depth + 1)

        trace_impact(symbol_name, 1)
        return affected

    def get_high_complexity_functions(
        self, threshold: int = 10
    ) -> List[Dict[str, Any]]:
        """Get functions with complexity above threshold."""
        results = []
        for node_data in self.nodes.values():
            if node_data["type"] in ("function", "method"):
                complexity = node_data.get("complexity", 1)
                if complexity > threshold:
                    results.append(
                        {
                            "name": node_data["name"],
                            "file": node_data["file"],
                            "line": node_data.get("line"),
                            "complexity": complexity,
                        }
                    )
        return sorted(results, key=lambda x: x["complexity"], reverse=True)

    def get_statistics(self) -> Dict[str, Any]:
        """Get graph statistics."""
        node_types: Dict[str, int] = {}
        for node_data in self.nodes.values():
            t = node_data["type"]
            node_types[t] = node_types.get(t, 0) + 1

        edge_types: Dict[str, int] = {}
        for edge in self.edges:
            t = edge["type"]
            edge_types[t] = edge_types.get(t, 0) + 1

        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "total_files": len(self.files),
            "node_types": node_types,
            "edge_types": edge_types,
        }
