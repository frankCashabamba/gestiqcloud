"""
Módulo de Producción - Gestión de Órdenes de Producción y Recetas

Sistema completo de planificación y ejecución de producción basado en recetas (BOM).

Arquitectura DDD (Domain-Driven Design):
- domain/: Entidades, Value Objects, Reglas de negocio
- application/: Casos de uso, Servicios de aplicación  
- infrastructure/: Repositorios, Implementaciones técnicas
- interface/: Controladores HTTP, Schemas Pydantic

Funcionalidades:
- CRUD de órdenes de producción
- Gestión de recetas (BOM - Bill of Materials)
- Iniciar/Completar/Cancelar producción
- Consumo automático de stock (ingredientes)
- Generación automática de productos terminados
- Registro de mermas y desperdicios
- Calculadora de producción (planificación)
- Estadísticas y reportes

Compatible con: Panadería, Restaurante, Manufactura y cualquier sector con recetas/BOM
"""

__version__ = "1.0.0"
