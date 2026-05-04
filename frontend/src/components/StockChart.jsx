import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
} from 'recharts'
import { useMemo } from 'react'

function Spinner() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
    </div>
  )
}

function ErrorMsg({ message }) {
  return (
    <div className="flex items-center justify-center h-full text-red-400 text-sm">
      {message}
    </div>
  )
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload || !payload.length) return null
  const p = payload[0]?.payload
  if (!p) return null
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-3 text-xs shadow-xl">
      <p className="text-gray-400 mb-1">{label}</p>
      {p.close != null && <p className="text-white">Close: <span className="text-blue-300">${p.close?.toFixed(2)}</span></p>}
      {p.open != null && <p className="text-gray-300">Open: ${p.open?.toFixed(2)}</p>}
      {p.high != null && <p className="text-green-400">High: ${p.high?.toFixed(2)}</p>}
      {p.low != null && <p className="text-red-400">Low: ${p.low?.toFixed(2)}</p>}
      {p.volume != null && <p className="text-gray-500">Vol: {(p.volume / 1e6).toFixed(1)}M</p>}
    </div>
  )
}

export default function StockChart({ ticker, data, loading, error }) {
  const chartData = useMemo(() => {
    if (!data) return []
    const maMap = {}
    if (data.ma_data) {
      for (const m of data.ma_data) {
        maMap[m.date] = m
      }
    }
    return data.prices.map(p => ({
      date: p.date,
      close: p.close,
      open: p.open,
      high: p.high,
      low: p.low,
      volume: p.volume,
      ma50: maMap[p.date]?.ma50 ?? null,
      ma100: maMap[p.date]?.ma100 ?? null,
      ma200: maMap[p.date]?.ma200 ?? null,
    }))
  }, [data])

  const srLevels = useMemo(() => {
    if (!data?.sr_levels) return []
    return data.sr_levels
  }, [data])

  const fibLevels = useMemo(() => {
    if (!data?.fibonacci_levels) return []
    return data.fibonacci_levels
  }, [data])

  // Show x-axis label every ~30 points
  const xAxisTicks = useMemo(() => {
    if (!chartData.length) return []
    const step = Math.max(1, Math.floor(chartData.length / 8))
    return chartData
      .filter((_, i) => i % step === 0)
      .map(d => d.date)
  }, [chartData])

  if (loading) return <Spinner />
  if (error) return <ErrorMsg message={error} />
  if (!data) return <div className="flex items-center justify-center h-full text-gray-600 text-sm">Select a stock to view chart</div>

  return (
    <div className="h-full flex flex-col">
      <h2 className="text-sm font-semibold text-gray-300 mb-2">
        {ticker} — Price Chart (1Y Daily)
      </h2>
      <div className="flex-1">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
            <defs>
              <linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
            <XAxis
              dataKey="date"
              ticks={xAxisTicks}
              tick={{ fill: '#6b7280', fontSize: 11 }}
              tickFormatter={d => {
                const parts = d.split('-')
                return `${parts[1]}/${parts[2].substring(0,2)}`
              }}
              axisLine={{ stroke: '#374151' }}
              tickLine={false}
            />
            <YAxis
              domain={['auto', 'auto']}
              tick={{ fill: '#6b7280', fontSize: 11 }}
              tickFormatter={v => `$${v}`}
              axisLine={{ stroke: '#374151' }}
              tickLine={false}
              width={60}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              wrapperStyle={{ fontSize: '11px', color: '#9ca3af' }}
              formatter={(value) => {
                const labels = { close: 'Price', ma50: 'MA 50', ma100: 'MA 100', ma200: 'MA 200' }
                return labels[value] || value
              }}
            />

            {/* S/R reference lines */}
            {srLevels.map((lvl, i) => (
              <ReferenceLine
                key={`sr-${i}`}
                y={lvl.price}
                stroke={lvl.color}
                strokeDasharray={lvl.level_type === 'pivot' ? '6 3' : '4 4'}
                strokeWidth={1}
                strokeOpacity={0.6}
              />
            ))}

            {/* Fibonacci reference lines */}
            {fibLevels.map((fib, i) => (
              <ReferenceLine
                key={`fib-${i}`}
                y={fib.price}
                stroke={fib.color}
                strokeDasharray="2 6"
                strokeWidth={1}
                strokeOpacity={0.45}
              />
            ))}

            {/* Price area */}
            <Area
              type="monotone"
              dataKey="close"
              stroke="#3b82f6"
              strokeWidth={2}
              fill="url(#priceGrad)"
              dot={false}
              activeDot={{ r: 4, fill: '#3b82f6' }}
            />

            {/* Moving averages */}
            <Line
              type="monotone"
              dataKey="ma50"
              stroke="#60a5fa"
              strokeWidth={1.5}
              dot={false}
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="ma100"
              stroke="#a855f7"
              strokeWidth={1.5}
              dot={false}
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="ma200"
              stroke="#d1d5db"
              strokeWidth={1.5}
              dot={false}
              connectNulls
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
