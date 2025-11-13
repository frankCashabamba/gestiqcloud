import re
from typing import Optional, List
import unicodedata
from typing import Literal
import hashlib
import json

# Patrones globales
FECHA_PATRONES = [
    r"\b\d{2}[/-]\d{2}[/-]\d{4}\b",
    r"\b\d{4}[/-]\d{2}[/-]\d{2}\b",
    r"(?:\d{1,2})\s*(?:de)?\s*(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s*\d{4}",
    r"(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}",
    r"Date (of issue|paid)?[:\-]?\s*(\w+\s+\d{1,2},?\s+\d{4})",
    r"Fecha (de emisión|valor|de la operación)?[:\-]?\s*(\d{2}[/-]\d{2}[/-]\d{4})",
]

NUMERO_FACTURA_PATRONES = [
    r"(?:Factura|Invoice|Receipt)[^\w]?\s*(?:N[ºo]?)?\s*[:\-]?\s*(\w[\w\-/]*)",
    r"Invoice number\s*[:\-]?\s*(\w[\w\-/]*)",
    r"Receipt number\s*[:\-]?\s*(\w[\w\-/]*)",
    r"\bN[ºo]?\s*[:\-]?\s*(\w[\w\-/]*)",
]

IMPORTE_PATRONES = [
    r"Total\s*[:\-]?\s*(\$|€|usd|eur|mxn|cop)?\s*(-?\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))",
    r"Total amount\s*(due)?\s*[:\-]?\s*(\$|€)?\s*(-?\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))",
    r"Amount (due|paid)?\s*[:\-]?\s*(\$|€)?\s*(-?\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))",
    r"Importe\s*(total|ordenado)?\s*[:\-]?\s*(\$|€)?\s*(-?\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))",
    r"CUOTA.*?(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))",
]

SUBTOTAL_PATRONES = [
    r"Subtotal\s*[:\-]?\s*(\$|€|usd|eur|mxn|cop)?\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))",
    r"\b(\$|€|usd|eur|mxn|cop)?\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))\s+Subtotal\b",
]

CIF_PATRONES = [
    r"\bNIF[:\-]?\s*([A-Z0-9]{8,10})",
    r"\bVAT\s*(Number|No)?[:\-]?\s*([A-Z0-9]+)",
    r"\bCIF[:\-]?\s*([A-Z0-9]{8,10})",
    r"(\b[A-Z]\d{7}[A-Z]?\b)",
]

NUMEROS_DECIMALES = r"-?\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})"


# Utilidades
def buscar(patron: str, texto: str, group: int = 0) -> Optional[str]:
    match = re.search(patron, texto, re.IGNORECASE)
    if not match:
        return None
    try:
        return match.group(group).strip()
    except IndexError:
        return match.group(0).strip()


def buscar_multiple(patrones: List[str], texto: str, group: int = 1) -> Optional[str]:
    for patron in patrones:
        match = re.search(patron, texto, re.IGNORECASE)
        if match:
            if match.lastindex:  # Hay grupos
                try:
                    return match.group(group).strip()
                except IndexError:
                    continue
            else:
                if group == 0:
                    return match.group(0).strip()
                else:
                    continue  # Si esperas grupo 1 pero no hay, intenta otro patrón
    return None


# Tipo de documento
DocumentoTipo = Literal[
    "factura",
    "recibo",
    "transferencia",
    "nómina",
    "presupuesto",
    "contrato",
    "desconocido",
]


