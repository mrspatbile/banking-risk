# MiFID II / MiFIR -- Markets in Financial Instruments

## Legislative Framework

| Instrument | Reference | Status | Content |
|------------|-----------|--------|---------|
| MiFID II | Directive 2014/65/EU | Transposed | Authorisation, conduct, market structure, product governance |
| MiFIR | Regulation (EU) 600/2014 | **Directly applicable** | Trading obligations, transparency, transaction reporting |
| MiFID II Quick Fix | Directive 2021/338/EU | Transposed | COVID relief -- research unbundling, bond tick sizes |
| MiFIR Review | Regulation (EU) 2024/791 | **Directly applicable** -- phased from 2024 | Consolidated tape, derivatives trading obligation reform |
| MiFID III | Directive 2024/790/EU | Transposition deadline 2026 | Aligned with MiFIR Review |

**Luxembourg transposition of MiFID II:**
- Law of 30 May 2018 on markets in financial instruments
- CSSF Regulation 18-03
- CSSF Circulars 18/716, 19/724

---

## Scope -- Who and What

**Entities in scope:**
- Investment firms (brokers, dealers, portfolio managers, advisers)
- Credit institutions providing investment services
- AIFMs and UCITS ManCos providing MiFID services (portfolio management, advice)
- Systematic internalisers (SIs) -- firms executing client orders against own book

**Financial instruments covered:**
- Transferable securities (equities, bonds, ETFs)
- Money market instruments
- Units in CIUs (UCITS, AIFs)
- Derivatives -- options, futures, swaps, FX forwards (where MiFID applies)
- Emission allowances

**FX forwards:** MiFID applies to FX forwards used for investment purposes.
Commercially-purpose FX forwards (hedging trade receivables) are carved out.

---

## 1. Market Structure

### Trading Venues

| Venue | Abbreviation | Description |
|-------|-------------|-------------|
| Regulated Market | RM | Exchange -- highest transparency, strictest rules |
| Multilateral Trading Facility | MTF | Operator-run multilateral system -- similar to RM |
| Organised Trading Facility | OTF | New under MiFID II -- for non-equity instruments (bonds, derivatives) |
| Systematic Internaliser | SI | Firm executing client orders against own book on organised basis |

OTF was created specifically to bring OTC bond and derivative trading onto
organised venues -- reduces dark pool activity.

### Trading Obligation

**MiFIR Articles 23 and 28:**

| Instrument | Obligation |
|------------|-----------|
| Shares admitted to trading on RM | Must trade on RM, MTF, or SI -- no pure OTC |
| Derivatives subject to clearing obligation | Must trade on RM, MTF, OTF, or equivalent third-country venue |

Derivatives trading obligation (DTO) covers: EUR and USD IRS, iTraxx and
CDX index CDS. Same instruments as EMIR clearing obligation -- coordinated.

---

## 2. Transparency

### Pre-Trade Transparency
Venues must publish current bid/ask prices and depth of book before execution.

### Post-Trade Transparency
Trades must be published as close to real-time as possible (within 1 minute
for equities).

### Consolidated Tape (MiFIR Review 2024)
Single EU-wide post-trade data feed per asset class -- equities, bonds,
ETFs, derivatives. Administered by a single Consolidated Tape Provider (CTP)
selected by ESMA. Addresses fragmentation across 300+ venues in the EU.
Bonds CTP operational target: 2026.

### Waivers and Deferrals
- **Pre-trade waivers:** large-in-scale, reference price, negotiated transactions
- **Post-trade deferrals:** illiquid bonds and derivatives -- publication delayed
  up to 4 weeks (reduced under MiFIR Review)

---

## 3. Transaction Reporting

**MiFIR Article 26:** investment firms must report all transactions in
financial instruments to their National Competent Authority (CSSF for
Luxembourg firms) by end of next business day (T+1).

**Key fields (65 data fields):**
- Instrument identifier (ISIN, CFI)
- Buyer and seller (LEI mandatory for legal entities)
- Price, quantity, venue
- Trader and client identifiers

