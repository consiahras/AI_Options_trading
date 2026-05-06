import { useState } from 'react'

// Inline-editable numeric field — defined at module level so state persists between renders
function EditableValue({ value, prefix, placeholder, onSave }) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft]     = useState('')

  const open = () => {
    setDraft(value != null ? value.toString() : '')
    setEditing(true)
  }
  const commit = () => {
    const n = parseFloat(draft)
    if (!isNaN(n) && n >= 0) onSave(n)
    setEditing(false)
  }
  const onKey = (e) => {
    if (e.key === 'Enter')  commit()
    if (e.key === 'Escape') setEditing(false)
  }

  if (editing) {
    return (
      <input
        autoFocus type="number" min="0" step="any"
        value={draft}
        onChange={e => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={onKey}
        className="w-full text-[11px] px-1.5 py-0.5 border border-blue-400 rounded bg-white text-gray-900 outline-none"
      />
    )
  }

  return (
    <button
      onClick={open}
      className="w-full text-left text-[11px] px-1 py-0.5 rounded hover:bg-blue-50 hover:text-blue-600 transition-colors"
    >
      {value != null
        ? <span className="text-gray-700 font-medium">{prefix}{Number(value) % 1 === 0 && prefix === '' ? Number(value).toFixed(0) : Number(value).toFixed(2)}</span>
        : <span className="text-gray-300 italic text-[10px]">{placeholder}</span>}
    </button>
  )
}

function OwnedRow({ stock, selected, onSelect, onDelete, onUpdate }) {
  return (
    <div className={`rounded-lg border transition-colors ${
      selected ? 'bg-blue-50 border-blue-300' : 'bg-white border-gray-200 hover:border-gray-300'
    }`}>
      {/* Ticker row */}
      <div className="flex items-center justify-between px-2.5 pt-2 pb-1 cursor-pointer" onClick={() => onSelect(stock.ticker)}>
        <span className={`text-sm font-semibold ${selected ? 'text-blue-700' : 'text-gray-800'}`}>
          {stock.ticker}
        </span>
        <button
          onClick={e => { e.stopPropagation(); onDelete(stock.ticker) }}
          className="text-gray-300 hover:text-red-500 transition-colors text-xs px-0.5"
          title="Remove"
        >✕</button>
      </div>
      {/* Editable fields */}
      <div className="grid grid-cols-2 gap-x-2 px-2.5 pb-2">
        <div>
          <p className="text-[9px] font-medium text-gray-400 uppercase tracking-wide mb-0.5">Avg Price</p>
          <EditableValue
            value={stock.avg_buy_price}
            prefix="$"
            placeholder="tap to set"
            onSave={val => onUpdate(stock.ticker, { avg_buy_price: val })}
          />
        </div>
        <div>
          <p className="text-[9px] font-medium text-gray-400 uppercase tracking-wide mb-0.5">Shares</p>
          <EditableValue
            value={stock.quantity}
            prefix=""
            placeholder="tap to set"
            onSave={val => onUpdate(stock.ticker, { quantity: val })}
          />
        </div>
      </div>
    </div>
  )
}

function WatchlistRow({ stock, selected, onSelect, onDelete, onUpdate }) {
  return (
    <div className={`rounded-lg border transition-colors ${
      selected ? 'bg-blue-50 border-blue-300' : 'bg-white border-gray-200 hover:border-gray-300'
    }`}>
      {/* Ticker row */}
      <div className="flex items-center justify-between px-2.5 pt-2 pb-1 cursor-pointer" onClick={() => onSelect(stock.ticker)}>
        <span className={`text-sm font-semibold ${selected ? 'text-blue-700' : 'text-gray-800'}`}>
          {stock.ticker}
        </span>
        <button
          onClick={e => { e.stopPropagation(); onDelete(stock.ticker) }}
          className="text-gray-300 hover:text-red-500 transition-colors text-xs px-0.5"
          title="Remove"
        >✕</button>
      </div>
      {/* Target price */}
      <div className="px-2.5 pb-2">
        <p className="text-[9px] font-medium text-gray-400 uppercase tracking-wide mb-0.5">Target Price</p>
        <EditableValue
          value={stock.target_price}
          prefix="$"
          placeholder="tap to set"
          onSave={val => onUpdate(stock.ticker, { target_price: val })}
        />
      </div>
    </div>
  )
}

export default function Sidebar({ stocks, selectedTicker, onSelect, onAdd, onUpdate, onDelete }) {
  const [newTicker, setNewTicker] = useState('')
  const [listType,  setListType]  = useState('watchlist')
  const [adding,    setAdding]    = useState(false)

  const owned     = stocks.filter(s => s.list_type === 'owned')
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

  return (
    <div className="flex flex-col h-full p-3 gap-4">
      {/* My Stocks */}
      <div>
        <h2 className="text-[10px] font-semibold uppercase tracking-widest text-gray-400 mb-2 px-1">
          My Stocks
        </h2>
        <div className="flex flex-col gap-1.5">
          {owned.length === 0
            ? <p className="text-xs text-gray-400 px-2">No stocks added</p>
            : owned.map(s => (
                <OwnedRow key={s.ticker} stock={s} selected={selectedTicker === s.ticker}
                  onSelect={onSelect} onDelete={onDelete} onUpdate={onUpdate} />
              ))}
        </div>
      </div>

      {/* Watch List */}
      <div>
        <h2 className="text-[10px] font-semibold uppercase tracking-widest text-gray-400 mb-2 px-1">
          Watch List
        </h2>
        <div className="flex flex-col gap-1.5">
          {watchlist.length === 0
            ? <p className="text-xs text-gray-400 px-2">No stocks added</p>
            : watchlist.map(s => (
                <WatchlistRow key={s.ticker} stock={s} selected={selectedTicker === s.ticker}
                  onSelect={onSelect} onDelete={onDelete} onUpdate={onUpdate} />
              ))}
        </div>
      </div>

      <div className="flex-1" />

      {/* Add Stock Form */}
      <div className="border-t border-gray-200 pt-3">
        <h2 className="text-[10px] font-semibold uppercase tracking-widest text-gray-400 mb-2 px-1">
          Add Stock
        </h2>
        <form onSubmit={handleAdd} className="flex flex-col gap-2">
          <input
            type="text"
            value={newTicker}
            onChange={e => setNewTicker(e.target.value.toUpperCase())}
            placeholder="Ticker (e.g. MSFT)"
            maxLength={10}
            className="w-full px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:border-blue-400 uppercase shadow-sm"
          />
          <div className="flex gap-3 text-xs text-gray-600">
            <label className="flex items-center gap-1.5 cursor-pointer">
              <input type="radio" name="listType" value="owned"
                checked={listType === 'owned'} onChange={() => setListType('owned')}
                className="accent-blue-500" />
              Owned
            </label>
            <label className="flex items-center gap-1.5 cursor-pointer">
              <input type="radio" name="listType" value="watchlist"
                checked={listType === 'watchlist'} onChange={() => setListType('watchlist')}
                className="accent-blue-500" />
              Watchlist
            </label>
          </div>
          <button
            type="submit"
            disabled={adding || !newTicker.trim()}
            className="w-full py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-200 disabled:text-gray-400 rounded-lg text-sm font-medium text-white transition-colors"
          >
            {adding ? 'Adding…' : '+ Add'}
          </button>
        </form>
      </div>
    </div>
  )
}
