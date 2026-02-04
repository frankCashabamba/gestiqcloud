#!/usr/bin/env python3
"""
Script to find remaining Spanish identifiers in Python and TypeScript files.
Helps track refactoring progress for English consistency.
"""

import os
import re
from pathlib import Path
from collections import defaultdict

# Spanish patterns to search for
SPANISH_PATTERNS = {
    "function_defs": r"^def\s+(buscar|extraer|detectar|limpiar|corregir|dividir|calcular|normalizar|es_)\w*",
    "variable_names": r"\b(pagina|bloque|fecha|importe|cliente|concepto|categoria|emisor|beneficiario|cuenta|referencia|etiqueta)\b",
    "comments_spanish": r"#.*[áéíóúñ¿¡]",
    "docstrings_spanish": r'"""[^"]*[áéíóúñ][^"]*"""',
    "constants": r"^[A-Z_]+\s*=",
}

SPANISH_KEYWORDS = {
    "buscar", "extraer", "detectar", "limpiar", "corregir",
    "dividir", "calcular", "normalizar", "procesar",
    "pagina", "bloque", "fecha", "importe", "cliente",
    "concepto", "categoria", "emisor", "beneficiario",
    "cuenta", "referencia", "etiqueta", "tipo",
}

def scan_file(filepath):
    """Scan a single file for Spanish identifiers."""
    issues = defaultdict(list)
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        return issues
    
    for line_num, line in enumerate(lines, 1):
        # Skip comments and strings in some cases
        stripped = line.strip()
        
        # Check for function definitions with Spanish names
        if "def " in line:
            for match in re.finditer(r'def\s+(\w+)', line):
                func_name = match.group(1)
                if any(keyword in func_name for keyword in SPANISH_KEYWORDS):
                    issues["spanish_functions"].append((line_num, func_name, line.rstrip()))
        
        # Check for variables
        if "=" in line and not line.strip().startswith("#"):
            for word in SPANISH_KEYWORDS:
                if re.search(rf'\b{word}\b', line):
                    issues["spanish_variables"].append((line_num, word, line.rstrip()))
        
        # Check for Spanish comments (very basic)
        if "#" in line:
            comment = line.split("#", 1)[1]
            if any(char in comment for char in "áéíóúñ¿¡"):
                issues["spanish_comments"].append((line_num, comment[:50].strip()))
    
    return issues

def find_all_spanish_files(root_path, exclude_dirs=None):
    """Find all Python and TypeScript files that may need refactoring."""
    if exclude_dirs is None:
        exclude_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', '.pytest_cache'}
    
    results = defaultdict(lambda: defaultdict(list))
    
    for root, dirs, files in os.walk(root_path):
        # Remove excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            if file.endswith(('.py', '.ts', '.tsx')):
                filepath = os.path.join(root, file)
                issues = scan_file(filepath)
                
                if issues:
                    rel_path = os.path.relpath(filepath, root_path)
                    results[rel_path] = issues
    
    return results

def print_report(results):
    """Print a formatted report of findings."""
    if not results:
        print("✅ No Spanish identifiers found!")
        return
    
    print(f"🔍 Found Spanish identifiers in {len(results)} files:\n")
    
    for filepath, issues in sorted(results.items()):
        print(f"📄 {filepath}")
        
        if issues.get("spanish_functions"):
            print("  Functions to rename:")
            for line_num, func_name, line in issues["spanish_functions"]:
                print(f"    Line {line_num}: {func_name}")
        
        if issues.get("spanish_variables"):
            print("  Variables to rename:")
            for line_num, var_name, line in issues["spanish_variables"]:
                print(f"    Line {line_num}: {var_name}")
        
        if issues.get("spanish_comments"):
            print("  Comments to translate:")
            for line_num, comment in issues["spanish_comments"][:3]:
                print(f"    Line {line_num}: {comment}...")
        
        print()

def main():
    """Main execution."""
    import sys
    
    # Determine root path
    if len(sys.argv) > 1:
        root_path = sys.argv[1]
    else:
        root_path = "."
    
    print(f"🔎 Scanning {root_path} for Spanish identifiers...\n")
    
    results = find_all_spanish_files(root_path)
    print_report(results)
    
    # Summary
    total_files = len(results)
    total_issues = sum(
        len(v) for issues in results.values() for v in issues.values()
    )
    
    print(f"📊 Summary:")
    print(f"  Files with Spanish identifiers: {total_files}")
    print(f"  Total issues found: {total_issues}")

if __name__ == "__main__":
    main()
