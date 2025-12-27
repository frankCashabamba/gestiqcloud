import React from 'react'

export default function VistaPreviaTabla({ headers, rows }: { headers: string[]; rows: Record<string, string>[] }) {
  if (headers.length === 0) {
    return (
      <div className="border rounded bg-white p-4 text-sm text-gray-500">
        No preview available.
      </div>
    )
  }

  return (
    <div className="overflow-auto border rounded">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="bg-gray-100">
            {headers.map((h) => (
              <th key={h} className="px-2 py-1 text-left">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-t">
              {headers.map((h) => (
                <td key={h} className="px-2 py-1">
                  {r[h]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
