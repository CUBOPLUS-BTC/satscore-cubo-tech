const BASE = '/proxy';

export const endpoints = {
  auth: {
    challenge: `${BASE}/auth/challenge`,
    verify: `${BASE}/auth/verify`,
    me: `${BASE}/auth/me`,
  },
  price: `${BASE}/price`,
  score: (address: string) => `${BASE}/score/${address}`,
  simulate: {
    volatility: `${BASE}/simulate/volatility`,
    conversion: `${BASE}/simulate/conversion`,
  },
  remittance: {
    compare: `${BASE}/remittance/compare`,
    fees: `${BASE}/remittance/fees`,
  },
} as const;
