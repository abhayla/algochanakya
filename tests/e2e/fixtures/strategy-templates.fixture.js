/**
 * Strategy Templates Fixture
 *
 * Contains all 21 strategy template configurations for E2E deployment testing.
 * Each template defines expected leg configurations that should appear in
 * Strategy Builder after deployment.
 */

/**
 * All 21 strategy templates with leg configurations
 */
export const STRATEGY_TEMPLATES = {
  // ============ BULLISH STRATEGIES (3) ============

  bull_call_spread: {
    name: 'bull_call_spread',
    displayName: 'Bull Call Spread',
    category: 'bullish',
    legCount: 2,
    legs: [
      { type: 'CE', position: 'BUY', strikeOffset: 0 },
      { type: 'CE', position: 'SELL', strikeOffset: 100 }
    ],
    hasEqLeg: false
  },

  bull_put_spread: {
    name: 'bull_put_spread',
    displayName: 'Bull Put Spread',
    category: 'bullish',
    legCount: 2,
    legs: [
      { type: 'PE', position: 'SELL', strikeOffset: 0 },
      { type: 'PE', position: 'BUY', strikeOffset: -100 }
    ],
    hasEqLeg: false
  },

  synthetic_long: {
    name: 'synthetic_long',
    displayName: 'Synthetic Long',
    category: 'bullish',
    legCount: 2,
    legs: [
      { type: 'CE', position: 'BUY', strikeOffset: 0 },
      { type: 'PE', position: 'SELL', strikeOffset: 0 }
    ],
    hasEqLeg: false,
    hasUnlimited: true // Unlimited profit and loss potential
  },

  // ============ BEARISH STRATEGIES (3) ============

  bear_put_spread: {
    name: 'bear_put_spread',
    displayName: 'Bear Put Spread',
    category: 'bearish',
    legCount: 2,
    legs: [
      { type: 'PE', position: 'BUY', strikeOffset: 0 },
      { type: 'PE', position: 'SELL', strikeOffset: -100 }
    ],
    hasEqLeg: false
  },

  bear_call_spread: {
    name: 'bear_call_spread',
    displayName: 'Bear Call Spread',
    category: 'bearish',
    legCount: 2,
    legs: [
      { type: 'CE', position: 'SELL', strikeOffset: 0 },
      { type: 'CE', position: 'BUY', strikeOffset: 100 }
    ],
    hasEqLeg: false
  },

  synthetic_short: {
    name: 'synthetic_short',
    displayName: 'Synthetic Short',
    category: 'bearish',
    legCount: 2,
    legs: [
      { type: 'PE', position: 'BUY', strikeOffset: 0 },
      { type: 'CE', position: 'SELL', strikeOffset: 0 }
    ],
    hasEqLeg: false,
    hasUnlimited: true // Unlimited profit and loss potential
  },

  // ============ NEUTRAL STRATEGIES (5) ============

  iron_condor: {
    name: 'iron_condor',
    displayName: 'Iron Condor',
    category: 'neutral',
    legCount: 4,
    legs: [
      { type: 'PE', position: 'BUY', strikeOffset: -200 },
      { type: 'PE', position: 'SELL', strikeOffset: -100 },
      { type: 'CE', position: 'SELL', strikeOffset: 100 },
      { type: 'CE', position: 'BUY', strikeOffset: 200 }
    ],
    hasEqLeg: false
  },

  iron_butterfly: {
    name: 'iron_butterfly',
    displayName: 'Iron Butterfly',
    category: 'neutral',
    legCount: 4,
    legs: [
      { type: 'PE', position: 'BUY', strikeOffset: -100 },
      { type: 'PE', position: 'SELL', strikeOffset: 0 },
      { type: 'CE', position: 'SELL', strikeOffset: 0 },
      { type: 'CE', position: 'BUY', strikeOffset: 100 }
    ],
    hasEqLeg: false
  },

  short_straddle: {
    name: 'short_straddle',
    displayName: 'Short Straddle',
    category: 'neutral',
    legCount: 2,
    legs: [
      { type: 'CE', position: 'SELL', strikeOffset: 0 },
      { type: 'PE', position: 'SELL', strikeOffset: 0 }
    ],
    hasEqLeg: false
  },

  short_strangle: {
    name: 'short_strangle',
    displayName: 'Short Strangle',
    category: 'neutral',
    legCount: 2,
    legs: [
      { type: 'CE', position: 'SELL', strikeOffset: 100 },
      { type: 'PE', position: 'SELL', strikeOffset: -100 }
    ],
    hasEqLeg: false
  },

  jade_lizard: {
    name: 'jade_lizard',
    displayName: 'Jade Lizard',
    category: 'neutral',
    legCount: 3,
    legs: [
      { type: 'PE', position: 'SELL', strikeOffset: -100 },
      { type: 'CE', position: 'SELL', strikeOffset: 100 },
      { type: 'CE', position: 'BUY', strikeOffset: 200 }
    ],
    hasEqLeg: false
  },

  // ============ VOLATILE STRATEGIES (3) ============

  long_straddle: {
    name: 'long_straddle',
    displayName: 'Long Straddle',
    category: 'volatile',
    legCount: 2,
    legs: [
      { type: 'CE', position: 'BUY', strikeOffset: 0 },
      { type: 'PE', position: 'BUY', strikeOffset: 0 }
    ],
    hasEqLeg: false,
    hasUnlimited: true // Unlimited profit potential
  },

  long_strangle: {
    name: 'long_strangle',
    displayName: 'Long Strangle',
    category: 'volatile',
    legCount: 2,
    legs: [
      { type: 'CE', position: 'BUY', strikeOffset: 100 },
      { type: 'PE', position: 'BUY', strikeOffset: -100 }
    ],
    hasEqLeg: false,
    hasUnlimited: true // Unlimited profit potential
  },

  reverse_iron_condor: {
    name: 'reverse_iron_condor',
    displayName: 'Reverse Iron Condor',
    category: 'volatile',
    legCount: 4,
    legs: [
      { type: 'PE', position: 'SELL', strikeOffset: -200 },
      { type: 'PE', position: 'BUY', strikeOffset: -100 },
      { type: 'CE', position: 'BUY', strikeOffset: 100 },
      { type: 'CE', position: 'SELL', strikeOffset: 200 }
    ],
    hasEqLeg: false
  },

  // ============ INCOME STRATEGIES (3) ============

  covered_call: {
    name: 'covered_call',
    displayName: 'Covered Call',
    category: 'income',
    legCount: 1, // EQ leg is skipped in deployment, only CE leg is created
    legs: [
      { type: 'CE', position: 'SELL', strikeOffset: 100 }
    ],
    hasEqLeg: true, // Has EQ leg in template, but skipped in deployment
    note: 'EQ leg is skipped during deployment'
  },

  cash_secured_put: {
    name: 'cash_secured_put',
    displayName: 'Cash Secured Put',
    category: 'income',
    legCount: 1,
    legs: [
      { type: 'PE', position: 'SELL', strikeOffset: -100 }
    ],
    hasEqLeg: false
  },

  wheel_strategy: {
    name: 'wheel_strategy',
    displayName: 'Wheel Strategy',
    category: 'income',
    legCount: 1,
    legs: [
      { type: 'PE', position: 'SELL', strikeOffset: -100 }
    ],
    hasEqLeg: false
  },

  // ============ ADVANCED STRATEGIES (5) ============

  calendar_spread: {
    name: 'calendar_spread',
    displayName: 'Calendar Spread',
    category: 'advanced',
    legCount: 2,
    legs: [
      { type: 'CE', position: 'SELL', strikeOffset: 0, expiryOffset: 0 },
      { type: 'CE', position: 'BUY', strikeOffset: 0, expiryOffset: 1 }
    ],
    hasEqLeg: false,
    multiExpiry: true,
    note: 'Legs have different expiry dates'
  },

  diagonal_spread: {
    name: 'diagonal_spread',
    displayName: 'Diagonal Spread',
    category: 'advanced',
    legCount: 2,
    legs: [
      { type: 'CE', position: 'SELL', strikeOffset: 100, expiryOffset: 0 },
      { type: 'CE', position: 'BUY', strikeOffset: 0, expiryOffset: 1 }
    ],
    hasEqLeg: false,
    multiExpiry: true,
    note: 'Legs have different strikes and expiry dates'
  },

  butterfly_spread: {
    name: 'butterfly_spread',
    displayName: 'Butterfly Spread',
    category: 'advanced',
    legCount: 4,
    legs: [
      { type: 'CE', position: 'BUY', strikeOffset: -100 },
      { type: 'CE', position: 'SELL', strikeOffset: 0 },
      { type: 'CE', position: 'SELL', strikeOffset: 0 },
      { type: 'CE', position: 'BUY', strikeOffset: 100 }
    ],
    hasEqLeg: false,
    note: 'Two middle legs at same strike'
  },

  ratio_backspread_call: {
    name: 'ratio_backspread_call',
    displayName: 'Call Ratio Backspread',
    category: 'advanced',
    legCount: 3,
    legs: [
      { type: 'CE', position: 'SELL', strikeOffset: -100 },
      { type: 'CE', position: 'BUY', strikeOffset: 0 },
      { type: 'CE', position: 'BUY', strikeOffset: 0 }
    ],
    hasEqLeg: false,
    hasUnlimited: true, // Unlimited profit potential
    note: 'Two BUY legs at same strike'
  },

  ratio_backspread_put: {
    name: 'ratio_backspread_put',
    displayName: 'Put Ratio Backspread',
    category: 'advanced',
    legCount: 3,
    legs: [
      { type: 'PE', position: 'SELL', strikeOffset: 100 },
      { type: 'PE', position: 'BUY', strikeOffset: 0 },
      { type: 'PE', position: 'BUY', strikeOffset: 0 }
    ],
    hasEqLeg: false,
    hasUnlimited: true, // Unlimited profit potential
    note: 'Two BUY legs at same strike'
  }
};

