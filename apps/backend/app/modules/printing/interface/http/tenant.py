from __future__ import annotations

import logging
import os
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
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

router = APIRouter()
logger = logging.getLogger("app.printing")


NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
ShortStr60 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
ShortStr32 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)]

MmWidth = Annotated[float, Field(ge=10, le=150)]
MmHeight = Annotated[float, Field(ge=15, le=120)]
GapMm = Annotated[float, Field(ge=0.5, le=10)]
ColumnGapMm = Annotated[float, Field(ge=0, le=20)]
OffsetMm = Annotated[float, Field(ge=-30, le=30)]
BarcodeWidth = Annotated[float, Field(ge=1, le=5)]
Baudrate = Annotated[int, Field(ge=1200, le=115200)]
Copies = Annotated[int, Field(ge=1, le=20)]
Columns = Annotated[int, Field(ge=1, le=6)]

PriceAlignment = Literal["left", "center", "right"]


def _get_company_settings(tenant_id: str, db: Session) -> CompanySettings | None:
    return db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_id).first()


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


class PrinterInfo(BaseModel):
    port: str
    name: str | None = None
    description: str | None = None
    hwid: str | None = None


class LabelConfigPayload(BaseModel):
    width_mm: MmWidth | None = None
    height_mm: MmHeight | None = None
    gap_mm: GapMm | None = None
    columns: Columns | None = None
    column_gap_mm: ColumnGapMm | None = None
    show_price: bool | None = None
    show_category: bool | None = None
    copies: Copies | None = None
    header_text: ShortStr60 | None = None
    footer_text: ShortStr60 | None = None
    offset_xmm: OffsetMm | None = None
    offset_ymm: OffsetMm | None = None
    barcode_width: BarcodeWidth | None = None
    price_alignment: PriceAlignment | None = None


class PrintingSettingsRequest(BaseModel):
    port: NonEmptyStr
    name: NonEmptyStr | None = None
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
    price_alignment: PriceAlignment | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SavePrinterLabelConfigRequest(BaseModel):
    printer_port: NonEmptyStr
    name: ShortStr60
    label_config: LabelConfigPayload


class BatchLabelItem(BaseModel):
    name: ShortStr60
    barcode: ShortStr60
    price: ShortStr32 | None = None
    copies: Copies = 1


class PrintLabelRequest(BaseModel):
    name: ShortStr60
    barcode: ShortStr60
    price: ShortStr32 | None = None
    copies: Copies = 1

    width_mm: MmWidth = 50
    height_mm: MmHeight = 40
    gap_mm: GapMm = 3
    columns: Columns = 1
    column_gap_mm: ColumnGapMm = 2

    header_text: ShortStr60 | None = None
    footer_text: ShortStr60 | None = None
    offset_xmm: OffsetMm | None = None
    offset_ymm: OffsetMm | None = None
    barcode_width: BarcodeWidth | None = None
    price_alignment: PriceAlignment | None = None

    port: str | None = None
    baudrate: Baudrate = 9600


class PrintLabelsRequest(BaseModel):
    labels: list[BatchLabelItem]

    width_mm: MmWidth = 50
    height_mm: MmHeight = 40
    gap_mm: GapMm = 3
    columns: Columns = 1
    column_gap_mm: ColumnGapMm = 2

    header_text: ShortStr60 | None = None
    footer_text: ShortStr60 | None = None
    offset_xmm: OffsetMm | None = None
    offset_ymm: OffsetMm | None = None
    barcode_width: BarcodeWidth | None = None
    price_alignment: PriceAlignment | None = None

    port: str | None = None
    baudrate: Baudrate = 9600


class ReceiptSettingsRequest(BaseModel):
    footer_message: str = "¡Gracias por su compra!"
    show_tax_breakdown: bool = True
    show_cashier: bool = True
    show_customer: bool = True
    custom_header: str | None = None
    custom_footer: str | None = None


