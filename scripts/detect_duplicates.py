#!/usr/bin/env python3
"""
Script to detect code duplication patterns in GestiQCloud.
Analyzes backend models and frontend types to identify opportunities for refactoring.
"""

import ast
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict, Counter


class DuplicateDetector:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.backend_root = self.project_root / "apps" / "backend" / "app"
        self.admin_root = self.project_root / "apps" / "admin" / "src"
        self.tenant_root = self.project_root / "apps" / "tenant" / "src"

        self.findings = {
            "backend_models": [],
            "backend_schemas": [],
            "frontend_types": [],
            "frontend_components": [],
            "validation_patterns": [],
        }

    def analyze(self) -> Dict:
        """Run complete analysis and return findings."""
        print(" Analyzing code duplication patterns...")

        self.analyze_backend_models()
        self.analyze_backend_schemas()
        self.analyze_frontend_types()
        self.analyze_validation_patterns()

        return self.findings

    def analyze_backend_models(self):
        """Analyze SQLAlchemy models for catalog patterns."""
        print("   Analyzing backend models...")

        model_files = list(self.backend_root.rglob("models/**/*.py"))

        for file_path in model_files:
            if "__pycache__" in str(file_path):
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Check for catalog-like patterns
                patterns = self._detect_catalog_patterns(content, file_path)
                if patterns:
                    self.findings["backend_models"].extend(patterns)

            except Exception as e:
                print(f"    ⚠️  Error analyzing {file_path}: {e}")

    def _detect_catalog_patterns(self, content: str, file_path: Path) -> List[Dict]:
        """Detect catalog model patterns in SQLAlchemy models."""
        patterns = []

        # Pattern 1: Models with id, tenant_id, code, name, description, is_active
        if self._has_catalog_fields(content):
            class_matches = re.findall(r'class\s+(\w+)\s*\([^)]*\)\s*:', content)
            for class_name in class_matches:
                if not class_name.startswith('Base'):
                    patterns.append({
                        "type": "catalog_model",
                        "file": str(file_path.relative_to(self.project_root)),
                        "class": class_name,
                        "suggestion": "Use BaseCatalogModel or BaseCatalogModelWithoutTenant"
                    })

        # Pattern 2: Repetitive field definitions
        field_patterns = re.findall(
            r'(id:\s*Mapped\[.*?\]\s*=\s*mapped_column.*?primary_key.*?default=uuid4)',
            content
        )
        if len(field_patterns) > 1:
            patterns.append({
                "type": "duplicate_id_fields",
                "file": str(file_path.relative_to(self.project_root)),
                "count": len(field_patterns),
                "suggestion": "Use BaseCatalogModel to inherit common fields"
            })

        # Pattern 3: Repetitive timestamp fields
        timestamp_patterns = re.findall(
            r'(created_at:\s*Mapped\[datetime\]\s*=\s*mapped_column.*?default=_get_now.*?server_default=func\.now)',
            content
        )
        if len(timestamp_patterns) > 1:
            patterns.append({
                "type": "duplicate_timestamp_fields",
                "file": str(file_path.relative_to(self.project_root)),
                "count": len(timestamp_patterns),
                "suggestion": "Use BaseCatalogModel for automatic timestamps"
            })

        return patterns

    def _has_catalog_fields(self, content: str) -> bool:
        """Check if content has catalog-like field patterns."""
        catalog_fields = [
            r'id:\s*Mapped\[.*?\]\s*=.*mapped_column.*primary_key',
            r'tenant_id:\s*Mapped\[.*?\]\s*=.*mapped_column.*ForeignKey',
            r'code:\s*Mapped\[.*?\]\s*=.*mapped_column.*String',
            r'name:\s*Mapped\[.*?\]\s*=.*mapped_column.*String.*nullable=False',
            r'description:\s*Mapped\[.*?\]\s*=.*mapped_column.*Text',
            r'is_active:\s*Mapped\[.*?\]\s*=.*mapped_column.*Boolean.*default=True',
            r'created_at:\s*Mapped\[datetime\]\s*=.*mapped_column',
            r'updated_at:\s*Mapped\[datetime\]\s*=.*mapped_column.*onupdate'
        ]

        return all(re.search(pattern, content) for pattern in catalog_fields)

    def analyze_backend_schemas(self):
        """Analyze Pydantic schemas for duplication."""
        print("   Analyzing backend schemas...")

        schema_files = list(self.backend_root.rglob("schemas/**/*.py"))

        for file_path in schema_files:
            if "__pycache__" in str(file_path):
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                patterns = self._detect_schema_patterns(content, file_path)
                if patterns:
                    self.findings["backend_schemas"].extend(patterns)

            except Exception as e:
                print(f"    ⚠️  Error analyzing {file_path}: {e}")

    def _detect_schema_patterns(self, content: str, file_path: Path) -> List[Dict]:
        """Detect schema duplication patterns."""
        patterns = []

        # Pattern 1: Base/Create/Update/Response pattern
        base_classes = re.findall(r'class\s+(\w+Base)\s*\([^)]*\)\s*:', content)
        create_classes = re.findall(r'class\s+(\w+Create)\s*\([^)]*\)\s*:\s*pass', content)
        update_classes = re.findall(r'class\s+(\w+Update)\s*\([^)]*\)\s*:', content)
        response_classes = re.findall(r'class\s+(\w+Response)\s*\([^)]*\)\s*:', content)

        if len(base_classes) >= 3:  # Multiple base classes suggest duplication
            patterns.append({
                "type": "duplicate_schema_pattern",
                "file": str(file_path.relative_to(self.project_root)),
                "base_count": len(base_classes),
                "create_count": len(create_classes),
                "update_count": len(update_classes),
                "response_count": len(response_classes),
                "suggestion": "Use schema_generator.create_catalog_schemas()"
            })

        return patterns

    def analyze_frontend_types(self):
        """Analyze TypeScript types for duplication."""
        print("  Analyzing frontend types...")

        admin_types = list(self.admin_root.rglob("types/**/*.ts"))
        tenant_types = list(self.tenant_root.rglob("types/**/*.ts"))

        # Find duplicate type definitions
        type_definitions = defaultdict(list)

        for file_path in admin_types + tenant_types:
            if "__tests__" in str(file_path):
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Extract interface/type definitions
                type_matches = re.findall(r'export\s+(interface|type)\s+(\w+)', content)
                for kind, type_name in type_matches:
                    type_definitions[type_name].append({
                        "file": str(file_path.relative_to(self.project_root)),
                        "kind": kind
                    })

            except Exception as e:
                print(f"    ⚠️  Error analyzing {file_path}: {e}")

        # Find duplicates
        for type_name, definitions in type_definitions.items():
            if len(definitions) > 1:
                self.findings["frontend_types"].append({
                    "type": "duplicate_type_definition",
                    "type_name": type_name,
                    "locations": definitions,
                    "suggestion": "Move to @packages/api-types/src/catalogs.ts"
                })

    def analyze_validation_patterns(self):
        """Analyze validation patterns for duplication."""
        print("  Analyzing validation patterns...")

        # Look for manual UUID validation patterns
        python_files = list(self.backend_root.rglob("**/*.py"))

        uuid_validations = []
        tenant_extractions = []

        for file_path in python_files:
            if "__pycache__" in str(file_path):
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Pattern 1: Manual UUID validation
                uuid_validation = re.findall(
                    r'UUID\(str\([^)]+\)\s*except\s+\(ValueError.*?TypeError\)',
                    content
                )
                if uuid_validation:
                    uuid_validations.append({
                        "file": str(file_path.relative_to(self.project_root)),
                        "count": len(uuid_validation)
                    })

                # Pattern 2: Manual tenant extraction
                tenant_extraction = re.findall(
                    r'tenant_id\s*=\s*claims\.get\(["\']tenant_id["\']',
                    content
                )
                if tenant_extraction:
                    tenant_extractions.append({
                        "file": str(file_path.relative_to(self.project_root)),
                        "count": len(tenant_extraction)
                    })

            except Exception as e:
                print(f"    ⚠️  Error analyzing {file_path}: {e}")

        if uuid_validations:
            self.findings["validation_patterns"].append({
                "type": "manual_uuid_validation",
                "total_count": sum(v["count"] for v in uuid_validations),
                "files": uuid_validations,
                "suggestion": "Use @validate_uuid decorator"
            })

        if tenant_extractions:
            self.findings["validation_patterns"].append({
                "type": "manual_tenant_extraction",
                "total_count": sum(t["count"] for t in tenant_extractions),
                "files": tenant_extractions,
                "suggestion": "Use @tenant_required decorator"
            })

    def generate_report(self) -> str:
        """Generate a detailed report of findings."""
        report = []
        report.append("# Code Duplication Analysis Report")
        report.append("=" * 50)
        report.append("")

        # Summary
        total_issues = sum(len(findings) for findings in self.findings.values())
        report.append(f"## Summary")
        report.append(f"- **Total Issues Found**: {total_issues}")
        report.append(f"- **Backend Model Issues**: {len(self.findings['backend_models'])}")
        report.append(f"- **Backend Schema Issues**: {len(self.findings['backend_schemas'])}")
        report.append(f"- **Frontend Type Issues**: {len(self.findings['frontend_types'])}")
        report.append(f"- **Validation Pattern Issues**: {len(self.findings['validation_patterns'])}")
        report.append("")

        # Backend Models
        if self.findings["backend_models"]:
            report.append("## Backend Models")
            report.append("")
            for issue in self.findings["backend_models"]:
                report.append(f"### {issue['type']}")
                report.append(f"- **File**: `{issue['file']}`")
                if 'class' in issue:
                    report.append(f"- **Class**: `{issue['class']}`")
                if 'count' in issue:
                    report.append(f"- **Count**: {issue['count']}")
                report.append(f"- **Suggestion**: {issue['suggestion']}")
                report.append("")

        # Backend Schemas
        if self.findings["backend_schemas"]:
            report.append("## Backend Schemas")
            report.append("")
            for issue in self.findings["backend_schemas"]:
                report.append(f"### {issue['type']}")
                report.append(f"- **File**: `{issue['file']}`")
                report.append(f"- **Base Classes**: {issue.get('base_count', 0)}")
                report.append(f"- **Suggestion**: {issue['suggestion']}")
                report.append("")

        # Frontend Types
        if self.findings["frontend_types"]:
            report.append("## Frontend Types")
            report.append("")
            for issue in self.findings["frontend_types"]:
                report.append(f"### {issue['type']}")
                report.append(f"- **Type**: `{issue['type_name']}`")
                report.append("- **Locations**:")
                for location in issue["locations"]:
                    report.append(f"  - `{location['file']}` ({location['kind']})")
                report.append(f"- **Suggestion**: {issue['suggestion']}")
                report.append("")

        # Validation Patterns
        if self.findings["validation_patterns"]:
            report.append("## Validation Patterns")
            report.append("")
            for issue in self.findings["validation_patterns"]:
                report.append(f"### {issue['type']}")
                report.append(f"- **Total Count**: {issue['total_count']}")
                report.append("- **Files**:")
                for file_info in issue["files"]:
                    report.append(f"  - `{file_info['file']}` ({file_info['count']} occurrences)")
                report.append(f"- **Suggestion**: {issue['suggestion']}")
                report.append("")

        # Recommendations
        report.append("## Recommendations")
        report.append("")

        recommendations = []

        if self.findings["backend_models"]:
            recommendations.append("**High Priority**: Apply BaseCatalogModel to catalog models")

        if self.findings["backend_schemas"]:
            recommendations.append("**High Priority**: Use schema_generator for catalog schemas")

        if self.findings["validation_patterns"]:
            recommendations.append("**High Priority**: Replace manual validations with decorators")

        if self.findings["frontend_types"]:
            recommendations.append("**Medium Priority**: Centralize frontend types in @packages/api-types")

        if not recommendations:
            report.append("No duplication issues found.")

        for index, recommendation in enumerate(recommendations, start=1):
            report.append(f"{index}. {recommendation}")

        report.append("")


def main():
    """Main function to run the duplicate detection."""
    project_root = Path(__file__).parent.parent

    print(" Starting Code Duplication Detection")
    print(f" Project Root: {project_root}")
    print("")

    detector = DuplicateDetector(str(project_root))
    findings = detector.analyze()

    report = detector.generate_report()

    # Save report
    report_path = project_root / "docs" / "duplication-report.md"
    report_path.parent.mkdir(exist_ok=True)

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f" Report saved to: {report_path}")
    print("")
    print(" Summary:")
    for category, issues in findings.items():
        print(f"  {category}: {len(issues)} issues")

    return findings


if __name__ == "__main__":
    main()
