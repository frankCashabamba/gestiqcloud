"""
E-invoicing Celery Tasks - SRI Ecuador & Facturae España
"""

import base64
import logging
import os
from decimal import Decimal
from typing import Any

# Celery is optional in the minimal test environment. Provide light shims so
# importing this module doesn't fail when celery isn't installed.
_MINIMAL = str(os.getenv("TEST_MINIMAL", "0")).lower() in ("1", "true", "yes")

try:  # pragma: no cover - trivial shim when TEST_MINIMAL
    from celery import Task  # type: ignore
except Exception:  # pragma: no cover
    if _MINIMAL:

        class Task:  # minimal base class to satisfy attribute access
            autoretry_for: tuple[Any, ...] = ()
            retry_kwargs: dict[str, Any] = {}
            retry_backoff: bool = False

    else:
        raise

logger = logging.getLogger(__name__)


class EInvoicingTask(Task):
    """Base task con manejo de errores"""

    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3, "countdown": 60}
    retry_backoff = True


# ============================================================================
# SRI Ecuador
# ============================================================================


def generate_facturae_xml(invoice_data: dict[str, Any]) -> str:
    """
    Generar XML Facturae conforme a especificación española.
    Versión simplificada para MVP.
    """
    from lxml import etree

    # Estructura básica Facturae 3.2
    root = etree.Element(
        "facturae",
        nsmap={
            None: "http://www.facturae.es/Facturae/2009/v3.2/Facturae",
            "ds": "http://www.w3.org/2000/09/xmldsig#",
        },
    )
    root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")

    # FileHeader
    file_header = etree.SubElement(root, "FileHeader")
    etree.SubElement(file_header, "SchemaVersion").text = "3.2"
    etree.SubElement(file_header, "Modality").text = "I"  # Individual
    etree.SubElement(file_header, "InvoiceIssuerType").text = "EM"

    # Parties
    parties = etree.SubElement(root, "Parties")

    # Seller
    seller = etree.SubElement(parties, "SellerParty")
    tax_id_seller = etree.SubElement(seller, "TaxIdentification")
    etree.SubElement(tax_id_seller, "PersonTypeCode").text = "J"  # Jurídica
    etree.SubElement(tax_id_seller, "ResidenceTypeCode").text = "R"  # Residente
    etree.SubElement(tax_id_seller, "TaxIdentificationNumber").text = invoice_data["empresa"]["ruc"]

    # Buyer
    buyer = etree.SubElement(parties, "BuyerParty")
    tax_id_buyer = etree.SubElement(buyer, "TaxIdentification")
    etree.SubElement(tax_id_buyer, "PersonTypeCode").text = "J"
    etree.SubElement(tax_id_buyer, "ResidenceTypeCode").text = "R"
    etree.SubElement(tax_id_buyer, "TaxIdentificationNumber").text = invoice_data["cliente"]["ruc"]

    # Invoices
    invoices = etree.SubElement(root, "Invoices")
    invoice = etree.SubElement(invoices, "Invoice")

    # InvoiceHeader
    header = etree.SubElement(invoice, "InvoiceHeader")
    etree.SubElement(header, "InvoiceNumber").text = invoice_data["numero"]
    etree.SubElement(header, "InvoiceSeriesCode").text = "A"
    etree.SubElement(header, "InvoiceDocumentType").text = "FC"  # Factura completa
    etree.SubElement(header, "InvoiceClass").text = "OO"

    # InvoiceIssueData
    issue_data = etree.SubElement(invoice, "InvoiceIssueData")
    etree.SubElement(issue_data, "IssueDate").text = invoice_data["fecha"].strftime("%Y-%m-%d")

    # TaxesOutputs
    taxes = etree.SubElement(invoice, "TaxesOutputs")
    tax = etree.SubElement(taxes, "Tax")
    etree.SubElement(tax, "TaxTypeCode").text = "01"  # IVA
    etree.SubElement(tax, "TaxRate").text = "21.00"  # TODO: calcular dinámicamente
    etree.SubElement(tax, "TaxableBase").text = f"{invoice_data['subtotal']:.2f}"
    etree.SubElement(tax, "TaxAmount").text = f"{invoice_data['iva']:.2f}"

    # InvoiceTotals
    totals = etree.SubElement(invoice, "InvoiceTotals")
    etree.SubElement(totals, "TaxOutputsTotal").text = f"{invoice_data['iva']:.2f}"
    etree.SubElement(totals, "TotalGrossAmount").text = f"{invoice_data['total']:.2f}"
    etree.SubElement(totals, "TotalGrossAmountBeforeTaxes").text = f"{invoice_data['subtotal']:.2f}"
    etree.SubElement(totals, "TotalTaxesOutputs").text = f"{invoice_data['iva']:.2f}"
    etree.SubElement(totals, "TotalExecutableAmount").text = f"{invoice_data['total']:.2f}"

    return etree.tostring(root, encoding="unicode", pretty_print=True)


