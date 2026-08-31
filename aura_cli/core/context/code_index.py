"""Codebase semantic indexer — inverted-index + vector search over source files.

Extracts classes, functions, imports and constants via AST; builds inverted
indexes for fast text search; caches index by content hash. Primary entry
points: index_codebase() and search_codebase().
"""

import ast
from collections import defaultdict
from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from aura_cli.core.logger import get_logger

try:
    import numpy as _numpy

    HAS_NUMPY = _numpy is not None
except ImportError:
    HAS_NUMPY = False

logger = get_logger(__name__)


class CodeIndex:
    """Index of an individual file"""

    def __init__(self, file_path: str):
        """Initialize the instance."""
        self.file_path = file_path
        self.classes: List[Dict[str, Any]] = []
        self.functions: List[Dict[str, Any]] = []
        self.imports: List[Dict[str, Any]] = []
        self.constants: List[Dict[str, Any]] = []
        self.docstrings: Dict[str, str] = {}
        self.code_structure: Dict[str, Any] = {}
        self.metadata: Dict[str, Any] = {}
        self.last_modified: Optional[datetime] = None
        self.content_hash: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialise the code index to a dict."""
        return {
            "file_path": self.file_path,
            "classes": self.classes,
            "functions": self.functions,
            "imports": self.imports,
            "constants": self.constants,
            "docstrings": self.docstrings,
            "code_structure": self.code_structure,
            "metadata": self.metadata,
            "last_modified": (
                self.last_modified.isoformat() if self.last_modified else None
            ),
            "content_hash": self.content_hash,
        }


class CodebaseIndexer:
    """Semantic indexer for the full codebase."""

    def __init__(self, scope: str = ".", cache_dir: Optional[str] = None):
        """Initialize the instance."""
        self.scope = Path(scope).resolve()
        from aura_cli.core.paths import ArtifactLayout

        self.cache_dir = (
            Path(cache_dir)
            if cache_dir
            else ArtifactLayout(self.scope).project("index_cache")
        )
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.file_indices: Dict[str, CodeIndex] = {}
        self.class_index: Dict[str, List[str]] = defaultdict(list)
        self.function_index: Dict[str, List[str]] = defaultdict(list)
        self.import_index: Dict[str, List[str]] = defaultdict(list)
        self.content_index: Dict[str, str] = {}

        self.keyword_index: Dict[str, Set[str]] = defaultdict(set)
        self.type_index: Dict[str, Set[str]] = defaultdict(set)

        self._cache_file = self.cache_dir / "codebase_index.json"
        self._indexed = False

    def index_codebase(self, force_reindex: bool = False) -> "CodebaseIndexer":
        """Index the full codebase."""
        if self._indexed and not force_reindex and self._load_cache():
            logger.info("Index loaded from cache")
            return self

        logger.info(f"Indexando codebase em {self.scope}")

        self._clear_indices()

        python_files = list(self.scope.rglob("*.py"))
        python_files = [f for f in python_files if not self._should_ignore(f)]

        logger.info(f"Found {len(python_files)} Python files to index")

        indexed_count = 0
        for file_path in python_files:
            try:
                self._index_file(file_path)
                indexed_count += 1
            except Exception as e:
                logger.warning(f"Error indexing {file_path}: {e}")

        logger.info(f"Indexing completed: {indexed_count} files indexed")

        self._save_cache()
        self._indexed = True

        return self

    def _should_ignore(self, path: Path) -> bool:
        """Return True if a path should be excluded from indexing."""
        ignore_patterns = {
            "__pycache__",
            ".git",
            ".venv",
            "venv",
            "node_modules",
            "build",
            "dist",
            ".pytest_cache",
            ".mypy_cache",
            ".tox",
            ".aura",
            "coding",
            "ops_workspace",
        }
        path_str = str(path)
        return any(pattern in path_str for pattern in ignore_patterns)

    def _index_file(self, file_path: Path):
        """Indexa um arquivo individual"""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            logger.warning(f"Não foi possível ler {file_path}: {e}")
            return

        content_hash = hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()

        relative_path = str(file_path.relative_to(self.scope))
        if (
            relative_path in self.content_index
            and self.content_index[relative_path] == content_hash
        ):
            return

        code_index = CodeIndex(relative_path)
        code_index.content_hash = content_hash
        code_index.last_modified = datetime.fromtimestamp(file_path.stat().st_mtime)

        try:
            tree = ast.parse(content, filename=str(file_path))

            self._extract_structures(tree, code_index, content)

            self.file_indices[relative_path] = code_index
            self.content_index[relative_path] = content_hash

            self._update_inverted_indices(code_index)

        except SyntaxError as e:
            logger.warning(f"Erro de sintaxe em {file_path}: {e}")
            code_index.metadata["syntax_error"] = str(e)
            self.file_indices[relative_path] = code_index

    def _extract_structures(self, tree: ast.AST, code_index: CodeIndex, content: str):
        """Extract structures from an AST."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_info = {
                    "name": node.name,
                    "line": node.lineno,
                    "bases": [self._ast_to_string(base) for base in node.bases],
                    "decorators": [
                        self._ast_to_string(dec) for dec in node.decorator_list
                    ],
                    "methods": [],
                }

                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        class_info["methods"].append(item.name)  # type: ignore[attr-defined]

                if (
                    node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)
                ):
                    class_info["docstring"] = node.body[0].value.value
                    code_index.docstrings[f"class:{node.name}"] = node.body[
                        0
                    ].value.value

                code_index.classes.append(class_info)

            elif isinstance(node, ast.FunctionDef):
                func_info = {
                    "name": node.name,
                    "line": node.lineno,
                    "args": [arg.arg for arg in node.args.args],
                    "decorators": [
                        self._ast_to_string(dec) for dec in node.decorator_list
                    ],
                    "is_async": isinstance(node, ast.AsyncFunctionDef),
                }

                if (
                    node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)
                ):
                    func_info["docstring"] = node.body[0].value.value
                    code_index.docstrings[f"function:{node.name}"] = node.body[
                        0
                    ].value.value

                code_index.functions.append(func_info)

            elif isinstance(node, ast.Import):
                for alias in node.names:
                    import_info = {
                        "module": alias.name,
                        "alias": alias.asname,
                        "line": node.lineno,
                    }
                    code_index.imports.append(import_info)

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    import_info = {
                        "module": module,
                        "name": alias.name,
                        "alias": alias.asname,
                        "line": node.lineno,
                    }
                    code_index.imports.append(import_info)

            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and isinstance(
                        node.value, (ast.Constant, ast.Str)
                    ):
                        const_info = {
                            "name": target.id,
                            "line": node.lineno,
                            "value": self._ast_to_string(node.value),
                        }
                        code_index.constants.append(const_info)

    def _ast_to_string(self, node: ast.AST) -> str:
        """Convert an AST node to a compact string representation."""
        try:
            if isinstance(node, ast.Constant):
                return str(node.value)
            elif isinstance(node, ast.Name):
                return node.id
            elif isinstance(node, ast.Attribute):
                return f"{self._ast_to_string(node.value)}.{node.attr}"
            elif isinstance(node, ast.Str):
                return node.s  # type: ignore[return-value]
            else:
                return ast.unparse(node) if hasattr(ast, "unparse") else str(node)
        except (AttributeError, TypeError, SyntaxError):
            return str(node)

    def _update_inverted_indices(self, code_index: CodeIndex):
        """Update inverted indices after indexing a file."""
        file_path = code_index.file_path

        for class_info in code_index.classes:
            self.class_index[class_info["name"]].append(file_path)
            keywords = self._extract_keywords(class_info["name"])
            for keyword in keywords:
                self.keyword_index[keyword].add(file_path)

        for func_info in code_index.functions:
            self.function_index[func_info["name"]].append(file_path)
            keywords = self._extract_keywords(func_info["name"])
            for keyword in keywords:
                self.keyword_index[keyword].add(file_path)

        for import_info in code_index.imports:
            module = import_info.get("module", "")
            if module:
                self.import_index[module].append(file_path)
                keywords = self._extract_keywords(module)
                for keyword in keywords:
                    self.keyword_index[keyword].add(file_path)

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text (camelCase, snake_case, etc.)."""
        keywords = set()

        keywords.add(text.lower())

        import re

        camel_case_parts = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)", text)
        for part in camel_case_parts:
            keywords.add(part.lower())

        snake_case_parts = text.split("_")
        for part in snake_case_parts:
            if part:
                keywords.add(part.lower())

        return list(keywords)

    def _clear_indices(self):
        """Limpa todos os indexs"""
        self.file_indices.clear()
        self.class_index.clear()
        self.function_index.clear()
        self.import_index.clear()
        self.content_index.clear()
        self.keyword_index.clear()
        self.type_index.clear()

    def _save_cache(self):
        """Persist the index to cache."""
        try:
            cache_data = {
                "format_version": 1,
                "file_indices": {k: v.to_dict() for k, v in self.file_indices.items()},
                "class_index": dict(self.class_index),
                "function_index": dict(self.function_index),
                "import_index": dict(self.import_index),
                "content_index": dict(self.content_index),
                "keyword_index": {k: list(v) for k, v in self.keyword_index.items()},
                "scope": str(self.scope),
                "timestamp": datetime.now().isoformat(),
            }

            with open(self._cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False)

            logger.info(f"Índice salvo no cache: {self._cache_file}")
        except Exception as e:
            logger.warning(f"Error saving cache: {e}")

    def _load_cache(self) -> bool:
        """Load the index from cache."""
        if not self._cache_file.exists():
            return False

        try:
            with open(self._cache_file, encoding="utf-8") as f:
                cache_data = json.load(f)
            if cache_data.get("format_version") != 1:
                logger.warning("Versão desconhecida do cache de índice; reindexando")
                return False

            self.file_indices = {
                k: self._dict_to_code_index(v)
                for k, v in cache_data.get("file_indices", {}).items()
            }
            self.class_index = defaultdict(list, cache_data.get("class_index", {}))
            self.function_index = defaultdict(
                list, cache_data.get("function_index", {})
            )
            self.import_index = defaultdict(list, cache_data.get("import_index", {}))
            self.content_index = cache_data.get("content_index", {})
            self.keyword_index = defaultdict(
                set, {k: set(v) for k, v in cache_data.get("keyword_index", {}).items()}
            )

            logger.info("Index loaded from cache successfully")
            return True
        except Exception as e:
            logger.warning(f"Error loading cache: {e}")
            return False

    def _dict_to_code_index(self, data: Dict) -> CodeIndex:
        """Deserialise a code index from a dict."""
        code_index = CodeIndex(data["file_path"])
        code_index.classes = data.get("classes", [])
        code_index.functions = data.get("functions", [])
        code_index.imports = data.get("imports", [])
        code_index.constants = data.get("constants", [])
        code_index.docstrings = data.get("docstrings", {})
        code_index.code_structure = data.get("code_structure", {})
        code_index.metadata = data.get("metadata", {})
        if data.get("last_modified"):
            code_index.last_modified = datetime.fromisoformat(data["last_modified"])
        code_index.content_hash = data.get("content_hash")
        return code_index

    def search(
        self, query: str, search_type: str = "semantic", limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search the code index by query string."""
        if not self._indexed:
            self.index_codebase()

        results = []

        if search_type == "exact":
            results.extend(self._search_exact(query))
        elif search_type == "class":
            results.extend(self._search_class(query))
        elif search_type == "function":
            results.extend(self._search_function(query))
        elif search_type == "import":
            results.extend(self._search_import(query))
        else:
            results.extend(self._search_semantic(query))

        results = self._deduplicate_results(results)
        results = self._rank_results(results, query)

        return results[:limit]

    def _search_exact(self, query: str) -> List[Dict[str, Any]]:
        """Exact-match search."""
        results = []

        if query in self.class_index:
            for file_path in self.class_index[query]:
                results.append(
                    {
                        "file_path": file_path,
                        "match_type": "class",
                        "match": query,
                        "context": self._get_context(file_path, "class", query),
                    }
                )

        if query in self.function_index:
            for file_path in self.function_index[query]:
                results.append(
                    {
                        "file_path": file_path,
                        "match_type": "function",
                        "match": query,
                        "context": self._get_context(file_path, "function", query),
                    }
                )

        return results

    def _search_class(self, query: str) -> List[Dict[str, Any]]:
        """Search for a class by name."""
        results = []
        query_lower = query.lower()

        for class_name, file_paths in self.class_index.items():
            if query_lower in class_name.lower():
                for file_path in file_paths:
                    results.append(
                        {
                            "file_path": file_path,
                            "match_type": "class",
                            "match": class_name,
                            "context": self._get_context(
                                file_path, "class", class_name
                            ),
                        }
                    )

        return results

    def _search_function(self, query: str) -> List[Dict[str, Any]]:
        """Search for a function by name."""
        results = []
        query_lower = query.lower()

        for func_name, file_paths in self.function_index.items():
            if query_lower in func_name.lower():
                for file_path in file_paths:
                    results.append(
                        {
                            "file_path": file_path,
                            "match_type": "function",
                            "match": func_name,
                            "context": self._get_context(
                                file_path, "function", func_name
                            ),
                        }
                    )

        return results

    def _search_import(self, query: str) -> List[Dict[str, Any]]:
        """Search for an import by name."""
        results = []
        query_lower = query.lower()

        for module, file_paths in self.import_index.items():
            if query_lower in module.lower():
                for file_path in file_paths:
                    results.append(
                        {
                            "file_path": file_path,
                            "match_type": "import",
                            "match": module,
                            "context": self._get_context(file_path, "import", module),
                        }
                    )

        return results

    def _search_semantic(self, query: str) -> List[Dict[str, Any]]:
        """Semantic search combining multiple strategies."""
        results = []
        query_keywords = self._extract_keywords(query)

        matched_files = set()
        for keyword in query_keywords:
            if keyword in self.keyword_index:
                matched_files.update(self.keyword_index[keyword])

        for file_path in matched_files:
            if file_path in self.file_indices:
                code_index = self.file_indices[file_path]

                for class_info in code_index.classes:
                    if any(kw in class_info["name"].lower() for kw in query_keywords):
                        results.append(
                            {
                                "file_path": file_path,
                                "match_type": "class",
                                "match": class_info["name"],
                                "context": self._get_context(
                                    file_path, "class", class_info["name"]
                                ),
                            }
                        )

                for func_info in code_index.functions:
                    if any(kw in func_info["name"].lower() for kw in query_keywords):
                        results.append(
                            {
                                "file_path": file_path,
                                "match_type": "function",
                                "match": func_info["name"],
                                "context": self._get_context(
                                    file_path, "function", func_info["name"]
                                ),
                            }
                        )

        return results

    def _get_context(
        self, file_path: str, match_type: str, match: str
    ) -> Dict[str, Any]:
        """Return context snippets for a query."""
        if file_path not in self.file_indices:
            return {}

        code_index = self.file_indices[file_path]
        context = {"file_path": file_path, "match_type": match_type, "match": match}

        if match_type == "class":
            for class_info in code_index.classes:
                if class_info["name"] == match:
                    context.update(
                        {
                            "line": class_info.get("line"),  # type: ignore[dict-item]
                            "docstring": class_info.get("docstring"),  # type: ignore[dict-item]
                            "methods": class_info.get("methods", []),
                        }
                    )
                    break
        elif match_type == "function":
            for func_info in code_index.functions:
                if func_info["name"] == match:
                    context.update(
                        {
                            "line": func_info.get("line"),  # type: ignore[dict-item]
                            "docstring": func_info.get("docstring"),  # type: ignore[dict-item]
                            "args": func_info.get("args", []),
                        }
                    )
                    break

        return context

    def _deduplicate_results(
        self, results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Remove duplicate results."""
        seen = set()
        unique_results = []
        for result in results:
            key = (result["file_path"], result["match_type"], result["match"])
            if key not in seen:
                seen.add(key)
                unique_results.append(result)
        return unique_results

    def _rank_results(
        self, results: List[Dict[str, Any]], query: str
    ) -> List[Dict[str, Any]]:
        """Rank results by relevance."""
        query_lower = query.lower()

        def score(result: Dict[str, Any]) -> float:
            """Calculate relevance score for search result."""
            score = 0.0
            match = result.get("match", "").lower()

            if match == query_lower:
                score += 100
            elif query_lower in match:
                score += 50
            elif match in query_lower:
                score += 25

            if result.get("match_type") == "class":
                score += 10

            if result.get("context", {}).get("docstring"):
                score += 5

            return score

        return sorted(results, key=score, reverse=True)

    def get_global_context(self, file_path: Optional[str] = None) -> Dict[str, Any]:
        """Return the global codebase context string."""
        if not self._indexed:
            self.index_codebase()

        context = {
            "total_files": len(self.file_indices),
            "total_classes": sum(
                len(idx.classes) for idx in self.file_indices.values()
            ),
            "total_functions": sum(
                len(idx.functions) for idx in self.file_indices.values()
            ),
            "total_imports": len(self.import_index),
            "top_classes": self._get_top_items(self.class_index, 10),
            "top_functions": self._get_top_items(self.function_index, 10),
            "top_imports": self._get_top_items(self.import_index, 10),
        }

        if file_path and file_path in self.file_indices:
            code_index = self.file_indices[file_path]
            context["file_context"] = {
                "classes": code_index.classes,
                "functions": code_index.functions,
                "imports": code_index.imports,
                "docstrings": code_index.docstrings,
            }

        return context

    def _get_top_items(
        self, index: Dict[str, List[str]], limit: int
    ) -> List[Tuple[str, int]]:
        """Return the most frequent items."""
        items = [(name, len(file_paths)) for name, file_paths in index.items()]
        items.sort(key=lambda x: x[1], reverse=True)
        return items[:limit]


def index_codebase(scope: str = ".", force_reindex: bool = False) -> Dict[str, Any]:
    """Index the full codebase."""
    indexer = CodebaseIndexer(scope=scope)
    indexer.index_codebase(force_reindex=force_reindex)

    return {
        "total_files": len(indexer.file_indices),
        "total_classes": sum(len(idx.classes) for idx in indexer.file_indices.values()),
        "total_functions": sum(
            len(idx.functions) for idx in indexer.file_indices.values()
        ),
        "total_imports": len(indexer.import_index),
        "cache_location": str(indexer._cache_file),
    }


def search_codebase(
    query: str, scope: str = ".", search_type: str = "semantic", limit: int = 20
) -> List[Dict[str, Any]]:
    """Search the indexed codebase and return matches."""
    indexer = CodebaseIndexer(scope=scope)
    return indexer.search(query, search_type=search_type, limit=limit)


def get_global_context(
    scope: str = ".", file_path: Optional[str] = None
) -> Dict[str, Any]:
    """Return the global codebase context string."""
    indexer = CodebaseIndexer(scope=scope)
    return indexer.get_global_context(file_path=file_path)
