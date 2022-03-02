# -*- coding: utf-8 -*-
'''
==================================================
@创建人: 杨兴财
@当前维护人: 杨兴财
@Desc: Expense Record Doc
==================================================
'''
import re
from datetime import datetime, date

from odoo import models, fields, api, _
from odoo.tools import float_compare
from odoo.exceptions import ValidationError
from odoo.addons.ps_studio.models.studio_service_config import transform_result



START_INDEX = 1
MIN_AMOUNT = 0
MIN_TAX_RATE = 0 # 默认汇率为0，最小值
MAX_TAX_RATE = 100 # 最大汇率值
TAX_RATE_PERCISION = 2 # 汇率精度 

class ErExpense(models.Model):
    _inherit = 'er.expense'

    ################################  default start  ################################

    def _default_settle_type_id(self):
        """
        结算方式默认值
        """
        settle_type_obj = self.env['mdm.settle.type']
        return settle_type_obj.search([('is_default', '=', True)], limit=1).id

    ################################  default end    ################################


    ################################  字段定义区 start  ################################
    
    req_amount_total = fields.Float(compute='_compute_amount_total')
    req_amount_total_lc = fields.Float(compute='_compute_amount_total')
    aprv_amount_total = fields.Float(compute='_compute_amount_total')
    aprv_amount_total_lc = fields.Float(compute='_compute_amount_total')
    unpush_pay_amount_total = fields.Float(compute='_compute_amount_total')
    input_vat_inv_domains = fields.Many2many(compute='_compute_input_vat_inv_domains')

    ################################  字段定义区 end    ################################


    ################################  计算方法区 start  ################################
    
    @api.depends('line1_expense_ids')
    def _compute_amount_total(self):
        """
        计算表头的合计金额
        """
        for rec in self:
            req_amount_total = 0
            req_amount_total_lc = 0
            aprv_amount_total = 0
            aprv_amount_total_lc = 0
            unpush_pay_amount_total = 0

            currency_id = rec.currency_id.id
            local_currency_id = rec.local_currency_id.id
            for line in rec.line1_expense_ids:
                req_amount_total = self._round(req_amount_total + line.req_amount, currency_id)
                req_amount_total_lc = self._round(req_amount_total_lc + line.req_amount_lc, local_currency_id)
                aprv_amount_total = self._round(aprv_amount_total + line.aprv_amount, currency_id)
                aprv_amount_total_lc = self._round(aprv_amount_total_lc + line.aprv_amount_lc, local_currency_id)
                unpush_pay_amount_total = self._round(unpush_pay_amount_total + line.unpush_pay_amount, currency_id)

            rec.req_amount_total = req_amount_total
            rec.req_amount_total_lc = req_amount_total_lc
            rec.aprv_amount_total = aprv_amount_total
            rec.aprv_amount_total_lc = aprv_amount_total_lc
            rec.unpush_pay_amount_total = unpush_pay_amount_total  

    @api.depends('exp_org_id', 'currency_id', 'project_id')
    def _compute_input_vat_inv_domains(self):
        """
        根据费用承担组织、币别、项目,计算进项增值税发票的过滤
        """
        input_vat_inv_obj = self.env['iv.input.vat.inv']
        for rec in self:
            domain = [
                ('sett_org_id', '=', rec.exp_org_id.id),
                ('currency_id', '=', rec.currency_id.id)
            ]
            if rec.project_id:
                domain.append(('project_id', '=', rec.project_id.id))
            rec.input_vat_inv_domains = input_vat_inv_obj.search(domain).ids

    ################################  计算方法区 end    ################################


    ################################  onchange方法区  start  ################################

    def _onchange_guests_num(self):
        """
        招待人数校验
        """
        if self.guests_num and self.guests_num <= 0:
            # 招待人数不能小于0
            raise ValidationError(_('The number of guests shall be more than 0')) 
    
    def _onchange_meeting_days(self):
        """
        会议天数校验
        """
        if self.meeting_days and self.meeting_days <= 0:
            # 会议天数不能小于0
            raise ValidationError(_('The number of meeting days shall be more than 0')) 

    def _onchange_line1_expense_ids(self):
        """
        明细行变更，更新sequence
        """
        for index, line in enumerate(self.line1_expense_ids, START_INDEX):
            line.sequence = index

    def _onchange_line1_collection_ids(self):
        """
        明细行变更，更新sequence
        """
        for index, line in enumerate(self.line1_collection_ids, START_INDEX):
            line.sequence = index

    def _onchange_settle_type_id(self):
        """
        更新收款信息
        """
        is_bank = self.settle_type_id.buss_type == 'bank'
        # 结算方式的业务类型从银行类切换成现金业务类时，收款信息（银行、账户名称、银行账号）的值清空
        # 从现金类切换成银行业务类时，重新自动携带默认值
        for collection_line in self.line1_collection_ids:
            collection_line._update_fin_data(is_bank)

    def _onchange_project_id(self):
        """
        项目变更时，更新明细信息中的核算状态
        """
        project_id = self.project_id
        for line in self.line1_expense_ids:
            exp_date = line.exp_date
            line.accting_state = line._get_accting_state(project_id, exp_date)

    def _onchange_pay_org_id(self):
        """
        付款组织变更，清空收款明细行中的收款单位
        暂时无法实现清空
        """
        for line in self.line1_collection_ids:
            line.collected_dept = None

    ################################  onchange方法区  end    ################################


    ################################  约束方法区  start  ################################
    
    def _check_exp_date(self, *args, **kwargs):
        """
        校验明细信息中费用日期是否超出项目日期范围
        """
        records = kwargs.get('record_ids', [])
        for rec in records:
            project_id = rec.project_id
            if project_id:
                for line in rec.line1_expense_ids:
                    if not line._is_valid_exp_date(project_id, line.exp_date): # or not line.accting_state:
                        # 费用日期已超出所选项目的时间范围，请检查
                        raise ValidationError(_('The expense date is out of the selected project time range, please check'))

    def _check_amount_and_tax(self, *args, **kwargs):
        """
        校验明细信息中的金额的合法性
        """
        records = kwargs.get('record_ids', [])
        for rec in records:
            if rec.meeting_days and rec.meeting_days <= 0:
                # 会议天数不能小于0
                raise ValidationError(_('The number of meeting days shall be more than 0'))
            if rec.guests_num and rec.guests_num <= 0:
                # 招待人数不能小于0
                raise ValidationError(_('The number of guests shall be more than 0'))
            currency_id = rec.currency_id.id
            for line in rec.line1_expense_ids:
                exp_amount = line.exp_amount
                if float_compare(exp_amount, MIN_AMOUNT, currency_id) != 1:
                    # 行%s, 费用金额不能小于0
                    raise ValidationError(_('Line %s, the amount of expense shall not be less than 0') % line.sequence)
                req_amount = line.req_amount
                if float_compare(req_amount, MIN_AMOUNT, currency_id) != 1:
                    # 行%s, 申请金额不能小于0
                    raise ValidationError(_('Line %s, the amount of requested shall not be less than 0') % line.sequence)
                tax_rate = line.tax_rate
                if float_compare(tax_rate, MIN_TAX_RATE, TAX_RATE_PERCISION) == -1 or float_compare(tax_rate, MAX_TAX_RATE, TAX_RATE_PERCISION) == 1:
                    # 税率必须介于0~100
                    raise ValidationError(_('The tax rate must be between 0~100'))
                tax = line.tax
                if float_compare(tax, MIN_AMOUNT, currency_id) == -1:
                    # 税额不能小于0
                    raise ValidationError(_('The amount of tax shall not be less than 0'))

                aprv_amount = line.aprv_amount
                if float_compare(aprv_amount, tax, currency_id) == -1:
                    # 行%s，核定报销金额不能小于税额
                    raise ValidationError(_('Line %s, the approved reimbursement amount cannot be less than the tax amount') % line.sequence)
                if float_compare(aprv_amount, req_amount, currency_id) == 1:
                    # 行%s，核定报销金额不能大于申请报销金额
                    raise ValidationError(_('Line %s, The approved reimbursement amount cannot be greater than the applied reimbursement amount') % line.sequence)
                
                # 如果发票类型为增值税专用发票或增值税普通发票，申请报销金额不能超过发票可报销金额
                if line.inv_type_type in ('vat_invoice', 'vat_general_invoice') \
                    and self._float_compare(line.req_amount, line.inv_id.invoice_balance, currency_id) == 1:
                    # 行%s，申请报销金额已超过发票可报销金额，请检查是否有其他报销单已关联了此发票
                    raise ValidationError(_('Line %s, the request amount has exceeded the reimbursable amount of the invoice, please check whether other reimbursement documents have been associated with this invoice') % line.sequence)
                if tax and not tax_rate:
                    # 税额不为0时，税率不允许为0
                    raise ValidationError(_('When the tax amount is not 0, the tax rate is not allowed to be 0'))

                
            collected_amount_total = 0
            for line2 in rec.line1_collection_ids:
                collected_amount = line2.collected_amount
                collected_amount_total += collected_amount
                if float_compare(collected_amount, MIN_AMOUNT, currency_id) == -1:
                    # 收款金额不能小于0
                    raise ValidationError(_('The amount of collected shall not be less than 0'))
            aprv_amount_total = rec.aprv_amount_total
            if float_compare(collected_amount_total, aprv_amount_total, currency_id) != 0:
                # 收款金额合计不等于核定报销金额合计，请检查
                raise ValidationError(_('The total amount collected is not equal to the total amount of approved reimbursement, please check'))

    def _check_document_control(self, *args, **kwargs):
        """
        校验单据控制(事前申请控制、报销标准管控)
        """
        records = kwargs.get('record_ids', [])
        for rec in records:
            # 事前申请控制：如果需要事前申请，则此单据一定要是下推来的
            # 如果不是下推的单据，则报错提示；否则，一定是申请单下推来的，即事前申请的
            if rec.is_request_ctrl and not rec.is_convert:
                # 此单据未关联费用申请单，保存失败
                raise ValidationError(_('This document is not associated with the expense request document, saving failed'))
            
    ################################  约束方法区  end    ################################


    ################################  服务器动作区  start  ################################
    
    ################################  服务器动作区  end    ################################


    ################################  按钮动作区  start  ################################

    def hook_after_save_update_inv_balance(self, *args, **kwargs):
        """
        保存后更新费用明细信息中引用发票的余额
        """
        source_model_name = self._name
        model_obj = self.env['ir.model']
        model_id_id = model_obj.search([('model', '=', source_model_name)], limit=1).id

        invs_data = []
        records = kwargs.get('record_ids', [])
        for record in records:
            currency_id_id = record.currency_id.id
            # 按照费用明细行引用的发票组装数据
            ref_inv_data = {}
            for line in record.line1_expense_ids:
                inv_id = line.inv_id
                if inv_id:
                    # 将申请报销金额作为发票占用金额
                    if inv_id not in ref_inv_data:
                        ref_inv_data[inv_id] = {
                            'doc_inv_record': inv_id,
                            'doc_occupy_inv_amount': line.req_amount
                        }
                    else:
                        doc_occupy_inv_amount = ref_inv_data[inv_id]['doc_occupy_inv_amount']
                        ref_inv_data[inv_id]['doc_occupy_inv_amount'] = self._round(doc_occupy_inv_amount + line.req_amount, currency_id_id)
            
            invs_data.append({
                'source_id': record.id,  # 业务单据表头记录id
                'source_model_name': source_model_name,  # 业务单据表头模型
                'source_model_id': model_id_id,  # 业务单据表头模型id
                'src_doc_type_id': record.document_type_id.id,  # 单据类型
                'document_number': record.number,  # 业务单据表头单据编号
                'biz_date': record.apply_date,  # 业务日期
                'ref_inv_data': ref_inv_data
            })
        # 通知更新发票占用金额
        self._event("on_listener_biz_doc_ref_invoice").notify(data_dict_list=invs_data)
    
    def hook_after_delete_update_inv_balance(self, *args, **kwargs):
        """
        删除后减掉费用明细信息中引用发票的余额
        """
        source_model_name = self._name
        model_obj = self.env['ir.model']
        model_id_id = model_obj.search([('model', '=', source_model_name)], limit=1).id

        invs_data = []
        records = kwargs.get('record_ids', [])
        for record in records:
            invs_data.append({
                'source_id': record.id,  # 业务单据表头记录id
                'source_model_name': source_model_name,  # 业务单据表头模型
                'source_model_id': model_id_id,  # 业务单据表头模型id
                'src_doc_type_id': record.document_type_id.id,  # 单据类型
                'document_number': record.number,  # 业务单据表头单据编号
                'biz_date': record.apply_date,  # 业务日期
                'ref_inv_data': {}
            })
        # 通知更新发票占用金额
        self._event("on_listener_biz_doc_ref_invoice").notify(data_dict_list=invs_data)

    def hock_push_ap_other_payable(self, records):
        '''
        费用报销单审核后自动生成其他应付单
        '''
        # pass

        # records = kwargs.get('record_ids', None)
        sett_org_id = self.push_get_sett_org_id(records)
        current_date = self.hook_push_current_date()
        biz_date = self.push_get_biz_date(records)
        document_type_id = self.env.ref('ps_ap.ap_other_expense_reimbursement_other_document_type_data').id
        tax_total = self.push_get_tax_total(records)
        lines = []
        for line in records.line1_expense_ids:
            line_data = (0, 0, {
                'amount': line.exp_amount,
                'amount_abs': line.exp_amount,
                'applied_amount': 0,
                'applied_amount_lc': 0,
                'create_date': current_date,
                'exp_bear_dept_id': line.exp_dept_id.id,
                'exp_item_id': line.exp_item_id.id,
                'inv_type_id': line.inv_type_id.id,
                # # '核算类型': line.inv_type,
                # '发票代码': line.inv_type,
                # '发票号码': line.inv_type,
                # '非增值税票号': line.inv_type,
                # '已申报': line.inv_type,
                # '申报日期': line.inv_type,
                'participation_cost_sharing': False,
                'sett_amount': 0,
                'sett_apply_amount': 0,
                'source_id': line.parent_id.id,
                'source_line1_id': line.id,
                'source_line1_model': 'er.expense.line1.expense',
                'source_model': 'er.expense',
                'source_number': line.parent_id.number,
                'sequence': line.sequence,
                'tax': line.tax,
                })
            lines.append(line_data)
        other_payable_obj = self.env['ap.other.payable']
        for record in records:
            
            target_doc = other_payable_obj.create({
                'apply_dept_id': record.apply_dept_id.id,
                'audit_date': current_date,
                'biz_date': biz_date,
                'contact_dept': str(record.contact_dept._name) + ',' + str(record.contact_dept.master_id),
                'curr_rate': record.curr_rate,
                'currency_id': record.currency_id.id,

                'document_type': 'other_payable', #
                'document_type_id': document_type_id,
                'due_date': biz_date,
                'include_tax_to_cos': False,
                'is_convert': True,
                'is_curr_rate_modify': False,
                'is_init_document': False,
                'is_red': False,
                'local_currency_id': record.local_currency_id.id,
                'pay_org_id': record.pay_org_id.id,
                'resale_state': 0,
                'sett_lc_total': 0,
                'sett_org_id': sett_org_id,
                'sett_type_id': record.settle_type_id.id,
                'source_doc_ids': record.id,
                'source_model_key': 'er.expense',
                'state': 'audit',
                'tax_total': tax_total,
                'project_id': record.project_id.id,
                'project_number': record.project_num,
                'line_ids': lines,
            })
            link_obj = self.env['studio.botp.record']
            # 创建link表数据
            link_obj.create({
                'source_model_key': 'er.expense',
                'source_doc_id': record.id,
                'source_doc_num': record.number,
                'target_model_key': 'ap.other.payable',
                'target_doc_id': target_doc.id,
                'target_doc_num': target_doc.number,
                'record_type': 'audit_auto_generate'
            })
    '''
    def hook_after_audit_cancel(self, *args, **kwargs):
        """
        反审核，满足以下条件可进行反审核：
        1. 未下推生成费用报销付款单（已在studio.base中实现）
        2. 费用报销其他应付单没有生成凭证
        """
        link_obj = self.env['studio.botp.record']
        other_payable_obj = self.env['ap.other.payable']

        records = kwargs.get('record_ids', [])
        for record in records:
            link = link_obj.search([
                ('source_model_key', '=', self._name),
                ('source_doc_id', '=', record.id),
                ('target_model_key', '=', 'ap.other.payable'),
                ('record_type', '=', 'audit_auto_generate'),
                ('delete_state', '=', False)
            ], limit=1)
            # 如果自动生成了其他应付单，则判断该其他应付单是否生成了凭证
            if link:
                other_payable_id = link.target_doc_id
                acct_center_link = link_obj.search([
                    ('source_model_key', '=', 'ap.other.payable'),
                    ('source_doc_id', '=', other_payable_id),
                    ('target_model_key', '=', 'gl.voucher'),
                    ('record_type', '=', 'acct_center'),
                    ('delete_state', '=', False)
                ], limit=1)
                # 如果已生成凭证则不允许反审核，否则，删除其他应付单和link表数据
                if acct_center_link:
                    # 当前单据对应的其他应付单已生成凭证，不允许反审核
                    raise ValidationError(_('Voucher has been generated for other account payable corresponding to the current document. The current document cannot be approved cancel'))
                else:
                    other_payable = other_payable_obj.browse(other_payable_id)
                    other_payable.write({
                        'state': 'save',
                        'audit_uid': None,
                        'audit_date': None,
                        'delete_state': 'delete',
                        'delete_uid': self.env.uid,
                        'delete_date': fields.Date.today()
                    })
                    link.write({
                        'delete_state': True
                    })
        '''
    ################################  按钮动作区  end    ################################


    ################################  私有方法区  start  ################################

    def _update_amount_local(self):
        """
        更新金额的本位币
        """
        curr_rate = self.curr_rate
        local_currency_id = self.local_currency_id.id
        aprv_amount_total_lc = 0
        req_amount_total_lc = 0
        for line1 in self.line1_expense_ids:
        # TODO:后续添加下推金额核销金额等本位币的计算
            line1.exp_amount_lc = self._round(line1.exp_amount * curr_rate, local_currency_id)
            line1.tax_lc = self._round(line1.tax * curr_rate, local_currency_id)
            line1.aprv_amount_lc = self._round(line1.aprv_amount * curr_rate, local_currency_id)
            line1.req_amount_lc = self._round(line1.req_amount * curr_rate, local_currency_id)

            aprv_amount_total_lc = self._round(aprv_amount_total_lc + line1.aprv_amount_lc, local_currency_id)
            req_amount_total_lc = self._round(req_amount_total_lc + line1.req_amount_lc, local_currency_id)
        
        self.aprv_amount_total_lc = aprv_amount_total_lc
        self.req_amount_total_lc = req_amount_total_lc

    ################################  私有方法区  end    ################################


    ################################  公共方法区  start  ################################
    
    ################################  公共方法区  end    ################################


    ################################  覆盖基类方法区  start  ################################
    
    ################################  覆盖基类方法区  end    ################################


    ################################  其他方法区  start  ################################

    def hook_push_apply_date(self, **kw):
        """
        @desc: 下推 目标单据申请日期 自定义方法
        @param: target_model: 目标单据模型名称
        @return: 当前系统日期
        """
        if kw.get('target_model', None) in ['cm.payment.requisition', 'cm.payment.requisition.line1']:
            return fields.Date.today()

    def hook_push_current_date(self, **kw):
        """
        @desc: 下推 当前日期 自定义方法
        @return: 当前系统日期
        """
        return fields.Date.today()

    def hook_push_apply_org_id(self, **kw):
        """
        @desc: 下推 目标单据申请组织 自定义方法
        @param: target_model: 目标单据模型名称
        @return: 若当前登录组织具有需求领域则以当前登录组织作为申请组织，若当前登录组织没有需求领域或没有审核，则无法下推生成付款申请单
             需求领域的校验已在过滤数据钩子中校验通过
        """
        if kw.get('target_model', None) == 'cm.payment.requisition':
            return self.env.user.ps_curr_org_id.id # 当前登录组织

    def comput_sett_curr_rate(self, source_doc_header=None, source_doc_line=None, target_model=None, target_field_name=None, **kw):
        """
        计算目标单据结算汇率
        @param source_doc_header: 来源单据表头数据对象
        @param source_doc_line: 来源单据表体数据对象
        @param target_model: 目标单据模型名称
        @param target_field_name: 目标单据字段名称
        @return 结算汇率值
        """
        # 其他业务付款单/其他业务付款退款单/其他业务付款申请单
        if source_doc_header and target_model in ('er.expense', 'cm.payment.requisition'): 
            org_obj = self.env['sys.admin.orgs'] # 组织结构
            sett_curr_id = source_doc_header.currency_id.id

            if target_model == 'cm.payment.requisition': # 根据“结算组织”的本位币、结算币别和“申请日期”获取对应汇率；
                org_id = source_doc_header.exp_org_id.id
                biz_date = fields.Date.today()

            result = org_obj.p_get_org_all_curr(org_id=org_id, currency_id=sett_curr_id, biz_date=biz_date) or {}
            return  result.get('curr_rate', 0)

    def hook_filter_recv_dept(self, **kw):
        """
        @desc: 下推 目标单据收款单位 自定义方法
        @param: target_model: 目标单据模型名称
        @return: 表体收款单位
        """
        if kw.get('target_model', None) == 'cm.payment.requisition': 
            line = kw.get('source_doc_line', None)
            dept = line.collected_dept._name + ',' + str(line.collected_dept.id)
            return dept

    def hook_push_pay_type_id(self, **kw):
        """
        @desc: 下推 目标单据明细行付款用途 自定义方法
        @param target_model: 目标单据模型名称
        @return 
            基础资料收付款用途：其他支出
        """
        if kw.get('target_model', None) == 'cm.payment.requisition.line1':
            # 默认SFKYT015实报实付，不可修改
            reimbursement = self.env.ref('ps_mdm.mdm_payment_purpose_data_SFKYT015', None)
            return reimbursement.id if reimbursement else None

    def hook_filter_source_data_info(self, source_docs=None, push_doc=None):
        """
        @desc: 单据下推过滤数据钩子函数，过滤来源单据列表，过滤条件不满足返回提示信息  
        @param: source_docs: 源单记录集(list)
        @param: push_doc: 下推单据模型名(str)
        @return: 满足下推条件的单据列表(list)
             不满足下推条件的提示信息(dict)
        """
        # 不满足下推条件的过滤数据提示信息 格式: {source_num: notice}
        filter_num_notice_dict = {}
        # 满足下推条件的单据
        new_source_docs = []

        for source_doc in source_docs: # 多条来源单据
            record = source_doc.get('er.expense', []) # 一条主表单据记录
            if record:
                if push_doc == 'cm.payment.requisition': 
                    curr_org_id = self.env.user.ps_curr_org_id # 当前登录组织
                    if not curr_org_id.p_judge_org_fun_domain(curr_org_id.id, "demand"):
                        # 当前登录组织不具有需求领域，无法下推形成付款申请单
                        filter_num_notice_dict[record.number] = _('The current login organization does not have a requirement domain, payment requisition cannot be generated')
                    else:
                        new_source_docs.append(source_doc)

        return new_source_docs, filter_num_notice_dict


    def listen_bill_target_doc_check(self, *args, **kwargs):
        '''
        付款申请单保存反写原单据可下推金额
        '''
        after_cancel_reverse_data = kwargs.get('after_cancel_reverse_data',{})
        apply_pay_amount = after_cancel_reverse_data.apply_pay_amount
        source_doc_ids = after_cancel_reverse_data.source_doc_ids
        record = self.browse(int(source_doc_ids))
        currency_id = record.currency_id.id
        for line in record.line1_expense_ids:
            unpush_pay_amount = line.unpush_pay_amount
            if unpush_pay_amount and apply_pay_amount:
                if float_compare(unpush_pay_amount, apply_pay_amount, currency_id) < 0:
                    line.push_pay_amount = unpush_pay_amount
                    apply_pay_amount = self._round(apply_pay_amount - unpush_pay_amount, currency_id)
                    line.unpush_pay_amount = 0
                    
                else:
                    line.unpush_pay_amount = self._round(unpush_pay_amount - apply_pay_amount, currency_id)
                    line.push_pay_amount = self._round(apply_pay_amount + line.push_pay_amount, currency_id)
                    apply_pay_amount = 0

    def listen_bill_target_doc_check_detele(self, *args, **kwargs):
        '''
        付款申请单删除反写原单据可下推金额
        '''
        after_cancel_reverse_data = kwargs.get('after_cancel_reverse_data',{})
        apply_pay_amount = after_cancel_reverse_data.apply_pay_amount
        source_doc_ids = after_cancel_reverse_data.source_doc_ids
        record = self.browse(int(source_doc_ids))
        currency_id = record.currency_id.id
        for line in record.line1_expense_ids:
            push_pay_amount = line.push_pay_amount
            if push_pay_amount and apply_pay_amount:
                if float_compare(push_pay_amount, apply_pay_amount, currency_id) < 0:
                    line.unpush_pay_amount = push_pay_amount
                    apply_pay_amount = self._round(apply_pay_amount - push_pay_amount, currency_id)
                    line.push_pay_amount = 0
                    
                else:
                    line.push_pay_amount = self._round(push_pay_amount - apply_pay_amount, currency_id)
                    line.unpush_pay_amount = self._round(apply_pay_amount + line.unpush_pay_amount, currency_id)
                    apply_pay_amount = 0

