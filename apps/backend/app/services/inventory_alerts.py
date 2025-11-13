"""
Inventory Alerts Service
Handles checking inventory levels and sending notifications
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from app.models.core.products import Product
from app.models.inventory.alerts import AlertConfig, AlertHistory
from app.models.inventory.stock import StockItem
from app.models.inventory.warehouse import Warehouse
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session


class InventoryAlertService:
    """Service for managing inventory alerts"""

    def __init__(self, db: Session):
        self.db = db

    def check_and_send_alerts(self, tenant_id: str | None = None) -> dict[str, Any]:
        """
        Check all active alert configurations and send notifications for products below threshold
        """
        results = {"alerts_sent": [], "errors": [], "configs_checked": 0}

        # Get active alert configs that need checking
        query = select(AlertConfig).where(
            and_(
                AlertConfig.is_active == True,
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
            except Exception as e:
                results["errors"].append(f"Config {config.id}: {str(e)}")

            # Update last checked time and next check time
            config.last_checked_at = datetime.utcnow()
            config.next_check_at = datetime.utcnow() + timedelta(
                minutes=config.check_frequency_minutes
            )

        self.db.commit()
        return results

    def _check_single_config(self, config: AlertConfig) -> list[dict[str, Any]]:
        """Check a single alert configuration and send alerts if needed"""
        alerts_sent = []

        # Get products that match the configuration filters
        products_to_check = self._get_products_for_config(config)

        for product_data in products_to_check:
            try:
                should_alert, message = self._should_send_alert(config, product_data)
                if should_alert:
                    sent_channels = self._send_alert_notification(config, product_data, message)
                    if sent_channels:
                        # Record the alert in history
                        self._record_alert_history(config, product_data, message, sent_channels)
                        alerts_sent.append(
                            {
                                "config_id": str(config.id),
                                "product_id": str(product_data["product_id"]),
                                "warehouse_id": product_data.get("warehouse_id"),
                                "channels": sent_channels,
                                "message": message,
                            }
                        )
            except Exception as e:
                # Log error but continue with other products
                print(
                    f"Error checking product {product_data['product_id']} for config {config.id}: {str(e)}"
                )

        return alerts_sent

    def _get_products_for_config(self, config: AlertConfig) -> list[dict[str, Any]]:
        """Get products that match the alert configuration filters"""
        # Build base query for stock items with product info
        query = (
            select(
                StockItem.product_id,
                StockItem.warehouse_id,
                StockItem.qty,
                Product.name.label("product_name"),
                Product.sku,
                Warehouse.name.label("warehouse_name"),
                Product.category_id,
            )
            .join(Product, Product.id == StockItem.product_id)
            .join(Warehouse, Warehouse.id == StockItem.warehouse_id)
            .where(StockItem.tenant_id == config.tenant_id)
            .where(Product.active == True)
        )

        # Apply warehouse filter
        if config.warehouse_ids:
            query = query.where(StockItem.warehouse_id.in_(config.warehouse_ids))

        # Apply category filter
        if config.category_ids:
            query = query.where(Product.category_id.in_(config.category_ids))

        # Apply product filter
        if config.product_ids:
            query = query.where(StockItem.product_id.in_(config.product_ids))

        rows = self.db.execute(query).all()

        products = []
        for row in rows:
            products.append(
                {
                    "product_id": row[0],
                    "warehouse_id": row[1],
                    "current_stock": float(row[2] or 0),
                    "product_name": row[3],
                    "sku": row[4],
                    "warehouse_name": row[5],
                    "category_id": row[6],
                }
            )

        return products

    def _should_send_alert(
        self, config: AlertConfig, product_data: dict[str, Any]
    ) -> tuple[bool, str]:
        """Determine if an alert should be sent for this product"""
        current_stock = product_data["current_stock"]

        # Calculate threshold
        if config.threshold_type == "percentage":
            # For percentage, we'd need to know the "normal" stock level
            # For now, assume we need a base stock level stored somewhere
            # For simplicity, convert to fixed threshold
            threshold = config.threshold_value  # Assume it's already a fixed number
        else:
            threshold = config.threshold_value

        if current_stock <= threshold:
            # Check cooldown - don't send alerts too frequently
            cooldown_period = datetime.utcnow() - timedelta(hours=config.cooldown_hours)

            recent_alerts = (
                self.db.query(AlertHistory)
                .filter(
                    and_(
                        AlertHistory.tenant_id == config.tenant_id,
                        AlertHistory.product_id == product_data["product_id"],
                        AlertHistory.alert_type == config.alert_type,
                        AlertHistory.sent_at >= cooldown_period,
                    )
                )
                .count()
            )

            if recent_alerts == 0:
                # Check daily limit
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

                if daily_alerts < config.max_alerts_per_day:
                    message = self._build_alert_message(config, product_data, threshold)
                    return True, message

        return False, ""

    def _build_alert_message(
        self, config: AlertConfig, product_data: dict[str, Any], threshold: float
    ) -> str:
        """Build the alert message"""
        product_name = product_data["product_name"]
        sku = product_data["sku"]
        current_stock = product_data["current_stock"]
        warehouse_name = product_data["warehouse_name"]

        if config.alert_type == "low_stock":
            alert_type_text = "STOCK BAJO"
        elif config.alert_type == "out_of_stock":
            alert_type_text = "SIN STOCK"
        else:
            alert_type_text = config.alert_type.upper()

        message = f"""🔔 ALERTA DE INVENTARIO - {alert_type_text}

Producto: {product_name}
SKU: {sku or 'N/A'}
Almacén: {warehouse_name}
Stock Actual: {current_stock}
Umbral: {threshold}

Configuración: {config.name}

Fecha: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"""

        return message

    def _send_alert_notification(
        self, config: AlertConfig, product_data: dict[str, Any], message: str
    ) -> list[str]:
        """Send alert notification through configured channels"""
        channels_sent = []

        try:
            from app.services.notifications import NotificationService

            notification_service = NotificationService(self.db)

            # Email notifications
            if config.notify_email and config.email_recipients:
                try:
                    notification_service.send_email(
                        recipients=config.email_recipients,
                        subject=f"Alerta de Inventario: {config.name}",
                        body=message,
                    )
                    channels_sent.append("email")
                except Exception as e:
                    print(f"Email notification failed: {str(e)}")

            # WhatsApp notifications
            if config.notify_whatsapp and config.whatsapp_numbers:
                try:
                    for number in config.whatsapp_numbers:
                        notification_service.send_whatsapp(number, message)
                    channels_sent.append("whatsapp")
                except Exception as e:
                    print(f"WhatsApp notification failed: {str(e)}")

            # Telegram notifications
            if config.notify_telegram and config.telegram_chat_ids:
                try:
                    for chat_id in config.telegram_chat_ids:
                        notification_service.send_telegram(chat_id, message)
                    channels_sent.append("telegram")
                except Exception as e:
                    print(f"Telegram notification failed: {str(e)}")

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
        """Record the alert in history"""
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
