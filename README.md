# Supplier Performance & Risk Scorecard — Odoo 19 Community

## Features
- Supplier scorecards by supplier, company and period.
- Receipt punctuality and purchase order completeness indicators.
- Weighted overall score, data confidence and risk level.
- Evaluation history and bulk scorecard generation.
- Risk alerts, follow-up activities and resolution workflow.
- Company-scoped dashboard, KPIs, charts and analysis.

## Installation
1. Copy `supplier_performance_scorecard` into your custom addons directory.
2. Restart Odoo and update the Apps list.
3. Install the module. Select French (`fr_FR`) as the user language to load the French translations.

## Calculation limitation
Punctuality uses the scheduled date currently recorded on each completed incoming receipt. Completeness uses currently received quantities on purchase orders. Later edits can affect a new evaluation of a past period; each saved evaluation preserves its result and calculation notes.
