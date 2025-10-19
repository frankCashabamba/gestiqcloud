# Plan de Migración e Implementación — GestiQCloud MVP

> **Objetivo**: Integrar el SPEC completo del ERP/CRM multi-tenant con la arquitectura existente del proyecto

## ✅ Estado Actual: Lo que YA tienes funcionando

### Backend (FastAPI + SQLAlchemy)
- ✅ Multi-tenant con RLS y GUC `app.tenant_id`
- ✅ Tabla `tenants` (UUID) mapeada a `core_empresa` (int)
- ✅ Sistema de migraciones automáticas (ops/migrations/)
- ✅ Módulo imports completo (batch/validación/promoción)
- ✅ Inventario con `stock_items`, `stock_moves`, `warehouses`
- ✅ Facturación básica: `invoices`, `invoice_lines`
- ✅ Celery worker + Redis
- ✅ E-factura stub (tablas `sri_submissions`, `sii_batches`)

### Frontend
- ✅ Admin PWA (React + Vite)
- ✅ Tenant PWA con Service Worker (Workbox)
- ✅ Offline-lite: outbox para writes + caché para GETs

### Infraestructura
- ✅ Docker Compose con Postgres 15
- ✅ Edge Gateway (Cloudflare Worker)
- ✅ Migraciones con RLS policies aplicadas

---

## 🎯 Roadmap de Implementación

### **FASE M1 — POS + Facturación + Impresión** (2 semanas)

#### Backend (Días 1-6)
**1. Verificar/aplicar migraciones POS existentes**
```bash
# Verificar si ya existe
ls ops/migrations/2025-10-10_090_pos/

# Si existe, verificar que se aplicó
docker exec db psql -U postgres -d gestiqclouddb_dev -c "\d pos_receipts"

# Si no existe, crear migración nueva
python scripts/py/bootstrap_imports.py --dir ops/migrations
```

**2. Crear endpoints POS**

Archivo: `apps/backend/app/routers/pos.py`
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.middleware.tenant import ensure_tenant
from app.models.pos import PosReceipt, PosReceiptLine, PosPayment
from app.models.core.facturacion import Invoice, InvoiceLine
from app.schemas.pos import ReceiptToInvoiceRequest
from uuid import UUID

router = APIRouter(prefix="/api/v1/pos", tags=["pos"])

@router.post("/receipts/{receipt_id}/to_invoice")
def ticket_to_invoice(
    receipt_id: UUID,
    data: ReceiptToInvoiceRequest,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant)
):
    """Convertir ticket POS a factura"""
    # 1. Obtener receipt
    receipt = db.query(PosReceipt).filter(
        PosReceipt.id == receipt_id,
        PosReceipt.tenant_id == tenant_id
    ).first()
    
    if not receipt:
        raise HTTPException(404, "Ticket no encontrado")
    
    if receipt.invoice_id:
        raise HTTPException(400, "Ticket ya facturado")
    
    # 2. Crear o buscar cliente
    from app.models.core.clients import Cliente
    customer = db.query(Cliente).filter(
        Cliente.tax_id == data.customer.tax_id,
        Cliente.empresa_id == get_empresa_id_from_tenant(tenant_id, db)
    ).first()
    
    if not customer:
        customer = Cliente(
            empresa_id=get_empresa_id_from_tenant(tenant_id, db),
            nombre=data.customer.name,
            tax_id=data.customer.tax_id,
            pais=data.customer.country
        )
        db.add(customer)
        db.flush()
    
    # 3. Asignar número de factura
    from app.services.numbering import assign_doc_number
    doc_number = assign_doc_number(
        db=db,
        tenant_id=tenant_id,
        doc_type='F',
        register_id=receipt.register_id
    )
    
    # 4. Crear Invoice
    invoice = Invoice(
        empresa_id=customer.empresa_id,
        numero=doc_number,
        cliente_id=customer.id,
        fecha=receipt.created_at.date(),
        subtotal=receipt.gross_total - receipt.tax_total,
        impuesto=receipt.tax_total,
        total=receipt.gross_total,
        estado='posted'
    )
    db.add(invoice)
    db.flush()
    
    # 5. Copiar líneas
    receipt_lines = db.query(PosReceiptLine).filter(
        PosReceiptLine.receipt_id == receipt_id
    ).all()
    
    for line in receipt_lines:
        invoice_line = InvoiceLine(
            invoice_id=invoice.id,
            producto_id=line.product_id,
            cantidad=line.qty,
            precio_unitario=line.unit_price,
            impuesto_tasa=line.tax_rate,
            descuento=line.discount_pct,
            total=line.line_total
        )
        db.add(invoice_line)
    
    # 6. Linkear receipt → invoice
    receipt.invoice_id = invoice.id
    receipt.status = 'invoiced'
    
    db.commit()
    
    return {
        "invoice_id": str(invoice.id),
        "numero": invoice.numero,
        "pdf_url": f"/api/v1/invoices/{invoice.id}/pdf"
    }

