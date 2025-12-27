from dataclasses import dataclass

try:
    from typing import Literal
except ImportError:  # python < 3.11
    from typing_extensions import Literal  # type: ignore[assignment]

try:
    import serial  # type: ignore[import]
except ImportError:  # pragma: no cover - runtime dependency
    serial = None  # type: ignore[assignment]


@dataclass
class LabelConfig:
    width_mm: float = 50
    height_mm: float = 40
    label_gap_mm: float = 3
    density: int = 8
    speed: int = 4


@dataclass
class ProductLabel:
    name: str
    barcode: str
    price: str | None = None
    copies: int = 1
    header_text: str | None = None
    footer_text: str | None = None
    offset_xmm: float | None = None
    offset_ymm: float | None = None
    barcode_width: float | None = None
    price_alignment: Literal["left", "center", "right"] | None = None


def _append_text(tspl: list[str], x: int, y: int, font: Literal["0", "3"], size_w: int, size_h: int, content: str) -> None:
    tspl.append(f'TEXT {x},{y},"{font}",0,{size_w},{size_h},"{content}"')


def _append_barcode(tspl: list[str], x: int, y: int, field: ProductLabel) -> None:
    narrow = max(1, min(5, round(field.barcode_width or 2)))
    wide = max(2, min(10, narrow * 2))
    tspl.append(f'BARCODE {x},{y},"128",150,1,0,{narrow},{wide},"{field.barcode}"')


DOTS_PER_MM = 8


def _mm_to_dots(value: float | None) -> int:
    return int(round((value or 0) * DOTS_PER_MM))


def build_tspl_payload(field: ProductLabel, config: LabelConfig) -> str:
    tspl: list[str] = [
        f"SIZE {config.width_mm} mm, {config.height_mm} mm",
        f"GAP {config.label_gap_mm} mm, 0 mm",
        f"DENSITY {config.density}",
        f"SPEED {config.speed}",
        "SET TEAR ON",
        "CLS",
    ]

    x_offset = _mm_to_dots(field.offset_xmm)
    y_offset = _mm_to_dots(field.offset_ymm)

    if field.header_text:
        _append_text(tspl, 10 + x_offset, 5 + y_offset, "3", 1, 1, field.header_text)
    _append_text(tspl, 20 + x_offset, 20 + y_offset, "3", 1, 1, field.name.upper())
    _append_barcode(tspl, 15 + x_offset, 50 + y_offset, field)

    if field.price:
        label_width_dots = int(round(config.width_mm * DOTS_PER_MM))
        base_price_x = 10 + x_offset
        if field.price_alignment == "center":
            price_x = max(base_price_x, label_width_dots // 2 - 20)
        elif field.price_alignment == "right":
            price_x = max(base_price_x, label_width_dots - 60)
        else:
            price_x = base_price_x
        _append_text(tspl, price_x, 260 + y_offset, "3", 2, 2, field.price)
    if field.footer_text:
        _append_text(tspl, 10 + x_offset, 300 + y_offset, "3", 1, 1, field.footer_text)

    tspl.append(f"PRINT {field.copies}")
    return "\r\n".join(tspl) + "\r\n"


def send_to_printer(port: str, payload: str, baudrate: int = 9600) -> None:
    if serial is None:
        raise RuntimeError("pyserial is required; install it with `pip install pyserial`")

    with serial.Serial(port, baudrate=baudrate, timeout=1) as conn:
        conn.write(payload.encode("latin-1", "replace"))
        conn.flush()
