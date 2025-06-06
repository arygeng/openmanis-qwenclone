import json
import re
from collections import defaultdict

def build_graph(dependencies):
    """Builds a directed graph from dependency data."""
    graph = defaultdict(list)
    nodes = set()
    for dep in dependencies:
        source = dep["source_module_qualname"]
        imported = dep["imported_module_qualname"]
        if source and imported: # Ensure both source and imported are not None or empty
            graph[source].append(imported)
            nodes.add(source)
            nodes.add(imported)
    return graph, nodes

def find_cycles_util(graph, node, visited, recursion_stack, path, cycles):
    """Utility function for DFS-based cycle detection."""
    visited[node] = True
    recursion_stack[node] = True
    path.append(node)

    for neighbor in graph.get(node, []):
        if not visited.get(neighbor, False):
            find_cycles_util(graph, neighbor, visited, recursion_stack, path, cycles)
        elif recursion_stack.get(neighbor, False):
            # Cycle detected
            cycle_start_index = path.index(neighbor)
            cycles.append(list(path[cycle_start_index:] + [neighbor])) # Add neighbor to complete the cycle path visually

    path.pop()
    recursion_stack[node] = False

def find_all_cycles(graph, nodes):
    """Finds all unique cycles in a directed graph."""
    visited = {node: False for node in nodes}
    recursion_stack = {node: False for node in nodes}
    cycles = []
    
    for node in nodes:
        if not visited.get(node, False):
            find_cycles_util(graph, node, visited, recursion_stack, [], cycles)
            
    # Deduplicate cycles (considering different starting points of the same cycle)
    unique_cycles_set = set()
    unique_cycles_list = []
    for cycle in cycles:
        # Normalize the cycle by starting with the smallest node (lexicographically)
        # to ensure that cycles like A->B->C->A and B->C->A->B are treated as the same.
        # For this, we find the smallest element and rotate the list.
        # The last element is a repeat of the first to show the cycle, so we ignore it for normalization.
        cycle_to_normalize = cycle[:-1]
        if not cycle_to_normalize: # Skip empty or single-node self-loops if not desired
            continue
        
        min_node = min(cycle_to_normalize)
        min_index = cycle_to_normalize.index(min_node)
        normalized_cycle_nodes = tuple(cycle_to_normalize[min_index:] + cycle_to_normalize[:min_index])
        
        if normalized_cycle_nodes not in unique_cycles_set:
            unique_cycles_set.add(normalized_cycle_nodes)
            # Reconstruct the display string for the report
            unique_cycles_list.append(" -> ".join(list(normalized_cycle_nodes) + [normalized_cycle_nodes[0]]))
            
    return unique_cycles_list

def parse_expected_issues(markdown_content):
    """Parses the 'Expected Issues' section from the markdown file."""
    issues = []
    # Regex to find the python code block under "Expected Issues:"
    # It looks for the start of the section, then the python code block.
    match = re.search(r"# Expected Issues:[\s\n]*```python\n(# Current broken imports in core/engine.py:\n)?(.*?)```", markdown_content, re.DOTALL | re.MULTILINE)
    if match:
        # The actual import lines are in the second capturing group.
        # If the comment line is present, it's part of the capture, so we adjust.
        content_block = match.group(2)
        lines = content_block.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith("#") or not line: # Skip comments and empty lines
                continue

            # Example line: from planner.planner import Planner  # Should be: TaskPlanner
            # Example line: from knowledge.memory_system import MemorySystem  # Module missing
            parts = line.split("#", 1)
            problematic_import = parts[0].strip()
            
            expected_info = ""
            if len(parts) > 1:
                expected_info = parts[1].strip()

            issues.append({
                "file": "core/engine.py", # As per the problem description
                "problematic_import": problematic_import,
                "expected": expected_info
            })
    return issues

def check_dependency_conflicts(dependencies_map, expected_issues):
    """Checks for dependency conflicts based on expected issues."""
    conflict_results = []

    # Create a quick lookup for dependencies by source file and import statement
    imports_by_file = defaultdict(set)
    for dep in dependencies_map:
        # Key in map is "source_file_path", not "source_file"
        # Key in map is "import_type", not "import_statement_type"
        # dep["imported_module_qualname"] is the module (e.g., "planner.planner")
        # dep["imported_symbols"] is a list (e.g., ["Planner"])

        source_file_path = dep["source_file_path"] # Correct key
        reconstructed_import = ""

        if dep["import_type"] == "from_import":
            # problematic_import format: "from module.name import Symbol"
            # dep["imported_module_qualname"] = "module.name"
            # dep["imported_symbols"] = ["Symbol"] (or ["Symbol", "Another"])
            if dep["imported_symbols"]:
                # The problematic issues in markdown are single imports.
                # We will check against the first symbol.
                # If "from x import y, z" is in map, and problematic is "from x import y", this will match.
                reconstructed_import = f"from {dep['imported_module_qualname']} import {dep['imported_symbols'][0]}"
            # else: # e.g. "from . import foo" - map has imported_module_qualname as resolved path to package, symbols as ["foo"]
                  # This case is less likely to match the specific problematic_import strings.
                  # For "from . import foo" in "pkg/mod.py", map might have:
                  # imported_module_qualname: "pkg", imported_symbols: ["foo"]
                  # reconstructed: "from pkg import foo" - this is not "from . import foo"
                  # However, the problematic imports are explicit like "from planner.planner import Planner"

        elif dep["import_type"] == "direct_import":
            reconstructed_import = f"import {dep['imported_module_qualname']}"
            # Problematic imports are "from..." so this branch won't match them.

        # Only consider imports from core/engine.py for conflict checking as per instructions
        if source_file_path == "core/engine.py" and reconstructed_import:
             imports_by_file[source_file_path].add(reconstructed_import)


    for issue in expected_issues:
        target_file = issue["file"] # e.g. "core/engine.py"
        problematic_import_str = issue["problematic_import"]
        
        found_in_map = False
        # Check if the problematic_import_str exists for the target_file
        # The `imports_by_file` keys are actual file paths like "core/engine.py"
        if problematic_import_str in imports_by_file.get(target_file, set()):
            found_in_map = True
        
        status_message = f"Problematic import '{problematic_import_str}' "
        if found_in_map:
            status_message += f"WAS FOUND in `{target_file}` in `import_dependencies_map.json`."
        else:
            status_message += f"was NOT FOUND in `{target_file}` in `import_dependencies_map.json`."

        if "Module missing" in issue["expected"]:
            status_message += " (Module is expected to be missing)."
            
        conflict_results.append({
            "file": target_file,
            "problematic_import": problematic_import_str,
            "expected": issue["expected"],
            "status": status_message
        })
        
    return conflict_results

