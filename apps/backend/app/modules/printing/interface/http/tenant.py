from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, confloat, constr
from serial.tools import list_ports
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.middleware.tenant import ensure_tenant
from app.models.company.company_settings import CompanySettings
from app.models.printing.printer_label_configuration import PrinterLabelConfiguration

from ...tspl import (
    LabelConfig,
    ProductLabel,
    build_tspl_payload,
    build_tspl_payload_for_labels,
    send_to_printer,
)


def build_label_config(
    width_mm: float | None,
    height_mm: float | None,
    gap_mm: float | None,
    columns: int | None = None,
    column_gap_mm: float | None = None,
) -> LabelConfig:
    config = LabelConfig()
    if width_mm is not None:
        config.width_mm = width_mm
    if height_mm is not None:
        config.height_mm = height_mm
    if gap_mm is not None:
        config.label_gap_mm = gap_mm
    if columns is not None:
        config.columns = columns
    if column_gap_mm is not None:
        config.column_gap_mm = column_gap_mm
    return config


router = APIRouter()
logger = logging.getLogger("app.printing")


class PrintLabelRequest(BaseModel):
    name: constr(strip_whitespace=True, min_length=1, max_length=60)
    barcode: constr(strip_whitespace=True, min_length=1, max_length=60)
    price: constr(strip_whitespace=True, min_length=1, max_length=32) | None = None
    copies: int = Field(1, ge=1, le=20)
    width_mm: confloat(gt=0, ge=10, le=150) = Field(50)
    height_mm: confloat(gt=0, ge=15, le=120) = Field(40)
    gap_mm: confloat(gt=0, ge=0.5, le=10) = Field(3)
    columns: int = Field(1, ge=1, le=6)
    column_gap_mm: confloat(ge=0, le=20) = Field(2)
    header_text: constr(strip_whitespace=True, min_length=1, max_length=60) | None = None
    footer_text: constr(strip_whitespace=True, min_length=1, max_length=60) | None = None
    offset_xmm: confloat(ge=-30, le=30) | None = None
    offset_ymm: confloat(ge=-30, le=30) | None = None
    barcode_width: confloat(gt=0, ge=1, le=5) | None = None
    price_alignment: Literal["left", "center", "right"] | None = None
    port: str | None = None
    baudrate: int = Field(9600, ge=1200, le=115200)


class PrinterInfo(BaseModel):
    port: str
    name: str | None = None
    description: str | None = None
    hwid: str | None = None


class LabelConfigPayload(BaseModel):
    width_mm: confloat(gt=0, ge=10, le=150) | None = None
    height_mm: confloat(gt=0, ge=15, le=120) | None = None
    gap_mm: confloat(gt=0, ge=0.5, le=10) | None = None
    columns: int | None = Field(None, ge=1, le=6)
    column_gap_mm: confloat(ge=0, le=20) | None = None
    show_price: bool | None = None
    show_category: bool | None = None
    copies: int | None = Field(None, ge=1, le=20)
    header_text: constr(strip_whitespace=True, min_length=1, max_length=60) | None = None
    footer_text: constr(strip_whitespace=True, min_length=1, max_length=60) | None = None
    offset_xmm: confloat(ge=-30, le=30) | None = None
    offset_ymm: confloat(ge=-30, le=30) | None = None
    barcode_width: confloat(gt=0, ge=1, le=5) | None = None
    price_alignment: Literal["left", "center", "right"] | None = None


class PrintingSettingsRequest(BaseModel):
    port: constr(strip_whitespace=True, min_length=1)
    name: constr(strip_whitespace=True, min_length=1) | None = None
    label_config: LabelConfigPayload | None = None


class PrinterLabelConfigResponse(BaseModel):
    id: UUID
    name: str
    printer_port: str
    width_mm: float | None = None
    height_mm: float | None = None
    gap_mm: float | None = None
    columns: int | None = None
    column_gap_mm: float | None = None
    copies: int | None = None
    show_price: bool | None = None
    show_category: bool | None = None
    header_text: str | None = None
    footer_text: str | None = None
    offset_xmm: float | None = None
    offset_ymm: float | None = None
    barcode_width: float | None = None
    price_alignment: Literal["left", "center", "right"] | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SavePrinterLabelConfigRequest(BaseModel):
    printer_port: constr(strip_whitespace=True, min_length=1)
    name: constr(strip_whitespace=True, min_length=1, max_length=60)
    label_config: LabelConfigPayload


