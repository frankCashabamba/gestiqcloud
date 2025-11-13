"""
Parser para extractos bancarios ISO 20022 CAMT.053 (XML).

Formato estándar para transacciones bancarias en Europa y América Latina.

Salida: lista de CanonicalDocument con doc_type='bank_tx'
"""

import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional


def parse_xml_camt053_bank(file_path: str) -> Dict[str, Any]:
    """
    Parse ISO 20022 CAMT.053 XML file with bank transactions.
    
    Args:
        file_path: Path to CAMT.053 XML file
        
    Returns:
        Dict with 'bank_transactions' list and metadata
    """
    transactions = []
    errors = []
    
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # CAMT.053 namespace
        ns = _detect_camt_namespace(root)
        
        # Extraer todas las transacciones del documento
        transactions = _extract_camt_transactions(root, ns)
        
    except ET.ParseError as e:
        errors.append(f"Error parsing XML: {str(e)}")
    except Exception as e:
        errors.append(f"Unexpected error: {str(e)}")
    
    return {
        "bank_transactions": transactions,
        "errors": errors,
        "rows_processed": len(transactions),
        "rows_parsed": len(transactions),
        "source_type": "xml",
        "parser": "xml_camt053_bank",
    }


def _detect_camt_namespace(root: ET.Element) -> Dict[str, str]:
    """Detectar namespace CAMT.053."""
    ns = {"camt": "urn:iso:std:iso:20022:tech:xsd:camt.053.001.02"}
    
    # Intentar extraer del tag raíz
    if root.tag.startswith("{"):
        detected_ns = root.tag.split("}")[0][1:]
        if "camt" in detected_ns or "053" in detected_ns:
            ns["camt"] = detected_ns
    
    return ns


def _extract_camt_transactions(root: ET.Element, ns: Dict[str, str]) -> List[Dict[str, Any]]:
    """Extraer transacciones del documento CAMT.053."""
    camt_ns = ns.get("camt", "urn:iso:std:iso:20022:tech:xsd:camt.053.001.02")
    
    def tag(name: str) -> str:
        return f"{{{camt_ns}}}{name}"
    
    transactions = []
    
    try:
        # Navegar a Statement -> AccountStatement -> Entry
        statements = root.findall(f".//{tag('Stmt')}")
        if not statements:
            statements = root.findall(f".//{tag('Document')}/{tag('BkToCstmrStmt')}/{tag('Stmt')}")
        
        for stmt in statements:
            entries = stmt.findall(f".//{tag('Ntry')}")
            
            for entry in entries:
                # Fecha de transacción
                booking_date = _get_text(entry, f"{tag('BookgDt')}/{tag('Dt')}")
                value_date = _get_text(entry, f"{tag('ValDt')}/{tag('Dt')}")
                
                # Monto y dirección
                amount_elem = entry.find(f"{tag('Amt')}")
                amount = _to_float(_get_text(amount_elem, ".")) if amount_elem is not None else 0.0
                
                debit_credit = _get_text(entry, f"{tag('CdtDbtInd')}")
                direction = "credit" if debit_credit == "CRDT" else "debit"
                
                # Concepto/narrativa
                purpose = _get_text(entry, f".//{tag('Pstd')}/{tag('Ustrd')}")
                if not purpose:
                    purpose = _get_text(entry, f".//{tag('RmtInf')}/{tag('Ustrd')}")
                if not purpose:
                    purpose = _get_text(entry, f".//{tag('Purpose')}/{tag('Cd')}")
                
                # Referencia
                reference = _get_text(entry, f"{tag('AcctSvcrRef')}")
                
                # Contraparte
                counterparty = None
                bnf = entry.find(f".//{tag('BnfcryAcct')}")
                if bnf is not None:
                    counterparty = _get_text(bnf, f"{tag('Nm')}")
                
                # IBAN
                iban = None
                iban_elem = entry.find(f".//{tag('IBAN')}")
                if iban_elem is not None:
                    iban = _get_text(iban_elem, ".")
                
                # Moneda
                currency = "EUR"  # Default
                if amount_elem is not None and "Ccy" in amount_elem.attrib:
                    currency = amount_elem.attrib.get("Ccy", "EUR")
                
                # Construir documento canónico
                transaction = {
                    "doc_type": "bank_tx",
                    "issue_date": booking_date or value_date,
                    "currency": currency,
                    "bank_tx": {
                        "amount": abs(amount),
                        "direction": direction,
                        "value_date": value_date or booking_date,
                        "narrative": purpose or "Bank transaction",
                        "counterparty": counterparty,
                        "external_ref": reference,
                    },
                    "payment": {"iban": iban} if iban else {},
                    "source": "camt053",
                    "confidence": 0.95,
                    "_metadata": {"parser": "xml_camt053_bank"}
                }
                
                # Limpiar nulos
                transaction = _clean_dict(transaction)
                transactions.append(transaction)
        
    except Exception as e:
        pass  # Silenciar errores en parsing específico
    
    return transactions


def _get_text(elem: Optional[ET.Element], xpath: str) -> Optional[str]:
    """Obtener texto de un elemento."""
    if elem is None:
        return None
    try:
        if xpath == ".":
            return elem.text
        found = elem.findtext(xpath)
        return found if found else None
    except Exception:
        return None


def _to_float(val) -> float | None:
    """Convertir a float."""
    if val is None or val == "":
        return None
    try:
        return float(str(val).replace(",", "."))
    except (ValueError, TypeError):
        return None


def _clean_dict(d: Dict) -> Dict:
    """Remover keys con valores None o dicts vacíos."""
    if not isinstance(d, dict):
        return d
    return {
        k: _clean_dict(v) if isinstance(v, dict) else v
        for k, v in d.items()
        if v is not None 
        and v != "" 
        and (not isinstance(v, dict) or any(_clean_dict(v).values()))
    }
