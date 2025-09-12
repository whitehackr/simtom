import pytest
from datetime import date, datetime

from simtom.core.entities import (
    CustomerRegistry, ProductRegistry, 
    PaymentMethodRegistry, DeviceRegistry
)


def test_customer_registry_basic_operations():
    registry = CustomerRegistry(max_entities=100, seed=42)
    
    # Test get_or_create
    customer1 = registry.get_or_create("test_customer_1")
    customer2 = registry.get_or_create("test_customer_1")  # Same ID
    
    # Should return same customer for same ID
    assert customer1["customer_id"] == customer2["customer_id"]
    assert customer1["email"] == customer2["email"]
    
    # Test different customers
    customer3 = registry.get_or_create("test_customer_2")
    assert customer1["customer_id"] != customer3["customer_id"]


def test_customer_registry_risk_attributes():
    registry = CustomerRegistry(seed=42)
    customer = registry.get_or_create("risk_test_customer")
    
    # Verify all risk attributes are present
    required_fields = [
        "customer_id", "email", "dob", "signup_date",
        "income_bracket", "employment_status", "credit_score_range",
        "country", "state", "zipcode", "address_stability",
        "signup_channel", "verification_level"
    ]
    
    for field in required_fields:
        assert field in customer
    
    # Verify field types and constraints
    assert isinstance(customer["dob"], date)
    assert isinstance(customer["signup_date"], date)
    assert customer["credit_score_range"] in ["excellent", "good", "fair", "poor"]
    assert customer["verification_level"] in ["verified", "partial", "unverified"]
    assert customer["country"] == "US"


def test_product_registry_bnpl_eligibility():
    registry = ProductRegistry(seed=42)
    
    # Generate multiple products to test BNPL eligibility logic
    products = [registry.get_or_create(f"prod_{i}") for i in range(50)]
    
    # Should have mix of BNPL eligible and non-eligible
    bnpl_eligible = [p for p in products if p["bnpl_eligible"]]
    assert len(bnpl_eligible) > 0, "Should have some BNPL eligible products"
    
    # BNPL eligible products should meet criteria
    for product in bnpl_eligible:
        assert product["price"] >= 50, "BNPL products should be >= $50"
        assert product["category"] in ["electronics", "clothing", "home"]


def test_payment_method_registry():
    registry = PaymentMethodRegistry(seed=42)
    
    payment_method = registry.get_or_create("customer1_payment_1")
    
    required_fields = ["payment_method_id", "customer_id", "type", "provider", "credit_limit", "creation_date"]
    for field in required_fields:
        assert field in payment_method
    
    assert payment_method["type"] == "bnpl_account"
    assert payment_method["provider"] in ["affirm", "klarna", "afterpay", "sezzle"]
    assert payment_method["credit_limit"] in [500, 1000, 1500, 2500, 5000]


def test_device_registry_trust_logic():
    registry = DeviceRegistry(seed=42)
    
    device = registry.get_or_create("test_device_1")
    
    required_fields = ["device_id", "type", "os", "is_trusted", "first_seen"]
    for field in required_fields:
        assert field in device
    
    assert device["type"] in ["mobile", "desktop", "tablet"]
    assert isinstance(device["is_trusted"], bool)
    
    # Test OS matching device type
    if device["type"] == "mobile":
        assert device["os"] in ["iOS", "Android"]
    elif device["type"] == "desktop":
        assert device["os"] in ["Windows", "macOS", "Linux"]


def test_registry_max_entities_enforcement():
    registry = CustomerRegistry(max_entities=3, seed=42)
    
    # Add entities up to limit
    customer1 = registry.get_or_create("cust_1")
    customer2 = registry.get_or_create("cust_2") 
    customer3 = registry.get_or_create("cust_3")
    
    assert registry.count() == 3
    
    # Adding 4th should evict oldest
    customer4 = registry.get_or_create("cust_4")
    assert registry.count() == 3
    
    # First customer should be evicted
    assert not registry.exists("cust_1")
    assert registry.exists("cust_4")


def test_registry_deterministic_generation():
    registry1 = CustomerRegistry(seed=42)
    registry2 = CustomerRegistry(seed=42)
    
    customer1 = registry1.get_or_create("test_customer")
    customer2 = registry2.get_or_create("test_customer")
    
    # Same seed should produce identical customers
    assert customer1["email"] == customer2["email"]
    assert customer1["dob"] == customer2["dob"]
    assert customer1["credit_score_range"] == customer2["credit_score_range"]