@router.get("/receipts/{receipt_id}/print")
def print_receipt(
    receipt_id: UUID,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
    width: int = 58  # 58mm o 80mm
):
    """Generar HTML para impresión térmica"""
    receipt = db.query(PosReceipt).filter(
        PosReceipt.id == receipt_id,
        PosReceipt.tenant_id == tenant_id
    ).first()
    
    if not receipt:
        raise HTTPException(404, "Ticket no encontrado")
    
    # Cargar líneas
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader('app/templates'))
    template = env.get_template(f'pos/ticket_{width}mm.html')
    
    html = template.render(
        ticket=receipt,
        lines=receipt.lines,
        empresa=get_empresa_data(tenant_id, db)
    )
    
    return HTMLResponse(content=html)

@router.post("/receipts/{receipt_id}/refund")
def refund_receipt(
    receipt_id: UUID,
    data: RefundRequest,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant)
):
    """Procesar devolución y crear vale si aplica"""
    receipt = db.query(PosReceipt).filter(
        PosReceipt.id == receipt_id,
        PosReceipt.tenant_id == tenant_id
    ).first()
    
    if not receipt or receipt.status != 'paid':
        raise HTTPException(400, "Ticket no válido para devolución")
    
    # Crear movimientos de stock inversos
    from app.models.inventory.stock import StockMove
    for line in receipt.lines:
        move = StockMove(
            tenant_id=tenant_id,
            kind='refund',
            product_id=line.product_id,
            qty=line.qty,
            ref_doc_type='receipt',
            ref_doc_id=receipt_id,
            posted_at=datetime.utcnow()
        )
        db.add(move)
    
    # Si reembolso es vale
    if data.refund_method == 'store_credit':
        from app.models.pos import StoreCredit
        import secrets
        credit = StoreCredit(
            tenant_id=tenant_id,
            code=secrets.token_urlsafe(12),
            customer_id=receipt.customer_id,
            currency=receipt.currency,
            amount_initial=receipt.gross_total,
            amount_remaining=receipt.gross_total,
            expires_at=datetime.utcnow().date() + timedelta(days=365),
            status='active'
        )
        db.add(credit)
        db.flush()
        
        # Evento de emisión
        from app.models.pos import StoreCreditEvent
        event = StoreCreditEvent(
            credit_id=credit.id,
            type='issue',
            amount=credit.amount_initial,
            ref_doc_type='refund',
            ref_doc_id=receipt_id
        )
        db.add(event)
    
    receipt.status = 'refunded'
    db.commit()
    
    return {"status": "ok", "store_credit_code": credit.code if data.refund_method == 'store_credit' else None}
```

**3. Servicio de numeración**

Archivo: `apps/backend/app/services/numbering.py`
```python
from sqlalchemy.orm import Session
from sqlalchemy import text
from uuid import UUID

