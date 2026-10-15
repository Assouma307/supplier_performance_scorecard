from datetime import date

from odoo.tests.common import TransactionCase


class TestSupplierRiskEvent(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.supplier = cls.env["res.partner"].create({"name": "Risk Event Test Supplier"})
        cls.scorecard = cls.env["supplier.performance.scorecard"].create({
            "supplier_id": cls.supplier.id,
            "company_id": cls.company.id,
            "period_start": date(2026, 1, 1),
            "period_end": date(2026, 1, 31),
        })

    def test_critical_score_creates_one_active_event(self):
        self.scorecard.write({
            "score": 42.0,
            "confidence": "medium",
            "risk_level": "critical",
            "last_evaluated_at": "2026-01-31 12:00:00",
        })
        RiskEvent = self.env["supplier.performance.risk.event"]
        RiskEvent.detect_for_scorecard(self.scorecard)
        RiskEvent.detect_for_scorecard(self.scorecard)
        events = RiskEvent.search([
            ("scorecard_id", "=", self.scorecard.id),
            ("rule_code", "=", "score_critical"),
            ("state", "!=", "resolved"),
        ])
        self.assertEqual(len(events), 1)
        self.assertEqual(events.severity, "critical")

    def test_resolved_event_can_be_recreated_if_risk_returns(self):
        self.scorecard.write({
            "score": 40.0,
            "confidence": "medium",
            "risk_level": "critical",
            "last_evaluated_at": "2026-01-31 12:00:00",
        })
        RiskEvent = self.env["supplier.performance.risk.event"]
        RiskEvent.detect_for_scorecard(self.scorecard)
        first_event = RiskEvent.search([
            ("scorecard_id", "=", self.scorecard.id),
            ("rule_code", "=", "score_critical"),
            ("state", "!=", "resolved"),
        ], limit=1)
        first_event.action_resolve()
        RiskEvent.detect_for_scorecard(self.scorecard)
        active = RiskEvent.search([
            ("scorecard_id", "=", self.scorecard.id),
            ("rule_code", "=", "score_critical"),
            ("state", "!=", "resolved"),
        ])
        self.assertEqual(len(active), 1)
        self.assertNotEqual(active.id, first_event.id)
