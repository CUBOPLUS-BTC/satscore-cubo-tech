export const en = {
  app: {
    name: 'Magma',
    tagline: 'Bitcoin Financial Intelligence',
    titleSuffix: '| Magma',
    description: 'Track your sats, analyze your wealth, and understand your financial footprint in the Bitcoin ecosystem.',
  },
  nav: {
    home: 'Home',
    remittance: 'Remittance',
    savings: 'Savings',
    logout: 'Logout',
    theme: 'Theme',
  },
  home: {
    welcomeDescription: 'Your money, your rules. See exactly where your sats go.',
    dontTrust: "Don't trust, verify",
    sources: '{count} Sources',
    verified: 'Verified',
    tools: {
      remittance: {
        title: 'Send money home',
        description: 'Find the cheapest way to send sats across borders. Compare fees instantly.',
      },
      savings: {
        title: 'Stack sats',
        description: 'Set a goal, save consistently, watch your Bitcoin grow over time.',
      },
    },
  },
  remittance: {
    title: 'Remittance',
    subtitle: 'How much are you sending? We\'ll find you the cheapest route.',
    amount: 'Amount (USD)',
    frequency: 'Frequency',
    compare: 'Compare Channels',
    comparing: 'Comparing...',
    compareOptions: 'How much are you sending?',
    availableChannels: 'Available Channels',
    annualSavings: 'Annual Savings',
    bestTime: 'Best Time to Send',
    recommended: 'RECOMMENDED',
    currentFee: 'Current Fee',
    lowFee: 'Low Fee',
    savings: 'Savings',
    potentialAnnualSavings: 'Potential Annual Savings',
    vsWorstChannel: 'vs worst channel with',
    fee: 'Fee',
    amountReceived: 'Amount Received',
    estimatedTime: 'Estimated Time',
    errorFetch: 'Failed to compare remittance options',
    frequencies: {
      monthly: 'Monthly',
      biweekly: 'Biweekly',
      weekly: 'Weekly',
    },
  },
  login: {
    loginWithLightning: 'Login with Lightning',
    loginWithNostr: 'Login with Nostr',
    scanWithWallet: 'Choose how to connect',
    scanQR: 'Scan QR Code',
    waitingForWallet: 'Waiting for wallet...',
    keysNeverLeave: 'No passwords, no accounts. Just your keys',
    connect: 'Connect',
  },
  error: {
    somethingWentWrong: 'Something went wrong',
    goBack: 'Go Back',
    home: 'Home',
  },
  common: {
    loading: 'Loading...',
    error: 'Error',
    retry: 'Retry',
    cancel: 'Cancel',
    close: 'Close',
  },
  savings: {
    title: 'Stack Sats',
    subtitle: 'How much could your Bitcoin be worth? Run the numbers.',
    projectionTitle: 'Run the numbers',
    monthlyAmount: 'Monthly Amount (USD)',
    years: 'Years',
    calculate: 'Calculate Projection',
    conservative: 'Conservative',
    moderate: 'Moderate',
    optimistic: 'Optimistic',
    annual: 'annual',
    multiplier: 'your investment',
    traditionalSavings: 'Traditional Savings (2%)',
    progressTitle: 'Your Savings Progress',
    totalInvested: 'Total Invested',
    currentValue: 'Current Value',
    streak: 'Streak',
    months: 'months',
    milestones: 'Milestones',
    depositAmount: 'Deposit Amount (USD)',
    recordDeposit: 'Record Deposit',
    recentDeposits: 'Recent Deposits',
    setupGoal: 'Set Up Your Savings Goal',
    monthlyTarget: 'Monthly Target (USD)',
    targetYears: 'Target Years',
    createGoal: 'Create Goal',
  },
  alerts: {
    title: 'Alerts',
    noAlerts: 'No alerts yet',
    feeStatus: 'Fee Status',
  },
} as const;

type StringifyDeep<T> = {
  [K in keyof T]: T[K] extends string
    ? string
    : T[K] extends object
      ? StringifyDeep<T[K]>
      : T[K];
};

export type Translations = StringifyDeep<typeof en>;
