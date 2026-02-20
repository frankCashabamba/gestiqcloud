"""
Modelo para logging de requests/responses de IA
Permite auditoría, análisis de errores y mejora continua
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Float, Index, Integer, String, Text

from app.db.base import Base


class AITaskLog(str, enum.Enum):
    """Tipos de tarea (matching AITask)"""

    CLASSIFICATION = "classification"
    ANALYSIS = "analysis"
    GENERATION = "generation"
    SUGGESTION = "suggestion"
    CHAT = "chat"
    EXTRACTION = "extraction"


class AIResponseStatus(str, enum.Enum):
    """Estado de la respuesta"""

    SUCCESS = "success"  # Respuesta exitosa
    ERROR = "error"  # Error del proveedor
    TIMEOUT = "timeout"  # Timeout
    FALLBACK = "fallback"  # Usado fallback
    RETRIED = "retried"  # Reintentado
    INVALID = "invalid"  # Respuesta inválida/no parseable
    PARTIAL = "partial"  # Respuesta parcial


class AIRequestLog(Base):
    """
    Log de todos los requests a IA
    Permite:
    - Auditoría de requests
    - Análisis de patrones de error
    - Mejora continua
    - Tracking de costos
    """

    __tablename__ = "ai_request_logs"

    # Identifiers
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(50), unique=True, index=True)  # UUID para tracing

    # Contexto
    tenant_id = Column(String(36), nullable=True, index=True)
    module = Column(String(50), nullable=True)  # copilot, imports, incidents, etc
    user_id = Column(String(36), nullable=True)

    # Request
    task = Column(String(20), index=True)  # classification, analysis, etc
    prompt_length = Column(Integer)
    prompt_hash = Column(String(64), nullable=True)  # SHA256 para dedup
    temperature = Column(Float, default=0.3)
    max_tokens = Column(Integer, nullable=True)
    model_requested = Column(String(50), nullable=True)

    # Provider
    provider_used = Column(String(20), index=True)  # ollama, ovhcloud, openai
    provider_model = Column(String(50), nullable=True)

    # Response
    status = Column(String(20), default="success", index=True)  # success, error, timeout, etc
    response_content_length = Column(Integer, default=0)
    tokens_used = Column(Integer, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)

    # Error tracking
    error_message = Column(Text, nullable=True)
    error_code = Column(String(50), nullable=True)
    retry_count = Column(Integer, default=0)
    fallback_used = Column(String(20), nullable=True)  # Qué fallback se usó

    # Quality metrics
    confidence_score = Column(Float, nullable=True)  # Si aplica
    user_feedback = Column(String(20), nullable=True)  # thumbs_up, thumbs_down, etc
    correction_applied = Column(String(255), nullable=True)  # Si fue corregido

    # Metadata
    request_metadata = Column(JSON, nullable=True)  # Context, custom data
    response_metadata = Column(JSON, nullable=True)  # Provider-specific data

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes para queries comunes
    __table_args__ = (
        # Para encontrar errores rápido
        Index("idx_ai_request_logs_status_created", "status", "created_at"),
        # Para analytics por module
        Index("idx_ai_request_logs_module_task", "module", "task"),
        # Para auditoría por tenant
        Index("idx_ai_request_logs_tenant_created", "tenant_id", "created_at"),
    )


class AIErrorAnalysis(Base):
    """
    Análisis de errores y patrones
    Identificar problemas recurrentes y sugerir soluciones
    """

    __tablename__ = "ai_error_analysis"

    id = Column(Integer, primary_key=True)

    # Patrón
    error_pattern = Column(
        String(100), unique=True, index=True
    )  # e.g., "ollama_connection_timeout"
    error_code = Column(String(50), nullable=True)
    error_message_pattern = Column(String(255))

    # Frecuencia
    occurrence_count = Column(Integer, default=1)
    last_occurred = Column(DateTime, index=True)

    # Análisis
    probable_cause = Column(Text)
    suggested_action = Column(Text)
    resolution_status = Column(String(50), default="open")  # open, investigating, resolved, wontfix

    # Soluciones aplicadas
    auto_correction_enabled = Column(String(50), nullable=True)  # retry, fallback, cache
    correction_config = Column(JSON, nullable=True)  # retry_count, delay, etc

    # Tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)


class AIErrorRecovery(Base):
    """
    Estrategias de recuperación ejecutadas
    Permite aprender qué funciona y qué no
    """

    __tablename__ = "ai_error_recovery"

    id = Column(Integer, primary_key=True)
    request_log_id = Column(Integer)  # Referencia a AIRequestLog

    # Estrategia ejecutada
    strategy_name = Column(String(50))  # retry, fallback, cache, regenerate
    step_number = Column(Integer)  # 1st attempt, 2nd retry, etc

    # Detalles
    action_taken = Column(String(100))  # Descripción de qué se hizo
    was_successful = Column(String(20), nullable=True)  # true, false
    recovery_time_ms = Column(Integer, nullable=True)

    # Resultado
    recovery_result = Column(JSON)  # Qué pasó: status, new_provider, etc

    created_at = Column(DateTime, default=datetime.utcnow)
