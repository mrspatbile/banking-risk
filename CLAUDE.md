# CLAUDE.md — banking-risk

## What this project is

Banking regulatory risk applications built on quant-risk-engine.
Covers IRRBB EVE/NII SOT, FRTB SA GIRR, CSRBB, credit risk IRB,
and liquidity risk (LCR, NSFR, stress testing, ILAAP).

The library at quant-risk-engine handles all curve construction,
instrument pricing, and model simulation. This repo applies
that infrastructure to regulatory and internal risk frameworks.
No pricing logic lives here — only domain application.

## Stack

- Python 3.13
- quant-risk-engine (local editable install)
- QuantLib via quant-risk-engine
- scipy (norm.cdf/ppf for IRB capital formula)

## How we work together

Do not make changes without checking with me first.

1. Read the ticket before touching anything.
2. Explain your understanding and proposed approach.
3. Wait for go-ahead before writing code.
4. One logical step at a time.
5. Explain what you did and the regulatory reasoning.
6. Commit message format: `BKR-NNN: short description`

## Things never to do without explicit permission

- Modify or delete passing tests
- Touch notebook files unless the task says so
- Introduce pricing logic — that belongs in quant-risk-engine
- Introduce new dependencies without flagging first
- Suggest or generate a commit directly to main

## Regulatory context

| Regulation | Where it matters |
|---|---|
| EBA/RTS/2022/10 | IRRBB EVE SOT 15%, NII SOT 5% |
| CRR3 Art. 325 | FRTB SA GIRR delta/vega/curvature, prescribed vertices |
| EBA/GL/2022/14 | IRRBB governance, NMD modelling, CSRBB |
| CRR Art. 153 | IRB capital formula — asset correlation, K, RWA |
| CRR Art. 228–230 | LGD floors — collateral haircut approach |
| CRR Art. 412–428 | LCR — liquidity coverage ratio |
| CRR Art. 428a–428ax | NSFR — net stable funding ratio |
| EBA/GL/2019/02 | LCR reporting and outflow rates |
| EBA/GL/2018/02 | Internal liquidity stress testing |
| EBA/GL/2021/01 | ILAAP — internal liquidity adequacy assessment |
| BCBS 248 | Intraday liquidity monitoring tools |
| EBA ITS 2021/05 | Asset encumbrance and funding gap reporting |

