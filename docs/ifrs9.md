# IFRS 9 -- Financial Instruments

## Legislative Framework

| Instrument | Reference | Status | Content |
|------------|-----------|--------|---------|
| IFRS 9 | IASB, effective 1 January 2018 | **Directly applicable** via EU endorsement | Classification, measurement, impairment, hedge accounting |
| EU Endorsement | Regulation (EU) 2016/2067 | Directly applicable | Endorsed IFRS 9 for EU use, replacing IAS 39 |
| Banking package carve-out | Regulation (EU) 2017/2395 | Expired | Transitional arrangements for regulatory capital impact |
| IFRS 9 Phase 2 amendments | Regulation (EU) 2020/2097 | Directly applicable | Interest rate benchmark reform (IBOR transition) |

**Applies to:** all IFRS-reporting entities -- EU-listed companies, banks,
insurers, and any fund electing IFRS reporting. Luxembourg banks and
investment firms reporting under IFRS are in scope. Luxembourg funds using
Lux GAAP apply analogous principles under the Law of 19 December 2002.

**Replaces:** IAS 39 -- the previous standard, widely criticised for
recognising losses too late (the "too little, too late" problem exposed in 2008).

---

## 1. Classification and Measurement

IFRS 9 classifies financial assets based on two criteria:

- **Business model** -- how the entity manages the asset (hold to collect, hold
  to collect and sell, or other)
- **Cash flow characteristics** -- whether contractual cash flows are solely
  payments of principal and interest (SPPI test)

### Financial Assets

| Category | Business model | SPPI test | Measurement |
|----------|---------------|-----------|-------------|
| Amortised cost (AC) | Hold to collect | Pass | Effective interest rate, no mark-to-market |
| Fair value through OCI (FVOCI) | Hold to collect and sell | Pass | Fair value, gains/losses in OCI; recycled to P&L on sale |
| Fair value through P&L (FVTPL) | Other / trading | Fail or designation | Full mark-to-market through P&L |

**SPPI test:** a bond with fixed or floating rate coupons passes. A convertible
bond, a bond with non-standard features (leverage, inverse floater), or an
equity instrument fails -- measured at FVTPL.

**Equity instruments:** always FVTPL unless irrevocably designated FVOCI at
inception (no recycling to P&L on sale -- dividends still recognised in P&L).

### Financial Liabilities

| Category | Measurement |
|----------|-------------|
| Amortised cost | Default -- loans, deposits, issued bonds |
| FVTPL | Trading liabilities, derivatives, designated at inception |

Own credit risk on FVTPL liabilities: changes in fair value due to own credit
risk recognised in OCI, not P&L -- prevents the counterintuitive gain on
own credit deterioration (IAS 39 issue).

### Derivatives

All derivatives measured at **FVTPL** unless designated as hedging instruments
under IFRS 9 hedge accounting. This includes CDS, IRS, FX forwards, options.

---

## 2. Impairment -- Expected Credit Loss (ECL)

The core innovation of IFRS 9 over IAS 39. Replaces the incurred loss model
with a **forward-looking expected credit loss** model. Losses recognised before
default occurs.

### Three-Stage Model

| Stage | Trigger | ECL measure | Interest recognition |
|-------|---------|-------------|---------------------|
| Stage 1 | No significant deterioration since origination | 12-month ECL | Effective interest on gross carrying amount |
| Stage 2 | Significant increase in credit risk (SICR) since origination | Lifetime ECL | Effective interest on gross carrying amount |
| Stage 3 | Credit impaired -- objective evidence of default | Lifetime ECL | Effective interest on net carrying amount (after ECL) |

**SICR indicators (non-exhaustive):**
- PD has increased significantly since origination (relative and absolute thresholds)
- 30 days past due (rebuttable presumption)
- Forbearance or restructuring
- Rating downgrade below investment grade
- Watchlist designation

**Default definition:** 90 days past due (rebuttable presumption) or
unlikely to pay without recourse to collateral.

### ECL Formula

$$ECL = PD \times LGD \times EAD \times DF$$

Where:
- **PD** -- probability of default over the relevant horizon (12-month for Stage 1, lifetime for Stage 2/3)
- **LGD** -- loss given default, net of collateral and recovery
- **EAD** -- exposure at default, including undrawn commitments
- **DF** -- discount factor to present value

### Point-in-Time vs Through-the-Cycle

IFRS 9 requires **point-in-time (PIT) PD** -- incorporating current economic
conditions and forward-looking information. This differs from:

- **Through-the-cycle (TTC) PD** -- used in Basel IRB models, stable across cycles
- **Market-implied PD** -- from CDS spreads, includes risk premium

Banks must adjust their TTC IRB PDs to PIT estimates using macroeconomic
overlays and scenario weighting.

### Forward-Looking Information (FLI)

Entities must incorporate reasonable and supportable forward-looking information:
- Macroeconomic scenarios (base, adverse, severe) with probability weights
- GDP growth, unemployment, interest rates, property prices
- Sector-specific indicators
- Central bank and IMF forecasts

