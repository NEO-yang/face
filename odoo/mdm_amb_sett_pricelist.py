for rec in self:
            pricelists = self.search([('sell_amb_unit_id', '=', rec.sell_amb_unit_id.id), ('delete_state','=','normal')])
            # 当前价目表的买卖单元和有效日期与价目表%s有重叠
            message = _("The buyer and seller unit and effective date of the current price list overlap with the price list %s, please re-enter")
            for pricelist in pricelists:
                if not (rec.active_date > pricelist.expired_date or rec.expired_date < pricelist.active_date):
                    if not pricelist.amb_buy_strategy or not rec.amb_buy_strategy:
                        raise ValidationError(message %pricelist.name)
                    else:
                        same_ids = [unitid for unitid in rec.buy_amb_unit_ids.ids if unitid in pricelist.buy_amb_unit_ids.ids]
                        if same_ids:
                            raise ValidationError(message %pricelist.name)