class BatchLabelItem(BaseModel):
    name: constr(strip_whitespace=True, min_length=1, max_length=60)
    barcode: constr(strip_whitespace=True, min_length=1, max_length=60)
    price: constr(strip_whitespace=True, min_length=1, max_length=32) | None = None
    copies: int = Field(1, ge=1, le=20)


class PrintLabelsRequest(BaseModel):
    labels: list[BatchLabelItem]
    width_mm: confloat(gt=0, ge=10, le=150) = Field(50)
    height_mm: confloat(gt=0, ge=15, le=120) = Field(40)
    gap_mm: confloat(gt=0, ge=0.5, le=10) = Field(3)
    columns: int = Field(1, ge=1, le=6)
    column_gap_mm: confloat(ge=0, le=20) = Field(2)
    header_text: constr(strip_whitespace=True, min_length=1, max_length=60) | None = None
    footer_text: constr(strip_whitespace=True, min_length=1, max_length=60) | None = None
    offset_xmm: confloat(ge=-30, le=30) | None = None
    offset_ymm: confloat(ge=-30, le=30) | None = None
    barcode_width: confloat(gt=0, ge=1, le=5) | None = None
    price_alignment: Literal["left", "center", "right"] | None = None
    port: str | None = None
    baudrate: int = Field(9600, ge=1200, le=115200)


def _resolve_port(tenant_id: str, db: Session, explicit: str | None = None) -> str | None:
    if explicit:
        return explicit

    company_settings = (
        db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_id).first()
    )
    if company_settings:
        settings = company_settings.settings or {}
        printing_cfg = settings.get("printing", {})
        port = printing_cfg.get("port")
        if port:
            return port

    return os.getenv("PRINTING_PORT")


def _store_printing_settings(
    tenant_id: str,
    db: Session,
    port: str,
    name: str | None,
    label_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    company_settings = (
        db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_id).first()
    )
    if not company_settings:
        raise HTTPException(status_code=404, detail="Tenant settings not configured yet")

    settings = company_settings.settings or {}
    printing_cfg = {**settings.get("printing", {}), "port": port, "name": name}
    if label_config:
        printing_cfg["label_config"] = label_config
    settings["printing"] = printing_cfg
    company_settings.settings = settings
    db.add(company_settings)
    db.commit()
    return printing_cfg


@router.get("/printing/printers", summary="List available serial printers")
async def list_printers() -> list[PrinterInfo]:
    ports = list_ports.comports()
    return [
        PrinterInfo(
            port=port.device,
            name=port.name or port.description,
            description=port.description,
            hwid=port.hwid,
        )
        for port in ports
    ]


@router.get("/printing/settings", summary="Get selected printer for tenant")
def get_printing_settings(
    tenant_id: str = Depends(ensure_tenant), db: Session = Depends(get_db)
) -> dict[str, Any] | None:
    company_settings = (
        db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_id).first()
    )
    if not company_settings:
        return None
    settings = company_settings.settings or {}
    return settings.get("printing")


