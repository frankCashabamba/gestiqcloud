"""Module: setup.py

Auto-generated module docstring."""

from setuptools import find_packages, setup

setup(
    name="gesticloud_fastapi",
    version="0.1.0",
    packages=find_packages(),
    install_requires=["fastapi", "uvicorn", "sqlalchemy", "PyJWT", "psycopg2-binary"],
)
