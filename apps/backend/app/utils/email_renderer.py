"""Module: email_renderer.py

Auto-generated module docstring."""

# app/utils/email_renderer.py

import os

from jinja2 import Environment, FileSystemLoader

# Ruta absoluta a app/templates
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "../templates")

env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))


def render_template(nombre_plantilla: str, contexto: dict) -> str:
    """
    Renderiza una plantilla HTML con el contexto dado.

    Args:
        nombre_plantilla (str): Nombre del archivo de plantilla (ej. bienvenida.html)
        contexto (dict): Diccionario con variables a inyectar en la plantilla

    Returns:
        str: HTML renderizado como string
    """
    template = env.get_template(nombre_plantilla)
    return template.render(**contexto)