def detectar_tipo_documento(texto: str) -> DocumentoTipo:
    def normalizar(t: str) -> str:
        t = unicodedata.normalize("NFD", t)
        return "".join(c for c in t if unicodedata.category(c) != "Mn").lower()

    texto = normalizar(texto)

    def hay(patrones: list[str]) -> bool:
        return any(re.search(p, texto) for p in patrones)

    patrones_recibo = [
        r"recibo",
        r"recib[oi]",
        r"reciec",
        r"receipt",
        r"recept",
        r"paid on",
        r"amount paid",
        r"payment history",
        r"payment received",
        r"thank you for your payment",
        r"visa",
        r"mastercard",
        r"paypal",
    ]
    patrones_transferencia = [
        r"iban",
        r"swift",
        r"beneficiario",
        r"orden de transferencia",
        r"transferencia[s]? (emitidas|realizadas|completadas)",
        r"referencia de pago",
        r"transfer completed",
    ]
    patrones_factura = [
        r"invoice",
        r"billing period",
        r"net amount",
        r"tax",
        r"vat",
        r"amount due",
        r"date of issue",
        r"subtotal",
        r"fecha de emision",
        r"nif",
        r"cif",
    ]
    patrones_nomina = [
        r"nomina",
        r"salario",
        r"sueldo",
        r"cotizaciones",
        r"seguridad social",
        r"retenciones irpf",
        r"base imponible",
        r"periodo de liquidacion",
    ]
    patrones_presupuesto = [
        r"presupuesto",
        r"cotizacion",
        r"estimado",
        r"estimacion de costos",
        r"propuesta economica",
        r"valor aproximado",
    ]
    patrones_contrato = [
        r"contrato",
        r"las partes acuerdan",
        r"vigencia",
        r"clausula",
        r"firmado por",
        r"obligaciones",
        r"rescision",
    ]

    if hay(patrones_recibo):
        return "recibo"
    if hay(patrones_transferencia):
        return "transferencia"
    if hay(patrones_factura):
        return "factura"
    if hay(patrones_nomina):
        return "nómina"
    if hay(patrones_presupuesto):
        return "presupuesto"
    if hay(patrones_contrato):
        return "contrato"

    return "desconocido"


# Extractores
def buscar_fecha(texto: str) -> Optional[str]:
    for patron in FECHA_PATRONES:
        matches = re.findall(patron, texto, flags=re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):  # Caso como ("of issue", "August 2, 2025")
                match = match[-1]  # Tomar la fecha
            return match.strip()
    return None


def buscar_numero_factura(texto: str) -> Optional[str]:
    return buscar_multiple(NUMERO_FACTURA_PATRONES, texto)


def buscar_importe(texto: str) -> Optional[str]:
    for patron in IMPORTE_PATRONES:
        match = re.search(patron, texto, re.IGNORECASE)
        if match:
            for grupo in match.groups():
                if grupo and re.match(NUMEROS_DECIMALES, grupo):
                    return grupo.replace(",", ".")
    return None


def buscar_subtotal(texto: str) -> Optional[str]:
    try:
        return buscar_multiple(SUBTOTAL_PATRONES, texto, group=1)
    except Exception as e:
        print("❌ Error buscando subtotal:", e)
        return None


def buscar_numero_mayor(texto: str) -> Optional[str]:
    numeros = re.findall(NUMEROS_DECIMALES, texto)
    valores = [
        float(num.replace(",", "."))
        for num in numeros
        if float(num.replace(",", ".")) > 0
    ]
    return f"{max(valores):.2f}" if valores else None


def buscar_cif(texto: str) -> Optional[str]:
    numero_factura = buscar_numero_factura(texto)
    matches = re.findall(r"\b[A-Z]\d{7}[A-Z]?\b", texto)
    for match in matches:
        if not numero_factura or match not in numero_factura:
            return match
    return buscar_multiple(CIF_PATRONES, texto, group=-1)


def buscar_concepto(texto: str) -> Optional[str]:
    match = re.search(r"(?i)concepto[:\-]?\s*(.+?)(?=\s+[A-Z][a-z]+\s*:|$)", texto)
    return match.group(1).strip() if match else None


def buscar_descripcion(texto: str) -> Optional[str]:
    match = re.search(r"(?i)description[:\-]?\s*(.+?)(?=\s+[A-Z][a-z]+\s*:|$)", texto)
    if match:
        return match.group(1).strip()
    posibles = re.findall(
        r"(ALQUILER|SERVICIO|PAGO|RENTA|SUSCRIPCIÓN|LICENSE|MONTHLY)",
        texto,
        re.IGNORECASE,
    )
    return posibles[0] if posibles else None


def extraer_bloque(lineas: List[str], indice: int) -> str:
    bloque = [lineas[indice].split(":", 1)[-1].strip()]
    for j in range(indice + 1, min(indice + 4, len(lineas))):
        if not re.match(r"^\s*\w+\s*[:\-]", lineas[j]):
            bloque.append(lineas[j].strip())
        else:
            break
    return " ".join(bloque)