## Running

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e /path/to/quant-risk-engine
pip install -e .[dev]
cp .env.example .env
nbstripout --install
pytest tests/ -v
jupyter lab
```

---

## Current status — 346 tests passing

### Modules

| Domain | File | Regulatory ref |
|---|---|---|
| IRRBB EVE SOT | `irrbb/eve.py` | EBA/RTS/2022/10 |
| IRRBB NII SOT | `irrbb/nii.py` | EBA/RTS/2022/10 |
| IRRBB repricing gap | `irrbb/gap.py` | EBA/GL/2022/14 |
| IRRBB banking book + NMD | `irrbb/book.py` | EBA/GL/2022/14 |
| IRRBB scenarios | `irrbb/scenarios.py` | EBA/RTS/2022/10 Annex III |
| FRTB GIRR delta | `frtb/girr/delta.py` | CRR3 Art. 325bd/bf |
| FRTB GIRR vega | `frtb/girr/vega.py` | CRR3 Art. 325bd/bf |
| FRTB GIRR curvature | `frtb/girr/curvature.py` | CRR3 Art. 325e/ef |
| FRTB vertex mapping | `frtb/vertex_mapping.py` | CRR3 Art. 325bd |
| FRTB trading portfolio | `frtb/portfolio.py` | CRR3 Art. 325 |
| CSRBB spread risk | `csrbb/spread_risk.py` | EBA/GL/2022/14 |
| Credit risk PD | `credit_risk/pd.py` | CRR Art. 163 |
| Credit risk LGD | `credit_risk/lgd.py` | CRR Art. 228–230 |
| Credit risk EL + IRB | `credit_risk/el.py` | CRR Art. 153/162 |
| Liquidity LCR | `liquidity/lcr.py` | CRR Art. 412–428 |
| Liquidity NSFR | `liquidity/nsfr.py` | CRR Art. 428a–428ax |
| Liquidity intraday | `liquidity/intraday.py` | BCBS 248 |
| Liquidity funding gap | `liquidity/funding_gap.py` | EBA ITS 2021/05 |
| Liquidity collateral | `liquidity/collateral.py` | EBA ITS 2021/05 |
| Liquidity stress | `liquidity/stress.py` | EBA/GL/2018/02 |
| Liquidity EWI | `liquidity/ewi.py` | EBA/GL/2021/01 |
| Liquidity ILAAP | `liquidity/ilaap.py` | EBA/GL/2021/01 |
| Shared curve projection | `shared/curve_projection.py` | — |
| Shared curve adapter | `shared/curves.py` | — |
| Shared date utils | `shared/dates.py` | — |
| Reporting styles + reporters | `utils/reporting.py` | — |

### Notebooks

| Notebook | Content |
|---|---|
| `notebooks/01_irrbb.ipynb` | EVE SOT, NII SOT, repricing gap, NMD banking book |
| `notebooks/02_frtb_girr.ipynb` | GIRR delta, vega, curvature, combined capital |
| `notebooks/03_csrbb.ipynb` | CS01, stress P&L, rating-bucket breakdown |
| `notebooks/04_credit_risk.ipynb` | PD models, LGD collateral, EL, IRB capital formula |
| `notebooks/05_liquidity_ratios.ipynb` | LCR (HQLA caps, outflows) and NSFR sensitivity |
| `notebooks/06_liquidity_monitoring.ipynb` | Intraday, funding gap, collateral, stress, EWI, ILAAP |

---

## Tickets

### Credit risk / CSRBB

| Ticket | Description |
|---|---|
| BKR-24 | `credit_risk/pd.py`: Rating_PD_Model and Logistic_PD_Model |
| BKR-25 | `credit_risk/lgd.py`: CRR_LGD_Model — collateral haircut approach |
| BKR-26 | `credit_risk/el.py`: Expected_Loss_Calculator + IRB capital K and RWA |
| BKR-27 | `csrbb/spread_risk.py`: SA_CSRBB_Calculator — CS01 and scenario stress P&L |

### IRRBB

| Ticket | Description |
|---|---|
| BKR-36 | `irrbb/eve.py`: SA_EVE_Calculator — EVE SOT 15% Tier 1 |
| BKR-37 | `irrbb/nii.py`: SA_NII_Calculator — NII SOT 5% Tier 1 |
| BKR-38 | `utils/reporting.py`: Dark_Style, Light_Style, EVE/NII/Gap/GIRR reporters |
| BKR-39 | `irrbb/__init__.py`: clean public API |

### FRTB

| Ticket | Description |
|---|---|
| BKR-40 | `frtb/girr/vega.py`: SA_GIRR_Vega_Calculator — Kronecker correlation matrix |
| BKR-41 | `frtb/vertex_mapping.py`: nearest_vertex, assign_to_bucket, all CRR3 vertex grids |
| BKR-42 | `frtb/portfolio.py`: Trading_Instrument, Standard_Trading_Portfolio |
| BKR-43 | `frtb/girr/curvature.py`: SA_GIRR_Curvature_Calculator, curvature_pnl_from_greeks |
| BKR-44 | `notebooks/02_frtb_girr.ipynb`: end-to-end FRTB GIRR demo |

### Liquidity risk

| Ticket | Description |
|---|---|
| BKR-46 | `liquidity/lcr.py`: SA_LCR_Calculator — HQLA caps, outflow/inflow rates |
| BKR-47 | `liquidity/nsfr.py`: SA_NSFR_Calculator — ASF/RSF factor tables |
| BKR-48 | `liquidity/intraday.py`: Intraday_Monitor — BCBS 248 daily monitoring tools |
| BKR-49 | `liquidity/funding_gap.py`: Funding_Gap_Analyser — maturity ladder and rollover risk |
| BKR-50 | `liquidity/collateral.py`: Collateral_Manager — encumbrance ratio, HQLA buffer |
| BKR-51 | `liquidity/stress.py`: Liquidity_Stress_Calculator — idiosyncratic / market-wide / combined |
| BKR-52 | `liquidity/ewi.py`: EWI_Monitor — traffic-light dashboard, CFP triggers |
| BKR-53 | `liquidity/ilaap.py`: ILAAP_Aggregator — adequacy status from all liquidity metrics |

# notice on implementation

No need to use from __future__ import annotations
 we are usign python 3.13
