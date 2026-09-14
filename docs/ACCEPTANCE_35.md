# Spec §35 product-level acceptance — Phase 14 evidence

| # | Criterion | Evidence |
|---|---|---|
| 1 | Income → allocation, obligations, budgets, STS, health | Phases 1–8 engines + APIs; fresh onboarding posts income (`test_new_family_onboards_without_seed`) |
| 2 | Bank balance ≠ Safe to Spend when commitments exist | Phase 4 STS tests / seed cash vs STS |
| 3 | ₦2m seed allocates to §7.3 | `test_seed_two_million_allocation_matches_spec` |
| 4 | Quarterly ₦450k → ₦150k/mo | Phase 3 obligation tests |
| 5 | Annual ₦600k → ₦50k/mo | Phase 3 obligation tests |
| 6 | Purchase ₦180k affordable / ₦500k buffer warning | Phase 4 purchase-check tests |
| 7 | Salon capital ≠ lifestyle spend | Phase 7 business tests |
| 8 | Health explainable component-by-component | Phase 8 `/financial-health/explain` |
| 9 | Household A cannot read B | `tests/test_tenancy.py` |
| 10 | No mock-mode flag | Architecture; `SEED_ON_START` only gates optional pilot data |
| 11 | AI never authors engine-foreign numbers | Phase 11 `InventingModel` rejection |
| 12 | Six-month seed shocks do not corrupt balances | Phase 8 analytics seed + simulation live-balance guards |
| 13 | Founding-family-only behavior is configuration, not product | Spec §0 litmus; engines have no tithe/baby hardcoding |
