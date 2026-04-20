"""Typed response models returned by the SDK.

The backend JSON is lenient (extra keys are ignored). Models expose the
fields the SDK considers stable; unknown keys are preserved via the
``raw`` attribute for forward compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass(frozen=True)
class PriceQuote:
    price_usd: float
    sources_count: int
    deviation: float
    has_warning: bool
    raw: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "PriceQuote":
        return cls(
            price_usd=float(data.get("price_usd", 0.0)),
            sources_count=int(data.get("sources_count", 0)),
            deviation=float(data.get("deviation", 0.0)),
            has_warning=bool(data.get("has_warning", True)),
            raw=data,
        )


@dataclass(frozen=True)
class ProjectionScenario:
    name: str
    annual_return_pct: float
    total_invested: float
    projected_value: float
    total_btc: float
    multiplier: float

    @classmethod
    def from_dict(cls, data: dict) -> "ProjectionScenario":
        return cls(
            name=str(data.get("name", "")),
            annual_return_pct=float(data.get("annual_return_pct", 0.0)),
            total_invested=float(data.get("total_invested", 0.0)),
            projected_value=float(data.get("projected_value", 0.0)),
            total_btc=float(data.get("total_btc", 0.0)),
            multiplier=float(data.get("multiplier", 0.0)),
        )


@dataclass(frozen=True)
class SavingsProjection:
    monthly_usd: float
    years: int
    total_invested: float
    current_btc_price: float
    scenarios: List[ProjectionScenario]
    traditional_value: float
    monthly_data: List[dict]
    raw: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "SavingsProjection":
        scenarios = [
            ProjectionScenario.from_dict(s) for s in data.get("scenarios", [])
        ]
        return cls(
            monthly_usd=float(data.get("monthly_usd", 0.0)),
            years=int(data.get("years", 0)),
            total_invested=float(data.get("total_invested", 0.0)),
            current_btc_price=float(data.get("current_btc_price", 0.0)),
            scenarios=scenarios,
            traditional_value=float(data.get("traditional_value", 0.0)),
            monthly_data=list(data.get("monthly_data", [])),
            raw=data,
        )


@dataclass(frozen=True)
class PensionProjection:
    total_invested_usd: float
    total_btc_accumulated: float
    current_value_usd: float
    avg_buy_price: float
    current_btc_price: float
    monthly_breakdown: List[dict]
    monthly_data: List[dict]
    raw: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "PensionProjection":
        return cls(
            total_invested_usd=float(data.get("total_invested_usd", 0.0)),
            total_btc_accumulated=float(data.get("total_btc_accumulated", 0.0)),
            current_value_usd=float(data.get("current_value_usd", 0.0)),
            avg_buy_price=float(data.get("avg_buy_price", 0.0)),
            current_btc_price=float(data.get("current_btc_price", 0.0)),
            monthly_breakdown=list(data.get("monthly_breakdown", [])),
            monthly_data=list(data.get("monthly_data", [])),
            raw=data,
        )


@dataclass(frozen=True)
class RemittanceChannel:
    name: str
    fee_percent: float
    fee_usd: float
    amount_received: float
    estimated_time: str
    is_recommended: bool
    is_live: bool

    @classmethod
    def from_dict(cls, data: dict) -> "RemittanceChannel":
        return cls(
            name=str(data.get("name", "")),
            fee_percent=float(data.get("fee_percent", 0.0)),
            fee_usd=float(data.get("fee_usd", 0.0)),
            amount_received=float(data.get("amount_received", 0.0)),
            estimated_time=str(data.get("estimated_time", "")),
            is_recommended=bool(data.get("is_recommended", False)),
            is_live=bool(data.get("is_live", False)),
        )


@dataclass(frozen=True)
class SendTimeRecommendation:
    best_time: str
    current_fee_sat_vb: int
    estimated_low_fee_sat_vb: int
    savings_percent: float

    @classmethod
    def from_dict(cls, data: dict) -> "SendTimeRecommendation":
        return cls(
            best_time=str(data.get("best_time", "")),
            current_fee_sat_vb=int(data.get("current_fee_sat_vb", 0)),
            estimated_low_fee_sat_vb=int(data.get("estimated_low_fee_sat_vb", 0)),
            savings_percent=float(data.get("savings_percent", 0.0)),
        )


@dataclass(frozen=True)
class RemittanceComparison:
    channels: List[RemittanceChannel]
    annual_savings: float
    best_channel: str
    savings_vs_worst: float
    worst_channel_name: str
    best_time: Optional[SendTimeRecommendation]
    raw: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "RemittanceComparison":
        bt = data.get("best_time")
        return cls(
            channels=[
                RemittanceChannel.from_dict(c) for c in data.get("channels", [])
            ],
            annual_savings=float(data.get("annual_savings", 0.0)),
            best_channel=str(data.get("best_channel", "")),
            savings_vs_worst=float(data.get("savings_vs_worst", 0.0)),
            worst_channel_name=str(data.get("worst_channel_name", "")),
            best_time=SendTimeRecommendation.from_dict(bt) if isinstance(bt, dict) else None,
            raw=data,
        )


@dataclass(frozen=True)
class SavingsProgress:
    has_goal: bool
    total_invested_usd: float
    total_btc: float
    current_value_usd: float
    roi_percent: float
    streak_months: int
    deposit_count: int
    recent_deposits: List[dict]
    milestones: List[dict]
    raw: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "SavingsProgress":
        return cls(
            has_goal=bool(data.get("has_goal", False)),
            total_invested_usd=float(data.get("total_invested_usd", 0.0)),
            total_btc=float(data.get("total_btc", 0.0)),
            current_value_usd=float(data.get("current_value_usd", 0.0)),
            roi_percent=float(data.get("roi_percent", 0.0)),
            streak_months=int(data.get("streak_months", 0)),
            deposit_count=int(data.get("deposit_count", 0)),
            recent_deposits=list(data.get("recent_deposits", [])),
            milestones=list(data.get("milestones", [])),
            raw=data,
        )


@dataclass(frozen=True)
class Alert:
    type: str
    message: str
    created_at: Optional[int]
    raw: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "Alert":
        return cls(
            type=str(data.get("type", "")),
            message=str(data.get("message", "")),
            created_at=(
                int(data["created_at"])
                if isinstance(data.get("created_at"), (int, float))
                else None
            ),
            raw=data,
        )


@dataclass(frozen=True)
class LiquidNetworkStatus:
    available: bool
    block_height: Optional[int]
    recommended_fee_sat_vb: float
    fee_estimates: dict
    network: str
    raw: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "LiquidNetworkStatus":
        height = data.get("block_height")
        return cls(
            available=bool(data.get("available", False)),
            block_height=int(height) if isinstance(height, (int, float)) else None,
            recommended_fee_sat_vb=float(data.get("recommended_fee_sat_vb", 0.0)),
            fee_estimates=dict(data.get("fee_estimates", {}))
            if isinstance(data.get("fee_estimates"), dict)
            else {},
            network=str(data.get("network", "liquid")),
            raw=data,
        )


@dataclass(frozen=True)
class LiquidAsset:
    asset_id: Optional[str]
    name: Optional[str]
    ticker: Optional[str]
    precision: Optional[int]
    issued_amount: Optional[int]
    burned_amount: Optional[int]
    raw: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "LiquidAsset":
        def _int(key: str) -> Optional[int]:
            value = data.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return int(value)
            return None

        return cls(
            asset_id=str(data["asset_id"]) if isinstance(data.get("asset_id"), str) else None,
            name=str(data["name"]) if isinstance(data.get("name"), str) else None,
            ticker=str(data["ticker"]) if isinstance(data.get("ticker"), str) else None,
            precision=_int("precision"),
            issued_amount=_int("issued_amount"),
            burned_amount=_int("burned_amount"),
            raw=data,
        )
