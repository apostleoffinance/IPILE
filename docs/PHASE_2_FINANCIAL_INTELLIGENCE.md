# Phase 2 — Financial Intelligence Engine

**Status:** Implementation in progress  
**Predecessor:** Phase 1 — PR #70 (automatic bank-alert ingestion and user controls)

## Objective

Turn provider-delivered bank alerts into normalized, explainable financial events. Gmail and Cloudflare forwarding are adapters; neither owns classification, account matching, confidence scoring, or ledger rules.

## Delivered in this phase

- Provider-neutral normalized event envelope with provider and provider-event identifiers.
- Deterministic transaction categorization against categories already configured by each household.
- Bank-domain-to-institution alias matching; account suggestion is accepted only when unique.
- Explicit currency/account compatibility checks; unknown currency never inherits a guessed currency.
- Explainable confidence score and band with review reasons.
- Review payload enrichment for suggested category, account, confidence and normalized event.
- Automatic posting remains gated by the existing trusted sender, exact unique account and explicit matching currency rules, plus a high-confidence threshold.
- No email body or unrelated inbox content is persisted by the intelligence layer.

## Confidence model

| Signal | Points |
|---|---:|
| Provider has verified sender authentication | 25 |
| Positive parsed amount | 15 |
| Valid transaction date | 15 |
| Unambiguous income/expense direction | 15 |
| Explicit ISO currency / unambiguous currency symbol | 15 |
| Unique institution and currency-compatible account | 15 |
| Existing household category matched by deterministic rule | 5 |

Scores are capped at 100. High is 85–100, medium is 65–84, low is below 65. This score is an explainability and routing aid, not a substitute for the non-negotiable auto-posting safety gates.

## Safety invariants

- No model-generated or speculative financial values.
- No account or currency guessing.
- Suggestions only reference categories that exist in the household.
- Provider event identifiers are metadata; bank transaction identity remains the cross-provider deduplication key.
- A review correction does not change ledger balances until the user approves it.
- All ledger writes continue through the existing transaction/import service.

## Acceptance tests

- Bank sender aliases resolve GTBank, UBA and OPay to their institution keys.
- Multiple candidate accounts remain unresolved.
- Currency mismatch cannot become an exact account match.
- Confidence score exposes reasons and cannot be high when currency/account signals are missing.
- Existing import, Gmail and Cloudflare tests remain green.
