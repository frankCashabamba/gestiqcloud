FIELD_ALIASES = {
    "es": {
        "invoice_number": ["numero", "número", "factura", "invoice_no", "no_factura"],
        "invoice_date": ["fecha", "fecha_factura", "date", "invoice_date"],
        "provider": ["proveedor", "supplier", "empresa", "vendor"],
        "client": ["cliente", "customer", "destinatario"],
        "amount": ["monto", "importe", "total", "amount", "valor"],
        "tax": ["iva", "impuesto", "tax", "tributacion"],
        "tax_id": ["ruc", "cif", "nif", "tax_id", "id_fiscal"],
        "currency": ["moneda", "divisa", "currency"],
        "account": ["cuenta", "account", "numero_cuenta"],
        "bank": ["banco", "bank", "entidad_bancaria"],
        "concept": ["concepto", "description", "descripcion"],
        "category": ["categoria", "category", "tipo"],
        "product": ["producto", "product", "articulo"],
        "quantity": ["cantidad", "qty", "amount"],
        "price": ["precio", "price", "valor_unitario"],
        "stock": ["stock", "existencias", "inventory"],
        "sku": ["sku", "codigo", "code"],
    },
    "en": {
        "invoice_number": ["invoice_no", "invoice_number", "invoice", "number"],
        "invoice_date": ["invoice_date", "date", "fecha"],
        "provider": ["provider", "supplier", "vendor", "company"],
        "client": ["client", "customer", "buyer"],
        "amount": ["amount", "total", "value", "monto"],
        "tax": ["tax", "vat", "iva"],
        "tax_id": ["tax_id", "vat_id", "ruc"],
        "currency": ["currency", "currency_code"],
        "account": ["account", "account_number"],
        "bank": ["bank", "bank_name"],
        "concept": ["concept", "description", "detail"],
        "category": ["category", "type"],
        "product": ["product", "item", "producto"],
        "quantity": ["quantity", "qty"],
        "price": ["price", "unit_price"],
        "stock": ["stock", "inventory"],
        "sku": ["sku", "product_code"],
    },
    "pt": {
        "invoice_number": ["nota_fiscal", "invoice", "numero"],
        "invoice_date": ["data", "data_emissao"],
        "provider": ["fornecedor", "supplier"],
        "client": ["cliente", "customer"],
        "amount": ["valor", "total", "amount"],
        "tax": ["impostos", "tax"],
        "tax_id": ["cnpj", "cpf", "tax_id"],
        "currency": ["moeda", "currency"],
        "account": ["conta", "account"],
        "bank": ["banco", "bank"],
        "concept": ["descricao", "description"],
        "category": ["categoria", "category"],
        "product": ["produto", "product"],
        "quantity": ["quantidade", "qty"],
        "price": ["preco", "price"],
        "stock": ["estoque", "stock"],
        "sku": ["sku", "codigo"],
    },
}

DOC_TYPE_ALIASES = {
    "invoice": ["invoice", "factura", "invoice_number", "venta", "nota_venta"],
    "expense_receipt": ["gasto", "expense", "receipt", "recibo", "voucher"],
    "bank_statement": ["banco", "bank", "statement", "extracto", "transaccion"],
    "bank_transaction": ["transaccion", "transaction", "transferencia", "movimiento"],
    "product_list": ["producto", "products", "catalogo", "inventory", "lista_precios"],
    "recipe": [
        "receta",
        "recipe",
        "costeo",
        "costing",
        "ingredientes",
        "preparacion",
    ],
    "generic": ["generic", "desconocido", "unknown"],
}

LANGUAGE_DETECTION = {
    "es": ["factura", "proveedor", "cliente", "ruc", "gasto", "recibo"],
    "en": ["invoice", "supplier", "customer", "tax", "expense", "receipt"],
    "pt": ["nota_fiscal", "fornecedor", "cliente", "cnpj", "despesa"],
}


def normalize_field_name(field: str, language: str = "es") -> str:
    if language not in FIELD_ALIASES:
        language = "es"

    field_lower = field.lower().strip()
    for canonical, aliases in FIELD_ALIASES[language].items():
        if field_lower in aliases:
            return canonical

    return field_lower


def detect_language(text: str) -> str:
    text_lower = text.lower()
    scores = {"es": 0, "en": 0, "pt": 0}

    for lang, keywords in LANGUAGE_DETECTION.items():
        for keyword in keywords:
            if keyword in text_lower:
                scores[lang] += 1

    if max(scores.values()) == 0:
        return "es"

    return max(scores, key=scores.get)


def resolve_field_alias(field: str, language: str = "es") -> str:
    return normalize_field_name(field, language)


def get_doc_type_aliases(doc_type: str) -> list[str]:
    for canonical, aliases in DOC_TYPE_ALIASES.items():
        if doc_type.lower() in aliases:
            return aliases
    return [doc_type.lower()]
