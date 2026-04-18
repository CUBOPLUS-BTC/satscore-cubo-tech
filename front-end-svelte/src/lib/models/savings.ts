export interface ProjectionScenario {
  name: string;
  annual_return_pct: number;
  total_invested: number;
  projected_value: number;
  total_btc: number;
  multiplier: number;
}

export interface MonthlyDataPoint {
  month: number;
  traditional: number;
  btc_moderate: number;
  invested: number;
}

export interface ProjectionResult {
  monthly_usd: number;
  years: number;
  total_invested: number;
  current_btc_price: number;
  scenarios: ProjectionScenario[];
  traditional_value: number;
  monthly_data: MonthlyDataPoint[];
}

export interface SavingsGoal {
  monthly_target_usd: number;
  target_years: number;
  created_at: number;
}

export interface SavingsDeposit {
  amount_usd: number;
  btc_price: number;
  btc_amount: number;
  created_at: number;
}

export interface Milestone {
  name: string;
  target: number;
  reached: boolean;
}

export interface SavingsProgress {
  has_goal: boolean;
  goal?: SavingsGoal;
  total_invested_usd: number;
  total_btc: number;
  current_value_usd: number;
  roi_percent: number;
  current_btc_price: number;
  streak_months: number;
  deposit_count: number;
  recent_deposits: SavingsDeposit[];
  milestones: Milestone[];
  next_milestone: Milestone | null;
}