def generate_markdown_report(cycles, conflicts, output_path="circular_imports_and_conflicts.md"):
    """Generates a markdown report of the analysis."""
    with open(output_path, "w") as f:
        f.write("# Dependency Analysis Report\n\n")
        
        f.write("## Circular Imports\n\n")
        if cycles:
            for cycle_path_str in cycles:
                f.write(f"*   `{cycle_path_str}`\n")
        else:
            f.write("*   No circular imports detected.\n")
        f.write("\n")
        
        f.write("## Dependency Conflicts and Missing Modules\n\n")
        f.write("(Based on `manus-ai-clone-docs/development_planning/phase1_detailed_implementation.md`)\n\n")
        
        # Group conflicts by file for the report
        conflicts_by_file = defaultdict(list)
        for conflict in conflicts:
            conflicts_by_file[conflict["file"]].append(conflict)
            
        for file_path, file_conflicts in conflicts_by_file.items():
            f.write(f"*   **File:** `{file_path}`\n")
            for conflict in file_conflicts:
                f.write(f"    *   **Problematic Import Found:** `{conflict['problematic_import']}`\n")
                f.write(f"    *   **Expected/Correct Import:** `{conflict['expected']}`\n")
                f.write(f"    *   **Status:** {conflict['status']}\n")
            f.write("\n") # Add a newline after each file's section for better readability

def main():
    dependencies_file = "import_dependencies_map.json"
    markdown_file_path = "manus-ai-clone-docs/development_planning/phase1_detailed_implementation.md"
    report_output_file = "circular_imports_and_conflicts.md"

    # 1. Load Dependency Data
    try:
        with open(dependencies_file, "r") as f:
            dependencies_map = json.load(f)
    except FileNotFoundError:
        print(f"Error: Dependency map file '{dependencies_file}' not found.")
        # Create an empty report indicating the prerequisite is missing
        with open(report_output_file, "w") as f_report:
            f_report.write("# Dependency Analysis Report\n\n")
            f_report.write(f"**ERROR:** Prerequisite file `{dependencies_file}` not found. Analysis cannot proceed.\n")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{dependencies_file}'.")
        with open(report_output_file, "w") as f_report:
            f_report.write("# Dependency Analysis Report\n\n")
            f_report.write(f"**ERROR:** Could not decode JSON from `{dependencies_file}`. Analysis cannot proceed.\n")
        return

    # 2. Build Dependency Graph
    # We need qualnames for graph nodes as per instructions
    # The map contains "source_module_qualname" and "imported_module_qualname"
    graph, nodes = build_graph(dependencies_map)

    # 3. Detect Circular Imports
    # Ensure nodes passed to find_all_cycles are the ones actually in the graph keys/values
    actual_graph_nodes = set(graph.keys())
    for imp_list in graph.values():
        for imp_node in imp_list:
            actual_graph_nodes.add(imp_node)
    
    circular_imports = find_all_cycles(graph, actual_graph_nodes)

    # 4. Parse Expected Issues from Markdown
    try:
        with open(markdown_file_path, "r", encoding="utf-8") as md_file:
            markdown_content = md_file.read()
    except FileNotFoundError:
        print(f"Error: Markdown file '{markdown_file_path}' not found.")
        # Proceed with cycle detection but note missing conflict analysis
        expected_issues = [] # No issues to check against
        # Add a note to the report if possible, or handle this in generate_markdown_report
        # For now, we'll let it generate the report with an empty conflict section if md is missing.
    else:
        expected_issues = parse_expected_issues(markdown_content)

    # 5. Identify Dependency Conflicts
    dependency_conflicts = check_dependency_conflicts(dependencies_map, expected_issues)
    
    # 6. Generate Markdown Report
    generate_markdown_report(circular_imports, dependency_conflicts, report_output_file)
    
    print(f"Analysis complete. Report generated: '{report_output_file}'")

if __name__ == "__main__":
    main()