def generate_sri_xml(invoice_data: dict[str, Any]) -> str:
    """
    Generar XML RIDE conforme a XSD SRI Ecuador.
    Versión simplificada para MVP - expandir según especificación completa.
    """
    from lxml import etree

    # Estructura básica factura SRI v1.1.0
    root = etree.Element("factura", id="comprobante", version="1.1.0")

    # Info tributaria
    info_trib = etree.SubElement(root, "infoTributaria")
    etree.SubElement(info_trib, "ambiente").text = "1"  # 1=Pruebas, 2=Producción
    etree.SubElement(info_trib, "tipoEmision").text = "1"  # Normal
    etree.SubElement(info_trib, "razonSocial").text = invoice_data["empresa"]["nombre"]
    etree.SubElement(info_trib, "nombreComercial").text = invoice_data["empresa"]["nombre"]
    etree.SubElement(info_trib, "ruc").text = invoice_data["empresa"]["ruc"]
    etree.SubElement(info_trib, "claveAcceso").text = generate_clave_acceso(invoice_data)
    etree.SubElement(info_trib, "codDoc").text = "01"  # 01=Factura
    etree.SubElement(info_trib, "estab").text = "001"  # Establecimiento
    etree.SubElement(info_trib, "ptoEmi").text = "001"  # Punto emisión
    etree.SubElement(info_trib, "secuencial").text = invoice_data["numero"].split("-")[-1].zfill(9)
    etree.SubElement(info_trib, "dirMatriz").text = invoice_data["empresa"].get("direccion", "N/A")

    # Info factura
    info_fact = etree.SubElement(root, "infoFactura")
    etree.SubElement(info_fact, "fechaEmision").text = invoice_data["fecha"].strftime("%d/%m/%Y")
    etree.SubElement(info_fact, "dirEstablecimiento").text = invoice_data["empresa"].get(
        "direccion", "N/A"
    )
    etree.SubElement(info_fact, "obligadoContabilidad").text = "SI"
    etree.SubElement(info_fact, "tipoIdentificacionComprador").text = "05"  # RUC
    etree.SubElement(info_fact, "razonSocialComprador").text = invoice_data["cliente"]["nombre"]
    etree.SubElement(info_fact, "identificacionComprador").text = invoice_data["cliente"]["ruc"]
    etree.SubElement(info_fact, "totalSinImpuestos").text = f"{invoice_data['subtotal']:.2f}"
    etree.SubElement(info_fact, "totalDescuento").text = "0.00"

    # Total con impuestos
    total_impuestos = etree.SubElement(info_fact, "totalConImpuestos")
    total_imp = etree.SubElement(total_impuestos, "totalImpuesto")
    etree.SubElement(total_imp, "codigo").text = "2"  # IVA
    etree.SubElement(total_imp, "codigoPorcentaje").text = "2"  # 12%
    etree.SubElement(total_imp, "baseImponible").text = f"{invoice_data['subtotal']:.2f}"
    etree.SubElement(total_imp, "valor").text = f"{invoice_data['impuesto']:.2f}"

    etree.SubElement(info_fact, "propina").text = "0.00"
    etree.SubElement(info_fact, "importeTotal").text = f"{invoice_data['total']:.2f}"
    etree.SubElement(info_fact, "moneda").text = "DOLAR"

    # Detalles
    detalles = etree.SubElement(root, "detalles")
    for line in invoice_data["lines"]:
        detalle = etree.SubElement(detalles, "detalle")
        etree.SubElement(detalle, "codigoPrincipal").text = line["sku"] or "PROD"
        etree.SubElement(detalle, "descripcion").text = line["descripcion"]
        etree.SubElement(detalle, "cantidad").text = f"{line['cantidad']:.2f}"
        etree.SubElement(detalle, "precioUnitario").text = f"{line['precio_unitario']:.4f}"
        etree.SubElement(detalle, "descuento").text = "0.00"
        etree.SubElement(detalle, "precioTotalSinImpuesto").text = f"{line['total']:.2f}"

        # Impuestos del detalle
        impuestos = etree.SubElement(detalle, "impuestos")
        impuesto = etree.SubElement(impuestos, "impuesto")
        etree.SubElement(impuesto, "codigo").text = "2"  # IVA
        etree.SubElement(impuesto, "codigoPorcentaje").text = "2"  # 12%
        etree.SubElement(impuesto, "tarifa").text = "12"
        etree.SubElement(impuesto, "baseImponible").text = f"{line['total']:.2f}"
        etree.SubElement(impuesto, "valor").text = f"{line['total'] * Decimal('0.12'):.2f}"

    # Info adicional
    info_adicional = etree.SubElement(root, "infoAdicional")
    etree.SubElement(info_adicional, "campoAdicional", nombre="Email").text = invoice_data[
        "cliente"
    ].get("email", "N/A")

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", pretty_print=True).decode(
        "utf-8"
    )


