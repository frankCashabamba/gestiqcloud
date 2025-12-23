# Desarrollo: Importación de Recetas desde Excel a Base de Datos

## 1. Objetivo

Implementar una **pipeline en Python** que permita:

1. Recibir un archivo Excel con el formato de costeo proporcionado.
2. Parsear cada hoja como una **receta**.
3. Extraer:
   - Datos generales de la receta.
   - Ingredientes requeridos.
   - Materiales o insumos adicionales.
4. Persistir todo en una **base de datos relacional** (PostgreSQL) usando SQLAlchemy.

Este documento describe el diseño técnico y las decisiones de implementación.

---

## 2. Alcance

Incluye:

- Modelo de datos (SQLAlchemy).
- Lógica para leer y parsear el Excel (`openpyxl`).
- Pipeline de importación (`Excel → Objetos Python → BD`).
- Punto de entrada para integración con FastAPI (ejemplo).

No incluye:

- Frontend (React/Vite).
- Gestión de autenticación/autorización.
- UI para seguimiento de imports.

---

## 3. Tecnologías

- **Lenguaje:** Python 3.x
- **ORM:** SQLAlchemy
- **Driver PostgreSQL:** `psycopg2`
- **Lectura Excel:** `openpyxl`
- **Framework web (para integración):** FastAPI (opcional, ver ejemplo en §9)

---

## 4. Modelo de Datos

### 4.1. Tabla `recipes`

Representa la receta principal.

| Campo                       | Tipo              | Descripción                                      |
|----------------------------|-------------------|--------------------------------------------------|
| `id`                       | Integer (PK)      | Identificador de la receta                       |
| `nombre`                   | String            | Nombre de la receta (celda `G3`)                 |
| `clasificacion`            | String            | Clasificación (celda `E4`)                       |
| `tipo_receta`              | String            | Tipo de receta (celda `E5`)                      |
| `origen`                   | String            | Origen (celda `E6`)                              |
| `porciones`                | Integer           | Nº de porciones (celda `E7`)                     |
| `temperatura_servicio`     | String            | Temperatura de servicio (celda `E9`)             |
| `costo_unitario_ingredientes` | Numeric(12,4) | Costo unitario ingredientes (celda `E8`)        |
| `costo_total_ingredientes` | Numeric(12,4)     | Costo total ingredientes (celda en col. S)       |

### 4.2. Tabla `recipe_ingredients`

Detalle de ingredientes requeridos.

| Campo              | Tipo              | Descripción                                                |
|--------------------|-------------------|------------------------------------------------------------|
| `id`               | Integer (PK)      | Identificador                                              |
| `receta_id`        | Integer (FK)      | Referencia a `recipes.id`                                  |
| `nombre`           | String            | Nombre del ingrediente (col. A)                           |
| `cantidad`         | Numeric(12,4)     | Cantidad requerida (col. F)                               |
| `unidad`           | String            | Unidad (gr, ml, etc., col. G)                             |
| `rendimiento_real` | Numeric(12,4)     | Rendimiento Real (col. O)                                 |
| `inversion_insumos`| Numeric(12,4)     | Inversión en insumos (col. Q)                             |
| `costo_fraccion`   | Numeric(12,6)     | Costo por fracción (col. R)                               |
| `importe`          | Numeric(12,4)     | Importe calculado (col. S)                                |

### 4.3. Tabla `recipe_materials`

Materiales o insumos adicionales.

| Campo          | Tipo              | Descripción                                         |
|----------------|-------------------|-----------------------------------------------------|
| `id`           | Integer (PK)      | Identificador                                       |
| `receta_id`    | Integer (FK)      | Referencia a `recipes.id`                           |
| `descripcion`  | String            | Descripción del material (col. A)                  |
| `cantidad`     | Numeric(12,4)     | Cantidad (col. G)                                   |
| `unidad_compra`| String            | Unidad de compra (col. K)                           |
| `precio_compra`| Numeric(12,4)     | Precio de compra (col. Q)                           |
| `costo_unitario`| Numeric(12,6)    | Costo unitario (col. R)                             |
| `importe`      | Numeric(12,4)     | Importe total (col. S)                              |

---

## 5. Reglas de Parseo del Excel

### 5.1. Datos de cabecera (receta)

Se leen de la hoja de cálculo en posiciones fijas:

- `G3` → `nombre`
- `E4` → `clasificacion`
- `E5` → `tipo_receta`
- `E6` → `origen`
- `E7` → `porciones`
- `E8` → `costo_unitario_ingredientes`
- `E9` → `temperatura_servicio`

