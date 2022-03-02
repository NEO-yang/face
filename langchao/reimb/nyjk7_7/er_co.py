# -*- coding: utf-8 -*-
'''
==================================================
@创建人: 杨兴财
@当前维护人: 杨兴财
@Desc: 费用报销单
==================================================
'''
import re

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


MIN_AMOUNT = 0


class ErExpenseLine1Collection(models.Model):
    _inherit = 'er.expense.line1.collection'

    ################################  default start  ################################

    ################################  default end    ################################


    ################################  字段定义区 start  ################################

    # 可下推付款金额
    unpush_amount = fields.Float(compute='_compute_unpush_amount')
    # 已核销金额
    recon_amount = fields.Float(compute='_compute_recon_and_unpay_amount')
    # 未核销金额
    unrecon_amount = fields.Float(compute='_compute_recon_and_unpay_amount')
    # 报销未付款金额
    unpay_amount = fields.Float(compute='_compute_recon_and_unpay_amount')

    ################################  字段定义区 end    ################################


    ################################  计算方法区 start  ################################

    @api.depends('collected_amount', 'push_amount', 'offset_loan_amount')
    def _compute_unpush_amount(self):
        """
        可下推付款金额=收款金额-已下推付款金额-冲借款金额
        """
        for rec in self:
            currency_id = rec.parent_id.currency_id
            rec.unpush_amount = self._round(rec.collected_amount - rec.push_amount - rec.offset_loan_amount, currency_id)
    
    @api.depends('collected_amount', 'pay_amount', 'offset_loan_amount')
    def _compute_recon_and_unpay_amount(self):
        """
        计算已核销金额/未核销金额/报销未付款金额：
        已核销金额=已付款金额+冲借款金额
        未核销金额=收款金额-已核销金额
        报销未付款金额=收款金额-已付款金额-冲借款金额
        """
        for rec in self:
            currency_id = rec.parent_id.currency_id.id
            rec.recon_amount = self._round(rec.pay_amount + rec.offset_loan_amount, currency_id)
            rec.unrecon_amount = self._round(rec.collected_amount - rec.recon_amount, currency_id)
            rec.unpay_amount = self._round(rec.collected_amount - rec.pay_amount - rec.offset_loan_amount, currency_id)

    ################################  计算方法区 end    ################################


    ################################  onchange方法区  start  ################################
    
    def _default_collected_dept(self):
        """
        获取默认的收款单位,以及收款金额逻辑如下
            1.收款单位：如果费用承担组织和付款组织一致，则收款单位默认为往来单位
            2.收款金额：默认为核定报销金额 - 已录入的收款信息
        """
        parent = self.parent_id
        if parent.exp_org_id == parent.pay_org_id:
            self.collected_dept = parent.contact_dept
        else:
            self.collected_dept = None
        self._onchange_collected_dept()

        # 获取收款金额默认值
        aprv_amount_total = parent.aprv_amount_total
        currency_id = parent.currency_id.id
        collected_amount_total = 0
        for line in parent.line1_collection_ids:
            collected_amount_total = self._round(collected_amount_total + line.collected_amount, currency_id)
        # 如果核定报销金额合计 > 当前已录入收款金额合计，则当前行收款信息为 核定报销金额合计 - 当前已录入收款金额合计
        if self._float_compare(aprv_amount_total, collected_amount_total, currency_id) == 1:
            self.collected_amount = aprv_amount_total - collected_amount_total

    def _onchange_collected_dept(self):
        """
        收款单位变更时，更新财务信息
        """
        is_bank = self.parent_id.settle_type_id.buss_type == 'bank'
        self._update_fin_data(is_bank)
    
    def _onchange_bank_acct(self):
        """
        校验银行账号全部为数字
        """
        if self.bank_acct:
            bank_acct = self.bank_acct.replace(' ', '')
            if not re.match(r'^\d+$', bank_acct):
                # 银行账号仅能为数字，请修改
                raise ValidationError(_('Bank account number can only be numbers, please modify'))
            else:
                self.bank_acct = bank_acct
    
    def _onchange_collected_amount(self):
        """
        校验收款金额不能小于0
        """
        if self._float_compare(self.collected_amount, MIN_AMOUNT, self.parent_id.currency_id.id) == -1:
            # 收款金额不能小于0
            raise ValidationError(_('The amount of collected shall not be less than 0'))

    ################################  onchange方法区  end    ################################


    ################################  约束方法区  start  ################################
    
    ################################  约束方法区  end    ################################


    ################################  服务器动作区  start  ################################
    
    ################################  服务器动作区  end    ################################


    ################################  按钮动作区  start  ################################

    ################################  按钮动作区  end    ################################


    ################################  私有方法区  start  ################################

    def _update_fin_data(self, is_bank):
        """
        根据收款单位及结算方式是否为银行，更新财务信息
        """
        self.bank_id = None
        self.acct_name = None
        self.bank_acct = None

        collected_dept = self.collected_dept
        if collected_dept and is_bank:
            if collected_dept._name == 'mdm.customer':
                default_line = collected_dept.cust_line1_bank_ids.filtered(lambda line: line.is_default)
                self.bank_id = default_line.bank_branch_id.id
                self.acct_name = default_line.acct_name
                self.bank_acct = default_line.number
            elif collected_dept._name == 'mdm.supplier':
                default_line = collected_dept.supl_line1_bank_ids.filtered(lambda line: line.is_default)
                self.bank_id = default_line.bank_branch_id.id
                self.acct_name = default_line.acct_name
                self.bank_acct = default_line.number
            elif collected_dept._name == 'mdm.employee':
                default_line = collected_dept.line_ids.filtered(lambda line: line.is_default)
                self.bank_id = default_line.bank_branch_id.id
                self.acct_name = default_line.acct_name
                self.bank_acct = default_line.bank_acct

    ################################  私有方法区  end    ################################


    ################################  公共方法区  start  ################################
    
    ################################  公共方法区  end    ################################


    ################################  覆盖基类方法区  start  ################################
    
    ################################  覆盖基类方法区  end    ################################


    ################################  其他方法区  start  ################################

    ################################  其他方法区  end    ################################
    