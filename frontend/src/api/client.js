const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const api = {
  getStocks: () =>
    fetch(`${BASE_URL}/api/stocks`).then(r => {
      if (!r.ok) throw new Error(`Failed to fetch stocks: ${r.status}`)
      return r.json()
    }),

  addStock: (ticker, listType) =>
    fetch(`${BASE_URL}/api/stocks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ticker: ticker.toUpperCase(), list_type: listType }),
    }).then(r => {
      if (!r.ok) return r.json().then(e => Promise.reject(new Error(e.detail || 'Failed to add stock')))
      return r.json()
    }),

  updateStock: (ticker, fields) =>
    fetch(`${BASE_URL}/api/stocks/${ticker}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(fields),
    }).then(r => {
      if (!r.ok) throw new Error(`Failed to update ${ticker}: ${r.status}`)
      return r.json()
    }),

  deleteStock: (ticker) =>
    fetch(`${BASE_URL}/api/stocks/${ticker}`, { method: 'DELETE' }).then(r => {
      if (!r.ok) throw new Error(`Failed to delete ${ticker}: ${r.status}`)
      return r.json()
    }),

  getChart: (ticker) =>
    fetch(`${BASE_URL}/api/chart/${ticker}`).then(r => {
      if (!r.ok) throw new Error(`Failed to fetch chart for ${ticker}: ${r.status}`)
      return r.json()
    }),

  getAnalysis: (ticker) =>
    fetch(`${BASE_URL}/api/analysis/${ticker}`).then(r => {
      if (!r.ok) throw new Error(`Failed to fetch analysis for ${ticker}: ${r.status}`)
      return r.json()
    }),
}
