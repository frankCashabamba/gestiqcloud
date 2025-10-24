"""
Servicio de Backflush - Consumo automático de materia prima al vender producto terminado

Según SPEC-1 líneas 584-596: al vender un producto terminado (FG) que tiene BOM,
se descuentan automáticamente las materias primas (RM) según la receta.
"""
import logging
from decimal import Decimal
from typing import Optional
from uuid import UUID
from datetime import datetime, date

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.core.products import Product, Recipe, RecipeIngredient
from app.models.inventory.stock_moves import StockMove
from app.models.inventory.warehouses import Warehouse

logger = logging.getLogger(__name__)


class BackflushService:
    """Servicio para backflush (consumo automático de MP)"""
    
    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id
    
    def execute_backflush(
        self,
        product_id: UUID,
        qty_sold: Decimal,
        ref_doc_type: str = "sale",
        ref_doc_id: Optional[UUID] = None,
        warehouse_id: Optional[int] = None,
    ) -> dict:
        """
        Ejecutar backflush para un producto vendido
        
        Args:
            product_id: UUID del producto terminado vendido
            qty_sold: Cantidad vendida
            ref_doc_type: Tipo de documento origen ('sale', 'pos_receipt')
            ref_doc_id: UUID del documento origen
            warehouse_id: ID del almacén (opcional, usa principal si no se especifica)
        
        Returns:
            dict con resumen: {consumed: [], warnings: []}
        """
        result = {
            "consumed": [],
            "warnings": [],
        }
        
        # Buscar el producto
        product = (
            self.db.query(Product)
            .filter(
                and_(
                    Product.id == product_id,
                    Product.tenant_id == self.tenant_id,
                )
            )
            .first()
        )
        
        if not product:
            result["warnings"].append(f"Producto {product_id} no encontrado")
            return result
        
        # Verificar si tiene receta (BOM)
        recipe = (
            self.db.query(Recipe)
            .filter(Recipe.product_id == product_id)
            .first()
        )
        
        if not recipe:
            logger.warning(f"Producto {product.sku or product.name} no tiene BOM definida - sin backflush")
            result["warnings"].append(f"Producto sin BOM: {product.sku or product.name}")
            return result
        
        # Obtener almacén (principal si no se especifica)
        if not warehouse_id:
            warehouse = (
                self.db.query(Warehouse)
                .filter(
                    and_(
                        Warehouse.tenant_id == self.tenant_id,
                        Warehouse.is_default == True,
                    )
                )
                .first()
            )
            warehouse_id = warehouse.id if warehouse else None
        
        if not warehouse_id:
            result["warnings"].append("No se encontró almacén principal")
            return result
        
        # Aplicar merma si está definida
        merma_pct = Decimal("0")  # recipe.merma_pct si existiera en el modelo
        factor_merma = Decimal("1") + (merma_pct / Decimal("100"))
        
        # Iterar ingredientes de la receta
        ingredients = (
            self.db.query(RecipeIngredient)
            .filter(RecipeIngredient.recipe_id == recipe.id)
            .all()
        )
        
        for ingredient in ingredients:
            # Cantidad a consumir = qty_por_unidad * qty_sold * (1 + merma%)
            qty_to_consume = (
                Decimal(str(ingredient.quantity)) * qty_sold * factor_merma
            )
            
            # Crear movimiento de stock (CONSUME)
            stock_move = StockMove(
                tenant_id=self.tenant_id,
                kind="consume",
                product_id=ingredient.product_id,
                warehouse_id=warehouse_id,
                qty=qty_to_consume,
                ref_doc_type=ref_doc_type,
                ref_doc_id=ref_doc_id,
                posted_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
            )
            
            self.db.add(stock_move)
            
            # Obtener nombre del producto RM
            rm_product = (
                self.db.query(Product)
                .filter(Product.id == ingredient.product_id)
                .first()
            )
            
            rm_name = rm_product.name if rm_product else str(ingredient.product_id)
            
            result["consumed"].append({
                "product_id": str(ingredient.product_id),
                "product_name": rm_name,
                "qty": float(qty_to_consume),
                "unit": ingredient.unit,
            })
            
            logger.info(
                f"Backflush: Consumido {qty_to_consume} {ingredient.unit} "
                f"de {rm_name} para producir {qty_sold} {product.name}"
            )
        
        # Commit de todos los movimientos
        try:
            self.db.commit()
            logger.info(f"Backflush completado: {len(result['consumed'])} ingredientes consumidos")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error en backflush: {e}")
            result["warnings"].append(f"Error al guardar movimientos: {str(e)}")
        
        return result
    
    def execute_backflush_for_sale_lines(
        self,
        sale_lines: list,
        warehouse_id: Optional[int] = None,
    ) -> dict:
        """
        Ejecutar backflush para múltiples líneas de venta
        
        Args:
            sale_lines: Lista de líneas de venta con product_id y qty
            warehouse_id: ID del almacén
        
        Returns:
            dict con resumen agregado
        """
        result = {
            "total_products": 0,
            "total_consumed": 0,
            "details": [],
            "warnings": [],
        }
        
        for line in sale_lines:
            product_id = line.get("product_id") or line.get("product")
            qty = line.get("qty") or line.get("cantidad")
            ref_doc_id = line.get("sale_id") or line.get("id")
            
            if not product_id or not qty:
                continue
            
            backflush_result = self.execute_backflush(
                product_id=product_id,
                qty_sold=Decimal(str(qty)),
                ref_doc_type="sale",
                ref_doc_id=ref_doc_id,
                warehouse_id=warehouse_id,
            )
            
            result["total_products"] += 1
            result["total_consumed"] += len(backflush_result["consumed"])
            result["details"].append({
                "product_id": str(product_id),
                "qty_sold": float(qty),
                "consumed": backflush_result["consumed"],
            })
            result["warnings"].extend(backflush_result["warnings"])
        
        return result


def execute_backflush_for_pos_receipt(
    db: Session,
    tenant_id: UUID,
    receipt_id: UUID,
    warehouse_id: Optional[int] = None,
) -> dict:
    """
    Helper para ejecutar backflush desde un POS receipt
    
    Args:
        db: Sesión de base de datos
        tenant_id: UUID del tenant
        receipt_id: UUID del recibo POS
        warehouse_id: ID del almacén
    
    Returns:
        dict con resumen del backflush
    """
    from app.models.pos.receipts import POSReceipt, POSItem
    
    # Obtener receipt y sus líneas
    receipt = (
        db.query(POSReceipt)
        .filter(
            and_(
                POSReceipt.id == receipt_id,
                POSReceipt.tenant_id == tenant_id,
            )
        )
        .first()
    )
    
    if not receipt:
        return {"warnings": [f"Receipt {receipt_id} no encontrado"]}
    
    # Obtener líneas del receipt
    items = (
        db.query(POSItem)
        .filter(POSItem.receipt_id == receipt.id)
        .all()
    )
    
    if not items:
        return {"warnings": ["Receipt sin líneas"]}
    
    # Convertir a formato para backflush
    sale_lines = [
        {
            "product_id": item.product_id,
            "qty": item.qty,
            "id": receipt_id,
        }
        for item in items
    ]
    
    # Ejecutar backflush
    service = BackflushService(db, tenant_id)
    return service.execute_backflush_for_sale_lines(sale_lines, warehouse_id)
