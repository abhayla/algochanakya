/**
 * Strategy Library Test Fixtures
 *
 * Mock data and helper functions for strategy library E2E tests.
 */

/**
 * Mock strategy templates for testing
 */
export const mockTemplates = [
  {
    id: 'template-001',
    name: 'iron_condor',
    display_name: 'Iron Condor',
    category: 'neutral',
    description: 'Sell an OTM put spread and an OTM call spread simultaneously. Profits when the underlying stays within a defined range.',
    legs_config: [
      { type: 'PE', position: 'BUY', strike_offset: -400 },
      { type: 'PE', position: 'SELL', strike_offset: -200 },
      { type: 'CE', position: 'SELL', strike_offset: 200 },
      { type: 'CE', position: 'BUY', strike_offset: 400 }
    ],
    max_profit: 'Limited',
    max_loss: 'Limited',
    breakeven: 'Two breakevens',
    market_outlook: 'neutral',
    volatility_preference: 'high_iv',
    ideal_iv_rank: '>50%',
    risk_level: 'medium',
    capital_requirement: 'medium',
    theta_positive: true,
    vega_positive: false,
    delta_neutral: true,
    gamma_risk: 'medium',
    win_probability: '~68%',
    profit_target: '50% of max profit',
    when_to_use: 'Market is range-bound',
    pros: ['High probability', 'Defined risk', 'Benefits from time decay'],
    cons: ['Limited profit', 'Requires active management'],
    common_mistakes: ['Setting wings too narrow', 'Not adjusting when tested'],
    exit_rules: ['Exit at 50% profit', 'Exit if short strike breached'],
    popularity_score: 95,
    difficulty_level: 'intermediate',
    tags: ['neutral', 'income', 'defined-risk']
  },
  {
    id: 'template-002',
    name: 'bull_call_spread',
    display_name: 'Bull Call Spread',
    category: 'bullish',
    description: 'Buy a call at lower strike and sell a call at higher strike. Debit spread that profits from moderate upward movement.',
    legs_config: [
      { type: 'CE', position: 'BUY', strike_offset: 0 },
      { type: 'CE', position: 'SELL', strike_offset: 200 }
    ],
    max_profit: 'Limited',
    max_loss: 'Limited',
    market_outlook: 'bullish',
    volatility_preference: 'low_iv',
    risk_level: 'low',
    capital_requirement: 'low',
    theta_positive: false,
    vega_positive: true,
    delta_neutral: false,
    win_probability: '~45%',
    popularity_score: 85,
    difficulty_level: 'beginner',
    tags: ['bullish', 'debit', 'defined-risk']
  },
  {
    id: 'template-003',
    name: 'bull_put_spread',
    display_name: 'Bull Put Spread',
    category: 'bullish',
    description: 'Sell a put at higher strike and buy a put at lower strike. Credit spread for bullish bias.',
    legs_config: [
      { type: 'PE', position: 'SELL', strike_offset: 0 },
      { type: 'PE', position: 'BUY', strike_offset: -200 }
    ],
    max_profit: 'Limited',
    max_loss: 'Limited',
    market_outlook: 'bullish',
    volatility_preference: 'high_iv',
    risk_level: 'low',
    capital_requirement: 'medium',
    theta_positive: true,
    vega_positive: false,
    delta_neutral: false,
    win_probability: '~65%',
    popularity_score: 92,
    difficulty_level: 'beginner',
    tags: ['bullish', 'credit', 'income']
  },
  {
    id: 'template-004',
    name: 'bear_call_spread',
    display_name: 'Bear Call Spread',
    category: 'bearish',
    description: 'Sell a call at lower strike, buy a call at higher strike. Credit spread for bearish or neutral outlook.',
    legs_config: [
      { type: 'CE', position: 'SELL', strike_offset: 0 },
      { type: 'CE', position: 'BUY', strike_offset: 200 }
    ],
    max_profit: 'Limited',
    max_loss: 'Limited',
    market_outlook: 'bearish',
    volatility_preference: 'high_iv',
    risk_level: 'low',
    capital_requirement: 'medium',
    theta_positive: true,
    vega_positive: false,
    delta_neutral: false,
    win_probability: '~65%',
    popularity_score: 88,
    difficulty_level: 'beginner',
    tags: ['bearish', 'credit']
  },
  {
    id: 'template-005',
    name: 'long_straddle',
    display_name: 'Long Straddle',
    category: 'volatile',
    description: 'Buy ATM call and ATM put. Profits from a big move in either direction.',
    legs_config: [
      { type: 'CE', position: 'BUY', strike_offset: 0 },
      { type: 'PE', position: 'BUY', strike_offset: 0 }
    ],
    max_profit: 'Unlimited',
    max_loss: 'Limited',
    market_outlook: 'volatile',
    volatility_preference: 'low_iv',
    risk_level: 'medium',
    capital_requirement: 'medium',
    theta_positive: false,
    vega_positive: true,
    delta_neutral: true,
    win_probability: '~35%',
    popularity_score: 75,
    difficulty_level: 'intermediate',
    tags: ['volatile', 'debit', 'vega-positive']
  },
  {
    id: 'template-006',
    name: 'short_straddle',
    display_name: 'Short Straddle',
    category: 'neutral',
    description: 'Sell ATM call and ATM put. Maximum premium collection with unlimited risk.',
    legs_config: [
      { type: 'CE', position: 'SELL', strike_offset: 0 },
      { type: 'PE', position: 'SELL', strike_offset: 0 }
    ],
    max_profit: 'Limited',
    max_loss: 'Unlimited',
    market_outlook: 'neutral',
    volatility_preference: 'high_iv',
    risk_level: 'high',
    capital_requirement: 'high',
    theta_positive: true,
    vega_positive: false,
    delta_neutral: true,
    win_probability: '~45%',
    popularity_score: 70,
    difficulty_level: 'advanced',
    tags: ['neutral', 'income', 'high-risk']
  },
  {
    id: 'template-007',
    name: 'short_strangle',
    display_name: 'Short Strangle',
    category: 'neutral',
    description: 'Sell OTM call and OTM put. Wider profit zone than straddle.',
    legs_config: [
      { type: 'CE', position: 'SELL', strike_offset: 200 },
      { type: 'PE', position: 'SELL', strike_offset: -200 }
    ],
    max_profit: 'Limited',
    max_loss: 'Unlimited',
    market_outlook: 'neutral',
    volatility_preference: 'high_iv',
    risk_level: 'high',
    capital_requirement: 'high',
    theta_positive: true,
    vega_positive: false,
    delta_neutral: true,
    win_probability: '~68%',
    popularity_score: 90,
    difficulty_level: 'advanced',
    tags: ['neutral', 'income', 'high-risk']
  }
];

