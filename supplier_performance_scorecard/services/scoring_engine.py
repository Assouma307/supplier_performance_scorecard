from collections import defaultdict
from datetime import timedelta

from odoo import fields, _


class SupplierScoringEngine:
    """Calculation service separated from ORM presentation models.

    Punctuality is measured per completed incoming picking in the selected
    receipt-completion period. Therefore, split/partial receipts are separate
    receipt events for punctuality. Completion is measured at purchase-order
    level using the current received quantities of the orders represented by
    those pickings.
    """

    PUNCTUALITY_WEIGHT = 0.70
    COMPLETENESS_WEIGHT = 0.30
    FORMULA_VERSION = "1.0"

    @staticmethod
    def calculate_score(punctuality_score, completeness_score):
        """Return a weighted score, renormalizing when one component is absent."""
        components = []
        if punctuality_score is not None:
            components.append((punctuality_score, SupplierScoringEngine.PUNCTUALITY_WEIGHT))
        if completeness_score is not None:
            components.append((completeness_score, SupplierScoringEngine.COMPLETENESS_WEIGHT))
        if not components:
            return 0.0
        total_weight = sum(weight for _, weight in components)
        return round(sum(score * weight for score, weight in components) / total_weight, 2)

    @staticmethod
    def classify_risk(score, confidence="high"):
        if score is None or confidence == "insufficient":
            return "insufficient"
        if score >= 85:
            return "low"
        if score >= 70:
            return "moderate"
        if score >= 50:
            return "high"
        return "critical"

    @staticmethod
    def classify_confidence(evaluable_receipts):
        if evaluable_receipts < 3:
            return "insufficient"
        if evaluable_receipts < 10:
            return "low"
        if evaluable_receipts < 30:
            return "medium"
        return "high"

    def compute(self, scorecard):
        start_dt = fields.Datetime.to_datetime(scorecard.period_start)
        # Exclusive upper bound avoids timezone and 23:59:59 precision issues.
        end_exclusive = fields.Datetime.to_datetime(scorecard.period_end) + timedelta(days=1)
        domain = [
            ("state", "=", "done"),
            ("picking_type_id.code", "=", "incoming"),
            ("purchase_id.partner_id", "=", scorecard.supplier_id.id),
            ("company_id", "=", scorecard.company_id.id),
            ("date_done", ">=", start_dt),
            ("date_done", "<", end_exclusive),
        ]
        pickings = scorecard.env["stock.picking"].search(domain, order="date_done, id")

        punctuality_events = 0
        on_time = 0
        late = 0
        missing_planned_date = 0
        order_ids = set()

        for picking in pickings:
            if picking.purchase_id:
                order_ids.add(picking.purchase_id.id)
            if not picking.scheduled_date or not picking.date_done:
                missing_planned_date += 1
                continue
            punctuality_events += 1
            if fields.Datetime.to_datetime(picking.date_done) <= fields.Datetime.to_datetime(picking.scheduled_date):
                on_time += 1
            else:
                late += 1

        punctuality_score = (on_time / punctuality_events * 100.0) if punctuality_events else None

        # Completion is assessed at purchase-order level to avoid treating every
        # partial receipt as a complete order. It uses the current qty_received.
        orders = scorecard.env["purchase.order"].browse(sorted(order_ids)).exists()
        line_completion_percentages = []
        evaluated_order_count = 0
        for order in orders:
            order_has_evaluable_line = False
            for line in order.order_line:
                if line.display_type or not line.product_id or line.product_qty <= 0:
                    continue
                order_has_evaluable_line = True
                received_ratio = min(max(line.qty_received, 0.0) / line.product_qty, 1.0)
                line_completion_percentages.append(received_ratio * 100.0)
            if order_has_evaluable_line:
                evaluated_order_count += 1

        # Average line ratios instead of adding quantities from unrelated
        # products or units of measure.
        completeness_score = (
            sum(line_completion_percentages) / len(line_completion_percentages)
            if line_completion_percentages else None
        )
        overall_score = self.calculate_score(punctuality_score, completeness_score)
        confidence = self.classify_confidence(punctuality_events)
        risk_level = self.classify_risk(overall_score if (punctuality_score is not None or completeness_score is not None) else None, confidence)

        return {
            "total_receipts": punctuality_events,
            "on_time_receipts": on_time,
            "late_receipts": late,
            "receipts_missing_planned_date": missing_planned_date,
            "evaluated_purchase_orders": evaluated_order_count,
            "punctuality_score": round(punctuality_score, 2) if punctuality_score is not None else 0.0,
            "completeness_score": round(completeness_score, 2) if completeness_score is not None else 0.0,
            "has_punctuality_data": punctuality_score is not None,
            "has_completeness_data": completeness_score is not None,
            "score": overall_score,
            "confidence": confidence,
            "risk_level": risk_level,
            "formula_version": self.FORMULA_VERSION,
            "evaluation_note": _(
                "Formula v%(version)s: receipt punctuality accounts for 70%% and purchase order completeness "
                "for 30%%. Weights are recalculated if a component has no usable data. "
                "Punctuality is calculated per completed receipt; partial receipts are "
                "counted separately. Completeness uses the currently received quantities on purchase orders. "
                "Receipts without a scheduled date are excluded from the punctuality calculation. The scheduled date "
                "may have been changed after the supplier’s original commitment."
            ) % {"version": self.FORMULA_VERSION},
        }
