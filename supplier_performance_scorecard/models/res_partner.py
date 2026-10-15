from odoo import fields, models, _


class ResPartner(models.Model):
    _inherit = "res.partner"

    supplier_scorecard_count = fields.Integer(compute="_compute_supplier_scorecard_count", string="Supplier Scorecards")

    def _compute_supplier_scorecard_count(self):
        counts = self.env["supplier.performance.scorecard"].read_group(
            [("supplier_id", "in", self.ids)], ["supplier_id"], ["supplier_id"]
        ) if self.ids else []
        count_map = {row["supplier_id"][0]: row["supplier_id_count"] for row in counts if row.get("supplier_id")}
        for partner in self:
            partner.supplier_scorecard_count = count_map.get(partner.id, 0)

    def action_open_supplier_scorecards(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Supplier Scorecards"),
            "res_model": "supplier.performance.scorecard",
            "view_mode": "list,form",
            "domain": [("supplier_id", "=", self.id)],
            "context": {"default_supplier_id": self.id},
        }
