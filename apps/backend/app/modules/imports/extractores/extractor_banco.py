"""
Extractor para movimientos bancarios: CSV, MT940, CAMT.053.

Soporta múltiples formatos bancarios y normaliza a schema canónico.
"""
from typing import List, Dict, Any, Optional
import csv
import re
from datetime import datetime
from io import StringIO
from app.modules.imports.domain.canonical_schema import (
    CanonicalDocument, build_routing_proposal
)


def extraer_banco_csv(
    content: str,
    country: str = "EC",
    encoding: str = "utf-8"
) -> List[Dict[str, Any]]:
    """
    Extrae movimientos bancarios desde CSV.
    
    Formato esperado:
    fecha,descripcion,referencia,debito,credito,saldo
    2025-01-15,Transferencia recibida,TRX123,,1500.00,5500.00
    2025-01-16,Pago servicios,SRV456,120.00,,5380.00
    
    Args:
        content: Contenido CSV como string
        country: País del banco
        encoding: Codificación del archivo
        
    Returns:
        Lista de CanonicalDocument tipo "bank_tx"
    """
    transactions = []
    
    try:
        reader = csv.DictReader(StringIO(content))
        
        for row in reader:
            # Normalizar nombres de columnas (minúsculas, sin espacios)
            row = {k.strip().lower(): v.strip() for k, v in row.items()}
            
            # Extraer campos principales
            fecha = row.get("fecha") or row.get("date") or row.get("value_date")
            descripcion = row.get("descripcion") or row.get("description") or row.get("narrative") or ""
            referencia = row.get("referencia") or row.get("reference") or row.get("ref")
            
            # Determinar monto y dirección
            debito_str = row.get("debito") or row.get("debit") or "0"
            credito_str = row.get("credito") or row.get("credit") or "0"
            
            debito = float(debito_str.replace(",", ".")) if debito_str else 0.0
            credito = float(credito_str.replace(",", ".")) if credito_str else 0.0
            
            if debito > 0:
                amount = debito
                direction = "debit"
            elif credito > 0:
                amount = credito
                direction = "credit"
            else:
                continue  # Saltar si no hay movimiento
            
            # Normalizar fecha a YYYY-MM-DD
            fecha_norm = _normalize_date(fecha)
            
            canonical: CanonicalDocument = {
                "doc_type": "bank_tx",
                "country": country,
                "currency": "USD" if country == "EC" else "EUR",
                "issue_date": fecha_norm,
                "bank_tx": {
                    "amount": amount,
                    "direction": direction,
                    "value_date": fecha_norm or "",
                    "narrative": descripcion,
                    "external_ref": referencia,
                },
                "source": "csv",
                "confidence": 0.95,  # CSV es muy preciso
            }
            
            # Propuesta de enrutamiento
            canonical["routing_proposal"] = build_routing_proposal(
                canonical,
                category_code=_categorize_narrative(descripcion),
                confidence=0.70
            )
            
            transactions.append(canonical)
    
    except Exception as e:
        print(f"❌ Error procesando CSV bancario: {e}")
        return []
    
    return transactions


def extraer_banco_mt940(content: str, country: str = "EC") -> List[Dict[str, Any]]:
    """
    Extrae movimientos desde formato MT940 (SWIFT).
    
    Estructura básica:
    :20:REF123
    :25:ACCOUNT/123456
    :28C:1/1
    :60F:C250115USD5000,00
    :61:2501150115DR120,00NTRFREF123//TRX456
    :86:Pago servicios básicos
    :62F:C250115USD4880,00
    
    Args:
        content: Contenido MT940 como string
        country: País del banco
        
    Returns:
        Lista de CanonicalDocument tipo "bank_tx"
    """
    transactions = []
    
    try:
        # Parsear bloques :61: (transacciones) y :86: (detalles)
        tx_blocks = re.findall(r':61:(.+?)(?=:(?:61|62|86))', content, re.DOTALL)
        detail_blocks = re.findall(r':86:(.+?)(?=:(?:61|86|62|-))', content, re.DOTALL)
        
        for idx, tx_block in enumerate(tx_blocks):
            # :61: formato: YYMMDDMMDDCRAMOUNT[,DECIMAL]NTRF[REF]//[DETAILS]
            match = re.match(
                r'(\d{6})(\d{4})?(C|D)R?(\d+),(\d{2})([A-Z]{4})',
                tx_block.replace('\n', '').strip()
            )
            
            if not match:
                continue
            
            date_str, _, dc_mark, amount_int, amount_dec, tx_code = match.groups()
            
            # Parsear fecha YYMMDD
            fecha_norm = f"20{date_str[0:2]}-{date_str[2:4]}-{date_str[4:6]}"
            
            # Dirección y monto
            direction = "credit" if dc_mark == "C" else "debit"
            amount = float(f"{amount_int}.{amount_dec}")
            
            # Narrativa desde bloque :86:
            narrative = detail_blocks[idx].strip() if idx < len(detail_blocks) else "Movimiento bancario"
            
            canonical: CanonicalDocument = {
                "doc_type": "bank_tx",
                "country": country,
                "currency": "USD" if country == "EC" else "EUR",
                "issue_date": fecha_norm,
                "bank_tx": {
                    "amount": amount,
                    "direction": direction,
                    "value_date": fecha_norm,
                    "narrative": narrative.replace('\n', ' '),
                    "external_ref": tx_code,
                },
                "source": "mt940",
                "confidence": 0.90,
            }
            
            canonical["routing_proposal"] = build_routing_proposal(
                canonical,
                category_code=_categorize_narrative(narrative),
                confidence=0.65
            )
            
            transactions.append(canonical)
    
    except Exception as e:
        print(f"❌ Error procesando MT940: {e}")
        return []
    
    return transactions