ECB and EBA have issued extensive guidance on FLI incorporation -- a major
area of supervisory scrutiny in SREP.

### Lifetime ECL for Stage 2/3

$$LifetimeECL = \sum_{t=1}^{T} PD_t \times LGD_t \times EAD_t \times DF_t$$

Marginal PD at each period $t$, conditional on survival to $t-1$.

---

## 3. Hedge Accounting

IFRS 9 hedge accounting is more principles-based and aligned with risk
management practice than IAS 39. Three types:

| Type | Hedged item | Hedging instrument | P&L treatment |
|------|------------|-------------------|---------------|
| Fair value hedge | Fixed rate asset/liability | IRS pay-fixed, CDS | Both item and instrument at fair value through P&L -- offsets |
| Cash flow hedge | Floating rate exposure, forecast transaction | IRS receive-fixed, FX forward | Effective portion in OCI; recycled when hedged item affects P&L |
| Net investment hedge | Foreign operation net assets | FX forward, cross-currency swap | In OCI; recycled on disposal of operation |

**Key conditions:**
- Economic relationship between hedged item and instrument
- Credit risk does not dominate the value changes
- Hedge ratio must reflect actual risk management quantities
- No quantitative effectiveness threshold (replaces IAS 39 80-125% rule)

**Portfolio fair value hedge of interest rate risk (macro hedge):**
IAS 39 carve-out still applies for EU banks hedging NII -- IFRS 9 macro hedge
accounting standard not yet finalised by IASB.

---

## 4. Application by Institution Type

### Banks and Credit Institutions

Primary focus: ECL impairment on loan portfolios, trade finance, off-balance
sheet commitments. ECL models are subject to:
- EBA Guidelines on ECL (EBA/GL/2017/06)
- ECB guidance on NPLs and provisioning
- SREP scrutiny of model assumptions, staging criteria, FLI

Key KPIs:
- **Cost of risk** -- ECL charge / average loan book
- **Coverage ratio** -- ECL stock / non-performing exposures
- **Stage 2 ratio** -- Stage 2 loans / total loans (leading indicator of stress)
- **NPE ratio** -- non-performing exposures / total exposures

### Asset Managers and AIFs

Focus on classification and measurement of portfolio holdings:
- Bonds held to collect: amortised cost if SPPI passes, business model documented
- Bonds in trading book: FVTPL
- Derivatives: always FVTPL unless hedge accounting designated
- Equity investments: FVTPL (or FVOCI election for strategic stakes)

ECL applies to trade receivables, intercompany loans, cash at banks -- not
typically to investment portfolios (which are FVTPL).

### Insurance Companies

IFRS 9 interacts with IFRS 17 (Insurance Contracts, effective 2023):
- Overlay approach or temporary exemption expired -- insurers now fully apply IFRS 9
- Significant FVOCI designation for bonds backing insurance liabilities
- OCI volatility management is a key focus

---

## 5. Key Metrics and KPIs

| Metric | Definition | Regulatory use |
|--------|-----------|---------------|
| ECL / Provision | Expected credit loss stock on balance sheet | SREP, Pillar 3 |
| Coverage ratio | ECL / NPE | EBA transparency exercise |
| Cost of risk | ECL charge for period / average gross loans | Investor and supervisory KPI |
| Stage 2 ratio | Stage 2 gross loans / total gross loans | Early warning indicator |
| NPE ratio | Non-performing exposures / total exposures | EBA definition, supervisory benchmark |
| PD (PIT) | Point-in-time probability of default | IFRS 9 ECL input |
| LGD | Loss given default net of recovery | IFRS 9 ECL input |
| EAD | Exposure at default including CCF for off-balance sheet | IFRS 9 ECL input |
| CCF | Credit conversion factor -- undrawn to EAD | IFRS 9 / Basel IV |

---

## 6. IFRS 9 vs Basel IV -- Key Differences

| Dimension | IFRS 9 ECL | Basel IV IRB |
|-----------|-----------|-------------|
| Objective | Financial reporting -- investor information | Regulatory capital -- loss absorption |
| PD type | Point-in-time | Through-the-cycle |
| LGD type | Point-in-time, economic | Downturn LGD |
| Horizon | 12-month (Stage 1) or lifetime | 1-year |
| Forward looking | Yes -- scenarios and FLI | Limited |
| Discount rate | Effective interest rate | Not discounted |

The gap between IFRS 9 provisions and Basel expected loss (EL = PD × LGD × EAD
TTC) creates the **regulatory provision shortfall or excess**:
- Shortfall: deducted from CET1
- Excess: added to Tier 2 capital (up to 0.6% of credit RWA)

---

*Regulation references: IFRS 9 (IASB 2014), Regulation (EU) 2016/2067,*
*EBA/GL/2017/06 (ECL guidelines), ECB Guidance on NPLs,*
*EBA/GL/2022/06 (definition of default).*