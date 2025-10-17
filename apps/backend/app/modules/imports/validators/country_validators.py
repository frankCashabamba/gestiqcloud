import re
from abc import ABC, abstractmethod
from typing import List
from .error_catalog import ERROR_CATALOG, ValidationError


class CountryValidator(ABC):
    """Clase base para validadores fiscales por país."""

    @abstractmethod
    def validate_tax_id(self, tax_id: str) -> List[ValidationError]:
        """Valida formato e integridad de identificación fiscal."""
        pass

    @abstractmethod
    def validate_tax_rates(self, rates: List[float]) -> List[ValidationError]:
        """Valida que las tasas de impuesto sean legales en el país."""
        pass

    @abstractmethod
    def validate_invoice_number(self, number: str) -> List[ValidationError]:
        """Valida formato de numeración de factura."""
        pass

    def _create_error(
        self, code: str, field: str, params: dict
    ) -> ValidationError:
        """Helper para crear errores formateados desde el catálogo."""
        catalog_entry = ERROR_CATALOG[code]
        return ValidationError(
            code=code,
            field=field,
            message=catalog_entry["message_template"].format(**params),
            severity=catalog_entry["severity"],
            params=params,
        )


class ECValidator(CountryValidator):
    """Validador para Ecuador (SRI)."""

    VALID_IVA_RATES = [0.0, 12.0, 15.0]
    VALID_ICE_RATES = [5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 75.0, 100.0, 150.0, 300.0]

    def validate_tax_id(self, tax_id: str) -> List[ValidationError]:
        """Valida RUC ecuatoriano (13 dígitos, módulo 11)."""
        errors = []
        
        if not tax_id or not tax_id.strip():
            return [
                self._create_error(
                    "EMPTY_VALUE",
                    "tax_id",
                    {"field": "tax_id", "value": tax_id or ""},
                )
            ]

        tax_id = tax_id.strip()
        
        if not re.match(r"^\d{13}$", tax_id):
            errors.append(
                self._create_error(
                    "INVALID_TAX_ID_FORMAT",
                    "tax_id",
                    {
                        "value": tax_id,
                        "expected_format": "13 dígitos numéricos (RUC Ecuador)",
                    },
                )
            )
            return errors

        if not self._validate_ruc_checksum(tax_id):
            errors.append(
                self._create_error(
                    "INVALID_TAX_ID_CHECKSUM",
                    "tax_id",
                    {"value": tax_id},
                )
            )

        return errors

    def _validate_ruc_checksum(self, ruc: str) -> bool:
        """Valida dígito verificador del RUC ecuatoriano (algoritmo módulo 11)."""
        if len(ruc) != 13:
            return False

        tipo = int(ruc[2])
        
        if tipo < 6:
            coef = [2, 1, 2, 1, 2, 1, 2, 1, 2]
            digito_verificador = int(ruc[9])
            suma = 0
            for i in range(9):
                producto = int(ruc[i]) * coef[i]
                suma += producto if producto < 10 else producto - 9
            modulo = suma % 10
            esperado = 0 if modulo == 0 else 10 - modulo
            return digito_verificador == esperado
        elif tipo == 6:
            coef = [3, 2, 7, 6, 5, 4, 3, 2]
            digito_verificador = int(ruc[8])
            suma = sum(int(ruc[i]) * coef[i] for i in range(8))
            residuo = suma % 11
            esperado = 0 if residuo == 0 else 11 - residuo
            return digito_verificador == esperado
        elif tipo == 9:
            coef = [4, 3, 2, 7, 6, 5, 4, 3, 2]
            digito_verificador = int(ruc[9])
            suma = sum(int(ruc[i]) * coef[i] for i in range(9))
            residuo = suma % 11
            esperado = 0 if residuo == 0 else 11 - residuo
            return digito_verificador == esperado
        
        return False

    def validate_tax_rates(self, rates: List[float]) -> List[ValidationError]:
        """Valida tasas de IVA e ICE para Ecuador."""
        errors = []
        valid_all = self.VALID_IVA_RATES + self.VALID_ICE_RATES
        
        for rate in rates:
            if rate not in valid_all:
                errors.append(
                    self._create_error(
                        "INVALID_TAX_RATE",
                        "tax_rate",
                        {
                            "rate": rate,
                            "country": "Ecuador",
                            "valid_rates": f"IVA: {self.VALID_IVA_RATES}, ICE: categoría específica",
                        },
                    )
                )
        
        return errors

    def validate_invoice_number(self, number: str) -> List[ValidationError]:
        """Valida formato XXX-XXX-XXXXXXXXX de factura ecuatoriana."""
        errors = []
        
        if not number or not number.strip():
            return [
                self._create_error(
                    "EMPTY_VALUE",
                    "invoice_number",
                    {"field": "invoice_number", "value": ""},
                )
            ]

        number = number.strip()
        
        if not re.match(r"^\d{3}-\d{3}-\d{9}$", number):
            errors.append(
                self._create_error(
                    "INVALID_INVOICE_NUMBER_FORMAT",
                    "invoice_number",
                    {
                        "value": number,
                        "expected_format": "XXX-XXX-XXXXXXXXX (ej: 001-001-000000123)",
                    },
                )
            )
        
        return errors

    def validate_clave_acceso(self, clave: str) -> List[ValidationError]:
        """Valida clave de acceso SRI (49 dígitos, módulo 11)."""
        errors = []
        
        if not clave or not clave.strip():
            return [
                self._create_error(
                    "EMPTY_VALUE",
                    "clave_acceso",
                    {"field": "clave_acceso", "value": ""},
                )
            ]

        clave = clave.strip()
        
        if not re.match(r"^\d{49}$", clave):
            errors.append(
                self._create_error(
                    "INVALID_CLAVE_ACCESO",
                    "clave_acceso",
                    {"value": clave},
                )
            )
            return errors

        if not self._validate_clave_checksum(clave):
            errors.append(
                self._create_error(
                    "INVALID_CLAVE_ACCESO",
                    "clave_acceso",
                    {"value": clave},
                )
            )
        
        return errors

    def _validate_clave_checksum(self, clave: str) -> bool:
        """Valida dígito verificador de clave de acceso (módulo 11)."""
        if len(clave) != 49:
            return False
        
        coef = [2, 3, 4, 5, 6, 7] * 8
        digito_verificador = int(clave[48])
        suma = sum(int(clave[i]) * coef[i] for i in range(48))
        residuo = suma % 11
        esperado = 0 if residuo == 0 else 11 - residuo
        
        return digito_verificador == esperado


