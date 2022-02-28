#  0909报销报表开始时间与结束时间BUG

    @api.onchange('exp_org_id')
    def _onchange_exp_org_id(self):
        """
        切换费用承担组织，清空部门和单位
        """
        self.exp_dept_ids = None
        self.customer_ids = None
        self.supplier_ids = None
        self.employee_ids = None
        self.department_ids = None
        self.project_ids = None
        ir_config_parameter_obj = self.env['ir.config_parameter']
        # 获取配置参数，若取不到默认为手工输入
        mto_code_rule_type = ir_config_parameter_obj.get_param(key=MTO_CODE_RULE, default='manual_input')
        # 当配置参数为 项目编号时，认为启用项目
        self.is_project_enable = True if mto_code_rule_type == 'project_number' else False

        # 开始日期与结束日期默认当前期间的开始于结束日期
        sys_line2_obj = self.env['mdm.accounting.system.line1.line2']
        sys_id = sys_line2_obj.search([('org_id', '=', self.exp_org_id.id)], limit=1)
        calendar_id = sys_id.parent_id.accting_policy_id.calendar_id
        today = fields.Date.today()
        # 获取当前期间
        account_calendar_obj = self.env['mdm.account.calendar']
        accting_period_id = account_calendar_obj.p_get_period(biz_date=today, calendar_id=calendar_id)
        self.start_date = accting_period_id.start_date
        self.end_date = accting_period_id.end_date