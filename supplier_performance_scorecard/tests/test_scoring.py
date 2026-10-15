from odoo.tests.common import TransactionCase

from ..services.scoring_engine import SupplierScoringEngine


class TestSupplierScoringEngine(TransactionCase):
    def test_weighted_score(self):
        self.assertEqual(SupplierScoringEngine.calculate_score(100, 50), 85.0)

    def test_missing_component_renormalizes_weight(self):
        self.assertEqual(SupplierScoringEngine.calculate_score(80, None), 80.0)
        self.assertEqual(SupplierScoringEngine.calculate_score(None, 60), 60.0)

    def test_no_component_is_zero(self):
        self.assertEqual(SupplierScoringEngine.calculate_score(None, None), 0.0)

    def test_risk_levels(self):
        self.assertEqual(SupplierScoringEngine.classify_risk(90, "high"), "low")
        self.assertEqual(SupplierScoringEngine.classify_risk(80, "high"), "moderate")
        self.assertEqual(SupplierScoringEngine.classify_risk(60, "high"), "high")
        self.assertEqual(SupplierScoringEngine.classify_risk(20, "high"), "critical")
        self.assertEqual(SupplierScoringEngine.classify_risk(99, "insufficient"), "insufficient")

    def test_confidence_levels(self):
        self.assertEqual(SupplierScoringEngine.classify_confidence(0), "insufficient")
        self.assertEqual(SupplierScoringEngine.classify_confidence(3), "low")
        self.assertEqual(SupplierScoringEngine.classify_confidence(10), "medium")
        self.assertEqual(SupplierScoringEngine.classify_confidence(30), "high")
