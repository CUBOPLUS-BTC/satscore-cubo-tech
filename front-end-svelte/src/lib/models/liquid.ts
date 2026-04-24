export type LiquidLayer = 'on_chain' | 'lightning' | 'liquid';
export type LiquidUrgency = 'low' | 'medium' | 'high' | 'instant';
export type LiquidPrivacyLevel = 'normal' | 'high' | 'confidential';

export interface LiquidBlock {
  height: number;
  tx_count: number;
  timestamp: number;
  size: number;
}

export interface LiquidOverview {
  network: 'liquid';
  block_height: number;
  block_time_seconds: number;
  settlement_time_seconds: number;
  mempool: {
    tx_count: number;
    vsize: number;
  };
  recent_blocks: {
    count: number;
    avg_tx_per_block: number;
    blocks: LiquidBlock[];
  };
  fee_rate_sat_vb: number;
  typical_tx_fee_sats: number;
  features: string[];
  data_source: string;
  timestamp: number;
}

export interface LiquidAsset {
  asset_id: string;
  name: string;
  ticker: string;
  precision: number;
  chain_stats?: Record<string, number>;
  mempool_stats?: Record<string, number>;
  available: boolean;
}

export interface LiquidAssets {
  l_btc: LiquidAsset;
  usdt: LiquidAsset;
  note: string;
}

export interface LiquidLayerComparison {
  name: string;
  settlement_seconds: number;
  privacy: string;
  min_amount_sats: number;
  best_for: string[];
}

export interface OnChainComparison extends LiquidLayerComparison {
  fee_fastest_sats: number;
  fee_economy_sats: number;
}

export interface LightningComparison extends LiquidLayerComparison {
  fee_typical_sats: number;
  fee_range: string;
}

export interface LiquidSidechainComparison extends LiquidLayerComparison {
  fee_typical_sats: number;
  supports_assets: boolean;
}

export interface RecommendationMatrixEntry {
  amount: string;
  best: LiquidLayer;
  reason: string;
}

export interface LiquidCompare {
  on_chain: OnChainComparison;
  lightning: LightningComparison;
  liquid: LiquidSidechainComparison;
  recommendation_matrix: Record<string, RecommendationMatrixEntry>;
}

export interface PegDirection {
  description: string;
  confirmations_required: number;
  estimated_time: string;
  minimum_amount_btc: number;
  fee: string;
  process: string[];
}

export interface PegAlternative {
  description: string;
  supports: string[];
  speed: string;
  fee?: string;
}

export interface LiquidWallet {
  name: string;
  by: string;
  custody?: string;
  platforms: string[];
  features: string[];
  description?: string;
}

export interface LiquidPegInfo {
  peg_in: PegDirection;
  peg_out: PegDirection;
  alternatives: Record<string, PegAlternative>;
  wallets: LiquidWallet[];
}

export interface LiquidOption {
  fee_usd: number;
  confirm_seconds: number;
  privacy: string;
}

export interface LiquidRecommendation {
  recommended_layer: LiquidLayer;
  reason: string;
  estimated_fee_usd: number;
  estimated_confirm_seconds: number;
  input: {
    amount_usd: number;
    urgency: LiquidUrgency;
    privacy: LiquidPrivacyLevel;
  };
  all_options: Record<LiquidLayer, LiquidOption>;
}

export interface LiquidRecommendInput {
  amount_usd: number;
  urgency: LiquidUrgency;
  privacy: LiquidPrivacyLevel;
}
