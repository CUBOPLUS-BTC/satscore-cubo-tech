import { PUBLIC_API_URL } from '$env/static/public';

const BASE = PUBLIC_API_URL;

export const endpoints = {
  auth: {
    challenge: `${BASE}/auth/challenge`,
    verify: `${BASE}/auth/verify`,
    me: `${BASE}/auth/me`,
    lnurl: `${BASE}/auth/lnurl`,
    lnurlStatus: (k1: string) => `${BASE}/auth/lnurl-status?k1=${k1}`,
  },
  price: `${BASE}/price`,
  remittance: {
    compare: `${BASE}/remittance/compare`,
    fees: `${BASE}/remittance/fees`,
  },
  savings: {
    project: `${BASE}/savings/project`,
    goal: `${BASE}/savings/goal`,
    deposit: `${BASE}/savings/deposit`,
    progress: `${BASE}/savings/progress`,
  },
  alerts: {
    list: (since: number) => `${BASE}/alerts?since=${since}`,
    status: `${BASE}/alerts/status`,
    preferences: `${BASE}/alerts/preferences`,
  },
  achievements: `${BASE}/achievements`,
  pension: {
    projection: `${BASE}/pension/projection`,
  },
  network: {
    status: `${BASE}/network/status`,
  },
};