#!/usr/bin/env python3
"""
Validador de variables de entorno críticas para Gestiqcloud
Verifica que no hay fallbacks a localhost en producción
"""

import os
import sys
from typing import List, Tuple

# Variables CRÍTICAS que deben estar siempre configuradas
CRITICAL_VARS = {
    "DEFAULT_FROM_EMAIL": {
        "description": "Email from para notificaciones",
        "must_not_contain": ["localhost"],
        "example": "no-reply@gestiqcloud.com"
    },
    "REDIS_URL": {
        "description": "URL de conexión a Redis",
        "must_not_contain": ["localhost", "127.0.0.1"],
        "example": "redis://cache.internal:6379/1"
    },
    "CORS_ORIGINS": {
        "description": "Origins permitidos (CSRF protection)",
        "must_not_contain": ["localhost", "127.0.0.1"],
        "example": "https://www.gestiqcloud.com,https://admin.gestiqcloud.com"
    },
    "DATABASE_URL": {
        "description": "URL de base de datos",
        "must_not_contain": ["localhost", "127.0.0.1"],
        "example": "postgresql://user:pass@postgres.internal/gestiqcloud"
    },
}

# Variables MODERADAS con defaults acceptables
MODERATE_VARS = {
    "VITE_API_URL": {
        "description": "API URL para frontend",
        "must_not_contain": ["localhost"],
        "example": "https://api.gestiqcloud.com/api/v1"
    },
    "VITE_ELECTRIC_URL": {
        "description": "ElectricSQL WebSocket URL",
        "must_not_contain": ["localhost"],
        "example": "ws://electric.internal:3000"
    },
    "CERT_PASSWORD": {
        "description": "Contraseña del certificado (e-invoicing)",
        "must_not_contain": ["CERT_PASSWORD", "TODO"],
        "example": "[desde AWS Secrets Manager]"
    }
}

class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

def check_var(name: str, config: dict, is_critical: bool = True) -> Tuple[bool, str]:
    """
    Valida una variable de entorno
    Retorna (es_válida, mensaje)
    """
    value = os.getenv(name, "")
    severity = "CRÍTICA" if is_critical else "MODERADA"
    
    if not value:
        msg = f"❌ {severity}: {name} no está configurada"
        return False, msg
    
    # Validar que no contiene valores prohibidos
    for forbidden in config.get("must_not_contain", []):
        if forbidden.lower() in value.lower():
            msg = f"❌ {severity}: {name} contiene '{forbidden}' (inválido en producción)"
            return False, msg
    
    msg = f"✅ {name} configurada correctamente"
    return True, msg

def validate_environment(env_type: str = "production") -> bool:
    """
    Valida el entorno
    env_type: 'production', 'staging', 'development'
    """
    print(f"\n{Colors.BOLD}🔍 Validando entorno: {env_type}{Colors.END}\n")
    
    all_valid = True
    
    # Validar variables críticas
    print(f"{Colors.BOLD}═══ Variables CRÍTICAS ═══{Colors.END}")
    for var_name, config in CRITICAL_VARS.items():
        is_valid, msg = check_var(var_name, config, is_critical=True)
        if is_valid:
            print(f"{Colors.GREEN}{msg}{Colors.END}")
        else:
            print(f"{Colors.RED}{msg}{Colors.END}")
            all_valid = False
        print(f"   📝 {config['description']}")
        print(f"   💡 Ejemplo: {config['example']}\n")
    
    # Validar variables moderadas
    if env_type == "production":
        print(f"{Colors.BOLD}═══ Variables MODERADAS ═══{Colors.END}")
        for var_name, config in MODERATE_VARS.items():
            is_valid, msg = check_var(var_name, config, is_critical=False)
            if is_valid:
                print(f"{Colors.GREEN}{msg}{Colors.END}")
            else:
                print(f"{Colors.YELLOW}{msg}{Colors.END}")
            print(f"   📝 {config['description']}\n")
    
    # Resumen
    print(f"{Colors.BOLD}═══ RESUMEN ═══{Colors.END}")
    if all_valid:
        print(f"{Colors.GREEN}✅ Todas las variables críticas están bien configuradas{Colors.END}\n")
        return True
    else:
        print(f"{Colors.RED}❌ Hay variables críticas no configuradas o mal configuradas{Colors.END}\n")
        return False

def print_checklist():
    """Imprime checklist de validación"""
    print(f"\n{Colors.BOLD}📋 CHECKLIST de Validación{Colors.END}\n")
    
    checklist_items = [
        ("DEFAULT_FROM_EMAIL", "no es localhost", os.getenv("DEFAULT_FROM_EMAIL", "").count("localhost") == 0),
        ("REDIS_URL", "no es localhost", os.getenv("REDIS_URL", "").count("localhost") == 0),
        ("CORS_ORIGINS", "no contiene localhost", os.getenv("CORS_ORIGINS", "").count("localhost") == 0),
        ("DATABASE_URL", "no es localhost", os.getenv("DATABASE_URL", "").count("localhost") == 0),
        ("VITE_API_URL", "configurada", bool(os.getenv("VITE_API_URL", ""))),
        ("VITE_ELECTRIC_URL", "configurada", bool(os.getenv("VITE_ELECTRIC_URL", ""))),
        ("CERT_PASSWORD", "no es placeholder", "TODO" not in os.getenv("CERT_PASSWORD", "")),
    ]
    
    all_ok = True
    for var_name, description, is_ok in checklist_items:
        symbol = "✅" if is_ok else "❌"
        color = Colors.GREEN if is_ok else Colors.RED
        print(f"{color}{symbol} {var_name}{Colors.END}: {description}")
        if not is_ok:
            all_ok = False
    
    return all_ok

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Validador de variables de entorno para Gestiqcloud"
    )
    parser.add_argument(
        "--env",
        choices=["production", "staging", "development"],
        default="development",
        help="Tipo de entorno a validar"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Modo estricto (falla con exit code 1 si hay problemas)"
    )
    
    args = parser.parse_args()
    
    print(f"\n{Colors.BOLD}🔧 Gestiqcloud - Validador de Entorno{Colors.END}")
    print(f"Versión: 1.0\n")
    
    # Validar
    is_valid = validate_environment(args.env)
    
    # Checklist
    checklist_ok = print_checklist()
    
    # Resultado final
    print(f"\n{Colors.BOLD}═══ RESULTADO FINAL ═══{Colors.END}")
    if is_valid and checklist_ok:
        print(f"{Colors.GREEN}✅ Entorno validado correctamente para {args.env}{Colors.END}\n")
        return 0
    else:
        print(f"{Colors.RED}❌ Entorno tiene problemas para {args.env}{Colors.END}\n")
        if args.strict:
            return 1
        else:
            print(f"{Colors.YELLOW}⚠️  Ejecute con --strict para fallar en validación{Colors.END}\n")
            return 0

if __name__ == "__main__":
    sys.exit(main())
