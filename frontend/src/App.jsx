import { useState, useEffect, useCallback, useMemo } from 'react'
import Sidebar from './components/Sidebar'
import StockChart from './components/StockChart'
import AnalysisPanel from './components/AnalysisPanel'
import { api } from './api/client'

export default function App() {
  const [stocks, setStocks] = useState([])
  const [selectedTicker, setSelectedTicker] = useState('AAPL')
  const [chartData, setChartData] = useState(null)
  const [analysisData, setAnalysisData] = useState(null)
  const [chartLoading, setChartLoading] = useState(false)
  const [analysisLoading, setAnalysisLoading] = useState(false)
  const [chartError, setChartError] = useState(null)
  const [analysisError, setAnalysisError] = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)

  const loadStockData = useCallback(async (ticker) => {
    setChartLoading(true)
    setAnalysisLoading(true)
    setChartError(null)
    setAnalysisError(null)
    setChartData(null)
    setAnalysisData(null)

    const [chartResult, analysisResult] = await Promise.allSettled([
      api.getChart(ticker),
      api.getAnalysis(ticker),
    ])

    if (chartResult.status === 'fulfilled') setChartData(chartResult.value)
    else setChartError(chartResult.reason?.message || 'Failed to load chart')

    if (analysisResult.status === 'fulfilled') setAnalysisData(analysisResult.value)
    else setAnalysisError(analysisResult.reason?.message || 'Failed to load analysis')

    setChartLoading(false)
    setAnalysisLoading(false)
    setLastUpdated(new Date())
  }, [])

  useEffect(() => {
    api.getStocks()
      .then(data => {
        setStocks(data.stocks || [])
        const first = (data.stocks || [])[0]
        if (first) { setSelectedTicker(first.ticker); loadStockData(first.ticker) }
        else loadStockData('AAPL')
      })
      .catch(() => loadStockData('AAPL'))
  }, [loadStockData])

  const handleSelectTicker = (ticker) => { setSelectedTicker(ticker); loadStockData(ticker) }

  const handleAddStock = async (ticker, listType) => {
    try { const data = await api.addStock(ticker, listType); setStocks(data.stocks || []) }
    catch (err) { alert(err.message || 'Failed to add stock') }
  }

  const handleDeleteStock = async (ticker) => {
    try {
      const data = await api.deleteStock(ticker)
      setStocks(data.stocks || [])
      if (ticker === selectedTicker) {
        const remaining = (data.stocks || [])[0]
        if (remaining) handleSelectTicker(remaining.ticker)
        else { setChartData(null); setAnalysisData(null) }
      }
    } catch (err) { alert(err.message || 'Failed to delete stock') }
  }

  const marketSignals = useMemo(() => {
    if (!chartData) return null
    const maData = (chartData.ma_data || []).filter(m => m.ma50 != null && m.ma200 != null)
    const lastMA = maData[maData.length - 1]
    const recent10 = maData.slice(-10)
    let crossType = null, crossRecent = false
    if (lastMA) {
      crossType = lastMA.ma50 > lastMA.ma200 ? 'golden' : 'death'
      for (let i = 1; i < recent10.length; i++) {
        const p = recent10[i - 1], c = recent10[i]
        if ((p.ma50 < p.ma200 && c.ma50 > c.ma200) || (p.ma50 > p.ma200 && c.ma50 < c.ma200)) { crossRecent = true; break }
      }
    }
    const stochData = (chartData.stochastic || []).filter(s => s.k != null && s.d != null)
    const lastS = stochData[stochData.length - 1]
    const prevS = stochData[stochData.length - 2]
    let stochSignal = 'WAIT', stochReason = 'Neutral zone'
    const stochK = lastS?.k ?? null
    if (lastS) {
      if (lastS.k > 80)       { stochSignal = 'SELL'; stochReason = 'Overbought' }
      else if (lastS.k < 20)  { stochSignal = 'BUY';  stochReason = 'Oversold' }
      else if (prevS && prevS.k < prevS.d && lastS.k > lastS.d) { stochSignal = 'BUY';  stochReason = '%K crossed above %D' }
      else if (prevS && prevS.k > prevS.d && lastS.k < lastS.d) { stochSignal = 'SELL'; stochReason = '%K crossed below %D' }
    }
    return { crossType, crossRecent, ma50: lastMA?.ma50, ma200: lastMA?.ma200, stochSignal, stochReason, stochK }
  }, [chartData])

  return (
    <div className="flex flex-col h-screen bg-slate-100 text-gray-900 overflow-hidden">
      {/* Header */}
      <header className="flex-none flex items-center justify-between px-6 py-3 bg-white border-b border-gray-200 z-10 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-sm font-bold text-white">
            AI
          </div>
          <h1 className="text-lg font-semibold tracking-tight text-gray-900">AI Options Trading</h1>
        </div>
        <div className="text-xs text-gray-500">
          {lastUpdated ? `Last updated: ${lastUpdated.toLocaleTimeString()}` : 'Loading…'}
        </div>
      </header>

      {/* Body */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <aside className="flex-none w-32 bg-slate-50 border-r border-gray-200 overflow-y-auto">
          <Sidebar
            stocks={stocks}
            selectedTicker={selectedTicker}
            onSelect={handleSelectTicker}
            onAdd={handleAddStock}
            onDelete={handleDeleteStock}
          />
        </aside>

        {/* Main content */}
        <main className="flex-1 flex flex-row overflow-hidden bg-slate-100">
          {/* Chart column — 70% of viewport width */}
          <div className="flex-none w-[70vw] h-full border-r border-gray-200 bg-white p-3">
            <StockChart
              ticker={selectedTicker}
              data={chartData}
              loading={chartLoading}
              error={chartError}
              stochSignal={marketSignals?.stochSignal}
              stochReason={marketSignals?.stochReason}
            />
          </div>

          {/* Analysis panel */}
          <div className="flex-1 overflow-y-auto bg-slate-100 p-4">
            <AnalysisPanel
              ticker={selectedTicker}
              data={analysisData}
              loading={analysisLoading}
              error={analysisError}
              marketSignals={marketSignals}
            />
          </div>
        </main>
      </div>
    </div>
  )
}
