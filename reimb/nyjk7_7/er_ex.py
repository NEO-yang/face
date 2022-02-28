# -*- coding: utf-8 -*-
'''
==================================================
@创建人: 杨兴财
@当前维护人: 杨兴财
@Desc: Expense Record Doc
==================================================
'''
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


MIN_AMOUNT = 0
MAX_AMOUNT = 100

class ErExpenseLine1Expense(models.Model):
    _inherit = 'er.expense.line1.expense'

    ################################  default start  ################################
 
    ################################  default end    ################################


    ################################  字段定义区 start  ################################

    delete_state = fields.Selection(related='parent_id.delete_state', readonly=True)
    # 申请/核定报销金额
    req_amount = fields.Float(compute='_compute_req_amount_and_aprv_amount')
    req_amount_lc = fields.Float(compute='_compute_req_amount_and_aprv_amount')
    aprv_amount = fields.Float(compute='_compute_req_amount_and_aprv_amount')
    aprv_amount_lc = fields.Float(compute='_compute_aprv_amount_lc')
    # 税额
    tax_lc = fields.Float(compute='_compute_tax_lc')
    exp_amount_lc = fields.Float(compute='_compute_exp_amount_lc')
    # 已下推付款金额本位币
    push_amount_lc = fields.Float(compute='_compute_push_amount_lc')
    # 可下推付款金额
    unpush_amount = fields.Float(compute='_compute_unpush_amount')
    unpush_amount_lc = fields.Float(compute='_compute_unpush_amount')
    # 已付款金额本位币
    pay_amount_lc = fields.Float(compute='_compute_pay_amount_lc')
    # 冲借款金额本位币
    offset_loan_amount_lc = fields.Float(compute='_compute_offset_loan_amount_lc')
    # 已核销金额
    recon_amount = fields.Float(compute='_compute_recon_and_unpay_amount')
    recon_amount_lc = fields.Float(compute='_compute_recon_and_unpay_amount')
    # 未核销金额
    unrecon_amount = fields.Float(compute='_compute_recon_and_unpay_amount')
    unrecon_amount_lc = fields.Float(compute='_compute_recon_and_unpay_amount')
    # 报销未付款金额
    unpay_amount = fields.Float(compute='_compute_recon_and_unpay_amount')
    unpay_amount_lc = fields.Float(compute='_compute_recon_and_unpay_amount')
    # 核算状态
    accting_state = fields.Selection(compute='_compute_accting_state')

    ################################  字段定义区 end    ################################


    ################################  计算方法区 start  ################################

    @api.depends('exp_amount', 'tax')
    def _compute_req_amount_and_aprv_amount(self):
        """
        计算申请/核定报销金额 = 不含税金额 + 税额
        """
        for rec in self:
            exp_amount = rec.exp_amount
            tax = rec.tax
            currency_id = rec.parent_id.currency_id.id
            req_amount = self._round(exp_amount + tax, currency_id)
            rec.req_amount = req_amount
            if not self._context.get('workflow_name', ''):
                rec.aprv_amount = req_amount
            else:
                rec.aprv_amount = rec.aprv_amount

            curr_rate = rec.parent_id.curr_rate
            local_currency_id = rec.parent_id.local_currency_id.id
            req_amount_lc = self._round(req_amount * curr_rate, local_currency_id)
            rec.req_amount_lc = req_amount_lc

    @api.depends('aprv_amount')
    def _compute_aprv_amount_lc(self):
        """
        计算申请/核定报销金额 = 不含税金额 + 税额
        """
        for rec in self:
            curr_rate = rec.parent_id.curr_rate
            local_currency_id = rec.parent_id.local_currency_id.id
            rec.aprv_amount_lc = self._round(rec.aprv_amount * curr_rate, local_currency_id)

    def _compute_tax(self):
        """
        计算税额
        """
        currency_id = self.parent_id.currency_id.id
        self.tax = self._round(self.exp_amount * self.tax_rate * 0.01, currency_id)
        
            
    @api.depends('tax')
    def _compute_tax_lc(self):
        """
        税额本位币
        """
        for rec in self:
            local_currency_id = rec.parent_id.local_currency_id.id
            rec.tax_lc = self._round(rec.tax * rec.parent_id.curr_rate, local_currency_id)

    @api.depends('exp_amount')
    def _compute_exp_amount_lc(self):
        """
        不含税金额本位币
        """
        for rec in self:
            local_currency_id = rec.parent_id.local_currency_id.id
            rec.exp_amount_lc = self._round(rec.exp_amount * rec.parent_id.curr_rate, local_currency_id)

    @api.depends('push_amount', 'aprv_amount', 'offset_loan_amount')
    def _compute_unpush_amount(self):
        """
        可下推付款金额=核定报销金额-已下推付款金额-冲借款金额
        """
        for rec in self:
            currency_id = rec.parent_id.currency_id.id
            rec.unpush_amount = self._round(rec.aprv_amount - rec.offset_loan_amount - rec.push_amount, currency_id)
            local_currency_id = rec.parent_id.local_currency_id.id
            rec.unpush_amount_lc = self._round(rec.aprv_amount_lc - rec.push_amount_lc - rec.offset_loan_amount_lc, local_currency_id)

    @api.depends('push_amount')
    def _compute_push_amount_lc(self):
        """
        计算已下推付款金额本位币
        """
        for rec in self:
            curr_rate = rec.parent_id.curr_rate
            local_currency_id = rec.parent_id.local_currency_id.id
            rec.push_amount_lc = self._round(rec.push_amount * curr_rate, local_currency_id)
    
    @api.depends('pay_amount')
    def _compute_pay_amount_lc(self):
        """
        计算已付款金额本位币
        """
        for rec in self:
            curr_rate = rec.parent_id.curr_rate
            local_currency_id = rec.parent_id.local_currency_id.id
            rec.pay_amount_lc = self._round(rec.pay_amount * curr_rate, local_currency_id)

    @api.depends('offset_loan_amount')
    def _compute_offset_loan_amount_lc(self):
        """
        计算冲借款金额本位币
        """
        for rec in self:
            curr_rate = rec.parent_id.curr_rate
            local_currency_id = rec.parent_id.local_currency_id.id
            rec.offset_loan_amount_lc = self._round(rec.offset_loan_amount * curr_rate, local_currency_id)

    @api.depends('aprv_amount', 'pay_amount', 'offset_loan_amount')
    def _compute_recon_and_unpay_amount(self):
        """
        计算费用明细行中的已核销金额、未核销金额、报销未付款金额
        已核销金额=已付款金额+冲借款金额
        未核销金额=核定报销金额-已核销金额
        报销未付款金额=核定报销金额-已付款金额-冲借款金额
        """
        for rec in self:
            currency_id = rec.parent_id.currency_id.id
            local_currency_id = rec.parent_id.local_currency_id.id
            # 已核销金额
            rec.recon_amount = self._round(rec.pay_amount + rec.offset_loan_amount, currency_id)
            rec.recon_amount_lc = self._round(rec.pay_amount_lc + rec.offset_loan_amount_lc, local_currency_id)
            # 未核销金额
            rec.unrecon_amount = self._round(rec.aprv_amount - rec.recon_amount, currency_id)
            rec.unrecon_amount_lc = self._round(rec.aprv_amount_lc - rec.recon_amount_lc, local_currency_id)
            # 报销未付款金额
            rec.unpay_amount = self._round(rec.aprv_amount - rec.pay_amount - rec.offset_loan_amount, currency_id)
            rec.unpay_amount_lc = self._round(rec.aprv_amount_lc - rec.pay_amount_lc - rec.offset_loan_amount_lc, local_currency_id)
    
    @api.depends('exp_date')
    def _compute_accting_state(self):
        """
        计算项目核算状态
        """
        for rec in self:
            project_id = rec.parent_id.project_id
            rec.accting_state = rec._get_accting_state(project_id, rec.exp_date)
   
    ################################  计算方法区 end    ################################


    ################################  onchange方法区  start  ################################

    def _onchange_inv_id(self):
        """
        选择发票时，带出报销金额，申请报销金额，税额
        """
        amount_no_tax = self.inv_id.amount_total
        # 申请报销金额 = 价税合计
        self.req_amount = self.inv_id.amount_tax_total
        # 核定报销金额
        self.aprv_amount = self.inv_id.amount_tax_total
        # 不含税金额
        self.exp_amount = amount_no_tax
        # 税额
        self.tax = self.inv_id.tax_total
        # 税率
        self.tax_rate = 0

    def _onchange_inv_type_id(self):
        """
        切换发票类型时，更新税率
        """
        # 更新税率
        self.tax_rate = self.inv_type_id.defaul_tax_rate
        self._compute_tax()

    def _onchange_exp_amount(self):
        """
        校验不含税金额不能小于0
        """
        if self._float_compare(self.exp_amount, MIN_AMOUNT, self.parent_id.currency_id.id) == -1:
            # 不含税金额不能小于0
            raise ValidationError(_('The amount of expense shall not be less than 0'))
        self._compute_tax()

    def _onchange_tax_rate(self):
        """
        校验税率必须介于0~100
        """
        if self._float_compare(self.tax_rate, MIN_AMOUNT, self.parent_id.currency_id.id) == -1\
            or self._float_compare(self.tax_rate, MAX_AMOUNT, self.parent_id.currency_id.id) == 1:
            # 税率必须介于0~100
            raise ValidationError(_('The tax rate must be between 0~100'))
        self._compute_tax()

    def _onchange_tax(self):
        """
        校验税额不能小于0
        """
        if self._float_compare(self.tax, MIN_AMOUNT, self.parent_id.currency_id.id) == -1:
            # 税额不能小于0
            raise ValidationError(_('The amount of tax shall not be less than 0'))
    
    def _default_exp_date(self):
        """
        获取费用日期默认值
        """
        apply_date = self.parent_id.apply_date
        project_id = self.parent_id.project_id
        self.exp_date = None
        # 判断申请日期是否超出项目日期范围
        if self._is_valid_exp_date(project_id, apply_date):
            self.exp_date = apply_date
        else:
            # 申请日期超出项目日期范围，考虑带出当前日期
            today = fields.Date.today()
            if self._is_valid_exp_date(project_id, today):
                self.exp_date = today

    def _onchange_exp_date(self):
        """
        费用日期变更时，校验费用日期是否超出项目日期范围，更新核算状态
        """
        project_id = self.parent_id.project_id
        if not self._is_valid_exp_date(project_id, self.exp_date):
            # 费用日期已超出所选项目的时间范围，请检查
            raise ValidationError(_('The expense date is out of the selected project time range, please check'))
        self.accting_state = self._get_accting_state(project_id, self.exp_date)

    ################################  onchange方法区  end    ################################


    ################################  约束方法区  start  ################################

    ################################  约束方法区  end    ################################


    ################################  服务器动作区  start  ################################
    
    ################################  服务器动作区  end    ################################


    ################################  按钮动作区  start  ################################

    ################################  按钮动作区  end    ################################


    ################################  私有方法区  start  ################################

    def _get_inv_domain(self, model=None, field_name=None, depend_fields=None):
        """
        获取发票的过滤
        """
        exp_org_data = depend_fields.get('exp_org_id', None)
        currency_data = depend_fields.get('currency_id', None)
        inv_type_data = depend_fields.get('inv_type_id', None)
        apply_emp_data = depend_fields.get('apply_emp_id', None)
        if isinstance(exp_org_data, dict) and isinstance(currency_data, dict) and isinstance(inv_type_data, dict) and isinstance(apply_emp_data, dict):
            domain = [
                ('sett_org_id', '=', exp_org_data.get('id', None)),
                ('currency_id', '=', currency_data.get('id', None)),
                ('inv_type_id', '=', inv_type_data.get('id', None)), 
                ('claim_uid', '=', apply_emp_data.get('id', None)), 
                ('invoice_balance', '>', 0), 
                ('is_error', '=', False),
                ('state', '=', 'audit'), 
                ('delete_state', '=', 'normal'), 
            ]
        else:
            domain = [('id', 'in', [])]
        return domain

    def _update_tax(self):
        """
        修改核定报销金额时更新税额
        """
        rate = self.tax_rate / 100
        #税额 = 核定报销金额 / (1 + 税率/100) * 税率/100
        self.tax = self.aprv_amount / (1 + rate) * rate
        # 不含税金额 = 核定报销金额-税额
        self.exp_amount = self.aprv_amount - self.tax

    def _get_real_project_id(self, project_id):
        """
        根据表头所选项目，获取真正的项目
        """
        if project_id:
            # 根据所选项目，查找真正的项目
            source_model = project_id.source_model_id.model
            source_doc_id = project_id.source_doc_id
            # 农银金科项目（防止所选项目映射到其他项目表中，而没有以下逻辑所用字段）
            if source_model == 'mdm.project.file.nyjk' and source_doc_id:
                project_obj = self.env[source_model]
                return project_obj.browse(source_doc_id)
        return None
    
    def _is_include_date(self, start_date, end_date, exp_date):
        """
        判断费用日期期间内是否包含某个日期：
        1. 开始日期不为空且结束日期不为空时，费用日期在区间内，为True
        2. 开始日期不为空且结束日期为空时，费用日期大于等于开始日期，为True
        3.其他情况为False
        """
        if start_date:
            if end_date:
                if start_date <= exp_date <= end_date:
                    return True
            else:
                if start_date <= exp_date:
                    return True
        return False
        
    def _get_accting_state(self, project_id, exp_date):
        """
        根据项目和费用日期获取核算状态
        """
        accting_state = None
        real_project_id = self._get_real_project_id(project_id)

        if real_project_id and exp_date:
            for project_line in real_project_id.line_ids:
                start_date = project_line.start_date
                end_date = project_line.end_date
                # 如果费用日期在此项目明细中，则核算状态为项目明细核算状态，并跳出循环
                if self._is_include_date(start_date, end_date, exp_date):
                    accting_state = project_line.accting_state
                    break
        return accting_state
        
    def _is_valid_exp_date(self, project_id, exp_date):
        """
        校验费用日期是否超出项目时间范围
        """
        real_project_id = self._get_real_project_id(project_id)
        if real_project_id and exp_date:
            establish_date = real_project_id.establish_date
            # 结项日期为空时使用当前日期
            closing_date = real_project_id.closing_date or fields.Date.today()
            if establish_date and not establish_date <= exp_date <= closing_date:
                return False
        return True

    def _get_inv_type_domain(self, model, field_name, depend_fields):
        """
        获取发票类型的domain过滤
        """
        exp_item_data = depend_fields.get('exp_item_id', None)
        domain = [('id', 'in', [])]
        if exp_item_data and exp_item_data.get('id', None):
            exp_item_obj = self.env['mdm.expense.item']
            exp_item = exp_item_obj.browse(exp_item_data['id'])
            inv_type_ids = exp_item.invoice_types.ids
            if inv_type_ids:
                # 如果费用项目对应的可选发票类型不为空，则过滤范围为可选发票类型
                domain = [('id', 'in', inv_type_ids)]
            else:
                # 如果费用项目对应的可选发票类型为空，代表可选范围为全部
                domain = []
        
        return domain

    ################################  私有方法区  end    ################################


    ################################  公共方法区  start  ################################
    
    ################################  公共方法区  end    ################################


    ################################  覆盖基类方法区  start  ################################
    
    ################################  覆盖基类方法区  end    ################################


    ################################  其他方法区  start  ################################

    ################################  其他方法区  end    ################################
    