def assign_doc_number(
    db: Session,
    tenant_id: str,
    doc_type: str,  # 'R' receipt, 'F' factura, 'C' abono
    register_id: UUID = None
) -> str:
    """Asignar número de documento con serie"""
    
    # Transacción para evitar race conditions
    with db.begin_nested():
        # Buscar serie activa
        query = text("""
            SELECT id, name, current_no 
            FROM doc_series 
            WHERE tenant_id = :tenant_id 
              AND doc_type = :doc_type 
              AND (:register_id IS NULL OR register_id = :register_id)
              AND active = true
            ORDER BY created_at DESC
            LIMIT 1
            FOR UPDATE
        """)
        
        result = db.execute(
            query,
            {"tenant_id": tenant_id, "doc_type": doc_type, "register_id": register_id}
        ).first()
        
        if not result:
            raise ValueError(f"No hay serie activa para doc_type={doc_type}")
        
        series_id, series_name, current_no = result
        next_no = current_no + 1
        
        # Actualizar contador
        update = text("""
            UPDATE doc_series 
            SET current_no = :next_no 
            WHERE id = :series_id
        """)
        db.execute(update, {"next_no": next_no, "series_id": series_id})
        
        # Formato: SERIE-0001
        return f"{series_name}-{next_no:04d}"
```

**4. Schemas Pydantic**

Archivo: `apps/backend/app/schemas/pos.py`
```python
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional

class CustomerQuick(BaseModel):
    name: str
    tax_id: str
    country: str = "EC"
    address: Optional[str] = None

class ReceiptToInvoiceRequest(BaseModel):
    customer: CustomerQuick
    series: Optional[str] = None

class RefundRequest(BaseModel):
    refund_method: str = Field(..., pattern="^(cash|card|store_credit)$")
    reason: str
