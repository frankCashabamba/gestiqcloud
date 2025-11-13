#!/usr/bin/env python3
"""
Script para arreglar errores comunes de linting automáticamente
"""

import re
from pathlib import Path


def fix_bare_except(file_path):
    """Arregla bare except statements"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Reemplazar except: con except Exception:
    content = re.sub(r'\n(\s+)except:\s*\n', r'\n\1except Exception:\n', content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"[OK] Fixed bare except in {file_path}")


def fix_true_comparisons(file_path):
    """Arregla comparaciones con True"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Reemplazar == True con is True (mejor aún, removerlo si es booleano)
    # Patrón: .field == True → .field
    content = re.sub(r'(\w+)\.(\w+)\s*==\s*True\b', r'\1.\2', content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"[OK] Fixed True comparisons in {file_path}")


def remove_unused_variables(file_path):
    """Comenta o remueve variables no usadas comunes"""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    new_lines = []
    for line in lines:
        # Si es una variable no usada común, prefijamos con _
        if re.match(r'\s+(\w+)\s*=\s*', line):
            var_name = re.match(r'\s+(\w+)\s*=\s*', line).group(1)
            if var_name in ['tenant_uuid', 'rotacion', 'total', 'job_data', 'original_available', 
                           'whatsapp_channel_id', 'telegram_channel_id', 'patterns', 'in_duplicate',
                           'result', 'class_pattern', 'applied_any', 'signed_xml', 'db']:
                line = line.replace(f'{var_name} =', f'_{var_name} =')
        new_lines.append(line)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print(f"[OK] Prefixed unused variables in {file_path}")


def add_missing_imports(file_path):
    """Añade imports faltantes comunes"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Mapa de nombres no definidos a sus imports
    import_map = {
        'UploadFile': 'from fastapi import UploadFile',
        'MovimientoTipo': 'from app.models.banking import MovimientoTipo',
        'BankAccount': 'from app.models.banking import BankAccount',
        'BankTransaction': 'from app.models.banking import BankTransaction',
        'Cliente': 'from app.models.clientes import Cliente',
        'Invoice': 'from app.models.invoices import Invoice',
        'Empresa': 'from app.models.empresa.tenant import Empresa',
        'tenant_id_from_request': 'from app.core.authz import tenant_id_from_request',
        'request': '',  # Este debe estar en parámetros de función
    }
    
    # Buscar nombres no definidos y añadir imports al inicio
    imports_to_add = set()
    for name, import_stmt in import_map.items():
        if name in content and import_stmt and import_stmt not in content:
            imports_to_add.add(import_stmt)
    
    if imports_to_add:
        # Encontrar el final de los imports existentes
        lines = content.split('\n')
        import_end = 0
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                import_end = i + 1
        
        # Insertar nuevos imports
        for imp in sorted(imports_to_add):
            lines.insert(import_end, imp)
            import_end += 1
        
        content = '\n'.join(lines)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"[OK] Added missing imports to {file_path}")


def fix_import_order(file_path):
    """Mueve imports al principio del archivo"""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Separar docstring, imports y código
    docstring_lines = []
    import_lines = []
    code_lines = []
    
    in_docstring = False
    docstring_done = False
    i = 0
    
    # Procesar docstring inicial si existe
    while i < len(lines):
        line = lines[i]
        if not docstring_done:
            if '"""' in line or "'''" in line:
                docstring_lines.append(line)
                if line.count('"""') == 2 or line.count("'''") == 2:
                    docstring_done = True
                    i += 1
                    break
                else:
                    in_docstring = not in_docstring
                    if not in_docstring:
                        docstring_done = True
                        i += 1
                        break
            elif line.startswith('#!'):
                docstring_lines.append(line)
            elif not line.strip():
                docstring_lines.append(line)
            else:
                docstring_done = True
                break
        i += 1
    
    # Procesar resto del archivo
    while i < len(lines):
        line = lines[i]
        if line.startswith('import ') or line.startswith('from '):
            import_lines.append(line)
        else:
            code_lines.append(line)
        i += 1
    
    # Reconstruir archivo
    new_content = ''.join(docstring_lines) + '\n' + ''.join(import_lines) + '\n' + ''.join(code_lines)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"[OK] Fixed import order in {file_path}")


def main():
    project_root = Path(__file__).parent.parent
    backend_path = project_root / 'apps' / 'backend'
    
    # Lista de archivos con problemas específicos
    files_to_fix = {
        'bare_except': [
            backend_path / 'app/modules/imports/extractores/extractor_desconocido.py',
            backend_path / 'app/modules/imports/extractores/extractor_transferencia.py',
            backend_path / 'app/modules/imports/interface/http/tenant.py',
            backend_path / 'app/routers/products.py',
            backend_path / 'app/modules/productos/interface/http/tenant.py',
        ],
        'true_comparisons': [
            backend_path / 'app/modules/modulos/infrastructure/repositories.py',
            backend_path / 'app/routers/router_admins.py',
            backend_path / 'app/routers/incidents.py',
            backend_path / 'app/modules/imports/interface/http/tenant.py',
        ],
    }
    
    print("Arreglando errores de linting...\n")
    
    # Arreglar bare except
    print("Arreglando bare except statements...")
    for file_path in files_to_fix['bare_except']:
        if file_path.exists():
            fix_bare_except(file_path)
    
    # Arreglar comparaciones con True
    print("\nArreglando comparaciones con True...")
    for file_path in files_to_fix['true_comparisons']:
        if file_path.exists():
            fix_true_comparisons(file_path)
    
    print("\nCorrecciones completadas!")
    print("\nEjecuta 'ruff check' para verificar errores restantes")


if __name__ == '__main__':
    main()
