"""AI-powered mapping suggestion for column headers."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from typing import Any

from app.config.settings import settings

logger = logging.getLogger("imports.ai.mapping")


@dataclass
class MappingSuggestion:
    """Resultado de sugerencia de mapping."""

    mappings: dict[str, str]
    transforms: dict[str, str] | None = None
    defaults: dict[str, Any] | None = None
    confidence: float = 0.0
    reasoning: str = ""
    from_cache: bool = False
    provider: str = "heuristics"


@dataclass
class MappingCache:
    """In-memory cache for mapping suggestions."""

    data: dict[str, Any] = field(default_factory=dict)
    cached_at: str = ""


class MappingSuggester:
    """Sugiere mappings de columnas usando IA o heurísticas."""

    TARGET_FIELDS = {
        "products": [
            "name",
            "sku",
            "price",
            "stock",
            "category",
            "description",
            "barcode",
            "unit",
            "cost",
        ],
        "bank_transactions": [
            "amount",
            "direction",
            "value_date",
            "narrative",
            "counterparty",
            "iban",
            "reference",
            "balance",
        ],
        "invoices": [
            "invoice_number",
            "issue_date",
            "vendor_name",
            "vendor_tax_id",
            "subtotal",
            "tax",
            "total",
            "due_date",
            "customer",
        ],
        "expenses": [
            "description",
            "amount",
            "expense_date",
            "category",
            "payment_method",
            "vendor",
            "receipt_number",
        ],
    }

    COMMON_MAPPINGS: dict[str, str] = {
        # Productos - Español
        "nombre": "name",
        "producto": "name",
        "articulo": "name",
        "item": "name",
        "descripcion": "description",
        "detalle": "description",
        "precio": "price",
        "precio_unitario": "price",
        "precio unitario": "price",
        "pvp": "price",
        "valor": "price",
        "costo": "cost",
        "coste": "cost",
        "cantidad": "stock",
        "stock": "stock",
        "existencia": "stock",
        "inventario": "stock",
        "categoria": "category",
        "grupo": "category",
        "familia": "category",
        "sku": "sku",
        "codigo": "sku",
        "referencia": "sku",
        "ref": "sku",
        "codigo_barras": "barcode",
        "codigo de barras": "barcode",
        "ean": "barcode",
        "upc": "barcode",
        "unidad": "unit",
        "um": "unit",
        "uom": "unit",
        # Productos - Inglés
        "name": "name",
        "product": "name",
        "product_name": "name",
        "description": "description",
        "price": "price",
        "unit_price": "price",
        "cost": "cost",
        "quantity": "stock",
        "qty": "stock",
        "category": "category",
        "code": "sku",
        "barcode": "barcode",
        "unit": "unit",
        # Banco - Español
        "importe": "amount",
        "monto": "amount",
        "valor": "amount",
        "debito": "amount",
        "credito": "amount",
        "fecha": "value_date",
        "fecha_valor": "value_date",
        "fecha valor": "value_date",
        "concepto": "narrative",
        "descripcion": "narrative",
        "detalle": "narrative",
        "contraparte": "counterparty",
        "beneficiario": "counterparty",
        "ordenante": "counterparty",
        "iban": "iban",
        "cuenta": "iban",
        "referencia": "reference",
        "saldo": "balance",
        # Banco - Inglés
        "amount": "amount",
        "debit": "amount",
        "credit": "amount",
        "date": "value_date",
        "value_date": "value_date",
        "narrative": "narrative",
        "statement": "narrative",
        "counterparty": "counterparty",
        "beneficiary": "counterparty",
        "reference": "reference",
        "balance": "balance",
        # Facturas - Español
        "factura": "invoice_number",
        "numero": "invoice_number",
        "numero_factura": "invoice_number",
        "nro_factura": "invoice_number",
        "fecha_emision": "issue_date",
        "fecha emision": "issue_date",
        "proveedor": "vendor_name",
        "emisor": "vendor_name",
        "ruc": "vendor_tax_id",
        "nit": "vendor_tax_id",
        "cif": "vendor_tax_id",
        "rfc": "vendor_tax_id",
        "subtotal": "subtotal",
        "base": "subtotal",
        "base_imponible": "subtotal",
        "iva": "tax",
        "impuesto": "tax",
        "igv": "tax",
        "total": "total",
        "total_factura": "total",
        "vencimiento": "due_date",
        "fecha_vencimiento": "due_date",
        "cliente": "customer",
        "comprador": "customer",
        # Facturas - Inglés
        "invoice": "invoice_number",
        "invoice_number": "invoice_number",
        "invoice_no": "invoice_number",
        "issue_date": "issue_date",
        "vendor": "vendor_name",
        "supplier": "vendor_name",
        "tax_id": "vendor_tax_id",
        "tax": "tax",
        "vat": "tax",
        "due_date": "due_date",
        "customer": "customer",
        "buyer": "customer",
        # Gastos - Español
        "gasto": "description",
        "motivo": "description",
        "fecha_gasto": "expense_date",
        "metodo_pago": "payment_method",
        "forma_pago": "payment_method",
        "recibo": "receipt_number",
        "comprobante": "receipt_number",
        # Gastos - Inglés
        "expense": "description",
        "expense_date": "expense_date",
        "payment_method": "payment_method",
        "receipt": "receipt_number",
    }

    def __init__(self):
        self._cache: dict[str, MappingSuggestion] = {}
        self._redis_available = False
        self._check_redis()

    def _check_redis(self):
        """Check if Redis is available for persistent cache."""
        if settings.REDIS_URL:
            try:
                import redis

                self._redis_client = redis.from_url(settings.REDIS_URL)
                self._redis_client.ping()
                self._redis_available = True
                logger.info("MappingSuggester: Redis cache enabled")
            except Exception as e:
                logger.warning(f"MappingSuggester: Redis unavailable, using in-memory cache: {e}")
                self._redis_available = False
        else:
            logger.info("MappingSuggester: Using in-memory cache (REDIS_URL not set)")

    def _get_cache_key(
        self, headers: list[str], doc_type: str, tenant_id: str | None = None
    ) -> str:
        """Genera key de cache."""
        data = f"{','.join(sorted(headers))}|{doc_type}|{tenant_id or ''}"
        return f"mapping:{hashlib.sha256(data.encode()).hexdigest()[:32]}"

    async def suggest_mapping(
        self,
        headers: list[str],
        sample_rows: list[list[Any]] | None = None,
        doc_type: str = "products",
        tenant_id: str | None = None,
        use_ai: bool = True,
    ) -> MappingSuggestion:
        """
        Sugiere mapping de columnas al schema canónico.

        1. Revisa cache (por hash de headers + doc_type)
        2. Si no hay cache, intenta IA (si habilitado y disponible)
        3. Fallback a heurísticas
        4. Guarda en cache el resultado
        """
        if not headers:
            return MappingSuggestion(
                mappings={},
                confidence=0.0,
                reasoning="No headers provided",
            )

        cache_key = self._get_cache_key(headers, doc_type, tenant_id)

        cached = self._get_from_cache(cache_key)
        if cached:
            logger.debug(f"Mapping suggestion cache hit: {cache_key[:16]}...")
            cached.from_cache = True
            return cached

        suggestion: MappingSuggestion | None = None

        if use_ai and settings.IMPORT_AI_PROVIDER != "local":
            try:
                suggestion = await self._suggest_with_ai(headers, sample_rows or [], doc_type)
                if suggestion and suggestion.confidence >= 0.7:
                    logger.info(
                        f"AI mapping suggestion: {len(suggestion.mappings)} mappings, "
                        f"confidence={suggestion.confidence:.0%}"
                    )
            except Exception as e:
                logger.warning(f"AI mapping suggestion failed, using heuristics: {e}")
                suggestion = None

        if not suggestion or suggestion.confidence < 0.5:
            suggestion = self._suggest_with_heuristics(headers, doc_type)

        self._set_in_cache(cache_key, suggestion)

        return suggestion

    def _get_from_cache(self, key: str) -> MappingSuggestion | None:
        """Retrieve from cache (Redis or in-memory)."""
        if self._redis_available:
            try:
                data = self._redis_client.get(key)
                if data:
                    parsed = json.loads(data)
                    return MappingSuggestion(**parsed)
            except Exception as e:
                logger.warning(f"Redis get error: {e}")

        return self._cache.get(key)

    def _set_in_cache(self, key: str, suggestion: MappingSuggestion):
        """Store in cache (Redis or in-memory)."""
        self._cache[key] = suggestion

        if self._redis_available:
            try:
                data = json.dumps(
                    {
                        "mappings": suggestion.mappings,
                        "transforms": suggestion.transforms,
                        "defaults": suggestion.defaults,
                        "confidence": suggestion.confidence,
                        "reasoning": suggestion.reasoning,
                        "provider": suggestion.provider,
                    }
                )
                self._redis_client.setex(key, settings.IMPORT_AI_CACHE_TTL, data)
            except Exception as e:
                logger.warning(f"Redis set error: {e}")

    async def _suggest_with_ai(
        self,
        headers: list[str],
        sample_rows: list[list[Any]],
        doc_type: str,
    ) -> MappingSuggestion:
        """Usa IA para sugerir mapping."""
        from app.modules.imports.ai import get_ai_provider_singleton

        target_fields = self.TARGET_FIELDS.get(doc_type, self.TARGET_FIELDS["products"])

        prompt = f"""Map these column headers from an Excel/CSV file to standard fields.