Para `costo_total_ingredientes`:

1. Buscar la fila donde en la **columna O** exista el texto `"COSTO TOTAL INGREDIENTES"`.
2. En esa fila, leer el valor de la **columna S**.

### 5.2. Tabla “INGREDIENTES REQUERIDOS”

1. Buscar la fila donde en la **columna A** aparezca el texto `"Ingredientes"` (cabecera de tabla).
2. Los datos comienzan en la fila siguiente.

Por cada fila de datos:

- Col. A → `nombre`
- Col. F → `cantidad`
- Col. G → `unidad`
- Col. O → `rendimiento_real`
- Col. Q → `inversion_insumos`
- Col. R → `costo_fraccion`
- Col. S → `importe`

La lectura se detiene cuando la celda de la columna A está vacía.

### 5.3. Tabla “MATERIALES O INSUMOS ADICIONALES”

1. Buscar la fila donde en la **columna A** aparezca el texto `"MATERIALES O INSUMOS ADICIONALES"`.
2. Saltar una fila de cabeceras.
3. Los datos comienzan dos filas después del título.

Por cada fila de datos:

- Col. A → `descripcion`
- Col. G → `cantidad`
- Col. K → `unidad_compra`
- Col. Q → `precio_compra`
- Col. R → `costo_unitario`
- Col. S → `importe`

La lectura se detiene cuando la celda de la columna A está vacía.

---

## 6. Estructura del Código Python

Se propone la siguiente organización de módulos (puedes adaptarla):

```text
app/
  models/
    __init__.py
    recipe.py          # Modelos SQLAlchemy
  services/
    __init__.py
    excel_importer.py  # Lógica de lectura y parseo del Excel
  db.py                # Configuración de SQLAlchemy
  main.py              # Punto de entrada / FastAPI
```

### 6.1. Modelos (`models/recipe.py`)

Contiene las clases:

- `Recipe`
- `RecipeIngredient`
- `RecipeMaterial`

Basadas en `declarative_base()` de SQLAlchemy:

```python
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, Integer, String, Numeric, ForeignKey

Base = declarative_base()

class Recipe(Base):
    __tablename__ = "recipes"
    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)
    # ... resto de campos ...

    ingredientes = relationship(
        "RecipeIngredient",
        back_populates="receta",
        cascade="all, delete-orphan",
    )
    materiales = relationship(
        "RecipeMaterial",
        back_populates="receta",
        cascade="all, delete-orphan",
    )

# RecipeIngredient y RecipeMaterial análogos
```

### 6.2. Configuración BD (`db.py`)

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+psycopg2://user:password@localhost:5432/tu_base"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)
```

### 6.3. Lógica de importación (`services/excel_importer.py`)

Responsabilidades:

- Abrir el Excel con `openpyxl`.
- Iterar por hojas.
- Parsear cabecera, ingredientes y materiales.
- Crear instancias de los modelos y persistirlas.

Funciones principales:

- `to_decimal(value)`
- `find_row(ws, text, col=1)`
- `parse_recipe_header(ws)`
- `parse_ingredients(ws)`
- `parse_materials(ws)`
- `parse_recipe_sheet(ws)`
- `import_workbook_to_db(excel_path: str)`

Ejemplo (versión resumida):

```python
from openpyxl import load_workbook
from decimal import Decimal
from typing import Optional, List, Dict, Tuple

from app.db import SessionLocal, engine
from app.models.recipe import Base, Recipe, RecipeIngredient, RecipeMaterial

def to_decimal(value) -> Optional[Decimal]:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None

def find_row(ws, text: str, col: int = 1) -> Optional[int]:
    text = text.strip().upper()
    for row in range(1, ws.max_row + 1):
        value = ws.cell(row=row, column=col).value
        if isinstance(value, str) and value.strip().upper() == text:
            return row
    return None

# parse_recipe_header, parse_ingredients, parse_materials, parse_recipe_sheet
# (idénticos a los definidos en la implementación)

