import ast
import json
import os
import pathlib

def get_module_qualname(file_path_str, project_root_str):
    """Converts a file path to a fully qualified module name."""
    file_path = pathlib.Path(file_path_str)
    project_root = pathlib.Path(project_root_str)
    relative_path = file_path.relative_to(project_root)
    parts = list(relative_path.parts)
    if parts[-1] == "__init__.py":
        parts.pop()
    elif parts[-1].endswith(".py"):
        parts[-1] = parts[-1][:-3]
    return ".".join(parts)

def resolve_relative_import(importing_module_qualname, level, module_name_parts):
    """Resolves a relative import to a fully qualified module name."""
    if not importing_module_qualname: # Should not happen if called correctly
        return ".".join(module_name_parts)

    importing_parts = importing_module_qualname.split('.')
    # If the importing module is a package (e.g., 'core' from 'core/__init__.py'),
    # its qualname might already be the package name.
    # If it's a module (e.g., 'core.engine'), we go up one level from the module.
    # For relative imports, the base is the package containing the current module.
    if level > 0:
        base_parts = importing_parts[:-(level -1)] if level > 1 else importing_parts[:-1]


    if not module_name_parts: # e.g. from . import foo
        return ".".join(base_parts)
    else:
        return ".".join(base_parts + module_name_parts)


def analyze_imports(file_path_str, project_root_str, file_lines):
    """Analyzes a single Python file for import statements."""
    dependencies = []
    source_module_qualname = get_module_qualname(file_path_str, project_root_str)
    file_path_relative_to_root = str(pathlib.Path(file_path_str).relative_to(project_root_str))

    try:
        with open(file_path_str, "r", encoding="utf-8") as source_file:
            content = source_file.read()
            tree = ast.parse(content, filename=file_path_str)
    except Exception as e:
        print(f"Error parsing {file_path_str}: {e}")
        return [] # Skip files that can't be parsed

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            original_import_statement = ""
            if hasattr(node, 'lineno') and node.lineno > 0 and node.lineno <= len(file_lines):
                original_import_statement = file_lines[node.lineno - 1].strip()

            for alias in node.names:
                imported_name = alias.name
                dependencies.append({
                    "source_file_path": file_path_relative_to_root,
                    "source_module_qualname": source_module_qualname,
                    "imported_module_qualname": imported_name, # For direct imports, this is the qualname
                    "imported_symbols": [], # Or None, as per spec
                    "import_type": "direct_import",
                    "is_relative": False, # Direct imports are absolute by nature in this context
                    "relative_level": 0,
                    "original_import_statement": original_import_statement or f"import {imported_name}",
                    "line_number": node.lineno
                })
        elif isinstance(node, ast.ImportFrom):
            original_import_statement = ""
            if hasattr(node, 'lineno') and node.lineno > 0 and node.lineno <= len(file_lines):
                original_import_statement = file_lines[node.lineno - 1].strip()

            level = node.level
            is_relative = level > 0
            module_parts = node.module.split('.') if node.module else []

            if is_relative:
                # For 'from . import foo' or 'from ..bar import baz'
                # The source_module_qualname is the importing module, e.g., 'pkg.sub.current_module'
                # If level is 1 (from .), base is 'pkg.sub'
                # If level is 2 (from ..), base is 'pkg'
                importing_qual_parts = source_module_qualname.split('.')
                
                # Determine the base for relative import resolution
                # If source_module_qualname ends with __init__ effectively, it's a package.
                # e.g. if source_file_path is core/__init__.py, source_module_qualname is 'core'
                # if source_file_path is core/engine.py, source_module_qualname is 'core.engine'
                
                path_obj = pathlib.Path(file_path_str)
                is_init_file = path_obj.name == "__init__.py"

                if is_init_file:
                    # 'from .foo' in 'pkg/__init__.py' means 'pkg.foo'
                    # 'from ..foo' in 'pkg/sub/__init__.py' means 'pkg.foo'
                    # base_parts should be the package containing __init__.py, then go up `level` times
                    # if source_module_qualname is 'pkg.sub', level 1 means 'pkg.sub', level 2 means 'pkg'
                    base_qual_parts = importing_qual_parts
                    if level > 0 : # for from . import x, level is 1, base is current package
                                   # for from .. import x, level is 2, base is parent package
                        base_qual_parts = importing_qual_parts[:-(level-1)]


                else: # Not an __init__.py file, e.g. core/engine.py (core.engine)
                      # from .foo -> core.foo
                      # from ..foo -> foo (assuming root is sibling of core)
                    base_qual_parts = importing_qual_parts[:-1] # Start with the package containing the module
                    if level > 1:
                        base_qual_parts = base_qual_parts[:-(level-2)]


                if node.module: # from .module import ...
                    imported_module_qualname = ".".join(base_qual_parts + module_parts)
                else: # from . import ...
                    imported_module_qualname = ".".join(base_qual_parts)

            else: # Absolute import
                imported_module_qualname = node.module if node.module else ""


            imported_symbols = [alias.name for alias in node.names]
            if not imported_symbols and not node.module and level > 0: # from . import X
                 # This case is tricky, if node.module is None, it means "from . import X"
                 # The "imported_module_qualname" should be the resolved path to X
                 # This logic might need refinement based on how ast handles `from . import X` vs `from .X import Y`
                 # For now, let's assume if module is None, it's importing symbols from the resolved relative path
                 pass # imported_module_qualname is already set

            dependencies.append({
                "source_file_path": file_path_relative_to_root,
                "source_module_qualname": source_module_qualname,
                "imported_module_qualname": imported_module_qualname,
                "imported_symbols": imported_symbols,
                "import_type": "from_import",
                "is_relative": is_relative,
                "relative_level": level,
                "original_import_statement": original_import_statement or f"from {'.' * level}{node.module or ''} import {', '.join(imported_symbols)}",
                "line_number": node.lineno
            })
    return dependencies

def main():
    project_root = os.getcwd()
    all_dependencies = []
    file_paths_to_scan = []

    for root, _, files in os.walk(project_root):
        # Skip .venv or venv directories
        if ".venv" in root.split(os.sep) or "venv" in root.split(os.sep) or "node_modules" in root.split(os.sep):
            continue
        for file in files:
            if file.endswith(".py"):
                file_paths_to_scan.append(os.path.join(root, file))

    for file_path in file_paths_to_scan:
        # Read lines once for original_import_statement
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                file_lines = f.readlines()
        except Exception as e:
            print(f"Could not read lines from {file_path}: {e}")
            file_lines = []
        
        # Ensure file_path is absolute for consistency in get_module_qualname and relative_to
        abs_file_path = os.path.abspath(file_path)
        abs_project_root = os.path.abspath(project_root)

        dependencies = analyze_imports(abs_file_path, abs_project_root, file_lines)
        all_dependencies.extend(dependencies)

    output_file = os.path.join(project_root, "import_dependencies_map.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_dependencies, f, indent=4)

    print(f"Dependency map generated: {output_file}")

if __name__ == "__main__":
    main()