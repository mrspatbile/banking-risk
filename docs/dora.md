# DORA -- Digital Operational Resilience Act

## Legislative Framework

| Instrument | Reference | Status | Content |
|------------|-----------|--------|---------|
| DORA | Regulation (EU) 2022/2554 | **Directly applicable** -- in force 17 January 2025 | ICT risk management, incident reporting, resilience testing, third-party risk |
| DORA Level 2 -- RTS/ITS batch 1 | Commission Delegated/Implementing Regulations 2024 | Directly applicable | ICT risk framework, incident classification, TLPT |
| DORA Level 2 -- RTS/ITS batch 2 | Commission Delegated/Implementing Regulations 2024 | Directly applicable | Third-party register, subcontracting, oversight framework |

**No transposition needed** -- DORA is a Regulation, directly applicable in all
member states including Luxembourg from 17 January 2025.

**Luxembourg:** CSSF Circular 24/847 -- supervisory expectations for DORA
implementation. CSSF is the competent authority for Luxembourg financial entities.

---

## Scope -- Who Is Covered

**Financial entities:**
- Credit institutions, investment firms, payment institutions
- AIFMs, UCITS ManCos, investment firms
- Insurance and reinsurance undertakings
- CCPs, trade repositories, regulated markets
- Crypto-asset service providers (CASPs) under MiCA

**ICT third-party service providers (ICT TPPs):**
- Cloud service providers (AWS, Microsoft Azure, Google Cloud)
- Data analytics providers, software vendors
- Critical ICT TPPs designated by ESAs subject to direct EU oversight

**Proportionality:** microenterprises (< 10 staff, < EUR 2M turnover) apply
simplified requirements.

---

## 1. ICT Risk Management Framework

**DORA Articles 5-16:**

Financial entities must maintain a comprehensive ICT risk management framework:

| Component | Requirement |
|-----------|-------------|
| Governance | Management body accountable for ICT risk -- cannot delegate fully |
| ICT risk strategy | Aligned with business strategy, reviewed annually |
| ICT asset inventory | All ICT assets supporting critical functions identified and classified |
| Protection and prevention | Access controls, encryption, patch management, network security |
| Detection | Continuous monitoring, anomaly detection |
| Response and recovery | Business continuity plans, RTO and RPO defined per critical function |
| Backup and restoration | Regular backups, tested restoration procedures |
| Learning | Post-incident reviews, threat intelligence integration |

**RTO / RPO for critical functions:** recovery time objective and recovery
point objective must be defined, documented, and tested. No prescribed
minimum -- proportionate to criticality.

---

## 2. ICT Incident Reporting

**DORA Articles 17-23:**

### Classification

| Category | Definition |
|----------|-----------|
| Major ICT incident | Meets DORA criteria -- significant impact on services, clients, or financial system |
| Significant cyber threat | Not yet an incident but potential for major impact -- voluntary notification encouraged |

**Major incident criteria (RTS):** combination of thresholds across:
- Number of clients affected
- Duration of service disruption
- Geographic spread
- Data losses
- Reputational, financial, or operational impact
- Criticality of affected services

### Reporting Timeline

| Report | Deadline |
|--------|---------|
| Initial notification | 4 hours after classification as major (24 hours max after detection) |
| Intermediate report | 72 hours after initial notification |
| Final report | 1 month after incident resolution |

**Reported to:** CSSF for Luxembourg entities. CSSF aggregates and reports
to EBA/ESMA/EIOPA. Cross-border incidents -- home NCA coordinates.

---

## 3. Digital Operational Resilience Testing

**DORA Articles 24-27:**

### Basic Testing (all entities)
Annual testing of ICT tools and systems:
- Vulnerability assessments
- Network security scans
- Gap analyses
- Physical security reviews

### Advanced Testing -- TLPT (significant entities only)
**Threat-Led Penetration Testing (TLPT):** simulates real cyberattacks using
intelligence on actual threat actors targeting the financial sector.

