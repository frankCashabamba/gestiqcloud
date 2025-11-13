"""OpenAI-based AI provider for classification."""

import json
import logging
from typing import Any

from app.config.settings import settings

from .base import AIProvider, ClassificationResult
from .cache import ClassificationCache

logger = logging.getLogger("imports.ai.openai")


class OpenAIProvider(AIProvider):
    """AI provider using OpenAI API (GPT-3.5-turbo or GPT-4)."""

    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        """
        Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key
            model: Model to use (gpt-3.5-turbo, gpt-4, etc.)
        """
        self.api_key = api_key
        self.model = model
        self.request_count = 0
        self.total_cost = 0.0

        # Import openai lazily
        try:
            import openai

            openai.api_key = api_key
            self.openai = openai
        except ImportError:
            raise RuntimeError(
                "OpenAI provider requires 'openai' package. " "Install with: pip install openai"
            )

        # Cache
        self.cache = (
            ClassificationCache(ttl_seconds=settings.IMPORT_AI_CACHE_TTL)
            if settings.IMPORT_AI_CACHE_ENABLED
            else None
        )

        logger.info(f"OpenAIProvider initialized (model: {self.model})")

    async def classify_document(
        self,
        text: str,
        available_parsers: list[str],
        doc_metadata: dict[str, Any] | None = None,
    ) -> ClassificationResult:
        """
        Classify document using GPT.

        Args:
            text: Document text (first 2000 chars used)
            available_parsers: Available parser IDs
            doc_metadata: Optional metadata

        Returns:
            ClassificationResult from GPT
        """
        # Try cache
        if self.cache:
            cached = self.cache.get(text, available_parsers)
            if cached:
                logger.debug("Classification cache hit")
                return ClassificationResult(**cached)

        # Prepare prompt
        parsers_str = "\n  - ".join(available_parsers)
        text_sample = text[:2000]  # Limit to avoid huge requests

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
            # Call OpenAI API
            import time

            start_time = time.time()

            response = self.openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a document classification expert."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=500,
            )

            execution_time = (time.time() - start_time) * 1000  # ms

            # Parse response
            response_text = response["choices"][0]["message"]["content"].strip()

            # Try to extract JSON
            try:
                data = json.loads(response_text)
            except json.JSONDecodeError:
                # Fallback: extract JSON from markdown code blocks
                if "```json" in response_text:
                    json_str = response_text.split("```json")[1].split("```")[0]
                    data = json.loads(json_str)
                elif "```" in response_text:
                    json_str = response_text.split("```")[1].split("```")[0]
                    data = json.loads(json_str)
                else:
                    raise ValueError("Could not parse JSON response")

            # Validate result
            suggested = data.get("suggested_parser", available_parsers[0])
            if suggested not in available_parsers:
                suggested = available_parsers[0]

            confidence = float(data.get("confidence", 0.5))
            confidence = min(max(confidence, 0.0), 1.0)  # Clamp 0-1

            # Calculate cost (approximate)
            # gpt-3.5-turbo: $0.0005/1K input, $0.0015/1K output
            # gpt-4: $0.03/1K input, $0.06/1K output
            input_tokens = len(text_sample) // 4  # rough estimate
            output_tokens = 100  # typical response

            if "gpt-4" in self.model:
                cost = (input_tokens * 0.00003) + (output_tokens * 0.00006)
            else:
                cost = (input_tokens * 0.0000005) + (output_tokens * 0.0000015)

            self.request_count += 1
            self.total_cost += cost

            # Create probabilities dict (estimate for others)
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
                reasoning=data.get("reasoning", "OpenAI classification"),
                provider="openai",
                enhanced_by_ai=True,
            )

            # Cache
            if self.cache:
                self.cache.set(text, available_parsers, result.__dict__)

            logger.info(
                f"OpenAI classification: {suggested} "
                f"({confidence:.0%}, {execution_time:.0f}ms, ${cost:.6f})"
            )

            return result

        except Exception as e:
            logger.error(f"OpenAI classification error: {e}")
            raise

    async def extract_fields(
        self,
        text: str,
        doc_type: str,
        expected_fields: list[str],
    ) -> dict[str, Any]:
        """
        Extract fields using GPT.
        """
        fields_str = "\n  - ".join(expected_fields)

        prompt = f"""Extract the following fields from this document ({doc_type}):

  - {fields_str}

Document text:
{text[:1000]}

Respond in JSON format with the extracted values:
{{
    "field_name": "extracted_value",
    ...
}}

If a field is not found, omit it. Respond ONLY with valid JSON."""

        try:
            response = self.openai.ChatCompletion.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=500,
            )

            response_text = response["choices"][0]["message"]["content"].strip()
            extracted = json.loads(response_text)

            self.total_cost += 0.001  # Rough estimate

            return extracted

        except Exception as e:
            logger.error(f"OpenAI field extraction error: {e}")
            return {}

    def get_telemetry(self) -> dict[str, Any]:
        """Get usage telemetry."""
        return {
            "provider": "openai",
            "model": self.model,
            "requests": self.request_count,
            "total_cost": round(self.total_cost, 6),
            "avg_cost_per_request": (
                round(self.total_cost / self.request_count, 6) if self.request_count > 0 else 0.0
            ),
            "latency_ms": "500-2000",
            "cache_enabled": self.cache is not None,
        }
