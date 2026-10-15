from datetime import date

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestSupplierScorecard(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.supplier = cls.env["res.partner"].create({
            "name": "Scorecard Test Supplier",
        })

    def test_create_scorecard_with_period(self):
        scorecard = self.env["supplier.performance.scorecard"].create({
            "supplier_id": self.supplier.id,
            "company_id": self.company.id,
            "period_start": date(2026, 1, 1),
            "period_end": date(2026, 1, 31),
        })
        self.assertEqual(scorecard.supplier_id, self.supplier)
        self.assertEqual(scorecard.risk_level, "insufficient")

    def test_invalid_period_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.env["supplier.performance.scorecard"].create({
                "supplier_id": self.supplier.id,
                "company_id": self.company.id,
                "period_start": date(2026, 2, 1),
                "period_end": date(2026, 1, 1),
            })

    def test_duplicate_period_is_rejected(self):
        values = {
            "supplier_id": self.supplier.id,
            "company_id": self.company.id,
            "period_start": date(2026, 3, 1),
            "period_end": date(2026, 3, 31),
        }
        self.env["supplier.performance.scorecard"].create(values)
        with self.assertRaises(Exception):
            with self.cr.savepoint():
                self.env["supplier.performance.scorecard"].create(values)