def import_workbook_to_db(excel_path: str) -> None:
    wb = load_workbook(excel_path, data_only=True)
    session = SessionLocal()
    try:
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]

            # G3 debe tener nombre de receta, si no se ignora la hoja
            if not ws["G3"].value:
                continue

            header, ingredients_data, materials_data = parse_recipe_sheet(ws)

            receta = Recipe(
                nombre=header["nombre"],
                clasificacion=header["clasificacion"],
                tipo_receta=header["tipo_receta"],
                origen=header["origen"],
                porciones=header["porciones"],
                temperatura_servicio=header["temperatura_servicio"],
                costo_unitario_ingredientes=header["costo_unitario_ingredientes"],
                costo_total_ingredientes=header["costo_total_ingredientes"],
            )

            for ing in ingredients_data:
                receta.ingredientes.append(
                    RecipeIngredient(
                        nombre=ing["nombre"],
                        cantidad=ing["cantidad"],
                        unidad=ing["unidad"],
                        rendimiento_real=ing["rendimiento_real"],
                        inversion_insumos=ing["inversion_insumos"],
                        costo_fraccion=ing["costo_fraccion"],
                        importe=ing["importe"],
                    )
                )

            for mat in materials_data:
                receta.materiales.append(
                    RecipeMaterial(
                        descripcion=mat["descripcion"],
                        cantidad=mat["cantidad"],
                        unidad_compra=mat["unidad_compra"],
                        precio_compra=mat["precio_compra"],
                        costo_unitario=mat["costo_unitario"],
                        importe=mat["importe"],
                    )
                )

            session.add(receta)

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

---

## 7. Flujo de Ejecución de la Pipeline

1. **Carga archivo**: se recibe un Excel (ruta en disco o `BytesIO` en un endpoint).
2. **Apertura**: `load_workbook(excel_path, data_only=True)`.
3. **Iteración por hojas**:
   - Si la celda `G3` está vacía, se considera plantilla/hoja vacía → se ignora.
   - Si hay valor, se trata como una receta válida.
4. **Parseo de cabecera**: `parse_recipe_header(ws)`.
5. **Parseo de ingredientes**: `parse_ingredients(ws)`.
6. **Parseo de materiales**: `parse_materials(ws)`.
7. **Construcción de objetos**:
   - Crear instancia `Recipe`.
   - Adjuntar listas de `RecipeIngredient` y `RecipeMaterial`.
8. **Persistencia**:
   - Añadir receta a la sesión.
   - Al final del proceso, `session.commit()`.

En caso de excepción, se hace `rollback()` y se relanza el error.

---

## 8. Integración con FastAPI (Ejemplo)

Ejemplo de endpoint para subir el Excel:

```python
# main.py
from fastapi import FastAPI, UploadFile, File, HTTPException
from tempfile import NamedTemporaryFile
import shutil

from app.services.excel_importer import import_workbook_to_db
from app.models.recipe import Base
from app.db import engine

app = FastAPI()

# Crear tablas al arrancar la app
Base.metadata.create_all(bind=engine)

@app.post("/importar-recetas")
async def importar_recetas(file: UploadFile = File(...)):
    if not file.filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=400, detail="El archivo debe ser Excel (.xlsx/.xlsm)")

    # Guardar a un temporal y reutilizar la función existente
    with NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        import_workbook_to_db(tmp_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error importando Excel: {e}")

    return {"status": "ok", "message": "Importación completada"}
```

---

## 9. Manejo de Errores y Validaciones

- **Validación de formato de archivo**: extensión `.xlsx`/`.xlsm`.
- **Validación de estructura**:
  - Si no se encuentra el texto esperado en las cabeceras (`"Ingredientes"`, `"MATERIALES O INSUMOS ADICIONALES"`, `"COSTO TOTAL INGREDIENTES"`), se puede:
    - Registrar una advertencia (log).
    - Saltar la parte afectada.
    - Opcional: lanzar excepción si se considera crítico.
- **Celdas vacías o tipos incorrectos**:
  - Se usa `to_decimal` para convertir a `Decimal` de forma segura.
  - Valores no convertibles se tratan como `None`.

---

## 10. Pruebas

Se recomienda cubrir:

1. **Pruebas unitarias** de helpers:
   - `to_decimal`
   - `find_row`
   - `parse_recipe_header`
   - `parse_ingredients`
   - `parse_materials`
2. **Pruebas de integración**:
   - Importar un archivo Excel de ejemplo y verificar:
     - Nº de recetas insertadas.
     - Integridad de ingredientes y materiales.
3. **Pruebas de error**:
   - Excel con cabeceras cambiadas o celdas clave vacías.
   - Excel con tipos de datos incorrectos (texto en campos numéricos).

---

## 11. Mejoras Futuras

- Soporte para **versionado** de recetas (guardar histórico de cambios).
- Registro de **usuario** que hizo el import y fecha/hora.
- Validaciones contra catálogos de productos (FK a tabla `productos`).
- Job asíncrono para importar archivos grandes (Celery, RQ, etc.).
- Pantalla de administración para revisar y editar las recetas importadas.

---
