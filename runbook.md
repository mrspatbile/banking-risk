Good reference. Your `banking-risk` runbook should follow the same structure but is simpler since there is no database. Here is a draft:

````markdown
# Runbook

## Environment setup

#### 1. Clone dependencies

This repo depends on `quant-risk-engine`. Clone both repos side by side:

```bash
git clone https://github.com/mrspatbile/quant-risk-engine.git
git clone https://github.com/mrspatbile/banking-risk.git
```

#### 2. Create and activate virtual environment

```bash
cd banking-risk
python3 -m venv .venv
source .venv/bin/activate
```

#### 3. Install dependencies

```bash
pip3 install -e ../quant-risk-engine
pip3 install -e .
```

#### 4. Configure environment variables

Copy the example env file and add your API credentials:

```bash
cp .env.example .env
```

Required variables:

```
ECB_API_KEY=...
```

## Notebook execution sequence

Open notebooks from the **project root** with the venv active:

```bash
jupyter lab
```

Notebooks are numbered and must be run in order. Each notebook saves
processed data to `data/processed/` for consumption by the next:

**yield curves**

1. `01_yield_curves/01_nss_curves.ipynb` -- ECB NSS AAA and all-issuers curves
2. `01_yield_curves/02_ois_bootstrap.ipynb` -- ESTR OIS curve bootstrap via QuantLib

**IRRBB**

3. `02_irrbb/01_eve_sot.ipynb` -- EVE supervisory outlier test, 6 EBA scenarios
4. `02_irrbb/02_nii_sot.ipynb` -- NII supervisory outlier test, parallel shocks
5. `02_irrbb/03_repricing_gap.ipynb` -- repricing gap analysis, addendum

> Note: All notebooks fetch live data from the ECB API on first run and
> cache results in `data/processed/`. Subsequent runs load from cache.

## Common errors and fixes

#### Module not found
```bash
ModuleNotFoundError: quant_risk
```
Ensure `quant-risk-engine` is installed in the active venv:
```bash
pip3 install -e ../quant-risk-engine
```

#### No OIS curve file found
```bash
FileNotFoundError: No OIS curve file found in data/processed/
```
Run notebook `02_ois_bootstrap.ipynb` before any IRRBB notebooks.

#### ECB API returns no data
The ECB SDW API has occasional downtime. Wait and retry. If the issue
persists check `https://sdw-wsrest.ecb.europa.eu` for service status.

#### NSS parameters not available for date
```bash
ValueError: No data available on or before ...
```
The requested valuation date is older than the cached parameter history.
Increase `last_n` in the `NSSCurve.from_ecb` call or re-run the NSS
notebook to fetch fresh data.
````