Headers: {headers}

{self._format_sample_rows(headers, sample_rows[:3]) if sample_rows else ""}

Target fields for {doc_type}: {target_fields}

Respond with JSON only (no markdown):
{{
  "mappings": {{"source_column": "target_field", ...}},
  "transforms": {{"column": "transform_type", ...}},
  "defaults": {{"field": "default_value", ...}},
  "reasoning": "brief explanation"
}}

Transform types: uppercase, lowercase, trim, parse_date, parse_number, none
Only include transforms and defaults if needed."""

        provider = await get_ai_provider_singleton()

        try:
            if hasattr(provider, "openai"):
                response = provider.openai.ChatCompletion.create(
                    model=getattr(provider, "model", "gpt-3.5-turbo"),
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a data mapping expert. Respond with valid JSON only.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.1,
                    max_tokens=800,
                )

                response_text = response["choices"][0]["message"]["content"].strip()
                data = self._parse_json_response(response_text)

                mappings = data.get("mappings", {})
                valid_mappings = {
                    k: v for k, v in mappings.items() if k in headers and v in target_fields
                }

                return MappingSuggestion(
                    mappings=valid_mappings,
                    transforms=data.get("transforms"),
                    defaults=data.get("defaults"),
                    confidence=len(valid_mappings) / max(len(headers), 1),
                    reasoning=data.get("reasoning", "AI-suggested mapping"),
                    provider=settings.IMPORT_AI_PROVIDER,
                )

        except Exception as e:
            logger.error(f"AI mapping error: {e}")
            raise

        return self._suggest_with_heuristics(headers, doc_type)

    def _parse_json_response(self, text: str) -> dict[str, Any]:
        """Parse JSON from AI response, handling markdown code blocks."""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            if "```json" in text:
                json_str = text.split("```json")[1].split("```")[0]
                return json.loads(json_str)
            elif "```" in text:
                json_str = text.split("```")[1].split("```")[0]
                return json.loads(json_str)
            raise

    def _suggest_with_heuristics(self, headers: list[str], doc_type: str) -> MappingSuggestion:
        """Fallback: sugerencia basada en patrones."""
        target_fields = self.TARGET_FIELDS.get(doc_type, self.TARGET_FIELDS["products"])
        mappings: dict[str, str] = {}
        transforms: dict[str, str] = {}
        used_targets: set[str] = set()

        for header in headers:
            header_lower = header.lower().strip()
            header_normalized = header_lower.replace("_", " ").replace("-", " ").replace(".", " ")

            matched_target: str | None = None

            if header_lower in self.COMMON_MAPPINGS:
                potential = self.COMMON_MAPPINGS[header_lower]
                if potential in target_fields and potential not in used_targets:
                    matched_target = potential

            if not matched_target:
                for keyword, target in self.COMMON_MAPPINGS.items():
                    if target not in target_fields or target in used_targets:
                        continue

                    if keyword in header_normalized or header_normalized in keyword:
                        matched_target = target
                        break

                    words = header_normalized.split()
                    if any(keyword == word or keyword in word for word in words):
                        matched_target = target
                        break

            if matched_target:
                mappings[header] = matched_target
                used_targets.add(matched_target)

                if matched_target in ("value_date", "issue_date", "expense_date", "due_date"):
                    transforms[header] = "parse_date"
                elif matched_target in (
                    "amount",
                    "price",
                    "cost",
                    "stock",
                    "subtotal",
                    "tax",
                    "total",
                ):
                    transforms[header] = "parse_number"

        coverage = len(mappings) / max(len(headers), 1)
        confidence = min(coverage * 1.2, 1.0)

        mapped_count = len(mappings)
        unmapped = len(headers) - mapped_count
        reasoning = f"Heuristic mapping: {mapped_count}/{len(headers)} columns matched"
        if unmapped > 0:
            reasoning += f" ({unmapped} unmapped)"

        return MappingSuggestion(
            mappings=mappings,
            transforms=transforms if transforms else None,
            defaults=None,
            confidence=confidence,
            reasoning=reasoning,
            provider="heuristics",
        )

    def _format_sample_rows(self, headers: list[str], rows: list[list[Any]]) -> str:
        """Formatea filas de muestra para el prompt."""
        if not rows:
            return ""

        lines = ["Sample data (first rows):"]
        for i, row in enumerate(rows[:3], 1):
            row_data = []
            for j, (h, v) in enumerate(zip(headers, row)):
                if j < 8:
                    v_str = str(v)[:50] if v else ""
                    row_data.append(f"{h}: {v_str}")
            lines.append(f"  Row {i}: {', '.join(row_data)}")

        return "\n".join(lines)

    def clear_cache(self, tenant_id: str | None = None):
        """Limpia cache (todo o por tenant)."""
        if tenant_id:
            keys_to_remove = [k for k in self._cache.keys() if tenant_id in k]
            for k in keys_to_remove:
                del self._cache[k]

            if self._redis_available:
                try:
                    for key in self._redis_client.scan_iter(f"mapping:*{tenant_id}*"):
                        self._redis_client.delete(key)
                except Exception as e:
                    logger.warning(f"Redis cache clear error: {e}")
        else:
            self._cache.clear()

            if self._redis_available:
                try:
                    for key in self._redis_client.scan_iter("mapping:*"):
                        self._redis_client.delete(key)
                except Exception as e:
                    logger.warning(f"Redis cache clear error: {e}")

        logger.info(f"Mapping cache cleared (tenant_id={tenant_id})")

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        stats = {
            "in_memory_entries": len(self._cache),
            "redis_available": self._redis_available,
        }

        if self._redis_available:
            try:
                keys = list(self._redis_client.scan_iter("mapping:*"))
                stats["redis_entries"] = len(keys)
            except Exception:
                stats["redis_entries"] = "error"

        return stats


mapping_suggester = MappingSuggester()
