#!/usr/bin/env python3
"""
Script to automatically apply refactor patterns to existing models and schemas.
Identifies models that can benefit from BaseCatalogModel and applies the refactor.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class RefactorCandidate:
    """Represents a candidate for refactoring."""
    file_path: str
    class_name: str
    current_pattern: str
    suggested_pattern: str
    confidence: float  # 0.0 to 1.0
    changes: List[str]


class RefactorApplier:
    """Automatically applies refactor patterns to existing code."""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.backend_root = self.project_root / "apps" / "backend" / "app"

        # Patterns to detect and replace
        self.patterns = {
            "catalog_model": {
                "detect": r'class\s+(\w+)\s*\([^)]*\)\s*:\s*\n\s*"""[^"]*"""[^"]*"""[^"]*"""[^"]*"""[^"]*"""[^"]*"""[^"]*"""[^"]*__tablename__\s*=\s*"[^"]+',
                "fields": [
                    r'id:\s*Mapped\[.*?\]\s*=\s*mapped_column.*?primary_key.*?default=uuid4',
                    r'tenant_id:\s*Mapped\[.*?\]\s*=\s*mapped_column.*?ForeignKey',
                    r'code:\s*Mapped\[.*?\]\s*=\s*mapped_column.*?String',
                    r'name:\s*Mapped\[.*?\]\s*=\s*mapped_column.*?String.*?nullable=False',
                    r'description:\s*Mapped\[.*?\]\s*=\s*mapped_column.*?Text',
                    r'is_active:\s*Mapped\[.*?\]\s*=\s*mapped_column.*?Boolean.*?default=True',
                    r'created_at:\s*Mapped\[datetime\]\s*=\s*mapped_column.*?default=lambda:.*datetime\.now',
                    r'updated_at:\s*Mapped\[datetime\]\s*=\s*mapped_column.*?onupdate=lambda:.*datetime\.now',
                ],
                "replacement": self._create_catalog_model_replacement(),
                "confidence_threshold": 0.8
            },
            "schema_base_create_update": {
                "detect": r'class\s+(\w+Base)\s*\([^)]*\)\s*:\s*\n.*?class\s+(\w+Create)\s*\([^)]*\)\s*:\s*\n.*?class\s+(\w+Update)\s*\([^)]*\)',
                "replacement": self._create_schema_replacement(),
                "confidence_threshold": 0.7
            }
        }

    def _create_catalog_model_replacement(self) -> str:
        """Create replacement text for catalog model pattern."""
        return '''from app.models.base import BaseCatalogModel

class {class_name}(BaseCatalogModel):
    """{class_name} model - follows catalog pattern"""

    __tablename__ = "{table_name}"
    __table_args__ = {{"extend_existing": True}

    # Additional fields specific to {class_name} go here'''

    def _create_schema_replacement(self) -> str:
        """Create replacement text for schema pattern."""
        return '''from app.utils.schema_generator import get_catalog_schemas

# Generate all schemas automatically - no manual definition needed!
{entity_name}Schemas = get_catalog_schemas("{entity_name}")
{entity_name}Base = {entity_name}Schemas["Base"]
{entity_name}Create = {entity_name}Schemas["Create"]
{entity_name}Update = {entity_name}Schemas["Update"]
{entity_name}Response = {entity_name}Schemas["Response"]

# Export for easy import
__all__ = [
    "{entity_name}Base",
    "{entity_name}Create",
    "{entity_name}Update",
    "{entity_name}Response",
]'''

    def analyze_file(self, file_path: Path) -> List[RefactorCandidate]:
        """Analyze a Python file for refactor candidates."""
        candidates = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            for pattern_name, pattern_config in self.patterns.items():
                matches = re.finditer(pattern_config["detect"], content, re.MULTILINE | re.DOTALL)

                for match in matches:
                    if pattern_name == "catalog_model":
                        candidate = self._analyze_catalog_model_match(match, file_path, pattern_config)
                    elif pattern_name == "schema_base_create_update":
                        candidate = self._analyze_schema_match(match, file_path, pattern_config)
                    else:
                        continue

                    if candidate and candidate.confidence >= pattern_config["confidence_threshold"]:
                        candidates.append(candidate)

        except Exception as e:
            print(f"    ⚠️  Error analyzing {file_path}: {e}")

        return candidates

    def _analyze_catalog_model_match(self, match, file_path: Path, pattern_config: Dict) -> Optional[RefactorCandidate]:
        """Analyze a catalog model pattern match."""
        class_name = match.group(1)

        # Extract table name from __tablename__ if possible
        content = match.group(0)

        # Count matching fields
        field_matches = 0
        for field_pattern in pattern_config["fields"]:
            if re.search(field_pattern, content):
                field_matches += 1

        confidence = field_matches / len(pattern_config["fields"])

        return RefactorCandidate(
            file_path=str(file_path),
            class_name=class_name,
            current_pattern="Manual SQLAlchemy model with duplicate fields",
            suggested_pattern="Inherit from BaseCatalogModel",
            confidence=confidence,
            changes=[
                "Replace manual field definitions with BaseCatalogModel inheritance",
                f"Reduce from ~{field_matches * 15} lines to ~5 lines"
            ]
        )

    def _analyze_schema_match(self, match, file_path: Path, pattern_config: Dict) -> Optional[RefactorCandidate]:
        """Analyze a schema pattern match."""
        base_name = match.group(1)

        # Extract entity name (remove Base/Create/Update suffix)
        entity_name = base_name.replace("Base", "")

        return RefactorCandidate(
            file_path=str(file_path),
            class_name=entity_name,
            current_pattern="Manual Base/Create/Update/Response schemas",
            suggested_pattern="Use schema_generator.create_catalog_schemas()",
            confidence=0.9,  # High confidence for this pattern
            changes=[
                "Replace manual schema definitions with automatic generation",
                "Reduce from ~80 lines to ~3 lines",
                "Ensure consistency across all catalog schemas"
            ]
        )

    def find_candidates(self) -> List[RefactorCandidate]:
        """Find all refactor candidates in the project."""
        print("🔍 Finding refactor candidates...")

        candidates = []

        # Search for model files
        model_files = list(self.backend_root.rglob("models/**/*.py"))
        for file_path in model_files:
            if "__pycache__" in str(file_path):
                continue

            file_candidates = self.analyze_file(file_path)
            candidates.extend(file_candidates)

        # Search for schema files
        schema_files = list(self.backend_root.rglob("schemas/**/*.py"))
        for file_path in schema_files:
            if "__pycache__" in str(file_path):
                continue

            file_candidates = self.analyze_file(file_path)
            candidates.extend(file_candidates)

        return candidates

    def apply_refactor(self, candidate: RefactorCandidate, dry_run: bool = True) -> bool:
        """Apply refactor to a specific candidate."""
        try:
            with open(candidate.file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if "catalog_model" in candidate.suggested_pattern:
                new_content = self._apply_catalog_model_refactor(content, candidate)
            elif "schema_generator" in candidate.suggested_pattern:
                new_content = self._apply_schema_refactor(content, candidate)
            else:
                print(f"    ⚠️  Unknown refactor pattern: {candidate.suggested_pattern}")
                return False

            if dry_run:
                print(f"    📝 Would refactor: {candidate.file_path}")
                print(f"       Class: {candidate.class_name}")
                print(f"       Confidence: {candidate.confidence:.2f}")
                print(f"       Changes: {len(candidate.changes)}")
                return True

            # Write the refactored content
            with open(candidate.file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            print(f"    ✅ Refactored: {candidate.file_path}")
            return True

        except Exception as e:
            print(f"    ❌ Failed to refactor {candidate.file_path}: {e}")
            return False

    def _apply_catalog_model_refactor(self, content: str, candidate: RefactorCandidate) -> str:
        """Apply catalog model refactor to content."""
        # Find the class definition
        class_pattern = rf'class\s+{candidate.class_name}\s*\([^)]*\)\s*:\s*\n'
        class_match = re.search(class_pattern, content)

        if not class_match:
            return content

        # Get table name from existing class
        table_name_match = re.search(r'__tablename__\s*=\s*"([^"]+)"', class_match.group(0))
        table_name = table_name_match.group(1) if table_name_match else candidate.class_name.lower() + "s"

        # Create new class definition
        new_class = f'''from app.models.base import BaseCatalogModel

class {candidate.class_name}(BaseCatalogModel):
    """{candidate.class_name} model - follows catalog pattern"""

    __tablename__ = "{table_name}"
    __table_args__ = {{"extend_existing": True}}

    # Additional fields specific to {candidate.class_name} go here'''

        # Replace the old class definition
        return content[:class_match.start()] + new_class + content[class_match.end():]

    def _apply_schema_refactor(self, content: str, candidate: RefactorCandidate) -> str:
        """Apply schema generator refactor to content."""
        # Find the schema definitions
        schema_pattern = rf'class\s+{candidate.class_name}Base.*?class\s+{candidate.class_name}Create.*?class\s+{candidate.class_name}Update'
        schema_match = re.search(schema_pattern, content, re.DOTALL)

        if not schema_match:
            return content

        # Create new schema definitions
        new_schemas = self.patterns["schema_base_create_update"]["replacement"].format(
            entity_name=candidate.class_name
        )

        # Replace the old schema definitions
        return content[:schema_match.start()] + new_schemas + content[schema_match.end():]

    def generate_report(self, candidates: List[RefactorCandidate]) -> str:
        """Generate a report of refactor candidates."""
        report = []
        report.append("# Automatic Refactor Report")
        report.append("=" * 50)
        report.append("")

        # Summary
        high_confidence = [c for c in candidates if c.confidence >= 0.8]
        medium_confidence = [c for c in candidates if 0.6 <= c.confidence < 0.8]
        low_confidence = [c for c in candidates if c.confidence < 0.6]

        report.append("## Summary")
        report.append(f"- **Total Candidates**: {len(candidates)}")
        report.append(f"- **High Confidence (≥0.8)**: {len(high_confidence)}")
        report.append(f"- **Medium Confidence (0.6-0.8)**: {len(medium_confidence)}")
        report.append(f"- **Low Confidence (<0.6)**: {len(low_confidence)}")
        report.append("")

        # Candidates by confidence
        if high_confidence:
            report.append("## High Confidence Candidates (Recommended)")
            report.append("")
            for candidate in high_confidence:
                report.append(f"### {candidate.class_name}")
                report.append(f"- **File**: `{candidate.file_path}`")
                report.append(f"- **Current**: {candidate.current_pattern}")
                report.append(f"- **Suggested**: {candidate.suggested_pattern}")
                report.append(f"- **Confidence**: {candidate.confidence:.2f}")
                report.append("- **Changes**:")
                for change in candidate.changes:
                    report.append(f"  - {change}")
                report.append("")

        if medium_confidence:
            report.append("## Medium Confidence Candidates (Review Recommended)")
            report.append("")
            for candidate in medium_confidence:
                report.append(f"### {candidate.class_name}")
                report.append(f"- **File**: `{candidate.file_path}`")
                report.append(f"- **Confidence**: {candidate.confidence:.2f}")
                report.append("")

        # Commands to apply
        report.append("## Apply Refactors")
        report.append("")
        report.append("### High Confidence (Safe to apply automatically)")
        report.append("```bash")
        report.append("# Apply high confidence refactors")
        report.append("python scripts/apply_refactor_patterns.py --apply --confidence 0.8")
        report.append("```")
        report.append("")

        return "\n".join(report)


def main():
    """Main function to run the refactor analysis."""
    import argparse

    parser = argparse.ArgumentParser(description="Automatically apply refactor patterns")
    parser.add_argument("--apply", action="store_true", help="Apply refactors (dry run by default)")
    parser.add_argument("--confidence", type=float, default=0.8, help="Minimum confidence threshold")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (default)")

    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    applier = RefactorApplier(str(project_root))

    print("🚀 Starting Automatic Refactor Analysis")
    print(f"📁 Project Root: {project_root}")
    print("")

    # Find candidates
    candidates = applier.find_candidates()

    # Filter by confidence
    filtered_candidates = [c for c in candidates if c.confidence >= args.confidence]

    print(f"📊 Found {len(candidates)} candidates, {len(filtered_candidates)} meet confidence threshold")
    print("")

    # Generate report
    report = applier.generate_report(filtered_candidates)

    # Save report
    report_path = project_root / "docs" / "refactor-report.md"
    report_path.parent.mkdir(exist_ok=True)

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"✅ Report saved to: {report_path}")
    print("")

    # Apply refactors if requested
    if args.apply:
        print("🔧 Applying refactors...")
        success_count = 0
        for candidate in filtered_candidates:
            if applier.apply_refactor(candidate, dry_run=args.dry_run):
                success_count += 1

        print(f"✅ Successfully applied {success_count} refactors")
        if not args.dry_run:
            print("⚠️  Files have been modified. Review changes before committing.")
    else:
        print("📝 Dry run completed. Use --apply to actually modify files.")

    return candidates


if __name__ == "__main__":
    main()
