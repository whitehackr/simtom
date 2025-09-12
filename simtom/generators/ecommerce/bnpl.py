from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import random
from enum import Enum

from .base import BaseEcommerceGenerator, BaseEcommerceConfig
from ...core.generator import GeneratorConfig
from ...core.registry import register_generator


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
            # Higher amount, electronics/luxury categories
            if product["category"] in ["electronics", "clothing"]:
                # Bump up price by 20-50%
                multiplier = random.uniform(1.2, 1.5)
                transaction["amount"] = round(product["price"] * multiplier, 2)
                transaction["purchase_context"] = "impulse"
            
        elif scenario == "credit_stretched":
            # Transaction near customer's credit limit
            credit_limit = random.choice([500, 1000, 1500])  # Typical BNPL limits
            transaction["amount"] = round(credit_limit * random.uniform(0.8, 0.95), 2)
            transaction["credit_utilization"] = transaction["amount"] / credit_limit
            
        elif scenario == "high_risk_behavior":
            # Multiple risk flags
            transaction["amount"] = round(product["price"] * random.uniform(1.3, 2.0), 2)
            transaction["purchase_context"] = "rushed"
            transaction["time_on_site_seconds"] = random.randint(30, 120)  # Very quick
        
        return transaction
    
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
            "checkout_speed": self._checkout_speed_for_scenario(scenario),
            "cart_abandonment_count": random.randint(0, 3),
            "price_comparison_time": self._price_comparison_time(scenario),
            
            # Economic context
            "economic_stress_factor": self.bnpl_config.economic_stress_factor,
            
            # Default prediction (for ML training)
            "will_default": self._simulate_default(risk_score),
        })
        
        # Add days_to_missed_payment after will_default is set
        if transaction["will_default"]:
            transaction["days_to_first_missed_payment"] = self._days_to_missed_payment(risk_score)
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
        """Calculate risk score based on multiple factors."""
        
        score = 0.0
        
        # Customer risk factors
        credit_scores = {"excellent": 0.1, "good": 0.3, "fair": 0.6, "poor": 0.9}
        score += credit_scores.get(customer["credit_score_range"], 0.5)
        
        verification_scores = {"verified": 0.1, "partial": 0.4, "unverified": 0.8}
        score += verification_scores.get(customer["verification_level"], 0.5)
        
        income_scores = {"100k+": 0.1, "75k-100k": 0.2, "50k-75k": 0.3, "25k-50k": 0.6, "<25k": 0.8}
        score += income_scores.get(customer["income_bracket"], 0.5)
        
        # Device trust
        if not device["is_trusted"]:
            score += 0.3
        
        # Product risk
        product_risk_scores = {"low": 0.1, "medium": 0.3, "high": 0.6}
        score += product_risk_scores.get(product["risk_category"], 0.3)
        
        # Scenario risk
        scenario_scores = {
            "low_risk_purchase": 0.0,
            "impulse_purchase": 0.3, 
            "credit_stretched": 0.6,
            "high_risk_behavior": 0.9
        }
        score += scenario_scores.get(scenario, 0.0)
        
        # Economic stress multiplier
        score *= (1 + self.bnpl_config.economic_stress_factor * 0.5)
        
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
    
    def _simulate_default(self, risk_score: float) -> bool:
        """Simulate whether transaction will default based on risk score."""
        adjusted_default_rate = self.bnpl_config.base_default_rate * (1 + risk_score * 3)
        return random.random() < adjusted_default_rate
    
    def _days_to_missed_payment(self, risk_score: float) -> int:
        """Simulate days until first missed payment."""
        # Higher risk = faster default
        base_days = 45  # Typical first payment cycle
        risk_factor = risk_score * 30
        return max(7, int(base_days - risk_factor + random.randint(-10, 10)))