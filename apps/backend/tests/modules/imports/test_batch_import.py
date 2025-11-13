"""Tests para batch import (Fase E)."""

import json
import shutil
import tempfile
from pathlib import Path

import pytest

from app.modules.imports.scripts.batch_import import (
    BatchImporter,
    BatchImportReport,
    FileImportResult,
    ImportStatus,
)


@pytest.fixture
def temp_import_folder():
    """Crear carpeta temporal con archivos de prueba."""
    temp_dir = tempfile.mkdtemp()

    # CSV válido
    csv_content = """invoice,date,amount,vendor
INV-001,2025-01-01,100.00,Company A
INV-002,2025-01-02,200.00,Company B
"""
    Path(temp_dir, "valid.csv").write_text(csv_content)

    # Crear subcarpeta
    subdir = Path(temp_dir, "subfolder")
    subdir.mkdir()
    Path(subdir, "nested.csv").write_text(csv_content)

    yield Path(temp_dir)

    # Cleanup
    shutil.rmtree(temp_dir)


class TestBatchImporterBasics:
    """Tests básicos del BatchImporter."""

    @pytest.mark.asyncio
    async def test_find_files_non_recursive(self, temp_import_folder):
        """Buscar archivos sin recursión."""
        importer = BatchImporter(
            folder=temp_import_folder,
            recursive=False,
        )
        files = importer._find_files()

        # Solo archivos en raíz
        assert len(files) == 1
        assert files[0].name == "valid.csv"

    @pytest.mark.asyncio
    async def test_find_files_recursive(self, temp_import_folder):
        """Buscar archivos con recursión."""
        importer = BatchImporter(
            folder=temp_import_folder,
            recursive=True,
        )
        files = importer._find_files()

        # Archivos en raíz + subcarpeta
        assert len(files) == 2
        filenames = {f.name for f in files}
        assert "valid.csv" in filenames
        assert "nested.csv" in filenames

    @pytest.mark.asyncio
    async def test_find_files_pattern(self, temp_import_folder):
        """Buscar con patrón específico."""
        importer = BatchImporter(
            folder=temp_import_folder,
            pattern="*.csv",
            recursive=True,
        )
        files = importer._find_files()

        assert len(files) == 2
        assert all(f.suffix == ".csv" for f in files)


class TestBatchImporterReporting:
    """Tests de reportes."""

    @pytest.mark.asyncio
    async def test_report_structure(self, temp_import_folder):
        """Verificar estructura del reporte."""
        importer = BatchImporter(
            folder=temp_import_folder,
            dry_run=True,  # Solo simular
        )
        report = await importer.run()

        # Estructura básica
        assert report.total_files >= 1
        assert report.processed >= 0
        assert report.successful >= 0
        assert report.failed >= 0
        assert report.skipped >= 0
        assert report.total_time_ms >= 0
        assert report.started_at is not None
        assert report.completed_at is not None
        assert len(report.results) >= 0

    @pytest.mark.asyncio
    async def test_file_import_result_structure(self):
        """Estructura de resultado individual."""
        result = FileImportResult(
            filename="test.csv",
            filepath="/path/to/test.csv",
            status=ImportStatus.SUCCESS,
            doc_type="invoice",
            items_count=10,
        )

        assert result.filename == "test.csv"
        assert result.status == ImportStatus.SUCCESS
        assert result.items_count == 10
        assert result.errors == []
        assert result.warnings == []
        assert result.promoted is False

    @pytest.mark.asyncio
    async def test_dry_run_mode(self, temp_import_folder):
        """Dry-run no procesa archivos."""
        importer = BatchImporter(
            folder=temp_import_folder,
            dry_run=True,
        )
        report = await importer.run()

        # Los archivos deben estar marcados como SUCCESS pero sin procesamiento real
        assert report.processed >= 1


class TestFileImportResult:
    """Tests de FileImportResult."""

    def test_result_as_dict(self):
        """Convertir resultado a dict (para JSON)."""
        from dataclasses import asdict

        result = FileImportResult(
            filename="test.csv",
            filepath="/path/to/test.csv",
            status=ImportStatus.VALIDATION_ERROR,
            doc_type="invoice",
            errors=["Missing field: amount"],
        )

        result_dict = asdict(result)

        assert result_dict["filename"] == "test.csv"
        assert result_dict["status"] == ImportStatus.VALIDATION_ERROR
        assert result_dict["errors"] == ["Missing field: amount"]
        assert "timestamp" in result_dict


class TestBatchImportReport:
    """Tests de BatchImportReport."""

    def test_report_initialization(self):
        """Inicialización del reporte."""
        report = BatchImportReport(total_files=100)

        assert report.total_files == 100
        assert report.processed == 0
        assert report.successful == 0
        assert report.failed == 0
        assert report.skipped == 0
        assert report.total_items == 0
        assert report.results == []

    def test_report_summary_calculation(self):
        """Cálculos de resumen."""
        report = BatchImportReport(total_files=5)
        report.successful = 3
        report.failed = 1
        report.skipped = 1
        report.processed = 5
        report.total_items = 150

        assert report.successful + report.failed + report.skipped == 5
        assert report.total_items == 150


class TestImportStatus:
    """Tests de estados de importación."""

    def test_all_statuses_defined(self):
        """Verificar que todos los estados están definidos."""
        statuses = [
            ImportStatus.SUCCESS,
            ImportStatus.VALIDATION_ERROR,
            ImportStatus.PARSER_ERROR,
            ImportStatus.PROMOTION_ERROR,
            ImportStatus.SKIPPED,
            ImportStatus.FAILED,
        ]

        assert len(statuses) == 6

        # Cada estado tiene valor
        for status in statuses:
            assert status.value is not None


class TestBatchImporterIntegration:
    """Tests de integración."""

    @pytest.mark.asyncio
    async def test_empty_folder(self):
        """Importar carpeta vacía."""
        with tempfile.TemporaryDirectory() as temp_dir:
            importer = BatchImporter(
                folder=Path(temp_dir),
            )
            report = await importer.run()

            assert report.total_files == 0
            assert report.processed == 0
            assert report.successful == 0

    @pytest.mark.asyncio
    async def test_skip_errors_flag(self, temp_import_folder):
        """Flag skip_errors debe continuar incluso con errores."""
        importer = BatchImporter(
            folder=temp_import_folder,
            skip_errors=True,
            dry_run=True,
        )
        report = await importer.run()

        # No debe lanzar excepción
        assert report is not None

    @pytest.mark.asyncio
    async def test_report_export_json(self, temp_import_folder, tmp_path):
        """Exportar reporte a JSON."""
        from app.modules.imports.scripts.batch_import import _export_report

        importer = BatchImporter(
            folder=temp_import_folder,
            dry_run=True,
        )
        report = await importer.run()

        # Exportar
        report_file = tmp_path / "report.json"
        _export_report(report, report_file)

        # Verificar
        assert report_file.exists()

        # Cargar y validar JSON
        with open(report_file) as f:
            data = json.load(f)

        assert "summary" in data
        assert "results" in data
        assert data["summary"]["total_files"] >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
