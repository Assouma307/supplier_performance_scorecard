from calendar import monthrange
from datetime import date

from odoo import fields, models, _
from odoo.exceptions import UserError


class SupplierScorecardBatchWizard(models.TransientModel):
    _name = "supplier.performance.scorecard.batch.wizard"
    _description = "Generate Supplier Scorecards"

    company_ids = fields.Many2many(
        "res.company", string="Companys", required=True,
        default=lambda self: self.env.companies,
    )
    period_start = fields.Date(required=True, default=lambda self: date.today().replace(day=1))
    period_end = fields.Date(required=True, default=lambda self: date.today().replace(day=monthrange(date.today().year, date.today().month)[1]))
    include_existing = fields.Boolean(
        string="Include Existing Scorecards", default=False,
        help="If enabled, existing scorecards are opened in the result but are not duplicated.",
    )

    def action_generate(self):
        self.ensure_one()
        if self.period_start > self.period_end:
            raise UserError(_("The start date must be on or before the end date."))
        companies = self.company_ids.filtered(lambda company: company in self.env.companies)
        if not companies:
            raise UserError(_("Select at least one company you can access."))

        partners = self.env["res.partner"].with_context(active_test=False).search([
            ("supplier_rank", ">", 0),
            ("active", "=", True),
        ], order="name, id")
        Scorecard = self.env["supplier.performance.scorecard"]
        scorecard_ids = []
        created = 0
        for company in companies:
            existing = Scorecard.with_company(company).search([
                ("company_id", "=", company.id),
                ("period_start", "=", self.period_start),
                ("period_end", "=", self.period_end),
            ])
            existing_keys = set(existing.mapped("supplier_id").ids)
            if self.include_existing:
                scorecard_ids.extend(existing.ids)
            vals_list = [{
                "supplier_id": partner.id,
                "company_id": company.id,
                "period_start": self.period_start,
                "period_end": self.period_end,
            } for partner in partners if partner.id not in existing_keys]
            if vals_list:
                new_records = Scorecard.with_company(company).create(vals_list)
                scorecard_ids.extend(new_records.ids)
                created += len(new_records)

        if not scorecard_ids:
            if self.include_existing:
                raise UserError(_("No supplier scorecard was found or generated. Check that supplier contacts exist and are configured as suppliers."))
            raise UserError(_("No new scorecards were generated. Existing scorecards were skipped; enable “Include Existing Scorecards” to open them."))
        action = {
            "type": "ir.actions.act_window",
            "name": _("Supplier Scorecards"),
            "res_model": "supplier.performance.scorecard",
            "view_mode": "list,form",
            "domain": [("id", "in", list(set(scorecard_ids)))],
            "target": "current",
        }
        action["context"] = {"search_default_group_by_company": 0}
        return action