```

**5. Plantilla HTML 58mm**

Archivo: `apps/backend/app/templates/pos/ticket_58mm.html`
```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        @page {
            width: 58mm;
            margin: 0;
        }
        body {
            width: 48mm;
            font-family: 'Courier New', monospace;
            font-size: 9pt;
            margin: 5mm 5mm;
            line-height: 1.2;
        }
        .header {
            text-align: center;
            font-weight: bold;
            margin-bottom: 3mm;
        }
        .info {
            font-size: 8pt;
            margin-bottom: 3mm;
        }
        .line {
            display: flex;
            justify-content: space-between;
            margin: 1mm 0;
        }
        .line-desc {
            flex: 1;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .line-price {
            text-align: right;
            min-width: 15mm;
        }
        .separator {
            border-top: 1px dashed #000;
            margin: 3mm 0;
        }
        .total {
            font-weight: bold;
            font-size: 11pt;
        }
        .footer {
            text-align: center;
            font-size: 7pt;
            margin-top: 5mm;
        }
    </style>
</head>
<body>
    <div class="header">
        {{ empresa.nombre }}
    </div>
    <div class="info">
        RUC/NIF: {{ empresa.ruc }}<br>
        Ticket: {{ ticket.number }}<br>
        Fecha: {{ ticket.created_at.strftime('%d/%m/%Y %H:%M') }}
    </div>
    
    <div class="separator"></div>
    
    {% for line in lines %}
    <div class="line">
        <span class="line-desc">
            {{ line.product.nombre }}<br>
            {{ line.qty }} x {{ "%.2f"|format(line.unit_price) }}
        </span>
        <span class="line-price">{{ "%.2f"|format(line.line_total) }}</span>
    </div>
    {% endfor %}
    
    <div class="separator"></div>
    
    <div class="line">
        <span>SUBTOTAL</span>
        <span>{{ "%.2f"|format(ticket.gross_total - ticket.tax_total) }}</span>
    </div>
    <div class="line">
        <span>IVA</span>
        <span>{{ "%.2f"|format(ticket.tax_total) }}</span>
    </div>
    <div class="line total">
        <span>TOTAL</span>
        <span>{{ "%.2f"|format(ticket.gross_total) }} {{ ticket.currency }}</span>
    </div>
    
    <div class="footer">
        ¡Gracias por su compra!<br>
        www.{{ empresa.dominio }}
    </div>
</body>
</html>
```

#### Frontend (Días 7-14)

**1. Crear módulo POS**

Archivo: `apps/tenant/src/pages/pos/POSView.tsx`
```tsx
import { useState, useEffect } from 'react';
import { BarcodeScanner } from '@/components/BarcodeScanner';
import { useOutbox } from '@/hooks/useOutbox';

export default function POSView() {
  const [shift, setShift] = useState(null);
  const [cart, setCart] = useState([]);
  const [scanning, setScanning] = useState(false);
  const { addToQueue, syncStatus } = useOutbox();
  
  const openShift = async (openingFloat: number) => {
    const shiftData = {
      register_id: localStorage.getItem('register_id'),
      opened_by: getCurrentUserId(),
      opening_float: openingFloat,
      opened_at: new Date().toISOString()
    };
    
    try {
      const response = await fetch('/api/v1/pos/shifts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(shiftData)
      });
      const shift = await response.json();
      setShift(shift);
    } catch (err) {
      // Si offline, guardar en outbox
      addToQueue('POST', '/api/v1/pos/shifts', shiftData);
      setShift({ ...shiftData, id: crypto.randomUUID(), offline: true });
    }
  };
  
  const addProduct = async (code: string) => {
    // Buscar producto (caché o API)
    const product = await fetchProduct(code);
    setCart([...cart, { ...product, qty: 1 }]);
  };
  
  const checkout = async (paymentMethod: string) => {
    const receipt = {
      register_id: shift.register_id,
      shift_id: shift.id,
      number: generateTempNumber(),
      lines: cart.map(item => ({
        product_id: item.id,
        qty: item.qty,
        unit_price: item.price,
        tax_rate: item.tax_rate,
        line_total: item.qty * item.price
      })),
      payments: [{
        method: paymentMethod,
        amount: calculateTotal()
      }],
      gross_total: calculateTotal(),
      tax_total: calculateTax(),
      currency: 'USD'
    };
    
    try {
      const response = await fetch('/api/v1/pos/receipts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(receipt)
      });
      const saved = await response.json();
      
      // Imprimir
      window.open(`/api/v1/pos/receipts/${saved.id}/print`, '_blank');
      
      setCart([]);
    } catch (err) {
      addToQueue('POST', '/api/v1/pos/receipts', receipt);
      alert('Venta guardada offline. Se sincronizará al reconectar.');
    }
  };
  
  return (
    <div className="pos-container">
      {!shift ? (
        <OpenShiftDialog onOpen={openShift} />
      ) : (
        <>
          <div className="pos-header">
            <h2>POS - Turno #{shift.id.slice(0, 8)}</h2>
            <button onClick={() => setScanning(true)}>Escanear</button>
            <span>Offline: {syncStatus.offline ? '🔴' : '🟢'}</span>
          </div>
          
          {scanning && (
            <BarcodeScanner 
              onScan={(code) => {
                addProduct(code);
                setScanning(false);
              }}
              onClose={() => setScanning(false)}
            />
          )}
          
          <div className="cart">
            {cart.map((item, idx) => (
              <CartLine key={idx} item={item} />
            ))}
          </div>
          
          <div className="totals">
            <p>Subtotal: {calculateSubtotal()}</p>
            <p>IVA: {calculateTax()}</p>
            <h3>TOTAL: {calculateTotal()}</h3>
          </div>
          
          <div className="actions">
            <button onClick={() => checkout('cash')}>💵 Efectivo</button>
            <button onClick={() => checkout('card')}>💳 Tarjeta</button>
          </div>
        </>
      )}
    </div>
  );
}
```

**2. Scanner de códigos con cámara**

Archivo: `apps/tenant/src/components/BarcodeScanner.tsx`
```tsx
import { useEffect, useRef } from 'react';

