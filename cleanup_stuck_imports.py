#!/usr/bin/env python3
"""
Limpia batches de importación atascados en estado PENDING o PARSING
que fueron creados hace más de X horas sin avance.
"""

import sys
from datetime import datetime, timedelta

# Configurar DB
from apps.backend.app.config.database import DATABASE_URL
from apps.backend.app.models.core.modelsimport import ImportBatch
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

engine = create_engine(DATABASE_URL)


def cleanup_stuck_imports(hours: int = 2):
    """Limpia batches atascados creados hace más de X horas"""

    with Session(engine) as session:
        # Batches que llevan más de X horas sin cambios
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        stuck_batches = (
            session.execute(
                select(ImportBatch).where(
                    (ImportBatch.status.in_(["PENDING", "PARSING"]))
                    & (ImportBatch.created_at < cutoff_time)
                )
            )
            .scalars()
            .all()
        )

        if not stuck_batches:
            print(f"✓ No hay batches atascados (creados hace > {hours}h)")
            return

        print(f"Encontrados {len(stuck_batches)} batches atascados:")

        for batch in stuck_batches:
            print(f"  - {batch.id} ({batch.source_type}) - creado: {batch.created_at}")
            session.delete(batch)

        session.commit()
        print(f"✓ {len(stuck_batches)} batches eliminados")


if __name__ == "__main__":
    hours = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    print(f"Limpiando batches atascados con más de {hours}h sin cambios...\n")
    cleanup_stuck_imports(hours)
