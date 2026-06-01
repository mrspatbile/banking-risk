![Python](https://img.shields.io/badge/Python-3.13-blue?logo=python&logoColor=white)
![CRR3](https://img.shields.io/badge/Reg-CRR3-orange)
![CRD](https://img.shields.io/badge/reg-CRD_VI-purple)
![Tests](https://github.com/mrspatbile/banking-risk/actions/workflows/test.yml/badge.svg)
![Tests passing](https://img.shields.io/badge/tests-462%20passing-brightgreen)

# banking-risk


This repository implements **regulatory risk frameworks** as executable logic, translating IRRBB, FRTB, CSRBB, and ICAAP requirements into computation, aggregation, decomposition, and reporting layers.

All curve construction, instrument pricing, scenario simulation and risk sensitivities are delegated to [quant-risk-engine](https://github.com/mrspatbile/quant-risk-engine), which provides the underlying quantitative primitives used across regulatory models.


---

## Regulatory scope

<small>

| Module | Regulation |
|---|---|


| Module     | Regulatory reference                    |
| ---------- | --------------------------------------- |
| `irrbb/*`  | EBA/RTS/2022/10                         |
| `csrbb/*`  | EBA/GL/2022/14                          |
| `frtb/*`   | CRR3 Art. 325bb                         |
| `lcr.py`   | CRR + DR 2015/61 + EBA/GL/2019/02 (reporting/outflow rates) |
| `nsfr.py`  | CRR (Arts. 428a et seq.)                |
| `ilaap.py` | EBA/GL/2021/01 + ECB ILAAP Guide |
| `credit_risk/` |  CRR Art. 153 (IRB formula), Art. 163 (PD), Art. 228–230 (LGD)                   | 

**Approach**: SA for FRTB and IRRBB. Implements CRR3 prescribed 
vertex grids, risk class bucketing, within-bucket netting, 
correlation matrices, and capital K/S computation. Regulatory features: curvature via full repricing, collateral haircut LGD, EVE/NII repricing gaps per EBA/RTS/2022/10.




</small>

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

Verify:

```bash
pytest tests/ -v
```

---

## Notebooks

Notebooks illustrate usage of the features implemented in the package.

```
notebooks/
01_irrbb.ipynb  
02_frtb_girr.ipynb                  
03_csrbb.ipynb       
04_credit_risk.ipynb            
05_liquidity_ratios.ipynb     
06_liquidity_monitoring.ipynb
07_frtb_sa.ipynb     
```
---

## Project layout

```
📁 src/banking_risk/
│
├── 📁 irrbb/
│   ├── scenarios.py
│   ├── nii.py
│   ├── eve.py
│   ├── gap.py
│   ├── book.py
│   └── constants.py
│
├── 📁 csrbb/
│   └── spread_risk.py
│
├── 📁 frtb/
│   ├── 📁 girr/       
│   ├── 📁 commodity/  
│   ├── 📁 csr/        
│   ├── 📁 fx/         
│   ├── 📁 equity/     
│   ├── sensitivity_engine.py
│   ├── sa.py
│   ├── vertex_mapping.py
│   ├── aggregator.py
│   ├── constants.py
│   └── portfolio.py
│
├── 📁 credit_risk/
│   ├── pd.py
│   ├── lgd.py
│   └── el.py
│
├── 📁  liquidity/
│   ├── collateral.py
│   ├── funding_gap.py
│   ├── intraday.py
│   ├── nsfr.py
│   ├── lcr.py
│   ├── ilaap.py
│   ├── stress.py
│   └── ewi.py
│
├── 📁 shared/
│   ├── curve_projection.py
│   ├── curves.py
│   └── dates.py
│
📁 tests/
    └── test_*.py  (462 tests)

 ```
---

## Tests

```bash
pytest tests/ -v
```

CI runs on every push and pull request to `main` via GitHub Actions (`.github/workflows/test.yml`).

