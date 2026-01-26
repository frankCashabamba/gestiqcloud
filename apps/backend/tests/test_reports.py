"""Reports module tests"""

from uuid import uuid4

import pytest

from app.modules.reports.domain.entities import (
    InventoryReport,
    ReportDefinition,
    ReportType,
    SalesReport,
)
from app.modules.reports.infrastructure.report_generator import ReportExporter


class TestReportDefinition:
    """Test report definition entity"""

    def test_create_report_definition(self):
        """Test creating report definition"""
        definition = ReportDefinition(
            id=uuid4(),
            tenant_id="tenant-1",
            name="Monthly Sales Report",
            report_type=ReportType.SALES_SUMMARY,
            include_totals=True,
            include_charts=True,
        )

        assert definition.name == "Monthly Sales Report"
        assert definition.report_type == ReportType.SALES_SUMMARY
        assert definition.include_totals is True


class TestSalesReport:
    """Test sales report generation"""

    def test_sales_report_structure(self):
        """Test sales report data structure"""
        report = SalesReport(
            columns=["Date", "Orders", "Items", "Total"],
            rows=[
                ["2024-01-19", 5, 15, "$1500.00"],
                ["2024-01-18", 3, 9, "$900.00"],
            ],
            total_sales=2400.00,
            total_items=24,
            order_count=8,
            average_order_value=300.00,
        )

        assert len(report.columns) == 4
        assert len(report.rows) == 2
        assert report.total_sales == 2400.00
        assert report.average_order_value == 300.00


class TestInventoryReport:
    """Test inventory report"""

    def test_inventory_report_structure(self):
        """Test inventory report data structure"""
        report = InventoryReport(
            columns=["Product", "Stock", "Unit Price", "Total Value"],
            rows=[
                ["Product A", 10, "$10.00", "$100.00"],
                ["Product B", 5, "$20.00", "$100.00"],
            ],
            total_items=2,
            low_stock_count=1,
            out_of_stock_count=0,
            total_value=200.00,
        )

        assert report.total_items == 2
        assert report.low_stock_count == 1
        assert report.total_value == 200.00


class TestReportExporter:
    """Test report export formats"""

    def test_export_to_json(self):
        """Test JSON export"""
        report = SalesReport(
            columns=["Date", "Total"],
            rows=[["2024-01-19", "$1500.00"]],
            summary={"total_sales": 1500.00},
        )

        json_bytes = ReportExporter.to_json(report)
        assert isinstance(json_bytes, bytes)
        assert b"Date" in json_bytes
        assert b"total_sales" in json_bytes

    def test_export_to_csv(self):
        """Test CSV export"""
        report = SalesReport(
            columns=["Date", "Orders", "Total"],
            rows=[
                ["2024-01-19", 5, "$1500.00"],
                ["2024-01-18", 3, "$900.00"],
            ],
            summary={"total_orders": 8},
        )

        csv_bytes = ReportExporter.to_csv(report)
        csv_str = csv_bytes.decode("utf-8")

        assert "Date" in csv_str
        assert "2024-01-19" in csv_str
        assert "total_orders" in csv_str

    def test_export_to_html(self):
        """Test HTML export"""
        report = SalesReport(
            columns=["Date", "Total"],
            rows=[["2024-01-19", "$1500.00"]],
        )

        html = ReportExporter.to_html(report, "Sales Report")
        assert "<table>" in html
        assert "Date" in html
        assert "2024-01-19" in html

    @pytest.mark.skipif(True, reason="Requires reportlab")
    def test_export_to_pdf(self):
        """Test PDF export"""
        report = SalesReport(
            columns=["Date", "Total"],
            rows=[["2024-01-19", "$1500.00"]],
        )

        pdf_bytes = ReportExporter.to_pdf(report, "Sales Report")
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0

    @pytest.mark.skipif(True, reason="Requires openpyxl")
    def test_export_to_excel(self):
        """Test Excel export"""
        report = SalesReport(
            columns=["Date", "Total"],
            rows=[["2024-01-19", "$1500.00"]],
            summary={"Total Sales": "$1500.00"},
        )

        excel_bytes = ReportExporter.to_excel(report)
        assert isinstance(excel_bytes, bytes)
        assert len(excel_bytes) > 0


class TestReportGeneration:
    """Test report generation"""

    def test_report_data_structure(self):
        """Test report data structure"""
        report = SalesReport(
            columns=["Col1", "Col2"],
            rows=[["Row1Col1", "Row1Col2"]],
            summary={"total": 100},
        )

        data_dict = report.to_dict()
        assert "columns" in data_dict
        assert "rows" in data_dict
        assert "summary" in data_dict


class TestReportFiltering:
    """Test report filtering"""

    def test_report_filters(self):
        """Test report filters"""
        definition = ReportDefinition(
            id=uuid4(),
            tenant_id="tenant-1",
            name="Filtered Report",
            report_type=ReportType.SALES_SUMMARY,
            filters={
                "date_from": "2024-01-01",
                "date_to": "2024-01-31",
                "customer_id": "cust-123",
            },
        )

        assert definition.filters["customer_id"] == "cust-123"
        assert definition.filters["date_from"] == "2024-01-01"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
