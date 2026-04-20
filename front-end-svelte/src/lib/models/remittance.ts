export interface ChannelComparison {
  name: string;
  fee_percent: number;
  fee_usd: number;
  amount_received: number;
  estimated_time: string;
  is_recommended: boolean;
  is_live: boolean;
}

export interface SendTimeRecommendation {
  best_time: string;
  current_fee_sat_vb: number;
  estimated_low_fee_sat_vb: number;
  savings_percent: number;
}

export interface RemittanceResult {
  channels: ChannelComparison[];
  annual_savings: number;
  best_channel: string;
  savings_vs_worst: number;
  worst_channel_name: string;
  best_time?: SendTimeRecommendation;
}
