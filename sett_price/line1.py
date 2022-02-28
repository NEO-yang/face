    @api.onchange('material_id')
    def _onchange_material_id(self):
        '''
        计价单位默认值值由物料带出
        '''
        for rec in self:
            rec.unit_id = rec.material_id.uom_id.id
            org_list = rec.parent_id.sell_amb_unit_id.amb_book_id.accting_sys_id.accting_org_ids.org_id.ids
            # 使用组织等于卖方阿米巴单元对应核算组织的物料
            return {
                'domain': {
                    'material_id': [('use_org_id', 'in', org_list)]
                }
            }

    @api.constrains('material_id')
    def _constrains_material_id(self):
        for rec in self:
            if rec.material_id.use_org_id not in rec.parent_id.sell_amb_unit_id.amb_book_id.accting_sys_id.accting_org_ids.org_id.ids