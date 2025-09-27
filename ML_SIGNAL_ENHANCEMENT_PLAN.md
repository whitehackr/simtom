# ML Signal Enhancement Plan: Architectural Decision Framework

**Date**: September 27, 2025

## Executive Summary

The Flit team's assessment has identified a fundamental disconnect between our data generation approach and machine learning requirements. This document provides a comprehensive analysis of the statistical, architectural, and modeling decisions required to transform Simtom into a production-ready ML training data platform. We evaluate two distinct architectural approaches and their implications for data quality, system reliability, and long-term maintainability.

## Root Cause Analysis: Where We Went Wrong

### The Signal Destruction Problem

Machine learning models require **predictive relationships** between features and target variables. Our current approach inadvertently destroys these relationships through over-randomization. Consider the fundamental difference:

**What we built**: Statistical realism through variance injection
- Generate risk_score based on customer attributes
- Add "realistic" noise to prevent deterministic correlations
- Generate default outcome with additional randomization
- Result: Feature-target correlations ~0.05 (essentially random)

**What ML needs**: Causal relationships with controlled noise
- Generate customer financial health as latent factor
- Derive risk_score, credit_score, income from latent factor with limited noise
- Generate default outcome primarily from latent factor
- Result: Feature-target correlations 0.30-0.55 (learnable patterns)

### The Behavioral Consistency Crisis

Real customers exhibit **temporal consistency** in their financial behavior. Our current per-transaction generation creates impossible scenarios:

- Customer defaults on transaction A at 10:00 AM
- Same customer successfully completes transaction B at 10:15 AM
- Customer defaults again on transaction C at 11:30 AM

This violates fundamental assumptions of risk modeling: **default is a customer state, not a transaction characteristic**.

### The Frequency Reality Gap

Our repeat customer rate of 70% combined with hourly generation creates customers transacting 720+ times per day. Real BNPL customers transact 1-4 times per month. This frequency distortion makes temporal pattern learning impossible.

## Statistical Modeling Fundamentals

### Correlation vs Causation in Synthetic Data

The challenge of synthetic data generation is creating **correlation that mimics causation** without explicit causal modeling. Two approaches exist:

**Approach 1: Correlation Injection**
Generate features independently, then mathematically adjust to achieve target correlations. This is mathematically complex and can create unrealistic feature combinations.

**Approach 2: Latent Factor Modeling**
Generate underlying latent factors (like "financial health"), then derive all observable features from these factors. This naturally creates realistic correlations.

### Multivariate Relationship Management

Real financial data exhibits complex interdependencies:
- Credit score correlates with income (+0.65)
- Income inversely correlates with debt-to-income ratio (-0.70)
- Credit score inversely correlates with default probability (-0.42)
- Age moderately correlates with income (+0.25)

Managing these relationships simultaneously requires either:
1. **Covariance matrix generation**: Sample from multivariate distributions
2. **Hierarchical generation**: Generate in dependency order with controlled noise
3. **Iterative adjustment**: Generate, measure, adjust until targets achieved

### Time Series Considerations for Customer Behavior

Customer financial health evolves over time following predictable patterns:
- **Stress accumulation**: Financial pressure builds gradually
- **Event-driven changes**: Job loss, medical expenses trigger rapid deterioration
- **Recovery patterns**: Financial rehabilitation follows characteristic curves
- **Seasonal effects**: Holiday spending, tax refunds create predictable cycles

## Architectural Decision Framework

### Option 1: Enhanced Current Architecture with Redis State Management

**Core Philosophy**: Evolutionary enhancement maintaining current FastAPI streaming approach while adding customer state persistence for correlation preservation.

#### Statistical Modeling Approach

**Latent Factor Generation**: Instead of independent feature generation, implement hierarchical customer profiling:

1. **Base Financial Health Score**: Primary latent factor (0.0-1.0)
2. **Derived Primary Features**: Credit score, income, age derived from base score with controlled noise
3. **Derived Secondary Features**: Risk scores, debt ratios computed from primary features
4. **Target Variable**: Default probability primarily determined by financial health score

