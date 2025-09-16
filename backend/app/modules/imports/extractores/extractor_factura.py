from typing import List
from app.modules.imports.schemas import DocumentoProcesado
from app.modules.imports.extractores.utilidades import (
    buscar_fecha, buscar_numero_factura, buscar_cif, buscar_importe, buscar_numero_mayor,
    buscar_subtotal, buscar_concepto, buscar_descripcion, buscar_emisor, buscar_cliente,
    es_concepto_valido
)


def extraer_factura(texto: str) -> List[DocumentoProcesado]:
    try:
        fecha = buscar_fecha(texto)
        numero = buscar_numero_factura(texto)
        cif = buscar_cif(texto)
        
        total_raw = buscar_importe(texto) or buscar_numero_mayor(texto) or "0.00"
        try:
            total = float(total_raw.replace(",", "."))
        except Exception:
            total = 0.0

        # No usar strip() si puede ser None
        subtotal_raw = buscar_subtotal(texto)
        if subtotal_raw:
            try:
                _ = subtotal_raw.strip()  # Solo para verificar que es válido
            except Exception as e:
                print("❌ Error buscando subtotal:", e)

        descripcion = buscar_descripcion(texto)
        concepto = buscar_concepto(texto)
        emisor = buscar_emisor(texto)
        cliente = buscar_cliente(texto)

        concepto_final = concepto or descripcion or ""
        if not es_concepto_valido(concepto_final):
            concepto_final = "Documento sin concepto"

        return [DocumentoProcesado(
            fecha=fecha or "desconocida",
            concepto=concepto_final,
            tipo="gasto" if total >= 0 else "ingreso",
            importe=total,
            cuenta="desconocida",
            categoria="otros",
            cliente=cliente or "desconocido",
            invoice=numero,
            documentoTipo="factura",
            origen="ocr"
        )]

    except Exception as e:
        print("❌ Error en extraer_factura:", e)
        return []
