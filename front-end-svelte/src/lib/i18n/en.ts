export const en = {
  nav: { home: 'Home', score: 'Score', simulator: 'Simulator', remittance: 'Remittance', logout: 'Logout' },
  home: {
    welcome: 'Bitcoin Financial Intelligence',
    quickActions: 'Quick Actions',
    analyzeAddress: 'Analyze Address',
    volatilitySimulator: 'Volatility Simulator',
    remittanceOptimizer: 'Remittance Optimizer',
    dontTrust: "Don't trust, verify",
  },
  price: { fromSources: 'from {count} sources', verified: 'Verified' },
  score: {
    title: 'Bitcoin Score',
    enterAddress: 'Enter a Bitcoin address to analyze',
    verify: 'Verify',
    recommendations: 'Recommendations',
  },
  simulator: {
    title: 'Volatility Simulator',
    amount: 'Amount (USD)',
    period: 'Analysis Period',
    run: 'Run Simulation',
    optimalDay: 'Optimal Day',
    expectedReturn: 'Expected Return',
    riskLevel: 'Risk Level',
    recommendation: 'Recommendation',
  },
  remittance: {
    title: 'Remittance Optimizer',
    amount: 'Amount (USD)',
    frequency: 'Frequency',
    compare: 'Compare Channels',
    annualSavings: 'Annual Savings',
    bestTime: 'Best Time to Send',
    recommended: 'Recommended',
  },
  common: { loading: 'Loading...', error: 'Error', retry: 'Retry', cancel: 'Cancel', close: 'Close' },
} as const;

type StringifyDeep<T> = {
  [K in keyof T]: T[K] extends string
    ? string
    : T[K] extends object
      ? StringifyDeep<T[K]>
      : T[K];
};

export type Translations = StringifyDeep<typeof en>;