#################################################################################################

    def push_get_sett_org_id(self, records):

        exp_org_id = records.exp_org_id.id
        date_dict = self.env['ap.other.payable']._get_sett_date(exp_org_id)
        activation_date = date_dict.get('AR_AP_ACTIVATION_DATE', None)
        if not activation_date:
            # 应付领域未启用
            raise ValidationError(_('The total amount collected is not equal'))
        else:
            return exp_org_id



    def push_get_biz_date(self, records):
        """
        应付单下推获取默认业务日期：
            1、当源单的审核日期早于其他应付单费用承担组织的当前期间的开始日期时，则取其他应付单当期开始日期作为单据业务日期；
            2、当源单的审核日期大于等于其他应付单费用承担组织的当前期间的开始日期时，则取源单审核日期作为单据的业务日期；
        """
        # source_doc = kwargs.get('source_doc_header')
        # target_model = kwargs.get('target_model')
        source_doc = records
        target_model = 'ap.other.payable'
        if target_model == 'ap.other.payable':
            date_dict = self.env['ap.other.payable']._get_sett_date(source_doc.exp_org_id.id)
            activation_date = date_dict.get('AR_AP_ACTIVATION_DATE', None)
            curr_start_date = date_dict.get('AR_AP_CURR_START_DATE', None)
        if not curr_start_date:
            curr_start_date = activation_date


        audit_date = source_doc.audit_date.date()
        if audit_date < curr_start_date:
            biz_date = curr_start_date
        else:
            biz_date = audit_date
        return biz_date

    def push_get_tax_total(self, records):
        """
        应付单下推获取税额合计
        """
        source_doc_line = records.line1_expense_ids
        target_model = 'ap.other.payable'
        tax = 0
        currency_id = records.currency_id.id
        if target_model == 'ap.other.payable':
            for rec in source_doc_line:
                tax = self._round(tax + rec.tax, currency_id)
        return tax

    def _hook_auto_push_down_after_aduit(self, **kwargs):
        """
        @desc: 费用报销单审核自动下推其他应付单
        @params: self: 对象
        @return: 下推提示信息
        """
        record = kwargs.get('record_ids', None)
        self.hock_push_ap_other_payable(record)
        pass
    #     source_order_line_id_list = list()  
    #     source_line_dict = dict()
    #     lines_info = []
    #     operation = _('Push Down Info: %s') % self.number
    #     record = kwargs.get('record_ids', None)



    #     # 审核时自动下推
    #     context = dict(self.env.context,
    #             source_doc_ids=[record.id],
    #             origin_source_dict=record.line1_expense_ids,
    #             source_model='er.expense',
    #             ignore_launch_condition=True,
    #             botp_type='from_er_expense',
    #         )
    #     self.env = self.env(context=context)
    #     rules = self.env['studio.botp.rule'].search([
    #         ('source_model_key', '=', 'er.expense'),
    #         ('target_model_key', '=', 'ap.other.payable'),
    #         ('rule_key', '=', 'HgjQXK'),
    #     ])
    #     # try:
    #     if rules:
    #         # 下推失败不要影响审核流程
    #         with self.env.cr.savepoint():
    #             doc_type = self.env.ref('ps_stk.stk_pro_pick_document_type_data2') # TODO:更换为费用报销
    #             for rule in rules:
    #                 return_info = self.env['studio.botp.wizard'].create({
    #                     'source_doc': 'er.expense',
    #                     'target_doc': rule.target_model_key,
    #                     'rule_key': rule.rule_key,
    #                     # 'doc_type': doc_type.number,
    #                 }).studio_button_confirm_push(is_manual=True)
    #                 validate_result = transform_result(return_info)
    #                 if validate_result:
    #                     if 'notify_dialog' in validate_result:
    #                         successful_info = validate_result['notify_dialog']['result']['successful']
    #                         if successful_info:
    #                             for item in successful_info:
    #                                 lines_info.append({'info': item['content'][2], 'operation': operation, 'pass_after_service': False, 'status': 'success'})
    #                     elif validate_result.get('info') != '单据下推成功':
    #                         lines_info.append(validate_result)
    #     # except Exception:
    #     #     return lines_info
    #     return lines_info

    ################################  其他方法区  end    ################################
    