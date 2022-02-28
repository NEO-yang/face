# -*- coding: utf-8 -*-
'''
==================================================
@创建人 ：郑兆涵
@当前维护人 : 郑兆涵
@Desc ：现金收支表
==================================================
'''

from odoo import api, models, fields, tools, _
from odoo.addons.ps_mdm.common import mdm_currency as curr
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import ValidationError
from odoo.addons.ps_admin.biz_log.models.biz_log_item import LogCategory, LogLevel
from odoo.addons.ps_cm.cm_base.models.cm_biz_item import CMBizLogItem 
from odoo.addons.ps_admin.sys_ele.sys_ele_ctrl import sys_ele_ctrl
from odoo.addons.ps_admin.precision import get_sys_precision

SOURCE_MODEL_LIST = [
    'cm.cash.recycling.line',  # 现金存取单（明细行）
    'cm.transfer.order',  # 转账购汇单（明细行）
    'cm.foreign.exchange',  # 转账购汇单（明细行）
    'cm.receivable.bill.line1.sale',  # 收款单（明细行）
    'cm.receivable.refund.bill.line1.sale',  # 收款退款单（明细行）
    'cm.payable.bill.line1',  # 付款单（明细行）
    'cm.payable.refund.bill.line1',  # 付款退款单（明细行）
    'cm.manual.journal.line1'  # 现金手工日记账（明细行）
]

