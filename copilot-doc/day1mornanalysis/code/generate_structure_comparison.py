import json
import re
import os

IMPORT_MAP_PATH = "import_dependencies_map.json"
PLANNING_DOC_PATH = "manus-ai-clone-docs/development_planning/phase1_detailed_implementation.md"
OUTPUT_DOC_PATH = "module_structure_comparison.md"
TARGET_FILE_FOR_ANALYSIS = "core/engine.py"

def load_json_data(file_path):
    """Loads JSON data from a file."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found - {file_path}")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from - {file_path}")
        return None

def get_import_details_from_map(import_map_data, source_file, original_import_stmt_to_find):
    """
    Searches import_map_data for line_number and actual import statement.
    The original_import_stmt_to_find is stripped of leading/trailing whitespace for comparison.
    """
    if not import_map_data:
        return None
    
    normalized_stmt_to_find = original_import_stmt_to_find.strip()
    for item in import_map_data:
        if item.get('source_file_path') == source_file:
            # Normalize the statement from the map as well for a more robust comparison
            map_stmt = item.get('original_import_statement', '').strip()
            if map_stmt == normalized_stmt_to_find:
                return {
                    'line_number': item.get('line_number', "N/A"),
                    'original_import_statement': item.get('original_import_statement', original_import_stmt_to_find) # Return the exact form from map
                }
    return None

def parse_planning_doc(file_path):
    """
    Extracts the "Expected Issues" for core/engine.py from the planning document.
    Returns a list of dicts: {'current_broken_import': str, 'comment': str}
    """
    issues = []
    try:
        with open(file_path, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: Planning document not found - {file_path}")
        return issues

    # Regex to find the section and then the import lines
    # This regex assumes the section starts with a specific header and imports follow.
    # It captures the import statement (group 1) and the comment (group 2).
    section_header = r"# Current broken imports in core/engine.py:"
    import_line_regex = r"^\s*(from\s+[\w\.\*]+\s+import\s+[\w\s,\*\(\)]+(?:\s+as\s+\w+)?)\s*#\s*(.*)$"

    in_section = False
    for line in content.splitlines():
        if section_header in line:
            in_section = True
            continue
        
        if in_section:
            if line.strip().startswith("#") and not re.match(import_line_regex, line): # Stop if it's a comment not matching format or new header
                 # Or if line is empty, or another header starts
                if not line.strip() or (line.strip().startswith("#") and not re.search(r"import", line)):
                    break # End of relevant section
            
            match = re.match(import_line_regex, line)
            if match:
                issues.append({
                    'current_broken_import': match.group(1).strip(),
                    'comment': match.group(2).strip()
                })
            elif not line.strip(): # Allow empty lines within the section
                continue
            elif line.strip() and not line.strip().startswith("from "): # If it's not an import and not empty, section might be over
                # This condition might need refinement based on actual doc structure
                pass # Continue scanning in case of intermittent non-import lines that are not section breaks

    if not issues:
        print(f"Warning: No issues extracted from {file_path} for {TARGET_FILE_FOR_ANALYSIS}. Check section header and format.")
    return issues

def derive_comparison_fields(current_broken_import_from_doc, comment):
    """
    Derives 'problem_identified', 'required_import', 'source_notes'
    based on the comment from the planning document.
    """
    problem_identified = "Problem details not fully derived from comment."
    required_import = current_broken_import_from_doc # Default
    source_notes = f"Per `phase1_detailed_implementation.md`: \"Expected Issues\". Comment: \"{comment}\"."

    # Case 1: Planner -> TaskPlanner
    if "from planner.planner import Planner" in current_broken_import_from_doc and "Should be: TaskPlanner" in comment:
        problem_identified = "Incorrect module name and/or class name."
        required_import = "from planner.task_planner import TaskPlanner"
        source_notes = "Per `phase1_detailed_implementation.md`: \"Expected Issues\". `Planner` should be `TaskPlanner` from `planner.task_planner`."
    
    # Case 2: MemorySystem missing
    elif "from knowledge.memory_system import MemorySystem" in current_broken_import_from_doc and "Module missing" in comment:
        problem_identified = "Module `knowledge.memory_system` is missing."
        required_import = "from knowledge.memory_system import MemorySystem" # Required is the same, but noted as missing
        source_notes = "Per `phase1_detailed_implementation.md`: \"Expected Issues\". Module planned for Day 3-4. A stub might be needed."

    # Case 3: ToolInterface -> ToolAdapter
    elif "from tools.tool_interface import ToolInterface" in current_broken_import_from_doc and "Should be: ToolAdapter" in comment:
        problem_identified = "Class name `ToolInterface` should be `ToolAdapter`."
        # Attempt to reconstruct the import statement
        match = re.match(r"from\s+([\w\.]+)\s+import\s+([\w]+)", current_broken_import_from_doc)
        if match:
            module_path = match.group(1)
            required_import = f"from {module_path} import ToolAdapter"
        else: # Fallback if regex fails
            required_import = "from tools.tool_interface import ToolAdapter" 
        source_notes = "Per `phase1_detailed_implementation.md`: \"Expected Issues\". `ToolAdapter` class expected in `tools/tool_interface.py`."
    
    # Add more generic handling if needed, or rely on the default for unhandled comments.
    # For now, the specific cases from the prompt are handled.

    return {
        'problem_identified': problem_identified,
        'required_import': required_import,
        'source_notes': source_notes
    }

def main():
    import_map_data = load_json_data(IMPORT_MAP_PATH)
    if import_map_data is None:
        print(f"Halting script due to issues loading {IMPORT_MAP_PATH}")
        return

    parsed_issues = parse_planning_doc(PLANNING_DOC_PATH)
    if not parsed_issues:
        print(f"No issues to process from {PLANNING_DOC_PATH}. {OUTPUT_DOC_PATH} will not be generated with specific issues.")
        # Still create the header, but the file will be mostly empty of issues.
        # Or decide to halt if no issues. For now, let's create the header.
    
    output_markdown_parts = [f"## Comparison for {TARGET_FILE_FOR_ANALYSIS}\n"]

    if not parsed_issues:
         output_markdown_parts.append("\nNo specific problematic imports for `core/engine.py` were found or parsed from the planning document.")


    for issue in parsed_issues:
        current_broken_import_from_doc = issue['current_broken_import']
        comment = issue['comment']

        line_num_display = "N/A"
        actual_import_to_display = current_broken_import_from_doc # Default

        details_from_map = get_import_details_from_map(
            import_map_data,
            TARGET_FILE_FOR_ANALYSIS,
            current_broken_import_from_doc
        )
        
        if details_from_map:
            line_num_display = str(details_from_map.get('line_number', "N/A"))
            actual_import_to_display = details_from_map.get('original_import_statement', current_broken_import_from_doc)
        else:
            # Note that it wasn't found in the map, line_num_display remains N/A
            # actual_import_to_display remains the one from the planning doc
            # The prompt says: "If the exact problematic import isn't found, state that."
            # This is implicitly handled by LNUM being N/A and current import being from doc.
            # We can add an explicit note if desired, e.g. in line_num_display
            line_num_display = "N/A (Not found in import_dependencies_map.json for this exact statement)"


        derived_fields = derive_comparison_fields(current_broken_import_from_doc, comment)

        entry = f"""---
**File Path:** {TARGET_FILE_FOR_ANALYSIS}
**Line No.:** {line_num_display}
**Current Import Statement / Module Usage:** {actual_import_to_display}
**Problem Identified:** {derived_fields['problem_identified']}
**Required Import Statement / Module Usage:** {derived_fields['required_import']}
**Source of Requirement / Notes:** {derived_fields['source_notes']}
---"""
        output_markdown_parts.append(entry)

    try:
        with open(OUTPUT_DOC_PATH, 'w') as f:
            f.write("\n".join(output_markdown_parts))
        print(f"Successfully generated {OUTPUT_DOC_PATH}")
    except IOError:
        print(f"Error: Could not write to output file - {OUTPUT_DOC_PATH}")

if __name__ == "__main__":
    main()