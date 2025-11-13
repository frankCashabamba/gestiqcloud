"""
Configuración de Celery para tareas asíncronas
"""

from celery import Celery
from celery.schedules import crontab
import os

# Configuración Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Inicializar Celery
celery_app = Celery(
    "gestiqcloud",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "app.workers.notifications",
        "app.workers.einvoicing_tasks",
        # Añadir más workers según sea necesario
    ],
)

# Configuración general
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Resultados
    result_expires=3600,  # 1 hora
    result_backend_transport_options={"master_name": "mymaster"},
    # Concurrencia
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
    # Retry
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Rate limits
    task_default_rate_limit="100/m",  # 100 tareas por minuto
)

# ============================================================================
# CELERY BEAT SCHEDULE - Tareas Programadas
# ============================================================================

celery_app.conf.beat_schedule = {
    # Revisar stock bajo cada hora
    "check-low-stock-every-hour": {
        "task": "app.workers.notifications.check_and_notify_low_stock",
        "schedule": crontab(minute=0),  # Cada hora en punto (XX:00)
        "options": {
            "expires": 3300,  # Expira en 55 minutos
        },
    },
    # Limpiar logs antiguos el primer día de cada mes
    "cleanup-old-logs-monthly": {
        "task": "app.workers.notifications.cleanup_old_logs",
        "schedule": crontab(day_of_month=1, hour=2, minute=0),  # Día 1 a las 2 AM
        "kwargs": {"days": 90},
        "options": {
            "expires": 86000,  # Expira en ~24 horas
        },
    },
    # E-factura: Enviar pendientes cada 30 minutos (si aplica)
    "send-pending-einvoices": {
        "task": "app.workers.einvoicing_tasks.process_pending_invoices",
        "schedule": crontab(minute="*/30"),  # Cada 30 minutos
        "options": {
            "expires": 1500,  # Expira en 25 minutos
        },
    },
    # Sincronizar estado SRI/AEAT cada 2 horas (si aplica)
    "sync-einvoice-status": {
        "task": "app.workers.einvoicing_tasks.sync_einvoice_status",
        "schedule": crontab(minute=15, hour="*/2"),  # XX:15 cada 2 horas
        "options": {
            "expires": 7000,
        },
    },
}

# ============================================================================
# TASK ROUTES - Distribución de tareas
# ============================================================================

celery_app.conf.task_routes = {
    "app.workers.notifications.*": {"queue": "notifications"},
    "app.workers.einvoicing_tasks.*": {"queue": "einvoicing"},
    "app.workers.reports.*": {"queue": "reports"},
}

# ============================================================================
# MONITORING
# ============================================================================

# Eventos para monitoring (Flower, etc)
celery_app.conf.worker_send_task_events = True
celery_app.conf.task_send_sent_event = True


if __name__ == "__main__":
    celery_app.start()