**Reported to:** Approved Reporting Mechanism (ARM) -- DTCC, UnaVista,
Tradeweb -- which forwards to NCA.

**LEI (Legal Entity Identifier):** mandatory for all legal entity counterparties.
No LEI, no trade -- firms cannot execute on behalf of a legal entity client
without a valid LEI.

---

## 4. Best Execution

**MiFID II Article 27:** firms must take sufficient steps to obtain the best
possible result for clients -- not just best price but also:
- Speed of execution
- Likelihood of execution and settlement
- Size and nature of the order
- Any other relevant consideration

**Order execution policy:** firms must maintain and publish an execution policy,
reviewed annually and on material change.

**RTS 27 and 28 reporting:** venues report execution quality data; firms report
top 5 execution venues per asset class annually. Suspended under MiFID Quick Fix,
replaced by simplified reporting under MiFID III.

---

## 5. Product Governance

**MiFID II Articles 16 and 24, Delegated Directive 2017/593:**

| Role | Obligation |
|------|-----------|
| Manufacturer | Define target market, stress test product, make information available to distributors |
| Distributor | Understand product, define own target market, ensure product reaches intended clients |

**Target market:** positive (who product is for) and negative (who it is not for)
defined across five criteria: client type, knowledge/experience, financial
situation, risk tolerance, objectives.

**Product intervention:** ESMA and NCAs can restrict or prohibit products
temporarily if significant investor protection concerns. Used for binary options,
CFDs with high leverage.

---

## 6. Client Classification

| Category | Protection level | Eligible for |
|----------|-----------------|-------------|
| Retail client | Highest -- full MiFID protections | Standard products |
| Professional client | Medium -- some protections waived | Wider product range |
| Eligible counterparty | Lowest -- most protections disappear | All instruments, no best execution obligation |

**Per se professionals:** credit institutions, investment firms, insurance companies,
pension funds, large corporates (two of three: EUR 20M balance sheet, EUR 40M
turnover, EUR 2M own funds).

**Elective professionals:** retail clients opting up -- must meet two of three:
10 transactions per quarter, EUR 500k portfolio, financial sector experience.

---

## 7. Research Unbundling

**MiFID II Article 24(7):** portfolio managers must pay for research separately
from execution -- cannot bundle into commissions (soft dollars banned in EU).

Payment via:
- Firm's own P&L
- Research payment account (RPA) funded by explicit client charge

**MiFID Quick Fix (2021):** temporary exemption for SME research and
fixed income research -- extended under MiFID III to make permanent for
fixed income, FX, and commodities research.

---

## 8. Key Metrics and Reporting KPIs

| Metric / Report | Content | Frequency |
|----------------|---------|-----------|
| Transaction report (Article 26) | All executed transactions | T+1 |
| Best execution report (RTS 28) | Top 5 venues by asset class | Annual |
| Order execution policy | Venue selection criteria | Annual review |
| LEI validation | Counterparty LEI active and valid | Pre-trade |
| Target market assessment | Product suitability for client segment | Per product / annual review |
| SI determination | Whether firm qualifies as SI per asset class | Quarterly |

---

## 9. Interaction with Other Regulation

| Regulation | Interaction |
|------------|-------------|
| EMIR | Trading obligation (MiFIR) covers same instruments as clearing obligation (EMIR) -- coordinated scope |
| AIFMD | AIFMs providing portfolio management or advice are subject to MiFID organisational requirements |
| UCITS | ManCos providing MiFID services in scope -- conduct and best execution apply |
| FRTB / CRR3 | Market risk capital applies to trading book instruments -- MiFID defines what must be in trading book |
| PRIIPs | Product governance (MiFID) and KID disclosure (PRIIPs) both apply to structured products sold to retail |
| DORA | ICT resilience requirements apply to MiFID investment firms as financial entities |

---

*Regulation references: Directive 2014/65/EU (MiFID II), Regulation (EU) 600/2014 (MiFIR),*
*Regulation (EU) 2024/791 (MiFIR Review), Directive 2024/790/EU (MiFID III),*
*Luxembourg Law of 30 May 2018, CSSF Regulation 18-03.*