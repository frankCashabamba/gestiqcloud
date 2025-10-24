"""
Importador Excel SPEC-1 - Específico para archivo 22-10-20251.xlsx

Mapeo según SPEC-1 líneas 182-248:
- REGISTRO → daily_inventory
- compras → purchase (si tiene datos reales)
- LECHE → milk_record (si tiene datos reales)
"""
import hashlib
import logging
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID

import pandas as pd
from sqlalchemy.orm import Session

from app.models.core.products import Product
from app.models.spec1.daily_inventory import DailyInventory
from app.models.spec1.purchase import Purchase
from app.models.spec1.milk_record import MilkRecord
from app.models.spec1.import_log import ImportLog
from app.models.spec1.sale import SaleHeader, SaleLine

logger = logging.getLogger(__name__)


class ExcelImporterSPEC1:
    """Importador Excel para SPEC-1"""
    
    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.stats = {
            "products_created": 0,
            "products_updated": 0,
            "daily_inventory_created": 0,
            "daily_inventory_updated": 0,
            "purchases_created": 0,
            "milk_records_created": 0,
            "sales_created": 0,
            "stock_items_initialized": 0,
            "stock_moves_created": 0,
            "errors": [],
            "warnings": [],
        }
    
    def extract_date_from_filename(self, filename: str) -> Optional[date]:
        """
        Extraer fecha del nombre del archivo
        Formatos: dd-mm-aaaa, dd mm aaaa, dd_mm_aaaa
        """
        # Quitar extensión
        name = filename.replace(".xlsx", "").replace(".xls", "")
        
        # Buscar patrón dd-mm-aaaa o variantes
        pattern = r"(\d{1,2})[\s\-_](\d{1,2})[\s\-_](\d{4})"
        match = re.search(pattern, name)
        
        if match:
            day, month, year = match.groups()
            try:
                return date(int(year), int(month), int(day))
            except ValueError:
                logger.warning(f"Fecha inválida en nombre: {filename}")
                return None
        
        return None
    
    def normalize_text(self, value: Any) -> Optional[str]:
        """Normalizar texto (trim, casing)"""
        if pd.isna(value):
            return None
        return str(value).strip()
    
    def normalize_number(self, value: Any) -> Optional[Decimal]:
        """Normalizar número (coma→punto, decimales)"""
        if pd.isna(value):
            return None
        
        # Convertir a string y limpiar
        s = str(value).strip().replace(",", ".")
        
        try:
            return Decimal(s)
        except Exception:
            return None
    
    def get_or_create_product(
        self,
        name: str,
        unit: str = "unidad",
        prefix_if_new: str = "[IMP]",
    ) -> Product:
        """Obtener o crear producto por nombre"""
        # Buscar existente (case-insensitive)
        product = (
            self.db.query(Product)
            .filter(
                Product.tenant_id == self.tenant_id,
                Product.name.ilike(name.strip()),
            )
            .first()
        )
        
        if product:
            return product
        
        # Crear nuevo
        product = Product(
            tenant_id=self.tenant_id,
            name=f"{prefix_if_new} {name}".strip() if prefix_if_new else name,
            unit=unit,
            price=0,
            stock=0,
        )
        
        self.db.add(product)
        self.db.flush()  # Para obtener el ID
        
        self.stats["products_created"] += 1
        logger.info(f"Producto creado: {product.name}")
        
        return product
    
    def import_registro_sheet(
        self,
        df: pd.DataFrame,
        fecha: date,
        filename: str,
        simulate_sales: bool = True,
    ) -> None:
        """
        Importar hoja REGISTRO → daily_inventory + sale_* (opcional)
        
        Columnas esperadas:
        - PRODUCTO
        - CANTIDAD (stock_inicial)
        - VENTA DIARIA (venta_unidades)
        - SOBRANTE DIARIO (stock_final)
        - PRECIO UNITARIO VENTA
        - TOTAL (ignorado, se recalcula)
        """
        logger.info(f"Importando hoja REGISTRO: {len(df)} filas")
        
        for idx, row in df.iterrows():
            try:
                # Extraer campos
                producto_name = self.normalize_text(row.get("PRODUCTO"))
                cantidad = self.normalize_number(row.get("CANTIDAD"))
                venta = self.normalize_number(row.get("VENTA DIARIA", row.get("VENTA_DIARIA")))
                sobrante = self.normalize_number(row.get("SOBRANTE DIARIO", row.get("SOBRANTE_DIARIO")))
                precio = self.normalize_number(row.get("PRECIO UNITARIO VENTA", row.get("PRECIO_UNITARIO_VENTA")))
                
                # Validar campos obligatorios
                if not producto_name:
                    self.stats["warnings"].append(f"Fila {idx}: Producto vacío")
                    continue
                
                # Producto
                product = self.get_or_create_product(producto_name)
                
                # Calcular digest para idempotencia
                row_str = f"{producto_name}|{fecha}|{cantidad}|{venta}|{sobrante}|{precio}"
                digest = hashlib.sha256(row_str.encode()).digest()
                
                # DailyInventory (upsert)
                existing_inv = (
                    self.db.query(DailyInventory)
                    .filter(
                        DailyInventory.tenant_id == self.tenant_id,
                        DailyInventory.product_id == product.id,
                        DailyInventory.fecha == fecha,
                    )
                    .first()
                )
                
                if existing_inv:
                    # Actualizar
                    existing_inv.stock_inicial = cantidad or Decimal("0")
                    existing_inv.venta_unidades = venta or Decimal("0")
                    existing_inv.stock_final = sobrante or Decimal("0")
                    existing_inv.precio_unitario_venta = precio
                    existing_inv.import_digest = digest
                    self.stats["daily_inventory_updated"] += 1
                else:
                    # Crear
                    inventory = DailyInventory(
                        tenant_id=self.tenant_id,
                        product_id=product.id,
                        fecha=fecha,
                        stock_inicial=cantidad or Decimal("0"),
                        venta_unidades=venta or Decimal("0"),
                        stock_final=sobrante or Decimal("0"),
                        precio_unitario_venta=precio,
                        source_file=filename,
                        source_row=int(idx) + 2,  # +2 por header y 0-index
                        import_digest=digest,
                        created_at=date.today(),
                    )
                    self.db.add(inventory)
                    self.stats["daily_inventory_created"] += 1
                
                # Import Log
                log = ImportLog(
                    tenant_id=self.tenant_id,
                    source_file=filename,
                    sheet="REGISTRO",
                    source_row=int(idx) + 2,
                    entity="daily_inventory",
                    entity_id=product.id,  # Temporal, se actualizará después del commit
                    digest=digest,
                    created_at=datetime.utcnow(),
                )
                self.db.add(log)
                
                # INTEGRACIÓN ERP: Inicializar stock real
                self._init_stock_items(product.id, cantidad or Decimal("0"))
                
                # INTEGRACIÓN ERP: Registrar venta histórica si existe
                if venta and venta > 0:
                    self._create_historical_sale_move(
                        product_id=product.id,
                        qty=venta,
                        fecha=fecha,
                        ref=f"HIST_{filename}_{idx}"
                    )
                
                # Simular venta para reportes (opcional)
                if simulate_sales and venta and venta > 0 and precio:
                    self.create_simulated_sale(
                        product_id=product.id,
                        qty=venta,
                        price=precio,
                        fecha=fecha,
                        ref=f"REGISTRO_{filename}_{idx}",
                    )
            
            except Exception as e:
                self.stats["errors"].append(f"Fila {idx}: {str(e)}")
                logger.error(f"Error en fila {idx}: {e}")
                continue
    
    def create_simulated_sale(
        self,
        product_id: UUID,
        qty: Decimal,
        price: Decimal,
        fecha: date,
        ref: str,
        tax_pct: Decimal = Decimal("12"),  # IVA Ecuador default
    ) -> None:
        """Crear venta simulada desde inventario"""
        # Calcular totales
        subtotal = qty * price
        tax = subtotal * (tax_pct / Decimal("100"))
        total = subtotal + tax
        
        # SaleHeader
        sale = SaleHeader(
            tenant_id=self.tenant_id,
            fecha=fecha,
            customer_name="Consumidor Final (Simulado)",
            total=total,
            total_tax=tax,
            payment_method="Efectivo",
            created_at=fecha,
        )
        self.db.add(sale)
        self.db.flush()
        
        # SaleLine
        line = SaleLine(
            sale_id=sale.id,
            product_id=product_id,
            qty=qty,
            price=price,
            tax_pct=tax_pct,
            total_line=total,
            created_at=fecha,
        )
        self.db.add(line)
        
        self.stats["sales_created"] += 1
    
    def _init_stock_items(self, product_id: UUID, qty: Decimal) -> None:
        """
        Inicializar stock_items con cantidad del Excel (stock inicial)
        Integración con ERP: Pobla la tabla stock_items
        """
        from sqlalchemy import text
        
        # Buscar almacén principal del tenant
        warehouse_query = text("""
            SELECT id FROM warehouses
            WHERE tenant_id = :tenant_id AND is_default = true
            LIMIT 1
        """)
        
        warehouse = self.db.execute(
            warehouse_query,
            {"tenant_id": str(self.tenant_id)}
        ).fetchone()
        
        if not warehouse:
            logger.warning(f"No default warehouse for tenant {self.tenant_id}, skipping stock init")
            return
        
        warehouse_id = warehouse[0]
        
        # Inicializar stock_items con CANTIDAD del Excel
        # Si ya existe, actualiza. Si no, crea.
        upsert_query = text("""
            INSERT INTO stock_items (tenant_id, warehouse_id, product_id, qty)
            VALUES (:tenant_id, :warehouse_id, :product_id, :qty)
            ON CONFLICT (tenant_id, warehouse_id, product_id)
            DO UPDATE SET qty = EXCLUDED.qty
        """)
        
        self.db.execute(
            upsert_query,
            {
                "tenant_id": str(self.tenant_id),
                "warehouse_id": warehouse_id,
                "product_id": product_id,
                "qty": float(qty)
            }
        )
        
        self.stats["stock_items_initialized"] += 1
        logger.debug(f"Stock inicializado: product={product_id}, qty={qty}")
    
    def _create_historical_sale_move(
        self,
        product_id: UUID,
        qty: Decimal,
        fecha: date,
        ref: str
    ) -> None:
        """
        Crear movimiento histórico de venta del Excel
        Esto registra la VENTA DIARIA como un stock_move
        """
        from sqlalchemy import text
        
        # Buscar almacén principal
        warehouse_query = text("""
            SELECT id FROM warehouses
            WHERE tenant_id = :tenant_id AND is_default = true
            LIMIT 1
        """)
        
        warehouse = self.db.execute(
            warehouse_query,
            {"tenant_id": str(self.tenant_id)}
        ).fetchone()
        
        if not warehouse:
            logger.warning(f"No default warehouse, skipping historical sale move")
            return
        
        warehouse_id = warehouse[0]
        
        # Crear stock_move de tipo 'sale' (salida = negativo)
        insert_query = text("""
            INSERT INTO stock_moves (
                tenant_id, product_id, warehouse_id, qty, kind, 
                ref_type, ref_id, posted_at, created_at
            )
            VALUES (
                :tenant_id, :product_id, :warehouse_id, :qty, 'sale',
                'historical', :ref_id, NOW(), NOW()
            )
        """)
        
        self.db.execute(
            insert_query,
            {
                "tenant_id": str(self.tenant_id),
                "product_id": product_id,
                "warehouse_id": warehouse_id,
                "qty": float(-qty),  # NEGATIVO (salida)
                "ref_id": ref
            }
        )
        
        # Actualizar stock_items restando la venta histórica
        update_query = text("""
            UPDATE stock_items
            SET qty = qty - :qty_sold
            WHERE tenant_id = :tenant_id 
              AND warehouse_id = :warehouse_id
              AND product_id = :product_id
        """)
        
        self.db.execute(
            update_query,
            {
                "tenant_id": str(self.tenant_id),
                "warehouse_id": warehouse_id,
                "product_id": product_id,
                "qty_sold": float(qty)
            }
        )
        
        self.stats["stock_moves_created"] += 1
        logger.debug(f"Historical sale move created: product={product_id}, qty={qty}")
    
    def import_file(
        self,
        file_path: str,
        fecha_manual: Optional[date] = None,
        simulate_sales: bool = True,
    ) -> dict:
        """
        Importar archivo Excel completo
        
        Args:
            file_path: Ruta al archivo
            fecha_manual: Fecha manual (si no se puede extraer del nombre)
            simulate_sales: Simular ventas desde REGISTRO
        
        Returns:
            dict con estadísticas
        """
        logger.info(f"Iniciando importación: {file_path}")
        
        # Extraer fecha
        filename = file_path.split("/")[-1].split("\\")[-1]
        fecha = self.extract_date_from_filename(filename)
        
        if not fecha:
            if fecha_manual:
                fecha = fecha_manual
            else:
                raise ValueError(
                    f"No se pudo extraer fecha del nombre '{filename}' "
                    "y no se proporcionó fecha_manual"
                )
        
        logger.info(f"Fecha del lote: {fecha}")
        
        # Leer Excel
        try:
            excel_file = pd.ExcelFile(file_path)
            sheets = excel_file.sheet_names
            logger.info(f"Hojas encontradas: {sheets}")
        except Exception as e:
            self.stats["errors"].append(f"Error leyendo Excel: {str(e)}")
            return self.stats
        
        # Importar REGISTRO
        if "REGISTRO" in sheets:
            df_registro = pd.read_excel(file_path, sheet_name="REGISTRO")
            self.import_registro_sheet(df_registro, fecha, filename, simulate_sales)
        else:
            self.stats["warnings"].append("Hoja 'REGISTRO' no encontrada")
        
        # Commit
        try:
            self.db.commit()
            logger.info("Importación completada con éxito")
        except Exception as e:
            self.db.rollback()
            self.stats["errors"].append(f"Error al guardar: {str(e)}")
            logger.error(f"Error al guardar: {e}")
        
        return self.stats
