"""
Inventory Alerts Service
Handles checking inventory levels and sending notifications.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.models.core.products import Product
from app.models.inventory.alerts import AlertConfig, AlertHistory
from app.models.inventory.stock import StockItem
from app.models.inventory.warehouse import Warehouse
from app.models.production._production_order import ProductionOrder


class InventoryAlertService:
    """Service for managing inventory and production alerts."""

    def __init__(self, db: Session):
        self.db = db

    def check_and_send_alerts(self, tenant_id: str | None = None) -> dict[str, Any]:
        """
        Check all active alert configurations and send notifications.
        """
        results = {"alerts_sent": [], "errors": [], "configs_checked": 0}

        query = select(AlertConfig).where(
            and_(
                AlertConfig.is_active,
                or_(
                    AlertConfig.next_check_at <= datetime.utcnow(),
                    AlertConfig.next_check_at.is_(None),
                ),
            )
        )

        if tenant_id:
            query = query.where(AlertConfig.tenant_id == tenant_id)

        configs = self.db.execute(query).scalars().all()
        results["configs_checked"] = len(configs)

        for config in configs:
            try:
                alerts_sent = self._check_single_config(config)
                results["alerts_sent"].extend(alerts_sent)
            except Exception as exc:
                results["errors"].append(f"Config {config.id}: {exc}")

            config.last_checked_at = datetime.utcnow()
            config.next_check_at = datetime.utcnow() + timedelta(
                minutes=config.check_frequency_minutes
            )

        self.db.commit()
        return results

    def _check_single_config(self, config: AlertConfig) -> list[dict[str, Any]]:
        """Check a single alert configuration and send alerts if needed."""
        alerts_sent: list[dict[str, Any]] = []
        targets_to_check = self._get_targets_for_config(config)

        for target_data in targets_to_check:
            try:
                should_alert, message = self._should_send_alert(config, target_data)
                if not should_alert:
                    continue
                sent_channels = self._send_alert_notification(config, target_data, message)
                if not sent_channels:
                    continue

                self._record_alert_history(config, target_data, message, sent_channels)
                alerts_sent.append(
                    {
                        "config_id": str(config.id),
                        "product_id": str(target_data["product_id"]),
                        "warehouse_id": target_data.get("warehouse_id"),
                        "channels": sent_channels,
                        "message": message,
                    }
                )
            except Exception as exc:
                print(
                    f"Error checking product {target_data['product_id']} for config {config.id}: {exc}"
                )

        return alerts_sent

    def _get_targets_for_config(self, config: AlertConfig) -> list[dict[str, Any]]:
        """Resolve the source dataset required by the alert type."""
        if config.alert_type == "high_waste":
            return self._get_waste_targets_for_config(config)
        return self._get_stock_targets_for_config(config)

    def _get_stock_targets_for_config(self, config: AlertConfig) -> list[dict[str, Any]]:
        """Get stock-based targets that match the alert configuration filters."""
        query = (
            select(
                StockItem.product_id,
                StockItem.warehouse_id,
                StockItem.qty,
                StockItem.expires_at,
                StockItem.lot,
                Product.name.label("product_name"),
                Product.sku,
                Warehouse.name.label("warehouse_name"),
                Product.category_id,
            )
            .join(Product, Product.id == StockItem.product_id)
            .join(Warehouse, Warehouse.id == StockItem.warehouse_id)
            .where(StockItem.tenant_id == config.tenant_id)
            .where(Product.active)
        )

        if config.warehouse_ids:
            query = query.where(StockItem.warehouse_id.in_(config.warehouse_ids))

        if config.category_ids:
            query = query.where(Product.category_id.in_(config.category_ids))

        if config.product_ids:
            query = query.where(StockItem.product_id.in_(config.product_ids))

        if config.alert_type == "expiring_stock":
            query = query.where(StockItem.expires_at.is_not(None)).where(StockItem.qty > 0)

        rows = self.db.execute(query).all()
        return [
            {
                "product_id": row[0],
                "warehouse_id": row[1],
                "current_stock": float(row[2] or 0),
                "expires_at": row[3],
                "lot": row[4],
                "product_name": row[5],
                "sku": row[6],
                "warehouse_name": row[7],
                "category_id": row[8],
            }
            for row in rows
        ]

    def _get_waste_targets_for_config(self, config: AlertConfig) -> list[dict[str, Any]]:
        """Get production waste totals grouped by finished product for the current day."""
        today = datetime.utcnow().date()
        day_start = datetime.combine(today, datetime.min.time())
        day_end = day_start + timedelta(days=1)

        query = (
            select(
                ProductionOrder.product_id,
                ProductionOrder.warehouse_id,
                func.coalesce(func.sum(ProductionOrder.waste_qty), 0).label("waste_qty"),
                Product.name.label("product_name"),
                Product.sku,
                Warehouse.name.label("warehouse_name"),
                Product.category_id,
            )
            .join(Product, Product.id == ProductionOrder.product_id)
            .outerjoin(Warehouse, Warehouse.id == ProductionOrder.warehouse_id)
            .where(ProductionOrder.tenant_id == config.tenant_id)
            .where(ProductionOrder.status == "COMPLETED")
            .where(ProductionOrder.completed_at >= day_start)
            .where(ProductionOrder.completed_at < day_end)
            .group_by(
                ProductionOrder.product_id,
                ProductionOrder.warehouse_id,
                Product.name,
                Product.sku,
                Warehouse.name,
                Product.category_id,
            )
        )

        if config.warehouse_ids:
            query = query.where(ProductionOrder.warehouse_id.in_(config.warehouse_ids))

        if config.category_ids:
            query = query.where(Product.category_id.in_(config.category_ids))

        if config.product_ids:
            query = query.where(ProductionOrder.product_id.in_(config.product_ids))

        rows = self.db.execute(query).all()
        return [
            {
                "product_id": row[0],
                "warehouse_id": row[1],
                "current_stock": float(row[2] or 0),
                "waste_qty": float(row[2] or 0),
                "product_name": row[3],
                "sku": row[4],
                "warehouse_name": row[5],
                "category_id": row[6],
            }
            for row in rows
        ]

    def _should_send_alert(
        self, config: AlertConfig, product_data: dict[str, Any]
    ) -> tuple[bool, str]:
        """Determine if an alert should be sent for this product."""
        current_stock = product_data["current_stock"]
        threshold = (
            config.threshold_value
            if config.threshold_type != "percentage"
            else config.threshold_value
        )

        if config.alert_type == "high_waste":
            should_alert = current_stock >= threshold
        elif config.alert_type == "expiring_stock":
            expires_at = product_data.get("expires_at")
            if not expires_at:
                return False, ""
            product_data["days_until_expiry"] = (expires_at - datetime.utcnow().date()).days
            should_alert = product_data["days_until_expiry"] <= int(threshold)
        else:
            should_alert = current_stock <= threshold

        if should_alert and self._can_send_alert(config, product_data["product_id"]):
            return True, self._build_alert_message(config, product_data, threshold)

        return False, ""

    def _can_send_alert(self, config: AlertConfig, product_id: Any) -> bool:
        """Check cooldown and daily limit for a candidate alert."""
        cooldown_period = datetime.utcnow() - timedelta(hours=config.cooldown_hours)

        recent_alerts = (
            self.db.query(AlertHistory)
            .filter(
                and_(
                    AlertHistory.tenant_id == config.tenant_id,
                    AlertHistory.product_id == product_id,
                    AlertHistory.alert_type == config.alert_type,
                    AlertHistory.sent_at >= cooldown_period,
                )
            )
            .count()
        )
        if recent_alerts > 0:
            return False

        today = datetime.utcnow().date()
        today_start = datetime.combine(today, datetime.min.time())
        daily_alerts = (
            self.db.query(AlertHistory)
            .filter(
                and_(
                    AlertHistory.alert_config_id == config.id,
                    AlertHistory.sent_at >= today_start,
                )
            )
            .count()
        )
        return daily_alerts < config.max_alerts_per_day

    def _build_alert_message(
        self, config: AlertConfig, product_data: dict[str, Any], threshold: float
    ) -> str:
        """Build the alert message."""
        product_name = product_data["product_name"]
        sku = product_data["sku"]
        current_stock = product_data["current_stock"]
        warehouse_name = product_data["warehouse_name"]

        if config.alert_type == "low_stock":
            alert_type_text = "STOCK BAJO"
        elif config.alert_type == "out_of_stock":
            alert_type_text = "SIN STOCK"
        elif config.alert_type == "expiring_stock":
            alert_type_text = "CADUCIDAD PROXIMA"
        elif config.alert_type == "high_waste":
            alert_type_text = "MERMA ALTA"
        else:
            alert_type_text = config.alert_type.upper()

        if config.alert_type == "expiring_stock":
            expires_at = product_data.get("expires_at")
            days_until_expiry = product_data.get("days_until_expiry")
            return f"""ALERTA DE INVENTARIO - {alert_type_text}

