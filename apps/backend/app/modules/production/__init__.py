"""
Production module - production order and recipe management.

Complete recipe-based production planning and execution system (BOM).

DDD (Domain-Driven Design) architecture:
- domain/: entities, value objects, business rules
- application/: use cases, application services
- infrastructure/: repositories, technical implementations
- interface/: HTTP controllers, Pydantic schemas

Features:
- Production order CRUD
- Recipe management (BOM - Bill of Materials)
- Start/complete/cancel production
- Automatic stock consumption (ingredients)
- Automatic finished goods generation
- Waste/scrap tracking
- Production calculator (planning)
- Statistics and reports

Compatible with: bakery, restaurant, manufacturing, and any sector using recipes/BOM
"""

__version__ = "1.0.0"
