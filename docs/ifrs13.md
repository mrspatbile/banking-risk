# IFRS 13 -- Fair Value Measurement

## Legislative Framework

| Instrument | Reference | Status | Content |
|------------|-----------|--------|---------|
| IFRS 13 | IASB, effective 1 January 2013 | **Directly applicable** via EU endorsement | Fair value definition, hierarchy, disclosure |
| EU Endorsement | Regulation (EU) 1255/2012 | Directly applicable | Endorsed IFRS 13 for EU use |
| IFRS 13 amendments | Regulation (EU) 2023/1803 | Directly applicable | Consolidated endorsement regulation |

**Applies to:** all IFRS-reporting entities where another standard requires
or permits fair value measurement. Does not itself require fair value -- it
only defines how to measure it when required by IFRS 9, IFRS 16, IAS 36, etc.

**Does not apply to:** share-based payments (IFRS 2), lease transactions (IFRS 16
measurement exceptions), net realisable value (IAS 2), value in use (IAS 36).

**Luxembourg specifics:** banks and listed entities report under IFRS --
full IFRS 13 applies. Luxembourg funds using Lux GAAP apply analogous fair
value principles under the Law of 19 December 2002 on the register of commerce
and CSSF guidance on NAV calculation.

---

## 1. Fair Value Definition

**IFRS 13.9:**

Fair value is the **exit price** -- the price received to sell an asset or
paid to transfer a liability in an orderly transaction between market
participants at the measurement date.

Four key elements:

| Element | Meaning | Common misconception |
|---------|---------|---------------------|
| Exit price | What you receive selling, not what you paid | Not transaction price / entry price |
| Orderly transaction | Normal market conditions | Not a forced or distressed sale |
| Market participant | Hypothetical knowledgeable buyer/seller | Not entity-specific assumptions |
| Measurement date | Point in time | Not averaged or smoothed |

**Principal market:** fair value measured in the principal market for the asset
(highest volume and activity). If no principal market, the most advantageous
market. Transaction costs excluded from fair value but used to determine
most advantageous market.

---

## 2. The Fair Value Hierarchy

Three levels based on the observability of inputs -- not the valuation technique itself.
**The level is determined by the lowest level input significant to the overall measurement.**

| Level | Input type | Observability |
|-------|-----------|--------------|
| Level 1 | Quoted prices in active markets for identical assets | Directly observable -- no adjustment |
| Level 2 | Observable inputs other than Level 1 | Indirectly observable -- market-corroborated |
| Level 3 | Unobservable inputs | Entity-developed -- significant judgment |

### Level 1

Unadjusted quoted price in an active market for an identical asset or liability.
Highest reliability -- no model required.

**Examples:** exchange-traded equities, on-the-run government bonds quoted by
primary dealers, listed futures and options, ETF market prices.

**Active market criteria:** sufficient frequency and volume of transactions to
provide pricing information on an ongoing basis. Thin markets or markets with
significant bid-ask spreads may not qualify as active.

### Level 2

Observable inputs other than Level 1 quoted prices. Includes:
- Quoted prices for similar (not identical) assets in active markets
- Quoted prices for identical assets in markets that are not active
- Observable market data -- yield curves, credit spreads, FX rates, implied volatilities
- Market-corroborated inputs -- derived from observable data by correlation or extrapolation

**Examples:**

| Instrument | Level 2 input |
|------------|--------------|
| OTC interest rate swap | OIS and EURIBOR curves from active interdealer markets |
| Corporate bond (IG, liquid) | Yield curve + observable credit spread |
| FX forward | Spot rate + OIS discount factors (CIP) |
| Vanilla OTC option | BSM with observable implied volatility surface |
| CDS (liquid single name) | Dealer-quoted CDS spreads via Markit composite |
| CLO tranche (senior, AAA) | Observable spread matrix from active secondary market |

**Level 2 does not require a simple model** -- a complex model can still be
Level 2 if all significant inputs are observable.

### Level 3

Unobservable inputs -- significant to the fair value but not corroborated
by market data. Entity develops its own assumptions about what market
participants would use.

**Examples:**

| Instrument | Level 3 input |
|------------|--------------|
| Private equity direct investment | Internally estimated cash flows, EBITDA multiples from non-active transactions |
| Direct real estate | Appraised value, occupancy assumptions, capitalisation rates |
| Private credit / unitranche | Spread assumptions with no observable secondary market |
| CLO equity tranche | Cash flow model with unobservable prepayment and default assumptions |
| Exotic OTC options | Correlation, long-dated volatility beyond observable surface |
| Illiquid structured products | Proprietary model with significant unobservable inputs |

---

## 3. Valuation Techniques

IFRS 13 recognises three approaches. Entities must maximise observable inputs
and minimise unobservable inputs regardless of technique chosen.

| Approach | Description | When used |
|----------|-------------|----------|
| Market approach | Prices from identical or comparable market transactions | Liquid instruments, comparable company analysis |
| Income approach | Discounts future cash flows or earnings | Bonds, loans, private equity, real estate |
| Cost approach | Current replacement cost | Rarely used for financial instruments |

