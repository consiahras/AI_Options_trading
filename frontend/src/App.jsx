import { useState, useEffect, useCallback } from 'react'
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

    if (chartResult.status === 'fulfilled') {
      setChartData(chartResult.value)
    } else {
      setChartError(chartResult.reason?.message || 'Failed to load chart')
    }

    if (analysisResult.status === 'fulfilled') {
      setAnalysisData(analysisResult.value)
    } else {
      setAnalysisError(analysisResult.reason?.message || 'Failed to load analysis')
    }

    setChartLoading(false)
    setAnalysisLoading(false)
    setLastUpdated(new Date())
  }, [])

  useEffect(() => {
    api.getStocks()
      .then(data => {
        setStocks(data.stocks || [])
        const first = (data.stocks || [])[0]
        if (first) {
          setSelectedTicker(first.ticker)
          loadStockData(first.ticker)
        } else {
          loadStockData('AAPL')
        }
      })
      .catch(err => {
        console.error('Failed to load stocks:', err)
        loadStockData('AAPL')
      })
  }, [loadStockData])

  const handleSelectTicker = (ticker) => {
    setSelectedTicker(ticker)
    loadStockData(ticker)
  }

  const handleAddStock = async (ticker, listType) => {
    try {
      const data = await api.addStock(ticker, listType)
      setStocks(data.stocks || [])
    } catch (err) {
      alert(err.message || 'Failed to add stock')
    }
  }

  const handleDeleteStock = async (ticker) => {
    try {
      const data = await api.deleteStock(ticker)
      setStocks(data.stocks || [])
      if (ticker === selectedTicker) {
        const remaining = (data.stocks || [])[0]
        if (remaining) {
          handleSelectTicker(remaining.ticker)
        } else {
          setChartData(null)
          setAnalysisData(null)
        }
      }
    } catch (err) {
      alert(err.message || 'Failed to delete stock')
    }
  }

  return (
    <div className="flex flex-col h-screen bg-gray-950 text-white overflow-hidden">
      {/* Header */}
      <header className="flex-none flex items-center justify-between px-6 py-3 bg-gray-900 border-b border-gray-800 z-10">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-sm font-bold">
            AI
          </div>
          <h1 className="text-lg font-semibold tracking-tight">AI Options Trading</h1>
        </div>
        <div className="text-xs text-gray-400">
          {lastUpdated
            ? `Last updated: ${lastUpdated.toLocaleTimeString()}`
            : 'Loading…'}
        </div>
      </header>

      {/* Body */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <aside className="flex-none w-60 bg-gray-900 border-r border-gray-800 overflow-y-auto">
          <Sidebar
            stocks={stocks}
            selectedTicker={selectedTicker}
            onSelect={handleSelectTicker}
            onAdd={handleAddStock}
            onDelete={handleDeleteStock}
          />
        </aside>

        {/* Main content */}
        <main className="flex-1 flex flex-col overflow-hidden">
          {/* Chart area */}
          <div className="flex-none h-[420px] border-b border-gray-800 bg-gray-950 p-4">
            <StockChart
              ticker={selectedTicker}
              data={chartData}
              loading={chartLoading}
              error={chartError}
            />
          </div>

          {/* Analysis panel */}
          <div className="flex-1 overflow-y-auto bg-gray-900 p-4">
            <AnalysisPanel
              ticker={selectedTicker}
              data={analysisData}
              loading={analysisLoading}
              error={analysisError}
            />
          </div>
        </main>
      </div>
    </div>
  )
}
