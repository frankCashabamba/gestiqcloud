"""CLI para importación batch de archivos.

Útil para entornos on-premise y automatización.

Uso:
    python -m app.modules.imports.cli import-folder --path /ruta/carpeta --doc-type invoice
    python -m app.modules.imports.cli classify --path /ruta/archivo.csv
    python -m app.modules.imports.cli list-parsers
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

import typer

# Setup logging
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("app.imports.cli")

app = typer.Typer(help="CLI para importación de archivos")


@app.command()
def list_parsers():
    """Listar todos los parsers disponibles."""
    try:
        from app.modules.imports.parsers import registry

        parsers = registry.list()
        if not parsers:
            typer.echo("No hay parsers registrados")
            return

        typer.echo("\n📋 Parsers Disponibles:\n")
        for meta in parsers:
            typer.echo(f"  ID: {meta.id}")
            typer.echo(f"    Doc Type: {meta.doc_type}")
            typer.echo(f"    Extensiones: {', '.join(meta.extensions)}")
            typer.echo(f"    Descripción: {meta.description}")
            typer.echo()
    except Exception as e:
        typer.echo(f"❌ Error: {e}", err=True)
        raise typer.Exit(code=1)


@app.command()
def classify(
    path: str = typer.Option(..., "--path", "-p", help="Ruta del archivo"),
    use_ai: bool = typer.Option(True, "--use-ai", help="Usar IA para mejorar clasificación"),
):
    """Clasificar un archivo."""
    try:
        file_path = Path(path)
        if not file_path.exists():
            typer.echo(f"❌ Archivo no existe: {path}", err=True)
            raise typer.Exit(code=1)

        from app.modules.imports.services.classifier import classifier

        typer.echo(f"\n🔍 Clasificando: {file_path.name}")

        if use_ai:
            # Usar clasificación con IA
            result = asyncio.run(classifier.classify_file_with_ai(str(file_path), file_path.name))
            typer.echo("\n✅ Clasificación (con IA):")
        else:
            # Usar solo heurísticas
            result = classifier.classify_file(str(file_path), file_path.name)
            typer.echo("\n✅ Clasificación (heurísticas):")

        typer.echo(json.dumps(result, indent=2, default=str))

    except Exception as e:
        typer.echo(f"❌ Error: {e}", err=True)
        raise typer.Exit(code=1)


@app.command()
def import_folder(
    path: str = typer.Option(..., "--path", "-p", help="Ruta de la carpeta"),
    doc_type: str | None = typer.Option(
        None, "--doc-type", "-t", help="Tipo de documento (invoice, expense, product, bank_tx)"
    ),
    parser_id: str | None = typer.Option(None, "--parser", help="ID del parser específico"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Simular sin procesar"),
    pattern: str = typer.Option("*.*", "--pattern", help="Patrón de archivos (ej: *.csv)"),
):
    """Importar archivos desde una carpeta."""
    try:
        folder = Path(path)
        if not folder.is_dir():
            typer.echo(f"❌ No es carpeta: {path}", err=True)
            raise typer.Exit(code=1)

        from app.modules.imports.domain.canonical_schema import CanonicalDocument
        from app.modules.imports.parsers import registry

        # Encontrar archivos
        files = list(folder.glob(pattern))
        if not files:
            typer.echo(f"⚠️  No se encontraron archivos con patrón: {pattern}")
            raise typer.Exit(code=0)

        typer.echo(f"\n📁 Carpeta: {folder}")
        typer.echo(f"📄 Archivos encontrados: {len(files)}\n")

        processed = 0
        errors = 0
        canonical_docs: list[CanonicalDocument] = []

        for file_path in files:
            if file_path.is_dir():
                continue

            typer.echo(f"  📄 {file_path.name}...", nl=False)

            try:
                # Obtener parser
                if parser_id:
                    parser = registry.get(parser_id)
                    if not parser:
                        typer.echo(f" ❌ Parser no encontrado: {parser_id}")
                        errors += 1
                        continue
                else:
                    # Auto-detectar
                    parsers = registry.get_by_extension(file_path.suffix.lower())
                    if doc_type:
                        parsers = [p for p in parsers if p.DOC_TYPE == doc_type]

                    if not parsers:
                        typer.echo(f" ⚠️  No hay parser para {file_path.suffix}")
                        continue

                    parser = parsers[0]

                if dry_run:
                    typer.echo(f" ✓ (dry-run, parser: {parser.PARSER_ID})")
                else:
                    # Parsear archivo
                    doc = asyncio.run(parser.parse(str(file_path)))
                    canonical_docs.append(doc)
                    typer.echo(f" ✓ ({len(doc.items)} items)")
                    processed += 1

            except Exception as e:
                typer.echo(f" ❌ {str(e)[:60]}")
                errors += 1
                logger.exception(f"Error procesando {file_path.name}")

        # Resumen
        typer.echo("\n📊 Resumen:")
        typer.echo(f"  ✓ Procesados: {processed}")
        typer.echo(f"  ❌ Errores: {errors}")
        typer.echo(f"  ⚠️  Skipped: {len(files) - processed - errors}")

        # Exportar canonical docs si no es dry-run
        if not dry_run and canonical_docs:
            output_file = (
                folder / f"canonical_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            export_data = [doc.dict() for doc in canonical_docs]
            output_file.write_text(json.dumps(export_data, indent=2, default=str), encoding="utf-8")
            typer.echo(f"\n💾 Exportado: {output_file}")

    except Exception as e:
        typer.echo(f"❌ Error: {e}", err=True)
        raise typer.Exit(code=1)


@app.command()
def export_metadata(
    output: str = typer.Option("parsers_metadata.json", "--output", "-o", help="Archivo de salida"),
):
    """Exportar metadata de parsers a JSON."""
    try:
        from app.modules.imports.parsers import registry

        parsers = registry.list()
        metadata = [p.dict() for p in parsers]

        output_path = Path(output)
        output_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        typer.echo(f"✅ Metadata exportada: {output_path}")
        typer.echo(f"   Total parsers: {len(metadata)}")

    except Exception as e:
        typer.echo(f"❌ Error: {e}", err=True)
        raise typer.Exit(code=1)


@app.command()
def validate_file(
    path: str = typer.Option(..., "--path", "-p", help="Ruta del archivo parseado (JSON)"),
    country: str | None = typer.Option(None, "--country", "-c", help="Código país (EC, ES, etc.)"),
):
    """Validar archivo parseado."""
    try:
        file_path = Path(path)
        if not file_path.exists():
            typer.echo(f"❌ Archivo no existe: {path}", err=True)
            raise typer.Exit(code=1)

        from app.modules.imports.domain.canonical_schema import CanonicalDocument
        from app.modules.imports.validators import validate_canonical

        # Cargar documento canónico
        with open(file_path, encoding="utf-8") as f:
            doc_dict = json.load(f)

        doc = CanonicalDocument(**doc_dict)

        typer.echo(f"\n✔️  Documento: {doc.doc_type}")
        typer.echo(f"   Items: {len(doc.items)}")

        # Validar
        errors = validate_canonical(doc)

        if not errors:
            typer.echo("\n✅ Validación exitosa (sin errores)")
        else:
            typer.echo("\n⚠️  Validación con errores:")
            for error in errors:
                typer.echo(f"  - {error}")

    except Exception as e:
        typer.echo(f"❌ Error: {e}", err=True)
        raise typer.Exit(code=1)


@app.command()
def batch_import(
    folder: str = typer.Option(..., "--folder", "-f", help="Carpeta a importar"),
    doc_type: str | None = typer.Option(
        None, "--doc-type", "-t", help="Tipo de documento (invoice, product, expense, bank_tx)"
    ),
    parser_id: str | None = typer.Option(None, "--parser", help="ID específico del parser"),
    pattern: str = typer.Option("*.*", "--pattern", help="Patrón de archivos (ej: *.csv)"),
    recursive: bool = typer.Option(
        True, "--recursive/--no-recursive", help="Buscar recursivamente en subcarpetas"
    ),
    validate: bool = typer.Option(True, "--validate/--no-validate", help="Validar documentos"),
    promote: bool = typer.Option(
        False, "--promote/--no-promote", help="Promocionar a tablas destino"
    ),
    country: str | None = typer.Option(
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
    """Importar archivos en batch desde carpeta local (Fase E)."""
    try:
        from pathlib import Path

        from app.modules.imports.scripts.batch_import import BatchImporter

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
        typer.echo("\n📊 Batch Import Summary:")
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
        from app.modules.imports.scripts.batch_import import _export_report

        _export_report(report_data, report_path)
        typer.echo(f"\n💾 Report: {report_path}")

        # Exit code
        if report_data.failed > 0:
            raise typer.Exit(code=1)

    except Exception as e:
        typer.echo(f"❌ Error: {e}", err=True)
        raise typer.Exit(code=1)


@app.command()
def health():
    """Health check de configuración."""
    try:
        from app.config.settings import settings

        typer.echo("\n🏥 Health Check:\n")

        # Parsers
        try:
            from app.modules.imports.parsers import registry

            parsers = registry.list()
            typer.echo(f"  ✅ Parsers: {len(parsers)} registrados")
        except Exception as e:
            typer.echo(f"  ❌ Parsers: {e}")

        # IA Provider
        typer.echo(f"  ✅ IA Provider: {settings.IMPORT_AI_PROVIDER}")
        typer.echo(f"  ✅ IA Threshold: {settings.IMPORT_AI_CONFIDENCE_THRESHOLD}")
        typer.echo(f"  ✅ IA Cache: {settings.IMPORT_AI_CACHE_ENABLED}")

        # Database
        try:
            from app.config.database import ping as db_ping

            db_ping()
            typer.echo("  ✅ Database: Connected")
        except Exception:
            typer.echo("  ⚠️  Database: No connection (optional)")

        typer.echo("\n✅ Sistema listo")

    except Exception as e:
        typer.echo(f"❌ Error: {e}", err=True)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