Multiple techniques may be used and weighted -- particularly for Level 3 where
no single technique is conclusive.

---

## 4. Specific Applications

### OTC Derivatives

Measured at FVTPL under IFRS 9. Fair value includes:
- **CVA (Credit Valuation Adjustment)** -- adjustment for counterparty default risk
- **DVA (Debit Valuation Adjustment)** -- adjustment for own default risk
- **FVA (Funding Valuation Adjustment)** -- cost of funding uncollateralised positions

Post-EMIR, cleared derivatives have VM posted daily -- CVA is minimal for cleared
trades. Bilateral uncleared trades require full CVA/DVA/FVA.

### Bonds and Loans

| Situation | Level | Technique |
|-----------|-------|-----------|
| On-the-run government bond | Level 1/2 | Market price or yield curve |
| IG corporate bond, liquid | Level 2 | Yield curve + observable credit spread |
| HY bond, illiquid | Level 2/3 | Dealer quotes or model |
| Performing loan (no active market) | Level 3 | DCF at current market rates |
| Non-performing loan | Level 3 | Recovery model, collateral value |

### Investment Funds

| Fund type | Level | Basis |
|-----------|-------|-------|
| Listed fund / ETF | Level 1 | Market price |
| Unlisted UCITS with daily NAV | Level 2 | NAV as practical expedient |
| Unlisted AIF with infrequent NAV | Level 2/3 | NAV if redemption available; Level 3 if locked up |
| Private equity fund (locked up) | Level 3 | NAV of underlying fund -- unobservable |

**NAV practical expedient (IFRS 13.48A):** for investment entities measuring
fund interests, NAV may be used as fair value if redemption is available at
NAV at or near measurement date.

### Real Estate

Direct real estate is always **Level 3** -- no active market for identical
properties. Valuation by independent appraiser using:
- Income capitalisation (passing rent / capitalisation rate)
- Discounted cash flow (projected rental income, exit yield)
- Comparable transactions (adjusted for differences)

Occupancy rate, lease expiry profile, market rental growth, and discount rate
are all Level 3 inputs subject to significant judgment.

---

## 5. Day 1 P&L

**IFRS 13.57-13.60:**

When transaction price differs from fair value at initial recognition:

| Situation | Treatment |
|-----------|-----------|
| Fair value evidenced by Level 1 or observable Level 2 inputs | Day 1 gain/loss recognised immediately in P&L |
| Fair value relies on significant Level 3 inputs | Day 1 gain/loss deferred -- amortised over life of instrument or until inputs become observable |

Day 1 P&L deferral is a significant issue for structured products, exotic
derivatives, and illiquid instruments where the bid-ask spread or model
uncertainty is large. Banks maintain Day 1 P&L reserves tracked instrument
by instrument.

---

## 6. Key Metrics and KPIs

| Metric | Definition | Regulatory / reporting use |
|--------|-----------|--------------------------|
| Level 3 ratio | Level 3 assets / total financial assets at fair value | Investor scrutiny -- higher ratio = more model risk |
| Level 3 transfers | Movements into/out of Level 3 | Disclosure required -- signals liquidity change |
| CVA | Credit valuation adjustment on derivative portfolio | P&L volatility, FRTB CVA capital charge |
| DVA | Debit valuation adjustment | P&L, offset to CVA for bilateral trades |
| Day 1 P&L reserve | Deferred gains on Level 3 instruments | Risk management KPI, auditor focus |
| Bid-ask adjustment | Adjustment from mid to exit price for less liquid instruments | Level 2/3 fair value refinement |

---

## 7. Disclosure Requirements

**IFRS 13.91-13.99:** for each class of assets and liabilities at fair value:

| Disclosure | Level 1 | Level 2 | Level 3 |
|------------|---------|---------|---------|
| Fair value at period end | Yes | Yes | Yes |
| Transfers between levels (and reasons) | Yes | Yes | Yes |
| Valuation technique and inputs | -- | Yes | Yes |
| Significant unobservable inputs and ranges | -- | -- | Yes |
| Sensitivity to changes in unobservable inputs | -- | -- | Yes |
| Reconciliation opening to closing balance | -- | -- | Yes |
| Unrealised gains/losses on Level 3 held at period end | -- | -- | Yes |

**Transfer policy:** entities must define and consistently apply a policy for
when transfers between levels are recognised -- typically at the beginning or
end of the reporting period.

---

## 8. IFRS 13 vs IFRS 9 -- Interaction

| Topic | IFRS 13 | IFRS 9 |
|-------|---------|--------|
| Scope | How to measure fair value | When to measure at fair value |
| CVA/DVA | Required for exit price | Required for FVTPL derivatives |
| Day 1 P&L | Recognition and deferral rules | Classification drives whether P&L or OCI |
| Hierarchy | Level 1/2/3 classification | Not addressed -- defers to IFRS 13 |

---

*Regulation references: IFRS 13 (IASB 2011), Regulation (EU) 1255/2012,*
*Regulation (EU) 2023/1803, CSSF guidance on NAV calculation,*
*EBA/GL/2020/06 (loan origination and monitoring -- fair value of collateral).*