export function BarcodeScanner({ onScan, onClose }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  
  useEffect(() => {
    let stream: MediaStream;
    let animationId: number;
    
    const startScanning = async () => {
      try {
        // @ts-ignore - BarcodeDetector is experimental
        if ('BarcodeDetector' in window) {
          // @ts-ignore
          const detector = new BarcodeDetector({
            formats: ['qr_code', 'ean_13', 'ean_8', 'code_128']
          });
          
          stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: 'environment' }
          });
          
          if (videoRef.current) {
            videoRef.current.srcObject = stream;
            await videoRef.current.play();
          }
          
          const canvas = document.createElement('canvas');
          const ctx = canvas.getContext('2d')!;
          
          const tick = async () => {
            if (!videoRef.current) return;
            
            canvas.width = videoRef.current.videoWidth;
            canvas.height = videoRef.current.videoHeight;
            ctx.drawImage(videoRef.current, 0, 0);
            
            const barcodes = await detector.detect(canvas);
            if (barcodes.length > 0) {
              onScan(barcodes[0].rawValue);
              return; // Stop scanning
            }
            
            animationId = requestAnimationFrame(tick);
          };
          
          tick();
        } else {
          alert('BarcodeDetector no soportado. Usar entrada manual.');
          onClose();
        }
      } catch (err) {
        console.error('Error accessing camera:', err);
        alert('No se pudo acceder a la cámara');
        onClose();
      }
    };
    
    startScanning();
    
    return () => {
      if (stream) {
        stream.getTracks().forEach(track => track.stop());
      }
      if (animationId) {
        cancelAnimationFrame(animationId);
      }
    };
  }, []);
  
  return (
    <div className="scanner-overlay">
      <div className="scanner-container">
        <video ref={videoRef} className="scanner-video" />
        <div className="scanner-frame" />
        <button onClick={onClose} className="close-btn">Cerrar</button>
      </div>
    </div>
  );
}
```

---

### **FASE M2 — E-factura + Pagos** (2-3 semanas)

#### E-factura Ecuador SRI (Días 15-19)

**1. Worker Celery SRI**

Archivo: `apps/backend/app/workers/einvoicing_sri.py`
```python
from celery import Task
from app.celery_app import celery_app
from lxml import etree
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import boto3
import requests

@celery_app.task(name="einvoicing.sign_and_send_sri")
def sign_and_send_sri(invoice_id: str, env: str = "sandbox"):
    """Firmar y enviar factura a SRI Ecuador"""
    from app.db.session import SessionLocal
    from app.models.core.facturacion import Invoice
    from app.models.einvoicing import SRISubmission
    
    db = SessionLocal()
    try:
        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")
        
        # 1. Generar XML RIDE
        xml_content = generate_sri_xml(invoice, db)
        
        # 2. Cargar certificado desde S3
        tenant_id = get_tenant_id_from_empresa(invoice.empresa_id, db)
        cert_data = load_certificate(tenant_id, env)
        
        # 3. Firmar XML
        signed_xml = sign_xml_sri(xml_content, cert_data)
        
        # 4. Enviar a SRI
        endpoint = get_sri_endpoint(env)
        clave_acceso = extract_clave_acceso(signed_xml)
        
        response = requests.post(
            f"{endpoint}/recepcion",
            data=signed_xml,
            headers={"Content-Type": "application/xml"},
            timeout=30
        )
        
        # 5. Guardar resultado
        submission = SRISubmission(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            invoice_id=invoice_id,
            xml_content=signed_xml,
            clave_acceso=clave_acceso,
            status='authorized' if response.status_code == 200 else 'rejected',
            error_message=response.text if response.status_code != 200 else None,
            submitted_at=datetime.utcnow()
        )
        db.add(submission)
        
        # Actualizar invoice
        invoice.estado = 'einvoice_sent' if submission.status == 'authorized' else 'draft'
        
        db.commit()
        return {"status": submission.status, "clave_acceso": clave_acceso}
        
    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()

