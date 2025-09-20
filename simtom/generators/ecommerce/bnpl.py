from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, date, time
import random
import numpy as np
from enum import Enum

from .base import BaseEcommerceGenerator, BaseEcommerceConfig
from ...core.generator import GeneratorConfig
from ...core.registry import register_generator
from ...core.holidays import get_active_holidays, is_weekend


class BNPLRiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class BNPLConfig(BaseEcommerceConfig):
    """Configuration for BNPL risk scenario generation."""

    # Risk scenario distribution
    risk_scenario_weights: Dict[str, float] = {
        "low_risk_purchase": 0.60,      # Normal, creditworthy customers
        "impulse_purchase": 0.20,       # Higher amounts, less planning
        "credit_stretched": 0.15,       # Near credit limits
        "high_risk_behavior": 0.05      # Multiple red flags
    }

    # Economic stress simulation
    economic_stress_factor: float = 0.0  # 0.0 = normal, 1.0 = recession

    # Default simulation parameters
    base_default_rate: float = 0.03     # 3% base default rate
    seasonal_multiplier: float = 1.2    # Higher defaults post-holidays

    # Volume distribution parameters
    volume_variation_enabled: bool = True  # Enable statistical volume distribution


@register_generator("bnpl")
class BNPLGenerator(BaseEcommerceGenerator):
    """BNPL transaction generator with realistic risk patterns."""
    
    def __init__(self, config):
        # Convert GeneratorConfig to BNPLConfig if needed
        if isinstance(config, GeneratorConfig) and not isinstance(config, BNPLConfig):
            # Create BNPLConfig with defaults, preserving original config values
            bnpl_config = BNPLConfig(**config.model_dump())
        else:
            bnpl_config = config

        super().__init__(bnpl_config)
        self.bnpl_config = bnpl_config

        # Risk patterns
        self.risk_scenarios = list(bnpl_config.risk_scenario_weights.keys())
        self.scenario_weights = list(bnpl_config.risk_scenario_weights.values())

        # Initialize historical timestamp generation if date range specified
        self.use_historical_timestamps = (
            bnpl_config.start_date is not None and bnpl_config.end_date is not None
        )
        if self.use_historical_timestamps:
            self._historical_timestamps = self._generate_historical_timestamps()
            self._timestamp_index = 0
    
    async def generate_record(self) -> Dict[str, Any]:
        """Generate BNPL transaction with risk indicators."""
        
        # Select risk scenario for this transaction
        scenario = random.choices(self.risk_scenarios, weights=self.scenario_weights)[0]
        
        # Generate base transaction
        transaction, customer, product, device, payment_method = self.generate_base_transaction()
        
        # Apply BNPL-specific modifications
        transaction = self._apply_bnpl_scenario(transaction, customer, product, scenario)
        
        # Add risk indicators
        transaction = self._add_risk_indicators(transaction, customer, product, device, scenario)

        # Timestamp is automatically handled by core generator via _get_record_timestamp()

        # Denormalize if configured
        final_record = self.denormalize_transaction(
            transaction, customer, product, device, payment_method
        )

        return final_record
    
    def _apply_bnpl_scenario(
        self, 
        transaction: Dict[str, Any], 
        customer: Dict[str, Any],
        product: Dict[str, Any],
        scenario: str
    ) -> Dict[str, Any]:
        """Apply scenario-specific modifications."""
        
        if scenario == "low_risk_purchase":
            # Normal transaction, no modifications needed
            pass
            
        elif scenario == "impulse_purchase":
            # Impulse behavior indicators (amount stays = product price)
            transaction["purchase_context"] = "impulse"
            
        elif scenario == "credit_stretched":
            # Credit utilization indicators (amount stays = product price)
            credit_limit = random.choice([500, 1000, 1500])  # Typical BNPL limits
            transaction["credit_utilization"] = transaction["amount"] / credit_limit
            
        elif scenario == "high_risk_behavior":
            # High risk behavior indicators (amount stays = product price)
            transaction["purchase_context"] = "rushed"
            transaction["time_on_site_seconds"] = random.randint(30, 120)  # Very quick
        
        return transaction

    def _generate_historical_timestamps(self) -> List[datetime]:
        """Generate realistic historical timestamps with statistical volume distribution."""
        if not self.use_historical_timestamps:
            return []

        if self.bnpl_config.volume_variation_enabled:
            return self._generate_volume_aware_timestamps()
        else:
            return self._generate_uniform_timestamps()

    def _generate_volume_aware_timestamps(self) -> List[datetime]:
        """Generate timestamps using 4-factor statistical volume model."""
        timestamps = []
        current_date = self.bnpl_config.start_date
        base_volume = self.config.base_daily_volume

        while current_date <= self.bnpl_config.end_date:
            daily_volume = self._calculate_statistical_daily_volume(base_volume, current_date)

            # Generate timestamps for this day
            for _ in range(daily_volume):
                timestamp = self._generate_simple_datetime(current_date)
                timestamps.append(timestamp)

            current_date += timedelta(days=1)

        return sorted(timestamps)

    def _generate_uniform_timestamps(self) -> List[datetime]:
        """Legacy uniform distribution for backward compatibility."""
        start_date = self.bnpl_config.start_date
        end_date = self.bnpl_config.end_date
        total_days = (end_date - start_date).days + 1

        # Use max_records if specified, otherwise use base_daily_volume
        if self.config.max_records is not None:
            total_records = self.config.max_records
        else:
            total_records = self.config.base_daily_volume * total_days

        timestamps = []
        for i in range(total_records):
            # Distribute records evenly across the date range
            day_progress = i / total_records
            day_offset = int(day_progress * total_days)
            target_date = start_date + timedelta(days=day_offset)

            # Generate realistic time with business patterns
            timestamp = self._generate_simple_datetime(target_date)
            timestamps.append(timestamp)

        return sorted(timestamps)

    def _calculate_statistical_daily_volume(self, base_volume: int, target_date: date) -> int:
        """Calculate daily volume using 4-factor statistical model."""
        # Set deterministic seed for reproducible results
        random.seed(self.config.seed + target_date.toordinal() if self.config.seed else None)
        np.random.seed(self.config.seed + target_date.toordinal() if self.config.seed else None)

        # Factor 1: Day of Week Effect
        dow_multiplier = self._get_day_of_week_multiplier(target_date)

        # Factor 2: Week of Month Effect (paycheck cycles)
        wom_multiplier = self._get_week_of_month_multiplier(target_date)

        # Factor 3: Month of Year Effect (seasonality)
        moy_multiplier = self._get_month_of_year_multiplier(target_date)

        # Factor 4: Special Events Effect
        event_multiplier = self._get_special_event_multiplier(target_date)

        # Apply multiplicative model
        total_multiplier = dow_multiplier * wom_multiplier * moy_multiplier * event_multiplier

        # Add realistic daily noise (log-normal distribution)
        noise_factor = np.random.lognormal(mean=0, sigma=0.1)  # ±10% daily variation

        final_volume = int(base_volume * total_multiplier * noise_factor)
        return max(1, final_volume)  # Minimum 1 transaction per day

    def _get_day_of_week_multiplier(self, date_obj: date) -> float:
        """E-commerce patterns based on industry data."""
        multipliers = {
            0: 1.15,  # Monday (post-weekend shopping)
            1: 1.10,  # Tuesday
            2: 1.05,  # Wednesday
            3: 1.10,  # Thursday
            4: 1.25,  # Friday (weekend prep)
            5: 0.85,  # Saturday (weekend low)
            6: 0.70   # Sunday (weekend low)
        }
        return multipliers[date_obj.weekday()]

    def _get_week_of_month_multiplier(self, date_obj: date) -> float:
        """Paycheck cycle effects (1st/3rd weeks higher)."""
        day_of_month = date_obj.day

        if day_of_month <= 7:      # Week 1 (payday effect)
            return 1.15
        elif day_of_month <= 14:   # Week 2
            return 0.95
        elif day_of_month <= 21:   # Week 3 (mid-month payday)
            return 1.10
        else:                      # Week 4 (pre-payday low)
            return 0.90

    def _get_month_of_year_multiplier(self, date_obj: date) -> float:
        """Conservative seasonal patterns (special events handled separately)."""
        month_multipliers = {
             1: 0.75,  # January (post-holiday low)
             2: 0.85,  # February
             3: 0.95,  # March
             4: 1.00,  # April (baseline)
             5: 1.00,  # May
             6: 1.05,  # June (summer start)
             7: 1.05,  # July
             8: 1.05,  # August (back-to-school baseline)
             9: 1.00,  # September
            10: 1.05,  # October (mild pre-holiday)
            11: 1.10,  # November (mild increase, events handle spikes)
            12: 1.20   # December (general holiday season, not specific events)
        }
        return month_multipliers[date_obj.month]

    def _get_special_event_multiplier(self, date_obj: date) -> float:
        """Realistic event effects (conservative multipliers)."""
        active_holidays = get_active_holidays(date_obj)

        if not active_holidays:
            return 1.0

        # Conservative, realistic multipliers - covers all holidays from holidays.py
        event_multipliers = {
            # Major shopping events
            'black_friday': 1.6,        # +60% (your spec)
            'cyber_monday': 1.4,        # +40% (your spec)

            # Major holidays (most businesses closed)
            'christmas_day': 0.1,       # Nearly everything closed
            'christmas_eve': 0.3,       # Most stores closed
            'new_years_day': 0.2,       # Holiday low
            'new_years_eve': 0.4,       # Early closures
            'thanksgiving': 0.2,        # Most closed

            # Shopping holidays
            'valentines_day': 1.15,     # +15%
            'mothers_day': 1.2,         # +20%
            'fathers_day': 1.1,         # +10%
            'halloween': 1.05,          # +5%

            # Regular holidays (reduced activity)
            'labor_day': 1.05,          # +5%
            'independence_day': 0.8,    # Reduced activity

            # Holiday periods
            'year_end_holidays': 0.5,   # General holiday period
            'christmas_shopping': 1.2,  # Shopping season
            'post_christmas': 1.3,      # Returns/sales
            'black_friday_week': 1.3,   # Extended shopping week
            'valentines_week': 1.1,     # Valentine shopping
            'mothers_day_week': 1.15,   # Mother's Day shopping
            'back_to_school': 1.2,      # Back-to-school shopping
            'summer_holidays': 1.0,     # Neutral
        }

        # Apply the most restrictive multiplier for suppressive effects,
        # most generous for boosting effects
        multipliers = [event_multipliers.get(holiday, 1.0) for holiday in active_holidays]

        # If any suppressive effects (< 1.0), use the minimum (most restrictive)
        # If only boosting effects (> 1.0), use the maximum (most generous)
        suppressive = [m for m in multipliers if m < 1.0]
        if suppressive:
            return min(suppressive)
        else:
            return max(multipliers)

    def _generate_simple_datetime(self, target_date: date) -> datetime:
        """Generate realistic datetime with business hour patterns."""
        # Generate time of day with business hour weighting
        hour = self._generate_business_hour()
        minute = random.randint(0, 59)
        second = random.randint(0, 59)

        return datetime.combine(target_date, time(hour, minute, second))


    def _generate_business_hour(self) -> int:
        """Generate hour of day with realistic business patterns.

        E-commerce patterns:
        - 70% during business hours (9am-6pm)
        - 20% during evening hours (6pm-11pm)
        - 10% during night/early morning (11pm-9am)
        """
        rand = random.random()

        if rand < 0.7:
            # Business hours (9am-6pm)
            return random.randint(9, 17)
        elif rand < 0.9:
            # Evening hours (6pm-11pm)
            return random.randint(18, 22)
        else:
            # Night/early morning (11pm-9am)
            return random.choice(list(range(23, 24)) + list(range(0, 9)))

    def _get_next_historical_timestamp(self) -> datetime:
        """Get the next historical timestamp, or current time if not using historical."""
        if not self.use_historical_timestamps or self._timestamp_index >= len(self._historical_timestamps):
            return datetime.utcnow()

        timestamp = self._historical_timestamps[self._timestamp_index]
        self._timestamp_index += 1
        return timestamp

    def get_current_day_rate_multiplier(self) -> float:
        """Get rate multiplier for current day (current-date mode only)."""
        # Historical mode should NOT use current-day multipliers during streaming
        # as it has pre-generated timestamps with volumes already calculated
        if self.use_historical_timestamps:
            return 1.0

        if not self.bnpl_config.volume_variation_enabled:
            return 1.0

        today = datetime.utcnow().date()

        # Set deterministic seed for reproducible daily noise
        np.random.seed(self.config.seed + today.toordinal() if self.config.seed else None)

        # Reuse existing 4-factor calculation
        dow_mult = self._get_day_of_week_multiplier(today)
        wom_mult = self._get_week_of_month_multiplier(today)
        moy_mult = self._get_month_of_year_multiplier(today)
        event_mult = self._get_special_event_multiplier(today)

        # Add realistic daily noise (same as historical mode)
        noise_factor = np.random.lognormal(mean=0, sigma=0.1)  # ±10% daily variation

        return dow_mult * wom_mult * moy_mult * event_mult * noise_factor


    def _add_risk_indicators(
        self,
        transaction: Dict[str, Any],
        customer: Dict[str, Any],
        product: Dict[str, Any],
        device: Dict[str, Any],
        scenario: str
    ) -> Dict[str, Any]:
        """Add comprehensive risk indicators."""
        
        # Calculate base risk score
        risk_score = self._calculate_risk_score(customer, product, device, scenario)
        
        # Add BNPL-specific fields
        transaction.update({
            # Risk assessment
            "risk_scenario": scenario,
            "risk_score": risk_score,
            "risk_level": self._risk_level_from_score(risk_score),
            
            # BNPL specifics
            "installment_count": self._select_installment_count(transaction["amount"]),
            "first_payment_amount": self._calculate_first_payment(transaction["amount"]),
            "payment_frequency": "bi_weekly",  # Most common
            
            # Behavioral indicators
            "purchase_context": transaction.get("purchase_context", "normal"),
            "checkout_speed": self._checkout_speed_for_scenario(scenario),
            "cart_abandonment_count": random.randint(0, 3),
            "price_comparison_time": self._price_comparison_time(scenario),
            "time_on_site_seconds": transaction.get("time_on_site_seconds", self._time_on_site_for_scenario(scenario)),
            
            # Economic context
            "economic_stress_factor": self.bnpl_config.economic_stress_factor,
            
            # Default prediction (for ML training)
            "will_default": self._simulate_default(risk_score),
        })
        
        # Add days_to_missed_payment after will_default is set
        if transaction["will_default"]:
            transaction["days_to_first_missed_payment"] = self._days_to_missed_payment(
                risk_score, transaction["installment_count"]
            )
        else:
            transaction["days_to_first_missed_payment"] = None
        
        return transaction
    
    def _calculate_risk_score(
        self,
        customer: Dict[str, Any],
        product: Dict[str, Any],
        device: Dict[str, Any],
        scenario: str
    ) -> float:
        """Calculate risk score using weighted average for natural distribution."""

        # Individual risk factors (0.0 to 1.0 each)
        credit_risk = {"excellent": 0.1, "good": 0.3, "fair": 0.6, "poor": 0.9}.get(
            customer["credit_score_range"], 0.5)

        verification_risk = {"verified": 0.1, "partial": 0.4, "unverified": 0.8}.get(
            customer["verification_level"], 0.5)

        income_risk = {"100k+": 0.1, "75k-100k": 0.2, "50k-75k": 0.3, "25k-50k": 0.6, "<25k": 0.8}.get(
            customer["income_bracket"], 0.5)

        device_risk = 0.7 if not device["is_trusted"] else 0.2

        product_risk = {"low": 0.1, "medium": 0.3, "high": 0.6}.get(
            product["risk_category"], 0.3)

        scenario_risk = {
            "low_risk_purchase": 0.1,
            "impulse_purchase": 0.4,
            "credit_stretched": 0.7,
            "high_risk_behavior": 0.9
        }.get(scenario, 0.3)

        # Weighted average (naturally distributes 0.0-1.0)
        risk_factors = [
            (credit_risk, 0.3),      # 30% weight - most important
            (verification_risk, 0.2), # 20% weight
            (income_risk, 0.2),      # 20% weight
            (device_risk, 0.1),      # 10% weight
            (product_risk, 0.1),     # 10% weight
            (scenario_risk, 0.1)     # 10% weight
        ]

        score = sum(risk * weight for risk, weight in risk_factors)

        # Economic stress multiplier (mild adjustment)
        score *= (1 + self.bnpl_config.economic_stress_factor * 0.2)

        return min(score, 1.0)  # Cap at 1.0
    
    def _risk_level_from_score(self, risk_score: float) -> str:
        """Convert numeric risk score to risk level."""
        if risk_score < 0.3:
            return BNPLRiskLevel.LOW
        elif risk_score < 0.6:
            return BNPLRiskLevel.MEDIUM
        elif risk_score < 0.8:
            return BNPLRiskLevel.HIGH
        else:
            return BNPLRiskLevel.VERY_HIGH
    
    def _select_installment_count(self, amount: float) -> int:
        """Select installment count based on amount."""
        if amount < 100:
            return 4  # 4 payments
        elif amount < 500:
            return random.choice([4, 6])
        elif amount < 1000:
            return random.choice([6, 12])
        else:
            return random.choice([12, 24])
    
    def _calculate_first_payment(self, amount: float) -> float:
        """Calculate first payment amount (typically 25% for BNPL)."""
        return round(amount * 0.25, 2)
    
    def _checkout_speed_for_scenario(self, scenario: str) -> str:
        """Determine checkout speed based on scenario."""
        speed_mapping = {
            "low_risk_purchase": random.choice(["normal", "slow"]),
            "impulse_purchase": "fast",
            "credit_stretched": "normal", 
            "high_risk_behavior": "very_fast"
        }
        return speed_mapping.get(scenario, "normal")
    
    def _price_comparison_time(self, scenario: str) -> int:
        """Time spent comparing prices (seconds)."""
        if scenario == "impulse_purchase":
            return random.randint(0, 60)
        elif scenario == "high_risk_behavior":
            return random.randint(0, 30)
        else:
            return random.randint(60, 300)

    def _time_on_site_for_scenario(self, scenario: str) -> int:
        """Total time spent on site before purchase (seconds)."""
        if scenario == "high_risk_behavior":
            return random.randint(30, 120)  # Very quick
        elif scenario == "impulse_purchase":
            return random.randint(120, 300)  # Quick decision
        elif scenario == "credit_stretched":
            return random.randint(300, 600)  # More deliberation
        else:
            return random.randint(180, 900)  # Normal browsing
    
    def _simulate_default(self, risk_score: float) -> bool:
        """Simulate historical default outcome using two-level statistical model."""

        # Level 1: Population-level default probability (Beta distribution)
        expected_default_rate = self._get_population_default_rate(risk_score)

        # Level 2: Individual variation (Normal noise around expected rate)
        actual_default_rate = self._add_individual_variation(expected_default_rate)

        # Convert probability to historical boolean outcome
        return random.random() < actual_default_rate

    def _get_population_default_rate(self, risk_score: float) -> float:
        """Map risk score to population default rate using Beta distribution.

        Creates realistic clustering:
        - Most customers around 3-5% default rate
        - Risk score 0.0 → ~0.5% (excellent customers)
        - Risk score 1.0 → ~20% (poor credit customers)
        """
        # Map risk score to Beta distribution percentiles
        percentile = 0.05 + (risk_score * 0.90)  # 5th to 95th percentile

        # Beta(2, 48) gives mean ≈ 4%, realistic shape for default rates
        # Using scipy would be ideal, but using approximation for simplicity
        return self._beta_ppf_approximation(percentile, a=2, b=48)

    def _beta_ppf_approximation(self, percentile: float, a: float, b: float) -> float:
        """Approximate Beta distribution percentile function."""
        # Simple approximation: linear interpolation between realistic bounds
        min_rate = 0.005  # 0.5% minimum default rate
        max_rate = 0.20   # 20% maximum default rate

        # Apply some curvature to approximate Beta distribution shape
        # Most people cluster around lower rates (realistic for defaults)
        curved_percentile = percentile ** 1.5  # Creates right-skewed distribution

        return min_rate + (curved_percentile * (max_rate - min_rate))

    def _add_individual_variation(self, expected_rate: float) -> float:
        """Add individual-level variation around expected default rate."""
        # Small normal noise representing unobservable factors
        # (job loss, medical emergency, family crisis, etc.)
        noise_std = 0.01  # 1% standard deviation

        # Generate normal noise around expected rate
        import numpy as np
        actual_rate = np.random.normal(expected_rate, noise_std)

        # Bound to realistic range [0.1%, 25%]
        return max(0.001, min(0.25, actual_rate))
    
    def _days_to_missed_payment(self, risk_score: float, installment_count: int) -> int:
        """Simulate days until first missed payment using payment period model."""

        # Payment periods: 1 through installment_count (bi-weekly payments)
        possible_periods = list(range(1, installment_count + 1))

        # Universal temporal risk pattern (same shape for all risk levels)
        base_pattern = self._create_universal_risk_pattern(len(possible_periods))

        # Risk score scales the entire pattern (higher risk = higher at all periods)
        risk_multiplier = 0.5 + (risk_score * 1.5)  # Range: 0.5x to 2.0x
        scaled_weights = [weight * risk_multiplier for weight in base_pattern]

        # Normalize to valid probabilities
        total_weight = sum(scaled_weights)
        if total_weight <= 0:  # Defensive check
            # Fallback to uniform distribution
            final_weights = [1.0 / len(possible_periods)] * len(possible_periods)
        else:
            final_weights = [w / total_weight for w in scaled_weights]

        # Choose payment period
        chosen_period = random.choices(possible_periods, weights=final_weights)[0]

        # Convert to days: period × 14 (bi-weekly)
        days = chosen_period * 14

        # ROBUSTNESS CHECK: Ensure always >= 14 when will_default = TRUE
        if days < 14:
            days = 14  # Force minimum valid value

        return days

    def _create_universal_risk_pattern(self, num_periods: int) -> list:
        """Create universal temporal risk pattern: low early, peak middle, decline late."""
        if num_periods <= 0:
            return [1.0]  # Defensive fallback

        if num_periods == 1:
            return [1.0]
        elif num_periods == 2:
            return [0.3, 0.7]  # Slightly higher risk in second period
        elif num_periods <= 4:
            # Short loans: gradual increase then decline
            return [0.2, 0.4, 0.3, 0.1][:num_periods]
        else:
            # Longer loans: more realistic curve
            pattern = []
            for i in range(num_periods):
                # Create bell-curve-like pattern peaked around middle periods
                position = i / (num_periods - 1)  # 0.0 to 1.0

                # Bell curve: low at ends, high in middle
                # Using simple quadratic approximation of bell curve
                if position <= 0.5:
                    risk_level = 0.1 + (position * 1.6)  # Rise from 0.1 to 0.9
                else:
                    risk_level = 0.9 - ((position - 0.5) * 1.6)  # Fall from 0.9 to 0.1

                pattern.append(max(0.05, risk_level))  # Minimum 5% weight

            return pattern