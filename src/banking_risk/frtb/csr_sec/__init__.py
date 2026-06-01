"""
FRTB CSR Securitisation (CRR3 Art. 325bi/bj) — BKR-60.

CSR with separate bucket structure for securitised credit exposures.

Non-CTP buckets (25): senior/non-senior × RMBS/CMBS/ABS/CLO/other
CTP buckets (16): index tranches, bespoke tranches

Higher risk weights than non-sec (up to 3.5%).
Within-bucket correlation: tenor × tranche seniority.
"""
