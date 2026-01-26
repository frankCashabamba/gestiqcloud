"""Country-specific validators for different tax systems."""

from abc import ABC, abstractmethod
from typing import Any


class CountryValidator(ABC):
    """Base validator for country-specific validation."""

    @abstractmethod
    def validate_tax_id(self, tax_id: str) -> list[dict[str, Any]]:
        """Validate tax identification number."""
        pass

    @abstractmethod
    def validate_tax_rates(self, rates: list[float]) -> list[dict[str, Any]]:
        """Validate tax rates allowed by country."""
        pass

    @abstractmethod
    def validate_invoice_number(self, invoice_number: str) -> list[dict[str, Any]]:
        """Validate invoice number format."""
        pass


class ECValidator(CountryValidator):
    """Validator for Ecuador (SRI - Servicio de Rentas Internas)."""

    # Valid IVA rates in Ecuador
    VALID_IVA_RATES = {0.0, 5.0, 12.0, 15.0}

    # Valid ICE rates in Ecuador (partial list)
    VALID_ICE_RATES = {5.0, 10.0, 20.0, 30.0, 100.0}

    def validate_tax_id(self, tax_id: str) -> list[dict[str, Any]]:
        """
        Validate Ecuador RUC (Registro Único de Contribuyentes).

        Format: 13 digits
        Structure:
        - Positions 1-2: Province code (01-24)
        - Positions 3-8: Unique identification
        - Position 9: Type (0=natural, 1=juridical, 6=government)
        - Positions 10-13: Sequential code (establishment)
        """
        errors = []

        if not tax_id:
            return [{"code": "EMPTY_VALUE", "message": "Tax ID cannot be empty"}]

        if not tax_id.isdigit():
            errors.append(
                {"code": "INVALID_TAX_ID_FORMAT", "message": "Tax ID must contain only digits"}
            )
            return errors

        if len(tax_id) != 13:
            errors.append(
                {
                    "code": "INVALID_TAX_ID_FORMAT",
                    "message": f"Tax ID must be 13 digits, got {len(tax_id)}",
                }
            )
            return errors

        # Validate province code (01-24)
        province_code = int(tax_id[:2])
        if province_code < 1 or province_code > 24:
            errors.append(
                {
                    "code": "INVALID_TAX_ID_FORMAT",
                    "message": f"Invalid province code: {province_code}",
                }
            )

        # Validate type digit (position 3: 0, 1, 6, 9)
        type_digit = int(tax_id[2])
        if type_digit not in (0, 1, 6, 9):
            errors.append(
                {
                    "code": "INVALID_TAX_ID_FORMAT",
                    "message": f"Invalid RUC type digit: {type_digit} (must be 0, 1, 6, or 9)",
                }
            )

        # Validate checksum (modulo 11)
        if not self._validate_ruc_checksum(tax_id):
            errors.append(
                {
                    "code": "INVALID_CHECKSUM",
                    "message": "Invalid RUC checksum",
                }
            )

        return errors

    def validate_clave_acceso(self, clave: str) -> list[dict[str, Any]]:
        """
        Validate Ecuador 'Clave de Acceso' (access key).

        Format: 49 digits
        Structure: DDMMYY + RUC(13) + Establishment(3) + Emission(3) + Sequential(9) + Type(2) + Checksum(1)
        """
        errors = []

        if not clave:
            return [{"code": "EMPTY_VALUE", "message": "Clave de Acceso cannot be empty"}]

        if len(clave) != 49:
            errors.append(
                {
                    "code": "INVALID_CLAVE_ACCESO",
                    "message": f"Clave de Acceso must be 49 digits, got {len(clave)}",
                }
            )
            return errors

        if not clave.isdigit():
            errors.append(
                {
                    "code": "INVALID_CLAVE_ACCESO",
                    "message": "Clave de Acceso must contain only digits",
                }
            )
            return errors

        # Validate date portion (DDMMYY)
        day = int(clave[0:2])
        month = int(clave[2:4])
        if day < 1 or day > 31 or month < 1 or month > 12:
            errors.append(
                {
                    "code": "INVALID_CLAVE_ACCESO",
                    "message": f"Invalid date in Clave de Acceso: {day}/{month}",
                }
            )

        return errors

    def validate_tax_rates(self, rates: list[float]) -> list[dict[str, Any]]:
        """Validate that tax rates are allowed in Ecuador."""
        errors = []
        valid_rates = self.VALID_IVA_RATES | self.VALID_ICE_RATES

        for rate in rates:
            if rate not in valid_rates:
                errors.append(
                    {
                        "code": "INVALID_TAX_RATE",
                        "message": f"Tax rate {rate}% not allowed in Ecuador",
                    }
                )

        return errors

    def validate_invoice_number(self, invoice_number: str) -> list[dict[str, Any]]:
        """
        Validate Ecuador invoice number format.

        Format: XXX-XXX-XXXXXXXXX (3-3-9 digits separated by hyphens)
        """
        if not invoice_number:
            return [{"code": "EMPTY_VALUE", "message": "Invoice number cannot be empty"}]

        parts = invoice_number.split("-")
        if len(parts) != 3:
            return [
                {
                    "code": "INVALID_INVOICE_NUMBER_FORMAT",
                    "message": "Invoice number must have format XXX-XXX-XXXXXXXXX",
                }
            ]

        # Validate each part is numeric and correct length
        if not (len(parts[0]) == 3 and parts[0].isdigit()):
            return [
                {
                    "code": "INVALID_INVOICE_NUMBER_FORMAT",
                    "message": "Invoice number format invalid",
                }
            ]

        if not (len(parts[1]) == 3 and parts[1].isdigit()):
            return [
                {
                    "code": "INVALID_INVOICE_NUMBER_FORMAT",
                    "message": "Invoice number format invalid",
                }
            ]

        if not (len(parts[2]) == 9 and parts[2].isdigit()):
            return [
                {
                    "code": "INVALID_INVOICE_NUMBER_FORMAT",
                    "message": "Invoice number format invalid",
                }
            ]

        return []

    @staticmethod
    def _validate_ruc_checksum(ruc: str) -> bool:
        """
        Validate RUC checksum using modulo 11.

        Algorithm based on Ecuador SRI (Servicio de Rentas Internas).

        The check digit is always calculated the same way regardless of type.
        """
        if len(ruc) != 13:
            return False

        # Position-based weights for digits 1-9 (0-indexed: 0-8)
        weights = [3, 2, 7, 6, 5, 4, 3, 2, 7]

        # Calculate checksum for first 9 digits
        total = sum(int(digit) * weight for digit, weight in zip(ruc[:9], weights))
        remainder = total % 11

        # Calculate check digit (same algorithm for all RUC types)
        check_digit = 0 if remainder == 0 else 11 - remainder
        if check_digit == 11:
            check_digit = 0

        # Verify against position 10 (0-indexed: 9)
        return int(ruc[9]) == check_digit

    @staticmethod
    def _validate_clave_checksum(clave: str) -> bool:
        """
        Validate Clave de Acceso checksum using modulo 11.

        Algorithm based on Ecuador SRI electronic document validation.
        """
        if len(clave) != 49:
            return False

        # Weights for clave de acceso (49 digits)
        weights = [7, 6, 5, 4, 3, 2] * 8 + [7, 6, 5, 4, 3, 2]

        # Calculate checksum for first 48 digits
        total = sum(int(digit) * weight for digit, weight in zip(clave[:48], weights[:48]))
        remainder = total % 11

        # Check digit calculation
        check_digit = (11 - remainder) % 11
        if check_digit == 11:
            check_digit = 0

        return int(clave[48]) == check_digit