| Parameter | Requirement |
|-----------|-------------|
| Frequency | At least every 3 years |
| Scope | Critical live production systems |
| Testers | External certified red team -- TIBER-EU framework |
| Coverage | Must include critical ICT TPPs in scope |
| Result | Remediation plan submitted to NCA |

**TIBER-EU:** ECB framework for threat intelligence-based ethical red teaming --
the methodology underlying TLPT. Already implemented voluntarily by major EU banks
pre-DORA; now mandatory for significant entities.

---

## 4. ICT Third-Party Risk Management

**DORA Articles 28-44:** the most operationally demanding component for most firms.

### Contractual Requirements

All contracts with ICT TPPs supporting critical or important functions must include:

- Full description of services and service levels
- Data location and processing locations
- Access and audit rights for the financial entity and NCA
- Termination rights -- including where ICT TPP is acquired or changes control
- Business continuity obligations of the ICT TPP
- Subcontracting restrictions and notification requirements

### ICT TPP Register

Entities must maintain a complete register of all ICT third-party arrangements,
submitted to NCA on request. EBA developing a central EU register of ICT TPPs.

### Concentration Risk

Entities must assess and manage concentration risk from reliance on:
- Single ICT TPP for multiple critical functions
- Single cloud provider (hyperscaler concentration)
- Geographic concentration of ICT infrastructure

No hard limits prescribed -- qualitative assessment and mitigation required.

### Critical ICT TPP Oversight

ESAs (EBA, ESMA, EIOPA) jointly designate Critical ICT TPPs -- primarily
major cloud providers. Designated Critical ICT TPPs subject to:
- Direct oversight by Lead Overseer (one of the ESAs)
- Annual oversight plans
- Information requests and on-site inspections
- Recommendations -- not binding but non-compliance reported publicly

---

## 5. Information Sharing

**DORA Article 45:** financial entities may share cyber threat information
and intelligence within trusted communities. DORA explicitly permits and
encourages this -- removes legal uncertainty around data sharing for
cybersecurity purposes.

---

## 6. Key Metrics and KPIs

| Metric | Definition | Use |
|--------|-----------|-----|
| RTO | Recovery time objective -- max acceptable downtime per critical function | BCP design, DORA compliance |
| RPO | Recovery point objective -- max acceptable data loss | Backup policy, DORA compliance |
| MTTI | Mean time to identify -- average detection time for incidents | Monitoring effectiveness |
| MTTR | Mean time to recover -- average resolution time | Resilience KPI |
| ICT TPP concentration ratio | % of critical functions dependent on single provider | Concentration risk |
| TLPT findings | Critical and high vulnerabilities identified | Remediation tracking |
| Incident reporting rate | Major incidents reported vs detected | Regulatory compliance |

---

## 7. Interaction with Other Regulation

| Regulation | Interaction |
|------------|-------------|
| NIS2 Directive (EU 2022/2555) | Cybersecurity baseline for all critical sectors -- DORA is lex specialis for financial sector, takes precedence |
| GDPR | ICT incident involving personal data -- parallel DORA incident report and GDPR data breach notification required |
| EMIR | CCPs already subject to operational resilience requirements -- DORA adds harmonised EU-wide framework |
| CRR3 / Basel IV | Operational risk capital covers ICT risk -- DORA adds qualitative resilience requirements on top |
| AIFMD / UCITS | AIFMs and ManCos in scope -- DORA operational risk requirements layer on top of AIFMD organisational requirements |
| MiFID II | Investment firms in scope -- DORA supplements MiFID II organisational and outsourcing requirements |

---

*Regulation references: Regulation (EU) 2022/2554 (DORA),*
*Commission Delegated Regulations 2024/1505 and 2024/1772 (RTS batch 1),*
*Commission Delegated Regulations 2024/2956 and 2024/2957 (RTS batch 2),*
*CSSF Circular 24/847, ECB TIBER-EU Framework.*