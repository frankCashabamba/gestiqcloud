import React from 'react'

export default function ImportarEmpresas() {
  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <div className="bg-white rounded-3xl shadow-sm border border-slate-200">
        <header className="px-6 py-5 border-b border-slate-200">
          <h1 className="text-2xl font-semibold text-slate-900">Import companies (Excel)</h1>
          <p className="text-slate-500 text-sm mt-1">
            Upload a .xlsx file with the indicated format to create companies in batch.
          </p>
        </header>
        <div className="px-6 py-8">
          <div className="rounded-2xl border-2 border-dashed border-slate-300 bg-slate-50 p-8 text-center">
            <p className="text-sm text-slate-600 mb-3">Drag your .xlsx file here or click to select it</p>
            <input type="file" accept=".xlsx,.xls" className="mx-auto block" disabled title="Coming soon" />
            <p className="text-xs text-slate-500 mt-4">Validation and preview will be enabled soon before importing.</p>
          </div>
          <section className="mt-8">
            <h2 className="text-sm font-semibold text-slate-700 mb-2">Expected format</h2>
            <ul className="text-sm text-slate-600 list-disc pl-5 space-y-1">
              <li>Columns: company_name, ruc, phone, address, country, province, city, zip_code, website, manager_first_name, manager_last_name, email, modules</li>
              <li>Separate multiple modules by comma (e.g.: importer,sales,billing)</li>
            </ul>
          </section>
        </div>
      </div>
    </div>
  )
}