class ESValidator(CountryValidator):
    """Validator for Spain (AEAT - Agencia Estatal de Administración Tributaria)."""

    # Valid IVA rates in Spain
    VALID_VAT_RATES = {0.0, 4.0, 10.0, 21.0}

    # NIF/NIE letters
    NIF_LETTERS = "TRWAGMYFPDXBNJZSQVHLCKE"
    NIE_LETTERS = "XYZ"

    def validate_tax_id(self, tax_id: str) -> list[dict[str, Any]]:
        """
        Validate Spanish tax ID (NIF, NIE, or CIF).

        - NIF: 8 digits + 1 letter
        - NIE: 1 letter (X, Y, Z) + 7 digits + 1 letter
        - CIF: 1 letter + 7 digits + 1 control character (digit or letter)
        """
        if not tax_id:
            return [{"code": "EMPTY_VALUE", "message": "Tax ID cannot be empty"}]

        tax_id = tax_id.upper().strip()

        # Check if it's NIF
        if tax_id[0].isdigit():
            return self._validate_nif(tax_id)

        # Check if it's NIE
        if tax_id[0] in self.NIE_LETTERS:
            return self._validate_nie(tax_id)

        # Check if it's CIF
        return self._validate_cif(tax_id)

    def validate_tax_rates(self, rates: list[float]) -> list[dict[str, Any]]:
        """Validate that tax rates are allowed in Spain."""
        errors = []

        for rate in rates:
            if rate not in self.VALID_VAT_RATES:
                errors.append(
                    {
                        "code": "INVALID_TAX_RATE",
                        "message": f"VAT rate {rate}% not allowed in Spain",
                    }
                )

        return errors

    def validate_invoice_number(self, invoice_number: str) -> list[dict[str, Any]]:
        """
        Validate Spanish invoice number format.

        Common formats:
        - FAC-2025-0001 (with hyphens)
        - 2025/0001 (with slash)
        - 20250001 (no separators)
        - Max 40 characters
        """
        errors = []

        if not invoice_number:
            return [{"code": "EMPTY_VALUE", "message": "Invoice number cannot be empty"}]

        if len(invoice_number) > 40:
            errors.append(
                {
                    "code": "INVALID_INVOICE_NUMBER_FORMAT",
                    "message": f"Invoice number too long: {len(invoice_number)} characters (max 40)",
                }
            )

        # Check for valid characters (alphanumeric, hyphen, slash)
        if not all(c.isalnum() or c in "-/" for c in invoice_number):
            errors.append(
                {
                    "code": "INVALID_INVOICE_NUMBER_FORMAT",
                    "message": "Invoice number contains invalid characters",
                }
            )

        return errors

    def _validate_nif(self, nif: str) -> list[dict[str, Any]]:
        """Validate Spanish NIF."""
        errors = []

        if len(nif) != 9:
            errors.append(
                {"code": "INVALID_TAX_ID_FORMAT", "message": "NIF must be 8 digits + 1 letter"}
            )
            return errors

        if not nif[:8].isdigit():
            errors.append(
                {"code": "INVALID_TAX_ID_FORMAT", "message": "NIF must start with 8 digits"}
            )
            return errors

        if not nif[8].isalpha():
            errors.append(
                {"code": "INVALID_TAX_ID_FORMAT", "message": "NIF must end with 1 letter"}
            )
            return errors

        # Validate control letter
        number = int(nif[:8])
        expected_letter = self.NIF_LETTERS[number % 23]

        if nif[8] != expected_letter:
            errors.append(
                {
                    "code": "INVALID_TAX_ID_CHECKSUM",
                    "message": f"Invalid NIF letter: expected {expected_letter}, got {nif[8]}",
                }
            )

        return errors

    def _validate_nie(self, nie: str) -> list[dict[str, Any]]:
        """Validate Spanish NIE."""
        errors = []

        if len(nie) != 9:
            errors.append(
                {
                    "code": "INVALID_TAX_ID_FORMAT",
                    "message": "NIE must be 1 letter + 7 digits + 1 letter",
                }
            )
            return errors

        if nie[0] not in self.NIE_LETTERS:
            errors.append(
                {
                    "code": "INVALID_TAX_ID_FORMAT",
                    "message": f"NIE must start with X, Y, or Z, got {nie[0]}",
                }
            )
            return errors

        if not nie[1:8].isdigit():
            errors.append(
                {
                    "code": "INVALID_TAX_ID_FORMAT",
                    "message": "NIE must have 7 digits in positions 2-8",
                }
            )
            return errors

        if not nie[8].isalpha():
            errors.append(
                {"code": "INVALID_TAX_ID_FORMAT", "message": "NIE must end with 1 letter"}
            )
            return errors

        # Validate control letter (same as NIF but with first letter converted to digit)
        nie_number = nie[0].replace("X", "0").replace("Y", "1").replace("Z", "2")
        number = int(nie_number + nie[1:8])
        expected_letter = self.NIF_LETTERS[number % 23]

        if nie[8] != expected_letter:
            errors.append(
                {
                    "code": "INVALID_TAX_ID_CHECKSUM",
                    "message": f"Invalid NIE letter: expected {expected_letter}, got {nie[8]}",
                }
            )

        return errors

    def _validate_cif(self, cif: str) -> list[dict[str, Any]]:
        """Validate Spanish CIF."""
        errors = []

        if len(cif) != 9:
            errors.append(
                {
                    "code": "INVALID_TAX_ID_FORMAT",
                    "message": "CIF must be 1 letter + 7 digits + 1 control character",
                }
            )
            return errors

        if not cif[0].isalpha():
            errors.append(
                {"code": "INVALID_TAX_ID_FORMAT", "message": "CIF must start with a letter"}
            )
            return errors

        if not cif[1:8].isdigit():
            errors.append(
                {
                    "code": "INVALID_TAX_ID_FORMAT",
                    "message": "CIF must have 7 digits in positions 2-8",
                }
            )
            return errors

        if not (cif[8].isdigit() or cif[8].isalpha()):
            errors.append(
                {"code": "INVALID_TAX_ID_FORMAT", "message": "CIF must end with a digit or letter"}
            )
            return errors

        # CIF checksum validation is complex and varies by type, simplified here
        # For now, we just validate format
        return errors
