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
  ReferenceArea,
  ResponsiveContainer,
} from 'recharts'
import { useMemo, useState, useRef, useEffect, useCallback } from 'react'

const FIB_BAND_COLORS = ['#3b82f6', '#06b6d4', '#22c55e', '#eab308', '#f97316', '#ef4444']

const PivotHighDot = ({ cx, cy, value }) => {
  if (value == null || cx == null || cy == null) return null
  const label = `$${value.toFixed(0)}`
  const w = label.length * 5.2 + 8
  return (
    <g>
      <rect x={cx - w / 2} y={cy - 20} width={w} height={13} rx={2}
        fill="#ffffff" stroke="#ef4444" strokeWidth={1} />
      <text x={cx} y={cy - 10} textAnchor="middle" fontSize={8.5} fill="#ef4444" fontWeight="600">
        {label}
      </text>
      <line x1={cx} y1={cy - 7} x2={cx} y2={cy} stroke="#ef4444" strokeWidth={1} opacity={0.5} />
    </g>
  )
}

const PivotLowDot = ({ cx, cy, value }) => {
  if (value == null || cx == null || cy == null) return null
  const label = `$${value.toFixed(0)}`
  const w = label.length * 5.2 + 8
  return (
    <g>
      <rect x={cx - w / 2} y={cy + 7} width={w} height={13} rx={2}
        fill="#ffffff" stroke="#22c55e" strokeWidth={1} />
      <text x={cx} y={cy + 17} textAnchor="middle" fontSize={8.5} fill="#22c55e" fontWeight="600">
        {label}
      </text>
      <line x1={cx} y1={cy} x2={cx} y2={cy + 7} stroke="#22c55e" strokeWidth={1} opacity={0.5} />
    </g>
  )
}

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

const PriceTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  const p = payload[0]?.payload
  if (!p) return null
  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg p-3 text-xs shadow-xl">
      <p className="text-gray-400 mb-1">{label}</p>
      {p.close != null && <p className="text-white">Close: <span className="text-blue-300">${p.close.toFixed(2)}</span></p>}
      {p.open  != null && <p className="text-gray-300">Open: ${p.open.toFixed(2)}</p>}
      {p.high  != null && <p className="text-green-400">High: ${p.high.toFixed(2)}</p>}
      {p.low   != null && <p className="text-red-400">Low: ${p.low.toFixed(2)}</p>}
      {p.volume!= null && <p className="text-gray-500">Vol: {(p.volume / 1e6).toFixed(1)}M</p>}
    </div>
  )
}

const StochTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg p-2 text-xs shadow-xl">
      <p className="text-gray-400 mb-1">{label}</p>
      {payload.map(p => (
        <p key={p.dataKey} style={{ color: p.color }}>
          {p.name}: {p.value?.toFixed(1)}
        </p>
      ))}
    </div>
  )
}

const STOCH_BADGE = {
  BUY:  'bg-green-100 text-green-700 border border-green-400',
  SELL: 'bg-red-100 text-red-700 border border-red-400',
  WAIT: 'bg-gray-100 text-gray-500 border border-gray-300',
}

// Shared axis / grid style for white background
const AXIS_TICK  = { fill: '#6b7280', fontSize: 11 }
const AXIS_LINE  = { stroke: '#d1d5db' }
const GRID_COLOR = '#e5e7eb'

