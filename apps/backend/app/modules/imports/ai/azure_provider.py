"""Azure OpenAI-based AI provider."""

import json
import logging
from typing import Any

from app.config.settings import settings

from .base import AIProvider, ClassificationResult
from .cache import ClassificationCache

logger = logging.getLogger("imports.ai.azure")


class AzureOpenAIProvider(AIProvider):
    """AI provider using Azure OpenAI Service."""

    def __init__(self, api_key: str, endpoint: str):
        """
        Initialize Azure OpenAI provider.

        Args:
            api_key: Azure OpenAI API key
            endpoint: Azure OpenAI endpoint URL
        """
        self.api_key = api_key
        self.endpoint = endpoint
        self.request_count = 0
        self.total_cost = 0.0

        # Import openai lazily
        try:
            import openai

            openai.api_type = "azure"
            openai.api_base = endpoint
            openai.api_version = "2023-05-15"
            openai.api_key = api_key
            self.openai = openai
        except ImportError:
            raise RuntimeError(
                "Azure provider requires 'openai' package. " "Install with: pip install openai"
            )

        # Cache
        self.cache = (
            ClassificationCache(ttl_seconds=settings.IMPORT_AI_CACHE_TTL)
            if settings.IMPORT_AI_CACHE_ENABLED
            else None
        )

        logger.info(f"AzureOpenAIProvider initialized (endpoint: {endpoint})")

    async def classify_document(
        self,
        text: str,
        available_parsers: list[str],
        doc_metadata: dict[str, Any] | None = None,
    ) -> ClassificationResult:
        """
        Classify document using Azure OpenAI.
        """
        # Try cache
        if self.cache:
            cached = self.cache.get(text, available_parsers)
            if cached:
                logger.debug("Azure classification cache hit")
                return ClassificationResult(**cached)

        # Prepare prompt
        parsers_str = "\n  - ".join(available_parsers)
        text_sample = text[:2000]

        prompt = f"""Classify this document and suggest which parser to use.

Available parsers:
  - {parsers_str}

Document text:
{text_sample}

Respond in JSON format (no markdown):
{{
    "suggested_parser": "parser_id",
    "confidence": 0.95,
    "reasoning": "brief explanation"
}}

Respond ONLY with valid JSON, no additional text."""

        try:
            import time

            start_time = time.time()

            response = self.openai.ChatCompletion.create(
                engine="gpt-35-turbo",  # Azure deployment name
                messages=[
                    {"role": "system", "content": "You are a document classification expert."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=500,
            )

            execution_time = (time.time() - start_time) * 1000

            response_text = response["choices"][0]["message"]["content"].strip()

            try:
                data = json.loads(response_text)
            except json.JSONDecodeError:
                if "```json" in response_text:
                    json_str = response_text.split("```json")[1].split("```")[0]
                    data = json.loads(json_str)
                elif "```" in response_text:
                    json_str = response_text.split("```")[1].split("```")[0]
                    data = json.loads(json_str)
                else:
                    raise ValueError("Could not parse JSON")

            suggested = data.get("suggested_parser", available_parsers[0])
            if suggested not in available_parsers:
                suggested = available_parsers[0]

            confidence = float(data.get("confidence", 0.5))
            confidence = min(max(confidence, 0.0), 1.0)

            # Azure pricing (approximate)
            cost = 0.002  # Rough estimate per request

            self.request_count += 1
            self.total_cost += cost

            probabilities = {}
            for p in available_parsers:
                if p == suggested:
                    probabilities[p] = round(confidence, 3)
                else:
                    probabilities[p] = round(
                        (1.0 - confidence) / max(len(available_parsers) - 1, 1), 3
                    )

            result = ClassificationResult(
                suggested_parser=suggested,
                confidence=confidence,
                probabilities=probabilities,
                reasoning=data.get("reasoning", "Azure OpenAI classification"),
                provider="azure",
                enhanced_by_ai=True,
            )

            if self.cache:
                self.cache.set(text, available_parsers, result.__dict__)

            logger.info(
                f"Azure classification: {suggested} "
                f"({confidence:.0%}, {execution_time:.0f}ms, ${cost:.6f})"
            )

            return result

        except Exception as e:
            logger.error(f"Azure classification error: {e}")
            raise

    async def extract_fields(
        self,
        text: str,
        doc_type: str,
        expected_fields: list[str],
    ) -> dict[str, Any]:
        """Extract fields using Azure OpenAI."""
        fields_str = "\n  - ".join(expected_fields)

        prompt = f"""Extract the following fields from this document ({doc_type}):

  - {fields_str}

Document text:
{text[:1000]}

Respond in JSON format:
{{
    "field_name": "extracted_value",
    ...
}}"""

        try:
            response = self.openai.ChatCompletion.create(
                engine="gpt-35-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=500,
            )

            response_text = response["choices"][0]["message"]["content"].strip()
            extracted = json.loads(response_text)

            self.total_cost += 0.002

            return extracted

        except Exception as e:
            logger.error(f"Azure field extraction error: {e}")
            return {}

    def get_telemetry(self) -> dict[str, Any]:
        """Get usage telemetry."""
        return {
            "provider": "azure",
            "endpoint": self.endpoint,
            "requests": self.request_count,
            "total_cost": round(self.total_cost, 6),
            "avg_cost_per_request": (
                round(self.total_cost / self.request_count, 6) if self.request_count > 0 else 0.0
            ),
            "latency_ms": "500-2000",
            "cache_enabled": self.cache is not None,
        }
