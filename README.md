# banking-risk

Banking regulatory risk applications built on [quant-risk-engine](https://github.com/mrspatbile/quant-risk-engine).

Covers IRRBB EVE/NII supervisory outlier tests, FRTB SA GIRR delta, CSRBB spread risk, and ICAAP credit risk components. All curve construction, instrument pricing, and model simulation lives in `quant-risk-engine`. This repo applies that infrastructure to regulatory and internal risk frameworks.

---

## Regulatory scope

| Module | Regulation | Metric |
|---|---|---|
| `irrbb/eve.py` | EBA/RTS/2022/10 | EVE SOT — 15% Tier 1 threshold |
| `irrbb/nii.py` | EBA/RTS/2022/10 | NII SOT — 5% Tier 1 threshold |
| `irrbb/scenarios.py` | EBA/RTS/2022/10 | 6 EBA supervisory shock scenarios |
| `frtb/girr.py` | CRR3 Art. 325 | SA GIRR delta risk charge |
| `csrbb/spread_risk.py` | EBA/GL/2022/14 | Credit spread risk in the banking book |
| `credit_risk/` | Internal / ICAAP | PD, LGD, EL |

---

## Stack

- Python 3.13
- [quant-risk-engine](https://github.com/mrspatbile/quant-risk-engine) — curve construction, QuantLib pricing
- numpy / scipy / pandas — numerical core
- matplotlib / plotly / seaborn — visualisation
- JupyterLab — interactive analysis

---

## Setup

Clone both repos side by side:

```bash
git clone https://github.com/mrspatbile/quant-risk-engine.git
git clone https://github.com/mrspatbile/banking-risk.git
```

Create a virtual environment and install:

```bash
cd banking-risk
python3 -m venv .venv
source .venv/bin/activate

pip install -e ../quant-risk-engine
pip install -e .[dev]
```

Configure environment variables:

```bash
cp .env.example .env
# add FRED_API_KEY to .env
```

Activate notebook output stripping:

```bash
nbstripout --install
```

Verify:

```bash
pytest tests/ -v
```

---

## Notebooks

Open from the project root with the venv active:

```bash
jupyter lab
```

Notebooks are numbered and must be run in order — each writes processed data to `data/processed/` for the next to consume.

```
notebooks/
├── 01_yield_curves/
│   ├── 01_nss_curves.ipynb        ECB NSS AAA and all-issuers curves
│   └── 02_ois_bootstrap.ipynb     ESTR OIS curve bootstrap via QuantLib
├── 02_irrbb/
│   ├── 01_eve_sot.ipynb           EVE supervisory outlier test, 6 scenarios
│   ├── 02_nii_sot.ipynb           NII supervisory outlier test
│   └── 03_repricing_gap.ipynb     Repricing gap analysis
├── 03_frtb/
│   └── 01_girr_delta.ipynb        FRTB SA GIRR delta charge
└── 04_icaap/
```

---

## Project layout

```
src/banking_risk/
├── config.py          Path constants, API keys, auto-create data dirs
├── logging.py         Rotating file logger for the banking_risk namespace
├── irrbb/
│   ├── scenarios.py   EBA rate shock vectors (6 scenarios)
│   ├── eve.py         EVE SOT calculation and outlier flag
│   └── nii.py         NII SOT calculation and outlier flag
├── frtb/
│   └── girr.py        FRTB SA GIRR delta aggregation
├── csrbb/
│   └── spread_risk.py Credit spread sensitivity in the banking book
├── credit_risk/
│   ├── pd.py          Probability of default
│   ├── lgd.py         Loss given default
│   └── el.py          Expected loss: EL = PD × LGD × EAD
└── utils/
    └── style.py       Shared matplotlib/pandas style for notebooks
```

---

## Tests

```bash
pytest tests/ -v
```

CI runs on every push and pull request to `main` via GitHub Actions (`.github/workflows/test.yml`).

---

## Data

Raw and processed data are gitignored. The pipeline uses:

- `data/cache/` — raw API responses (ECB SDW, FRED)
- `data/processed/` — serialised curves and cashflow data (Parquet)

Neither directory is committed. Run the yield curve notebooks first to populate `data/processed/` before running any IRRBB or FRTB notebooks.

---

## Common errors

**`ModuleNotFoundError: quant_risk`**
Reinstall the editable dependency: `pip install -e ../quant-risk-engine`

**`FileNotFoundError: No OIS curve file found in data/processed/`**
Run `01_yield_curves/02_ois_bootstrap.ipynb` before any IRRBB notebook.

**ECB API returns no data**
The ECB SDW API has occasional downtime. Retry after a few minutes.

**`ValueError: No data available on or before ...`**
Increase `last_n` in the `NSSCurve.from_ecb` call or re-run the NSS notebook to fetch fresh data.
