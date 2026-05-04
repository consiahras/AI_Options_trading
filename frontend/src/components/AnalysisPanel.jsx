function Spinner() {
  return (
    <div className="flex items-center justify-center py-12">
      <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
    </div>
  )
}

function ErrorMsg({ message }) {
  return (
    <div className="text-red-400 text-sm py-6 text-center">{message}</div>
  )
}

const REC_STYLES = {
  CONSIDER: 'bg-green-500/20 text-green-400 border border-green-500/30',
  AVOID: 'bg-red-500/20 text-red-400 border border-red-500/30',
  CAUTION: 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30',
}

const IVR_BAR_COLOR = (ivr) => {
  if (ivr < 30) return 'bg-green-500'
  if (ivr > 50) return 'bg-red-500'
  return 'bg-yellow-500'
}

export default function AnalysisPanel({ ticker, data, loading, error }) {
  if (loading) return <Spinner />
  if (error) return <ErrorMsg message={error} />
  if (!data) {
    return (
      <div className="text-gray-600 text-sm text-center py-8">
        Select a stock to view analysis
      </div>
    )
  }

  const { current_price, iv, iv_rank, call_premium, put_premium, strike, greeks, strategies } = data

  return (
    <div className="space-y-4">
      {/* Title & IV Summary */}
      <div className="flex flex-wrap items-start gap-4 justify-between">
        <div>
          <h2 className="text-base font-semibold text-white">{ticker} — Options Analysis</h2>
          <p className="text-xs text-gray-400 mt-0.5">
            Current Price: <span className="text-white font-medium">${current_price?.toFixed(2)}</span>
            {' '}&bull;{' '}
            ATM Strike: <span className="text-white font-medium">${strike?.toFixed(0)}</span>
            {' '}&bull;{' '}
            30-day expiry
          </p>
        </div>

        <div className="flex gap-4">
          {/* IV */}
          <div className="bg-gray-800 rounded-lg px-4 py-2 text-center min-w-[90px]">
            <p className="text-xs text-gray-500 mb-0.5">Implied Vol</p>
            <p className="text-lg font-bold text-blue-300">{iv?.toFixed(1)}%</p>
          </div>
          {/* IV Rank */}
          <div className="bg-gray-800 rounded-lg px-4 py-2 text-center min-w-[110px]">
            <p className="text-xs text-gray-500 mb-0.5">IV Rank</p>
            <p className={`text-lg font-bold ${iv_rank < 30 ? 'text-green-400' : iv_rank > 50 ? 'text-red-400' : 'text-yellow-400'}`}>
              {iv_rank?.toFixed(1)}
            </p>
            <div className="w-full bg-gray-700 rounded-full h-1 mt-1">
              <div
                className={`h-1 rounded-full ${IVR_BAR_COLOR(iv_rank)}`}
                style={{ width: `${Math.min(100, iv_rank)}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Premiums & Greeks */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard label="Call Premium (30d ATM)" value={`$${call_premium?.toFixed(2)}`} color="text-green-300" />
        <MetricCard label="Put Premium (30d ATM)" value={`$${put_premium?.toFixed(2)}`} color="text-red-300" />
        <MetricCard label="Delta (Call / Put)" value={`${greeks?.delta_call?.toFixed(3)} / ${greeks?.delta_put?.toFixed(3)}`} color="text-blue-300" />
        <MetricCard label="Theta (Call / Put)" value={`${greeks?.theta_call?.toFixed(4)} / ${greeks?.theta_put?.toFixed(4)}`} color="text-purple-300" />
      </div>

      {/* Strategy Table */}
      <div className="overflow-x-auto rounded-xl border border-gray-800">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-800/80 text-gray-400 text-xs uppercase tracking-wide">
              <th className="text-left px-4 py-3 font-medium">Strategy</th>
              <th className="text-right px-4 py-3 font-medium">Premium (30d ATM)</th>
              <th className="text-center px-4 py-3 font-medium">IVR Signal</th>
              <th className="text-left px-4 py-3 font-medium">S/R Context</th>
              <th className="text-center px-4 py-3 font-medium">Recommendation</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800">
            {strategies?.map((s, i) => (
              <tr key={i} className="hover:bg-gray-800/40 transition-colors">
                <td className="px-4 py-3 font-medium text-white">{s.strategy}</td>
                <td className="px-4 py-3 text-right font-mono text-gray-200">{s.premium}</td>
                <td className="px-4 py-3 text-center text-xs">
                  <span className={`inline-block px-2 py-0.5 rounded-full ${
                    s.ivr_signal.includes('✓')
                      ? 'bg-green-500/15 text-green-400'
                      : s.ivr_signal.includes('✗')
                      ? 'bg-red-500/15 text-red-400'
                      : 'bg-yellow-500/15 text-yellow-400'
                  }`}>
                    {s.ivr_signal}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-400 text-xs">{s.sr_context}</td>
                <td className="px-4 py-3 text-center">
                  <span className={`inline-block px-3 py-0.5 rounded-full text-xs font-semibold ${REC_STYLES[s.recommendation] || ''}`}>
                    {s.recommendation}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* IVR Legend */}
      <div className="text-xs text-gray-500 flex flex-wrap gap-4 pt-1">
        <span><span className="text-green-400 font-medium">IVR &lt; 30</span> — Low IV: favour buying options</span>
        <span><span className="text-yellow-400 font-medium">IVR 30–50</span> — Neutral: exercise caution</span>
        <span><span className="text-red-400 font-medium">IVR &gt; 50</span> — High IV: favour selling options</span>
      </div>
    </div>
  )
}

function MetricCard({ label, value, color }) {
  return (
    <div className="bg-gray-800 rounded-lg px-4 py-3">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className={`text-sm font-semibold font-mono ${color}`}>{value}</p>
    </div>
  )
}
