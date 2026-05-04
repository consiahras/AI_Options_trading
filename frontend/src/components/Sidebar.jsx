import { useState } from 'react'

export default function Sidebar({ stocks, selectedTicker, onSelect, onAdd, onDelete }) {
  const [newTicker, setNewTicker] = useState('')
  const [listType, setListType] = useState('watchlist')
  const [adding, setAdding] = useState(false)

  const owned = stocks.filter(s => s.list_type === 'owned')
  const watchlist = stocks.filter(s => s.list_type === 'watchlist')

  const handleAdd = async (e) => {
    e.preventDefault()
    const t = newTicker.trim().toUpperCase()
    if (!t) return
    setAdding(true)
    await onAdd(t, listType)
    setNewTicker('')
    setAdding(false)
  }

  const StockRow = ({ stock }) => (
    <div
      className={`flex items-center justify-between px-3 py-2 rounded-lg cursor-pointer group transition-colors ${
        selectedTicker === stock.ticker
          ? 'bg-blue-600/20 border border-blue-500/40 text-blue-300'
          : 'hover:bg-gray-800 border border-transparent text-gray-200'
      }`}
      onClick={() => onSelect(stock.ticker)}
    >
      <span className="text-sm font-medium">{stock.ticker}</span>
      <button
        onClick={(e) => {
          e.stopPropagation()
          onDelete(stock.ticker)
        }}
        className="opacity-0 group-hover:opacity-100 text-gray-500 hover:text-red-400 transition-all text-xs px-1 rounded"
        title="Remove"
      >
        ✕
      </button>
    </div>
  )

  return (
    <div className="flex flex-col h-full p-3 gap-4">
      {/* My Stocks */}
      <div>
        <h2 className="text-xs font-semibold uppercase tracking-widest text-gray-500 mb-2 px-1">
          My Stocks
        </h2>
        <div className="flex flex-col gap-1">
          {owned.length === 0 ? (
            <p className="text-xs text-gray-600 px-2">No stocks added</p>
          ) : (
            owned.map(s => <StockRow key={s.ticker} stock={s} />)
          )}
        </div>
      </div>

      {/* Watch List */}
      <div>
        <h2 className="text-xs font-semibold uppercase tracking-widest text-gray-500 mb-2 px-1">
          Watch List
        </h2>
        <div className="flex flex-col gap-1">
          {watchlist.length === 0 ? (
            <p className="text-xs text-gray-600 px-2">No stocks added</p>
          ) : (
            watchlist.map(s => <StockRow key={s.ticker} stock={s} />)
          )}
        </div>
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Add Stock Form */}
      <div className="border-t border-gray-800 pt-3">
        <h2 className="text-xs font-semibold uppercase tracking-widest text-gray-500 mb-2 px-1">
          Add Stock
        </h2>
        <form onSubmit={handleAdd} className="flex flex-col gap-2">
          <input
            type="text"
            value={newTicker}
            onChange={e => setNewTicker(e.target.value.toUpperCase())}
            placeholder="Ticker (e.g. MSFT)"
            maxLength={10}
            className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 uppercase"
          />
          <div className="flex gap-3 text-xs text-gray-400">
            <label className="flex items-center gap-1.5 cursor-pointer">
              <input
                type="radio"
                name="listType"
                value="owned"
                checked={listType === 'owned'}
                onChange={() => setListType('owned')}
                className="accent-blue-500"
              />
              Owned
            </label>
            <label className="flex items-center gap-1.5 cursor-pointer">
              <input
                type="radio"
                name="listType"
                value="watchlist"
                checked={listType === 'watchlist'}
                onChange={() => setListType('watchlist')}
                className="accent-blue-500"
              />
              Watchlist
            </label>
          </div>
          <button
            type="submit"
            disabled={adding || !newTicker.trim()}
            className="w-full py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:text-gray-500 rounded-lg text-sm font-medium transition-colors"
          >
            {adding ? 'Adding…' : '+ Add'}
          </button>
        </form>
      </div>
    </div>
  )
}
