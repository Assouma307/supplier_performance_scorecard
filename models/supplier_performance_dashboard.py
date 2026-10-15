from odoo import api, fields, models, _


class SupplierPerformanceDashboard(models.TransientModel):
    _name = "supplier.performance.dashboard"
    _description = "Supplier Performance Dashboard"

    company_id = fields.Many2one(
        "res.company", string="Company", required=True,
        default=lambda self: self.env.company, readonly=True,
    )
    evaluated_scorecard_count = fields.Integer(string="Evaluated Scorecards", compute="_compute_dashboard")
    supplier_count = fields.Integer(string="Evaluated Suppliers", compute="_compute_dashboard")
    average_score = fields.Float(string="Average Overall Score (%)", digits=(5, 2), compute="_compute_dashboard")
    average_punctuality = fields.Float(string="Average Punctuality (%)", digits=(5, 2), compute="_compute_dashboard")
    on_time_rate = fields.Float(string="On-time Receipt Rate (%)", digits=(5, 2), compute="_compute_dashboard")
    open_alert_count = fields.Integer(string="Open Alerts", compute="_compute_dashboard")
    critical_alert_count = fields.Integer(string="Critical Alerts", compute="_compute_dashboard")
    high_alert_count = fields.Integer(string="High Alerts", compute="_compute_dashboard")
    low_risk_count = fields.Integer(string="Low Risk", compute="_compute_dashboard")
    moderate_risk_count = fields.Integer(string="Moderate Risk", compute="_compute_dashboard")
    high_risk_count = fields.Integer(string="High Risk", compute="_compute_dashboard")
    critical_risk_count = fields.Integer(string="Critical Risk", compute="_compute_dashboard")
    insufficient_count = fields.Integer(string="Insufficient data", compute="_compute_dashboard")

    @api.depends("company_id")
    def _compute_dashboard(self):
        Scorecard = self.env["supplier.performance.scorecard"]
        RiskEvent = self.env["supplier.performance.risk.event"]
        for dashboard in self:
            company = dashboard.company_id or self.env.company
            base_domain = [("company_id", "=", company.id)]
            evaluated = Scorecard.search(base_domain + [("last_evaluated_at", "!=", False)])
            scored = evaluated.filtered(lambda rec: rec.confidence != "insufficient")
            punctual = evaluated.filtered("has_punctuality_data")
            receipt_total = sum(evaluated.mapped("total_receipts"))
            on_time_total = sum(evaluated.mapped("on_time_receipts"))
            open_events = RiskEvent.search(base_domain + [("state", "!=", "resolved")])

            dashboard.evaluated_scorecard_count = len(evaluated)
            dashboard.supplier_count = len(evaluated.mapped("supplier_id"))
            dashboard.average_score = sum(scored.mapped("score")) / len(scored) if scored else 0.0
            dashboard.average_punctuality = (
                sum(punctual.mapped("punctuality_score")) / len(punctual) if punctual else 0.0
            )
            dashboard.on_time_rate = (on_time_total / receipt_total * 100.0) if receipt_total else 0.0
            dashboard.open_alert_count = len(open_events)
            dashboard.critical_alert_count = len(open_events.filtered(lambda event: event.severity == "critical"))
            dashboard.high_alert_count = len(open_events.filtered(lambda event: event.severity == "high"))
            dashboard.low_risk_count = len(scored.filtered(lambda rec: rec.risk_level == "low"))
            dashboard.moderate_risk_count = len(scored.filtered(lambda rec: rec.risk_level == "moderate"))
            dashboard.high_risk_count = len(scored.filtered(lambda rec: rec.risk_level == "high"))
            dashboard.critical_risk_count = len(scored.filtered(lambda rec: rec.risk_level == "critical"))
            dashboard.insufficient_count = len(evaluated.filtered(lambda rec: rec.confidence == "insufficient"))

    def _open_action(self, action_xmlid, extra_domain=None):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(action_xmlid)
        model = action.get("res_model")
        domain = [("company_id", "=", self.company_id.id)]
        if model == "supplier.performance.risk.event":
            domain.append(("state", "!=", "resolved"))
        if extra_domain:
            domain.extend(extra_domain)
        action["domain"] = domain
        action["context"] = dict(self.env.context, allowed_company_ids=[self.company_id.id], default_company_id=self.company_id.id)
        return action

    def action_open_scorecards(self):
        return self._open_action("supplier_performance_scorecard.action_supplier_scorecard")

    def action_open_low_scores(self):
        return self._open_action(
            "supplier_performance_scorecard.action_supplier_scorecard",
            [("risk_level", "in", ["high", "critical"])],
        )

    def action_open_alerts(self):
        return self._open_action("supplier_performance_scorecard.action_supplier_risk_event")

    def action_open_critical_alerts(self):
        return self._open_action(
            "supplier_performance_scorecard.action_supplier_risk_event",
            [("severity", "=", "critical"), ("state", "!=", "resolved")],
        )

    def action_open_evaluations(self):
        return self._open_action("supplier_performance_scorecard.action_supplier_evaluation")

    def action_open_analytics(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "supplier_performance_scorecard.action_supplier_scorecard_analytics"
        )
        action["domain"] = [
            ("company_id", "=", self.company_id.id),
            ("last_evaluated_at", "!=", False),
        ]
        action["context"] = dict(
            self.env.context,
            allowed_company_ids=[self.company_id.id],
            search_default_group_by_risk=1,
        )
        return action