@router.post("/printing/settings", summary="Persist selected printer for tenant")
def set_printing_settings(
    payload: PrintingSettingsRequest,
    tenant_id: str = Depends(ensure_tenant),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    label_cfg = payload.label_config.dict(exclude_none=True) if payload.label_config else None
    return _store_printing_settings(tenant_id, db, payload.port, payload.name, label_cfg)


@router.get(
    "/printing/configurations",
    summary="List saved printer label configurations for the tenant",
    response_model=list[PrinterLabelConfigResponse],
)
def list_printer_label_configurations(
    port: str | None = None,
    tenant_id: str = Depends(ensure_tenant),
    db: Session = Depends(get_db),
) -> list[PrinterLabelConfigResponse]:
    query = (
        db.query(PrinterLabelConfiguration)
        .filter(PrinterLabelConfiguration.tenant_id == tenant_id)
        .order_by(PrinterLabelConfiguration.created_at.desc())
    )
    if port:
        query = query.filter(PrinterLabelConfiguration.printer_port == port)
    return query.all()


@router.post(
    "/printing/configurations",
    summary="Persist a label configuration for a printer and tenant",
    response_model=PrinterLabelConfigResponse,
)
def create_printer_label_configuration(
    payload: SavePrinterLabelConfigRequest,
    tenant_id: str = Depends(ensure_tenant),
    db: Session = Depends(get_db),
) -> PrinterLabelConfigResponse:
    cfg = payload.label_config
    record = PrinterLabelConfiguration(
        tenant_id=tenant_id,
        printer_port=payload.printer_port,
        name=payload.name,
        width_mm=cfg.width_mm,
        height_mm=cfg.height_mm,
        gap_mm=cfg.gap_mm,
        columns=cfg.columns,
        column_gap_mm=cfg.column_gap_mm,
        copies=cfg.copies,
        show_price=cfg.show_price,
        show_category=cfg.show_category,
        header_text=cfg.header_text,
        footer_text=cfg.footer_text,
        offset_xmm=cfg.offset_xmm,
        offset_ymm=cfg.offset_ymm,
        barcode_width=cfg.barcode_width,
        price_alignment=cfg.price_alignment,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.post("/printing/labels", summary="Send TSPL label to attached printer")
async def print_label(
    payload: PrintLabelRequest,
    tenant_id: str = Depends(ensure_tenant),
    db: Session = Depends(get_db),
) -> dict[str, int | str]:
    port = _resolve_port(tenant_id, db, payload.port)
    if not port:
        raise HTTPException(
            status_code=400,
            detail="No printer port configured; specify `port` or set PRINTING_PORT.",
        )

    logger.info(
        "Printing %d copies of %s via %s@%d (%s×%smm gap=%.1f header=%s footer=%s)",
        payload.copies,
        payload.name,
        port,
        payload.baudrate,
        payload.width_mm,
        payload.height_mm,
        payload.gap_mm,
        payload.header_text,
        payload.footer_text,
    )

    label = ProductLabel(
        name=payload.name,
        barcode=payload.barcode,
        price=payload.price,
        copies=payload.copies,
        header_text=payload.header_text,
        footer_text=payload.footer_text,
        offset_xmm=payload.offset_xmm,
        offset_ymm=payload.offset_ymm,
        barcode_width=payload.barcode_width,
        price_alignment=payload.price_alignment,
    )
    config = build_label_config(
        payload.width_mm,
        payload.height_mm,
        payload.gap_mm,
        payload.columns,
        payload.column_gap_mm,
    )
    tspl = build_tspl_payload(label, config)

    try:
        send_to_printer(port, tspl, baudrate=payload.baudrate)
    except Exception as exc:  # pragma: no cover - depends on hardware
        logger.exception("Failed sending TSPL label to %s", port)
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "printed": payload.copies,
        "port": port,
    }


@router.post("/printing/labels/batch", summary="Send TSPL labels batch to attached printer")
async def print_labels_batch(
    payload: PrintLabelsRequest,
    tenant_id: str = Depends(ensure_tenant),
    db: Session = Depends(get_db),
) -> dict[str, int | str]:
    port = _resolve_port(tenant_id, db, payload.port)
    if not port:
        raise HTTPException(
            status_code=400,
            detail="No printer port configured; specify `port` or set PRINTING_PORT.",
        )

    expanded_labels: list[ProductLabel] = []
    for item in payload.labels:
        for _ in range(item.copies):
            expanded_labels.append(
                ProductLabel(
                    name=item.name,
                    barcode=item.barcode,
                    price=item.price,
                    copies=1,
                    header_text=payload.header_text,
                    footer_text=payload.footer_text,
                    offset_xmm=payload.offset_xmm,
                    offset_ymm=payload.offset_ymm,
                    barcode_width=payload.barcode_width,
                    price_alignment=payload.price_alignment,
                )
            )

    if not expanded_labels:
        raise HTTPException(status_code=400, detail="No labels to print.")

    config = build_label_config(
        payload.width_mm,
        payload.height_mm,
        payload.gap_mm,
        payload.columns,
        payload.column_gap_mm,
    )
    tspl = build_tspl_payload_for_labels(expanded_labels, config)

    try:
        send_to_printer(port, tspl, baudrate=payload.baudrate)
    except Exception as exc:  # pragma: no cover - depends on hardware
        logger.exception("Failed sending TSPL labels to %s", port)
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "printed": len(expanded_labels),
        "port": port,
    }