def generate_sri_xml(invoice, db):
    """Generar XML conforme a XSD SRI"""
    # Estructura básica factura SRI v1.0.0
    root = etree.Element("factura", id="comprobante", version="1.0.0")
    
    # Info tributaria
    info_trib = etree.SubElement(root, "infoTributaria")
    etree.SubElement(info_trib, "ambiente").text = "1"  # Pruebas
    etree.SubElement(info_trib, "tipoEmision").text = "1"  # Normal
    etree.SubElement(info_trib, "razonSocial").text = invoice.empresa.nombre
    etree.SubElement(info_trib, "ruc").text = invoice.empresa.ruc
    # ... más campos según XSD
    
    # Info factura
    info_fact = etree.SubElement(root, "infoFactura")
    etree.SubElement(info_fact, "fechaEmision").text = invoice.fecha.strftime("%d/%m/%Y")
    etree.SubElement(info_fact, "totalSinImpuestos").text = str(invoice.subtotal)
    etree.SubElement(info_fact, "totalDescuento").text = "0.00"
    etree.SubElement(info_fact, "importeTotal").text = str(invoice.total)
    
    # Detalles
    detalles = etree.SubElement(root, "detalles")
    for line in invoice.lines:
        detalle = etree.SubElement(detalles, "detalle")
        etree.SubElement(detalle, "codigoPrincipal").text = line.producto.sku
        etree.SubElement(detalle, "descripcion").text = line.producto.nombre
        etree.SubElement(detalle, "cantidad").text = str(line.cantidad)
        etree.SubElement(detalle, "precioUnitario").text = str(line.precio_unitario)
        etree.SubElement(detalle, "precioTotalSinImpuesto").text = str(line.total)
    
    return etree.tostring(root, xml_declaration=True, encoding='UTF-8', pretty_print=True)

def sign_xml_sri(xml_content, cert_data):
    """Firmar XML con certificado digital"""
    from signxml import XMLSigner
    
    # Cargar certificado y clave privada
    # TODO: Implementar firma XAdES-BES según SRI
    signer = XMLSigner(
        method=signxml.methods.enveloped,
        signature_algorithm="rsa-sha256",
        digest_algorithm="sha256",
    )
    
    signed = signer.sign(
        xml_content,
        key=cert_data['private_key'],
        cert=cert_data['certificate']
    )
    
    return signed
```

**2. Endpoint para enviar factura**

```python
@router.post("/einvoicing/send")
def send_einvoice(
    data: EInvoiceSendRequest,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant)
):
    """Encolar factura para firma y envío"""
    invoice = db.query(Invoice).filter(
        Invoice.id == data.invoice_id
    ).first()
    
    if not invoice:
        raise HTTPException(404, "Factura no encontrada")
    
    # Determinar ambiente (sandbox/prod)
    from app.models.tenant import Tenant
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    env = tenant.einvoice_env or "sandbox"
    
    # Encolar tarea
    if data.country == "EC":
        from app.workers.einvoicing_sri import sign_and_send_sri
        task = sign_and_send_sri.delay(str(invoice.id), env)
    elif data.country == "ES":
        from app.workers.einvoicing_facturae import sign_and_send_facturae
        task = sign_and_send_facturae.delay(str(invoice.id), env)
    else:
        raise HTTPException(400, "País no soportado")
    
    return {"task_id": task.id, "status": "enqueued"}
```

#### Pagos Online (Días 20-23)

**1. Stripe Provider**

Archivo: `apps/backend/app/services/payments/stripe_provider.py`
```python
import stripe
from app.config import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

def create_payment_link(
    amount: float,
    currency: str,
    invoice_id: str,
    success_url: str,
    cancel_url: str
):
    """Crear enlace de pago Stripe"""
    session = stripe.checkout.Session.create(
        mode='payment',
        line_items=[{
            'price_data': {
                'currency': currency.lower(),
                'product_data': {
                    'name': f'Factura #{invoice_id[:8]}'
                },
                'unit_amount': int(amount * 100)  # Centavos
            },
            'quantity': 1
        }],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={'invoice_id': invoice_id}
    )
    
    return {
        'url': session.url,
        'session_id': session.id
    }

def handle_webhook(payload, sig_header):
    """Procesar webhook de Stripe"""
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
        
        if event.type == 'checkout.session.completed':
            session = event.data.object
            invoice_id = session.metadata.get('invoice_id')
            
            # Actualizar invoice como pagada
            from app.db.session import SessionLocal
            from app.models.core.facturacion import Invoice
            db = SessionLocal()
            invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
            if invoice:
                invoice.estado = 'paid'
                db.commit()
            db.close()
            
        return {"status": "ok"}
    except Exception as e:
        raise ValueError(f"Webhook error: {str(e)}")
