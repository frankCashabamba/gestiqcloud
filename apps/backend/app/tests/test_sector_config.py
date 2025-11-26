"""
Tests de Configuración Multi-Sector

Valida que sector_defaults.py retorna los campos correctos por sector y módulo.
"""

from app.services.sector_defaults import SECTOR_DEFAULTS, get_sector_categories, get_sector_defaults


class TestSectorDefaults:
    """Tests de configuración de campos por sector"""

    def test_get_panaderia_productos(self):
        """Panadería debe tener campos específicos en productos"""
        fields = get_sector_defaults("productos", "panaderia")

        assert len(fields) > 0
        field_names = [f["field"] for f in fields]

        # Campos básicos
        assert "code" in field_names
        assert "name" in field_names
        assert "precio" in field_names

        # Campos específicos panadería
        assert "peso_unitario" in field_names
        assert "caducidad_dias" in field_names
        assert "ingredientes" in field_names
        assert "receta_id" in field_names

    def test_get_retail_productos(self):
        """Retail debe tener campos específicos en productos"""
        fields = get_sector_defaults("productos", "retail")

        field_names = [f["field"] for f in fields]

        # Campos específicos retail
        assert "marca" in field_names
        assert "modelo" in field_names
        assert "talla" in field_names
        assert "color" in field_names
        assert "margen" in field_names
        assert "stock_minimo" in field_names

        # NO debe tener campos de panadería
        assert "peso_unitario" not in field_names or not fields[
            [f["field"] for f in fields].index("peso_unitario")
        ].get("visible")

    def test_get_restaurante_productos(self):
        """Restaurante debe tener campos específicos"""
        fields = get_sector_defaults("productos", "restaurante")

        field_names = [f["field"] for f in fields]

        # Campos específicos restaurante
        assert "ingredientes" in field_names
        assert "receta_id" in field_names
        assert "tiempo_preparacion" in field_names
        assert "raciones" in field_names

    def test_get_taller_productos(self):
        """Taller debe tener campos específicos"""
        fields = get_sector_defaults("productos", "taller")

        field_names = [f["field"] for f in fields]

        # Campos específicos taller
        assert "code" in field_names
        assert "tipo" not in field_names  # type, not tipo
        assert "type" in field_names
        assert "marca_vehiculo" in field_names
        assert "modelo_vehiculo" in field_names

    def test_field_structure(self):
        """Todos los campos deben tener estructura correcta"""
        fields = get_sector_defaults("productos", "panaderia")

        for field in fields:
            assert "field" in field
            assert "visible" in field
            assert "required" in field
            assert "ord" in field
            assert "label" in field
            assert isinstance(field["field"], str)
            assert isinstance(field["visible"], bool)
            assert isinstance(field["required"], bool)

    def test_fallback_to_default(self):
        """Si sector no existe, debe retornar panadería como fallback"""
        fields = get_sector_defaults("productos", "sector_inexistente")

        assert len(fields) > 0
        # Debe ser panadería (fallback)
        field_names = [f["field"] for f in fields]
        assert "peso_unitario" in field_names  # Campo típico de panadería


class TestSectorCategories:
    """Tests de categorías por defecto por sector"""

    def test_panaderia_categories(self):
        """Panadería debe tener categorías correctas"""
        cats = get_sector_categories("panaderia", "productos")

        assert "Pan" in cats
        assert "Bollería" in cats
        assert "Pastelería" in cats

    def test_retail_categories(self):
        """Retail debe tener categorías correctas"""
        cats = get_sector_categories("retail", "productos")

        assert "Ropa" in cats
        assert "Electrónica" in cats
        assert "Hogar" in cats

    def test_restaurante_categories(self):
        """Restaurante debe tener categorías correctas"""
        cats = get_sector_categories("restaurante", "productos")

        assert "Entrantes" in cats
        assert "Principales" in cats
        assert "Postres" in cats
        assert "Bebidas" in cats

    def test_taller_categories(self):
        """Taller debe tener categorías correctas"""
        cats = get_sector_categories("taller", "productos")

        assert "Motor" in cats
        assert "Frenos" in cats
        assert "Suspensión" in cats

    def test_expenses_categories_different_by_sector(self):
        """Categories of expenses should be different per sector"""
        pan_cats = get_sector_categories("panaderia", "expenses")
        retail_cats = get_sector_categories("retail", "expenses")

        assert "Materias Primas" in pan_cats
        assert "Mercancía" in retail_cats

        # Deben ser diferentes
        assert pan_cats != retail_cats


class TestAllSectorsHaveConfig:
    """Verifica que todos los sectores tienen configuración completa"""

    def test_all_sectors_exist(self):
        """Los 4 sectores deben estar definidos"""
        assert "panaderia" in SECTOR_DEFAULTS
        assert "retail" in SECTOR_DEFAULTS
        assert "restaurante" in SECTOR_DEFAULTS
        assert "taller" in SECTOR_DEFAULTS

    def test_all_sectors_have_productos(self):
        """Todos los sectores deben tener config de productos"""
        for sector in ["panaderia", "retail", "restaurante", "taller"]:
            assert "productos" in SECTOR_DEFAULTS[sector]
            assert len(SECTOR_DEFAULTS[sector]["productos"]) > 0

    def test_all_sectors_have_proveedores(self):
        """Todos los sectores deben tener config de suppliers/proveedores"""
        for sector in ["panaderia", "retail", "restaurante", "taller"]:
            # Key is "suppliers" in English now
            assert "suppliers" in SECTOR_DEFAULTS[sector]
            assert len(SECTOR_DEFAULTS[sector]["suppliers"]) > 0

    def test_all_sectors_have_required_fields(self):
        """Todos los sectores deben tener campos básicos en productos"""
        for sector in ["panaderia", "retail", "restaurante", "taller"]:
            fields = get_sector_defaults("productos", sector)
            field_names = [f["field"] for f in fields]

            # Campos universales (now in English)
            assert "code" in field_names
            assert "name" in field_names
            assert "precio" in field_names or "precio_venta" in field_names
            assert "impuesto" in field_names or "active" in field_names
