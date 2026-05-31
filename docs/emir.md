# Financial Market Infrastructure Regulation -- Quick Reference

## EMIR -- European Market Infrastructure Regulation

| Instrument | Reference | Status | Content |
|------------|-----------|--------|---------|
| EMIR | Regulation (EU) 648/2012 | **Directly applicable** | Original framework -- clearing, reporting, risk mitigation |
| EMIR Refit | Regulation (EU) 2019/834 | **Directly applicable** | Simplified obligations for smaller counterparties, NFC thresholds |
| EMIR 3.0 | Regulation (EU) 2024/2987 | **Directly applicable** -- application from 2025 | Active account requirement, CCP supervision reform |

**Directly applicable throughout** -- no member state transposition needed.
Luxembourg implementation: CSSF Circular 12/552 and subsequent updates for
Luxembourg-domiciled entities.

---

## Scope -- What EMIR Covers

OTC derivatives as defined in MiFID II Annex I -- any derivative not traded
on a regulated exchange. In practice:

| Asset class | Instruments covered |
|-------------|-------------------|
| Interest rates | IRS, OIS, swaptions, caps/floors, FRAs |
| Credit | CDS, index CDS (iTraxx) |
| FX | FX forwards > 3 days, cross-currency swaps, FX options |
| Equity | OTC equity options, total return swaps |
| Commodity | OTC commodity derivatives |

**Not covered:** exchange-traded derivatives (futures, listed options) -- these
are subject to MiFID II/MiFIR instead.

---

## Three Core Obligations

### 1. Clearing Obligation
Standardised OTC derivatives must be cleared through a CCP (LCH, ICE Clear Europe,
Eurex Clearing). Currently mandated classes:

| Class | Instruments |
|-------|-------------|
| Interest rate | EUR, USD, GBP, JPY plain vanilla IRS; OIS |
| Credit | iTraxx Main and Crossover index CDS; CDX equivalents |

Single name CDS: **not yet mandated** for clearing -- bilateral with margin.

### 2. Margin Requirements
Non-cleared derivatives must exchange:

| Margin type | Requirement |
|-------------|-------------|
| Variation margin (VM) | Daily, mark-to-market -- all financial counterparties |
| Initial margin (IM) | Phase-in by counterparty size -- ISDA SIMM or schedule-based |

### 3. Reporting Obligation
All OTC derivative trades reported to a trade repository within T+1.
Approved EU trade repositories: DTCC, REGIS-TR, UnaVista, KDPW.
EMIR Refit (2019) introduced double-sided reporting -- both counterparties report.

---

## Counterparty Classification

| Type | Definition | Clearing obligation |
|------|------------|-------------------|
| FC (Financial Counterparty) | Banks, asset managers, insurers, AIFMs | Yes, above thresholds |
| NFC+ (Non-Financial above threshold) | Corporates exceeding clearing threshold | Yes |
| NFC- (Non-Financial below threshold) | Corporates below clearing threshold | No -- risk mitigation only |

**Clearing thresholds (EMIR Refit):**

| Asset class | Threshold |
|-------------|-----------|
| Credit derivatives | EUR 1 billion gross notional |
| Equity derivatives | EUR 1 billion gross notional |
| Interest rate | EUR 3 billion gross notional |
| FX | EUR 3 billion gross notional |
| Commodity | EUR 3 billion gross notional |

---

## EMIR 3.0 -- Key Changes (2024/2987)

Application from 2025. Main addition:

**Active account requirement** -- EU entities subject to the clearing obligation
must hold an active account at an EU CCP (not just LCH London) and clear a
minimum proportion of trades there. Systemic risk concern -- concentration of EUR IRS clearing at a third-country CCP (LCH London) creates operational and jurisdictional risk for EU financial stability. Active account requirement ensures EU CCPs maintain viable clearing capacity for EUR-denominated instruments.

---

## Interaction with Other Regulation

| Regulation | Interaction |
|------------|-------------|
| MiFID II / MiFIR | Trading obligation -- liquid OTC derivatives must trade on venue (SEF/OTF) |
| Basel IV / CRR3 | Cleared trades: lower CVA and counterparty credit RWA vs bilateral |
| AIFMD | AIFMs are FCs -- full EMIR obligations apply to AIF derivative books |
| UCITS | UCITS ManCos are FCs -- EMIR applies; OTC counterparty limits under UCITS still apply separately |

---

*Regulation references: Regulation (EU) 648/2012 (EMIR), Regulation (EU) 2019/834*
*( EMIR Refit), Regulation (EU) 2024/2987 (EMIR 3.0), CSSF Circular 12/552.*