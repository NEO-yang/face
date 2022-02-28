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
from odoo.addons.ps_mdm.common import mdm_currency as curr
from odoo.tools import float_compare


TAX_RATE_DIGIT = 2

class AmbExpenseReimbLine1(models.Model):
    _inherit = 'amb.expense.reimb.line1'
    _order = 'sequence'

    ################################  default start  ################################
    
    ################################  default end    ################################


    ################################  字段定义区 start  ################################

    # tax_amount = fields.Float(compute="_compute_tax_amount")
    # reimb_amount = fields.Float(compute="_compute_reimb_amount")
    exp_amount_local = fields.Float(compute="_compute_exp_amount_local")
    tax_amount_local = fields.Float(compute="_compute_tax_amount_local")
    reimb_amount_local = fields.Float(compute="_compute_reimb_amount_local")

    ################################  字段定义区 end    ################################


    ################################  计算方法区 start  ################################
    # @api.depends('exp_amount', 'tax_rate')
    # def _compute_tax_amount(self):
    #     """
    #     税额=费用金额*税率*0.01
    #     """
    #     for rec in self:
    #         rec.tax_amount = rec.env['mdm.currency'].p_amount_float_round(rec.exp_amount * rec.tax_rate * 0.01, rec.parent_id.currency_id.id)

    # @api.depends('tax_amount', 'exp_amount')
    # def _compute_reimb_amount(self):
    #     """
    #     报销金额=费用金额+税额
    #     """
    #     for rec in self:
    #         rec.reimb_amount = rec.env['mdm.currency'].p_amount_float_round(rec.exp_amount + rec.tax_amount, rec.parent_id.currency_id.id)

    @api.depends('exp_amount', 'curr_rate')
    def _compute_exp_amount_local(self):
        for rec in self:
            # 费用金额本位币
            rec.exp_amount_local = rec.env['mdm.currency'].p_amount_float_round(rec.exp_amount * rec.curr_rate, rec.parent_id.local_currency_id.id)

    @api.depends('tax_amount', 'curr_rate')
    def _compute_tax_amount_local(self):
        for rec in self:
            # 税额本位币
            rec.tax_amount_local = rec.env['mdm.currency'].p_amount_float_round(rec.tax_amount * rec.curr_rate, rec.parent_id.local_currency_id.id)

    @api.depends('reimb_amount', 'curr_rate')
    def _compute_reimb_amount_local(self):
        for rec in self:
            # 报销金额本位币
            rec.reimb_amount_local = rec.env['mdm.currency'].p_amount_float_round(rec.reimb_amount * rec.curr_rate, rec.parent_id.local_currency_id.id) 

    ################################  计算方法区 end    ################################


    ################################  onchange方法区  start  ################################
    @api.onchange('exp_dept_id')
    def _onchange_exp_dept_id(self):
        """
        表头的费用承担部门有值，则新增明细行的时候携带表头的费用承担部门作为默认值
        """
        if not self.exp_dept_id and self.parent_id.exp_dept_id:
            self.exp_dept_id = self.parent_id.exp_dept_id

    @api.onchange('exp_amount')
    def _onchange_exp_amount(self):
        '''
        校验费用金额
        '''
        if self.env['mdm.currency'].p_amount_float_compare(self.exp_amount, 0, self.parent_id.currency_id.id) < 0:
            #费用金额不能小于0
            self.exp_amount = 0
            return {'warning': {
                'type': 'warning','message': _("Expense amount cannot be less than 0")  
            }}
        else:
            self.tax_amount = self.env['mdm.currency'].p_amount_float_round(self.exp_amount * self.tax_rate * 0.01, self.parent_id.currency_id.id)
            self.reimb_amount = self.env['mdm.currency'].p_amount_float_round(self.exp_amount + self.tax_amount, self.parent_id.currency_id.id)


            
    @api.onchange('tax_rate')
    def _onchange_tax_rate(self):
        '''
        校验税率
        '''
        if float_compare(self.tax_rate, 0, precision_digits=TAX_RATE_DIGIT) < 0:
            #税率不能小于0
            self.tax_rate = 0
            return {'warning': {
                'type': 'warning','message': _("Tax rate cannot be less than 0")  
            }}
        else:
            self.tax_amount = self.env['mdm.currency'].p_amount_float_round(self.exp_amount * self.tax_rate * 0.01, self.parent_id.currency_id.id)
            self.reimb_amount = self.env['mdm.currency'].p_amount_float_round(self.exp_amount + self.tax_amount, self.parent_id.currency_id.id)

            
    @api.onchange('tax_amount')
    def _onchange_tax_amount(self):
        '''
        校验税额
        '''
        if self.env['mdm.currency'].p_amount_float_compare(self.tax_amount, 0, self.parent_id.currency_id.id) < 0:
            #税额不能小于0
            self.tax_amount = 0
            return {'warning': {
                'type': 'warning','message': _("Tax amount cannot be less than 0")  
            }}
        else:
            self.reimb_amount = self.env['mdm.currency'].p_amount_float_round(self.exp_amount + self.tax_amount, self.parent_id.currency_id.id)

        
    @api.onchange('reimb_amount')
    def _onchange_reimb_amount(self):
        '''
        校验报销金额
        '''
        if self.env['mdm.currency'].p_amount_float_compare(self.reimb_amount, 0, self.parent_id.currency_id.id) < 0:
            #报销金额不能小于0
            self.reimb_amount = 0
            return {'warning': {
                'type': 'warning','message': _("Reimbursement amount cannot be less than 0")  }}
        else:
                #报销金额/（1+税率*0.01）=费用金额
            self.exp_amount = self.env['mdm.currency'].p_amount_float_round(self.reimb_amount / (1 + self.tax_rate * 0.01), self.parent_id.currency_id.id)
            self.tax_amount = self.env['mdm.currency'].p_amount_float_round(self.reimb_amount - self.exp_amount, self.parent_id.currency_id.id)
    ################################  onchange方法区  end    ################################


    ################################  约束方法区  start  ################################

    @api.constrains('exp_amount')
    def _check_exp_amount(self):
        for rec in self:
            if rec.env['mdm.currency'].p_amount_float_compare(rec.exp_amount, 0, rec.parent_id.currency_id.id) < 0:
                #费用金额不能小于0
                raise ValidationError(_('Expense amount cannot be less than 0'))

    @api.constrains('tax_rate')
    def _check_tax_rate(self):
        for rec in self:
            if float_compare(rec.tax_rate, 0, precision_digits=TAX_RATE_DIGIT) < 0:
                #税率不能小于0
                raise ValidationError(_('Tax rate cannot be less than 0'))

    @api.constrains('tax_amount')
    def _check_tax_amount(self):
        for rec in self:
            if rec.env['mdm.currency'].p_amount_float_compare(rec.tax_amount, 0, rec.parent_id.currency_id.id) < 0:
                #税额不能小于0
                raise ValidationError(_('Tax amount cannot be less than 0'))
            if rec.tax_amount and not rec.tax_rate:
                # 税额不为0时，税率不允许为0
                raise ValidationError(_('When the tax amount is not 0, the tax rate is not allowed to be 0'))
            # TODO:费用金额*税率不等于税额时（计算时注意金额精度），返回提示：行%s，费用金额乘以税率不等于税额，您想继续保存吗？
            # 这个校验先不做，等studio支持以后再适配
            # if rec.env['mdm.currency'].p_amount_float_compare(rec.tax_rate * rec.exp_amount, rec.tax_amount, rec.parent_id.currency_id.id) != 0:
            #     # 行%s，费用金额乘以税率不等于税额，您想继续保存吗？
            #     raise ValidationError(_('Line %s, the expense amount multiplied by the tax rate does not equal the tax amount, do you want to continue?'))

    @api.constrains('reimb_amount')
    def _check_reimb_amount(self):
        for rec in self:
            if rec.env['mdm.currency'].p_amount_float_compare(rec.reimb_amount, 0, rec.parent_id.currency_id.id) <= 0:
                #行%s，报销金额必须大于0
                raise ValidationError(_('Line %s, reimbursement amount must be greater than 0') %rec.sequence)
    ################################  约束方法区  end    ################################


    ################################  服务器动作区  start  ################################
    
    ################################  服务器动作区  end    ################################


    ################################  按钮动作区  start  ################################

    ################################  按钮动作区  end    ################################


    ################################  私有方法区  start  ################################
    
    ################################  私有方法区  end    ################################


    ################################  公共方法区  start  ################################
    
    ################################  公共方法区  end    ################################


    ################################  覆盖基类方法区  start  ################################
    
    ################################  覆盖基类方法区  end    ################################


    ################################  其他方法区  start  ################################

    ################################  其他方法区  end    ################################
    