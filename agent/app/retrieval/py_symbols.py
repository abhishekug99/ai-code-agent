import ast
from typing import Dict, List, Any, Optional


def _safe_parse(code: str) -> Optional[ast.AST]:
    try:
        return ast.parse(code)
    except Exception:
        return None


def extract_python_summary(code: str) -> Dict[str, Any]:
    """
    Extracts lightweight signals:
    - top-level classes/functions
    - imports
    - fastapi-style route decorators/calls (heuristic)
    """
    tree = _safe_parse(code)
    if tree is None:
        return {"classes": [], "functions": [], "imports": [], "routes": []}

    classes: List[str] = []
    functions: List[str] = []
    imports: List[str] = []
    routes: List[str] = []

    # imports
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                imports.append(n.name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            for n in node.names:
                imports.append(f"{mod}.{n.name}" if mod else n.name)

    # top-level defs
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            classes.append(node.name)
        elif isinstance(node, ast.FunctionDef):
            functions.append(node.name)
        elif isinstance(node, ast.AsyncFunctionDef):
            functions.append(node.name)

    # FastAPI-ish heuristic: look for decorator like @router.get("/path")
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                # decorator could be a call like router.get("/x")
                if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                    if dec.func.attr in {"get", "post", "put", "delete", "patch"}:
                        path_arg = None
                        if dec.args and isinstance(dec.args[0], ast.Constant) and isinstance(dec.args[0].value, str):
                            path_arg = dec.args[0].value
                        routes.append(f"{dec.func.attr.upper()} {path_arg or '(unknown)'} -> {node.name}")

    # de-dupe + limit
    def uniq(xs: List[str], limit: int) -> List[str]:
        out = []
        seen = set()
        for x in xs:
            if x in seen:
                continue
            seen.add(x)
            out.append(x)
            if len(out) >= limit:
                break
        return out

    return {
        "classes": uniq(classes, 50),
        "functions": uniq(functions, 50),
        "imports": uniq(imports, 80),
        "routes": uniq(routes, 80),
    }
