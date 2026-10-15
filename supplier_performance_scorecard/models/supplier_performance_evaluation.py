from odoo import api, fields, models, _


class SupplierPerformanceEvaluation(models.Model):
    _name = "supplier.performance.evaluation"
    _description = "Supplier Performance Evaluation"
    _order = "evaluated_at desc, id desc"
    _rec_name = "name"

    name = fields.Char(compute="_compute_name", store=True)
    scorecard_id = fields.Many2one("supplier.performance.scorecard", required=True, ondelete="cascade", index=True)
    supplier_id = fields.Many2one("res.partner", required=True, readonly=True, index=True)
    company_id = fields.Many2one("res.company", required=True, readonly=True, index=True)
    period_start = fields.Date(required=True, readonly=True)
    period_end = fields.Date(required=True, readonly=True)
    evaluated_at = fields.Datetime(required=True, readonly=True, index=True)
    total_receipts = fields.Integer(readonly=True)
    on_time_receipts = fields.Integer(readonly=True)
    late_receipts = fields.Integer(readonly=True)
    receipts_missing_planned_date = fields.Integer(readonly=True)
    evaluated_purchase_orders = fields.Integer(readonly=True)
    punctuality_score = fields.Float(digits=(5, 2), readonly=True)
    completeness_score = fields.Float(digits=(5, 2), readonly=True)
    has_punctuality_data = fields.Boolean(readonly=True)
    has_completeness_data = fields.Boolean(readonly=True)
    score = fields.Float(string="Overall Score (%)", digits=(5, 2), readonly=True)
    confidence = fields.Selection(
        [("insufficient", "Insufficient data"), ("low", "Low"), ("medium", "Mediumne"), ("high", "Highe")], readonly=True,
    )
    risk_level = fields.Selection(
        [("insufficient", "Insufficient data"), ("low", "Low Risk"), ("moderate", "Moderate Risk"),
         ("high", "High Risk"), ("critical", "Critical Risk")], readonly=True,
    )
    formula_version = fields.Char(readonly=True)
    evaluation_note = fields.Text(readonly=True)

    @api.depends("supplier_id", "period_start", "period_end", "evaluated_at")
    def _compute_name(self):
        for rec in self:
            rec.name = _("%s — from %s to %s — %s") % (
                rec.supplier_id.display_name or _("Supplier"),
                rec.period_start or "?", rec.period_end or "?", rec.evaluated_at or "?",
            )
