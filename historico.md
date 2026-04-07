# 📦 Módulo Histórico - Documento de Prompts para AMP

## 🎯 Objetivo

Crear un módulo histórico de consulta que permita:

- Importar ficheros  utilizando el actual importador de ficheros nada harcodeado todo tablas 
- Normalizar datos
- Consultarlos desde UI
- NO afectar contabilidad real ni stock

---

## 🧠 CONTEXTO TÉCNICO

- Backend: FastAPI
- DB: PostgreSQL
- Frontend: React + Vite + TSX

---

## 🧩 PROMPT 1 — CREAR ESQUEMA Y TABLAS

Create a PostgreSQL schema called "historical" and generate tables for imports, masters, sales, purchases, stock and daily sales.

---

## ⚙️ PROMPT 2 — MODELOS SQLALCHEMY

Generate SQLAlchemy models with relationships and typing.

---

## 🚀 PROMPT 3 — IMPORT SERVICE

Create FastAPI service to upload, parse and validate files using pandas.

---

## 🔄 PROMPT 4 — NORMALIZATION SERVICE

Transform staging data into normalized tables avoiding duplicates.

---

## 🌐 PROMPT 5 — FASTAPI ROUTERS

Create endpoints under /historical for imports, sales, purchases, stock and dashboard.

---

## 📊 PROMPT 6 — DASHBOARD QUERIES

Create aggregated queries for metrics and grouping.

---

## ⚛️ PROMPT 7 — FRONTEND BASE

Create React module with pages, hooks and API layer.

---

## 🧾 PROMPT 8 — IMPORT UI

Drag & drop upload with results and history.

---

## 📈 PROMPT 9 — SALES UI

Table with filters and detail modal.

---

## 🧮 PROMPT 10 — DASHBOARD UI

Cards and charts using Recharts.

---

## 🔐 REGLAS

- No afectar contabilidad real
- No modificar stock real
- Solo lectura tras importación

---

## ✅ RESULTADO

Módulo para importar y consultar histórico sin impacto en sistema principal.
