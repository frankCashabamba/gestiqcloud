"""
Importador genérico de productos + stock desde Excel/CSV
Para poblar catálogo de productos y stock inicial en el ERP
"""
from __future__ import annotations

import hashlib
import logging
from decimal import Decimal
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from app.models.core.producto import Producto
from app.models.inventory.stock import StockItem

logger = logging.getLogger(__name__)


class ProductsImporter:
    """
    Importador genérico para poblar catálogo de productos + stock inicial.
    
    Formato esperado Excel/CSV:
    - PRODUCTO / NOMBRE / NAME (obligatorio)
    - CANTIDAD / STOCK / QTY (opcional, default 0)
    - PRECIO / PRICE / PRECIO_VENTA (opcional)
    - CATEGORIA / CATEGORY (opcional)
    - CODIGO / SKU / CODE (opcional)
    
    Uso:
        importer = ProductsImporter(db, tenant_id)
        result = importer.import_from_excel("productos.xlsx", sheet_name="Catalogo")
    """
    
    def __init__(
        self,
        db: Session,
        tenant_id: str,
        warehouse_id: str | None = None,
    ):
        self.db = db
        self.tenant_id = tenant_id
        self.warehouse_id = warehouse_id or "default"
        self.stats = {
            "products_created": 0,
            "products_updated": 0,
            "products_skipped": 0,
            "stock_initialized": 0,
            "errors": [],
            "warnings": [],
        }
    
    def import_from_excel(
        self,
        file_path: str,
        sheet_name: str = "Hoja1",
        update_existing: bool = False,
    ) -> dict[str, Any]:
        """
        Importa productos desde Excel.
        
        Args:
            file_path: Ruta al archivo Excel
            sheet_name: Nombre de la hoja a importar
            update_existing: Si True, actualiza productos existentes
        
        Returns:
            Diccionario con estadísticas de importación
        """
        try:
            # Leer Excel
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            logger.info(f"Leyendo {len(df)} filas de {file_path}:{sheet_name}")
            
            # Normalizar nombres de columnas
            df.columns = df.columns.str.strip().str.upper()
            
            # Detectar columnas
            name_col = self._detect_column(df, ["PRODUCTO", "NOMBRE", "NAME"])
            qty_col = self._detect_column(df, ["CANTIDAD", "STOCK", "QTY"])
            price_col = self._detect_column(df, ["PRECIO", "PRICE", "PRECIO_VENTA", "PRECIO UNITARIO VENTA"])
            code_col = self._detect_column(df, ["CODIGO", "SKU", "CODE"])
            category_col = self._detect_column(df, ["CATEGORIA", "CATEGORY"])
            
            if not name_col:
                raise ValueError("No se encontró columna de nombre de producto (PRODUCTO/NOMBRE/NAME)")
            
            # Procesar cada fila
            for idx, row in df.iterrows():
                try:
                    self._process_row(
                        row,
                        name_col=name_col,
                        qty_col=qty_col,
                        price_col=price_col,
                        code_col=code_col,
                        category_col=category_col,
                        update_existing=update_existing,
                    )
                except Exception as e:
                    self.stats["errors"].append(f"Fila {idx + 2}: {str(e)}")
                    logger.error(f"Error en fila {idx + 2}: {e}")
            
            self.db.commit()
            logger.info(f"Importación completada: {self.stats}")
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error en importación: {e}")
            raise
        
        return self.stats
    
    def _detect_column(self, df: pd.DataFrame, candidates: list[str]) -> str | None:
        """Detecta la primera columna que coincida con los candidatos."""
        for col in df.columns:
            if col in candidates:
                return col
        return None
    
    def _process_row(
        self,
        row: pd.Series,
        name_col: str,
        qty_col: str | None,
        price_col: str | None,
        code_col: str | None,
        category_col: str | None,
        update_existing: bool,
    ) -> None:
        """Procesa una fila del Excel."""
        # Extraer datos
        name = self._normalize_text(row.get(name_col))
        if not name or name.upper() in ["TOTAL", "SUBTOTAL", ""]:
            self.stats["products_skipped"] += 1
            return
        
        qty = self._normalize_number(row.get(qty_col)) if qty_col else Decimal("0")
        price = self._normalize_number(row.get(price_col)) if price_col else None
        code = self._normalize_text(row.get(code_col)) if code_col else None
        category = self._normalize_text(row.get(category_col)) if category_col else None
        
        # Buscar producto existente por nombre
        existing = (
            self.db.query(Producto)
            .filter(
                Producto.tenant_id == self.tenant_id,
                Producto.nombre.ilike(name),
            )
            .first()
        )
        
        if existing:
            if update_existing:
                # Actualizar producto
                if price is not None:
                    existing.precio_venta = price
                if code:
                    existing.codigo = code
                if category:
                    existing.categoria = category
                self.stats["products_updated"] += 1
                product = existing
            else:
                self.stats["products_skipped"] += 1
                self.stats["warnings"].append(f"Producto '{name}' ya existe, omitido")
                return
        else:
            # Crear producto nuevo
            product = Producto(
                tenant_id=self.tenant_id,
                nombre=name,
                codigo=code,
                precio_venta=price or Decimal("0"),
                categoria=category,
                activo=True,
            )
            self.db.add(product)
            self.db.flush()  # Para obtener el ID
            self.stats["products_created"] += 1
        
        # Inicializar stock si qty > 0
        if qty and qty > 0:
            self._init_stock(product.id, qty)
    
    def _init_stock(self, product_id: str, qty: Decimal) -> None:
        """Inicializa stock de un producto."""
        existing_stock = (
            self.db.query(StockItem)
            .filter(
                StockItem.tenant_id == self.tenant_id,
                StockItem.product_id == product_id,
                StockItem.warehouse_id == self.warehouse_id,
            )
            .first()
        )
        
        if existing_stock:
            existing_stock.qty_on_hand = qty
        else:
            stock = StockItem(
                tenant_id=self.tenant_id,
                product_id=product_id,
                warehouse_id=self.warehouse_id,
                qty_on_hand=qty,
            )
            self.db.add(stock)
        
        self.stats["stock_initialized"] += 1
    
    @staticmethod
    def _normalize_text(value: Any) -> str | None:
        """Normaliza texto."""
        if pd.isna(value) or value is None:
            return None
        text = str(value).strip()
        return text if text else None
    
    @staticmethod
    def _normalize_number(value: Any) -> Decimal | None:
        """Normaliza número."""
        if pd.isna(value) or value is None or value == "":
            return None
        try:
            # Limpiar string
            if isinstance(value, str):
                value = value.replace(",", ".").strip()
                # Ignorar fórmulas de Excel
                if value.startswith("="):
                    return None
            return Decimal(str(value))
        except (ValueError, TypeError):
            return None