class CmCashIncomeExpense(models.Model):
    _name = 'cm.cash.income.expense'
    _description = "Cm Cash Income Expense"  # 现金收支表

    ################################  默认值区 start  ################################

    @api.model
    def _select_objects(self):
        """
        Reference字段定义
        """
        model_ids = self.env["ir.model"].search([('model', 'in', ['mdm.customer', 'mdm.supplier', 'mdm.department', 'mdm.employee'])])
        return [(model.model, model.name) for model in model_ids]

    ################################  默认值区 end    ################################


    ################################  字段定义区 start  ################################

    tenant_id = fields.Integer(string="Tenant") # 租户
    number = fields.Char(string="Number")  # 编码
    source_create_uid = fields.Many2one('res.users', string="Source Create Uid")  # 创建人
    summary = fields.Text(string='Summary')  # 摘要
    state = fields.Selection([
        ('creating', 'Creating'), 
        ('temporary', 'Temporary'), 
        ('save', 'Save'), 
        ('submit', 'Submit'),
        ('audit', 'Audit')], string='State', default='creating') # 数据状态(制单/暂存/已保存/审核中/已审核)
    biz_date = fields.Date(default=fields.Date.context_today, string='Business Date')  # 业务日期
    source_sequence = fields.Integer(string='Source Sequence')  # 单据行号
    sett_number = fields.Char(string='Settlement Number') # 结算号
    currency_id = fields.Many2one('mdm.currency', string='Currency')  # 币别
    local_currency_id = fields.Many2one('mdm.currency', string='Local Currency')  # 本位币
    recpay_org_id = fields.Many2one('sys.admin.orgs', string='Receivable Payable Organization')  # 收付组织
    sett_org_id = fields.Many2one('sys.admin.orgs', string='Settle Organization')  # 结算组织
    contact_dept = fields.Reference(selection=lambda self: self._select_objects(), string='Contact Department')  # 往来单位
    cash_acct_number_id = fields.Many2one('mdm.cash.acct.number', string='Cash Account Number')  # 现金账号
    payment_purpose = fields.Many2one('mdm.payment.purpose', string='Payment Purpose') # 收付款用途
    sett_type_id = fields.Many2one('mdm.settle.type', string='Settle Method') # 结算方式
    is_check = fields.Boolean(string='Is Check', default=False) # 勾对
    source_model_id = fields.Many2one('ir.model', string="Source Model Id")  # 来源单据明细行模型id
    source_doc_id = fields.Integer(string="Source Doc Id")  # 来源单据明细行id
    source_parent_model_id = fields.Many2one('ir.model', string="Source Parent Model Id")  # 来源单据主表模型id
    source_parent_doc_id = fields.Integer(string="Source Parent Doc Id")  # 来源单据主表id

    # 收入金额
    income_amount = fields.Float(string='Income Amount', digits=get_sys_precision(), precision_field='currency_id', precision_type='amount_precision')  # 收入金额原币
    income_amount_local = fields.Float(string='Local Income Amount', digits=get_sys_precision(), precision_field='local_currency_id', precision_type='amount_precision')  # 收入金额本位币

    # 支出金额
    expense_amount = fields.Float(string='Expense Amount', digits=get_sys_precision(), precision_field='currency_id', precision_type='amount_precision')  # 支出金额原币
    expense_amount_local = fields.Float(string='Local Expense Amount', digits=get_sys_precision(), precision_field='local_currency_id', precision_type='amount_precision')  # 支出金额本位币

    ################################  字段定义区 end    ################################


    ################################  计算方法区 start  ################################
            
    ################################  计算方法区 end   ################################


    ################################  onchange方法区  start  ################################
    
    ################################  onchange方法区  end   ################################


    ################################  约束方法区  start  ################################
   
    ################################  约束方法区  end   ################################


    ################################  服务器动作区  start  ################################

    ################################  服务器动作区  end   ################################


    ################################  按钮动作区  start  ################################

    ################################  按钮动作区  end   ################################


    ################################  私有方法区  start  ################################

    def _get_model_id(self, model_name):
        """
        @desc: 获取所有来源单据模型id
        @params: self: 实列
        @params: model_name: 模型名
        @return: 返回一个数字id。
        """
        model_id = self.env['ir.model'].search([('model', '=', model_name)])
        if len(model_id) != 1:
            raise ValidationError(_('The model data of the current operation data document is incorrect, please check!'))  # 当前操作数据单据模型数据有误，请检查！
        return model_id.id

    def _create_data_type_cash_deposit(self, obj, source_model_id, source_parent_model_id, flag=False):
        """
        @desc: 创建现金存款单相关数据到后台表中
        @params: self: 实列
        @params: obj: 各个单据的明细行数据对象
        @params: source_model_id: 来源单据明细行模型id
        @params: source_parent_model_id: 来源单据主表模型id
        @return: 返回一个list，包含所有需要创建的记录的字典集合。
        """
        create_list = list()

        # 优化性能，将主表obj对象对应字段，提出到for循环外，提高性能
        obj_tenant_id = obj.tenant_id  # 租户
        obj_source_create_uid = obj.create_uid.id if obj.create_uid else None  # 创建人
        obj_number = obj.number  # 单据编号
        obj_recpay_org_id = obj.recv_org_id.id if obj.recv_org_id else None  # 收付组织
        obj_biz_date = obj.biz_date  # 业务日期
        obj_state = 'audit'  # 单据状态
        obj_local_currency_id = obj.local_currency_id.id if obj.local_currency_id else None  # 本位币
        obj_source_parent_doc_id = obj.id  # 来源单据主表id

        if flag:
            obj_source_create_uid = obj.create_uid  # 创建人
            obj_recpay_org_id = obj.recv_org_id  # 收付组织
            obj_local_currency_id = obj.local_currency_id  # 本位币
            obj_state = obj.state  # 单据状态

        for res in obj.line_ids:

            # 由于性能优化，将res的所有字段进行公共提取
            currency_id = res.currency_id  # 币别
            source_sequence = res.sequence  # 单据行号
            cash_acct_number_id = res.cash_acct_number  # 现金账号
            expense_amount = self._round(res.pay_amount, currency_id)  # 支出金额
            expense_amount_local = self._round(res.pay_amount_lc, obj_local_currency_id)  # 支出金额本位币
            sett_number = res.sett_number  # 结算号
            summary = res.abstract  # 摘要
            is_check = res.is_check  # 勾对
            source_doc_id = res.id  # 来源单据明细行id

            # 使用create的批量创建方法，获取汇集数据视图的所有字段
            if expense_amount != 0 or expense_amount_local != 0:
                # 如果收入金额/收入金额本位币/支出金额/支出金额本位币都为 0 ，则不进行数据创建
                new_dict = {
                    'tenant_id': obj_tenant_id,  # 租户
                    'source_create_uid': obj_source_create_uid,  # 创建人
                    'number': obj_number,  # 单据编号
                    'recpay_org_id': obj_recpay_org_id,  # 收付组织
                    'biz_date': obj_biz_date,  # 业务日期
                    'state': obj_state,  # 单据状态
                    'currency_id': currency_id.id if currency_id else None,  # 币别
                    'local_currency_id': obj_local_currency_id,  # 本位币
                    'sett_org_id': None,  # 结算组织
                    'contact_dept': None,  # 往来单位
                    'source_sequence': source_sequence,  # 单据行号
                    'cash_acct_number_id': cash_acct_number_id.id if cash_acct_number_id else None,  # 现金账号
                    'income_amount': 0,  # 收入金额
                    'expense_amount': expense_amount,  # 支出金额
                    'income_amount_local': 0,  # 收入金额本位币
                    'expense_amount_local': expense_amount_local,  # 支出金额本位币
                    'payment_purpose': None,  # 收付款用途
                    'sett_number': sett_number,  # 结算号
                    'sett_type_id': None,  # 结算方式
                    'summary': summary if summary else '',  # 摘要
                    'is_check': is_check,  # 勾对
                    'source_model_id': source_model_id,  # 来源单据明细行模型id
                    'source_doc_id': source_doc_id,  # 来源单据明细行id
                    'source_parent_model_id': source_parent_model_id,  # 来源单据主表模型id
                    'source_parent_doc_id': obj_source_parent_doc_id,  # 来源单据主表id
                }
                if flag:
                    # flag存在则说明不需要进行数据创建，这里直接获取many2one字段的对象即可
                    new_dict['currency_id'] = currency_id  # 币别
                    new_dict['cash_acct_number_id'] = cash_acct_number_id  # 现金账号
                    new_dict['source_parent_model'] = res.parent_id._name  # 来源单据主表模型

                create_list.append(new_dict)
        return create_list

    def _create_data_type_cash_withdrawals(self, obj, source_model_id, source_parent_model_id, flag=False):
        """
        @desc: 创建现金取款单相关数据到后台表中
        @params: self: 实列
        @params: obj: 各个单据的明细行数据对象
        @params: source_model_id: 来源单据明细行模型id
        @params: source_parent_model_id: 来源单据主表模型id
        @return: 返回一个list，包含所有需要创建的记录的字典集合。
        """
        create_list = list()

        # 优化性能，将主表obj对象对应字段，提出到for循环外，提高性能
        obj_tenant_id = obj.tenant_id  # 租户
        obj_source_create_uid = obj.create_uid.id if obj.create_uid else None  # 创建人
        obj_number = obj.number  # 单据编号
        obj_recpay_org_id = obj.recv_org_id.id if obj.recv_org_id else None  # 收付组织
        obj_biz_date = obj.biz_date  # 业务日期
        obj_state = 'audit'  # 单据状态
        obj_local_currency_id = obj.local_currency_id.id if obj.local_currency_id else None  # 本位币
        obj_source_parent_doc_id = obj.id  # 来源单据主表id

        if flag:
            # flag存在则说明不需要进行数据创建，这里直接获取many2one字段的对象即可
            obj_source_create_uid = obj.create_uid  # 创建人
            obj_recpay_org_id = obj.recv_org_id  # 收付组织
            obj_local_currency_id = obj.local_currency_id  # 收付组织
            obj_state = obj.state  # 单据状态

        for res in obj.line_ids:

            # 由于性能优化，将res的所有字段进行公共提取
            currency_id = res.currency_id  # 币别
            source_sequence = res.sequence  # 单据行号
            cash_acct_number_id = res.cash_acct_number  # 现金账号
            income_amount = self._round(res.amount, currency_id)  # 收入金额
            income_amount_local = self._round(res.amount_lc, obj_local_currency_id)  # 收入金额本位币
            sett_number = res.sett_number  # 结算号
            summary = res.abstract  # 摘要
            is_check = res.is_check  # 勾对
            source_doc_id = res.id  # 来源单据明细行id

            # 使用create的批量创建方法，获取汇集数据视图的所有字段
            if income_amount != 0 or income_amount_local != 0:
                # 如果收入金额/收入金额本位币/支出金额/支出金额本位币都为 0 ，则不进行数据创建
                new_dict = {
                    'tenant_id': obj_tenant_id,  # 租户
                    'source_create_uid': obj_source_create_uid,  # 创建人
                    'number': obj_number,  # 单据编号
                    'recpay_org_id': obj_recpay_org_id,  # 收付组织
                    'biz_date': obj_biz_date,  # 业务日期
                    'state': obj_state,  # 单据状态
                    'currency_id': currency_id.id if currency_id else None,  # 币别
                    'local_currency_id': obj_local_currency_id,  # 本位币
                    'sett_org_id': None,  # 结算组织
                    'contact_dept': None,  # 往来单位
                    'source_sequence': source_sequence,  # 单据行号
                    'cash_acct_number_id': cash_acct_number_id.id if cash_acct_number_id else None,  # 现金账号
                    'income_amount': income_amount,  # 收入金额
                    'expense_amount': 0,  # 支出金额
                    'income_amount_local': income_amount_local,  # 收入金额本位币
                    'expense_amount_local': 0,  # 支出金额本位币
                    'payment_purpose': None,  # 收付款用途
                    'sett_number': sett_number,  # 结算号
                    'sett_type_id': None,  # 结算方式
                    'summary': summary if summary else '',  # 摘要
                    'is_check': is_check,  # 勾对
                    'source_model_id': source_model_id,  # 来源单据明细行模型id
                    'source_doc_id': source_doc_id,  # 来源单据明细行id
                    'source_parent_model_id': source_parent_model_id,  # 来源单据主表模型id
                    'source_parent_doc_id': obj_source_parent_doc_id,  # 来源单据主表id
                }
                if flag:
                    # flag存在则说明不需要进行数据创建，这里直接获取many2one字段的对象即可
                    new_dict['currency_id'] = currency_id  # 币别
                    new_dict['cash_acct_number_id'] = cash_acct_number_id  # 现金账号
                    new_dict['source_parent_model'] = res.parent_id._name  # 来源单据主表模型

                create_list.append(new_dict)
        return create_list

    def _create_data_type_cash_transfer(self, obj, source_model_id, source_parent_model_id, flag=False):
        """
        @desc: 创建现金转账单相关数据到后台表中
        @params: self: 实列
        @params: obj: 各个单据的明细行数据对象
        @params: source_model_id: 来源单据明细行模型id
        @params: source_parent_model_id: 来源单据主表模型id
        @return: 返回一个list，包含所有需要创建的记录的字典集合。
        """
        create_list = list()

        # 优化性能，将主表obj对象对应字段，提出到for循环外，提高性能
        obj_tenant_id = obj.tenant_id  # 租户
        obj_source_create_uid = obj.create_uid.id if obj.create_uid else None  # 创建人
        obj_number = obj.number  # 单据编号
        obj_recpay_org_id = obj.col_org_id.id if obj.col_org_id else None  # 收付组织
        obj_biz_date = obj.biz_date  # 业务日期
        obj_state = 'audit'  # 单据状态
        obj_local_currency_id = obj.local_curr_id.id if obj.local_curr_id else None  # 本位币
        obj_source_parent_doc_id = obj.id  # 来源单据主表id

        if flag:
            # flag存在则说明不需要进行数据创建，这里直接获取many2one字段的对象即可
            obj_source_create_uid = obj.create_uid  # 创建人
            obj_recpay_org_id = obj.col_org_id  # 收付组织
            obj_local_currency_id = obj.local_curr_id  # 本位币
            obj_state = obj.state  # 单据状态

        for res in obj.transfer_order_ids:

            # 由于性能优化，将res的所有字段进行公共提取
            currency_id = res.currency_id  # 币别
            source_sequence = res.sequence  # 单据行号
            cash_in_acct_number_id = res.cash_in_account_id  # 现金账号（转入）
            cash_out_acct_number_id = res.cash_out_account_id  # 现金账号（转出）
            income_amount = self._round(res.in_amount, currency_id)  # 收入金额
            income_amount_local = self._round(res.in_amount_lc, obj_local_currency_id)  # 收入金额本位币
            charge = res.charge  # 手续费
            charge_local = res.charge_lc  # 手续费本位币
            sett_in_number = res.in_no  # 结算号（转入）
            sett_out_number = res.out_no  # 结算号（转入）
            summary = res.abstract  # 摘要
            is_in_check = res.is_in_check  # 勾对（转入）
            is_out_check = res.is_out_check  # 勾对（转出）
            source_doc_id = res.id  # 来源单据明细行id

            # 使用create的批量创建方法，获取汇集数据视图的所有字段
            if income_amount != 0 or income_amount_local != 0:
                # 如果收入金额/收入金额本位币/支出金额/支出金额本位币都为 0 ，则不进行数据创建
                new_dict = {
                    'tenant_id': obj_tenant_id,  # 租户
                    'source_create_uid': obj_source_create_uid,  # 创建人
                    'number': obj_number,  # 单据编号
                    'recpay_org_id': obj_recpay_org_id,  # 收付组织
                    'biz_date': obj_biz_date,  # 业务日期
                    'state': obj_state,  # 单据状态
                    'currency_id': currency_id.id if currency_id else None,  # 币别
                    'local_currency_id': obj_local_currency_id,  # 本位币
                    'sett_org_id': None,  # 结算组织
                    'contact_dept': None,  # 往来单位
                    'source_sequence': source_sequence,  # 单据行号
                    'cash_acct_number_id': cash_in_acct_number_id.id if cash_in_acct_number_id else None,  # 现金账号
                    'income_amount': income_amount,  # 收入金额
                    'expense_amount': 0,  # 支出金额
                    'income_amount_local': income_amount_local,  # 收入金额本位币
                    'expense_amount_local': 0,  # 支出金额本位币
                    'payment_purpose': None,  # 收付款用途
                    'sett_number': sett_in_number,  # 结算号
                    'sett_type_id': None,  # 结算方式
                    'summary': summary if summary else '',  # 摘要
                    'is_check': is_in_check,  # 勾对
                    'source_model_id': source_model_id,  # 来源单据明细行模型id
                    'source_doc_id': source_doc_id,  # 来源单据明细行id
                    'source_parent_model_id': source_parent_model_id,  # 来源单据主表模型id
                    'source_parent_doc_id': obj_source_parent_doc_id,  # 来源单据主表id
                }
                if flag:
                    # flag存在则说明不需要进行数据创建，这里直接获取many2one字段的对象即可
                    new_dict['currency_id'] = currency_id  # 币别
                    new_dict['cash_acct_number_id'] = cash_in_acct_number_id  # 现金账号
                    new_dict['source_parent_model'] = res.parent_id._name  # 来源单据主表模型

                create_list.append(new_dict)

            if charge != 0 or charge_local != 0:
                # 如果收入金额/收入金额本位币/支出金额/支出金额本位币都为 0 ，则不进行数据创建
                new_dict = {
                    'tenant_id': obj_tenant_id,  # 租户
                    'source_create_uid': obj_source_create_uid,  # 创建人
                    'number': obj_number,  # 单据编号
                    'recpay_org_id': obj_recpay_org_id,  # 收付组织
                    'biz_date': obj_biz_date,  # 业务日期
                    'state': obj_state,  # 单据状态
                    'currency_id': currency_id.id if currency_id else None,  # 币别
                    'local_currency_id': obj_local_currency_id,  # 本位币
                    'sett_org_id': None,  # 结算组织
                    'contact_dept': None,  # 往来单位
                    'source_sequence': res.sequence,  # 单据行号
                    'cash_acct_number_id': cash_out_acct_number_id.id if cash_out_acct_number_id else None,  # 现金账号
                    'income_amount': 0,  # 收入金额
                    'expense_amount': self._round(charge, currency_id),  # 支出金额
                    'income_amount_local': 0,  # 收入金额本位币
                    'expense_amount_local': self._round(charge_local, obj_local_currency_id),  # 支出金额本位币
                    'payment_purpose': None,  # 收付款用途
                    'sett_number': sett_out_number,  # 结算号
                    'sett_type_id': None,  # 结算方式
                    'summary': summary if summary else '',  # 摘要
                    'is_check': is_out_check,  # 勾对
                    'source_model_id': source_model_id,  # 来源单据明细行模型id
                    'source_doc_id': source_doc_id,  # 来源单据明细行id
                    'source_parent_model_id': source_parent_model_id,  # 来源单据主表模型id
                    'source_parent_doc_id': obj_source_parent_doc_id,  # 来源单据主表id
                }
                if flag:
                    # flag存在则说明不需要进行数据创建，这里直接获取many2one字段的对象即可
                    new_dict['currency_id'] = res.currency_id  # 币别
                    new_dict['cash_acct_number_id'] = res.cash_out_account_id  # 现金账号
                    new_dict['payment_purpose'] = None  # 收付款用途
                    new_dict['sett_type_id'] = None  # 结算方式
                    new_dict['source_parent_model'] = res.parent_id._name  # 来源单据主表模型

                create_list.append(new_dict)

            if income_amount != 0 or income_amount_local != 0:
                # 如果收入金额/收入金额本位币/支出金额/支出金额本位币都为 0 ，则不进行数据创建
                new_dict = {
                    'tenant_id': obj_tenant_id,  # 租户
                    'source_create_uid': obj_source_create_uid,  # 创建人
                    'number': obj_number,  # 单据编号
                    'recpay_org_id': obj_recpay_org_id,  # 收付组织
                    'biz_date': obj_biz_date,  # 业务日期
                    'state': obj_state,  # 单据状态
                    'currency_id': currency_id.id if currency_id else None,  # 币别
                    'local_currency_id': obj_local_currency_id,  # 本位币
                    'sett_org_id': None,  # 结算组织
                    'contact_dept': None,  # 往来单位
                    'source_sequence': source_sequence,  # 单据行号
                    'cash_acct_number_id': cash_out_acct_number_id.id if cash_out_acct_number_id else None,  # 现金账号
                    'income_amount': 0,  # 收入金额
                    'expense_amount': income_amount,  # 支出金额
                    'income_amount_local': 0,  # 收入金额本位币
                    'expense_amount_local': income_amount_local,  # 支出金额本位币
                    'payment_purpose': None,  # 收付款用途
                    'sett_number': sett_out_number,  # 结算号
                    'sett_type_id': None,  # 结算方式
                    'summary': summary if summary else '',  # 摘要
                    'is_check': is_out_check,  # 勾对
                    'source_model_id': source_model_id,  # 来源单据明细行模型id
                    'source_doc_id': source_doc_id,  # 来源单据明细行id
                    'source_parent_model_id': source_parent_model_id,  # 来源单据主表模型id
                    'source_parent_doc_id': obj_source_parent_doc_id,  # 来源单据主表id
                }
                if flag:
                    # flag存在则说明不需要进行数据创建，这里直接获取many2one字段的对象即可
                    new_dict['currency_id'] = currency_id  # 币别
                    new_dict['cash_acct_number_id'] = cash_out_acct_number_id  # 现金账号
                    new_dict['source_parent_model'] = res.parent_id._name  # 来源单据主表模型

                create_list.append(new_dict)
        return create_list

    def _create_data_type_foreign_cash(self, obj, source_model_id, source_parent_model_id, flag=False):
        """
        @desc: 创建现金购汇单相关数据到后台表中
        @params: self: 实列
        @params: obj: 各个单据的明细行数据对象
        @params: source_model_id: 来源单据明细行模型id
        @params: source_parent_model_id: 来源单据主表模型id
        @return: 返回一个list，包含所有需要创建的记录的字典集合。
        """
        create_list = list()

        # 优化性能，将主表obj对象对应字段，提出到for循环外，提高性能
        obj_tenant_id = obj.tenant_id  # 租户
        obj_source_create_uid = obj.create_uid.id if obj.create_uid else None  # 创建人
        obj_number = obj.number  # 单据编号
        obj_recpay_org_id = obj.col_org_id.id if obj.col_org_id else None  # 收付组织
        obj_biz_date = obj.biz_date  # 业务日期
        obj_state = 'audit'  # 单据状态
        obj_local_currency_id = obj.local_curr_id.id if obj.local_curr_id else None  # 本位币
        obj_source_parent_doc_id = obj.id  # 来源单据主表id

        if flag:
            # flag存在则说明不需要进行数据创建，这里直接获取many2one字段的对象即可
            obj_source_create_uid = obj.create_uid  # 创建人
            obj_recpay_org_id = obj.col_org_id  # 收付组织
            obj_local_currency_id = obj.local_curr_id  # 本位币
            obj_state = obj.state  # 单据状态

        for res in obj.foreign_exchange_ids:

            # 由于性能优化，将res的所有字段进行公共提取
            in_currency_id = res.in_currency_id  # 币别（转入）
            out_currency_id = res.out_currency_id  # 币别（转出）
            source_sequence = res.sequence  # 单据行号
            cash_in_acct_number_id = res.cash_in_account_id  # 现金账号（转入）
            cash_out_acct_number_id = res.cash_out_account_id  # 现金账号（转出）
            income_amount = self._round(res.in_amount, in_currency_id)  # 收入金额
            income_amount_local = self._round(res.in_amount_lc, obj_local_currency_id)  # 收入金额本位币
            charge = res.charge  # 手续费
            charge_local = res.charge_lc  # 手续费本位币
            expense_amount = self._round(res.out_amount, out_currency_id)  # 支出金额
            expense_amount_local = self._round(res.out_amount_lc, obj_local_currency_id)  # 支出金额本位币
            sett_in_number = res.in_no  # 结算号（转入）
            sett_out_number = res.out_no  # 结算号（转入）
            summary = res.abstract  # 摘要
            is_in_check = res.is_in_check  # 勾对（转入）
            is_out_check = res.is_out_check  # 勾对（转出）
            source_doc_id = res.id  # 来源单据明细行id

            # 使用create的批量创建方法，获取汇集数据视图的所有字段
            if income_amount != 0 or income_amount_local != 0:
                # 如果收入金额/收入金额本位币/支出金额/支出金额本位币都为 0 ，则不进行数据创建
                new_dict = {
                    'tenant_id': obj_tenant_id,  # 租户
                    'source_create_uid': obj_source_create_uid,  # 创建人
                    'number': obj_number,  # 单据编号
                    'recpay_org_id': obj_recpay_org_id,  # 收付组织
                    'biz_date': obj_biz_date,  # 业务日期
                    'state': obj_state,  # 单据状态
                    'currency_id': in_currency_id.id if in_currency_id else None,  # 币别
                    'local_currency_id': obj_local_currency_id,  # 本位币
                    'sett_org_id': None,  # 结算组织
                    'contact_dept': None,  # 往来单位
                    'source_sequence': source_sequence,  # 单据行号
                    'cash_acct_number_id': cash_in_acct_number_id.id if cash_in_acct_number_id else None,  # 现金账号
                    'income_amount': income_amount,  # 收入金额
                    'expense_amount': 0,  # 支出金额
                    'income_amount_local': income_amount_local,  # 收入金额本位币
                    'expense_amount_local': 0,  # 支出金额本位币
                    'payment_purpose': None,  # 收付款用途
                    'sett_number': sett_in_number,  # 结算号
                    'sett_type_id': None,  # 结算方式
                    'summary': summary if summary else '',  # 摘要
                    'is_check': is_in_check,  # 勾对
                    'source_model_id': source_model_id,  # 来源单据明细行模型id
                    'source_doc_id': source_doc_id,  # 来源单据明细行id
                    'source_parent_model_id': source_parent_model_id,  # 来源单据主表模型id
                    'source_parent_doc_id': obj_source_parent_doc_id,  # 来源单据主表id
                }
                if flag:
                    # flag存在则说明不需要进行数据创建，这里直接获取many2one字段的对象即可
                    new_dict['currency_id'] = in_currency_id  # 币别
                    new_dict['cash_acct_number_id'] = cash_in_acct_number_id  # 现金账号
                    new_dict['source_parent_model'] = res.parent_id._name  # 来源单据主表模型

                create_list.append(new_dict)

            if charge != 0 or charge_local != 0:
                # 如果收入金额/收入金额本位币/支出金额/支出金额本位币都为 0 ，则不进行数据创建
                new_dict = {
                    'tenant_id': obj_tenant_id,  # 租户
                    'source_create_uid': obj_source_create_uid,  # 创建人
                    'number': obj_number,  # 单据编号
                    'recpay_org_id': obj_recpay_org_id,  # 收付组织
                    'biz_date': obj_biz_date,  # 业务日期
                    'state': obj_state,  # 单据状态
                    'currency_id': out_currency_id.id if out_currency_id else None,  # 币别
                    'local_currency_id': obj_local_currency_id,  # 本位币
                    'sett_org_id': None,  # 结算组织
                    'contact_dept': None,  # 往来单位
                    'source_sequence': source_sequence,  # 单据行号
                    'cash_acct_number_id': cash_out_acct_number_id.id if cash_out_acct_number_id else None,  # 现金账号
                    'income_amount': 0,  # 收入金额
                    'expense_amount': self._round(charge, out_currency_id),  # 支出金额
                    'income_amount_local': 0,  # 收入金额本位币
                    'expense_amount_local': self._round(charge_local, obj_local_currency_id),  # 支出金额本位币
                    'payment_purpose': None,  # 收付款用途
                    'sett_number': sett_out_number,  # 结算号
                    'sett_type_id': None,  # 结算方式
                    'summary': summary if summary else '',  # 摘要
                    'is_check': is_out_check,  # 勾对
                    'source_model_id': source_model_id,  # 来源单据明细行模型id
                    'source_doc_id': source_doc_id,  # 来源单据明细行id
                    'source_parent_model_id': source_parent_model_id,  # 来源单据主表模型id
                    'source_parent_doc_id': obj_source_parent_doc_id,  # 来源单据主表id
                }
                if flag:
                    # flag存在则说明不需要进行数据创建，这里直接获取many2one字段的对象即可
                    new_dict['currency_id'] = out_currency_id  # 币别
                    new_dict['cash_acct_number_id'] = cash_out_acct_number_id  # 现金账号
                    new_dict['payment_purpose'] = None  # 收付款用途
                    new_dict['sett_type_id'] = None  # 结算方式
                    new_dict['source_parent_model'] = res.parent_id._name  # 来源单据主表模型

                create_list.append(new_dict)

            if expense_amount != 0 or expense_amount_local != 0:
                # 如果收入金额/收入金额本位币/支出金额/支出金额本位币都为 0 ，则不进行数据创建
                new_dict = {
                    'tenant_id': obj_tenant_id,  # 租户
                    'source_create_uid': obj_source_create_uid,  # 创建人
                    'number': obj_number,  # 单据编号
                    'recpay_org_id': obj_recpay_org_id,  # 收付组织
                    'biz_date': obj_biz_date,  # 业务日期
                    'state': obj_state,  # 单据状态
                    'currency_id': out_currency_id.id if out_currency_id else None,  # 币别
                    'local_currency_id': obj_local_currency_id,  # 本位币
                    'sett_org_id': None,  # 结算组织
                    'contact_dept': None,  # 往来单位
                    'source_sequence': source_sequence,  # 单据行号
                    'cash_acct_number_id': cash_out_acct_number_id.id if cash_out_acct_number_id else None,  # 现金账号
                    'income_amount': 0,  # 收入金额
                    'expense_amount': expense_amount,  # 支出金额
                    'income_amount_local': 0,  # 收入金额本位币
                    'expense_amount_local': expense_amount_local,  # 支出金额本位币
                    'payment_purpose': None,  # 收付款用途
                    'sett_number': sett_out_number,  # 结算号
                    'sett_type_id': None,  # 结算方式
                    'summary': summary if summary else '',  # 摘要
                    'is_check': is_out_check,  # 勾对
                    'source_model_id': source_model_id,  # 来源单据明细行模型id
                    'source_doc_id': source_doc_id,  # 来源单据明细行id
                    'source_parent_model_id': source_parent_model_id,  # 来源单据主表模型id
                    'source_parent_doc_id': obj_source_parent_doc_id,  # 来源单据主表id
                }
                if flag:
                    # flag存在则说明不需要进行数据创建，这里直接获取many2one字段的对象即可
                    new_dict['currency_id'] = out_currency_id  # 币别
                    new_dict['cash_acct_number_id'] = cash_out_acct_number_id  # 现金账号
                    new_dict['source_parent_model'] = res.parent_id._name  # 来源单据主表模型

                create_list.append(new_dict)
        return create_list

    def _create_data_type_sale_receive(self, obj, source_model_id, source_parent_model_id, flag=False):
        """
        @desc: 创建销售业务收款单/其他业务收款单相关数据到后台表中
        @params: self: 实列
        @params: obj: 各个单据的明细行数据对象
        @params: source_model_id: 来源单据明细行模型id
        @params: source_parent_model_id: 来源单据主表模型id
        @return: 返回一个list，包含所有需要创建的记录的字典集合。
        """
        create_list = list()

        # 优化性能，将主表obj对象对应字段，提出到for循环外，提高性能
        obj_tenant_id = obj.tenant_id  # 租户
        obj_source_create_uid = obj.create_uid.id if obj.create_uid else None  # 创建人
        obj_number = obj.number  # 单据编号
        obj_recpay_org_id = obj.recv_org_id.id if obj.recv_org_id else None  # 收付组织
        obj_biz_date = obj.biz_date  # 业务日期
        obj_state = 'audit'  # 单据状态
        obj_currency_id = obj.currency_id.id if obj.currency_id else None  # 币别
        obj_local_currency_id = obj.local_curr_id.id if obj.local_curr_id else None  # 本位币
        obj_sett_org_id = obj.sett_org_id.id if obj.sett_org_id else None  # 结算组织
        obj_contact_dept = str(obj.contact_dept._name) + ',' + str(obj.contact_dept.id) if obj.contact_dept else None  # 往来单位
        obj_source_parent_doc_id = obj.id  # 来源单据主表id

        if flag:
            # flag存在则说明不需要进行数据创建，这里直接获取many2one字段的对象即可
            obj_source_create_uid = obj.create_uid  # 创建人
            obj_recpay_org_id = obj.recv_org_id  # 收付组织
            obj_currency_id = obj.currency_id  # 币别
            obj_local_currency_id = obj.local_curr_id  # 本位币
            obj_state = obj.state  # 单据状态

        for res in obj.line_sale_ids:
            if res.sett_type_id.buss_type == 'cash':
                # 取明细行数据，结算方式为现金业务的
                
                # 由于性能优化，将res的所有字段进行公共提取
                source_sequence = res.sequence  # 单据行号
                cash_acct_number_id = res.cash_acct_id  # 现金账号
                income_amount = abs(self._round(res.discount_amount, obj_currency_id))  # 收入金额
                income_amount_local = abs(self._round(res.discount_amount_local, obj_local_currency_id))  # 收入金额本位币
                expense_amount = abs(self._round(res.commission, obj_currency_id))  # 支出金额
                expense_amount_local = abs(self._round(res.commission_local, obj_local_currency_id))  # 支出金额本位币
                payment_purpose = res.biz_type_id  # 收付款用途
                sett_number = res.sett_number  # 结算号
                sett_type_id = res.sett_type_id  # 结算方式
                summary = res.note  # 摘要
                is_check = res.is_check  # 勾对
                source_doc_id = res.id  # 来源单据明细行id

                # 使用create的批量创建方法，获取汇集数据视图的所有字段
                if expense_amount != 0 or expense_amount_local != 0:
                    # 如果收入金额/收入金额本位币/支出金额/支出金额本位币都为 0 ，则不进行数据创建
                    new_dict = {
                        'tenant_id': obj_tenant_id,  # 租户
                        'source_create_uid': obj_source_create_uid,  # 创建人
                        'number': obj_number,  # 单据编号
                        'recpay_org_id': obj_recpay_org_id,  # 收付组织
                        'biz_date': obj_biz_date,  # 业务日期
                        'state': obj_state,  # 单据状态
                        'currency_id': obj_currency_id,  # 币别
                        'local_currency_id': obj_local_currency_id,  # 本位币
                        'sett_org_id': obj_sett_org_id,  # 结算组织
                        'contact_dept': obj_contact_dept,  # 往来单位
                        'source_sequence': source_sequence,  # 单据行号
                        'cash_acct_number_id': cash_acct_number_id.id if cash_acct_number_id else None,  # 现金账号
                        'income_amount': 0,  # 收入金额
                        'expense_amount': expense_amount,  # 支出金额
                        'income_amount_local': 0,  # 收入金额本位币
                        'expense_amount_local': expense_amount_local,  # 支出金额本位币
                        'payment_purpose': payment_purpose.id if payment_purpose else None,  # 收付款用途
                        'sett_number': sett_number,  # 结算号
                        'sett_type_id': sett_type_id.id if sett_type_id else None,  # 结算方式
                        'summary': summary if summary else '',  # 摘要
                        'is_check': is_check,  # 勾对
                        'source_model_id': source_model_id,  # 来源单据明细行模型id
                        'source_doc_id': source_doc_id,  # 来源单据明细行id
                        'source_parent_model_id': source_parent_model_id,  # 来源单据主表模型id
                        'source_parent_doc_id': obj_source_parent_doc_id,  # 来源单据主表id
                    }
                    if flag:
                        # flag存在则说明不需要进行数据创建，这里直接获取many2one字段的对象即可
                        new_dict['cash_acct_number_id'] = cash_acct_number_id  # 现金账号
                        new_dict['payment_purpose'] = payment_purpose  # 收付款用途
                        new_dict['sett_type_id'] = sett_type_id  # 结算方式
                        new_dict['source_parent_model'] = res.parent_id._name  # 来源单据主表模型

                    create_list.append(new_dict)

                if income_amount != 0 or income_amount_local != 0:
                    # 如果收入金额/收入金额本位币/支出金额/支出金额本位币都为 0 ，则不进行数据创建
                    new_dict = {
                        'tenant_id': obj_tenant_id,  # 租户
                        'source_create_uid': obj_source_create_uid,  # 创建人
                        'number': obj_number,  # 单据编号
                        'recpay_org_id': obj_recpay_org_id,  # 收付组织
                        'biz_date': obj_biz_date,  # 业务日期
                        'state': obj_state,  # 单据状态
                        'currency_id': obj_currency_id,  # 币别
                        'local_currency_id': obj_local_currency_id,  # 本位币
                        'sett_org_id': obj_sett_org_id,  # 结算组织
                        'contact_dept': obj_contact_dept,  # 往来单位
                        'source_sequence': source_sequence,  # 单据行号
                        'cash_acct_number_id': cash_acct_number_id.id if cash_acct_number_id else None,  # 现金账号
                        'income_amount': income_amount,  # 收入金额
                        'expense_amount': 0,  # 支出金额
                        'income_amount_local': income_amount_local,  # 收入金额本位币
                        'expense_amount_local': 0,  # 支出金额本位币
                        'payment_purpose': payment_purpose.id if payment_purpose else None,  # 收付款用途
                        'sett_number': sett_number,  # 结算号
                        'sett_type_id': sett_type_id.id if sett_type_id else None,  # 结算方式
                        'summary': summary if summary else '',  # 摘要
                        'is_check': is_check,  # 勾对
                        'source_model_id': source_model_id,  # 来源单据明细行模型id
                        'source_doc_id': source_doc_id,  # 来源单据明细行id
                        'source_parent_model_id': source_parent_model_id,  # 来源单据主表模型id
                        'source_parent_doc_id': obj_source_parent_doc_id,  # 来源单据主表id
                    }
                    if flag:
                        # flag存在则说明不需要进行数据创建，这里直接获取many2one字段的对象即可
                        new_dict['cash_acct_number_id'] = cash_acct_number_id  # 现金账号
                        new_dict['payment_purpose'] = payment_purpose  # 收付款用途
                        new_dict['sett_type_id'] = sett_type_id  # 结算方式
                        new_dict['source_parent_model'] = res.parent_id._name  # 来源单据主表模型

                    create_list.append(new_dict)
        return create_list

    def _create_data_type_sale_refund(self, obj, source_model_id, source_parent_model_id, flag=False):
        """
        @desc: 创建销售业务收款退款单/其他业务收款退款单相关数据到后台表中
        @params: self: 实列
        @params: obj: 各个单据的明细行数据对象
        @params: source_model_id: 来源单据明细行模型id
        @params: source_parent_model_id: 来源单据主表模型id
        @return: 返回一个list，包含所有需要创建的记录的字典集合。
        """
        create_list = list()

        # 优化性能，将主表obj对象对应字段，提出到for循环外，提高性能
        obj_tenant_id = obj.tenant_id  # 租户
        obj_source_create_uid = obj.create_uid.id if obj.create_uid else None  # 创建人
        obj_number = obj.number  # 单据编号
        obj_recpay_org_id = obj.recv_org_id.id if obj.recv_org_id else None  # 收付组织
        obj_biz_date = obj.biz_date  # 业务日期
        obj_state = 'audit'  # 单据状态
        obj_currency_id = obj.currency_id.id if obj.currency_id else None  # 币别
        obj_local_currency_id = obj.local_curr_id.id if obj.local_curr_id else None  # 本位币
        obj_sett_org_id = obj.sett_org_id.id if obj.sett_org_id else None  # 结算组织
        obj_contact_dept = str(obj.contact_dept._name) + ',' + str(obj.contact_dept.id) if obj.contact_dept else None  # 往来单位
        obj_source_parent_doc_id = obj.id  # 来源单据主表id

        if flag:
            # flag存在则说明不需要进行数据创建，这里直接获取many2one字段的对象即可
            obj_source_create_uid = obj.create_uid  # 创建人
            obj_recpay_org_id = obj.recv_org_id  # 收付组织
            obj_currency_id = obj.currency_id  # 币别
            obj_local_currency_id = obj.local_curr_id  # 本位币
            obj_state = obj.state  # 单据状态

        for res in obj.line_sale_ids:
            if res.sett_type_id.buss_type == 'cash':

                # 由于性能优化，将res的所有字段进行公共提取
                source_sequence = res.sequence  # 单据行号
                cash_acct_number_id = res.cash_acct_id  # 现金账号
                income_amount = abs(self._round(res.discount_amount, obj_currency_id))  # 收入金额
                income_amount_local = abs(self._round(res.discount_amount_local, obj_local_currency_id))  # 收入金额本位币
                expense_amount = abs(self._round(res.commission, obj_currency_id))  # 支出金额
                expense_amount_local = abs(self._round(res.commission_local, obj_local_currency_id))  # 支出金额本位币
                payment_purpose = res.biz_type_id  # 收付款用途
                sett_number = res.sett_number  # 结算号
                sett_type_id = res.sett_type_id  # 结算方式
                summary = res.note  # 摘要
                is_check = res.is_check  # 勾对
                source_doc_id = res.id  # 来源单据明细行id

                # 取明细行数据，结算方式为现金业务的
                # 使用create的批量创建方法，获取汇集数据视图的所有字段
                if expense_amount != 0 or expense_amount_local != 0:
                    # 如果收入金额/收入金额本位币/支出金额/支出金额本位币都为 0 ，则不进行数据创建
                    new_dict = {
                        'tenant_id': obj_tenant_id,  # 租户
                        'source_create_uid': obj_source_create_uid,  # 创建人
                        'number': obj_number,  # 单据编号
                        'recpay_org_id': obj_recpay_org_id,  # 收付组织
                        'biz_date': obj_biz_date,  # 业务日期
                        'state': obj_state,  # 单据状态
                        'currency_id': obj_currency_id,  # 币别
                        'local_currency_id': obj_local_currency_id,  # 本位币
                        'sett_org_id': obj_sett_org_id,  # 结算组织
                        'contact_dept': obj_contact_dept,  # 往来单位
                        'source_sequence': source_sequence,  # 单据行号
                        'cash_acct_number_id': cash_acct_number_id.id if cash_acct_number_id else None,  # 现金账号
                        'income_amount': 0,  # 收入金额
                        'expense_amount': expense_amount,  # 支出金额
                        'income_amount_local': 0,  # 收入金额本位币
                        'expense_amount_local': expense_amount_local,  # 支出金额本位币
                        'payment_purpose': payment_purpose.id if payment_purpose else None,  # 收付款用途
                        'sett_number': sett_number,  # 结算号
                        'sett_type_id': sett_type_id.id if sett_type_id else None,  # 结算方式
                        'summary': summary if summary else '',  # 摘要
                        'is_check': is_check,  # 勾对
                        'source_model_id': source_model_id,  # 来源单据明细行模型id
                        'source_doc_id': source_doc_id,  # 来源单据明细行id
                        'source_parent_model_id': source_parent_model_id,  # 来源单据主表模型id
                        'source_parent_doc_id': obj_source_parent_doc_id,  # 来源单据主表id
                    }
                    if flag:
                        # flag存在则说明不需要进行数据创建，这里直接获取many2one字段的对象即可
                        new_dict['cash_acct_number_id'] = cash_acct_number_id  # 现金账号
                        new_dict['payment_purpose'] = payment_purpose  # 收付款用途
                        new_dict['sett_type_id'] = sett_type_id  # 结算方式
                        new_dict['source_parent_model'] = res.parent_id._name  # 来源单据主表模型

                    create_list.append(new_dict)

                if income_amount != 0 or income_amount_local != 0:
                    # 如果收入金额/收入金额本位币/支出金额/支出金额本位币都为 0 ，则不进行数据创建
                    new_dict = {
                        'tenant_id': obj_tenant_id,  # 租户
                        'source_create_uid': obj_source_create_uid,  # 创建人
                        'number': obj_number,  # 单据编号
                        'recpay_org_id': obj_recpay_org_id,  # 收付组织
                        'biz_date': obj_biz_date,  # 业务日期
                        'state': obj_state,  # 单据状态
                        'currency_id': obj_currency_id,  # 币别
                        'local_currency_id': obj_local_currency_id,  # 本位币
                        'sett_org_id': obj_sett_org_id,  # 结算组织
                        'contact_dept': obj_contact_dept,  # 往来单位
                        'source_sequence': source_sequence,  # 单据行号
                        'cash_acct_number_id': cash_acct_number_id.id if cash_acct_number_id else None,  # 现金账号
                        'income_amount': 0,  # 收入金额
                        'expense_amount': income_amount,  # 支出金额
                        'income_amount_local': 0,  # 收入金额本位币
                        'expense_amount_local': income_amount_local,  # 支出金额本位币
                        'payment_purpose': payment_purpose.id if payment_purpose else None,  # 收付款用途
                        'sett_number': sett_number,  # 结算号
                        'sett_type_id': sett_type_id.id if sett_type_id else None,  # 结算方式
                        'summary': summary if summary else '',  # 摘要
                        'is_check': is_check,  # 勾对
                        'source_model_id': source_model_id,  # 来源单据明细行模型id
                        'source_doc_id': source_doc_id,  # 来源单据明细行id
                        'source_parent_model_id': source_parent_model_id,  # 来源单据主表模型id
                        'source_parent_doc_id': obj_source_parent_doc_id,  # 来源单据主表id
                    }
                    if flag:
                        # flag存在则说明不需要进行数据创建，这里直接获取many2one字段的对象即可
                        new_dict['cash_acct_number_id'] = cash_acct_number_id  # 现金账号
                        new_dict['payment_purpose'] = payment_purpose  # 收付款用途
                        new_dict['sett_type_id'] = sett_type_id  # 结算方式
                        new_dict['source_parent_model'] = res.parent_id._name  # 来源单据主表模型

                    create_list.append(new_dict)
        return create_list

    def _create_data_type_purchase_receive(self, obj, source_model_id, source_parent_model_id, flag=False):
        """
        @desc: 创建采购业务付款单/其他业务付款单相关数据到后台表中
        @params: self: 实列
        @params: obj: 各个单据的明细行数据对象
        @params: source_model_id: 来源单据明细行模型id
        @params: source_parent_model_id: 来源单据主表模型id
        @return: 返回一个list，包含所有需要创建的记录的字典集合。
        """
        create_list = list()

        # 优化性能，将主表obj对象对应字段，提出到for循环外，提高性能
        obj_tenant_id = obj.tenant_id  # 租户
        obj_source_create_uid = obj.create_uid.id if obj.create_uid else None  # 创建人
        obj_number = obj.number  # 单据编号
        obj_recpay_org_id = obj.pay_org_id.id if obj.pay_org_id else None  # 收付组织
        obj_biz_date = obj.biz_date  # 业务日期
        obj_state = 'audit'  # 单据状态
        obj_currency_id = obj.sett_curr_id.id if obj.sett_curr_id else None  # 币别
        obj_local_currency_id = obj.local_curr_id.id if obj.local_curr_id else None  # 本位币
        obj_sett_org_id = obj.sett_org_id.id if obj.sett_org_id else None  # 结算组织
        obj_contact_dept = str(obj.contact_dept._name) + ',' + str(obj.contact_dept.id) if obj.contact_dept else None  # 往来单位
        obj_source_parent_doc_id = obj.id  # 来源单据主表id

        if flag:
            # flag存在则说明不需要进行数据创建，这里直接获取many2one字段的对象即可
            obj_source_create_uid = obj.create_uid  # 创建人
            obj_recpay_org_id = obj.pay_org_id  # 收付组织
            obj_currency_id = obj.sett_curr_id  # 币别
            obj_local_currency_id = obj.local_curr_id  # 本位币
            obj_state = obj.state  # 单据状态

        for res in obj.line_ids:

            # 由于性能优化，将res的所有字段进行公共提取
            source_sequence = res.sequence  # 单据行号
            cash_acct_number_id = res.cash_acct_id  # 现金账号
            income_amount = abs(self._round(res.discount_amount, obj_currency_id))  # 收入金额
            income_amount_local = abs(self._round(res.discount_amount_local, obj_local_currency_id))  # 收入金额本位币
            expense_amount = abs(self._round(res.commission, obj_currency_id))  # 支出金额
            expense_amount_local = abs(self._round(res.commission_local, obj_local_currency_id))  # 支出金额本位币
            payment_purpose = res.pay_type_id  # 收付款用途
            sett_number = res.sett_num  # 结算号
            sett_type_id = res.sett_type_id  # 结算方式
            summary = res.note  # 摘要
            is_check = res.is_check  # 勾对
            source_doc_id = res.id  # 来源单据明细行id

            if res.sett_type_id.buss_type == 'cash':
                # 取明细行数据，结算方式为现金业务的
                # 使用create的批量创建方法，获取汇集数据视图的所有字段
                if expense_amount != 0 or expense_amount_local != 0:
                    # 如果收入金额/收入金额本位币/支出金额/支出金额本位币都为 0 ，则不进行数据创建
                    new_dict = {
                        'tenant_id': obj_tenant_id,  # 租户
                        'source_create_uid': obj_source_create_uid,  # 创建人
                        'number': obj_number,  # 单据编号
                        'recpay_org_id': obj_recpay_org_id,  # 收付组织
                        'biz_date': obj_biz_date,  # 业务日期
                        'state': obj_state,  # 单据状态
                        'currency_id': obj_currency_id,  # 币别
                        'local_currency_id': obj_local_currency_id,  # 本位币
                        'sett_org_id': obj_sett_org_id,  # 结算组织
                        'contact_dept': obj_contact_dept,  # 往来单位
                        'source_sequence': source_sequence,  # 单据行号
                        'cash_acct_number_id': cash_acct_number_id.id if cash_acct_number_id else None,  # 现金账号
                        'income_amount': 0,  # 收入金额
                        'expense_amount': expense_amount,  # 支出金额
                        'income_amount_local': 0,  # 收入金额本位币
                        'expense_amount_local': expense_amount_local,  # 支出金额本位币
                        'payment_purpose': payment_purpose.id if payment_purpose else None,  # 收付款用途
                        'sett_number': sett_number,  # 结算号
                        'sett_type_id': sett_type_id.id if sett_type_id else None,  # 结算方式
                        'summary': summary if summary else '',  # 摘要
                        'is_check': is_check,  # 勾对
                        'source_model_id': source_model_id,  # 来源单据明细行模型id
                        'source_doc_id': source_doc_id,  # 来源单据明细行id
                        'source_parent_model_id': source_parent_model_id,  # 来源单据主表模型id
                        'source_parent_doc_id': obj_source_parent_doc_id,  # 来源单据主表id
                    }
                    if flag:
                        # flag存在则说明不需要进行数据创建，这里直接获取many2one字段的对象即可
                        new_dict['cash_acct_number_id'] = cash_acct_number_id  # 现金账号
                        new_dict['payment_purpose'] = payment_purpose  # 收付款用途
                        new_dict['sett_type_id'] = sett_type_id  # 结算方式
                        new_dict['source_parent_model'] = res.parent_id._name  # 来源单据主表模型

                    create_list.append(new_dict)

                if income_amount != 0 or income_amount_local != 0:
                    # 如果收入金额/收入金额本位币/支出金额/支出金额本位币都为 0 ，则不进行数据创建
                    new_dict = {
                        'tenant_id': obj_tenant_id,  # 租户
                        'source_create_uid': obj_source_create_uid,  # 创建人
                        'number': obj_number,  # 单据编号
                        'recpay_org_id': obj_recpay_org_id,  # 收付组织
                        'biz_date': obj_biz_date,  # 业务日期
                        'state': obj_state,  # 单据状态
                        'currency_id': obj_currency_id,  # 币别
                        'local_currency_id': obj_local_currency_id,  # 本位币
                        'sett_org_id': obj_sett_org_id,  # 结算组织
                        'contact_dept': obj_contact_dept,  # 往来单位
                        'source_sequence': source_sequence,  # 单据行号
                        'cash_acct_number_id': cash_acct_number_id.id if cash_acct_number_id else None,  # 现金账号
                        'income_amount': 0,  # 收入金额
                        'expense_amount': income_amount,  # 支出金额
                        'income_amount_local': 0,  # 收入金额本位币
                        'expense_amount_local': income_amount_local,  # 支出金额本位币
                        'payment_purpose': payment_purpose.id if payment_purpose else None,  # 收付款用途
                        'sett_number': sett_number,  # 结算号
                        'sett_type_id': sett_type_id.id if sett_type_id else None,  # 结算方式
                        'summary': summary if summary else '',  # 摘要
                        'is_check': is_check,  # 勾对
                        'source_model_id': source_model_id,  # 来源单据明细行模型id
                        'source_doc_id': source_doc_id,  # 来源单据明细行id
                        'source_parent_model_id': source_parent_model_id,  # 来源单据主表模型id
                        'source_parent_doc_id': obj_source_parent_doc_id,  # 来源单据主表id
                    }
                    if flag:
                        # flag存在则说明不需要进行数据创建，这里直接获取many2one字段的对象即可
                        new_dict['cash_acct_number_id'] = cash_acct_number_id  # 现金账号
                        new_dict['payment_purpose'] = payment_purpose  # 收付款用途
                        new_dict['sett_type_id'] = sett_type_id  # 结算方式
                        new_dict['source_parent_model'] = res.parent_id._name  # 来源单据主表模型

                    create_list.append(new_dict)
        return create_list

    def _create_data_type_purchase_refund(self, obj, source_model_id, source_parent_model_id, flag=False):
        """
        @desc: 创建采购业务付款退款单/其他业务付款退款单相关数据到后台表中
        @params: self: 实列
        @params: obj: 各个单据的明细行数据对象
        @params: source_model_id: 来源单据明细行模型id
        @params: source_parent_model_id: 来源单据主表模型id
        @return: 返回一个list，包含所有需要创建的记录的字典集合。
        """
        create_list = list()

        # 优化性能，将主表obj对象对应字段，提出到for循环外，提高性能
        obj_tenant_id = obj.tenant_id  # 租户
        obj_source_create_uid = obj.create_uid.id if obj.create_uid else None  # 创建人
        obj_number = obj.number  # 单据编号
        obj_recpay_org_id = obj.pay_org_id.id if obj.pay_org_id else None  # 收付组织
        obj_biz_date = obj.biz_date  # 业务日期
        obj_state = 'audit'  # 单据状态
        obj_currency_id = obj.sett_curr_id.id if obj.sett_curr_id else None  # 币别
        obj_local_currency_id = obj.local_curr_id.id if obj.local_curr_id else None  # 本位币
        obj_sett_org_id = obj.sett_org_id.id if obj.sett_org_id else None  # 结算组织
        obj_contact_dept = str(obj.contact_dept._name) + ',' + str(obj.contact_dept.id) if obj.contact_dept else None  # 往来单位
        obj_source_parent_doc_id = obj.id  # 来源单据主表id

        if flag:
            # flag存在则说明不需要进行数据创建，这里直接获取many2one字段的对象即可
            obj_source_create_uid = obj.create_uid  # 创建人
            obj_recpay_org_id = obj.pay_org_id  # 收付组织
            obj_currency_id = obj.sett_curr_id  # 币别
            obj_local_currency_id = obj.local_curr_id  # 本位币
            obj_state = obj.state  # 单据状态

        for res in obj.line_ids:

            # 由于性能优化，将res的所有字段进行公共提取
            source_sequence = res.sequence  # 单据行号
            cash_acct_number_id = res.cash_acct_id  # 现金账号
            income_amount = abs(self._round(res.discount_amount, obj_currency_id))  # 收入金额
            income_amount_local = abs(self._round(res.discount_amount_local, obj_local_currency_id))  # 收入金额本位币
            expense_amount = abs(self._round(res.commission, obj_currency_id))  # 支出金额
            expense_amount_local = abs(self._round(res.commission_local, obj_local_currency_id))  # 支出金额本位币
            payment_purpose = res.pay_type_id  # 收付款用途
            sett_number = res.sett_num  # 结算号
            sett_type_id = res.sett_type_id  # 结算方式
            summary = res.note  # 摘要
            is_check = res.is_check  # 勾对
            source_doc_id = res.id  # 来源单据明细行id

            if res.sett_type_id.buss_type == 'cash':
                # 取明细行数据，结算方式为现金业务的
                # 使用create的批量创建方法，获取汇集数据视图的所有字段
                if expense_amount != 0 or expense_amount_local != 0:
                    # 如果收入金额/收入金额本位币/支出金额/支出金额本位币都为 0 ，则不进行数据创建
                    new_dict = {
                        'tenant_id': obj_tenant_id,  # 租户
                        'source_create_uid': obj_source_create_uid,  # 创建人
                        'number': obj_number,  # 单据编号
                        'recpay_org_id': obj_recpay_org_id,  # 收付组织
                        'biz_date': obj_biz_date,  # 业务日期
                        'state': obj_state,  # 单据状态
                        'currency_id': obj_currency_id,  # 币别
                        'local_currency_id': obj_local_currency_id,  # 本位币
                        'sett_org_id': obj_sett_org_id,  # 结算组织
                        'contact_dept': obj_contact_dept,  # 往来单位
                        'source_sequence': source_sequence,  # 单据行号
                        'cash_acct_number_id': cash_acct_number_id.id if cash_acct_number_id else None,  # 现金账号
                        'income_amount': 0,  # 收入金额
                        'expense_amount': expense_amount,  # 支出金额
                        'income_amount_local': 0,  # 收入金额本位币
                        'expense_amount_local': expense_amount_local,  # 支出金额本位币
                        'payment_purpose': payment_purpose.id if payment_purpose else None,  # 收付款用途
                        'sett_number': sett_number,  # 结算号
                        'sett_type_id': sett_type_id.id if sett_type_id else None,  # 结算方式
                        'summary': summary if summary else '',  # 摘要
                        'is_check': is_check,  # 勾对
                        'source_model_id': source_model_id,  # 来源单据明细行模型id
                        'source_doc_id': source_doc_id,  # 来源单据明细行id
                        'source_parent_model_id': source_parent_model_id,  # 来源单据主表模型id
                        'source_parent_doc_id': obj_source_parent_doc_id,  # 来源单据主表id
                    }
                    if flag:
                        # flag存在则说明不需要进行数据创建，这里直接获取many2one字段的对象即可
                        new_dict['cash_acct_number_id'] = cash_acct_number_id  # 现金账号
                        new_dict['payment_purpose'] = payment_purpose  # 收付款用途
                        new_dict['sett_type_id'] = sett_type_id  # 结算方式
                        new_dict['source_parent_model'] = res.parent_id._name  # 来源单据主表模型

                    create_list.append(new_dict)

                if income_amount != 0 or income_amount_local != 0:
                    # 如果收入金额/收入金额本位币/支出金额/支出金额本位币都为 0 ，则不进行数据创建
                    new_dict = {
                        'tenant_id': obj_tenant_id,  # 租户
                        'source_create_uid': obj_source_create_uid,  # 创建人
                        'number': obj_number,  # 单据编号
                        'recpay_org_id': obj_recpay_org_id,  # 收付组织
                        'biz_date': obj_biz_date,  # 业务日期
                        'state': obj_state,  # 单据状态
                        'currency_id': obj_currency_id,  # 币别
                        'local_currency_id': obj_local_currency_id,  # 本位币
                        'sett_org_id': obj_sett_org_id,  # 结算组织
                        'contact_dept': obj_contact_dept,  # 往来单位
                        'source_sequence': source_sequence,  # 单据行号
                        'cash_acct_number_id': cash_acct_number_id.id if cash_acct_number_id else None,  # 现金账号
                        'income_amount': income_amount,  # 收入金额
                        'expense_amount': 0,  # 支出金额
                        'income_amount_local': income_amount_local,  # 收入金额本位币
                        'expense_amount_local': 0,  # 支出金额本位币
                        'payment_purpose': payment_purpose.id if payment_purpose else None,  # 收付款用途
                        'sett_number': sett_number,  # 结算号
                        'sett_type_id': sett_type_id.id if sett_type_id else None,  # 结算方式
                        'summary': summary if summary else '',  # 摘要
                        'is_check': is_check,  # 勾对
                        'source_model_id': source_model_id,  # 来源单据明细行模型id
                        'source_doc_id': source_doc_id,  # 来源单据明细行id
                        'source_parent_model_id': source_parent_model_id,  # 来源单据主表模型id
                        'source_parent_doc_id': obj_source_parent_doc_id,  # 来源单据主表id
                    }
                    if flag:
                        # flag存在则说明不需要进行数据创建，这里直接获取many2one字段的对象即可
                        new_dict['cash_acct_number_id'] = cash_acct_number_id  # 现金账号
                        new_dict['payment_purpose'] = payment_purpose  # 收付款用途
                        new_dict['sett_type_id'] = sett_type_id  # 结算方式
                        new_dict['source_parent_model'] = res.parent_id._name  # 来源单据主表模型

                    create_list.append(new_dict)
        return create_list

    def _create_data_type_manual_journal(self, obj, source_model_id, source_parent_model_id, flag=False):
        """
        @desc: 创建现金手工日记账相关数据到后台表中
        @params: self: 实列
        @params: obj: 各个单据的明细行数据对象
        @params: source_model_id: 来源单据明细行模型id
        @params: source_parent_model_id: 来源单据主表模型id
        @return: 返回一个list，包含所有需要创建的记录的字典集合。
        """
        create_list = list()

        # 优化性能，将主表obj对象对应字段，提出到for循环外，提高性能
        obj_tenant_id = obj.tenant_id  # 租户
        obj_source_create_uid = obj.create_uid.id if obj.create_uid else None  # 创建人
        obj_number = obj.number  # 单据编号
        obj_recpay_org_id = obj.payrecv_org_id.id if obj.payrecv_org_id else None  # 收付组织
        obj_biz_date = obj.biz_date  # 业务日期
        obj_state = 'audit'  # 单据状态
        obj_currency_id = obj.currency_id.id if obj.currency_id else None  # 币别
        obj_local_currency_id = obj.local_currency_id.id if obj.local_currency_id else None  # 本位币
        obj_source_parent_doc_id = obj.id  # 来源单据主表id

        if flag:
            # flag存在则说明不需要进行数据创建，这里直接获取many2one字段的对象即可
            obj_source_create_uid = obj.create_uid  # 创建人
            obj_recpay_org_id = obj.payrecv_org_id  # 收付组织
            obj_currency_id = obj.currency_id  # 币别
            obj_local_currency_id = obj.local_currency_id  # 本位币
            obj_state = obj.state  # 单据状态

        for res in obj.line1_ids:

            # 由于性能优化，将res的所有字段进行公共提取
            source_sequence = res.sequence  # 单据行号
            cash_acct_number_id = res.cash_acct_number_id  # 现金账号
            income_amount = self._round(res.debit, obj_currency_id)  # 收入金额
            income_amount_local = self._round(res.debit_local, obj_local_currency_id)  # 收入金额本位币
            expense_amount = self._round(res.credit, obj_currency_id)  # 支出金额
            expense_amount_local = self._round(res.credit_local, obj_local_currency_id)  # 支出金额本位币
            sett_number = res.sett_num  # 结算号
            sett_type_id = res.sett_type_id  # 结算方式
            summary = res.summary  # 摘要
            is_check = res.is_check  # 勾对
            source_doc_id = res.id  # 来源单据明细行id

            # 使用create的批量创建方法，获取汇集数据视图的所有字段
            if income_amount != 0 or income_amount_local != 0:
                # 如果收入金额/收入金额本位币/支出金额/支出金额本位币都为 0 ，则不进行数据创建
                new_dict = {
                    'tenant_id': obj_tenant_id,  # 租户
                    'source_create_uid': obj_source_create_uid,  # 创建人
                    'number': obj_number,  # 单据编号
                    'recpay_org_id': obj_recpay_org_id,  # 收付组织
                    'biz_date': obj_biz_date,  # 业务日期
                    'state': obj_state,  # 单据状态
                    'currency_id': obj_currency_id,  # 币别
                    'local_currency_id': obj_local_currency_id,  # 本位币
                    'sett_org_id': None,  # 结算组织
                    'contact_dept': None,  # 往来单位
                    'source_sequence': source_sequence,  # 单据行号
                    'cash_acct_number_id': cash_acct_number_id.id if cash_acct_number_id else None,  # 现金账号
                    'income_amount': income_amount,  # 收入金额
                    'expense_amount': 0,  # 支出金额
                    'income_amount_local': income_amount_local,  # 收入金额本位币
                    'expense_amount_local': 0,  # 支出金额本位币
                    'payment_purpose': None,  # 收付款用途
                    'sett_number': sett_number,  # 结算号
                    'sett_type_id': sett_type_id.id,  # 结算方式
                    'summary': summary if summary else '',  # 摘要
                    'is_check': is_check,  # 勾对
                    'source_model_id': source_model_id,  # 来源单据明细行模型id
                    'source_doc_id': source_doc_id,  # 来源单据明细行id
                    'source_parent_model_id': source_parent_model_id,  # 来源单据主表模型id
                    'source_parent_doc_id': obj_source_parent_doc_id,  # 来源单据主表id
                }
                if flag:
                    # flag存在则说明不需要进行数据创建，这里直接获取many2one字段的对象即可
                    new_dict['cash_acct_number_id'] = cash_acct_number_id  # 现金账号
                    new_dict['sett_type_id'] = sett_type_id  # 结算方式
                    new_dict['source_parent_model'] = res.parent_id._name  # 来源单据主表模型

                create_list.append(new_dict)

            if expense_amount != 0 or expense_amount_local != 0:
                # 如果收入金额/收入金额本位币/支出金额/支出金额本位币都为 0 ，则不进行数据创建
                new_dict = {
                    'tenant_id': obj_tenant_id,  # 租户
                    'source_create_uid': obj_source_create_uid,  # 创建人
                    'number': obj_number,  # 单据编号
                    'recpay_org_id': obj_recpay_org_id,  # 收付组织
                    'biz_date': obj_biz_date,  # 业务日期
                    'state': obj_state,  # 单据状态
                    'currency_id': obj_currency_id,  # 币别
                    'local_currency_id': obj_local_currency_id,  # 本位币
                    'sett_org_id': None,  # 结算组织
                    'contact_dept': None,  # 往来单位
                    'source_sequence': source_sequence,  # 单据行号
                    'cash_acct_number_id': cash_acct_number_id.id if cash_acct_number_id else None,  # 现金账号
                    'income_amount': 0,  # 收入金额
                    'expense_amount': expense_amount,  # 支出金额
                    'income_amount_local': 0,  # 收入金额本位币
                    'expense_amount_local': expense_amount_local,  # 支出金额本位币
                    'payment_purpose': None,  # 收付款用途
                    'sett_number': sett_number,  # 结算号
                    'sett_type_id': sett_type_id.id,  # 结算方式
                    'summary': summary if summary else '',  # 摘要
                    'is_check': is_check,  # 勾对
                    'source_model_id': source_model_id,  # 来源单据明细行模型id
                    'source_doc_id': source_doc_id,  # 来源单据明细行id
                    'source_parent_model_id': source_parent_model_id,  # 来源单据主表模型id
                    'source_parent_doc_id': obj_source_parent_doc_id,  # 来源单据主表id
                }
                if flag:
                    # flag存在则说明不需要进行数据创建，这里直接获取many2one字段的对象即可
                    new_dict['cash_acct_number_id'] = cash_acct_number_id  # 现金账号
                    new_dict['sett_type_id'] = sett_type_id  # 结算方式
                    new_dict['source_parent_model'] = res.parent_id._name  # 来源单据主表模型

                create_list.append(new_dict)
        return create_list

    def _round(self, value, currency_id):
        return self.env["mdm.currency"].p_amount_float_round(value, currency_id)

    def _get_parent_data(self, model, domain, fields):
        records = self.env[model].search(domain)
        return records.ids, records.read(fields=fields)

    def _get_line_dict(self, doc_ids, model, fields):
        lines_data = self.env[model].search_read([('parent_id', 'in', doc_ids)], fields=fields)

        lines_dict = dict() # 存放parent_id及表体的对应关系，即根据parent_id进行分组
        for line in lines_data:
            if line['parent_id']:
                parent_id = line['parent_id'][0]
                if parent_id not in lines_dict:
                    lines_dict[parent_id] = []
                lines_dict[parent_id].append(line)
        return lines_dict
    

    def _create_data_type_sale_receive_s(self, parent, lines, source_model_id, source_parent_model_id, source_parent_model, cash_sett_type_ids):
        """
        @desc: 创建销售业务收款单/其他业务收款单相关数据到后台表中
        @params: self: 实列
        @params: obj: 各个单据的明细行数据对象
        @params: source_model_id: 来源单据明细行模型id
        @params: source_parent_model_id: 来源单据主表模型id
        @return: 返回一个list，包含所有需要创建的记录的字典集合。
        """
        create_list = list()

        # 优化性能，将主表obj对象对应字段，提出到for循环外，提高性能
        doc_id = parent['id']  # 来源单据主表id
        tenant_id = parent['tenant_id']  # 租户
        number = parent['number']  # 单据编号
        create_uid = parent['create_uid']  # 创建人
        recpay_org_id = parent['recv_org_id'] # 收付组织
        biz_date = parent['biz_date']  # 业务日期
        state = parent['state']  # 单据状态
        currency_id = parent['currency_id'] # 币别
        local_currency_id = parent['local_curr_id']  # 本位币
        sett_org_id = parent['sett_org_id'] and parent['sett_org_id'][0]  # 结算组织
        contact_dept = parent['contact_dept']  # 往来单位
        for line in lines:
            sett_type_id = line['sett_type_id']
            # 取明细行数据，结算方式为现金业务的
            if sett_type_id and sett_type_id[0] in cash_sett_type_ids:
                cash_acct_number_id = line['cash_acct_id']  # 现金账号
                payment_purpose = line['biz_type_id']  # 收付款用途
                income_amount = abs(line['discount_amount'])  # 收入金额
                income_amount_local = abs(line['discount_amount_local'])  # 收入金额本位币
                expense_amount = abs(line['commission'])  # 支出金额
                expense_amount_local = abs(line['commission_local'])  # 支出金额本位币

                base_dict = {
                    'tenant_id': tenant_id,  # 租户
                    'source_create_uid': create_uid,  # 创建人
                    'number': number,  # 单据编号
                    'recpay_org_id': recpay_org_id,  # 收付组织
                    'biz_date': biz_date,  # 业务日期
                    'state': state,  # 单据状态
                    'currency_id': currency_id,  # 币别
                    'local_currency_id': local_currency_id,  # 本位币
                    'sett_org_id': sett_org_id,  # 结算组织
                    'contact_dept': contact_dept,  # 往来单位
                    'source_sequence': line['sequence'],  # 单据行号
                    'sett_number': line['sett_number'],  # 结算号
                    'summary': line['note'] or '',  # 摘要
                    'is_check': line['is_check'],  # 勾对
                    'source_model_id': source_model_id,  # 来源单据明细行模型id
                    'source_doc_id': line['id'],  # 来源单据明细行id
                    'source_parent_doc_id': doc_id,  # 来源单据主表id
                    'cash_acct_number_id': cash_acct_number_id,  # 现金账号
                    'payment_purpose': payment_purpose,  # 收付款用途
                    'sett_type_id': sett_type_id,  # 结算方式
                    'source_parent_model': source_parent_model # 来源单据主表模型
                }
                
                if expense_amount != 0 or expense_amount_local != 0:
                    # 如果收入金额/收入金额本位币/支出金额/支出金额本位币都为 0 ，则不进行数据创建
                    create_list.append({
                        'income_amount': 0,  # 收入金额
                        'expense_amount': expense_amount,  # 支出金额
                        'income_amount_local': 0,  # 收入金额本位币
                        'expense_amount_local': expense_amount_local,  # 支出金额本位币
                        **base_dict
                    })

                if income_amount != 0 or income_amount_local != 0:
                    # 如果收入金额/收入金额本位币/支出金额/支出金额本位币都为 0 ，则不进行数据创建
                    create_list.append({
                        'income_amount': income_amount,  # 收入金额
                        'expense_amount': 0,  # 支出金额
                        'income_amount_local': income_amount_local,  # 收入金额本位币
                        'expense_amount_local': 0,  # 支出金额本位币
                        **base_dict
                    })
        return create_list

    def _create_data_type_cash_recycling_s(self, parent, lines, source_model_id, source_parent_model_id, source_parent_model):
        """
        @desc: 创建现金存款单相关数据到后台表中
        @params: self: 实列
        @params: parent: 现金存取单表头数据
        @params: source_model_id: 来源单据明细行模型id
        @params: source_parent_model_id: 来源单据主表模型id
        @return: 返回一个list，包含所有需要创建的记录的字典集合。
        """
        create_list = list()

        # 优化性能，将主表obj对象对应字段，提出到for循环外，提高性能
        doc_id = parent['id']  # 来源单据主表id
        tenant_id = parent['tenant_id']  # 租户
        number = parent['number']  # 单据编号
        create_uid = parent['create_uid']  # 创建人
        recpay_org_id = parent['recv_org_id'] # 收付组织
        biz_date = parent['biz_date']  # 业务日期
        state = parent['state']  # 单据状态
        local_currency_id = parent['local_currency_id']  # 本位币
        document_type = parent['document_type'] # 单据类型
    
        for line in lines:
            currency_id = line['currency_id']  # 币别
            cash_acct_number = line['cash_acct_number']  # 现金账号
            amount = line['pay_amount'] # 支出金额
            amount_local = line['pay_amount_lc']  # 支出金额本位币

            # 使用create的批量创建方法，获取汇集数据视图的所有字段
            if amount != 0 or amount_local != 0:
                # 如果收入金额/收入金额本位币/支出金额/支出金额本位币都为 0 ，则不进行数据创建
                new_dict = {
                    'tenant_id': tenant_id,  # 租户
                    'source_create_uid': create_uid,  # 创建人
                    'number': number,  # 单据编号
                    'recpay_org_id': recpay_org_id,  # 收付组织
                    'biz_date': biz_date,  # 业务日期
                    'state': state,  # 单据状态
                    'local_currency_id': local_currency_id,  # 本位币
                    'sett_org_id': None,  # 结算组织
                    'contact_dept': None,  # 往来单位
                    'source_sequence': line['sequence'],  # 单据行号
                    'payment_purpose': None,  # 收付款用途
                    'sett_number': line['sett_number'],  # 结算号
                    'sett_type_id': None,  # 结算方式
                    'summary': line['abstract'] or '',  # 摘要
                    'is_check': line['is_check'],  # 勾对
                    'source_model_id': source_model_id,  # 来源单据明细行模型id
                    'source_doc_id': line['id'],  # 来源单据明细行id
                    'source_parent_model_id': source_parent_model_id,  # 来源单据主表模型id
                    'source_parent_doc_id': doc_id,  # 来源单据主表id
                    'source_parent_model': source_parent_model,  # 来源单据主表模型
                    'currency_id': currency_id,  # 币别
                    'cash_acct_number_id': cash_acct_number # 现金账号
                }
                # 存款单
                if document_type == 'cash_deposit':
                    new_dict.update({
                        'income_amount': 0,  # 收入金额
                        'expense_amount': amount,  # 支出金额
                        'income_amount_local': 0,  # 收入金额本位币
                        'expense_amount_local': amount_local,  # 支出金额本位币
                    })
                # 取款单
                else:
                    new_dict.update({
                        'income_amount': amount,  # 收入金额
                        'expense_amount': 0,  # 支出金额
                        'income_amount_local': amount_local,  # 收入金额本位币
                        'expense_amount_local': 0,  # 支出金额本位币
                    })
                
        

                create_list.append(new_dict)
        return create_list
    def _create_data_type_cash_transfer_s(self, parent, transfer_lines, source_model_id, source_parent_model_id, source_parent_model):
    # def _create_data_type_cash_transfer_s(self, obj, source_model_id, source_parent_model_id, flag=False):
        """
        @desc: 创建现金转账单相关数据到后台表中
        @params: self: 实列
        @params: obj: 各个单据的明细行数据对象
        @params: source_model_id: 来源单据明细行模型id
        @params: source_parent_model_id: 来源单据主表模型id
        @return: 返回一个list，包含所有需要创建的记录的字典集合。
        """
        create_list = list()

        # 优化性能，将主表obj对象对应字段，提出到for循环外，提高性能
        obj_source_parent_doc_id = source_parent_model_id  # 来源单据主表id
        obj_tenant_id = parent['tenant_id']  # 租户
        obj_number = parent['number']  # 单据编号
        obj_source_create_uid = parent['create_uid']  # 创建人
        obj_recpay_org_id = parent['col_org_id'] # 收付组织
        obj_biz_date = parent['biz_date']  # 业务日期
        obj_state = parent['state']  # 单据状态
        # obj_currency_id = parent['currency_id'] # 币别
        obj_local_currency_id = parent['local_curr_id']  # 本位币
       

        for line in transfer_lines:

            # 由于性能优化，将line的所有字段进行公共提取
            currency_id = line['currency_id']  # 币别
            source_sequence = line['sequence']  # 单据行号
            cash_in_acct_number_id = line['cash_in_account_id']  # 现金账号（转入）
            cash_out_acct_number_id = line['cash_out_account_id']  # 现金账号（转出）
            income_amount = self._round(line['in_amount'], currency_id[0])  # 收入金额
            income_amount_local = self._round(line['in_amount_lc'], obj_local_currency_id[0])  # 收入金额本位币
            charge = line['charge']  # 手续费
            charge_local = line['charge_lc']  # 手续费本位币
            sett_in_number = line['in_no']  # 结算号（转入）
            sett_out_number = line['out_no']  # 结算号（转入）
            summary = line['abstract']  # 摘要
            is_in_check = line['is_in_check']  # 勾对（转入）
            is_out_check = line['is_out_check']  # 勾对（转出）
            source_doc_id = line['id']  # 来源单据明细行id

            # 使用create的批量创建方法，获取汇集数据视图的所有字段
            if income_amount != 0 or income_amount_local != 0:
                # 如果收入金额/收入金额本位币/支出金额/支出金额本位币都为 0 ，则不进行数据创建
                new_dict = {
                    'tenant_id': obj_tenant_id,  # 租户
                    'source_create_uid': obj_source_create_uid,  # 创建人
                    'number': obj_number,  # 单据编号
                    'recpay_org_id': obj_recpay_org_id,  # 收付组织
                    'biz_date': obj_biz_date,  # 业务日期
                    'state': obj_state,  # 单据状态
                    'currency_id': currency_id if currency_id else None,  # 币别
                    'local_currency_id': obj_local_currency_id,  # 本位币
                    'sett_org_id': None,  # 结算组织
                    'contact_dept': None,  # 往来单位
                    'source_sequence': source_sequence,  # 单据行号
                    'cash_acct_number_id': cash_in_acct_number_id if cash_in_acct_number_id else None,  # 现金账号
                    'income_amount': income_amount,  # 收入金额
                    'expense_amount': 0,  # 支出金额
                    'income_amount_local': income_amount_local,  # 收入金额本位币
                    'expense_amount_local': 0,  # 支出金额本位币
                    'payment_purpose': None,  # 收付款用途
                    'sett_number': sett_in_number,  # 结算号
                    'sett_type_id': None,  # 结算方式
                    'summary': summary if summary else '',  # 摘要
                    'is_check': is_in_check,  # 勾对
                    'source_model_id': source_model_id,  # 来源单据明细行模型id
                    'source_doc_id': source_doc_id,  # 来源单据明细行id
                    'source_parent_model_id': source_parent_model_id,  # 来源单据主表模型id
                    'source_parent_doc_id': obj_source_parent_doc_id,  # 来源单据主表id
                    'source_parent_model': source_parent_model # 来源单据主表模型

                }
                
                    

                create_list.append(new_dict)

            if charge != 0 or charge_local != 0:
                # 如果收入金额/收入金额本位币/支出金额/支出金额本位币都为 0 ，则不进行数据创建
                new_dict = {
                    'tenant_id': obj_tenant_id,  # 租户
                    'source_create_uid': obj_source_create_uid,  # 创建人
                    'number': obj_number,  # 单据编号
                    'recpay_org_id': obj_recpay_org_id,  # 收付组织
                    'biz_date': obj_biz_date,  # 业务日期
                    'state': obj_state,  # 单据状态
                    'currency_id': currency_id if currency_id else None,  # 币别
                    'local_currency_id': obj_local_currency_id,  # 本位币
                    'sett_org_id': None,  # 结算组织
                    'contact_dept': None,  # 往来单位
                    # 'cash_acct_number_id': cash_out_acct_number_id[0] if cash_out_acct_number_id else None,  # 现金账号
                    'income_amount': 0,  # 收入金额
                    'expense_amount': self._round(charge, currency_id[0]),  # 支出金额
                    'income_amount_local': 0,  # 收入金额本位币
                    'expense_amount_local': self._round(charge_local, obj_local_currency_id[0]),  # 支出金额本位币
                    'payment_purpose': None,  # 收付款用途
                    'sett_number': sett_out_number,  # 结算号
                    'sett_type_id': None,  # 结算方式
                    'summary': summary if summary else '',  # 摘要
                    'is_check': is_out_check,  # 勾对
                    'source_model_id': source_model_id,  # 来源单据明细行模型id
                    'source_doc_id': source_doc_id,  # 来源单据明细行id
                    'source_parent_model_id': source_parent_model_id,  # 来源单据主表模型id
                    'source_parent_doc_id': obj_source_parent_doc_id,  # 来源单据主表id
                    'source_parent_model': source_parent_model # 来源单据主表模型
                }
                

                create_list.append(new_dict)

            if income_amount != 0 or income_amount_local != 0:
                # 如果收入金额/收入金额本位币/支出金额/支出金额本位币都为 0 ，则不进行数据创建
                new_dict = {
                    'tenant_id': obj_tenant_id,  # 租户
                    'source_create_uid': obj_source_create_uid,  # 创建人
                    'number': obj_number,  # 单据编号
                    'recpay_org_id': obj_recpay_org_id,  # 收付组织
                    'biz_date': obj_biz_date,  # 业务日期
                    'state': obj_state,  # 单据状态
                    'currency_id': currency_id if currency_id else None,  # 币别
                    'local_currency_id': obj_local_currency_id,  # 本位币
                    'sett_org_id': None,  # 结算组织
                    'contact_dept': None,  # 往来单位
                    'source_sequence': source_sequence,  # 单据行号
                    'cash_acct_number_id': cash_out_acct_number_id if cash_out_acct_number_id else None,  # 现金账号
                    'income_amount': 0,  # 收入金额
                    'expense_amount': income_amount,  # 支出金额
                    'income_amount_local': 0,  # 收入金额本位币
                    'expense_amount_local': income_amount_local,  # 支出金额本位币
                    'payment_purpose': None,  # 收付款用途
                    'sett_number': sett_out_number,  # 结算号
                    'sett_type_id': None,  # 结算方式
                    'summary': summary if summary else '',  # 摘要
                    'is_check': is_out_check,  # 勾对
                    'source_model_id': source_model_id,  # 来源单据明细行模型id
                    'source_doc_id': source_doc_id,  # 来源单据明细行id
                    'source_parent_model_id': source_parent_model_id,  # 来源单据主表模型id
                    'source_parent_doc_id': obj_source_parent_doc_id,  # 来源单据主表id
                    'source_parent_model': source_parent_model # 来源单据主表模型
                }
                create_list.append(new_dict)
        return create_list
    
    def _create_data_type_foreign_cash_s(self, parent, foreign_lines, source_model_id, source_parent_model_id, source_parent_model):
        """
        @desc: 创建现金购汇单相关数据到后台表中
        @params: self: 实列
        @params: obj: 各个单据的明细行数据对象
        @params: source_model_id: 来源单据明细行模型id
        @params: source_parent_model_id: 来源单据主表模型id
        @return: 返回一个list，包含所有需要创建的记录的字典集合。
        """
        create_list = list()

        # 优化性能，将主表obj对象对应字段，提出到for循环外，提高性能
        obj_tenant_id = parent['tenant_id']  # 租户
        obj_source_create_uid = parent['create_uid']  # 创建人
        obj_number = parent['number']  # 单据编号
        obj_recpay_org_id = parent['col_org_id']  # 收付组织
        obj_biz_date = parent['biz_date']  # 业务日期
        obj_state = parent['state']  # 单据状态
        obj_local_currency_id = parent['local_curr_id']  # 本位币
        obj_source_parent_doc_id = source_parent_model_id  # 来源单据主表id


        for line in foreign_lines:

            # 由于性能优化，将line的所有字段进行公共提取
            in_currency_id = line['in_currency_id']  # 币别（转入）
            out_currency_id = line['out_currency_id']  # 币别（转出）
            source_sequence = line['sequence']  # 单据行号
            cash_in_acct_number_id = line['cash_in_account_id']  # 现金账号（转入）
            cash_out_acct_number_id = line['cash_out_account_id']  # 现金账号（转出）
            income_amount = self._round(line['in_amount'], in_currency_id[0])  # 收入金额
            income_amount_local = self._round(line['in_amount_lc'], obj_local_currency_id[0])  # 收入金额本位币
            charge = line['charge']  # 手续费
            charge_local = line['charge_lc']  # 手续费本位币
            expense_amount = self._round(line['out_amount'], out_currency_id[0])  # 支出金额
            expense_amount_local = self._round(line['out_amount_lc'], obj_local_currency_id[0])  # 支出金额本位币
            sett_in_number = line['in_no']  # 结算号（转入）
            sett_out_number = line['out_no']  # 结算号（转入）
            summary = line['abstract']  # 摘要
            is_in_check = line['is_in_check']  # 勾对（转入）
            is_out_check = line['is_out_check']  # 勾对（转出）
            source_doc_id = line['id']  # 来源单据明细行id

            # 使用create的批量创建方法，获取汇集数据视图的所有字段
            if income_amount != 0 or income_amount_local != 0:
                # 如果收入金额/收入金额本位币/支出金额/支出金额本位币都为 0 ，则不进行数据创建
                new_dict = {
                    'tenant_id': obj_tenant_id,  # 租户
                    'source_create_uid': obj_source_create_uid,  # 创建人
                    'number': obj_number,  # 单据编号
                    'recpay_org_id': obj_recpay_org_id,  # 收付组织
                    'biz_date': obj_biz_date,  # 业务日期
                    'state': obj_state,  # 单据状态
                    'currency_id': in_currency_id if in_currency_id else None,  # 币别
                    'local_currency_id': obj_local_currency_id,  # 本位币
                    'sett_org_id': None,  # 结算组织
                    'contact_dept': None,  # 往来单位
                    'source_sequence': source_sequence,  # 单据行号
                    'cash_acct_number_id': cash_in_acct_number_id if cash_in_acct_number_id else None,  # 现金账号
                    'income_amount': income_amount,  # 收入金额
                    'expense_amount': 0,  # 支出金额
                    'income_amount_local': income_amount_local,  # 收入金额本位币
                    'expense_amount_local': 0,  # 支出金额本位币
                    'payment_purpose': None,  # 收付款用途
                    'sett_number': sett_in_number,  # 结算号
                    'sett_type_id': None,  # 结算方式
                    'summary': summary if summary else '',  # 摘要
                    'is_check': is_in_check,  # 勾对
                    'source_model_id': source_model_id,  # 来源单据明细行模型id
                    'source_doc_id': source_doc_id,  # 来源单据明细行id
                    'source_parent_model_id': source_parent_model_id,  # 来源单据主表模型id
                    'source_parent_doc_id': obj_source_parent_doc_id,  # 来源单据主表id
                    'source_parent_model': source_parent_model # 来源单据主表模型
                }
                

                create_list.append(new_dict)

            if charge != 0 or charge_local != 0:
                # 如果收入金额/收入金额本位币/支出金额/支出金额本位币都为 0 ，则不进行数据创建
                new_dict = {
                    'tenant_id': obj_tenant_id,  # 租户
                    'source_create_uid': obj_source_create_uid,  # 创建人
                    'number': obj_number,  # 单据编号
                    'recpay_org_id': obj_recpay_org_id,  # 收付组织
                    'biz_date': obj_biz_date,  # 业务日期
                    'state': obj_state,  # 单据状态
                    'currency_id': out_currency_id if out_currency_id else None,  # 币别
                    'local_currency_id': obj_local_currency_id,  # 本位币
                    'sett_org_id': None,  # 结算组织
                    'contact_dept': None,  # 往来单位
                    'source_sequence': source_sequence,  # 单据行号
                    'cash_acct_number_id': cash_out_acct_number_id if cash_out_acct_number_id else None,  # 现金账号
                    'income_amount': 0,  # 收入金额
                    'expense_amount': self._round(charge, out_currency_id),  # 支出金额
                    'income_amount_local': 0,  # 收入金额本位币
                    'expense_amount_local': self._round(charge_local, obj_local_currency_id),  # 支出金额本位币
                    'payment_purpose': None,  # 收付款用途
                    'sett_number': sett_out_number,  # 结算号
                    'sett_type_id': None,  # 结算方式
                    'summary': summary if summary else '',  # 摘要
                    'is_check': is_out_check,  # 勾对
                    'source_model_id': source_model_id,  # 来源单据明细行模型id
                    'source_doc_id': source_doc_id,  # 来源单据明细行id
                    'source_parent_model_id': source_parent_model_id,  # 来源单据主表模型id
                    'source_parent_doc_id': obj_source_parent_doc_id,  # 来源单据主表id
                    'source_parent_model': source_parent_model # 来源单据主表模型
                }
                

                create_list.append(new_dict)

            if expense_amount != 0 or expense_amount_local != 0:
                # 如果收入金额/收入金额本位币/支出金额/支出金额本位币都为 0 ，则不进行数据创建
                new_dict = {
                    'tenant_id': obj_tenant_id,  # 租户
                    'source_create_uid': obj_source_create_uid,  # 创建人
                    'number': obj_number,  # 单据编号
                    'recpay_org_id': obj_recpay_org_id,  # 收付组织
                    'biz_date': obj_biz_date,  # 业务日期
                    'state': obj_state,  # 单据状态
                    'currency_id': out_currency_id if out_currency_id else None,  # 币别
                    'local_currency_id': obj_local_currency_id,  # 本位币
                    'sett_org_id': None,  # 结算组织
                    'contact_dept': None,  # 往来单位
                    'source_sequence': source_sequence,  # 单据行号
                    'cash_acct_number_id': cash_out_acct_number_id if cash_out_acct_number_id else None,  # 现金账号
                    'income_amount': 0,  # 收入金额
                    'expense_amount': expense_amount,  # 支出金额
                    'income_amount_local': 0,  # 收入金额本位币
                    'expense_amount_local': expense_amount_local,  # 支出金额本位币
                    'payment_purpose': None,  # 收付款用途
                    'sett_number': sett_out_number,  # 结算号
                    'sett_type_id': None,  # 结算方式
                    'summary': summary if summary else '',  # 摘要
                    'is_check': is_out_check,  # 勾对
                    'source_model_id': source_model_id,  # 来源单据明细行模型id
                    'source_doc_id': source_doc_id,  # 来源单据明细行id
                    'source_parent_model_id': source_parent_model_id,  # 来源单据主表模型id
                    'source_parent_doc_id': obj_source_parent_doc_id,  # 来源单据主表id
                    'source_parent_model': source_parent_model # 来源单据主表模型
                }
                

                create_list.append(new_dict)
        return create_list

    def _create_data_type_sale_refund_s(self, parent, lines, source_model_id, source_parent_model_id, source_parent_model, cash_sett_type_ids):
        """
        @desc: 创建销售业务收款退款单/其他业务收款退款单相关数据到后台表中
        @params: self: 实列
        @params: obj: 各个单据的明细行数据对象
        @params: source_model_id: 来源单据明细行模型id
        @params: source_parent_model_id: 来源单据主表模型id
        @return: 返回一个list，包含所有需要创建的记录的字典集合。
        """
        create_list = list()

        # 优化性能，将主表obj对象对应字段，提出到for循环外，提高性能
        obj_source_create_uid = parent['create_uid']  # 创建人
        obj_number = parent['number']  # 单据编号
        obj_recpay_org_id = parent['recv_org_id']  # 收付组织
        obj_biz_date = parent['biz_date']  # 业务日期
        obj_state = parent['state']  # 单据状态
        obj_currency_id = parent['currency_id']  # 币别
        obj_local_currency_id = parent['local_curr_id']  # 本位币
        obj_sett_org_id = parent['sett_org_id']  # 结算组织
        obj_source_parent_doc_id = source_parent_model_id  # 来源单据主表id

    

        for line in lines:
            if line['sett_type_id'][0] == cash_sett_type_ids[0]:

                # 由于性能优化，将res的所有字段进行公共提取
                source_sequence = line['sequence']  # 单据行号
                cash_acct_number_id = line['cash_acct_id']  # 现金账号
                income_amount = abs(self._round(line['discount_amount'], obj_currency_id[0]))  # 收入金额
                income_amount_local = abs(self._round(line['discount_amount_local'], obj_local_currency_id[0]))  # 收入金额本位币
                expense_amount = abs(self._round(line['commission'], obj_currency_id[0]))  # 支出金额
                expense_amount_local = abs(self._round(line['commission_local'], obj_local_currency_id[0]))  # 支出金额本位币
                payment_purpose = line['biz_type_id']  # 收付款用途
                sett_number = line['sett_number']  # 结算号
                sett_type_id = line['sett_type_id']  # 结算方式
                summary = line['note']  # 摘要
                is_check = line['is_check']  # 勾对
                source_doc_id = line['id']  # 来源单据明细行id

                # 取明细行数据，结算方式为现金业务的
                # 使用create的批量创建方法，获取汇集数据视图的所有字段
                if expense_amount != 0 or expense_amount_local != 0:
                    # 如果收入金额/收入金额本位币/支出金额/支出金额本位币都为 0 ，则不进行数据创建
                    new_dict = {
                        'source_create_uid': obj_source_create_uid,  # 创建人
                        'number': obj_number,  # 单据编号
                        'recpay_org_id': obj_recpay_org_id,  # 收付组织
                        'biz_date': obj_biz_date,  # 业务日期
                        'state': obj_state,  # 单据状态
                        'currency_id': obj_currency_id,  # 币别
                        'local_currency_id': obj_local_currency_id,  # 本位币
                        'sett_org_id': obj_sett_org_id,  # 结算组织
                        'contact_dept': obj_contact_dept,  # 往来单位
                        'source_sequence': source_sequence,  # 单据行号
                        'cash_acct_number_id': cash_acct_number_id if cash_acct_number_id else None,  # 现金账号
                        'income_amount': 0,  # 收入金额
                        'expense_amount': expense_amount,  # 支出金额
                        'income_amount_local': 0,  # 收入金额本位币
                        'expense_amount_local': expense_amount_local,  # 支出金额本位币
                        'payment_purpose': payment_purpose if payment_purpose else None,  # 收付款用途
                        'sett_number': sett_number,  # 结算号
                        'sett_type_id': sett_type_id if sett_type_id else None,  # 结算方式
                        'summary': summary if summary else '',  # 摘要
                        'is_check': is_check,  # 勾对
                        'source_model_id': source_model_id,  # 来源单据明细行模型id
                        'source_doc_id': source_doc_id,  # 来源单据明细行id
                        'source_parent_model_id': source_parent_model_id,  # 来源单据主表模型id
                        'source_parent_doc_id': obj_source_parent_doc_id,  # 来源单据主表id
                        'source_parent_model': source_parent_model # 来源单据主表模型
                    }
                   

                    create_list.append(new_dict)

                if income_amount != 0 or income_amount_local != 0:
                    # 如果收入金额/收入金额本位币/支出金额/支出金额本位币都为 0 ，则不进行数据创建
                    new_dict = {
                        'source_create_uid': obj_source_create_uid,  # 创建人
                        'number': obj_number,  # 单据编号
                        'recpay_org_id': obj_recpay_org_id,  # 收付组织
                        'biz_date': obj_biz_date,  # 业务日期
                        'state': obj_state,  # 单据状态
                        'currency_id': obj_currency_id,  # 币别
                        'local_currency_id': obj_local_currency_id,  # 本位币
                        'sett_org_id': obj_sett_org_id,  # 结算组织
                        'source_sequence': source_sequence,  # 单据行号
                        'cash_acct_number_id': cash_acct_number_id if cash_acct_number_id else None,  # 现金账号
                        'income_amount': 0,  # 收入金额
                        'expense_amount': income_amount,  # 支出金额
                        'income_amount_local': 0,  # 收入金额本位币
                        'expense_amount_local': income_amount_local,  # 支出金额本位币
                        'payment_purpose': payment_purpose if payment_purpose else None,  # 收付款用途
                        'sett_number': sett_number,  # 结算号
                        'sett_type_id': sett_type_id if sett_type_id else None,  # 结算方式
                        'summary': summary if summary else '',  # 摘要
                        'is_check': is_check,  # 勾对
                        'source_model_id': source_model_id,  # 来源单据明细行模型id
                        'source_doc_id': source_doc_id,  # 来源单据明细行id
                        'source_parent_model_id': source_parent_model_id,  # 来源单据主表模型id
                        'source_parent_doc_id': obj_source_parent_doc_id,  # 来源单据主表id
                        'source_parent_model': source_parent_model # 来源单据主表模型
                    }
                    

                    create_list.append(new_dict)
        return create_list

    def _create_data_type_purchase_receive_s(self, parent, lines, source_model_id, source_parent_model_id, source_parent_model, cash_sett_type_ids):
        """
        @desc: 创建采购业务付款单/其他业务付款单相关数据到后台表中
        @params: self: 实列
        @params: obj: 各个单据的明细行数据对象
        @params: source_model_id: 来源单据明细行模型id
        @params: source_parent_model_id: 来源单据主表模型id
        @return: 返回一个list，包含所有需要创建的记录的字典集合。
        """
        create_list = list()

        # 优化性能，将主表obj对象对应字段，提出到for循环外，提高性能
        obj_source_create_uid = parent['create_uid']  # 创建人
        obj_number = parent['number']  # 单据编号
        obj_recpay_org_id = parent['pay_org_id']  # 收付组织
        obj_biz_date = parent['biz_date']  # 业务日期
        obj_state = parent['state']    # 单据状态
        obj_currency_id = parent['sett_curr_id']  # 结算币别
        obj_local_currency_id = parent['local_curr_id']  # 本位币
        obj_sett_org_id = parent['sett_org_id']  # 结算组织
        obj_source_parent_doc_id = source_parent_model_id  # 来源单据主表id	



        for line in lines:

            # 由于性能优化，将line的所有字段进行公共提取
            source_sequence = line['sequence']  # 单据行号
            cash_acct_number_id = line['cash_acct_id']  # 现金账号
            income_amount = abs(self._round(line['discount_amount'], obj_currency_id[0]))  # 收入金额
            income_amount_local = abs(self._round(line['discount_amount_local'], obj_local_currency_id[0]))  # 收入金额本位币
            expense_amount = abs(self._round(line['commission'], obj_currency_id[0]))  # 支出金额
            expense_amount_local = abs(self._round(line['commission_local'], obj_local_currency_id[0]))  # 支出金额本位币
            payment_purpose = line['pay_type_id']  # 收付款用途
            sett_type_id = line['sett_type_id']  # 结算方式
            summary = line['note']  # 摘要
            is_check = line['is_check']  # 勾对
            source_doc_id = line['id']  # 来源单据明细行id

            if line['sett_type_id'][0] == cash_sett_type_ids[0]:
                # 取明细行数据，结算方式为现金业务的
                # 使用create的批量创建方法，获取汇集数据视图的所有字段
                if expense_amount != 0 or expense_amount_local != 0:
                    # 如果收入金额/收入金额本位币/支出金额/支出金额本位币都为 0 ，则不进行数据创建
                    new_dict = {
                        'source_create_uid': obj_source_create_uid,  # 创建人
                        'number': obj_number,  # 单据编号
                        'recpay_org_id': obj_recpay_org_id,  # 收付组织
                        'biz_date': obj_biz_date,  # 业务日期
                        'state': obj_state,  # 单据状态
                        'currency_id': obj_currency_id,  # 币别
                        'local_currency_id': obj_local_currency_id,  # 本位币
                        'sett_org_id': obj_sett_org_id,  # 结算组织
                        'source_sequence': source_sequence,  # 单据行号
                        'cash_acct_number_id': cash_acct_number_id if cash_acct_number_id else None,  # 现金账号
                        'income_amount': 0,  # 收入金额
                        'expense_amount': expense_amount,  # 支出金额
                        'income_amount_local': 0,  # 收入金额本位币
                        'expense_amount_local': expense_amount_local,  # 支出金额本位币
                        'payment_purpose': payment_purpose if payment_purpose else None,  # 收付款用途
                        'sett_type_id': sett_type_id if sett_type_id else None,  # 结算方式
                        'summary': summary if summary else '',  # 摘要
                        'is_check': is_check,  # 勾对
                        'source_model_id': source_model_id,  # 来源单据明细行模型id
                        'source_doc_id': source_doc_id,  # 来源单据明细行id
                        'source_parent_model_id': source_parent_model_id,  # 来源单据主表模型id
                        'source_parent_doc_id': obj_source_parent_doc_id,  # 来源单据主表id
                        'source_parent_model': source_parent_model # 来源单据主表模型
                    }
                    

                    create_list.append(new_dict)

                if income_amount != 0 or income_amount_local != 0:
                    # 如果收入金额/收入金额本位币/支出金额/支出金额本位币都为 0 ，则不进行数据创建
                    new_dict = {
                        'source_create_uid': obj_source_create_uid,  # 创建人
                        'number': obj_number,  # 单据编号
                        'recpay_org_id': obj_recpay_org_id,  # 收付组织
                        'biz_date': obj_biz_date,  # 业务日期
                        'state': obj_state,  # 单据状态
                        'currency_id': obj_currency_id,  # 币别
                        'local_currency_id': obj_local_currency_id,  # 本位币
                        'sett_org_id': obj_sett_org_id,  # 结算组织
                        'source_sequence': source_sequence,  # 单据行号
                        'cash_acct_number_id': cash_acct_number_id if cash_acct_number_id else None,  # 现金账号
                        'income_amount': 0,  # 收入金额
                        'expense_amount': income_amount,  # 支出金额
                        'income_amount_local': 0,  # 收入金额本位币
                        'expense_amount_local': income_amount_local,  # 支出金额本位币
                        'payment_purpose': payment_purpose if payment_purpose else None,  # 收付款用途
                        'sett_type_id': sett_type_id if sett_type_id else None,  # 结算方式
                        'summary': summary if summary else '',  # 摘要
                        'is_check': is_check,  # 勾对
                        'source_model_id': source_model_id,  # 来源单据明细行模型id
                        'source_doc_id': source_doc_id,  # 来源单据明细行id
                        'source_parent_model_id': source_parent_model_id,  # 来源单据主表模型id
                        'source_parent_doc_id': obj_source_parent_doc_id,  # 来源单据主表id
                        'source_parent_model': source_parent_model # 来源单据主表模型
                    }
                    

                    create_list.append(new_dict)
        return create_list

    def _create_data_type_purchase_refund_s(self, parent, lines, source_model_id, source_parent_model_id, source_parent_model, cash_sett_type_ids):
        """
        @desc: 创建采购业务付款退款单/其他业务付款退款单相关数据到后台表中
        @params: self: 实列
        @params: obj: 各个单据的明细行数据对象
        @params: source_model_id: 来源单据明细行模型id
        @params: source_parent_model_id: 来源单据主表模型id
        @return: 返回一个list，包含所有需要创建的记录的字典集合。
        """
        create_list = list()

        # 优化性能，将主表obj对象对应字段，提出到for循环外，提高性能
        obj_source_create_uid =  parent['create_uid']  # 创建人
        obj_number = parent['number']  # 单据编号
        obj_recpay_org_id = parent['pay_org_id']    # 收付组织
        obj_biz_date = parent['biz_date']  # 业务日期
        obj_state = parent['state']  # 单据状态
        obj_currency_id = parent['sett_curr_id']  # 币别
        obj_local_currency_id = parent['local_curr_id']  # 本位币
        obj_sett_org_id = parent['sett_org_id']  # 结算组织
        obj_source_parent_doc_id = source_parent_model_id  # 来源单据主表id

        

        for line in lines:

            # 由于性能优化，将line的所有字段进行公共提取
            source_sequence = line['sequence']  # 单据行号
            cash_acct_number_id = line['cash_acct_id']  # 现金账号
            income_amount = abs(self._round(line['discount_amount'], obj_currency_id[0]))  # 收入金额
            income_amount_local = abs(self._round(line['discount_amount_local'], obj_local_currency_id[0]))  # 收入金额本位币
            expense_amount = abs(self._round(line['commission'], obj_currency_id[0]))  # 支出金额
            expense_amount_local = abs(self._round(line['commission_local'], obj_local_currency_id[0]))  # 支出金额本位币
            payment_purpose = line['pay_type_id']  # 收付款用途
            sett_number = line['sett_num']  # 结算号
            sett_type_id = line['sett_type_id']  # 结算方式
            summary = line['note']  # 摘要
            is_check = line['is_check']  # 勾对
            source_doc_id = line['id']  # 来源单据明细行id

            if line['sett_type_id'][0] == cash_sett_type_ids[0]:
                # 取明细行数据，结算方式为现金业务的
                # 使用create的批量创建方法，获取汇集数据视图的所有字段
                if expense_amount != 0 or expense_amount_local != 0:
                    # 如果收入金额/收入金额本位币/支出金额/支出金额本位币都为 0 ，则不进行数据创建
                    new_dict = {
                        'source_create_uid': obj_source_create_uid,  # 创建人
                        'number': obj_number,  # 单据编号
                        'recpay_org_id': obj_recpay_org_id,  # 收付组织
                        'biz_date': obj_biz_date,  # 业务日期
                        'state': obj_state,  # 单据状态
                        'currency_id': obj_currency_id,  # 币别
                        'local_currency_id': obj_local_currency_id,  # 本位币
                        'sett_org_id': obj_sett_org_id,  # 结算组织
                        'source_sequence': source_sequence,  # 单据行号
                        'cash_acct_number_id': cash_acct_number_id if cash_acct_number_id else None,  # 现金账号
                        'income_amount': 0,  # 收入金额
                        'expense_amount': expense_amount,  # 支出金额
                        'income_amount_local': 0,  # 收入金额本位币
                        'expense_amount_local': expense_amount_local,  # 支出金额本位币
                        'payment_purpose': payment_purpose if payment_purpose else None,  # 收付款用途
                        'sett_number': sett_number,  # 结算号
                        'sett_type_id': sett_type_id if sett_type_id else None,  # 结算方式
                        'summary': summary if summary else '',  # 摘要
                        'is_check': is_check,  # 勾对
                        'source_model_id': source_model_id,  # 来源单据明细行模型id
                        'source_doc_id': source_doc_id,  # 来源单据明细行id
                        'source_parent_model_id': source_parent_model_id,  # 来源单据主表模型id
                        'source_parent_doc_id': obj_source_parent_doc_id,  # 来源单据主表id
                        'source_parent_model': source_parent_model # 来源单据主表模型
                    }
                    

                    create_list.append(new_dict)

                if income_amount != 0 or income_amount_local != 0:
                    # 如果收入金额/收入金额本位币/支出金额/支出金额本位币都为 0 ，则不进行数据创建
                    new_dict = {
                        'source_create_uid': obj_source_create_uid,  # 创建人
                        'number': obj_number,  # 单据编号
                        'recpay_org_id': obj_recpay_org_id,  # 收付组织
                        'biz_date': obj_biz_date,  # 业务日期
                        'state': obj_state,  # 单据状态
                        'currency_id': obj_currency_id,  # 币别
                        'local_currency_id': obj_local_currency_id,  # 本位币
                        'sett_org_id': obj_sett_org_id,  # 结算组织
                        'source_sequence': source_sequence,  # 单据行号
                        'cash_acct_number_id': cash_acct_number_id if cash_acct_number_id else None,  # 现金账号
                        'income_amount': income_amount,  # 收入金额
                        'expense_amount': 0,  # 支出金额
                        'income_amount_local': income_amount_local,  # 收入金额本位币
                        'expense_amount_local': 0,  # 支出金额本位币
                        'payment_purpose': payment_purpose if payment_purpose else None,  # 收付款用途
                        'sett_number': sett_number,  # 结算号
                        'sett_type_id': sett_type_id if sett_type_id else None,  # 结算方式
                        'summary': summary if summary else '',  # 摘要
                        'is_check': is_check,  # 勾对
                        'source_model_id': source_model_id,  # 来源单据明细行模型id
                        'source_doc_id': source_doc_id,  # 来源单据明细行id
                        'source_parent_model_id': source_parent_model_id,  # 来源单据主表模型id
                        'source_parent_doc_id': obj_source_parent_doc_id,  # 来源单据主表id
                        'source_parent_model': source_parent_model # 来源单据主表模型
                    }
                    

                    create_list.append(new_dict)
        return create_list
    def _create_data_type_manual_journal_s(self, parent, lines, source_model_id, source_parent_model_id, source_parent_model):
        """
        @desc: 创建现金手工日记账相关数据到后台表中
        @params: self: 实列
        @params: obj: 各个单据的明细行数据对象
        @params: source_model_id: 来源单据明细行模型id
        @params: source_parent_model_id: 来源单据主表模型id
        @return: 返回一个list，包含所有需要创建的记录的字典集合。
        """
        create_list = list()

        # 优化性能，将主表obj对象对应字段，提出到for循环外，提高性能
        obj_source_create_uid = parent['create_uid']   # 创建人
        obj_number = parent['number']  # 单据编号
        obj_recpay_org_id = parent['payrecv_org_id']  # 收付组织
        obj_biz_date = parent['biz_date']  # 业务日期
        obj_state = parent['state']  # 单据状态
        obj_currency_id = parent['currency_id']  # 币别
        obj_local_currency_id = parent['local_currency_id']   # 本位币
        obj_source_parent_doc_id = source_parent_model_id  # 来源单据主表id

    

        for line in lines:

            # 由于性能优化，将line的所有字段进行公共提取
            source_sequence = line['sequence']  # 单据行号
            cash_acct_number_id = line['cash_acct_number_id']  # 现金账号
            income_amount = self._round(line['debit'], obj_currency_id[0])  # 收入金额
            income_amount_local = self._round(line['debit_local'], obj_local_currency_id[0])  # 收入金额本位币
            expense_amount = self._round(line['credit'], obj_currency_id[0])  # 支出金额
            expense_amount_local = self._round(line['credit_local'], obj_local_currency_id[0])  # 支出金额本位币
            sett_number = line['sett_num']  # 结算号
            sett_type_id = line['sett_type_id']  # 结算方式
            summary = line['summary']  # 摘要
            is_check = line['is_check']  # 勾对
            source_doc_id = line['id']  # 来源单据明细行id

            # 使用create的批量创建方法，获取汇集数据视图的所有字段
            if income_amount != 0 or income_amount_local != 0:
                # 如果收入金额/收入金额本位币/支出金额/支出金额本位币都为 0 ，则不进行数据创建
                new_dict = {
                    'source_create_uid': obj_source_create_uid,  # 创建人
                    'number': obj_number,  # 单据编号
                    'recpay_org_id': obj_recpay_org_id,  # 收付组织
                    'biz_date': obj_biz_date,  # 业务日期
                    'state': obj_state,  # 单据状态
                    'currency_id': obj_currency_id,  # 币别
                    'local_currency_id': obj_local_currency_id,  # 本位币
                    'sett_org_id': None,  # 结算组织
                    'source_sequence': source_sequence,  # 单据行号
                    'cash_acct_number_id': cash_acct_number_id if cash_acct_number_id else None,  # 现金账号
                    'income_amount': income_amount,  # 收入金额
                    'expense_amount': 0,  # 支出金额
                    'income_amount_local': income_amount_local,  # 收入金额本位币
                    'expense_amount_local': 0,  # 支出金额本位币
                    'payment_purpose': None,  # 收付款用途
                    'sett_number': sett_number,  # 结算号
                    'sett_type_id': sett_type_id,  # 结算方式
                    'summary': summary if summary else '',  # 摘要
                    'is_check': is_check,  # 勾对
                    'source_model_id': source_model_id,  # 来源单据明细行模型id
                    'source_doc_id': source_doc_id,  # 来源单据明细行id
                    'source_parent_model_id': source_parent_model_id,  # 来源单据主表模型id
                    'source_parent_doc_id': obj_source_parent_doc_id,  # 来源单据主表id
                    'source_parent_model': source_parent_model # 来源单据主表模型
                }
                

                create_list.append(new_dict)

            if expense_amount != 0 or expense_amount_local != 0:
                # 如果收入金额/收入金额本位币/支出金额/支出金额本位币都为 0 ，则不进行数据创建
                new_dict = {
                    'source_create_uid': obj_source_create_uid,  # 创建人
                    'number': obj_number,  # 单据编号
                    'recpay_org_id': obj_recpay_org_id,  # 收付组织
                    'biz_date': obj_biz_date,  # 业务日期
                    'state': obj_state,  # 单据状态
                    'currency_id': obj_currency_id,  # 币别
                    'local_currency_id': obj_local_currency_id,  # 本位币
                    'sett_org_id': None,  # 结算组织
                    'source_sequence': source_sequence,  # 单据行号
                    'cash_acct_number_id': cash_acct_number_id if cash_acct_number_id else None,  # 现金账号
                    'income_amount': 0,  # 收入金额
                    'expense_amount': expense_amount,  # 支出金额
                    'income_amount_local': 0,  # 收入金额本位币
                    'expense_amount_local': expense_amount_local,  # 支出金额本位币
                    'payment_purpose': None,  # 收付款用途
                    'sett_number': sett_number,  # 结算号
                    'sett_type_id': sett_type_id,  # 结算方式
                    'summary': summary if summary else '',  # 摘要
                    'is_check': is_check,  # 勾对
                    'source_model_id': source_model_id,  # 来源单据明细行模型id
                    'source_doc_id': source_doc_id,  # 来源单据明细行id
                    'source_parent_model_id': source_parent_model_id,  # 来源单据主表模型id
                    'source_parent_doc_id': obj_source_parent_doc_id,  # 来源单据主表id
                    'source_parent_model': source_parent_model # 来源单据主表模型
                }
                

                create_list.append(new_dict)
        return create_list
    ################################  私有方法区  end   ################################


    ################################  公共方法区  start  ################################

    def p_set_data(self, source_model, obj_list, flag=False):
        """
        @desc: 根据各个单据审核成功后，需要向现金收支表中插入后台数据
        @params: self: 实列
        @params: source_model: 来源单据明细行模型名
        @params: obj_list: 各类单据的明细行本次审核的所有数据对象
        @return: None
        """
        if source_model not in SOURCE_MODEL_LIST:
            return
        source_model_id = self._get_model_id(source_model)

        create_list = list()
        if source_model == 'cm.cash.recycling.line':
            # 现金存取单
            source_parent_model = 'cm.cash.recycling'
            source_parent_model_id = self._get_model_id(source_parent_model)

            for obj in obj_list:
                document_type = obj.document_type
                if document_type == 'cash_deposit':
                    # 现金存款单
                    create_list.extend(self._create_data_type_cash_deposit(obj, source_model_id, source_parent_model_id, flag))
                if document_type == 'cash_withdrawals':
                    # 现金取款单
                    create_list.extend(self._create_data_type_cash_withdrawals(obj, source_model_id, source_parent_model_id, flag))
                
        if source_model in ['cm.transfer.order', 'cm.foreign.exchange']:
            # 转账购汇单
            source_parent_model = 'cm.transfer.settle'
            source_parent_model_id = self._get_model_id(source_parent_model)

            for obj in obj_list:
                document_type = obj.document_type
                if document_type == 'cash_transfer':
                    # 现金转账单
                    create_list.extend(self._create_data_type_cash_transfer(obj, source_model_id, source_parent_model_id, flag))
                if document_type == 'foreign_cash':
                    # 现金购汇单
                    create_list.extend(self._create_data_type_foreign_cash(obj, source_model_id, source_parent_model_id, flag))
        
        if source_model == 'cm.receivable.bill.line1.sale': 
            # 收款单
            source_parent_model = 'cm.receivable.bill'
            source_parent_model_id = self._get_model_id(source_parent_model)
            for obj in obj_list:
                biz_type = obj.biz_type
                if biz_type == 'receive':
                    # 销售业务收款单/其他业务收款单
                    create_list.extend(self._create_data_type_sale_receive(obj, source_model_id, source_parent_model_id, flag))

        if source_model == 'cm.receivable.refund.bill.line1.sale': 
            # 收款退款单
            source_parent_model = 'cm.receivable.refund.bill'
            source_parent_model_id = self._get_model_id(source_parent_model)
            for obj in obj_list:
                biz_type = obj.biz_type
                if biz_type == 'refund':
                    # 销售业务收款退款单/其他业务收款退款单
                    create_list.extend(self._create_data_type_sale_refund(obj, source_model_id, source_parent_model_id, flag))

        if source_model == 'cm.payable.bill.line1':
            # 付款单
            source_parent_model = 'cm.payable.bill'
            source_parent_model_id = self._get_model_id(source_parent_model)
            for obj in obj_list:
                biz_type = obj.biz_type
                if biz_type == 'payable':
                    # 采购业务付款单/其他业务付款单
                    create_list.extend(self._create_data_type_purchase_receive(obj, source_model_id, source_parent_model_id, flag))
                
        if source_model == 'cm.payable.refund.bill.line1':
            # 付款退款单
            source_parent_model = 'cm.payable.refund.bill'
            source_parent_model_id = self._get_model_id(source_parent_model)
            for obj in obj_list:
                biz_type = obj.biz_type
                if biz_type == 'refund':
                    # 采购业务付款退款单/其他业务付款退款单
                    create_list.extend(self._create_data_type_purchase_refund(obj, source_model_id, source_parent_model_id, flag))

        if source_model == 'cm.manual.journal.line1':
            # 现金手工日记账
            source_parent_model = 'cm.manual.journal'
            source_parent_model_id = self._get_model_id(source_parent_model)

            for obj in obj_list:
                # 现金手工日记账
                create_list.extend(self._create_data_type_manual_journal(obj, source_model_id, source_parent_model_id, flag))
            
        if not flag:
            # self.create(create_list)
            # 由于性能问题，改用sql进行数据创建
            if create_list:
                self.env['ps.sql'].p_sql_create('cm_cash_income_expense', create_list)
            return

        return create_list

    def p_delete_data(self, source_model, line_ids):
        """
        @desc: 根据各个单据反审核成功后，需要删除掉现金收支表中相关数据
        @params: self: 实列
        @params: source_model: 来源单据模型
        @params: line_ids: 各个单据的明细行数据id列表
        @return: None
        """
        if line_ids:
            source_model_id = self._get_model_id(source_model)
            self.search([('source_model_id', '=', source_model_id), ('source_doc_id', 'in', line_ids)]).unlink()

    def p_set_data_second(self, source_model, docs, flag=False):
        """
        @desc: 根据各个单据审核成功后，需要向现金收支表中插入后台数据
        @params: self: 实列
        @params: source_model: 来源单据明细行模型名
        @params: docs: 各类单据的明细行本次审核的所有数据对象
        @return: None
        """
        if source_model not in SOURCE_MODEL_LIST:
            return
        source_model_id = self._get_model_id(source_model)

        create_list = list()
        doc_ids = [doc.id for doc in docs]
        if source_model == 'cm.cash.recycling.line':
            # 现金存取单
            source_parent_model = 'cm.cash.recycling'
            source_parent_model_id = self._get_model_id(source_parent_model)
            recycling_data = docs.read( 
                fields=['tenant_id', 'number', 'create_uid', 'recv_org_id', 'biz_date', 'local_currency_id', 'state', 'document_type'])
            lines_dict = self._get_line_dict(
                doc_ids=doc_ids, 
                model=source_model,
                fields=['currency_id', 'sequence', 'cash_acct_number', 'pay_amount', 'pay_amount_lc', 'sett_number', 'abstract', 'is_check', 'parent_id']
                )
            
            for parent in recycling_data:
                lines = lines_dict[parent['id']]
                create_list.extend(self._create_data_type_cash_recycling_s(parent, lines, source_model_id, source_parent_model_id, source_parent_model))   
        elif source_model == 'cm.receivable.bill.line1.sale': 
            # 收款单
            source_parent_model = 'cm.receivable.bill'
            source_parent_model_id = self._get_model_id(source_parent_model)
            receivable_bill_data = docs.read( 
                fields=['tenant_id', 'number', 'create_uid', 'recv_org_id', 'biz_date', 'currency_id', 'local_curr_id', 'state', 'sett_org_id', 'contact_dept', 'biz_type'])
            lines_dict = self._get_line_dict(
                doc_ids=doc_ids, 
                model=source_model,
                fields=['sett_type_id', 'sequence', 'cash_acct_id', 'discount_amount', 'discount_amount_local', 
                    'commission', 'commission_local', 'biz_type_id', 'sett_number', 'note', 'is_check', 'parent_id']
                )
            cash_sett_type_ids = self.env['mdm.settle.type'].with_context(disable_state_filter=True).search([('buss_type', '=', 'cash')]).ids

            for parent in receivable_bill_data:
                lines = lines_dict[parent['id']]
                biz_type = parent['biz_type']
                if biz_type == 'receive':
                    # 销售业务收款单/其他业务收款单
                    create_list.extend(self._create_data_type_sale_receive_s(parent, lines, source_model_id, source_parent_model_id, source_parent_model, cash_sett_type_ids))
        
        elif source_model in ['cm.transfer.order', 'cm.foreign.exchange']:
            # 转账购汇单
            source_parent_model = 'cm.transfer.settle'
            source_parent_model_id = self._get_model_id(source_parent_model)

            parent_data = docs.read( 
                fields=['tenant_id', 'number', 'create_uid', 'col_org_id', 'biz_date', 'local_curr_id', 'state', 'document_type'])


            if source_model == 'cm.transfer.order':
                transfer_dict = self._get_line_dict(
                    doc_ids=doc_ids, 
                    model=source_model,
                    fields=['currency_id', 'charge', 'charge_lc', 'sequence', 'cash_out_account_id', 'in_amount', 'in_amount_lc', 'cash_in_account_id', 'out_amount', 'out_amount_lc', 'out_no', 'in_no', 
                        'abstract', 'is_out_check', 'is_in_check','parent_id']
                    )
                for parent in parent_data:
                    document_type = parent['document_type']
                    transfer_lines = transfer_dict[parent['id']]
                    if document_type == 'cash_transfer':
                    # 现金转账单
                        create_list.extend(self._create_data_type_cash_transfer_s(parent, transfer_lines, source_model_id, source_parent_model_id, source_parent_model))
            else:
                foreign_dict = self._get_line_dict(
                doc_ids=doc_ids, 
                model=source_model,
                # fields=['out_currency_id', 'in_currency_id', 'sequence', 'cash_out_account_id', 'cash_in_account_id', 'out_amount', 'out_amount_lc', 
                #     'in_amount', 'in_amount_lc', 'out_no', 'in_no', 'abstract', 'is_out_check', 'is_in_check', 'parent_id']
                fields=['out_currency_id', 'in_currency_id', 'sequence', 'charge', 'charge_lc', 'cash_out_account_id', 'cash_in_account_id', 'out_amount', 'out_amount_lc', 
                    'in_amount', 'in_amount_lc', 'out_no', 'in_no', 'abstract', 'is_out_check', 'is_in_check', 'parent_id']
                )

                for parent in parent_data:
                    document_type = parent['document_type']
                    foreign_lines = foreign_dict[parent['id']]
                    if document_type == 'foreign_cash':
                        # 现金购汇单
                        create_list.extend(self._create_data_type_foreign_cash_s(parent, foreign_lines, source_model_id, source_parent_model_id, source_parent_model))
        
        elif source_model == 'cm.receivable.refund.bill.line1.sale': 
            # 收款退款单
            source_parent_model = 'cm.receivable.refund.bill'
            source_parent_model_id = self._get_model_id(source_parent_model)
            refund_bill_data = docs.read( 
                fields=['number', 'create_uid', 'recv_org_id', 'biz_date', 'currency_id', 'sett_org_id', 'local_curr_id', 'state', 'biz_type'])
            lines_dict = self._get_line_dict(
                doc_ids=doc_ids, 
                model=source_model,
                fields=['sett_type_id', 'sequence', 'cash_acct_id', 'discount_amount', 'discount_amount_local', 
                    'commission', 'commission_local', 'biz_type_id', 'sett_number', 'note', 'is_check', 'parent_id']
                )
            cash_sett_type_ids = self.env['mdm.settle.type'].with_context(disable_state_filter=True).search([('buss_type', '=', 'cash')]).ids
            

            for parent in refund_bill_data:
                lines = lines_dict[parent['id']]
                biz_type = parent['biz_type']
                if biz_type == 'refund':
                    # 销售业务收款退款单/其他业务收款退款单
                    create_list.extend(self._create_data_type_sale_refund_s(parent, lines, source_model_id, source_parent_model_id, source_parent_model, cash_sett_type_ids))
       
        elif source_model == 'cm.payable.bill.line1':
            # 付款单
            source_parent_model = 'cm.payable.bill'
            source_parent_model_id = self._get_model_id(source_parent_model)
            payable_bill_data = docs.read( 
                fields=['tenant_id', 'number', 'create_uid', 'pay_org_id', 'biz_date', 'sett_curr_id', 'local_curr_id', 'state', 'sett_org_id', 'contact_dept', 'biz_type'])
            lines_dict = self._get_line_dict(
                doc_ids=doc_ids, 
                model=source_model,
                fields=['sett_type_id', 'sequence', 'cash_acct_id', 'discount_amount', 'discount_amount_local', 
                    'commission', 'commission_local', 'note', 'is_check', 'parent_id','pay_type_id']
                )
            cash_sett_type_ids = self.env['mdm.settle.type'].with_context(disable_state_filter=True).search([('buss_type', '=', 'cash')]).ids

            for parent in payable_bill_data:
                lines = lines_dict[parent['id']]
                biz_type = parent['biz_type']
                if biz_type == 'payable':
                    # 付款单
                    create_list.extend(self._create_data_type_purchase_receive_s(parent, lines, source_model_id, source_parent_model_id, source_parent_model, cash_sett_type_ids))

        elif source_model == 'cm.payable.refund.bill.line1':##################################
            # 付款退款单
            source_parent_model = 'cm.payable.refund.bill'
            source_parent_model_id = self._get_model_id(source_parent_model)
            refund_bill_data = docs.read( 
                fields=[ 'number', 'create_uid', 'pay_org_id', 'biz_date', 'sett_curr_id', 'local_curr_id', 'state', 'sett_org_id', 'biz_type'])
            lines_dict = self._get_line_dict(
                doc_ids=doc_ids, 
                model=source_model,
                fields=['sett_type_id', 'sequence', 'cash_acct_id', 'discount_amount', 'discount_amount_local', 
                    'commission', 'commission_local', 'pay_type_id', 'sett_num', 'note', 'is_check', 'parent_id']
                )
            cash_sett_type_ids = self.env['mdm.settle.type'].with_context(disable_state_filter=True).search([('buss_type', '=', 'cash')]).ids

            for parent in refund_bill_data:
                lines = lines_dict[parent['id']]
                biz_type = parent['biz_type']
                if biz_type == 'refund':
                    # 采购业务付款退款单/其他业务付款退款单
                    create_list.extend(self._create_data_type_purchase_refund_s(parent, lines, source_model_id, source_parent_model_id, source_parent_model, cash_sett_type_ids))

        elif source_model == 'cm.manual.journal.line1':
            # 现金手工日记账
            source_parent_model = 'cm.manual.journal'
            source_parent_model_id = self._get_model_id(source_parent_model)
            journal_data = docs.read( 
                fields=['number', 'create_uid', 'payrecv_org_id', 'biz_date', 'currency_id', 'local_currency_id', 'state', 'source_doc'])
            lines_dict = self._get_line_dict(
                doc_ids=doc_ids, 
                model=source_model,
                fields=['sett_type_id', 'sequence', 'cash_acct_number_id', 'debit', 'debit_local', 'credit', 'credit_local',  
                    'sett_num', 'summary', 'is_check', 'parent_id']
                )

            for parent in journal_data:
                lines = lines_dict[parent['id']]
    
                if parent['source_doc'] == 'manual':
                # 现金手工日记账
                    create_list.extend(self._create_data_type_manual_journal_s(parent, lines, source_model_id, source_parent_model_id, source_parent_model))

        return create_list
    ################################  公共方法区  end   ################################


    ################################  覆盖基类方法区  start  ################################

    ################################  覆盖基类方法区  end   ################################


    ################################  其他方法区  start  ################################

    ################################  其他方法区  end   ################################