```

---

### **FASE M3 — Offline Real (ElectricSQL)** (3-4 semanas)

**1. Docker Compose con ElectricSQL**

```yaml
# Añadir a docker-compose.yml
  electric:
    image: electricsql/electric:latest
    container_name: electric
    environment:
      DATABASE_URL: postgresql://postgres:root@db:5432/gestiqclouddb_dev
      ELECTRIC_WRITE_TO_PG_MODE: "direct_writes"
    ports:
      - "5133:5133"
    depends_on:
      db:
        condition: service_healthy
```

**2. Cliente PGlite en Frontend**

```tsx
import { PGlite } from '@electric-sql/pglite';
import { electrify } from 'electric-sql';

let db: ElectricDatabase;

export async function initElectricDB() {
  const pglite = await PGlite.create({
    dataDir: 'idb://gestiqcloud-pos'
  });
  
  db = await electrify({
    url: 'http://localhost:5133',
    schema: posSchema,
    auth: () => ({ token: getAuthToken() })
  });
  
  await db.connect();
  
  // Suscribirse a shapes
  await db.shape('pos_receipts', {
    where: { register_id: getRegisterId() }
  });
  
  return db;
}
```

---

## 📋 Checklist de Tareas

### M1 — POS
- [ ] Verificar migración 2025-10-10_090_pos aplicada
- [ ] Crear `doc_series` table (nueva migración)
- [ ] Añadir columna `invoice_id` a `pos_receipts`
- [ ] Implementar `apps/backend/app/routers/pos.py`
- [ ] Implementar `apps/backend/app/services/numbering.py`
- [ ] Crear plantilla `ticket_58mm.html`
- [ ] Frontend: Vista `/pos` en `apps/tenant`
- [ ] Frontend: Componente `BarcodeScanner`
- [ ] Frontend: Modal "Convertir a Factura"
- [ ] Test: `test_pos_ticket_to_invoice.py`
- [ ] Test: Flujo completo E2E

### M2 — E-factura
- [ ] Implementar `sign_and_send_sri` (Celery task)
- [ ] Implementar `sign_and_send_facturae` (Celery task)
- [ ] Tabla `einv_credentials` para certificados
- [ ] Endpoint `/einvoicing/send`
- [ ] Endpoint `/einvoicing/status/{id}`
- [ ] Frontend: Botón "Enviar a SRI/AEAT"
- [ ] Frontend: Vista de estado e-factura

### M2 — Pagos
- [ ] Implementar `StripeProvider`
- [ ] Implementar `KushkiProvider`
- [ ] Endpoint `/payments/link`
- [ ] Endpoint `/payments/webhook/{provider}`
- [ ] Frontend: Botón "Pagar Online"

### M3 — Offline Real
- [ ] Docker: servicio ElectricSQL
- [ ] Configurar shapes (pos, products, stock)
- [ ] Frontend: PGlite client
- [ ] Reconciliación de conflictos
- [ ] Feature flag `ELECTRIC_SYNC_ENABLED`

---

## 🚀 Comandos Rápidos

```bash
# Arrancar proyecto completo
docker compose up -d

# Ver logs backend
docker logs -f backend

# Ejecutar migraciones
python scripts/py/bootstrap_imports.py --dir ops/migrations

# Test backend
pytest apps/backend/app/tests -v

# Health check
curl http://localhost:8000/api/v1/imports/health

# Ver estado de Celery
docker logs -f celery-worker

# Shell DB
docker exec -it db psql -U postgres -d gestiqclouddb_dev

# Consultar tenants
docker exec db psql -U postgres -d gestiqclouddb_dev -c "SELECT id, name, country FROM tenants;"
```

---

## 📚 Recursos Adicionales

- **AGENTS.md**: Arquitectura completa y especificaciones
- **README_DEV.md**: Setup y troubleshooting
- **docker-compose.yml**: Orquestación local
- **ops/migrations/**: Historial de migraciones SQL
- Documentación SRI: https://www.sri.gob.ec/facturacion-electronica
- Documentación Facturae: https://www.facturae.gob.es/

---

**Última actualización**: Enero 2025  
**Versión**: 1.0.0