This approach ensures **mathematical correlation preservation** while maintaining interpretable relationships between features.

#### State Management Strategy

**Customer State Persistence**: Redis-backed customer profiles that maintain:
- Current financial health score and trajectory
- Transaction frequency budget and last transaction timestamp
- Default state (healthy/stressed/defaulted) with cascade implications
- Historical transaction patterns for realistic progression

**Temporal Evolution Modeling**: Customer financial health evolves based on:
- **Natural drift**: Gradual changes following Brownian motion patterns
- **Transaction impact**: Purchase amounts relative to income affect stress levels
- **External factors**: Economic conditions, seasonal patterns influence all customers
- **Recovery patterns**: Post-stress financial rehabilitation follows empirical curves

#### Transaction Frequency Management

**Budget-Based Approach**: Each customer allocated realistic monthly transaction budget based on:
- Income level (higher income → more frequent transactions)
- Age demographics (younger customers more active)
- Credit score (better credit → higher confidence)
- Historical patterns (existing customers follow established frequency)

**Temporal Spacing**: Transactions distributed using realistic inter-arrival patterns rather than uniform hourly generation.

#### Advantages of Enhanced Current Architecture

**Implementation Continuity**: Builds directly on existing codebase with minimal disruption to current API contracts and deployment infrastructure.

**Proven Technology Stack**: Redis provides battle-tested state management with excellent performance characteristics and mature monitoring tools.

**Gradual Migration Path**: Can implement enhancements incrementally, validating improvements at each stage without complete system overhaul.

**Operational Familiarity**: Team already understands FastAPI patterns, database interactions, and streaming response management.

#### Challenges of Enhanced Current Architecture

**Correlation Complexity**: Managing multivariate correlations across thousands of features requires sophisticated mathematical modeling and continuous validation.

**State Synchronization**: Distributed generation requires careful coordination to prevent race conditions and ensure consistent customer state updates.

**Memory Scaling**: Customer state storage grows linearly with customer base, requiring capacity planning and potential data retention policies.

**Mathematical Edge Cases**: Correlation targets may conflict mathematically, requiring priority hierarchies and compromise trade-offs.

### Option 2: SimPy Discrete Event Simulation Architecture

**Core Philosophy**: Fundamental paradigm shift to event-driven simulation where customers are autonomous agents with realistic temporal behavior patterns.

#### Simulation Modeling Approach

**Customer as Agent**: Each customer represents an independent process with internal state and decision-making logic:
- **Financial health evolution**: Continuous background process updating stress levels
- **Transaction decision making**: Probabilistic decisions based on current state and external factors
- **Life event processing**: Major events (job loss, medical expenses) trigger state changes
- **Behavioral adaptation**: Transaction patterns evolve based on past outcomes

**Emergent Correlation**: Rather than forcing correlations, allow realistic customer behavior to naturally create the statistical relationships observed in real data.

#### Event-Driven Architecture

**Natural Temporal Patterns**: SimPy's event scheduling creates realistic temporal distribution automatically:
- Customers naturally space transactions based on financial capacity
- Default cascades occur organically when financial stress exceeds thresholds
- Seasonal patterns emerge from collective customer behavior responses
- Economic stress periods affect all customers simultaneously but differently

**System Events**: Global events affect all customers simultaneously:
- **Economic cycles**: Recession periods increase stress for all customer segments
- **Seasonal patterns**: Holiday spending, back-to-school periods drive transaction volume
- **Regulatory changes**: Interest rate changes affect customer borrowing behavior
- **Market events**: Major economic announcements influence consumer confidence

#### Advantages of SimPy Architecture

**Statistical Naturalness**: Correlations emerge naturally from realistic behavior modeling rather than artificial injection, creating more authentic feature relationships.

