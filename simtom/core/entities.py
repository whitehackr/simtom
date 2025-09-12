from typing import Dict, Any, List, Optional
from datetime import datetime, date
from faker import Faker
import random
from collections import defaultdict


class EntityRegistry:
    """Base class for managing lightweight entity stores."""
    
    def __init__(self, max_entities: int = 100_000, seed: Optional[int] = None):
        self.entities: Dict[str, Dict[str, Any]] = {}
        self.max_entities = max_entities
        self.fake = Faker()
        if seed:
            self.fake.seed_instance(seed)
            random.seed(seed)
    
    def get(self, entity_id: str) -> Optional[Dict[str, Any]]:
        return self.entities.get(entity_id)
    
    def exists(self, entity_id: str) -> bool:
        return entity_id in self.entities
    
    def register(self, entity_id: str, entity_data: Dict[str, Any]) -> None:
        if len(self.entities) >= self.max_entities:
            # Simple LRU eviction - remove oldest
            oldest_id = next(iter(self.entities))
            del self.entities[oldest_id]
        
        self.entities[entity_id] = entity_data
    
    def get_or_create(self, entity_id: str) -> Dict[str, Any]:
        if entity_id in self.entities:
            return self.entities[entity_id]
        
        entity_data = self._generate_entity(entity_id)
        self.register(entity_id, entity_data)
        return entity_data
    
    def _generate_entity(self, entity_id: str) -> Dict[str, Any]:
        raise NotImplementedError
    
    def count(self) -> int:
        return len(self.entities)


class CustomerRegistry(EntityRegistry):
    """Registry for customer entities with BNPL risk attributes."""
    
    def __init__(self, max_entities: int = 100_000, seed: Optional[int] = None):
        super().__init__(max_entities, seed)
        
        # Risk-based distributions
        self.income_brackets = ["<25k", "25k-50k", "50k-75k", "75k-100k", "100k+"]
        self.employment_statuses = ["employed", "self_employed", "unemployed", "student", "retired"]
        self.credit_score_ranges = ["excellent", "good", "fair", "poor"]
        self.signup_channels = ["organic", "paid_search", "social", "referral", "email"]
        self.verification_levels = ["verified", "partial", "unverified"]
        self.address_stability = ["new", "stable", "frequent_mover"]
    
    def _generate_entity(self, customer_id: str) -> Dict[str, Any]:
        signup_date = self.fake.date_between(start_date="-2y", end_date="today")
        
        return {
            "customer_id": customer_id,
            "email": self.fake.email(),
            "dob": self.fake.date_of_birth(minimum_age=18, maximum_age=70),
            "signup_date": signup_date,
            
            # Risk demographics
            "income_bracket": random.choice(self.income_brackets),
            "employment_status": random.choice(self.employment_statuses),
            "credit_score_range": random.choices(
                self.credit_score_ranges, 
                weights=[15, 35, 35, 15]  # Normal distribution
            )[0],
            
            # Address risk indicators
            "country": "US",  # Simplify for now
            "state": self.fake.state_abbr(),
            "zipcode": self.fake.zipcode(),
            "address_stability": random.choices(
                self.address_stability,
                weights=[20, 60, 20]  # Most customers stable
            )[0],
            
            # Behavioral risk
            "signup_channel": random.choice(self.signup_channels),
            "verification_level": random.choices(
                self.verification_levels,
                weights=[60, 30, 10]  # Most verified
            )[0]
        }


class ProductRegistry(EntityRegistry):
    """Registry for product entities with BNPL eligibility."""
    
    def __init__(self, max_entities: int = 50_000, seed: Optional[int] = None):
        super().__init__(max_entities, seed)
        
        # BNPL-relevant categories
        self.categories = {
            "electronics": ["smartphones", "laptops", "tablets", "headphones", "cameras"],
            "clothing": ["shoes", "dresses", "jeans", "jackets", "accessories"],
            "home": ["furniture", "appliances", "decor", "bedding", "kitchen"],
            "beauty": ["skincare", "makeup", "haircare", "fragrances", "tools"],
            "sports": ["fitness", "outdoor", "team_sports", "athletic_wear"]
        }
        
        # Price ranges by category (BNPL eligibility often price-dependent)
        self.category_price_ranges = {
            "electronics": (50, 3000),
            "clothing": (25, 500),
            "home": (100, 2000),
            "beauty": (15, 300),
            "sports": (30, 800)
        }
        
        self.brands = ["Apple", "Samsung", "Nike", "Adidas", "IKEA", "Sephora", "Zara", "H&M"]
        self.risk_categories = ["low", "medium", "high"]
    
    def _generate_entity(self, product_id: str) -> Dict[str, Any]:
        category = random.choice(list(self.categories.keys()))
        subcategory = random.choice(self.categories[category])
        min_price, max_price = self.category_price_ranges[category]
        price = round(random.uniform(min_price, max_price), 2)
        
        # BNPL eligibility based on price and category
        bnpl_eligible = price >= 50 and category in ["electronics", "clothing", "home"]
        
        return {
            "product_id": product_id,
            "category": category,
            "subcategory": subcategory,
            "brand": random.choice(self.brands),
            "price": price,
            "bnpl_eligible": bnpl_eligible,
            "risk_category": random.choices(
                self.risk_categories,
                weights=[50, 35, 15]  # Most products low risk
            )[0]
        }


class PaymentMethodRegistry(EntityRegistry):
    """Registry for customer payment methods including BNPL."""
    
    def __init__(self, max_entities: int = 200_000, seed: Optional[int] = None):
        super().__init__(max_entities, seed)
        
        self.bnpl_providers = ["affirm", "klarna", "afterpay", "sezzle"]
        self.credit_limits = [500, 1000, 1500, 2500, 5000]
    
    def _generate_entity(self, payment_method_id: str) -> Dict[str, Any]:
        # Extract customer_id from payment_method_id pattern
        customer_id = payment_method_id.split('_')[0] if '_' in payment_method_id else payment_method_id
        
        return {
            "payment_method_id": payment_method_id,
            "customer_id": customer_id,
            "type": "bnpl_account",
            "provider": random.choice(self.bnpl_providers),
            "credit_limit": random.choice(self.credit_limits),
            "creation_date": self.fake.date_between(start_date="-1y", end_date="today")
        }


class DeviceRegistry(EntityRegistry):
    """Registry for customer devices with trust indicators."""
    
    def __init__(self, max_entities: int = 150_000, seed: Optional[int] = None):
        super().__init__(max_entities, seed)
        
        self.device_types = ["mobile", "desktop", "tablet"]
        self.operating_systems = {
            "mobile": ["iOS", "Android"],
            "desktop": ["Windows", "macOS", "Linux"],
            "tablet": ["iOS", "Android", "Windows"]
        }
    
    def _generate_entity(self, device_id: str) -> Dict[str, Any]:
        device_type = random.choice(self.device_types)
        os_options = self.operating_systems[device_type]
        
        # Trust based on device age (older = more trusted)
        first_seen = self.fake.date_between(start_date="-2y", end_date="today")
        days_old = (date.today() - first_seen).days
        is_trusted = days_old > 30  # Trusted after 30 days
        
        return {
            "device_id": device_id,
            "type": device_type,
            "os": random.choice(os_options),
            "is_trusted": is_trusted,
            "first_seen": first_seen
        }