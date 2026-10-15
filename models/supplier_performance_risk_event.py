from odoo import api, fields, models, _


class SupplierPerformanceRiskEvent(models.Model):
    _name = "supplier.performance.risk.event"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Supplier Risk Alert"
    _order = "detected_at desc, id desc"
    _rec_name = "name"

    name = fields.Char(required=True, readonly=True)
    scorecard_id = fields.Many2one(
        "supplier.performance.scorecard", required=True, readonly=True,
        ondelete="cascade", index=True,
    )
    supplier_id = fields.Many2one("res.partner", required=True, readonly=True, index=True)
    company_id = fields.Many2one("res.company", required=True, readonly=True, index=True)
    rule_code = fields.Selection(
        [
            ("score_critical", "Critical score"),
            ("score_high", "Low score"),
            ("score_drop", "Score deterioration"),
            ("repeated_late", "Repeated late receipts"),
        ], required=True, readonly=True, index=True,
    )
    severity = fields.Selection(
        [("moderate", "Moderatee"), ("high", "Highe"), ("critical", "Critical")],
        required=True, readonly=True, index=True,
    )
    description = fields.Text(readonly=True)
    detected_at = fields.Datetime(required=True, readonly=True, default=fields.Datetime.now, index=True)
    score_at_detection = fields.Float(readonly=True, digits=(5, 2))
    previous_score = fields.Float(readonly=True, digits=(5, 2))
    state = fields.Selection(
        [("new", "New"), ("in_progress", "In Progress"), ("resolved", "Resolved")],
        required=True, default="new", index=True,
    )
    active_key = fields.Char(index=True, copy=False, readonly=True)

    _sql_constraints = [
        ("active_risk_event_unique", "unique(active_key)",
         "An active alert already exists for this scorecard and rule."),
    ]

    @api.model
    def _ensure_event(self, scorecard, rule_code, severity, title, description, previous_score=None):
        key = "%s:%s" % (scorecard.id, rule_code)
        existing = self.search([("active_key", "=", key)], limit=1)
        values = {
            "name": title,
            "scorecard_id": scorecard.id,
            "supplier_id": scorecard.supplier_id.id,
            "company_id": scorecard.company_id.id,
            "rule_code": rule_code,
            "severity": severity,
            "description": description,
            "detected_at": fields.Datetime.now(),
            "score_at_detection": scorecard.score,
            "previous_score": previous_score if previous_score is not None else 0.0,
            "active_key": key,
        }
        if existing:
            # Keep the original detection date and follow-up state; update the supporting evidence.
            existing.write({
                "severity": severity,
                "description": description,
                "score_at_detection": scorecard.score,
                "previous_score": previous_score if previous_score is not None else 0.0,
            })
            return existing
        return self.create(values)

    @api.model
    def detect_for_scorecard(self, scorecard):
        """Create or update active alerts for an evaluated scorecard without duplicates."""
        scorecard.ensure_one()
        if not scorecard.last_evaluated_at:
            return True

        triggered = set()
        score = scorecard.score or 0.0
        insufficient_data = scorecard.confidence == "insufficient"

        if score < 50:
            triggered.add("score_critical")
            self._ensure_event(
                scorecard, "score_critical", "critical",
                _("Supplier score is critical"),
                (
                    _("The overall score is %(score).2f/100, below the critical threshold of 50. ")
                    + (_("Note: available data is insufficient to ensure this assessment is reliable.") if insufficient_data else "")
                ) % {"score": score},
            )
        elif score < 70:
            triggered.add("score_high")
            self._ensure_event(
                scorecard, "score_high", "high",
                _("Supplier score requires attention"),
                (
                    _("The overall score is %(score).2f/100, below the attention threshold of 70. ")
                    + (_("Note: available data is insufficient to ensure this assessment is reliable.") if insufficient_data else "")
                ) % {"score": score},
            )

        evaluations = self.env["supplier.performance.evaluation"].search(
            [("scorecard_id", "=", scorecard.id)], order="evaluated_at desc, id desc", limit=2
        )
        if len(evaluations) == 2:
            latest, previous = evaluations[0], evaluations[1]
            drop = (previous.score or 0.0) - (latest.score or 0.0)
            if drop >= 15:
                triggered.add("score_drop")
                self._ensure_event(
                    scorecard, "score_drop", "high",
                    _("Supplier performance has deteriorated"),
                    _("The score decreased by %(drop).2f points, from %(previous).2f to %(current).2f.") % {
                        "drop": drop, "previous": previous.score, "current": latest.score,
                    },
                    previous_score=previous.score,
                )

        recent_pickings = self.env["stock.picking"].search([
            ("state", "=", "done"),
            ("picking_type_id.code", "=", "incoming"),
            ("purchase_id.partner_id", "=", scorecard.supplier_id.id),
            ("company_id", "=", scorecard.company_id.id),
            ("date_done", "!=", False),
            ("scheduled_date", "!=", False),
        ], order="date_done desc, id desc", limit=5)
        evaluable = len(recent_pickings)
        late_count = sum(
            1 for picking in recent_pickings
            if fields.Datetime.to_datetime(picking.date_done) > fields.Datetime.to_datetime(picking.scheduled_date)
        )
        if evaluable >= 5 and late_count >= 3:
            triggered.add("repeated_late")
            self._ensure_event(
                scorecard, "repeated_late", "high",
                _("Repeated late supplier receipts"),
                _("%(late)s of the last %(total)s evaluable receipts were late.") % {
                    "late": late_count, "total": evaluable,
                },
            )

        # Les alertes de seuil de score et de retards répétés sont clôturées automatiquement
        # lorsque les conditions ne sont plus réunies. Les alertes de dégradation restent ouvertes
        # until a user resolves them because they represent a detected trend.
        auto_resolve_codes = {"score_critical", "score_high", "repeated_late"} - triggered
        if auto_resolve_codes:
            stale = self.search([
                ("scorecard_id", "=", scorecard.id),
                ("rule_code", "in", list(auto_resolve_codes)),
                ("state", "!=", "resolved"),
            ])
            stale.write({"state": "resolved", "active_key": False})
        return True

    @api.model
    def cron_evaluate_supplier_risks(self):
        scorecards = self.env["supplier.performance.scorecard"].sudo().search([
            ("last_evaluated_at", "!=", False),
        ])
        RiskEvent = self.sudo()
        for scorecard in scorecards:
            RiskEvent.detect_for_scorecard(scorecard)
        return True

    def action_open_scorecard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Supplier Scorecard"),
            "res_model": "supplier.performance.scorecard",
            "view_mode": "form",
            "res_id": self.scorecard_id.id,
            "target": "current",
        }

    def action_mark_in_progress(self):
        self.write({"state": "in_progress"})
        return True

    def action_resolve(self):
        self.write({"state": "resolved", "active_key": False})
        return True

    def action_create_followup_activity(self):
        self.ensure_one()
        activity_type = self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)
        model_id = self.env["ir.model"]._get_id(self._name)
        self.env["mail.activity"].create({
            "activity_type_id": activity_type.id if activity_type else False,
            "res_model_id": model_id,
            "res_id": self.id,
            "user_id": self.env.user.id,
            "date_deadline": fields.Date.context_today(self),
            "summary": self.name,
            "note": self.description or self.name,
        })
        if self.state == "new":
            self.state = "in_progress"
        return True
