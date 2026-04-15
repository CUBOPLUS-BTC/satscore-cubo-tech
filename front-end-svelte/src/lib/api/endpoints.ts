const BASE_URL = import.meta.env.VITE_API_URL ?? 'https://api.eclalune.com';

export const endpoints = {
  auth: {
    challenge: `${BASE_URL}/auth/challenge`,
    verify: `${BASE_URL}/auth/verify`,
    me: `${BASE_URL}/auth/me`,
  },
  price: `${BASE_URL}/price`,
  score: (address: string) => `${BASE_URL}/score/${address}`,
  simulate: {
    volatility: `${BASE_URL}/simulate/volatility`,
    conversion: `${BASE_URL}/simulate/conversion`,
  },
  remittance: {
    compare: `${BASE_URL}/remittance/compare`,
    fees: `${BASE_URL}/remittance/fees`,
  },
} as const;
