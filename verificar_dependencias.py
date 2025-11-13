#!/usr/bin/env python3
"""Script para verificar las dependencias del importador OCR."""

import sys


def check_dependency(name: str, import_name: str = None):
    """Verifica si una dependencia está instalada."""
    import_name = import_name or name
    try:
        module = __import__(import_name)
        version = getattr(module, "__version__", "OK")
        print(f"✅ {name}: {version}")
        return True
    except ImportError:
        print(f"❌ {name}: NO INSTALADO")
        return False


print("=" * 60)
print("VERIFICACIÓN DE DEPENDENCIAS PARA IMPORTADOR OCR")
print("=" * 60)

all_ok = True

# Dependencias críticas
print("\n📦 Dependencias Críticas:")
all_ok &= check_dependency("PyMuPDF", "fitz")
all_ok &= check_dependency("Pytesseract", "pytesseract")
all_ok &= check_dependency("OpenCV", "cv2")
all_ok &= check_dependency("Pillow (PIL)", "PIL")

# Dependencias opcionales
print("\n📦 Dependencias Opcionales:")
check_dependency("EasyOCR", "easyocr")
check_dependency("Pyzbar (QR)", "pyzbar")

# Verificar configuración de Tesseract
print("\n🔧 Configuración de Tesseract:")
try:
    import io

    import pytesseract
    from PIL import Image

    # Crear imagen de prueba
    test_img = Image.new("RGB", (100, 30), color="white")

    # Intentar ejecutar Tesseract
    try:
        pytesseract.get_tesseract_version()
        print("✅ Tesseract ejecutable encontrado y funcional")
    except Exception as e:
        print("⚠️ Tesseract instalado pero no encontrado en PATH:")
        print(f"   Error: {e}")
        print("\n   Solución en Windows:")
        print("   1. Descarga: https://github.com/UB-Mannheim/tesseract/wiki")
        print("   2. Instala en: C:\\Program Files\\Tesseract-OCR\\")
        print("   3. Agrega al PATH o configura:")
        print(
            "      pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'"
        )
except ImportError:
    print("⚠️ No se puede verificar Tesseract (pytesseract no instalado)")

print("\n" + "=" * 60)
if all_ok:
    print("✅ TODAS LAS DEPENDENCIAS CRÍTICAS INSTALADAS")
else:
    print("❌ FALTAN DEPENDENCIAS CRÍTICAS")
    print("\nInstala las faltantes con:")
    print("  pip install PyMuPDF pytesseract opencv-python Pillow")
    sys.exit(1)

print("=" * 60)
