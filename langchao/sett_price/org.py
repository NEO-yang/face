    ################################  字段定义区 start  ################################
    use_org_ids = fields.Many2many(compute='_compute_use_org_ids')
    ################################  字段定义区 end    ################################


    ################################  计算方法区 start  ################################

    @api.depends('sell_amb_unit_id')
    def _compute_use_org_ids(self):
        """
        计算卖方阿米巴单元的结算组织及其下属组织字段
        """
        if self.sell_amb_unit_id:
            # 卖方阿米巴归属核算组织
            sell_amb_org_id = self.sell_amb_unit_id.accting_org_id.id
            accting_sys = self.amb_org_sys_id.accting_sys_id
            if self._is_available_accting_sys(accting_sys):
                accting_sys_id = accting_sys.id
                # 对应会计核算体系下，该核算组织下业务组织
                accting_sys_line_obj = self.env['mdm.accounting.system.line1']
                accting_sys_line = accting_sys_line_obj.search(
                    [('delete_state', '=', 'normal'), 
                    ('parent_id', '=', accting_sys_id), 
                    ('org_id', '=', sell_amb_org_id)], 
                    limit=1)
                self.use_org_ids = accting_sys_line.accting_org_line_ids.org_id.ids
            else:
                self.use_org_ids = False
        else:
            self.use_org_ids = False

    ####