class ESValidator(CountryValidator):
    """Validador para España (AEAT)."""

    VALID_IVA_RATES = [0.0, 4.0, 10.0, 21.0]

    def validate_tax_id(self, tax_id: str) -> List[ValidationError]:
        """Valida NIF/CIF/NIE español con letra de control."""
        errors = []
        
        if not tax_id or not tax_id.strip():
            return [
                self._create_error(
                    "EMPTY_VALUE",
                    "tax_id",
                    {"field": "tax_id", "value": tax_id or ""},
                )
            ]

        tax_id = tax_id.strip().upper()
        
        if re.match(r"^[0-9]{8}[A-Z]$", tax_id):
            if not self._validate_nif(tax_id):
                errors.append(
                    self._create_error(
                        "INVALID_TAX_ID_CHECKSUM",
                        "tax_id",
                        {"value": tax_id},
                    )
                )
        elif re.match(r"^[XYZ][0-9]{7}[A-Z]$", tax_id):
            if not self._validate_nie(tax_id):
                errors.append(
                    self._create_error(
                        "INVALID_TAX_ID_CHECKSUM",
                        "tax_id",
                        {"value": tax_id},
                    )
                )
        elif re.match(r"^[A-W][0-9]{7}[0-9A-J]$", tax_id):
            if not self._validate_cif(tax_id):
                errors.append(
                    self._create_error(
                        "INVALID_TAX_ID_CHECKSUM",
                        "tax_id",
                        {"value": tax_id},
                    )
                )
        else:
            errors.append(
                self._create_error(
                    "INVALID_TAX_ID_FORMAT",
                    "tax_id",
                    {
                        "value": tax_id,
                        "expected_format": "NIF (12345678A), CIF (A12345678), o NIE (X1234567A)",
                    },
                )
            )
        
        return errors

    def _validate_nif(self, nif: str) -> bool:
        """Valida NIF español."""
        letras = "TRWAGMYFPDXBNJZSQVHLCKE"
        numero = int(nif[:8])
        letra = nif[8]
        return letras[numero % 23] == letra

    def _validate_nie(self, nie: str) -> bool:
        """Valida NIE español."""
        prefijos = {"X": "0", "Y": "1", "Z": "2"}
        letras = "TRWAGMYFPDXBNJZSQVHLCKE"
        numero = int(prefijos[nie[0]] + nie[1:8])
        letra = nie[8]
        return letras[numero % 23] == letra

    def _validate_cif(self, cif: str) -> bool:
        """Valida CIF español."""
        pares = sum(int(cif[i]) for i in range(2, 8, 2))
        impares = sum(
            sum(divmod(int(cif[i]) * 2, 10)) for i in range(1, 8, 2)
        )
        suma = pares + impares
        unidad = suma % 10
        control = (10 - unidad) % 10
        
        letra_control = "JABCDEFGHI"[control]
        
        return cif[8] == str(control) or cif[8] == letra_control

    def validate_tax_rates(self, rates: List[float]) -> List[ValidationError]:
        """Valida tasas de IVA para España."""
        errors = []
        
        for rate in rates:
            if rate not in self.VALID_IVA_RATES:
                errors.append(
                    self._create_error(
                        "INVALID_TAX_RATE",
                        "tax_rate",
                        {
                            "rate": rate,
                            "country": "España",
                            "valid_rates": ", ".join(f"{r}%" for r in self.VALID_IVA_RATES),
                        },
                    )
                )
        
        return errors

    def validate_invoice_number(self, number: str) -> List[ValidationError]:
        """Valida formato alfanumérico libre de factura española."""
        errors = []
        
        if not number or not number.strip():
            return [
                self._create_error(
                    "EMPTY_VALUE",
                    "invoice_number",
                    {"field": "invoice_number", "value": ""},
                )
            ]

        number = number.strip()
        
        if not re.match(r"^[A-Z0-9\-/]{1,30}$", number, re.IGNORECASE):
            errors.append(
                self._create_error(
                    "INVALID_INVOICE_NUMBER_FORMAT",
                    "invoice_number",
                    {
                        "value": number,
                        "expected_format": "Alfanumérico, hasta 30 caracteres (ej: FAC-2025-001)",
                    },
                )
            )
        
        return errors


def get_validator_for_country(country_code: str) -> CountryValidator:
    """Factory para obtener validador según código de país."""
    validators = {
        "EC": ECValidator,
        "ES": ESValidator,
    }
    
    validator_class = validators.get(country_code.upper())
    if not validator_class:
        raise ValueError(
            f"No hay validador disponible para el país: {country_code}. "
            f"Países soportados: {', '.join(validators.keys())}"
        )
    
    return validator_class()