def extraer_banco_camt053(content: str, country: str = "EC") -> List[Dict[str, Any]]:
    """
    Extrae movimientos desde formato CAMT.053 (ISO 20022 XML).
    
    Estructura simplificada:
    <Ntry>
      <Amt Ccy="USD">120.00</Amt>
      <CdtDbtInd>DBIT</CdtDbtInd>
      <ValDt><Dt>2025-01-15</Dt></ValDt>
      <NtryDtls>
        <TxDtls>
          <RmtInf><Ustrd>Pago servicios</Ustrd></RmtInf>
        </TxDtls>
      </NtryDtls>
    </Ntry>
    
    Args:
        content: XML CAMT.053 como string
        country: País del banco
        
    Returns:
        Lista de CanonicalDocument tipo "bank_tx"
    """
    transactions = []
    
    try:
        # Parsear entries <Ntry>
        entries = re.findall(r'<Ntry>(.*?)</Ntry>', content, re.DOTALL)
        
        for entry in entries:
            # Amount
            amt_match = re.search(r'<Amt Ccy="([A-Z]{3})">([0-9.]+)</Amt>', entry)
            if not amt_match:
                continue
            currency, amount_str = amt_match.groups()
            amount = float(amount_str)
            
            # Credit/Debit
            cd_match = re.search(r'<CdtDbtInd>(CRDT|DBIT)</CdtDbtInd>', entry)
            direction = "credit" if cd_match and cd_match.group(1) == "CRDT" else "debit"
            
            # Value date
            date_match = re.search(r'<ValDt><Dt>([0-9-]+)</Dt></ValDt>', entry)
            value_date = date_match.group(1) if date_match else None
            
            # Narrative
            narr_match = re.search(r'<Ustrd>(.*?)</Ustrd>', entry)
            narrative = narr_match.group(1).strip() if narr_match else "Movimiento bancario"
            
            # Reference
            ref_match = re.search(r'<EndToEndId>(.*?)</EndToEndId>', entry)
            ref = ref_match.group(1) if ref_match else None
            
            canonical: CanonicalDocument = {
                "doc_type": "bank_tx",
                "country": country,
                "currency": currency,
                "issue_date": value_date,
                "bank_tx": {
                    "amount": amount,
                    "direction": direction,
                    "value_date": value_date or "",
                    "narrative": narrative,
                    "external_ref": ref,
                },
                "source": "camt053",
                "confidence": 0.95,
            }
            
            canonical["routing_proposal"] = build_routing_proposal(
                canonical,
                category_code=_categorize_narrative(narrative),
                confidence=0.70
            )
            
            transactions.append(canonical)
    
    except Exception as e:
        print(f"❌ Error procesando CAMT.053: {e}")
        return []
    
    return transactions


# ============================================================================
# Helpers
# ============================================================================

def _normalize_date(date_str: Optional[str]) -> Optional[str]:
    """Normaliza fecha a formato YYYY-MM-DD."""
    if not date_str:
        return None
    
    # Intentar varios formatos comunes
    formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d-%m-%Y",
        "%Y%m%d",
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    
    return date_str  # Devolver original si no se puede parsear


def _categorize_narrative(narrative: str) -> str:
    """Categoriza automáticamente por narrativa usando keywords."""
    narrative_lower = narrative.lower()
    
    if any(kw in narrative_lower for kw in ["gasolina", "combustible", "fuel", "gas"]):
        return "FUEL"
    elif any(kw in narrative_lower for kw in ["luz", "agua", "internet", "servicios", "utilities"]):
        return "UTILITIES"
    elif any(kw in narrative_lower for kw in ["nómina", "salario", "payroll", "salary"]):
        return "PAYROLL"
    elif any(kw in narrative_lower for kw in ["alquiler", "rent", "arriendo"]):
        return "RENT"
    elif any(kw in narrative_lower for kw in ["proveedor", "supplier", "compra"]):
        return "SUPPLIES"
    else:
        return "OTHER"