**Temporal Realism**: Event-driven simulation naturally creates realistic spacing, frequency patterns, and temporal dependencies without explicit frequency management.

**Behavioral Authenticity**: Customer behavior follows realistic decision-making patterns, creating authentic edge cases and behavioral diversity.

**Scalability Simplicity**: Each customer runs independently, enabling straightforward parallel processing and horizontal scaling.

**Causal Clarity**: Clear separation between customer state, decision processes, and environmental factors makes system behavior interpretable and debuggable.

#### Challenges of SimPy Architecture

**Paradigm Shift Complexity**: Complete architectural overhaul requires significant development effort and team learning curve for event-driven simulation concepts.

**Performance Characteristics**: Simulation overhead may impact generation throughput, requiring careful optimization for real-time streaming requirements.

**Deterministic Reproducibility**: Ensuring consistent output across simulation runs requires careful seed management and event ordering strategies.

**Integration Complexity**: Current FastAPI streaming infrastructure requires redesign to accommodate event-driven generation patterns.

**Debugging Complexity**: Emergent behavior can be difficult to debug when correlations don't meet targets, requiring simulation analysis tools.

## Technical Implementation Considerations

### Data Quality Measurement and Validation

Both architectures require robust validation frameworks to ensure ML readiness:

**Correlation Monitoring**: Continuous measurement of feature-target relationships with automated alerting when correlations drift outside acceptable ranges.

**Distribution Validation**: Statistical tests comparing generated data distributions against target distributions derived from financial literature and industry benchmarks.

**Edge Case Detection**: Identification of impossible or highly unlikely feature combinations that could confuse ML models.

**Temporal Consistency Checks**: Validation that customer behavior follows realistic temporal patterns without impossible state transitions.

### Performance and Scaling Architecture

**Redis-Enhanced Approach Scaling**:
- Customer state lookups: ~2ms latency impact per transaction
- Memory requirements: ~5KB per customer, linear scaling with customer base
- Throughput bottleneck: Redis cluster performance (~300K ops/second)
- Scaling strategy: Redis clustering with customer-based sharding

**SimPy Approach Scaling**:
- Simulation overhead: ~10-50ms per customer event depending on complexity
- Memory requirements: Python object overhead for customer agents
- Throughput bottleneck: Event processing and Python GIL limitations
- Scaling strategy: Process-based parallelization with customer segmentation

### Operational Complexity Assessment

**Redis-Enhanced Operational Requirements**:
- Infrastructure: Redis cluster deployment, monitoring, backup/recovery
- Monitoring: Customer state drift, correlation validation, performance metrics
- Debugging: State inspection tools, correlation analysis dashboards
- Maintenance: Redis upgrades, capacity planning, data retention policies

**SimPy Operational Requirements**:
- Infrastructure: Simulation runtime management, event queue monitoring
- Monitoring: Simulation performance, convergence validation, agent behavior analysis
- Debugging: Simulation replay tools, agent state inspection, event tracing
- Maintenance: Simulation parameter tuning, agent behavior updates

## Decision Matrix and Recommendations

### Evaluation Criteria

**ML Performance Impact**: Ability to achieve target feature-target correlations and support viable model training
**Implementation Risk**: Development complexity, timeline, and probability of successful deployment
**Operational Overhead**: Long-term maintenance, monitoring, and scaling requirements
**Team Capability**: Alignment with current team skills and infrastructure familiarity

### Short-Term Recommendation: Enhanced Redis Architecture

For immediate ML signal enhancement, the Redis-based approach offers the optimal balance of impact and feasibility:

**Rationale**: The Flit team needs ML-viable data within 4-6 weeks. The Redis enhancement builds directly on existing architecture with proven technology components. While more complex than current implementation, it leverages team expertise and existing infrastructure.

**Risk Mitigation**: Incremental implementation allows validation at each stage. If correlation management proves too complex, individual components (frequency limiting, default cascades) still provide significant improvement over current state.

### Long-Term Strategic Direction: SimPy Migration Evaluation

