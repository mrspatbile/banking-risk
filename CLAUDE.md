# CLAUDE.md — banking-risk

## What this project is

Banking regulatory risk applications built on quant-risk-engine.
Covers IRRBB EVE/NII SOT, FRTB SA GIRR, ICAAP stress testing.

The library at quant-risk-engine handles all curve construction,
instrument pricing, and model simulation. This repo applies
that infrastructure to regulatory and internal risk frameworks.
No pricing logic lives here — only domain application.

## Stack

- Python 3.13
- quant-risk-engine (local editable install)
- QuantLib via quant-risk-engine

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
| CRR3 Art. 325 | FRTB SA GIRR delta, prescribed vertices |
| EBA/GL/2022/14 | IRRBB governance, NMD modelling |

## Running

    python -m venv .venv
    source .venv/bin/activate
    pip install -e /path/to/quant-risk-engine
    pip install -e .[dev]
    cp .env.example .env   # add API keys
    nbstripout --install
    pytest tests/ -v
    jupyter lab
```

---

## 12. Install sequence (first time)

```bash
python -m venv .venv
source .venv/bin/activate

# install quant-risk-engine as editable dependency
pip install -e /path/to/quant-risk-engine

# install this project
pip install -e .[dev]

# configure notebook output stripping
nbstripout --install

# environment
cp .env.example .env
# edit .env with your keys

# verify
pytest tests/ -v
```

---

## 13. First notebooks to add

```
notebooks/
├── 01_irrbb/
│   ├── 01_eve_sot.ipynb       ← move from quant-risk-engine nb03
│   └── 02_nii_sot.ipynb
├── 02_frtb/
│   └── 01_girr_delta.ipynb
└── 03_icaap/
```