/**
 * Get strategies by category
 * @param {string} category - Category name (bullish, bearish, neutral, volatile, income, advanced)
 * @returns {Array} Array of strategy templates in that category
 */
export function getStrategiesByCategory(category) {
  return Object.values(STRATEGY_TEMPLATES).filter(s => s.category === category);
}

/**
 * Get strategy names by category
 * @param {string} category - Category name
 * @returns {Array<string>} Array of strategy names
 */
export function getStrategyNamesByCategory(category) {
  return Object.keys(STRATEGY_TEMPLATES).filter(
    name => STRATEGY_TEMPLATES[name].category === category
  );
}

/**
 * Lot sizes for each underlying
 */
export const LOT_SIZES = {
  NIFTY: 75,
  BANKNIFTY: 15,
  FINNIFTY: 25
};

/**
 * Strike step sizes for each underlying
 */
export const STRIKE_STEPS = {
  NIFTY: 50,
  BANKNIFTY: 100,
  FINNIFTY: 50
};

/**
 * Categories in display order
 */
export const CATEGORIES = [
  'bullish',
  'bearish',
  'neutral',
  'volatile',
  'income',
  'advanced'
];

/**
 * Get all strategy names
 * @returns {Array<string>} Array of all strategy names
 */
export function getAllStrategyNames() {
  return Object.keys(STRATEGY_TEMPLATES);
}

/**
 * Get strategy count by category
 * @returns {Object} Object with category counts
 */
export function getStrategyCounts() {
  return {
    bullish: 3,
    bearish: 3,
    neutral: 5,
    volatile: 3,
    income: 3,
    advanced: 5,
    total: 22
  };
}
