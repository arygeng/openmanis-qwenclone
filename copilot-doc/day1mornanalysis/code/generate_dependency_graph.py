import json
import graphviz
from collections import defaultdict

# Define a color palette for different top-level packages
PACKAGE_COLORS = {
    'core': 'lightblue',
    'planner': 'lightgreen',
    'knowledge': 'lightcoral',
    'security': 'lightsalmon',
    'system_integration': 'lightseagreen',
    'tools': 'lightgoldenrodyellow',
    'web_interface': 'lightpink',
    'config': 'lightgray',
    # Add more as needed
    'default': 'whitesmoke' # Default color for packages not in this map
}

def get_node_color(module_qualname):
    """Determines node fill color based on the top-level package."""
    top_level_package = module_qualname.split('.')[0]
    return PACKAGE_COLORS.get(top_level_package, PACKAGE_COLORS['default'])

def generate_graph(dependencies_file, output_dot_file, output_image_file):
    """
    Generates a dependency graph from the given JSON file.
    """
    try:
        with open(dependencies_file, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Dependencies file '{dependencies_file}' not found.")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{dependencies_file}'.")
        return

    adj_list = defaultdict(set)
    all_nodes = set()

    for item in data:
        source_module = item.get('source_module_qualname')
        imported_module = item.get('imported_module_qualname')

        if source_module and imported_module:
            adj_list[source_module].add(imported_module)
            all_nodes.add(source_module)
            all_nodes.add(imported_module)

    # Detect cycle edges using DFS
    path_dfs = []
    recursion_stack = set()
    visited_dfs = set()
    cycled_edges_dfs = set()

    def detect_cycle_edges_dfs(u):
        visited_dfs.add(u)
        recursion_stack.add(u)
        path_dfs.append(u)

        for v in adj_list.get(u, []):
            if v not in visited_dfs:
                detect_cycle_edges_dfs(v)
            elif v in recursion_stack:  # Cycle detected
                try:
                    # Mark the back edge
                    cycled_edges_dfs.add((path_dfs[-1], v))
                    # Mark other edges in the cycle path
                    start_index = path_dfs.index(v)
                    for i in range(start_index, len(path_dfs) - 1):
                        cycled_edges_dfs.add((path_dfs[i], path_dfs[i+1]))
                except ValueError:
                    # This should ideally not happen if logic is correct
                    pass
        
        if path_dfs: # Ensure path_dfs is not empty before pop
             path_dfs.pop()
        if u in recursion_stack: # Ensure u is in recursion_stack before remove
            recursion_stack.remove(u)

    for node in list(all_nodes): # Iterate over a copy
        if node not in visited_dfs:
            detect_cycle_edges_dfs(node)

    dot = graphviz.Digraph(comment='Module Import Dependencies', engine='dot')
    dot.attr(rankdir='LR', size='20,20', overlap='false', splines='true', ratio='auto', concentrate='true')

    # Add nodes
    for node_name in all_nodes:
        fill_color = get_node_color(node_name)
        node_attrs = {'style': 'filled', 'fillcolor': fill_color, 'shape': 'box'}
        
        is_node_in_cycle = False
        for s, t in cycled_edges_dfs:
            if s == node_name or t == node_name:
                is_node_in_cycle = True
                break
        if is_node_in_cycle:
            node_attrs['color'] = 'red' # Border color for nodes in cycles
            node_attrs['penwidth'] = '2.0'

        dot.node(node_name, label=node_name, **node_attrs)

    # Add edges
    for source_module, imported_modules in adj_list.items():
        for imported_module in imported_modules:
            edge_attrs = {}
            if (source_module, imported_module) in cycled_edges_dfs:
                edge_attrs['color'] = 'red'
                edge_attrs['penwidth'] = '2.0'
            dot.edge(source_module, imported_module, **edge_attrs)

    try:
        # Save .dot source file
        with open(output_dot_file, 'w') as f:
            f.write(dot.source)
        print(f"Saved DOT source to {output_dot_file}")

        # Render to PNG
        base_output_filename = output_image_file.replace('.png', '')
        dot.render(filename=base_output_filename, directory='.', format='png', cleanup=True)
        print(f"Saved PNG image to {output_image_file}")

    except Exception as e:
        print(f"Error during graph rendering or saving: {e}")
        print("Please ensure Graphviz (both the Python library and the command-line tools) is installed and in your system's PATH.")
        print("  Python library: pip install graphviz")
        print("  Command-line tools (examples):")
        print("    Debian/Ubuntu: sudo apt-get install graphviz")
        print("    macOS (Homebrew): brew install graphviz")
        print("    Windows: Download from graphviz.org and add to PATH.")

if __name__ == "__main__":
    dependencies_json_file = 'import_dependencies_map.json'
    graph_dot_output = 'import_dependency_graph.dot'
    graph_png_output = 'import_dependency_graph.png'

    print(f"Generating dependency graph from '{dependencies_json_file}'...")
    generate_graph(dependencies_json_file, graph_dot_output, graph_png_output)
    print("Graph generation process finished.")