function Tip({ text, children }) {
  return (
    <span className="relative group cursor-help inline-block">
      {children}
      <span className="pointer-events-none absolute z-50 opacity-0 group-hover:opacity-100 transition-opacity duration-150 bottom-full left-1/2 -translate-x-1/2 mb-2 w-56 bg-gray-900 text-white text-xs rounded-lg px-3 py-2 shadow-xl text-center leading-relaxed">
        {text}
        <span className="absolute top-full left-1/2 -translate-x-1/2 border-[5px] border-transparent border-t-gray-900" />
      </span>
    </span>
  )
}

function Spinner() {
  return (
    <div className="flex items-center justify-center py-12">
      <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
    </div>
  )
}

function ErrorMsg({ message }) {
  return <div className="text-red-500 text-sm py-6 text-center">{message}</div>
}

const REC_STYLES = {
  CONSIDER: 'bg-green-100 text-green-700 border border-green-300',
  AVOID:    'bg-red-100 text-red-700 border border-red-300',
  CAUTION:  'bg-yellow-100 text-yellow-700 border border-yellow-300',
}

const IVR_BAR_COLOR = (ivr) => {
  if (ivr < 30) return 'bg-green-500'
  if (ivr > 50) return 'bg-red-500'
  return 'bg-yellow-500'
}

function MarketSignalCard({ signals, ticker }) {
  if (!signals || !signals.crossType) return null

  const isBull    = signals.crossType === 'golden'
  const crossLabel = isBull
    ? (signals.crossRecent ? 'Recent Golden Cross' : 'Golden Cross Active')
    : (signals.crossRecent ? 'Recent Death Cross'  : 'Death Cross Active')

  const trendWord  = isBull ? 'BULL' : 'BEAR'
  const trendColor = isBull ? 'text-green-600' : 'text-red-600'
  const trendBg    = isBull ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'
  const crossColor = isBull ? 'text-green-700' : 'text-red-700'

  const stochSentence = signals.stochK != null
    ? `Stochastic at ${signals.stochK.toFixed(1)} — ${signals.stochReason.toLowerCase()}.`
    : 'Stochastic data unavailable.'

  const combinedBias = (() => {
    if (isBull  && signals.stochSignal === 'BUY')  return { word: 'STRONG BUY',       color: 'text-green-700 bg-green-100 border-green-300' }
    if (isBull  && signals.stochSignal === 'SELL') return { word: 'CAUTION',           color: 'text-yellow-700 bg-yellow-100 border-yellow-300' }
    if (!isBull && signals.stochSignal === 'SELL') return { word: 'STRONG SELL',       color: 'text-red-700 bg-red-100 border-red-300' }
    if (!isBull && signals.stochSignal === 'BUY')  return { word: 'WATCH FOR BOUNCE',  color: 'text-yellow-700 bg-yellow-100 border-yellow-300' }
    return isBull
      ? { word: 'WAIT (UPTREND)',   color: 'text-green-700 bg-green-100 border-green-300' }
      : { word: 'WAIT (DOWNTREND)', color: 'text-red-700 bg-red-100 border-red-300' }
  })()

  return (
    <div className={`rounded-xl border p-4 ${trendBg}`}>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-semibold uppercase tracking-widest text-gray-500">
          Market Trend — {ticker}
        </h3>
        <span className={`text-xs font-bold px-2 py-0.5 rounded border ${combinedBias.color}`}>
          {combinedBias.word}
        </span>
      </div>
      <p className="text-sm text-gray-700 leading-relaxed">
        {ticker} is currently in a{' '}
        <span className={`font-bold ${trendColor}`}>{trendWord} market</span>.{' '}
        <span className={`font-medium ${crossColor}`}>{crossLabel}</span>
        {signals.ma50 && signals.ma200 && (
          <> — MA50 (
            <span className="text-blue-600 font-mono">${signals.ma50.toFixed(2)}</span>
            ) is {isBull ? 'above' : 'below'} MA200 (
            <span className="text-gray-600 font-mono">${signals.ma200.toFixed(2)}</span>
            ), indicating a{isBull ? 'n uptrend' : ' downtrend'}.
          </>
        )}{' '}
        {stochSentence}{' '}
        Overall bias: <span className={`font-bold ${trendColor}`}>{combinedBias.word}</span>.
      </p>
    </div>
  )
}

