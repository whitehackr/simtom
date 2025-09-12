from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import random
from faker import Faker

from ...core.generator import BaseGenerator, GeneratorConfig
from ...core.entities import (
    CustomerRegistry, ProductRegistry, 
    PaymentMethodRegistry, DeviceRegistry
)


class BaseEcommerceConfig(GeneratorConfig):
    """Extended configuration for ecommerce generators."""
    
    # Entity pool sizes
    max_customers: int = 10_000
    max_products: int = 5_000
    max_payment_methods: int = 20_000
    max_devices: int = 15_000
    
    # Denormalization level
    denormalize_entities: bool = True  # Flat ML records vs references
    
    # Customer behavior patterns
    repeat_customer_rate: float = 0.7  # 70% of transactions from existing customers
    bnpl_adoption_rate: float = 0.25   # 25% of eligible transactions use BNPL


class BaseEcommerceGenerator(BaseGenerator):
    """Base generator for ecommerce scenarios with entity consistency."""
    
    def __init__(self, config: BaseEcommerceConfig):
        super().__init__(config)
        self.ecom_config = config
        
        # Initialize entity registries
        self.customers = CustomerRegistry(
            max_entities=config.max_customers, 
            seed=config.seed
        )
        self.products = ProductRegistry(
            max_entities=config.max_products,
            seed=config.seed
        )
        self.payment_methods = PaymentMethodRegistry(
            max_entities=config.max_payment_methods,
            seed=config.seed
        )
        self.devices = DeviceRegistry(
            max_entities=config.max_devices,
            seed=config.seed
        )
        
        # Track customer IDs for repeat behavior
        self._known_customer_ids: List[str] = []
    
    def get_or_create_customer(self) -> Dict[str, Any]:
        """Get existing customer or create new one based on repeat rate."""
        
        # Decide if this should be a repeat customer
        if (self._known_customer_ids and 
            random.random() < self.ecom_config.repeat_customer_rate):
            customer_id = random.choice(self._known_customer_ids)
        else:
            # Create new customer
            customer_id = f"cust_{len(self._known_customer_ids) + 1:06d}"
            self._known_customer_ids.append(customer_id)
        
        return self.customers.get_or_create(customer_id)
    
    def get_product(self) -> Dict[str, Any]:
        """Get a random product from catalog."""
        # Generate product ID deterministically for consistency
        product_id = f"prod_{random.randint(1, self.ecom_config.max_products):06d}"
        return self.products.get_or_create(product_id)
    
    def get_payment_method(self, customer_id: str, require_bnpl: bool = False) -> Dict[str, Any]:
        """Get payment method for customer, optionally requiring BNPL."""
        payment_method_id = f"{customer_id}_pm_{random.randint(1, 3)}"
        payment_method = self.payment_methods.get_or_create(payment_method_id)
        
        # Override type if BNPL required
        if require_bnpl:
            payment_method["type"] = "bnpl_account"
        
        return payment_method
    
    def get_device(self, customer_id: str) -> Dict[str, Any]:
        """Get device for customer (customers typically have 1-2 devices)."""
        device_id = f"{customer_id}_device_{random.randint(1, 2)}"
        return self.devices.get_or_create(device_id)
    
    def should_use_bnpl(self, product: Dict[str, Any]) -> bool:
        """Determine if BNPL should be used based on product and adoption rate."""
        if not product.get("bnpl_eligible", False):
            return False
        
        return random.random() < self.ecom_config.bnpl_adoption_rate
    
    def generate_base_transaction(self) -> Dict[str, Any]:
        """Generate base transaction with entity references."""
        
        # Get entities
        customer = self.get_or_create_customer()
        product = self.get_product()
        device = self.get_device(customer["customer_id"])
        
        # Determine payment method
        use_bnpl = self.should_use_bnpl(product)
        payment_method = self.get_payment_method(
            customer["customer_id"], 
            require_bnpl=use_bnpl
        )
        
        # Base transaction data
        transaction = {
            "transaction_id": f"txn_{self._records_generated:08d}",
            "timestamp": datetime.utcnow(),
            "customer_id": customer["customer_id"],
            "product_id": product["product_id"],
            "device_id": device["device_id"],
            "payment_method_id": payment_method["payment_method_id"],
            "amount": product["price"],
            "currency": "USD",
            "status": "completed"
        }
        
        return transaction, customer, product, device, payment_method
    
    def denormalize_transaction(
        self, 
        transaction: Dict[str, Any],
        customer: Dict[str, Any], 
        product: Dict[str, Any],
        device: Dict[str, Any],
        payment_method: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create flat ML-ready record with all entity attributes."""
        
        if not self.ecom_config.denormalize_entities:
            return transaction  # Return normalized (just references)
        
        # Flatten all entities into single record
        denormalized = {
            # Transaction core
            **transaction,
            
            # Customer attributes (prefixed for clarity)
            "customer_age_bracket": self._age_bracket_from_dob(customer["dob"]),
            "customer_tenure_days": (datetime.now().date() - customer["signup_date"]).days,
            "customer_income_bracket": customer["income_bracket"],
            "customer_credit_score_range": customer["credit_score_range"],
            "customer_verification_level": customer["verification_level"],
            "customer_address_stability": customer["address_stability"],
            "customer_state": customer["state"],
            
            # Product attributes
            "product_category": product["category"],
            "product_subcategory": product["subcategory"],
            "product_brand": product["brand"],
            "product_price": product["price"],
            "product_bnpl_eligible": product["bnpl_eligible"],
            "product_risk_category": product["risk_category"],
            
            # Device attributes
            "device_type": device["type"],
            "device_os": device["os"],
            "device_is_trusted": device["is_trusted"],
            
            # Payment method attributes
            "payment_provider": payment_method.get("provider"),
            "payment_type": payment_method["type"],
            "payment_credit_limit": payment_method.get("credit_limit")
        }
        
        return denormalized
    
    def _age_bracket_from_dob(self, dob) -> str:
        """Convert date of birth to age bracket."""
        from datetime import date
        age = (date.today() - dob).days // 365
        
        if age < 25:
            return "18-24"
        elif age < 35:
            return "25-34"  
        elif age < 45:
            return "35-44"
        elif age < 55:
            return "45-54"
        else:
            return "55+"
    
    async def generate_record(self) -> Dict[str, Any]:
        """Override this in specific generators (BNPL, etc.)."""
        transaction, customer, product, device, payment_method = self.generate_base_transaction()
        return self.denormalize_transaction(transaction, customer, product, device, payment_method)