# BNPL Data Field Guide

This guide explains the business context and data generation logic for each field in Simtom's BNPL dataset to support ML model development and interpretation.

## Field Categories & Business Context

### Transaction Core

| Field | Type | Business Context |
|-------|------|------------------|
| `transaction_id` | string | Sequential transaction identifier. In production, would be UUID or similar. |
| `amount` | float | Total transaction amount in USD. **Always equals product_price** (BNPL business rule - customers pay exactly what product costs). |
| `_timestamp` | datetime | Transaction completion time. Generated using realistic business hour patterns (70% business hours, 20% evening, 10% night/early morning). |

### Product Information

| Field | Type | Business Context |
|-------|------|------------------|
| `product_category` | string | Primary product classification (electronics, clothing, home, beauty, sports). Distribution reflects e-commerce patterns: electronics 35%, clothing 25%, home 20%, beauty 12%, sports 8%. |
| `product_price` | float | Product retail price. Ranges calibrated for BNPL eligibility: electronics $30-400, clothing $20-150, home $25-300, beauty $15-80, sports $25-200. |
| `product_risk_category` | string | Risk classification determined by product characteristics. **High risk**: easily resold items (electronics, luxury). **Medium risk**: fashion items with return volatility. **Low risk**: everyday consumables. Derived from category, brand, and price analysis. |
| `product_bnpl_eligible` | boolean | BNPL platform eligibility. Based on price threshold ($50+) and category policy. Reflects real platform restrictions. |

### Customer Demographics

| Field | Type | Business Context |
|-------|------|------------------|
| `customer_age_bracket` | string | Age ranges reflect BNPL user demographics. Distribution: 18-24 (12%), 25-34 (35%), 35-44 (28%), 45-54 (15%), 55+ (10%). Younger skew reflects digital payment adoption. |
| `customer_income_bracket` | string | Household income ranges based on US Census distribution: <25k (15%), 25k-50k (28%), 50k-75k (23%), 75k-100k (18%), 100k+ (16%). |
| `customer_credit_score_range` | string | FICO score ranges used by BNPL platforms: **excellent** (750+), **good** (650-749), **fair** (550-649), **poor** (<550). Obtained from credit bureau at account opening. |
| `customer_verification_level` | string | Identity verification completeness. **verified**: Full identity + income verification. **partial**: Basic identity only. **unverified**: Minimal verification. Higher verification = lower risk due to reduced fraud potential. |
| `customer_tenure_days` | int | Days since customer account creation. Longer tenure indicates platform familiarity and payment history establishment. |
| `customer_address_stability` | string | Address change frequency indicator. **stable**: No address changes >12 months. **new**: Recent address change within 3 months. **frequent_mover**: Multiple changes within 12 months. Determined from customer profile updates and shipping address changes. |

### Device & Payment Context

| Field | Type | Business Context |
|-------|------|------------------|
| `device_type` | string | Transaction device type. Realistic distribution: mobile 55%, desktop 30%, tablet 15%. Reflects e-commerce shopping patterns. |
| `device_os` | string | Operating system. Mobile: iOS/Android reflecting market share. Desktop: Windows/macOS/Linux by usage patterns. |
| `device_is_trusted` | boolean | Device recognition status. Devices become "trusted" after 30+ days of usage. Trusted devices indicate lower fraud risk. |
| `payment_credit_limit` | int | BNPL credit limit assigned to customer. Determined by underwriting engine using income, credit score, and platform history. Typical ranges: $500-5000. |

### BNPL Payment Structure

| Field | Type | Business Context |
|-------|------|------------------|
| `installment_count` | int | Number of payment installments. Determined by transaction amount and customer risk profile: <$100 → 4 payments, <$500 → 4-6 payments, <$1000 → 6-12 payments, $1000+ → 12-24 payments. |
| `first_payment_amount` | float | Initial payment due at checkout. Standard BNPL model: 25% of total amount. Some platforms vary by risk assessment. |
| `payment_frequency` | string | Payment schedule. "bi_weekly" is industry standard (every 2 weeks). |