export default function AnalysisPanel({ ticker, data, loading, error, marketSignals }) {
  if (loading) return <Spinner />
  if (error)   return <ErrorMsg message={error} />
  if (!data) {
    return (
      <div className="space-y-4">
        <MarketSignalCard signals={marketSignals} ticker={ticker} />
        <div className="text-gray-400 text-sm text-center py-8">Select a stock to view analysis</div>
      </div>
    )
  }

  const { current_price, iv, iv_rank, call_premium, put_premium, strike, greeks, strategies } = data

  return (
    <div className="space-y-4 text-gray-900">
      <MarketSignalCard signals={marketSignals} ticker={ticker} />

      {/* Title & IV Summary */}
      <div className="flex flex-wrap items-start gap-4 justify-between">
        <div>
          <h2 className="text-base font-semibold text-gray-900">{ticker} — Options Analysis</h2>
          <p className="text-xs text-gray-500 mt-0.5">
            Current Price: <span className="text-gray-900 font-medium">${current_price?.toFixed(2)}</span>
            {' '}&bull;{' '}
            ATM Strike: <span className="text-gray-900 font-medium">${strike?.toFixed(0)}</span>
            {' '}&bull;{' '}
            30-day expiry
          </p>
        </div>
        <div className="flex gap-4">
          <div className="bg-white border border-gray-200 rounded-lg px-4 py-2 text-center min-w-[90px] shadow-sm">
            <p className="text-xs text-gray-500 mb-0.5">Implied Vol</p>
            <p className="text-lg font-bold text-blue-600">{iv?.toFixed(1)}%</p>
          </div>
          <div className="bg-white border border-gray-200 rounded-lg px-4 py-2 text-center min-w-[110px] shadow-sm">
            <p className="text-xs text-gray-500 mb-0.5">IV Rank</p>
            <p className={`text-lg font-bold ${iv_rank < 30 ? 'text-green-600' : iv_rank > 50 ? 'text-red-600' : 'text-yellow-600'}`}>
              {iv_rank?.toFixed(1)}
            </p>
            <div className="w-full bg-gray-200 rounded-full h-1 mt-1">
              <div className={`h-1 rounded-full ${IVR_BAR_COLOR(iv_rank)}`}
                style={{ width: `${Math.min(100, iv_rank)}%` }} />
            </div>
          </div>
        </div>
      </div>

      {/* Premiums & Greeks */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard label="Call Premium (30d ATM)" value={`$${call_premium?.toFixed(2)}`}  color="text-green-600" />
        <MetricCard label="Put Premium (30d ATM)"  value={`$${put_premium?.toFixed(2)}`}   color="text-red-600" />
        <MetricCard
          label="Delta (Call / Put)" color="text-blue-600"
          value={`${greeks?.delta_call?.toFixed(3)} / ${greeks?.delta_put?.toFixed(3)}`}
          tip="Rate of change of option price per $1 move in the stock. Call delta is positive (profits as stock rises); put delta is negative (profits as stock falls). ATM options are near ±0.50."
        />
        <MetricCard
          label="Theta (Call / Put)" color="text-purple-600"
          value={`${greeks?.theta_call?.toFixed(4)} / ${greeks?.theta_put?.toFixed(4)}`}
          tip="Daily time decay — how much value the option loses each day as expiry approaches. Negative for buyers (cost), positive for sellers (income). Accelerates near expiry."
        />
      </div>

      {/* Strategy Table */}
      <div className="overflow-x-auto rounded-xl border border-gray-200 shadow-sm bg-white">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-gray-500 text-xs uppercase tracking-wide border-b border-gray-200">
              <th className="text-left px-4 py-3 font-medium">
                <Tip text="The options strategy — direction and premium type determine when each is appropriate.">Strategy</Tip>
              </th>
              <th className="text-right px-4 py-3 font-medium">
                <Tip text="Theoretical premium from Black-Scholes at the at-the-money strike with 30 days to expiry. Buyers pay this; sellers collect it.">Premium (30d ATM)</Tip>
              </th>
              <th className="text-center px-4 py-3 font-medium">
                <Tip text="IV Rank (0–100): where current implied volatility sits in its 52-week range. Low (&lt;30) = cheap premiums, favour buying. High (&gt;50) = expensive premiums, favour selling.">IVR Signal</Tip>
              </th>
              <th className="text-left px-4 py-3 font-medium">
                <Tip text="How the current price relates to support/resistance levels and the overall market trend direction.">S/R Context</Tip>
              </th>
              <th className="text-center px-4 py-3 font-medium">
                <Tip text="Combined signal from market direction (MA cross + Stochastic) and IV Rank. CONSIDER = good setup, CAUTION = mixed signals, AVOID = unfavourable conditions.">Recommendation</Tip>
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {strategies?.map((s, i) => (
              <tr key={i} className="hover:bg-gray-50 transition-colors">
                <td className="px-4 py-3 font-medium text-gray-900">{s.strategy}</td>
                <td className="px-4 py-3 text-right font-mono text-gray-700">{s.premium}</td>
                <td className="px-4 py-3 text-center text-xs">
                  <span className={`inline-block px-2 py-0.5 rounded-full ${
                    s.ivr_signal.includes('✓') ? 'bg-green-100 text-green-700'
                    : s.ivr_signal.includes('✗') ? 'bg-red-100 text-red-700'
                    : 'bg-yellow-100 text-yellow-700'
                  }`}>
                    {s.ivr_signal}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-500 text-xs">{s.sr_context}</td>
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
        <span><span className="text-green-600 font-medium">IVR &lt; 30</span> — Low IV: favour buying options</span>
        <span><span className="text-yellow-600 font-medium">IVR 30–50</span> — Neutral: exercise caution</span>
        <span><span className="text-red-600 font-medium">IVR &gt; 50</span> — High IV: favour selling options</span>
      </div>
    </div>
  )
}

function MetricCard({ label, value, color, tip }) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg px-4 py-3 shadow-sm">
      <p className="text-xs text-gray-500 mb-1">
        {tip ? <Tip text={tip}>{label}</Tip> : label}
      </p>
      <p className={`text-sm font-semibold font-mono ${color}`}>{value}</p>
    </div>
  )
}
