from dataclasses import dataclass
from typing import Optional


@dataclass
class ChannelComparison:
    name: str
    fee_percent: float
    fee_usd: float
    amount_received: float
    estimated_time: str
    is_recommended: bool
    is_live: bool = False

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "fee_percent": self.fee_percent,
            "fee_usd": self.fee_usd,
            "amount_received": self.amount_received,
            "estimated_time": self.estimated_time,
            "is_recommended": self.is_recommended,
            "is_live": self.is_live,
        }


@dataclass
class SendTimeRecommendation:
    best_time: str
    current_fee_sat_vb: int
    estimated_low_fee_sat_vb: int
    savings_percent: float

    def to_dict(self) -> dict:
        return {
            "best_time": self.best_time,
            "current_fee_sat_vb": self.current_fee_sat_vb,
            "estimated_low_fee_sat_vb": self.estimated_low_fee_sat_vb,
            "savings_percent": self.savings_percent,
        }


@dataclass
class RemittanceResponse:
    channels: list
    annual_savings: float
    best_channel: str
    savings_vs_worst: float = 0.0
    worst_channel_name: str = ""
    best_time: Optional[SendTimeRecommendation] = None

    def to_dict(self) -> dict:
        return {
            "channels": [
                c.to_dict() if hasattr(c, "to_dict") else c for c in self.channels
            ],
            "annual_savings": self.annual_savings,
            "best_channel": self.best_channel,
            "savings_vs_worst": self.savings_vs_worst,
            "worst_channel_name": self.worst_channel_name,
            "best_time": (
                self.best_time.to_dict()
                if self.best_time and hasattr(self.best_time, "to_dict")
                else None
            ),
        }