def p_get_unaudit_data(self, start_date, end_date):
    """
    @desc: 根据各个单据审核成功后，需要向现金收支表中插入后台数据
    @params: self: 实列
    @params: source_model: 来源单据明细行模型名
    @params: docs: 各类单据的明细行本次审核的所有数据对象
    @return: None
    """
    domain = [
        ('state', 'in', ['save', 'submit']),
        ('delete_state', '=', 'normal'),
        ('biz_date', '>=', start_date),
        ('biz_date', '<=', end_date)
        ]
    bank_sett_type_ids = self.env['mdm.settle.type'].with_context(disable_state_filter=True).search([('buss_type', '=', 'bank')]).ids
    result = []
    for parent_model, child_model, parent_domain in DOC_MODELS:
    records = self.env[parent_model].search(domain + parent_domain)
    func_name = '_get_%s_data' % self.env[child_model]._table
    source_parent_model_id = self._get_model_id(parent_model)
    if hasattr(self, func_name):
    if func_name in ['_get_cm_receivable_bill_line1_sale_data',
    '_get_cm_receivable_refund_bill_line1_sale_data',
    '_get_cm_payable_bill_line1_data',
    '_get_cm_payable_refund_bill_line1_data',
    '_get_cm_manual_journal_line1_data']:
    # 收款单，付款单，收款退款单，付款退款单，结算方式必填
    result.extend(getattr(self, func_name)(records, parent_model, child_model, source_parent_model_id, bank_sett_type_ids))
    else:
    result.extend(getattr(self, func_name)(records, parent_model, child_model, source_parent_model_id))

    return result
