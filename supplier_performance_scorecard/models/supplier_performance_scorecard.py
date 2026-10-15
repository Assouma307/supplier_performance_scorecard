from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

from ..services.scoring_engine import SupplierScoringEngine


class SupplierPerformanceScorecard(models.Model):
    _name = "supplier.performance.scorecard"
    _description = "Supplier Performance Scorecard"
    _order = "score desc, supplier_id"

    name = fields.Char(string="Reference", compute="_compute_name", store=True)
    supplier_id = fields.Many2one(
        "res.partner", string="Supplier", required=True, index=True,
        domain="[('supplier_rank', '>', 0)]", ondelete="cascade",
    )
    company_id = fields.Many2one(
        "res.company", string="Company", required=True,
        default=lambda self: self.env.company, index=True,
    )
    period_start = fields.Date(string="Period Start", required=True, index=True)
    period_end = fields.Date(string="Period End", required=True, index=True)
    total_receipts = fields.Integer(string="Evaluable Receipts", readonly=True, default=0)
    on_time_receipts = fields.Integer(string="On-time Receipts", readonly=True, default=0)
    late_receipts = fields.Integer(string="Late Receipts", readonly=True, default=0)
    receipts_missing_planned_date = fields.Integer(string="Receipts Missing Planned Date", readonly=True, default=0)
    evaluated_purchase_orders = fields.Integer(string="Evaluated Purchase Orders", readonly=True, default=0)
    punctuality_score = fields.Float(string="Punctuality (%)", digits=(5, 2), readonly=True, default=0.0)
    completeness_score = fields.Float(string="Order Completeness (%)", digits=(5, 2), readonly=True, default=0.0)
    has_punctuality_data = fields.Boolean(readonly=True, default=False)
    has_completeness_data = fields.Boolean(readonly=True, default=False)
    score = fields.Float(
        string="Overall Score (%)", digits=(5, 2), readonly=True, default=0.0,
        help="Weighted score calculated from receipt punctuality and purchase order completeness.",
    )
    confidence = fields.Selection(
        [("insufficient", "Insufficient data"), ("low", "Low"), ("medium", "Mediumne"), ("high", "Highe")],
        string="Data Confidence", readonly=True, default="insufficient",
    )
    risk_level = fields.Selection(
        [("insufficient", "Insufficient data"), ("low", "Low Risk"), ("moderate", "Moderate Risk"),
         ("high", "High Risk"), ("critical", "Critical Risk")],
        string="Risk Level", readonly=True, default="insufficient", index=True,
    )
    last_evaluated_at = fields.Datetime(string="Last Evaluated At", readonly=True)
    formula_version = fields.Char(string="Formula Version", readonly=True)
    evaluation_note = fields.Text(string="Calculation Notes", readonly=True)
    evaluation_ids = fields.One2many(
        "supplier.performance.evaluation", "scorecard_id", string="Evaluations History", readonly=True,
    )

    _sql_constraints = [
        ("supplier_company_period_unique", "unique(supplier_id, company_id, period_start, period_end)",
         "A scorecard already exists for this supplier, company and period."),
    ]

    @api.depends("supplier_id", "company_id", "period_start", "period_end")
    def _compute_name(self):
        for rec in self:
            period = "%s - %s" % (rec.period_start or "?", rec.period_end or "?")
            rec.name = "%s — %s — %s" % (
                rec.supplier_id.display_name or _("Supplier"),
                rec.company_id.name or "", period,
            )

    @api.constrains("period_start", "period_end")
    def _check_period(self):
        for rec in self:
            if not rec.period_start or not rec.period_end:
                raise ValidationError(_("The period start and end dates are required."))
            if rec.period_start > rec.period_end:
                raise ValidationError(_("The start date must be on or before the end date."))

    @api.constrains("supplier_id", "company_id")
    def _check_supplier_company(self):
        for rec in self:
            if rec.supplier_id and rec.company_id and rec.company_id not in self.env.companies:
                # Do not reject legitimate records in another allowed company; only
                # prevent accidental evaluation outside the active allowed-company set.
                raise ValidationError(_("You cannot create a scorecard for a company you cannot access."))

    def action_recompute_score(self):
        engine = SupplierScoringEngine()
        for rec in self:
            if not rec.supplier_id:
                raise UserError(_("Please select a supplier first."))
            if not rec.period_start or not rec.period_end:
                raise UserError(_("Please enter both period dates before evaluating the supplier."))
            values = engine.compute(rec)
            now = fields.Datetime.now()
            values.update({"last_evaluated_at": now})
            rec.write(values)
            history_values = dict(values)
            history_values.pop("last_evaluated_at", None)
            rec.env["supplier.performance.evaluation"].create({
                "scorecard_id": rec.id,
                "supplier_id": rec.supplier_id.id,
                "company_id": rec.company_id.id,
                "period_start": rec.period_start,
                "period_end": rec.period_end,
                "evaluated_at": now,
                **history_values,
            })
            # Detect risks immediately after a successful evaluation.
            rec.env["supplier.performance.risk.event"].detect_for_scorecard(rec)
        return True

    def action_open_supplier(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Supplier"),
            "res_model": "res.partner",
            "view_mode": "form",
            "res_id": self.supplier_id.id,
            "target": "current",
        }

    def action_view_history(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Evaluations History"),
            "res_model": "supplier.performance.evaluation",
            "view_mode": "list,form",
            "domain": [("scorecard_id", "=", self.id)],
            "context": {"default_scorecard_id": self.id},
            "target": "current",
        }
