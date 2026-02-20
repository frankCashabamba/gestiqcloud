import re
from datetime import datetime
from typing import Any, Optional

from app.modules.imports.domain.interfaces import CountryRulePack, DocType


class CountryPackRegistry:
    def __init__(self):
        self.packs: dict[str, CountryRulePack] = {}
        self.default_pack = None

    def register(self, pack: CountryRulePack) -> None:
        self.packs[pack.get_country_code()] = pack
        if self.default_pack is None:
            self.default_pack = pack

    def get(self, country_code: str) -> Optional[CountryRulePack]:
        return self.packs.get(country_code, self.default_pack)

    def list_all(self) -> list[str]:
        return list(self.packs.keys())


class BaseCountryPack(CountryRulePack):
    def __init__(self, country_code: str, currency: str):
        self._country_code = country_code
        self._currency = currency
        self._field_aliases = {}
        self._tax_id_patterns = []
        self._date_formats = []

    def get_country_code(self) -> str:
        return self._country_code

    def get_currency(self) -> str:
        return self._currency

    def get_field_aliases(self) -> dict[str, list[str]]:
        return self._field_aliases

    def validate_tax_id(self, tax_id: str) -> tuple[bool, Optional[str]]:
        for pattern in self._tax_id_patterns:
            if re.match(pattern, tax_id):
                return True, None
        return False, f"Invalid tax ID format for {self._country_code}"

    def validate_date_format(self, date_str: str) -> tuple[bool, Optional[str]]:
        for fmt in self._date_formats:
            try:
                datetime.strptime(date_str, fmt)
                return True, None
            except ValueError:
                pass
        return False, f"Invalid date format for {self._country_code}"

    def validate_fiscal_fields(self, data: dict[str, Any]) -> list[dict[str, str]]:
        errors = []

        if "tax_id" in data and data["tax_id"]:
            valid, error = self.validate_tax_id(data["tax_id"])
            if not valid:
                errors.append({"field": "tax_id", "error": error})

        if "invoice_date" in data and data["invoice_date"]:
            valid, error = self.validate_date_format(data["invoice_date"])
            if not valid:
                errors.append({"field": "invoice_date", "error": error})

        if "currency" in data and data["currency"]:
            if data["currency"].upper() != self._currency:
                errors.append({
                    "field": "currency",
                    "error": f"Expected {self._currency}, got {data['currency']}",
                })

        return errors


class EcuadorPack(BaseCountryPack):
    def __init__(self):
        super().__init__("EC", "USD")
        self._tax_id_patterns = [
            r"^\d{10,13}$",
        ]
        self._date_formats = ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"]
        self._field_aliases = {
            "ruc": ["ruc", "tax_id", "cedula"],
            "razon_social": ["razon_social", "company_name"],
            "direccion": ["direccion", "address"],
        }


class SpainPack(BaseCountryPack):
    def __init__(self):
        super().__init__("ES", "EUR")
        self._tax_id_patterns = [
            r"^[A-Z]\d{8}$",
            r"^\d{8}[A-Z]$",
        ]
        self._date_formats = ["%d/%m/%Y", "%Y-%m-%d"]
        self._field_aliases = {
            "cif": ["cif", "tax_id", "nif"],
            "empresa": ["empresa", "company_name"],
            "domicilio": ["domicilio", "address"],
        }


class PeruPack(BaseCountryPack):
    def __init__(self):
        super().__init__("PE", "PEN")
        self._tax_id_patterns = [
            r"^\d{11}$",
        ]
        self._date_formats = ["%d/%m/%Y", "%Y-%m-%d"]
        self._field_aliases = {
            "ruc": ["ruc", "tax_id"],
            "razon_social": ["razon_social", "company_name"],
        }


class MexicoPack(BaseCountryPack):
    def __init__(self):
        super().__init__("MX", "MXN")
        self._tax_id_patterns = [
            r"^[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}$",
        ]
        self._date_formats = ["%d/%m/%Y", "%Y-%m-%d"]
        self._field_aliases = {
            "rfc": ["rfc", "tax_id"],
            "razon_social": ["razon_social", "company_name"],
        }


class BrazilPack(BaseCountryPack):
    def __init__(self):
        super().__init__("BR", "BRL")
        self._tax_id_patterns = [
            r"^\d{11}$",
            r"^\d{14}$",
        ]
        self._date_formats = ["%d/%m/%Y", "%Y-%m-%d"]
        self._field_aliases = {
            "cpf": ["cpf", "tax_id"],
            "cnpj": ["cnpj", "company_tax_id"],
        }


def create_registry() -> CountryPackRegistry:
    registry = CountryPackRegistry()
    registry.register(EcuadorPack())
    registry.register(SpainPack())
    registry.register(PeruPack())
    registry.register(MexicoPack())
    registry.register(BrazilPack())
    return registry