Producto: {product_name}
SKU: {sku or "N/A"}
Almacen: {warehouse_name}
Stock actual: {current_stock}
Lote: {product_data.get("lot") or "N/A"}
Caduca: {expires_at.isoformat() if expires_at else "N/A"}
Dias restantes: {days_until_expiry if days_until_expiry is not None else "N/A"}
Umbral: {int(threshold)} dias

Configuracion: {config.name}

Fecha: {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")}"""

        if config.alert_type == "high_waste":
            return f"""ALERTA DE PRODUCCION - {alert_type_text}

Producto: {product_name}
SKU: {sku or "N/A"}
Almacen: {warehouse_name}
Merma del dia: {current_stock}
Umbral: {threshold}

Configuracion: {config.name}

Fecha: {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")}"""

        return f"""ALERTA DE INVENTARIO - {alert_type_text}

Producto: {product_name}
SKU: {sku or "N/A"}
Almacen: {warehouse_name}
Stock actual: {current_stock}
Umbral: {threshold}

Configuracion: {config.name}

Fecha: {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")}"""

    def _send_alert_notification(
        self, config: AlertConfig, product_data: dict[str, Any], message: str
    ) -> list[str]:
        """Send alert notification through configured channels."""
        channels_sent: list[str] = []

        try:
            from app.services.notifications import NotificationService

            notification_service = NotificationService(self.db)

            if config.notify_email and config.email_recipients:
                try:
                    notification_service.send_email(
                        recipients=config.email_recipients,
                        subject=f"Alerta de Inventario: {config.name}",
                        body=message,
                    )
                    channels_sent.append("email")
                except Exception as exc:
                    print(f"Email notification failed: {exc}")

            if config.notify_whatsapp and config.whatsapp_numbers:
                try:
                    for number in config.whatsapp_numbers:
                        notification_service.send_whatsapp(number, message)
                    channels_sent.append("whatsapp")
                except Exception as exc:
                    print(f"WhatsApp notification failed: {exc}")

            if config.notify_telegram and config.telegram_chat_ids:
                try:
                    for chat_id in config.telegram_chat_ids:
                        notification_service.send_telegram(chat_id, message)
                    channels_sent.append("telegram")
                except Exception as exc:
                    print(f"Telegram notification failed: {exc}")

        except ImportError:
            print("Notification service not available")

        return channels_sent

    def _record_alert_history(
        self,
        config: AlertConfig,
        product_data: dict[str, Any],
        message: str,
        channels_sent: list[str],
    ) -> None:
        """Record the alert in history."""
        history = AlertHistory(
            tenant_id=config.tenant_id,
            alert_config_id=config.id,
            product_id=product_data["product_id"],
            warehouse_id=product_data.get("warehouse_id"),
            alert_type=config.alert_type,
            threshold_value=config.threshold_value,
            current_stock=product_data["current_stock"],
            message=message,
            channels_sent=channels_sent,
        )
        self.db.add(history)