def generate_clave_acceso(invoice_data: dict[str, Any]) -> str:
    """
    Generar clave de acceso SRI (49 dígitos).
    Formato: DDMMYYYYTTCCCCCCCRRRREEEEPPPSSSSSSSSV
    """

    fecha = invoice_data["fecha"]
    dd = fecha.strftime("%d")
    mm = fecha.strftime("%m")
    yyyy = fecha.strftime("%Y")
    tt = "01"  # Tipo comprobante (01=Factura)
    ruc = invoice_data["empresa"]["ruc"]
    ee = "001"  # Establecimiento
    ppp = "001"  # Punto emisión
    ssssssss = invoice_data["numero"].split("-")[-1].zfill(8)
    codigo_num = "12345678"  # Código numérico aleatorio
    tipo_emision = "1"

    # Componer sin dígito verificador
    parcial = f"{dd}{mm}{yyyy}{tt}{ruc}{ee}{ppp}{ssssssss}{codigo_num}{tipo_emision}"

    # Calcular dígito verificador (módulo 11)
    digito = calcular_digito_verificador_modulo11(parcial)

    return parcial + str(digito)


def calcular_digito_verificador_modulo11(cadena: str) -> int:
    """Calcular dígito verificador módulo 11"""
    factor = 2
    suma = 0

    for i in range(len(cadena) - 1, -1, -1):
        suma += int(cadena[i]) * factor
        factor = 7 if factor == 2 else factor - 1

    resto = suma % 11
    digito = 11 - resto

    if digito == 11:
        return 0
    elif digito == 10:
        return 1
    else:
        return digito


def sign_xml_sri(xml_content: str, cert_data: dict[str, Any]) -> str:
    """
    Firmar XML con certificado digital.
    Requiere: signxml, cryptography
    """
    import base64

    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.serialization import pkcs12
    from signxml import XMLSigner

    # Cargar certificado P12
    p12_data = base64.b64decode(cert_data["p12_base64"])
    private_key, certificate, _ = pkcs12.load_key_and_certificates(
        p12_data, cert_data["password"].encode(), backend=default_backend()
    )

    # Firmar XML
    signer = XMLSigner(
        method="enveloped",
        signature_algorithm="rsa-sha1",
        digest_algorithm="sha1",
        c14n_algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315",
    )

    signed = signer.sign(xml_content, key=private_key, cert=certificate)

    return signed.decode("utf-8") if isinstance(signed, bytes) else signed


def send_to_sri(xml_signed: str, env: str = "sandbox") -> dict[str, Any]:
    """Enviar XML firmado al SRI"""
    import requests

    url = (
        "https://cel.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline"
        if env == "production"
        else "https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline"
    )

    headers = {"Content-Type": "text/xml; charset=utf-8"}

    response = requests.post(url, data=xml_signed, headers=headers, timeout=30)

    # Parsear respuesta SOAP
    if response.status_code == 200:
        # Simplificado - implementar parsing SOAP completo
        if "RECIBIDA" in response.text:
            return {"status": "authorized", "message": "Comprobante recibido"}
        else:
            return {"status": "rejected", "message": response.text}
    else:
        return {"status": "error", "message": f"HTTP {response.status_code}"}


# ============================================================================
# Facturae España
# ============================================================================


def sign_facturae_xml(xml_content: str, cert_data: dict[str, Any]) -> str:
    """Firmar XML Facturae con XAdES"""
    # Similar a SRI pero con formato XAdES
    return sign_xml_sri(xml_content, cert_data)


# ============================================================================
# Celery Tasks
# ============================================================================

try:  # pragma: no cover
    from app.celery_app import celery_app  # type: ignore
except Exception:  # Provide no-op task decorator in tests when minimal
    if _MINIMAL:

        class _DummyCeleryApp:
            def task(self, *dargs, **dkwargs):
                def _decorator(fn):
                    return fn

                return _decorator

        celery_app = _DummyCeleryApp()  # type: ignore
    else:
        raise