def buscar_emisor(texto: str) -> Optional[str]:
    lineas = texto.splitlines()
    for i, linea in enumerate(lineas):
        if re.search(
            r"^\s*(From|De|Emitido por|Proveedor|Seller|Company name)\b[:\-]?",
            linea,
            re.IGNORECASE,
        ):
            return extraer_bloque(lineas, i)
    return None


def buscar_cliente(texto: str) -> Optional[str]:
    lineas = texto.splitlines()
    for i, linea in enumerate(lineas):
        if re.search(
            r"^\s*(To|Bill to|Para|Destinatario|Cliente)\b[:\-]?", linea, re.IGNORECASE
        ):
            return extraer_bloque(lineas, i)
    return None


def limpiar_valor(valor: str) -> str:
    valor = re.sub(r"\s+", " ", valor)
    valor = re.sub(r"[^\w\s@.,:/()-]", "", valor)
    return valor.strip()[:120]


def corregir_errores_ocr(texto: str) -> str:
    reemplazos = {
        r"CONCERTO": "CONCEPTO",
        r"CONCEPTO[:;]?": "CONCEPTO:",
        r"FERHA|FECHA d2": "FECHA",
        r"Yaldr": "valor",
        r"env[oó@]": "envío",
        r"operacicn|operacidn|operaciin|operarifn": "operación",
        r"Drdenado|Ordenadoc": "ordenado",
        r"@lqvidar|Mquidar|Gquidar|a Mquidar": "a liquidar",
        r"Contsalr|Contrzvalr|Contisvalor|Contisvalor:": "contravalor",
        r"Guenta|Cuenla|Cue": "cuenta",
        r"TITLLAR|Oltimo Beneficiarioc|Ultimd Beneficiario": "titular",
        r"GASTOSPORGVENTA|GAsTOSPORCVENTADe|GasTOS PORCVENTA|GASTOS POR CVENTA": "GASTOS POR CUENTA DE",
        r"ALQULER|ALOULER|ALQUILER HES": "ALQUILER MES",
        r"Nuesta|Nuestra|Nvestra": "Nuestra",
        r"feferencia|relerecia|[[]eferencia": "referencia",
        r"Imfone|Impone|iMporte": "Importe",
        r"liqidar|liquidr|bquidar": "liquidar",
        r"fecho": "fecha",
    }
    for error, fix in reemplazos.items():
        texto = re.sub(error, fix, texto, flags=re.IGNORECASE)
    return texto


def es_concepto_valido(texto: str) -> bool:
    if not texto or len(texto.strip()) < 5:
        return False
    texto_upper = texto.upper()
    if any(
        p in texto_upper
        for p in [
            "IBAN",
            "CUENTA",
            "ENTIDAD",
            "BENEFICIARIO",
            "TITULAR",
            "TIPO OPERACION",
        ]
    ):
        return False
    return True


def dividir_bloques_transferencias(texto: str) -> List[str]:
    """
    Divide el texto en bloques basados en encabezados de transferencia o fechas con errores comunes del OCR.
    """
    texto = corregir_errores_ocr(texto)

    # Patrón más tolerante para fechas y encabezados típicos OCR
    patron = r"(?=(?:\d{2}[-/ ]{1,2}\d{2,3}[-/ ]{1,2}\d{4})|(?:TRANSFERENCIAS\s+EMITIDAS\s+-?\s+ORDEN\s+DE\s+TRANSFERENCIA))"

    bloques = re.split(patron, texto, flags=re.IGNORECASE)
    bloques = [b.strip() for b in bloques if len(b.strip()) > 100]  # eliminamos ruido

    print(f"🧩 Bloques detectados: {len(bloques)}")
    return bloques


def calcular_hash_documento(tenant_id: int, datos: dict) -> str:
    """
    Calcula un hash único por empresa + datos del documento.
    """
    datos_relevantes = {
        "tenant_id": tenant_id,
        "fecha": datos.get("fecha"),
        "concepto": datos.get("concepto"),
        "importe": datos.get("importe"),
        "cliente": datos.get("cliente"),
        "tipo": datos.get("documentoTipo"),  # importante si varía
    }

    json_data = json.dumps(datos_relevantes, sort_keys=True)
    return hashlib.sha256(json_data.encode("utf-8")).hexdigest()
