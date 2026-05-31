# Banking Regulation Reference -- Quant Risk Engine

A concise reference covering the main prudential and market risk regulations
applicable to EU banks, with focus on quantitative implementation.

---

## 1 The Basel Framework

The Basel Accords are international banking standards published by the
**Basel Committee on Banking Supervision (BCBS)** at the Bank for
International Settlements (BIS) in Basel, Switzerland. They are not
directly binding -- they become law when transposed into local regulation
(CRR/CRD in the EU).

| Version | Year | Key innovations |
|---------|------|----------------|
| Basel I | 1988 | First capital adequacy framework -- 8% minimum capital ratio |
| Basel II | 2004 | Three pillars, internal ratings, operational risk |
| Basel III | 2010 | Post-GFC response -- liquidity ratios (LCR, NSFR), leverage ratio, capital buffers |
| Basel IV (BCBS d424) | 2017 | Output floor, FRTB, revised SA for credit risk, finalised in 2017, implemented 2025 |

### Three Pillars

| Pillar | Content |
|--------|---------|
| Pillar 1 | Minimum capital requirements -- credit, market, operational risk |
| Pillar 2 | Supervisory review -- ICAAP, ILAAP, SREP |
| Pillar 3 | Market discipline -- public disclosure requirements |

---

## 2 EU Implementation -- CRR/CRD Framework

| Regulation | Year | Content |
|------------|------|---------|
| CRR1 / CRD4 | 2013 | Basel III transposition into EU law |
| CRR2 / CRD5 | 2019 | FRTB market risk framework, NSFR, leverage ratio |
| CRR3 / CRD6 | 2024 | Basel IV -- FRTB SA mandatory, output floor, credit risk SA revision |

**CRR3 key dates:**
- Published: June 2024 (Regulation EU 2024/1623)
- Application: January 2025 (phased)
- Output floor: 72.5% of SA capital by 2030

<small><i>

- CRR: Capital Risk Regulation
- CRD: Capital Risk Directiv
</i></small>
---

## 3 Capital Requirements -- Pillar 1

### 3.1 Capital Ratios

$$\text{CET1 ratio} = \frac{\text{Common Equity Tier 1}}{\text{Risk Weighted Assets}} \geq 4.5\%$$

$$\text{Tier 1 ratio} = \frac{\text{Tier 1 Capital}}{\text{Risk Weighted Assets}} \geq 6\%$$

$$\text{Total Capital ratio} = \frac{\text{Total Capital}}{\text{Risk Weighted Assets}} \geq 8\%$$

### 3.2 Capital Buffers (on top of minimums)

| Buffer | Rate | Trigger |
|--------|------|---------|
| Capital Conservation Buffer | 2.5% | Automatic restrictions on distributions if breached |
| Countercyclical Buffer (CCyB) | 0-2.5% | Set by national authority (CSSF for Luxembourg) |
| G-SII / O-SII Buffer | 1-3.5% | For systemically important institutions |
| Systemic Risk Buffer | 1-3% | National discretion |

### 3.3 Tier 1 Capital Components

| Component | Description | Instrument |
|-----------|--|---------|
| CET1 | Common Equity Tier1 | Ordinary shares, share premium, retained earnings, other comprehensive income |
| AT1 | Additional Tier 1 | Perpetual instruments -- CoCo bonds (write-down or conversion trigger) |
| Tier 2 |  | Subordinated debt, general provisions |

---

## 4 Market Risk -- FRTB

**FRTB** = Fundamental Review of the Trading Book (BCBS d352/d457)
Implemented in EU via CRR3 (mandatory from 2025).

### 4.1 Trading Book vs Banking Book

| Book | Instruments | Capital treatment |
|------|-------------|------------------|
| Trading book | Held for short-term trading, market making | FRTB market risk capital |
| Banking book | Held to maturity, loans, deposits | Credit risk capital + IRRBB |

The boundary is strictly defined -- misclassification triggers capital add-ons.

### 4.2 FRTB Approaches

| Approach | Description | Who uses it |
|----------|-------------|-------------|
| Standardised Approach (SA) | Prescriptive sensitivity-based method | All banks (mandatory fallback) |
| Internal Models Approach (IMA) | Bank's own ES model, per-desk approval | Large banks with regulatory approval |

**Output floor:** IMA capital cannot be less than 72.5% of SA capital.

### 4.3 FRTB SA -- Sensitivities-Based Method

Three components per risk class:

| Component | Description | Formula |
|-----------|-------------|---------|
| Delta | Sensitivity to risk factor level | $\sum_k s_k \cdot RW_k$ aggregated with correlations |
| Vega | Sensitivity to implied volatility | Same structure as delta |
| Curvature | Non-linear risk (options) | Scenario-based, uses stressed sensitivities |

