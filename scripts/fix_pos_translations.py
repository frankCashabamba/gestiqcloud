#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script para traducir todos los strings hardcodeados en POSView.tsx"""

import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Leer el archivo
with open("apps/tenant/src/modules/pos/POSView.tsx", "r", encoding="utf-8") as f:
    content = f.read()

# Lista de reemplazos (old, new)
replacements = [
    # Alerts y prompts
    (
        "alert(`Producto no encontrado:\n${code}\\nDeseas crearlo?`)",
        "alert(`${t('pos:errors.productNotFound')}: ${code}\\n${t('pos:errors.confirmCreate')}`)",
    ),
    (
        "alert('El total supera el limite para consumidor final. Se requieren datos.')",
        "alert(t('pos:errors.totalExceedsLimit'))",
    ),
    (
        "alert('Selecciona el tipo de identificacion del comprador.')",
        "alert(t('pos:errors.selectIdentificationType'))",
    ),
    (
        "alert('Completa nombre e identificacion del comprador.')",
        "alert(t('pos:errors.completeIdentification'))",
    ),
    ("alert('No hay líneas en el carrito')", "alert(t('pos:errors.emptyCart'))"),
    ("alert('Abre un turno primero')", "alert(t('pos:errors.noShiftOpen'))"),
    (
        "alert('El total requiere datos del comprador.')",
        "alert(t('pos:errors.requiresBuyerData'))",
    ),
    ("alert('No hay tickets en espera')", "alert(t('pos:errors.heldTickets'))"),
    ("alert('ID no encontrado')", "alert(t('pos:errors.idNotFound'))"),
    (
        "alert('No hay nada para reimprimir todavía.')",
        "alert(t('pos:errors.nothingToReprint'))",
    ),
    ("alert('No se pudo reimprimir.')", "alert(t('pos:errors.reprintFailed'))"),
    (
        "alert('Factura generada correctamente')",
        "alert(t('pos:errors.invoiceGeneratedSuccess'))",
    ),
    (
        "alert('Producto existente agregado al carrito.')",
        "alert(t('pos:createProduct.existingAdded'))",
    ),
    (
        "alert('No se pudo crear el producto')",
        "alert(t('pos:createProduct.creationFailed'))",
    ),
    ("alert('Impresion finalizada')", "alert(t('pos:errors.printingFinished'))"),
    # Register creation
    ('placeholder="Caja Principal"', "placeholder={t('pos:register.nameDefault')}"),
    ('placeholder="CAJA-1"', "placeholder={t('pos:register.codeDefault')}"),
    # Header buttons
    (
        "onClick={() => setTicketNotes(prompt('Notas del ticket', ticketNotes) || ticketNotes)}",
        "onClick={() => setTicketNotes(prompt(t('pos:header.notes'), ticketNotes) || ticketNotes)}",
    ),
    (
        "Notas\n                    </button>",
        "{t('pos:header.notes')}\n                    </button>",
    ),
    (
        "onClick={() => setGlobalDiscountPct(parseFloat(prompt('Descuento global (%)', String(globalDiscountPct)) || String(globalDiscountPct)))}",
        "onClick={() => setGlobalDiscountPct(parseFloat(prompt(t('pos:header.discount') + ' (%)', String(globalDiscountPct)) || String(globalDiscountPct)))}",
    ),
    (
        "Descuento\n                        </button>",
        "{t('pos:header.discount')}\n                        </button>",
    ),
    (
        "Reportes diarios\n                        </button>",
        "{t('pos:header.dailyReports')}\n                        </button>",
    ),
    (
        "Ticket en espera\n                    </button>",
        "{t('pos:header.holdTicket')}\n                    </button>",
    ),
    (
        "Recuperar\n                    </button>",
        "{t('pos:header.resume')}\n                    </button>",
    ),
    (
        "Reimprimir\n                    </button>",
        "{t('pos:header.reprint')}\n                    </button>",
    ),
    (
        "Cobrar pendientes\n                        </button>",
        "{t('pos:header.pendingPayments')}\n                        </button>",
    ),
    ("Online", "t('pos:header.online')"),
    ("Offline", "t('pos:header.offline')"),
    (
        "Cerrar turno\n                        </button>",
        "{t('pos:header.closingShift')}\n                        </button>",
    ),
    # Search
    (
        "Buscar\n                    </button>",
        "{t('pos:search.button')}\n                    </button>",
    ),
    (
        'placeholder="Buscar productos o escanear código (F2)"',
        "placeholder={t('pos:search.placeholder')}",
    ),
    ('placeholder="Codigo de barras"', "placeholder={t('pos:search.barcodeInput')}"),
]

# Aplicar reemplazos
for old, new in replacements:
    if old in content:
        content = content.replace(old, new)
        print(f"✓ Reemplazado: {old[:50]}...")
    else:
        print(f"⚠ No encontrado: {old[:50]}...")

# Escribir el archivo actualizado
with open("apps/tenant/src/modules/pos/POSView.tsx", "w", encoding="utf-8") as f:
    f.write(content)

print("\n✅ Archivo POSView.tsx actualizado exitosamente")
