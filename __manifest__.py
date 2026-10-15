{
    "name": "Supplier Performance & Risk Scorecard",
    "version": "19.0.1.3.4",
    "category": "Purchases",
    "summary": "Evaluate supplier performance and identify purchasing risks",
    "description": """
Supplier Performance & Risk Scorecard for Odoo 19 Community.

Features:
- Supplier scorecards by company and period
- Receipt punctuality and purchase order completeness indicators
- Explainable risk classification and alerts
- Evaluation history
- Bulk scorecard generation
- Company-scoped dashboard with KPIs, charts and analysis

MVP limitation: punctuality uses the currently recorded scheduled date on each
completed incoming receipt. Purchase order completeness uses currently received
quantities. If these values are edited later, a new evaluation of a past period
may differ from the earlier result. Each saved evaluation preserves its result
and calculation notes.
""",
    "author": "Supplier Performance Scorecard",
    "license": "LGPL-3",
    "price": 79.0,
    "currency": "EUR",
    "depends": ["purchase_stock", "mail"],
    "data": [
        "security/supplier_scorecard_security.xml",
        "security/ir.model.access.csv",
        "views/supplier_scorecard_views.xml",
        "views/supplier_evaluation_views.xml",
        "views/supplier_scorecard_batch_views.xml",
        "views/supplier_risk_event_views.xml",
        "views/supplier_performance_dashboard_views.xml",
        "views/res_partner_views.xml",
        "data/supplier_scorecard_cron.xml",
    ],
    "application": True,
    "installable": True,
}