The SimPy approach represents the theoretically superior solution for authentic financial behavior simulation:

**Evaluation Timeline**: After Redis enhancements demonstrate improved ML performance, allocate 2-3 month evaluation period for SimPy proof-of-concept focusing on:
- Correlation achievement through emergent behavior
- Performance characteristics for real-time streaming
- Integration complexity with existing API infrastructure
- Team learning curve and development velocity

**Migration Decision Criteria**: SimPy migration justified if proof-of-concept demonstrates:
- Superior correlation stability with less manual tuning
- Comparable or better performance characteristics
- Clearer behavioral interpretability for business stakeholders
- Reasonable migration effort from enhanced Redis architecture

## Implementation Roadmap

### Phase 1: Critical Signal Enhancement (Weeks 1-4)
Implement core Redis-based enhancements addressing Flit team's immediate blocking issues:
- Customer state persistence for behavioral consistency
- Transaction frequency limiting for realistic temporal patterns
- Default cascade modeling for customer-level state coherence
- Basic correlation monitoring and validation

### Phase 2: Statistical Sophistication (Weeks 5-8)
Enhance statistical modeling for production ML requirements:
- Multivariate correlation management using latent factor modeling
- Dynamic correlation adjustment based on validation feedback
- Temporal evolution patterns for customer financial health
- Comprehensive edge case handling and validation

### Phase 3: Production Hardening (Weeks 9-12)
Operational readiness for production ML training data generation:
- Performance optimization and scaling validation
- Comprehensive monitoring and alerting infrastructure
- Documentation and team training for operational procedures
- Integration testing with Flit team ML pipeline

### Phase 4: SimPy Evaluation (Months 4-6)
Parallel evaluation track for long-term architectural evolution:
- SimPy proof-of-concept development
- Performance and correlation quality comparison
- Migration effort assessment and business case development
- Strategic decision on architectural direction

## Success Metrics and Validation Framework

### ML Performance Targets
- Feature-target correlations achieve ranges specified by Flit team (0.30-0.55)
- Model AUC-ROC improvement from 0.615 to >0.75
- Algorithm differentiation demonstrating learnable signal variance
- High-confidence prediction capability >80% (vs current 31.5%)

### Behavioral Realism Targets
- Customer transaction frequency: 1-4 per month (realistic BNPL patterns)
- Default state consistency: Zero impossible default pattern scenarios
- Temporal spacing: Natural distribution of inter-transaction intervals
- Lifecycle progression: Authentic customer financial health evolution

### System Performance Targets
- Generation throughput: Maintain >1000 transactions/second
- Latency impact: <5ms additional latency per transaction for state management
- Memory efficiency: <10GB total memory for 1M customer state management
- Reliability: 99.9% uptime with graceful degradation for infrastructure failures

## Conclusion

The enhancement of Simtom for ML training data represents a fundamental shift from demographic realism to statistical relationship authenticity. Both architectural approaches offer viable paths forward, with the Redis-enhanced approach providing immediate relief for blocking ML development issues while the SimPy approach offers superior long-term potential for authentic behavioral simulation.

The key insight from the Flit team's assessment is that synthetic data quality for ML requires **signal preservation over variance injection**. Our current approach optimized for statistical distribution matching while inadvertently destroying the causal relationships that enable model learning.

Success requires balancing multiple competing objectives: correlation strength for ML viability, behavioral authenticity for business relevance, system performance for operational requirements, and implementation feasibility for delivery timelines. The recommended phased approach allows iterative validation and course correction while maintaining momentum toward production-ready ML training data generation.

The decision framework presented here provides the foundation for architectural evolution that can adapt to changing requirements while maintaining the core mission: generating synthetic data so realistic it enables production machine learning model development for financial risk assessment.

---

**Next Steps**: Technical team review and stakeholder alignment on architectural direction and implementation timeline
**Priority**: CRITICAL - ML training data quality directly blocks production model development