def _resolve_port(tenant_id: str, db: Session, explicit: str | None = None) -> str | None:
    if explicit:
        return explicit

    company_settings = _get_company_settings(tenant_id, db)
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
    company_settings = _get_company_settings(tenant_id, db)
    if not company_settings:
        raise HTTPException(status_code=404, detail="Tenant settings not configured yet")

    settings = dict(company_settings.settings or {})
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
    return [
        PrinterInfo(
            port=port.device,
            name=port.name or port.description,
            description=port.description,
            hwid=port.hwid,
        )
        for port in list_ports.comports()
    ]


@router.get("/printing/settings", summary="Get selected printer for tenant")
def get_printing_settings(
    tenant_id: str = Depends(ensure_tenant),
    db: Session = Depends(get_db),
) -> dict[str, Any] | None:
    company_settings = _get_company_settings(tenant_id, db)
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
    label_cfg = payload.label_config.model_dump(exclude_none=True) if payload.label_config else None
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
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "printed": payload.copies,
        "port": port,
    }


@router.get("/printing/receipt-settings", summary="Get receipt template settings")
def get_receipt_settings(
    tenant_id: str = Depends(ensure_tenant),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    company_settings = _get_company_settings(tenant_id, db)
    if not company_settings:
        return {}

    settings = company_settings.settings or {}

    return settings.get(
        "receipt_template",
        {
            "footer_message": "¡Gracias por su compra!",
            "show_tax_breakdown": True,
            "show_cashier": True,
            "show_customer": True,
        },
    )


@router.post("/printing/receipt-settings", summary="Save receipt template settings")
def save_receipt_settings(
    payload: ReceiptSettingsRequest,
    tenant_id: str = Depends(ensure_tenant),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    company_settings = _get_company_settings(tenant_id, db)
    if not company_settings:
        raise HTTPException(status_code=404, detail="Tenant settings not configured yet")

    settings = dict(company_settings.settings or {})
    receipt_template = payload.model_dump()

    settings["receipt_template"] = receipt_template
    company_settings.settings = settings

    db.add(company_settings)
    db.commit()

    return receipt_template


@router.get("/printing/receipt-preview", summary="Get a sample receipt text preview")
def get_receipt_preview(
    tenant_id: str = Depends(ensure_tenant),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    from app.modules.printing.templates.receipt_80mm import (
        PaymentInfo,
        ReceiptData,
        ReceiptLine,
        render_receipt_text,
    )

    company_settings = _get_company_settings(tenant_id, db)

    cfg: dict[str, Any] = {}
    company_name = "Mi Empresa S.A."
    company_address = "Av. Principal 123, Ciudad"
    company_ruc = "1234567890001"

    if company_settings:
        settings = company_settings.settings or {}
        general = settings.get("general", {})

        company_name = general.get("company_name", company_name)
        company_address = general.get("address", company_address)
        company_ruc = general.get("ruc", company_ruc)
        cfg = settings.get("receipt_template", {})

    data = ReceiptData(
        receipt_number="R-000123",
        date=datetime(2026, 3, 17, 10, 30),
        cashier_name="María López",
        register_name="Caja 1",
        company_name=company_name,
        company_address=company_address,
        company_ruc=company_ruc,
        company_phone="(02) 555-1234",
        customer_name="Juan Pérez" if cfg.get("show_customer", True) else None,
        lines=[
            ReceiptLine(
                "Producto A", Decimal("2"), Decimal("15.00"), Decimal("0"), Decimal("0.12")
            ),
            ReceiptLine(
                "Producto B", Decimal("1"), Decimal("25.00"), Decimal("10"), Decimal("0.12")
            ),
            ReceiptLine("Producto C (nombre largo de ejemplo)", Decimal("3"), Decimal("5.50")),
        ],
        payments=[
            PaymentInfo("Efectivo", Decimal("80.00")),
        ],
        footer_message=cfg.get("footer_message", "¡Gracias por su compra!"),
        notes=cfg.get("custom_footer") or None,
    )

    return {"preview": render_receipt_text(data)}


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

    expanded_labels = [
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
        for item in payload.labels
        for _ in range(item.copies)
    ]

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
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "printed": len(expanded_labels),
        "port": port,
    }
