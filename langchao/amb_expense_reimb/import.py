    def _check_inport(rec):
        if not rec.apply_date:
            # 申请日期不允许为空
            raise ValidationError(_('The request date cannot be empty'))
        if not rec.apply_org_id:
            # 申请组织不允许为空
            raise ValidationError(_('The applying org cannot be empty'))
        else:
            domain = rec.env['sys.admin.orgs'].p_get_main_org_domain(rec._name, option="pre_create")
            if apply_org_id not in rec.env['sys.admin.orgs'].search(domain):
                # 申请组织不存在，请重新输入
                raise ValidationError(_('Applying Org does not exist, please re-enter'))

        if not rec.apply_emp_id:
            # 申请人不允许为空
            raise ValidationError(_('The applicant cannot be empty'))
        else:
            if rec.apply_emp_id.use_org_id != rec.apply_emp_id:
                # 申请人不存在，请重新输入
                raise ValidationError(_('Applicant does not exist, please re-enter'))

        if not rec.apply_dept_id:
            # 申请部门不允许为空
            raise ValidationError(_('The applying dept cannot be empty'))
        else:
            if rec.apply_dept_id.use_org_id != rec.apply_emp_id:
                # 申请部门不存在，请重新输入
                raise ValidationError(_('Applying Dept does not exist, please re-enter'))
        if not rec.exp_org_id:
            # 费用承担组织不允许为空
            raise ValidationError(_('The expense bearing org cannot be empty'))
        else:
            if exp_org_id not in  rec._compute_exp_org_id_domain:
                # 费用承担组织不存在，请重新输入
                raise ValidationError(_('Expense Bearing Org does not exist, please re-enter'))
        if exp_dept_id:
            if rec.exp_dept_id.use_org_id != rec.exp_org_id:

                # 费用承担部门不存在，请重新输入 
                raise ValidationError(_('Expense Bearing Dept does not exist, please re-enter'))
        if not rec.pay_org_id:
            # 付款组织不允许为空
            raise ValidationError(_('The payment org cannot be empty'))
        else:
            if rec.pay_org_id == rec.exp_org_id:
                if not rec.exp_org_id.p_judge_org_fun_domain(rec.exp_org_id.id, 'recpay'):
                    # 付款组织不存在，请重新输入
                    raise ValidationError(_('Payment Org does not exist, please re-enter'))
            else:
                # 付款组织与费用承担组织值不同时，付款组织要与费用承担组织有结算委托收付的关系且该组织状态为已审核，
                # 付款组织不存在，请重新输入
                raise ValidationError(_('Payment Org does not exist, please re-enter'))
        if not rec.contact_dept:
            # 往来单位不允许为空
            raise ValidationError(_('The reciprocal unit cannot be empty'))
        else:
            if rec.contact_dept.use_org_id != rec.exp_org_id:
                raise ValidationError(_('Reciprocal Unit does not exist, please re-enter'))

        if not rec.currency_id:
            # 币别不允许为空
            raise ValidationError(_('The currency cannot be empty'))
        else:
            if rec.currency_id.state != audit:
                # 币别不存在，请重新输入
                raise ValidationError(_('Currency does not exist, please re-enter'))
        if not rec.curr_rate:
            # 汇率不允许为空
            raise ValidationError(_('The exchange rate cannot be empty'))
        else：
            if isinstance(rec.curr_rate,float) and len(str(x).split(".")[1]) != 6:
            # 汇率值无效，请重新输入
            raise ValidationError(_('Exchange rate is invalid, please re-enter'))

        if not rec.reason:
            # 报销事由不允许为空
            raise ValidationError(_('The reimbursement reason cannot be empty'))




##########################################################################################






        if not rec.exp_dept_id:
            # 费用承担部门不允许为空
            raise ValidationError(_('The expense bearing dept cannot be empty'))
        else：
            if rec.exp_dept_id.use_org_id != rec.parent_id.exp_org_id:

                # 费用承担部门不存在，请重新输入 
                raise ValidationError(_('Expense Bearing Dept does not exist, please re-enter'))

        if not rec.exp_item_id:
            # 费用项目不允许为空
            raise ValidationError(_('The expense item cannot be empty'))
        else：
            if rec.exp_item_id.state != "audit":

                # 费用项目不存在，请重新输入
                raise ValidationError(_('Expense Item does not exist, please re-enter))
        #费用金额精度与表头币别精度保持一致





        def _create_sequence(self, **kwargs):
        """
        sequence自动生成
        """
        records = kwargs.get('origin_args')
        for record in records:
            for index, line in enumerate(record['line1_ids']):
                line_rec = line[LINE_INDEX]
                line_rec['sequence'] = index + 1
                if not line_rec.get('tax_amount', None):
                    line_rec['tax_amount'] = self._round(line_rec['exp_amount'] * line_rec['tax_rate'] * 0.01, record['currency_id'])
                if not line_rec.get('reimb_amount', None):
                    line_rec['reimb_amount'] = self._round(line_rec['exp_amount'] + line_rec['tax_amount'], record['currency_id'])