/**
 * Mock wizard response for testing
 */
export const mockWizardResponse = {
  recommendations: [
    {
      template: mockTemplates[0], // Iron Condor
      score: 85,
      match_reasons: [
        '✓ Perfect match for neutral market',
        '✓ Ideal for high IV environments',
        '✓ Matches your medium risk tolerance'
      ],
      warnings: null
    },
    {
      template: mockTemplates[6], // Short Strangle
      score: 72,
      match_reasons: [
        '✓ Works in neutral markets',
        '✓ Time decay works in your favor'
      ],
      warnings: ['Higher risk than your preference']
    },
    {
      template: mockTemplates[2], // Bull Put Spread
      score: 65,
      match_reasons: [
        '✓ Works in sideways-to-bullish markets',
        '✓ Time decay works in your favor'
      ],
      warnings: null
    }
  ],
  inputs: {
    market_outlook: 'neutral',
    volatility_view: 'high_iv',
    risk_tolerance: 'medium'
  },
  total_matches: 5
};

/**
 * Mock categories response
 */
export const mockCategories = {
  categories: [
    { category: 'bullish', count: 5, display_name: 'Bullish' },
    { category: 'bearish', count: 3, display_name: 'Bearish' },
    { category: 'neutral', count: 6, display_name: 'Neutral' },
    { category: 'volatile', count: 3, display_name: 'Volatile' },
    { category: 'income', count: 4, display_name: 'Income' },
    { category: 'advanced', count: 5, display_name: 'Advanced' }
  ],
  total: 26
};

/**
 * Mock deploy response
 */
export const mockDeployResponse = {
  template_name: 'iron_condor',
  display_name: 'Iron Condor',
  underlying: 'NIFTY',
  spot_price: 26000,
  atm_strike: 26000,
  expiry: '2024-12-26',
  legs: [
    {
      type: 'PE',
      position: 'BUY',
      strike: 25600,
      expiry: '2024-12-26',
      instrument_token: 12341,
      tradingsymbol: 'NIFTY24DEC25600PE',
      ltp: 35,
      lots: 1
    },
    {
      type: 'PE',
      position: 'SELL',
      strike: 25800,
      expiry: '2024-12-26',
      instrument_token: 12342,
      tradingsymbol: 'NIFTY24DEC25800PE',
      ltp: 60,
      lots: 1
    },
    {
      type: 'CE',
      position: 'SELL',
      strike: 26200,
      expiry: '2024-12-26',
      instrument_token: 12343,
      tradingsymbol: 'NIFTY24DEC26200CE',
      ltp: 80,
      lots: 1
    },
    {
      type: 'CE',
      position: 'BUY',
      strike: 26400,
      expiry: '2024-12-26',
      instrument_token: 12344,
      tradingsymbol: 'NIFTY24DEC26400CE',
      ltp: 40,
      lots: 1
    }
  ],
  estimated_premium: 65,
  margin_required: 75000
};

