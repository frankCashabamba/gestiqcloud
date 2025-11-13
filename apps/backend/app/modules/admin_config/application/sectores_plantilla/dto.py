from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class SectorPlantillaIn:
    sector_name: str
    business_type_id: Optional[int] = None
    business_category_id: Optional[int] = None
    template_config: dict = field(default_factory=dict)
    active: bool = True


@dataclass
class SectorPlantillaOut:
    id: int
    sector_name: str
    business_type_id: Optional[int]
    business_category_id: Optional[int]
    template_config: dict
    active: bool
    created_at: datetime
