export interface Alert {
  id: string;
  type: 'fee_low' | 'fee_high' | 'price_move' | 'savings_milestone';
  message: string;
  data: Record<string, unknown>;
  created_at: number;
}

export interface AlertStatus {
  fees: Record<string, number>;
  price: { price_usd: number; sources_count: number };
  recommendation: 'on-chain' | 'lightning' | 'either';
  message: string;
  half_hour_fee: number;
  economy_fee: number;
}