@celery_app.task(base=EInvoicingTask, name="einvoicing.sign_and_send_sri")
def sign_and_send_sri_task(invoice_id: str, tenant_id: str, env: str = "sandbox"):
    """Tarea: Firmar y enviar factura a SRI Ecuador"""
    from sqlalchemy import text

    from app.config.database import SessionLocal

    db = SessionLocal()
    try:
        # 1. Obtener datos de factura
        query = text(
            """
        SELECT
        f.id, f.numero, f.fecha, f.subtotal, f.iva, f.total,
        t.name as empresa_nombre, t.tax_id as empresa_ruc,
        t.address as empresa_direccion,
        c.name as cliente_nombre, c.identificacion as cliente_ruc,
        c.email as cliente_email
        FROM facturas f
        JOIN tenants t ON t.id = f.tenant_id

        JOIN clientes c ON c.id = f.cliente_id
            WHERE f.id = :invoice_id AND f.tenant_id = :tenant_id
        """
        )

        invoice = db.execute(query, {"invoice_id": invoice_id, "tenant_id": tenant_id}).first()
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")

        # 2. Obtener líneas
        lines_query = text(
            """
        SELECT
        fl.cantidad, fl.precio_unitario, fl.total,
        p.name as descripcion, p.sku
        FROM invoice_lines fl
        LEFT JOIN products p ON p.id = fl.producto_id
        WHERE fl.invoice_id = :invoice_id
        """
        )

        lines = db.execute(lines_query, {"invoice_id": invoice_id}).fetchall()

        # 3. Preparar datos
        invoice_data = {
            "numero": invoice[1],
            "fecha": invoice[2],
            "subtotal": invoice[3],
            "impuesto": invoice[4],
            "total": invoice[5],
            "empresa": {
                "nombre": invoice[6],
                "ruc": invoice[7],
                "direccion": invoice[8],
            },
            "cliente": {"nombre": invoice[9], "ruc": invoice[10], "email": invoice[11]},
            "lines": [
                {
                    "cantidad": line[0],
                    "precio_unitario": line[1],
                    "total": line[2],
                    "descripcion": line[3],
                    "sku": line[4],
                }
                for line in lines
            ],
        }

        # 4. Generar XML
        xml_content = generate_sri_xml(invoice_data)

        # 5. Cargar certificado desde CertificateManager (bridge async -> sync)
        import asyncio

        from app.services.certificate_manager import certificate_manager

        def _get_cert_ec():
            return loop.run_until_complete(certificate_manager.get_certificate(tenant_id, "EC"))

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            cert_info = _get_cert_ec()
        finally:
            try:
                loop.close()
            except Exception:
                pass
        if not cert_info:
            raise ValueError(f"No certificate found for tenant {tenant_id} in Ecuador")

        cert_data = {
            "p12_base64": base64.b64encode(cert_info["cert_data"]).decode(),
            "password": "CERT_PASSWORD",  # TODO: Recuperar de credenciales seguras
        }

        # 6. Firmar
        signed_xml = sign_xml_sri(xml_content, cert_data)

        # 7. Enviar a SRI
        result = send_to_sri(signed_xml, env)

        # 8. Guardar resultado
        clave_acceso = generate_clave_acceso(invoice_data)

        insert_submission = text(
            """
        INSERT INTO sri_submissions (
        tenant_id, invoice_id, payload, receipt_number,
        status, error_message
        )
        VALUES (
        :tenant_id, :invoice_id, :payload, :receipt_number,
        :status, :error_message
        )
        """
        )

        db.execute(
            insert_submission,
            {
                "tenant_id": tenant_id,
                "invoice_id": int(invoice_id),
                "payload": signed_xml,
                "receipt_number": clave_acceso,
                "status": result["status"],
                "error_message": result.get("message"),
            },
        )

        # 9. Actualizar invoice
        if result["status"] == "authorized":
            update_invoice = text(
                """
                UPDATE invoices SET estado = 'einvoice_sent'
                WHERE id = :invoice_id
            """
            )
            db.execute(update_invoice, {"invoice_id": invoice_id})

        db.commit()

        logger.info(f"SRI invoice processed: {invoice_id} -> {result['status']}")

        return {
            "status": result["status"],
            "clave_acceso": clave_acceso,
            "message": result.get("message"),
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error processing SRI invoice {invoice_id}: {e}")
        raise

    finally:
        db.close()


@celery_app.task(base=EInvoicingTask, name="einvoicing.sign_and_send_facturae")
def sign_and_send_facturae_task(invoice_id: str, tenant_id: str, env: str = "sandbox"):
    """Tarea: Firmar y enviar Facturae España"""
    import asyncio

    from sqlalchemy import text

    from app.config.database import SessionLocal

    db = SessionLocal()
    try:
        logger.info(f"Facturae task started: {invoice_id} for tenant {tenant_id}")

        # 1. Obtener datos de factura
        query = text(
            """
            SELECT
                f.id, f.numero, f.fecha, f.subtotal, f.iva, f.total,
                t.name as empresa_nombre, t.tax_id as empresa_ruc,
                t.address as empresa_direccion,
                c.name as cliente_nombre, c.identificacion as cliente_ruc,
                c.email as cliente_email
            FROM facturas f
            JOIN tenants t ON t.id = f.tenant_id

            JOIN clientes c ON c.id = f.cliente_id
            WHERE f.id = :invoice_id AND f.tenant_id = :tenant_id
        """
        )

        invoice = db.execute(query, {"invoice_id": invoice_id, "tenant_id": tenant_id}).first()
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")

        # 2. Preparar datos y generar XML Facturae
        invoice_data = {
            "numero": invoice[1],
            "fecha": invoice[2],
            "subtotal": invoice[3],
            "iva": invoice[4],
            "total": invoice[5],
            "empresa": {
                "nombre": invoice[6],
                "ruc": invoice[7],
                "direccion": invoice[8],
            },
            "cliente": {"nombre": invoice[9], "ruc": invoice[10], "email": invoice[11]},
        }
        xml_content = generate_facturae_xml(invoice_data)

        # 3. Firmar (bridge async -> sync)
        from app.services.certificate_manager import certificate_manager

        def _get_cert():
            return loop.run_until_complete(certificate_manager.get_certificate(tenant_id, "ES"))

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            cert_info = _get_cert()
        finally:
            try:
                loop.close()
            except Exception:
                pass

        if not cert_info:
            raise ValueError(f"No certificate found for tenant {tenant_id} in Spain")

        cert_data = {
            "p12_base64": base64.b64encode(cert_info["cert_data"]).decode(),
            "password": "CERT_PASSWORD",  # TODO: Recuperar de credenciales seguras
        }
        _signed_xml = sign_facturae_xml(xml_content, cert_data)

        # 4. Enviar a AEAT/SII (TODO: implementar)
        result = {"status": "ACCEPTED", "message": "Facturae enviado (stub)"}

        # 5. Guardar resultado en SII batch
        from datetime import datetime

        period = datetime.now().strftime("%Y%m")

        # Insertar en batch
        batch_query = text(
            """
            INSERT INTO sii_batches (tenant_id, period, status)
            VALUES (:tenant_id, :period, 'PENDING')
            ON CONFLICT (tenant_id, period) DO NOTHING
            RETURNING id
        """
        )

        batch_result = db.execute(batch_query, {"tenant_id": tenant_id, "period": period}).first()

        # Si no hay retorno, obtener el batch existente
        if not batch_result:
            existing_batch = db.execute(
                text(
                    """
                SELECT id FROM sii_batches
                WHERE tenant_id = :tenant_id AND period = :period
            """
                ),
                {"tenant_id": tenant_id, "period": period},
            ).first()
            batch_id = existing_batch[0] if existing_batch else None
        else:
            batch_id = batch_result[0]

        # Insertar item en el batch
        if batch_id:
            item_query = text(
                """
                INSERT INTO sii_batch_items (
                    tenant_id, batch_id, invoice_id, status
                ) VALUES (
                    :tenant_id, :batch_id, :invoice_id, :status
                )
            """
            )

            db.execute(
                item_query,
                {
                    "tenant_id": tenant_id,
                    "batch_id": batch_id,
                    "invoice_id": int(invoice_id),
                    "status": result["status"],
                },
            )

        # 6. Actualizar factura
        if result["status"] == "ACCEPTED":
            update_query = text(
                """
                UPDATE facturas
                SET estado = 'posted'
                WHERE id = :invoice_id
            """
            )
            db.execute(update_query, {"invoice_id": invoice_id})

        db.commit()
        return result
    except Exception as e:
        db.rollback()
        logger.error(f"Error Facturae {invoice_id}: {e}")
        raise
    finally:
        db.close()


@celery_app.task(name="einvoicing.send_einvoice")
def send_einvoice_task(invoice_id: str, country: str, env: str = "sandbox"):
    """Tarea unificada: Despachar según país"""

    if country == "EC":
        return sign_and_send_sri_task.delay(invoice_id, env)
    elif country == "ES":
        return sign_and_send_facturae_task.delay(invoice_id, env)
    else:
        raise ValueError(f"País no soportado: {country}")
