#!/usr/bin/env python3
"""Update remaining Spanish class names and error messages"""

from pathlib import Path

# Define replacements for each module
replacements = {
    "idiomas": [
        ("class ListarIdiomas", "class ListLanguages"),
        ("class ObtenerIdioma", "class GetLanguage"),
        ("class CrearIdioma", "class CreateLanguage"),
        ("class ActualizarIdioma", "class UpdateLanguage"),
        ("class EliminarIdioma", "class DeleteLanguage"),
        ('raise ValueError("idioma_no_encontrado")', 'raise ValueError("language_not_found")'),
        ("idioma = ", "language = "),
        ("if not idioma:", "if not language:"),
        ("return idioma", "return language"),
    ],
    "locales": [
        ("class ListarLocales", "class ListLocales"),
        ("class ObtenerLocale", "class GetLocale"),
        ("class CrearLocale", "class CreateLocale"),
        ("class ActualizarLocale", "class UpdateLocale"),
        ("class EliminarLocale", "class DeleteLocale"),
        ('raise ValueError("locale_no_encontrado")', 'raise ValueError("locale_not_found")'),
        ("locale = ", "loc = "),
        ("if not locale:", "if not loc:"),
        ("return locale", "return loc"),
    ],
    "dias_semana": [
        ("class ListarDiasSemana", "class ListWeekDays"),
        ("class ObtenerDiaSemana", "class GetWeekDay"),
        ("class CrearDiaSemana", "class CreateWeekDay"),
        ("class ActualizarDiaSemana", "class UpdateWeekDay"),
        ("class EliminarDiaSemana", "class DeleteWeekDay"),
        ('raise ValueError("dia_no_encontrado")', 'raise ValueError("day_not_found")'),
        ("dia = ", "day = "),
        ("if not dia:", "if not day:"),
        ("return dia", "return day"),
    ],
    "timezones": [
        ("class ListarTimezones", "class ListTimezones"),
        ("class ObtenerTimezone", "class GetTimezone"),
        ("class CrearTimezone", "class CreateTimezone"),
        ("class ActualizarTimezone", "class UpdateTimezone"),
        ("class EliminarTimezone", "class DeleteTimezone"),
        ('raise ValueError("timezone_no_encontrado")', 'raise ValueError("timezone_not_found")'),
        ("tz = ", "timezone = "),
        ("if not tz:", "if not timezone:"),
        ("return tz", "return timezone"),
    ],
    "tipos_empresa": [
        ("class ListarTiposEmpresa", "class ListCompanyTypes"),
        ("class ObtenerTipoEmpresa", "class GetCompanyType"),
        ("class CrearTipoEmpresa", "class CreateCompanyType"),
        ("class ActualizarTipoEmpresa", "class UpdateCompanyType"),
        ("class EliminarTipoEmpresa", "class DeleteCompanyType"),
        (
            'raise ValueError("tipo_empresa_no_encontrado")',
            'raise ValueError("company_type_not_found")',
        ),
        ("tipo = ", "company_type = "),
        ("if not tipo:", "if not company_type:"),
        ("return tipo", "return company_type"),
    ],
    "tipos_negocio": [
        ("class ListarTiposNegocio", "class ListBusinessTypes"),
        ("class ObtenerTipoNegocio", "class GetBusinessType"),
        ("class CrearTipoNegocio", "class CreateBusinessType"),
        ("class ActualizarTipoNegocio", "class UpdateBusinessType"),
        ("class EliminarTipoNegocio", "class DeleteBusinessType"),
        (
            'raise ValueError("tipo_negocio_no_encontrado")',
            'raise ValueError("business_type_not_found")',
        ),
        ("tipo = ", "business_type = "),
        ("if not tipo:", "if not business_type:"),
        ("return tipo", "return business_type"),
    ],
    "sectores_plantilla": [
        ("class ListarSectoresPlantilla", "class ListTemplateSectors"),
        ("class ObtenerSectorPlantilla", "class GetTemplateSector"),
        ("class CrearSectorPlantilla", "class CreateTemplateSector"),
        ("class ActualizarSectorPlantilla", "class UpdateTemplateSector"),
        ("class EliminarSectorPlantilla", "class DeleteTemplateSector"),
        ('raise ValueError("sector_no_encontrado")', 'raise ValueError("sector_not_found")'),
        ("sector = ", "sector = "),
        ("if not sector:", "if not sector:"),
        ("return sector", "return sector"),
    ],
    "horarios_atencion": [
        ("class ListarHorarios", "class ListAttentionSchedules"),
        ("class ObtenerHorario", "class GetAttentionSchedule"),
        ("class CrearHorario", "class CreateAttentionSchedule"),
        ("class ActualizarHorario", "class UpdateAttentionSchedule"),
        ("class EliminarHorario", "class DeleteAttentionSchedule"),
        ('raise ValueError("horario_no_encontrado")', 'raise ValueError("schedule_not_found")'),
        ("horario = ", "schedule = "),
        ("if not horario:", "if not schedule:"),
        ("return horario", "return schedule"),
    ],
}

base_path = Path("app/modules/admin_config/application")

for module_name, repl_list in replacements.items():
    use_cases_file = base_path / module_name / "use_cases.py"

    if not use_cases_file.exists():
        print(f"⚠️  {use_cases_file} not found")
        continue

    with open(use_cases_file, encoding="utf-8") as f:
        content = f.read()

    original_content = content

    for old, new in repl_list:
        content = content.replace(old, new)

    if content != original_content:
        with open(use_cases_file, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ {module_name}: Updated")
    else:
        print(f"⚠️  {module_name}: No changes")

print("\n✅ Done!")
