from typing import List
import re
from app.modules.imports.schemas import DocumentoProcesado
from app.modules.imports.extractores.utilidades import (
    corregir_errores_ocr,
    dividir_bloques_transferencias,
    limpiar_valor,
    es_concepto_valido,
)

def extraer_transferencias(texto: str) -> List[DocumentoProcesado]:
    texto = corregir_errores_ocr(texto)
    bloques = dividir_bloques_transferencias(texto)
    print(f"🔍 TOTAL BLOQUES DETECTADOS: {len(bloques)}")

    resultados: List[DocumentoProcesado] = []

    for i, bloque in enumerate(bloques):
        print(f"\n--- BLOQUE {i+1} ---")
        print(bloque[:1000])

        # Fecha
        fecha_match = re.search(r"\b\d{2}[-/ ]{1,2}\d{2,3}[-/ ]{1,2}\d{4}\b", bloque)
        fecha = limpiar_valor(fecha_match.group(0)) if fecha_match else "desconocida"

        # Importe
        importe = 0.0
        for etiqueta in ["a liquidar", "contravalor", "importe ordenado"]:
            match = re.search(
                fr"{etiqueta}[^\d]{{0,10}}([\d]+[.,]\d{{2}})",
                bloque,
                re.IGNORECASE
            )
            if match:
                valor_raw = match.group(1).replace(",", ".")
                try:
                    valor_float = float(valor_raw)
                    if 10 <= valor_float <= 5000:
                        importe = valor_float
                        break
                except:
                    continue

        # IBAN
        iban_match = re.search(r"\bES\d{2}(?:\s?\d{4}){5}", bloque, re.IGNORECASE)
        cuenta = limpiar_valor(iban_match.group(0).replace(" ", "")) if iban_match else "desconocida"

        # Cliente
        cliente_match = re.search(
            r"TITULAR[:\s]+(.{3,80}?)\s+(?:Tipo operación|Tipo operaci[oó]n|Importe|Contravalor)",
            bloque,
            re.IGNORECASE
        )
        cliente = limpiar_valor(cliente_match.group(1)) if cliente_match else "desconocido"

        # Concepto / descripción
        concepto_final = "Documento sin concepto"
        concepto_match = re.search(r"CONCEPTO[:;\s]+(.{10,150})", bloque, re.IGNORECASE)
        if concepto_match:
            posible = limpiar_valor(concepto_match.group(1))
            posible = re.split(
                r"(cuenta|iban|entidad|importe|titular|tipo operaci[oó]n|beneficiario|fecha|referencia|Nuestra)",
                posible, 1
            )[0]
            if es_concepto_valido(posible):
                concepto_final = posible

        resultados.append(DocumentoProcesado(
            fecha=fecha,
            concepto=concepto_final,
            tipo="gasto",  # Puedes inferir si es ingreso según lógica, por ahora se asume gasto
            importe=importe,
            cuenta=cuenta,
            categoria="otros",
            cliente=cliente,
            invoice=None,
            documentoTipo="transferencia",
            origen="ocr"
        ))

    return resultados