### Risk Assessment & Behavioral Context

| Field | Type | Business Context |
|-------|------|------------------|
| `risk_scenario` | string | Transaction context determined by real-time behavioral analysis. **low_risk_purchase**: Normal browsing and checkout behavior. **impulse_purchase**: Fast checkout with minimal price comparison. **credit_stretched**: Transaction amount near customer's credit limit. **high_risk_behavior**: Multiple risk indicators (rushed checkout, new device, high amount). |
| `risk_score` | float | Pre-transaction risk assessment (0.0-1.0). Calculated by platform's underwriting engine using weighted factors: credit score (30%), verification level (20%), income bracket (20%), device trust (10%), product risk (10%), transaction context (10%). This is a basic screening score - ML models would provide more sophisticated risk assessment. |
| `risk_level` | string | Risk score categorization. **low** (<0.3), **medium** (0.3-0.6), **high** (0.6-0.8), **very_high** (0.8+). Used for business rule application and reporting. |

### Transaction Behavioral Indicators

| Field | Type | Business Context |
|-------|------|------------------|
| `purchase_context` | string | Purchase decision context. **impulse**: Fast decision with limited research. **rushed**: Quick checkout under time pressure. **normal**: Standard shopping behavior. Derived from time spent browsing and checkout speed. |
| `checkout_speed` | string | Checkout completion speed. **very_fast** (<30 seconds), **fast** (30-60 seconds), **normal** (1-5 minutes), **slow** (>5 minutes). Measured from cart to payment completion. |
| `cart_abandonment_count` | int | Number of previous abandoned carts for this customer session. Higher counts may indicate purchase hesitation or price sensitivity. |
| `price_comparison_time` | int | Seconds spent on price comparison activities. Tracked through user behavior analytics. Lower times correlate with impulse purchases. |
| `time_on_site_seconds` | int | Total session time before purchase. Measured from site entry to transaction completion. Very low times (high_risk_behavior scenario) indicate rushed decisions. |
| `credit_utilization` | float | Transaction amount as percentage of available credit limit. Higher utilization indicates greater financial strain. |

### Economic Context

| Field | Type | Business Context |
|-------|------|------------------|
| `economic_stress_factor` | float | Macroeconomic stress indicator (0.0 = normal economy, 1.0 = recession). Affects default rate modeling and risk adjustments. |

### ML Target Variables

| Field | Type | Business Context |
|-------|------|------------------|
| `will_default` | boolean | Whether customer will miss payments on this transaction. Simulated using risk-adjusted base default rate (3% baseline, scaled by risk score). Primary classification target for ML models. |
| `days_to_first_missed_payment` | int/null | Days until first missed payment occurs (null if no default). Useful for time-to-event modeling and early intervention systems. |

## Key Business Insights

### Risk Assessment Pipeline
1. **Real-time context detection** → `risk_scenario` (behavioral analysis)
2. **Basic underwriting** → `risk_score` (rule-based engine)
3. **ML enhancement** → Advanced models using all features
4. **Decision engine** → Approval/denial with terms

### Model Interpretation Guidelines

**Pre-transaction Features**: All customer demographics, device info, and product attributes are available at decision time.

**Transaction Context**: Risk scenario and behavioral indicators are derived from real-time user behavior during the shopping session.

**Perfect Correlations**: `amount` = `product_price` always (BNPL business constraint).

**Natural Correlations**: Credit score ↔ default rate (strong), age ↔ product preferences (moderate), income ↔ spending (weak).

### Feature Engineering Recommendations

**Time-based**: Extract seasonality, day-of-week, and holiday effects from `_timestamp`.

**Risk combinations**: Combine credit score + verification level, device trust + tenure.

**Behavioral patterns**: Ratio features like `first_payment_amount/amount`, `time_on_site_seconds/price_comparison_time`.

**Customer history**: Aggregate features by `customer_id` for repeat customer analysis.

---

This data represents realistic BNPL transaction patterns with proper business logic and industry-standard risk assessment practices.