const flag = (value, fallback) => {
  if (value === undefined || value === null || value === '') return fallback
  const v = String(value).toLowerCase().trim()
  return v === 'true' || v === '1' || v === 'yes' || v === 'on'
}

const env = import.meta.env

export const features = {
  modules: {
    dashboard: flag(env.VITE_ENABLE_DASHBOARD, true),
    optionchain: flag(env.VITE_ENABLE_OPTIONCHAIN, true),
    strategy: flag(env.VITE_ENABLE_STRATEGY, true),
    positions: flag(env.VITE_ENABLE_POSITIONS, true),
    settings: flag(env.VITE_ENABLE_SETTINGS, true),
    strategies: flag(env.VITE_ENABLE_STRATEGIES, true),
    autopilot: flag(env.VITE_ENABLE_AUTOPILOT, false),
    ai: flag(env.VITE_ENABLE_AI, false),
    watchlist: flag(env.VITE_ENABLE_WATCHLIST, false),
    ofo: flag(env.VITE_ENABLE_OFO, false),
  },
  brokers: {
    zerodha: flag(env.VITE_ENABLE_BROKER_ZERODHA, true),
    angelone: flag(env.VITE_ENABLE_BROKER_ANGELONE, true),
    upstox: flag(env.VITE_ENABLE_BROKER_UPSTOX, true),
    dhan: flag(env.VITE_ENABLE_BROKER_DHAN, true),
    fyers: flag(env.VITE_ENABLE_BROKER_FYERS, false),
    paytm: flag(env.VITE_ENABLE_BROKER_PAYTM, false),
  },
}

export const isModuleEnabled = (name) => features.modules[name] === true
export const isBrokerEnabled = (name) => features.brokers[name] === true