export default function StockChart({ ticker, data, loading, error, stochSignal, stochReason }) {
  const [visibleStart, setVisibleStart] = useState(0)
  const [dragging, setDragging] = useState(false)
  const containerRef   = useRef(null)
  const isDragging     = useRef(false)
  const dragStartX     = useRef(0)
  const dragStartIdx   = useRef(0)
  const wheelStateRef  = useRef({ totalPoints: 0, setVisibleStart: null })

  // ── Build full data array ─────────────────────────────────────────────────
  const chartData = useMemo(() => {
    if (!data) return []
    const maMap = {}
    if (data.ma_data) for (const m of data.ma_data) maMap[m.date] = m
    const stochMap = {}
    if (data.stochastic) for (const s of data.stochastic) stochMap[s.date] = s
    const pivotHighMap = {}, pivotLowMap = {}
    if (data.pivot_markers) {
      for (const m of data.pivot_markers) {
        if (m.type === 'high') pivotHighMap[m.date] = m.price
        else                   pivotLowMap[m.date]  = m.price
      }
    }
    return data.prices.map(p => ({
      date: p.date, close: p.close, open: p.open,
      high: p.high, low: p.low, volume: p.volume,
      ma50:  maMap[p.date]?.ma50  ?? null,
      ma100: maMap[p.date]?.ma100 ?? null,
      ma200: maMap[p.date]?.ma200 ?? null,
      stoch_k: stochMap[p.date]?.k ?? null,
      stoch_d: stochMap[p.date]?.d ?? null,
      pivotHigh: pivotHighMap[p.date] ?? null,
      pivotLow:  pivotLowMap[p.date]  ?? null,
    }))
  }, [data])

  // Default to last ~3 months when ticker changes
  useEffect(() => {
    if (chartData.length > 0)
      setVisibleStart(Math.max(0, chartData.length - 63))
  }, [chartData])

  const totalPoints   = chartData.length
  const visibleData   = useMemo(() => chartData.slice(visibleStart), [chartData, visibleStart])
  const visiblePoints = visibleData.length

  // Keep ref updated every render so the wheel listener always sees current values
  wheelStateRef.current = { totalPoints, setVisibleStart }

  // ── Zoom via mouse wheel ──────────────────────────────────────────────────
  // Attach the wheel listener each time data arrives (containerRef is null
  // during loading/spinner, so we depend on `data` to re-attach once the
  // chart div is actually in the DOM).
  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const fn = (e) => {
      e.preventDefault()
      const { totalPoints: tp, setVisibleStart: setVS } = wheelStateRef.current
      const step = Math.max(3, Math.floor(tp * 0.04))
      setVS(prev =>
        e.deltaY < 0
          ? Math.min(prev + step, tp - 10)   // scroll up   = zoom in
          : Math.max(0, prev - step)          // scroll down = zoom out
      )
    }
    el.addEventListener('wheel', fn, { passive: false })
    return () => el.removeEventListener('wheel', fn)
  }, [data])   // re-attach whenever data changes (null → loaded)

  // ── Pan via mouse drag ────────────────────────────────────────────────────
  const handleMouseDown = useCallback((e) => {
    isDragging.current   = true
    dragStartX.current   = e.clientX
    dragStartIdx.current = visibleStart
    setDragging(true)
  }, [visibleStart])

  const handleMouseMove = useCallback((e) => {
    if (!isDragging.current) return
    const w      = containerRef.current?.offsetWidth || 800
    const pxPerPt = w / Math.max(visiblePoints, 1)
    const delta  = Math.round((dragStartX.current - e.clientX) / pxPerPt)
    setVisibleStart(Math.max(0, Math.min(totalPoints - 10, dragStartIdx.current + delta)))
  }, [visiblePoints, totalPoints])

  const handleMouseUp = useCallback(() => {
    isDragging.current = false
    setDragging(false)
  }, [])

  // ── X-axis ticks (based on visible window) ────────────────────────────────
  const xAxisTicks = useMemo(() => {
    if (!visibleData.length) return []
    const step = Math.max(1, Math.floor(visibleData.length / 8))
    return visibleData.filter((_, i) => i % step === 0).map(d => d.date)
  }, [visibleData])

  const tickFormatter = d => {
    const parts = d.split('-')
    return `${parts[1]}/${parts[2].substring(0, 2)}`
  }

  const fibLevels = useMemo(() => data?.fibonacci_levels || [], [data])

  // ── Render guards ─────────────────────────────────────────────────────────
  if (loading) return <Spinner />
  if (error)   return <ErrorMsg message={error} />
  if (!data)   return (
    <div className="flex items-center justify-center h-full text-gray-400 text-sm">
      Select a stock to view chart
    </div>
  )

  return (
    <div className="h-full flex flex-col gap-1">
      {/* Header row */}
      <div className="flex-none flex items-center justify-between px-1">
        <h2 className="text-sm font-semibold text-gray-700">
          {ticker} — Price Chart (1Y Daily)
        </h2>
        <span className="text-[10px] text-gray-500">
          Scroll to zoom · Drag to pan · showing {visiblePoints}/{totalPoints} days
        </span>
      </div>

      {/* ── Main price chart ─────────────────────────────────────────────── */}
      <div
        ref={containerRef}
        className="flex-1 min-h-0 rounded-lg overflow-hidden"
        style={{
          background: '#ffffff',
          cursor: dragging ? 'grabbing' : 'grab',
          userSelect: 'none',
        }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={visibleData} margin={{ top: 8, right: 95, left: 10, bottom: 5 }}>
            <defs>
              <linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#3b82f6" stopOpacity={0.18} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.01} />
              </linearGradient>
            </defs>

            <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} />
            <XAxis dataKey="date" ticks={xAxisTicks} tick={AXIS_TICK}
              tickFormatter={tickFormatter} axisLine={AXIS_LINE} tickLine={false} />
            <YAxis domain={['auto', (dataMax) => dataMax * 1.01]} tick={AXIS_TICK}
              tickFormatter={v => `$${v}`} axisLine={AXIS_LINE} tickLine={false} width={60} />
            <Tooltip content={<PriceTooltip />} />
            <Legend wrapperStyle={{ fontSize: '11px', color: '#6b7280' }}
              formatter={v => ({ close: 'Price', ma50: 'MA 50', ma100: 'MA 100', ma200: 'MA 200' }[v] || v)} />

            {/* Fibonacci coloured bands */}
            {fibLevels.length > 1 && fibLevels.slice(0, -1).map((fib, i) => (
              <ReferenceArea key={`fib-band-${i}`}
                y1={fib.price} y2={fibLevels[i + 1].price}
                fill={FIB_BAND_COLORS[i] || '#6b7280'} fillOpacity={0.1} strokeOpacity={0} />
            ))}

            {/* Fibonacci lines with right-side labels */}
            {fibLevels.map((fib, i) => {
              const col = FIB_BAND_COLORS[Math.min(i, FIB_BAND_COLORS.length - 1)]
              return (
                <ReferenceLine key={`fib-${i}`} y={fib.price} stroke={col}
                  strokeDasharray={i === 0 || i === fibLevels.length - 1 ? '0' : '4 4'}
                  strokeWidth={i === 0 || i === fibLevels.length - 1 ? 1.5 : 1}
                  strokeOpacity={0.75}
                  label={{ value: `${fib.label} $${fib.price.toFixed(2)}`, position: 'right',
                    fontSize: 9, fill: col, dx: 6 }} />
              )
            })}

            {/* Pivot high/low markers */}
            <Line dataKey="pivotHigh" stroke="none" dot={<PivotHighDot />}
              activeDot={false} isAnimationActive={false} legendType="none" />
            <Line dataKey="pivotLow" stroke="none" dot={<PivotLowDot />}
              activeDot={false} isAnimationActive={false} legendType="none" />

            {/* Price area */}
            <Area type="monotone" dataKey="close" stroke="#3b82f6" strokeWidth={2}
              fill="url(#priceGrad)" dot={false} activeDot={{ r: 4, fill: '#3b82f6' }} />

            {/* Moving averages */}
            <Line type="monotone" dataKey="ma50"  stroke="#2563eb" strokeWidth={1.5} dot={false} connectNulls />
            <Line type="monotone" dataKey="ma100" stroke="#9333ea" strokeWidth={1.5} dot={false} connectNulls />
            <Line type="monotone" dataKey="ma200" stroke="#374151" strokeWidth={1.5} dot={false} connectNulls />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* ── Stochastic Oscillator ─────────────────────────────────────────── */}
      <div className="flex-none h-[145px]">
        <div className="flex items-center justify-between px-1 mb-0.5">
          <p className="text-[10px] text-gray-500 font-medium">
            Stochastic (14, 3) &nbsp;
            <span className="text-yellow-500">%K</span>
            <span className="text-gray-400"> / </span>
            <span className="text-purple-500">%D</span>
          </p>
          {stochSignal && (
            <span className={`text-[11px] font-bold px-2 py-0.5 rounded ${STOCH_BADGE[stochSignal] || STOCH_BADGE.WAIT}`}
              title={stochReason}>
              {stochSignal}
            </span>
          )}
        </div>
        <div className="h-[120px] rounded-lg overflow-hidden" style={{ background: '#ffffff' }}>
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={visibleData} margin={{ top: 2, right: 55, left: 10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} />
              <XAxis dataKey="date" ticks={xAxisTicks} tick={{ fill: '#9ca3af', fontSize: 9 }}
                tickFormatter={tickFormatter} axisLine={AXIS_LINE} tickLine={false} />
              <YAxis domain={[0, 100]} ticks={[0, 20, 50, 80, 100]}
                tick={{ fill: '#9ca3af', fontSize: 9 }} axisLine={AXIS_LINE} tickLine={false} width={28} />
              <Tooltip content={<StochTooltip />} />

              <ReferenceArea y1={80} y2={100} fill="#fee2e2" fillOpacity={0.4} strokeOpacity={0} />
              <ReferenceArea y1={0}  y2={20}  fill="#dcfce7" fillOpacity={0.4} strokeOpacity={0} />

              <ReferenceLine y={80} stroke="#ef4444" strokeDasharray="4 3" strokeOpacity={0.6}
                label={{ value: '80', position: 'right', fontSize: 8, fill: '#ef4444', dx: 4 }} />
              <ReferenceLine y={20} stroke="#22c55e" strokeDasharray="4 3" strokeOpacity={0.6}
                label={{ value: '20', position: 'right', fontSize: 8, fill: '#22c55e', dx: 4 }} />

              <Line type="monotone" dataKey="stoch_k" stroke="#d97706" strokeWidth={1.5}
                dot={false} name="%K" connectNulls />
              <Line type="monotone" dataKey="stoch_d" stroke="#9333ea" strokeWidth={1.5}
                dot={false} name="%D" connectNulls />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}
