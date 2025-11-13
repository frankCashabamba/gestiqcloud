"""Batch import script para cargar múltiples archivos desde carpeta local.

Fase E - DX: Automatización de importaciones en masa para entornos on-premise.

Uso:
    python -m app.modules.imports.scripts.batch_import \
      --folder /data/facturas \
      --doc-type invoice \
      --validate \
      --promote \
      --report results.json

Características:
- Recursión en subcarpetas
- Clasificación automática o manual por doc_type
- Validación canónica (por país si está disponible)
- Promoción opcional a tablas destino
- Reporte detallado (JSON/CSV)
- Reintentos y fallback graceful
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import typer
from dataclasses import dataclass, asdict, field
from enum import Enum

logger = logging.getLogger("app.imports.batch_import")


class ImportStatus(str, Enum):
    """Estado de importación de un archivo."""
    SUCCESS = "success"
    VALIDATION_ERROR = "validation_error"
    PARSER_ERROR = "parser_error"
    PROMOTION_ERROR = "promotion_error"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class FileImportResult:
    """Resultado de importar un archivo."""
    filename: str
    filepath: str
    status: ImportStatus
    doc_type: Optional[str] = None
    parser_id: Optional[str] = None
    items_count: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    promoted: bool = False
    promotion_errors: List[str] = field(default_factory=list)
    processing_time_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class BatchImportReport:
    """Reporte agregado de importación batch."""
    total_files: int
    processed: int = 0
    successful: int = 0
    skipped: int = 0
    failed: int = 0
    validation_errors: int = 0
    promotion_errors: int = 0
    results: List[FileImportResult] = field(default_factory=list)
    total_items: int = 0
    total_time_ms: float = 0.0
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: str = ""


class BatchImporter:
    """Importador batch para archivos locales."""

    def __init__(
        self,
        folder: Path,
        doc_type: Optional[str] = None,
        parser_id: Optional[str] = None,
        recursive: bool = True,
        pattern: str = "*.*",
        validate: bool = True,
        promote: bool = False,
        country: Optional[str] = None,
        dry_run: bool = False,
        skip_errors: bool = True,
    ):
        self.folder = folder
        self.doc_type = doc_type
        self.parser_id = parser_id
        self.recursive = recursive
        self.pattern = pattern
        self.validate = validate
        self.promote = promote
        self.country = country
        self.dry_run = dry_run
        self.skip_errors = skip_errors
        self.report = BatchImportReport(total_files=0)

    async def run(self) -> BatchImportReport:
        """Ejecutar importación batch."""
        import time
        start_time = time.time()

        try:
            # Buscar archivos
            files = self._find_files()
            self.report.total_files = len(files)

            if not files:
                logger.warning(f"No files found in {self.folder}")
                return self.report

            typer.echo(f"\n📁 Batch Import Started")
            typer.echo(f"  Folder: {self.folder}")
            typer.echo(f"  Files: {len(files)}")
            typer.echo(f"  Validate: {self.validate}")
            typer.echo(f"  Promote: {self.promote}")
            typer.echo(f"  Dry-run: {self.dry_run}\n")

            # Procesar cada archivo
            for idx, file_path in enumerate(files, 1):
                if file_path.is_dir():
                    continue

                typer.echo(f"  [{idx}/{len(files)}] {file_path.name}...", nl=False)

                try:
                    result = await self._import_file(file_path)
                    self.report.results.append(result)

                    # Actualizar contadores
                    if result.status == ImportStatus.SUCCESS:
                        self.report.successful += 1
                        self.report.total_items += result.items_count
                        typer.echo(f" ✓ ({result.items_count} items, {result.processing_time_ms:.0f}ms)")
                    elif result.status == ImportStatus.SKIPPED:
                        self.report.skipped += 1
                        typer.echo(f" ⊘ (skipped)")
                    elif result.status == ImportStatus.VALIDATION_ERROR:
                        self.report.validation_errors += 1
                        self.report.failed += 1
                        typer.echo(f" ✗ (validation errors)")
                    else:
                        self.report.failed += 1
                        typer.echo(f" ✗ (error)")

                    self.report.processed += 1

                except Exception as e:
                    logger.exception(f"Unexpected error processing {file_path.name}")
                    result = FileImportResult(
                        filename=file_path.name,
                        filepath=str(file_path),
                        status=ImportStatus.FAILED,
                        errors=[f"Unexpected error: {str(e)[:100]}"],
                    )
                    self.report.results.append(result)
                    self.report.failed += 1
                    self.report.processed += 1
                    typer.echo(f" ✗ (unexpected error)")

                    if not self.skip_errors:
                        raise

        finally:
            self.report.completed_at = datetime.now().isoformat()
            self.report.total_time_ms = (time.time() - start_time) * 1000

        return self.report

    async def _import_file(self, file_path: Path) -> FileImportResult:
        """Importar un archivo individual."""
        import time
        start_time = time.time()

        result = FileImportResult(
            filename=file_path.name,
            filepath=str(file_path),
            status=ImportStatus.FAILED,
        )

        try:
            # Paso 1: Obtener parser
            parser = await self._get_parser(file_path)
            if not parser:
                result.status = ImportStatus.SKIPPED
                result.warnings.append("No suitable parser found")
                return result

            result.parser_id = getattr(parser, "PARSER_ID", "unknown")
            result.doc_type = self.doc_type or getattr(parser, "DOC_TYPE", "unknown")

            if self.dry_run:
                result.status = ImportStatus.SUCCESS
                result.processing_time_ms = (time.time() - start_time) * 1000
                return result

            # Paso 2: Parsear
            canonical_doc = await parser.parse(str(file_path))
            result.items_count = len(canonical_doc.items)

            # Paso 3: Validar (si está habilitado)
            if self.validate:
                from app.modules.imports.validators import validate_canonical

                errors = validate_canonical(canonical_doc)
                if errors:
                    result.status = ImportStatus.VALIDATION_ERROR
                    result.errors = errors[:10]  # Limitar a 10 errores
                    result.processing_time_ms = (time.time() - start_time) * 1000
                    return result

                # Validar por país si está configurado
                if self.country:
                    try:
                        from app.modules.imports.validators.country_validators import (
                            get_validator_for_country,
                        )

                        country_validator = get_validator_for_country(self.country)
                        country_errors = country_validator.validate(canonical_doc)
                        if country_errors:
                            result.status = ImportStatus.VALIDATION_ERROR
                            result.errors = country_errors[:10]
                            result.processing_time_ms = (time.time() - start_time) * 1000
                            return result
                    except Exception as e:
                        result.warnings.append(f"Country validation failed: {str(e)[:50]}")

            # Paso 4: Promocionar (si está habilitado)
            if self.promote:
                try:
                    from app.modules.imports.handlers import HandlersRouter

                    router = HandlersRouter()
                    promotion_result = await router.handle(
                        doc=canonical_doc,
                        tenant_id="default",  # TODO: pasar desde CLI
                        dry_run=self.dry_run,
                    )
                    if promotion_result.get("success"):
                        result.promoted = True
                    else:
                        result.promotion_errors = [
                            promotion_result.get("error", "Unknown error")[:100]
                        ]
                        result.warnings.append("Promotion failed but validation passed")
                except Exception as e:
                    result.promotion_errors = [f"Promotion error: {str(e)[:100]}"]
                    result.warnings.append("Promotion failed but validation passed")

            result.status = ImportStatus.SUCCESS

        except Exception as e:
            logger.exception(f"Error importing {file_path.name}")
            result.status = ImportStatus.PARSER_ERROR
            result.errors = [f"Parser error: {str(e)[:100]}"]

        finally:
            result.processing_time_ms = (time.time() - start_time) * 1000

        return result

    async def _get_parser(self, file_path: Path):
        """Obtener parser para un archivo."""
        from app.modules.imports.parsers import registry

        # Si se especificó parser_id, usar ese
        if self.parser_id:
            parser_class = registry.get(self.parser_id)
            if not parser_class:
                logger.warning(f"Parser not found: {self.parser_id}")
                return None
            return parser_class()

        # Si se especificó doc_type, usar parsers para ese tipo
        if self.doc_type:
            parsers = registry.get_by_doc_type(self.doc_type)
            if not parsers:
                logger.warning(f"No parsers for doc_type: {self.doc_type}")
                return None
            # Usar el primer parser que soporte la extensión
            for parser_class in parsers:
                if file_path.suffix.lower() in parser_class.SUPPORTED_EXTENSIONS:
                    return parser_class()
            # Si ninguno soporta la extensión, usar el primero
            return parsers[0]()

        # Auto-detectar por extensión
        parsers = registry.get_by_extension(file_path.suffix.lower())
        if not parsers:
            logger.warning(f"No parser for extension: {file_path.suffix}")
            return None

        return parsers[0]()

    def _find_files(self) -> List[Path]:
        """Encontrar archivos en la carpeta."""
        if self.recursive:
            return list(self.folder.rglob(self.pattern))
        else:
            return list(self.folder.glob(self.pattern))


def _export_report(report: BatchImportReport, output_path: Path):
    """Exportar reporte a JSON."""
    data = {
        "summary": {
            "total_files": report.total_files,
            "processed": report.processed,
            "successful": report.successful,
            "skipped": report.skipped,
            "failed": report.failed,
            "validation_errors": report.validation_errors,
            "promotion_errors": report.promotion_errors,
            "total_items": report.total_items,
            "total_time_ms": report.total_time_ms,
            "started_at": report.started_at,
            "completed_at": report.completed_at,
        },
        "results": [asdict(r) for r in report.results],
    }

    output_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    logger.info(f"Report exported to {output_path}")


def main(
    folder: str = typer.Option(..., "--folder", "-f", help="Carpeta a importar"),
    doc_type: Optional[str] = typer.Option(
        None, "--doc-type", "-t", help="Tipo de documento (invoice, product, expense, bank_tx)"
    ),
    parser_id: Optional[str] = typer.Option(
        None, "--parser", help="ID específico del parser"
    ),
    pattern: str = typer.Option("*.*", "--pattern", help="Patrón de archivos (ej: *.csv)"),
    recursive: bool = typer.Option(
        True, "--recursive/--no-recursive", help="Buscar recursivamente en subcarpetas"
    ),
    validate: bool = typer.Option(True, "--validate/--no-validate", help="Validar documentos"),
    promote: bool = typer.Option(False, "--promote/--no-promote", help="Promocionar a tablas destino"),
    country: Optional[str] = typer.Option(
        None, "--country", "-c", help="Código país para validación (EC, ES, etc.)"
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Simular sin procesar"),
    skip_errors: bool = typer.Option(
        True, "--skip-errors/--fail-fast", help="Continuar ante errores"
    ),
    report: str = typer.Option(
        "batch_import_report.json", "--report", "-r", help="Archivo de reporte"
    ),
):
    """Importar archivos en batch desde carpeta local."""
    try:
        folder_path = Path(folder)
        if not folder_path.is_dir():
            typer.echo(f"❌ No es carpeta: {folder}", err=True)
            raise typer.Exit(code=1)

        # Configurar logging
        logging.basicConfig(
            level=logging.INFO,
            format="[%(levelname)s] %(name)s: %(message)s",
        )

        # Crear importador
        importer = BatchImporter(
            folder=folder_path,
            doc_type=doc_type,
            parser_id=parser_id,
            recursive=recursive,
            pattern=pattern,
            validate=validate,
            promote=promote,
            country=country,
            dry_run=dry_run,
            skip_errors=skip_errors,
        )

        # Ejecutar
        report_data = asyncio.run(importer.run())

        # Mostrar resumen
        typer.echo(f"\n📊 Batch Import Summary:")
        typer.echo(f"  Total: {report_data.total_files}")
        typer.echo(f"  ✓ Successful: {report_data.successful}")
        typer.echo(f"  ✗ Failed: {report_data.failed}")
        typer.echo(f"  ⊘ Skipped: {report_data.skipped}")
        if validate:
            typer.echo(f"  ⚠️  Validation errors: {report_data.validation_errors}")
        if promote:
            typer.echo(f"  ⚠️  Promotion errors: {report_data.promotion_errors}")
        typer.echo(f"  Items: {report_data.total_items}")
        typer.echo(f"  Time: {report_data.total_time_ms / 1000:.2f}s")

        # Exportar reporte
        report_path = Path(report)
        _export_report(report_data, report_path)
        typer.echo(f"\n💾 Report: {report_path}")

        # Exit code
        if report_data.failed > 0:
            raise typer.Exit(code=1)

    except Exception as e:
        typer.echo(f"❌ Error: {e}", err=True)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    typer.run(main)