### 4.4 FRTB Risk Classes

| Risk class | Abbreviation | Risk factors |
|------------|-------------|-------------|
| General Interest Rate Risk | GIRR | OIS curves, government curves per currency |
| Credit Spread Risk -- non-securitisation | CSR-NS | Corporate bond spreads by rating/sector |
| Credit Spread Risk -- securitisation | CSR-SNC | ABS, CLO tranches |
| Equity Risk | EQ | Equity spot, repo, implied vol |
| Commodity Risk | COM | Commodity spot, forward curve |
| Foreign Exchange Risk | FX | Spot FX rates |

### 4.5 GIRR -- Key Rate Sensitivity

GIRR delta is the sensitivity of instrument NPV to a 1bp move at each
prescribed tenor vertex:

**Prescribed FRTB GIRR vertices:**
0.25Y, 0.5Y, 1Y, 2Y, 3Y, 5Y, 10Y, 15Y, 20Y, 30Y

$$s_k = \frac{\partial V}{\partial r_k} \cdot 0.0001$$

Where $r_k$ is the risk-free rate at vertex $k$.

**Risk weights by tenor (EUR, GIRR):**

| Tenor | Risk weight |
|-------|------------|
| 0.25Y | 1.7% |
| 0.5Y | 1.7% |
| 1Y | 1.6% |
| 2Y | 1.3% |
| 3Y | 1.2% |
| 5Y | 1.1% |
| 10Y | 1.1% |
| 15Y | 1.1% |
| 20Y | 1.1% |
| 30Y | 1.1% |

### 4.6 FRTB IMA -- Expected Shortfall

IMA uses **Expected Shortfall (ES)** at 97.5% confidence over 10 days,
replacing the old 99% VaR over 10 days:

$$ES_{97.5\%} = -\frac{1}{1-0.975} \int_0^{0.025} VaR_u \, du$$

ES is computed on:
- **Current period** -- 12-month observation window
- **Stressed period** -- worst 12-month window since 2007

Capital = $\max(ES_t, m_c \cdot \bar{ES})$ where $m_c \geq 1.5$ is the
multiplier (increases with backtesting exceptions).

---

## 5 Interest Rate Risk in the Banking Book -- IRRBB

### 5.1 Regulatory Framework

| Regulation | Content |
|------------|---------|
| EBA/GL/2022/14 | IRRBB guidelines -- identification, measurement, management |
| EBA/RTS/2022/09 | Standardised approach (SA) -- OIS discounting, 19 buckets |
| EBA/RTS/2022/10 | Supervisory Outlier Tests (SOT) -- EVE 15%, NII 5% |

### 5.2 Six Prescribed Shock Scenarios

| Scenario | Description |
|----------|-------------|
| Parallel up | Uniform shift up across all maturities |
| Parallel down | Uniform shift down across all maturities |
| Steepener | Short rates down, long rates up |
| Flattener | Short rates up, long rates down |
| Short rate up | Shock at short end, fading to zero at 20Y |
| Short rate down | Negative shock at short end, fading to zero at 20Y |

**EBA Annex I shock sizes (bps):**

| Currency | Parallel | Short | Long |
|----------|----------|-------|------|
| EUR | 200 | 250 | 100 |
| USD | 200 | 300 | 150 |
| GBP | 250 | 300 | 150 |
| JPY | 100 | 100 | 100 |
| CHF | 100 | 150 | 100 |

**Post-shock floor (Article 4 EBA/RTS/2022/10):**

$$floor(T) = -150\text{bps} + 3\text{bps} \times T$$

### 5.3 Economic Value of Equity (EVE)

$$EVE = PV(\text{assets}) - PV(\text{liabilities})$$

$$\Delta EVE = \sum_i CF_i \cdot \left[ P_{shocked}(0,T_i) - P_{base}(0,T_i) \right]$$

**EVE Supervisory Outlier Test:**

$$\frac{|\Delta EVE|}{Tier\,1\,capital} > 15\% \Rightarrow \text{outlier}$$

### 5.4 Net Interest Income (NII)

NII measures interest income over a 1-year horizon under shocked rates.
Fixed rate positions keep their rate. Floating rate positions reprice
at the forward rate implied by the shocked OIS curve at each reset date.

**NII Supervisory Outlier Test (operational since 2024):**

$$\frac{|\Delta NII|}{Tier\,1\,capital} > 5\% \Rightarrow \text{outlier}$$

Only parallel up and parallel down scenarios apply to the NII SOT.