/**
 * Mock compare response
 */
export const mockCompareResponse = {
  strategies: [
    {
      template: mockTemplates[0],
      metrics: {
        max_profit: 'Limited',
        max_loss: 'Limited',
        win_probability: '~68%',
        risk_level: 'medium',
        theta_positive: true,
        vega_positive: false,
        delta_neutral: true,
        capital_requirement: 'medium',
        difficulty: 'intermediate',
        num_legs: 4
      }
    },
    {
      template: mockTemplates[5],
      metrics: {
        max_profit: 'Limited',
        max_loss: 'Unlimited',
        win_probability: '~45%',
        risk_level: 'high',
        theta_positive: true,
        vega_positive: false,
        delta_neutral: true,
        capital_requirement: 'high',
        difficulty: 'advanced',
        num_legs: 2
      }
    }
  ],
  comparison_matrix: {
    iron_condor: {
      max_profit: 'Limited',
      max_loss: 'Limited',
      risk_level: 'medium',
      theta_positive: true,
      vega_positive: false,
      delta_neutral: true
    },
    short_straddle: {
      max_profit: 'Limited',
      max_loss: 'Unlimited',
      risk_level: 'high',
      theta_positive: true,
      vega_positive: false,
      delta_neutral: true
    }
  }
};

/**
 * Setup mock API responses for Playwright
 * @param {Page} page - Playwright page object
 */
export async function setupMockApiResponses(page) {
  // Mock templates list
  await page.route('**/api/strategy-library/templates', (route) => {
    const url = route.request().url();

    // Handle category filter
    if (url.includes('category=')) {
      const category = url.match(/category=(\w+)/)?.[1];
      const filtered = mockTemplates.filter(t => t.category === category);
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(filtered)
      });
    }
    // Handle search filter
    else if (url.includes('search=')) {
      const search = url.match(/search=([^&]+)/)?.[1]?.toLowerCase() || '';
      const filtered = mockTemplates.filter(t =>
        t.name.toLowerCase().includes(search) ||
        t.display_name.toLowerCase().includes(search) ||
        t.description.toLowerCase().includes(search)
      );
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(filtered)
      });
    }
    // Return all templates
    else {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockTemplates)
      });
    }
  });

  // Mock categories
  await page.route('**/api/strategy-library/templates/categories', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(mockCategories)
    });
  });

  // Mock template details
  await page.route('**/api/strategy-library/templates/*', (route) => {
    const url = route.request().url();
    const name = url.split('/').pop();
    const template = mockTemplates.find(t => t.name === name);

    if (template) {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(template)
      });
    } else {
      route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Template not found' })
      });
    }
  });

  // Mock wizard
  await page.route('**/api/strategy-library/wizard', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(mockWizardResponse)
    });
  });

  // Mock deploy
  await page.route('**/api/strategy-library/deploy', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(mockDeployResponse)
    });
  });

  // Mock compare
  await page.route('**/api/strategy-library/compare', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(mockCompareResponse)
    });
  });

  // Mock popular
  await page.route('**/api/strategy-library/popular', (route) => {
    const popular = mockTemplates
      .sort((a, b) => b.popularity_score - a.popularity_score)
      .slice(0, 5);

    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ strategies: popular })
    });
  });
}

/**
 * Helper to create a test template with custom properties
 */
export function createMockTemplate(overrides = {}) {
  return {
    id: `template-${Date.now()}`,
    name: 'custom_strategy',
    display_name: 'Custom Strategy',
    category: 'neutral',
    description: 'A custom test strategy',
    legs_config: [{ type: 'CE', position: 'SELL', strike_offset: 0 }],
    max_profit: 'Limited',
    max_loss: 'Limited',
    market_outlook: 'neutral',
    volatility_preference: 'any',
    risk_level: 'medium',
    capital_requirement: 'medium',
    theta_positive: false,
    vega_positive: false,
    delta_neutral: false,
    win_probability: '~50%',
    popularity_score: 50,
    difficulty_level: 'intermediate',
    tags: [],
    ...overrides
  };
}

/**
 * Assert template structure
 */
export function assertTemplateStructure(template) {
  const requiredFields = [
    'id', 'name', 'display_name', 'category', 'description',
    'legs_config', 'max_profit', 'max_loss', 'market_outlook',
    'volatility_preference', 'risk_level', 'capital_requirement'
  ];

  for (const field of requiredFields) {
    if (!(field in template)) {
      throw new Error(`Template missing required field: ${field}`);
    }
  }

  return true;
}