### 5.5 EBA 19 Maturity Buckets

| Bucket | Range | Bucket | Range |
|--------|-------|--------|-------|
| 1 | Overnight | 11 | >4Y-5Y |
| 2 | >1D-1M | 12 | >5Y-6Y |
| 3 | >1M-3M | 13 | >6Y-7Y |
| 4 | >3M-6M | 14 | >7Y-8Y |
| 5 | >6M-9M | 15 | >8Y-9Y |
| 6 | >9M-1Y | 16 | >9Y-10Y |
| 7 | >1Y-1.5Y | 17 | >10Y-15Y |
| 8 | >1.5Y-2Y | 18 | >15Y-20Y |
| 9 | >2Y-3Y | 19 | >20Y |
| 10 | >3Y-4Y | | |

Equity is slotted in bucket 19 (>20Y) so the repricing gap sums to zero.

### 5.6 Behavioural Modelling

Key behavioural assumptions required by EBA:

| Item | EBA constraint |
|------|---------------|
| NMD core component | Maximum 50-90% of total NMDs |
| NMD average maturity | Maximum 4-5 years for core component |
| Prepayment scalars | 0.8x and 1.2x applied to baseline estimates |
| Early redemption scalars | 0.8x and 1.2x applied to baseline estimates |


NMD: Non-Maturity Deposits. These are deposits that have no contractual maturity date. The depositor can withdraw at any time.
Examples:
- Current accounts: Day-to-day transaction accounts -- can be withdrawn instantly
- Savings accounts: No fixed term -- variable rate, withdrawable on demandSight deposits
- Overnight deposits -- no fixed maturity
- Retail NMDs: Personal current and savings accounts
- Wholesale NMDs: Corporate current accounts, financial institution deposits

Why NMDs are complex for IRRBB:
Contractually they reprice overnight -- the bank could change the rate tomorrow and the depositor could withdraw tomorrow. This suggests they should sit in bucket 1 (overnight) of the EBA repricing gap.
But behaviourally they are much **stickier**. Retail customers rarely move their savings accounts even when rates change. Empirically a large portion of NMD balances stays with the bank for years -- this is the core component.


The EBA constraints:

Core component -- the stable portion unlikely to leave even under rate stress. EBA caps this at 50-90% of total NMDs depending on the deposit type
Average maturity cap -- the core component cannot be modelled with an average maturity longer than 4-5 years
Non-core component -- the volatile portion, slotted in bucket 1



---

## 6 Liquidity Risk -- LCR and NSFR

### 6.1 Liquidity Coverage Ratio (LCR)

Ensures sufficient High Quality Liquid Assets (HQLA) to survive a
30-day stress scenario:

$$LCR = \frac{HQLA}{Net\,Cash\,Outflows_{30\,days}} \geq 100\%$$

**HQLA levels:**

| Level | Assets | Haircut |
|-------|--------|---------|
| Level 1 | Central bank reserves, sovereign bonds (0% RW) | 0% |
| Level 2A | Sovereign bonds (20% RW), covered bonds (AA-) | 15% |
| Level 2B | RMBS, corporate bonds (BBB-), equities | 25-50% |

### 6.2 Net Stable Funding Ratio (NSFR)

Ensures stable funding over a 1-year horizon:

$$NSFR = \frac{Available\,Stable\,Funding}{Required\,Stable\,Funding} \geq 100\%$$

---

## 7 ICAAP and ILAAP -- Pillar 2

### 7.1 ICAAP -- Internal Capital Adequacy Assessment Process

The bank's own assessment of capital adequacy under Pillar 2.
Submitted annually to the regulator (CSSF in Luxembourg).

**Key components:**

| Component | Description |
|-----------|-------------|
| Business model analysis | Sustainability of earnings, strategic risks |
| Risk identification | All material risks including Pillar 2 risks |
| Capital quantification | Economic capital per risk type |
| Stress testing | Adverse scenario capital impact |
| Capital planning | Forward-looking capital adequacy |

**Pillar 2 risks not covered by Pillar 1:**

| Risk | Description |
|------|-------------|
| IRRBB | Interest rate risk in the banking book |
| Concentration risk | Single name, sector, geographic concentrations |
| Pension risk | Defined benefit pension fund obligations |
| Strategic risk | Business model viability |
| Reputational risk | Brand and franchise risk |

**Economic capital models:**

| Risk type | Common approach |
|-----------|----------------|
| Credit risk | IRB, CreditMetrics, Merton model |
| Market risk | Historical simulation VaR, ES |
| IRRBB | EVE sensitivity, NII at risk |
| Operational risk | AMA, loss distribution approach |

**RAROC -- Risk-Adjusted Return on Capital:**

$$RAROC = \frac{Revenue - Expected\,Loss - Costs}{Economic\,Capital}$$

Target RAROC typically set above the cost of equity (WACC).

### 7.2 ILAAP -- Internal Liquidity Adequacy Assessment Process

The bank's own assessment of liquidity adequacy under Pillar 2.

**Key components:**

| Component | Description |
|-----------|-------------|
| Liquidity risk appetite | Board-approved liquidity risk tolerance |
| Liquidity buffer | Surplus HQLA above LCR minimum |
| Survival horizon | Days of survival under stress without market access |
| Funding diversification | Concentration by counterparty, instrument, currency |
| Intraday liquidity | Real-time liquidity management |
| Contingency funding plan | Actions under liquidity stress |

**Survival horizon analysis:**

$$\text{Survival days} = \frac{\text{Liquidity buffer}}{\text{Daily net cash outflow under stress}}$$

Regulators typically expect a minimum survival horizon of 30 days
(aligned with LCR) with an internal target of 90+ days.

---

## 8 XVA -- Valuation Adjustments

Post-2008 derivatives pricing includes multiple valuation adjustments:

| Adjustment | Abbreviation | Description |
|------------|-------------|-------------|
| Credit Valuation Adjustment | CVA | Cost of counterparty default risk |
| Debit Valuation Adjustment | DVA | Benefit of own default risk |
| Funding Valuation Adjustment | FVA | Cost of funding uncollateralised derivatives |
| Margin Valuation Adjustment | MVA | Cost of posting initial margin |
| Capital Valuation Adjustment | KVA | Cost of regulatory capital held against derivatives |

**CVA formula:**

$$CVA = (1 - R) \int_0^T EE(t) \cdot dPD(t)$$

Where:
- $EE(t)$ -- Expected Exposure at time $t$
- $PD(t)$ -- Probability of default by time $t$
- $R$ -- Recovery rate

**EMIR impact on XVA:**
- Cleared trades: VM posted daily eliminates CVA, but MVA applies
- Non-cleared trades: bilateral CSA drives FVA and MVA
- OIS discounting mandatory for collateralised derivatives

---

## 9 Key Metrics Reference

| Metric | Formula | Regulatory use |
|--------|---------|---------------|
| DV01 / PV01 | $ModDuration \times P \times 0.0001$ | FRTB GIRR delta, IRRBB |
| Modified Duration | $-\frac{1}{P}\frac{\partial P}{\partial y}$ | UCITS global exposure |
| Convexity | $\frac{1}{P}\frac{\partial^2 P}{\partial y^2}$ | FRTB curvature |
| VaR (99%, 10d) | Historical / parametric / MC | Legacy market risk |
| ES (97.5%, 10d) | $E[L \| L > VaR_{97.5\%}]$ | FRTB IMA |
| LCR | HQLA / Net outflows (30d) | Liquidity Pillar 1 |
| NSFR | ASF / RSF | Liquidity Pillar 1 |
| CET1 ratio | CET1 / RWA | Capital Pillar 1 |
| RAROC | (Revenue - EL - Costs) / EC | ICAAP Pillar 2 |
| EVE SOT | $\|\Delta EVE\|$ / Tier 1 > 15% | IRRBB |
| NII SOT | $\|\Delta NII\|$ / Tier 1 > 5% | IRRBB |

---

## 10 SREP -- Supervisory Review and Evaluation Process

The annual supervisory assessment conducted by the regulator (CSSF/ECB)
that determines Pillar 2 capital and liquidity add-ons.

**SREP elements:**

| Element | Content |
|---------|---------|
| Business model analysis | Viability and sustainability |
| Internal governance | Risk culture, board effectiveness |
| Capital adequacy | ICAAP review, Pillar 2R and 2G add-ons |
| Liquidity adequacy | ILAAP review, liquidity add-ons |

**Pillar 2 capital add-ons:**

| Type | Description |
|------|-------------|
| Pillar 2 Requirement (P2R) | Binding minimum -- breach triggers restrictions |
| Pillar 2 Guidance (P2G) | Non-binding -- breach triggers supervisory dialogue |

**Overall Capital Requirement (OCR):**

$$OCR = P1 + P2R + CBR$$

Where CBR = Combined Buffer Requirement (conservation + countercyclical + systemic buffers).

---

*Reference document for the Quant Risk Engine project.*
*Regulation references: CRR3 (EU 2024/1623), EBA/GL/2022/14, EBA/RTS/2022/09,*
*EBA/RTS/2022/10, BCBS d457, EMIR (EU 648/2012).*