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
READ_ID_INDEX = 0 # many2one类型字段read结果中ID的索引
ENTER_TYPE_DICT = {
            # 召开会议:1.召开董事会会议2.召开营销推介类会3.召开经营分析类会议4.召开专项研发类会议5.召开党务类会议6.召开其他类会议
            'Hold Meeting': ['SYS_EXP_000121', 'SYS_EXP_000122', 'SYS_EXP_000123', 'SYS_EXP_000124', 'SYS_EXP_000125', 'SYS_EXP_000126'],
            # 公务接待:1.接待国内公务来访人员
            'Official reception': ['SYS_EXP_000131'],
            # 车辆使用: 1.公务出行用车
            'Vehicle use': ['SYS_EXP_000141'],
            # 年检及团体会费: 年检及团体会费
            'Annual inspection and group membership fees': ['SYS_EXP_000151'],
            # 业务营销招待 1.接待客户或业务合作伙伴2.接待来访外宾支出
            'Business marketing entertainment': ['SYS_EXP_000211', 'SYS_EXP_000212'],
            # 购买营销用品 1.购买业务营销用品 2.制作业务宣传用品 3.购买招标所需用品
            'Buy marketing supplies': ['SYS_EXP_000221', 'SYS_EXP_000222', 'SYS_EXP_000223'],
            # 其他营销活动 1.其他业务营销支出
            'Other marketing activities': ['SYS_EXP_000231'],
            # 员工招聘 1.新员工招聘支出
            'Staff recruitment': ['SYS_EXP_000311'],
            # 员工培训 员工教育培训支出
            'Staff training': ['SYS_EXP_000321'],
            # 党建活动 1.购买党建活动物品2.开展党员培训3.租赁、修缮党组织活动场所4.表彰、补助党员
            'Party building activities': ['SYS_EXP_000411', 'SYS_EXP_000412', 'SYS_EXP_000413', 'SYS_EXP_000414'],
            # 零星购置各种物品 1.办公机具或用品2.电子设备配件或耗材3.日常办公资料印刷4.订购报刊杂志资料5.消防器材或设施6.短期租赁房屋或设备7.短期租赁其他软硬件
            'Used for business management': ['SYS_EXP_000511', 'SYS_EXP_000512', 'SYS_EXP_000513', 'SYS_EXP_000514', 'SYS_EXP_000515', 'SYS_EXP_000516', 'SYS_EXP_000517'],
            # 用于项目研发 1.采购研发材料2.租赁研发设备
            'For project research and development': ['SYS_EXP_000521', 'SYS_EXP_000522'],
            # 用于员工个人 1.职工培训教材用具2.员工工装及劳保用品3.购买员工福利用品
            'For employees': ['SYS_EXP_000531', 'SYS_EXP_000532', 'SYS_EXP_000533'],
            # 用于员工集体 1.购置集体生活福利设施2.组织全体员工体检3.购买用于员工医品4.员工工装及劳保用品
            'For the employee collective': ['SYS_EXP_000541', 'SYS_EXP_000542', 'SYS_EXP_000543', 'SYS_EXP_000532'],
            # 为经营管理服务 1.办公场所日常保障服务2.软件或设备升级维保服务3.零星装修维修服务4.保险服务5.法律事务服务6.会计或审计咨询服务7.业务咨询评估服务8.广告宣传服务9.外包服务
            'Serve for business management': ['SYS_EXP_000611', 'SYS_EXP_000612', 'SYS_EXP_000613', 'SYS_EXP_000614', 'SYS_EXP_000615', 'SYS_EXP_000616', 'SYS_EXP_000617', 'SYS_EXP_000618', 'SYS_EXP_000619'],
            # 为项目研发服务  1.项目研发外协服务2.项目研发设计服务3.项目研发造价服务4.项目研发评审
            'Serve for project research and development': ['SYS_EXP_000621', 'SYS_EXP_000622', 'SYS_EXP_000623', 'SYS_EXP_000624'],
            # 为员工集体服务  1.自设食堂服务人员费用2.自设理发室服务人员费用3.其他集体福利服务费用
            'Serving employees collectively': ['SYS_EXP_000631', 'SYS_EXP_000632', 'SYS_EXP_000633'],
            # 缴纳税金或行政费1.缴纳税金2.缴纳残疾人就业保障金
            'Pay taxes or administrative fees': ['SYS_EXP_000711', 'SYS_EXP_000712'],
            # 营业外支出事项 1.公益性捐赠支2.监管检查罚款3.资产处置损失4.资产盘亏损失
            'Non-operating expenses': ['SYS_EXP_000721', 'SYS_EXP_000722', 'SYS_EXP_000723', 'SYS_EXP_000724'],
            # 员工探亲 1.员工探亲
            'Employees visit relatives': ['SYS_EXP_000731']

        }


class ErExpense(models.Model):
    _inherit = 'er.expense'

    ################################  default start  ################################

    def _default_settle_type_id(self):
        """
        结算方式默认值
        """
        settle_type_obj = self.env['mdm.settle.type']
        return settle_type_obj.search([('is_default', '=', True)], limit=1).id

    def _default_document_type_id(self):
        '''
        农银金科专用
        获取默认单据类型
        '''
        num_list = self._context.get('type_num', None)
        if num_list:
            default_num = num_list[0]
            doc_type_obj = self.env['mdm.document.type']
            doc_type_id = doc_type_obj.search([('number', '=', default_num)])
            return doc_type_id
        else:
            return None


    def _domain_doc_type(self):
        '''
        农银金科专用
        多单据入口下获取对应单据类型
        '''
        num_list = self._context.get('type_num', None)        
        if num_list:
            return [('number', 'in', num_list)]

        else:
            return [('model_name', '=', self._name)]

    ################################  default end    ################################


    ################################  字段定义区 start  ################################

    # 单据类型 农银金科专用
    document_type_id = fields.Many2one(domain=lambda self: self._domain_doc_type(), default=lambda self: self._default_document_type_id())
    # 申请报销金额
    req_amount_total = fields.Float(compute='_compute_amount_total')
    req_amount_total_lc = fields.Float(compute='_compute_amount_total')
    # 核定报销金额
    aprv_amount_total = fields.Float(compute='_compute_amount_total')
    aprv_amount_total_lc = fields.Float(compute='_compute_amount_total')
    # 冲借款金额合计
    offset_loan_amount_total = fields.Float(compute='_compute_amount_total')
    offset_loan_amount_total_lc = fields.Float(compute='_compute_amount_total')
    # 已付款金额合计
    pay_amount_total = fields.Float(compute='_compute_amount_total')
    pay_amount_total_lc = fields.Float(compute='_compute_amount_total')
    # 已下推付款金额合计
    push_amount_total = fields.Float(compute='_compute_amount_total')
    push_amount_total_lc = fields.Float(compute='_compute_amount_total')
    # 报销未付款金额合计
    unpay_amount_total = fields.Float(compute='_compute_amount_total')
    unpay_amount_total_lc = fields.Float(compute='_compute_amount_total')
    # 可下推付款金额合计
    unpush_amount_total = fields.Float(compute='_compute_amount_total')
    unpush_amount_total_lc = fields.Float(compute='_compute_amount_total')
    # 已核销金额
    recon_amount_total = fields.Float(compute='_compute_amount_total')
    recon_amount_total_lc = fields.Float(compute='_compute_amount_total')
    # 未核销金额
    unrecon_amount_total = fields.Float(compute='_compute_amount_total')
    unrecon_amount_total_lc = fields.Float(compute='_compute_amount_total')

    input_vat_inv_domains = fields.Many2many(compute='_compute_input_vat_inv_domains')

    ################################  字段定义区 end    ################################


    ################################  计算方法区 start  ################################
    
    @api.depends('line1_expense_ids', 'line1_expense_ids.push_amount', 'line1_expense_ids.offset_loan_amount', 'line1_expense_ids.pay_amount')
    def _compute_amount_total(self):
        """
        计算表头的合计金额
        """
        for rec in self:
            req_amount_total = 0
            req_amount_total_lc = 0
            aprv_amount_total = 0
            aprv_amount_total_lc = 0

            #  下推所用金额字段
            offset_loan_amount_total = 0
            offset_loan_amount_total_lc = 0
            pay_amount_total = 0
            pay_amount_total_lc = 0
            push_amount_total = 0
            push_amount_total_lc = 0
            unpay_amount_total = 0
            unpay_amount_total_lc = 0
            unpush_amount_total = 0
            unpush_amount_total_lc = 0
            recon_amount_total = 0
            recon_amount_total_lc = 0
            unrecon_amount_total = 0
            unrecon_amount_total_lc = 0

            currency_id = rec.currency_id.id
            local_currency_id = rec.local_currency_id.id
            for line in rec.line1_expense_ids:
                req_amount_total = self._round(req_amount_total + line.req_amount, currency_id)
                req_amount_total_lc = self._round(req_amount_total_lc + line.req_amount_lc, local_currency_id)
                aprv_amount_total = self._round(aprv_amount_total + line.aprv_amount, currency_id)
                aprv_amount_total_lc = self._round(aprv_amount_total_lc + line.aprv_amount_lc, local_currency_id)
                offset_loan_amount_total = self._round(offset_loan_amount_total + line.offset_loan_amount, currency_id)
                offset_loan_amount_total_lc = self._round(offset_loan_amount_total_lc + line.offset_loan_amount_lc, local_currency_id)
                pay_amount_total = self._round(pay_amount_total + line.pay_amount, currency_id)
                pay_amount_total_lc = self._round(pay_amount_total_lc + line.pay_amount_lc, local_currency_id)
                push_amount_total = self._round(push_amount_total + line.push_amount, currency_id)
                push_amount_total_lc = self._round(push_amount_total_lc + line.push_amount_lc, local_currency_id)
                unpay_amount_total = self._round(unpay_amount_total + line.unpay_amount, currency_id)
                unpay_amount_total_lc = self._round(unpay_amount_total_lc + line.unpay_amount_lc, local_currency_id)
                unpush_amount_total = self._round(unpush_amount_total + line.unpush_amount, currency_id)
                unpush_amount_total_lc = self._round(unpush_amount_total_lc + line.unpush_amount_lc, local_currency_id)
                recon_amount_total = self._round(recon_amount_total + line.recon_amount, currency_id)
                recon_amount_total_lc = self._round(recon_amount_total_lc + line.recon_amount_lc, local_currency_id)
                unrecon_amount_total = self._round(unrecon_amount_total + line.unrecon_amount, currency_id)
                unrecon_amount_total_lc = self._round(unrecon_amount_total_lc + line.unrecon_amount_lc, local_currency_id)
  

            rec.req_amount_total = req_amount_total
            rec.req_amount_total_lc = req_amount_total_lc
            rec.aprv_amount_total = aprv_amount_total
            rec.aprv_amount_total_lc = aprv_amount_total_lc
            rec.unpush_amount_total = unpush_amount_total  

            rec.offset_loan_amount_total = offset_loan_amount_total
            rec.offset_loan_amount_total_lc = offset_loan_amount_total_lc
            rec.pay_amount_total = pay_amount_total
            rec.pay_amount_total_lc = pay_amount_total_lc
            rec.push_amount_total = push_amount_total
            rec.push_amount_total_lc = push_amount_total_lc
            rec.unpay_amount_total = unpay_amount_total
            rec.unpay_amount_total_lc = unpay_amount_total_lc
            rec.unpush_amount_total_lc = unpush_amount_total_lc
            rec.recon_amount_total = recon_amount_total
            rec.recon_amount_total_lc = recon_amount_total_lc
            rec.unrecon_amount_total = unrecon_amount_total
            rec.unrecon_amount_total_lc = unrecon_amount_total_lc

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
                    if not line._is_valid_exp_date(project_id, line.exp_date) or not line.accting_state:
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
            is_convert = rec.is_convert  # 是否下推单据
            src_line_amount_dict = {}  # 来源单据明细金额字典
            for line in rec.line1_expense_ids:
                exp_amount = line.exp_amount
                if float_compare(exp_amount, MIN_AMOUNT, currency_id) != 1:
                    # 行%s, 不含税金额不能小于0
                    raise ValidationError(_('Line %s, the amount of expense shall not be less than 0') % line.sequence)
                req_amount = line.req_amount
                if float_compare(req_amount, MIN_AMOUNT, currency_id) != 1:
                    # 行%s, 申请金额不能小于0
                    raise ValidationError(_('Line %s, the amount of requested shall not be less than 0') % line.sequence)
                aprv_amount = line.aprv_amount
                if float_compare(aprv_amount, MIN_AMOUNT, currency_id) != 1:
                    # 行%s, 核定报销金额不能小于0
                    raise ValidationError(_('Line %s, the amount of approved shall not be less than 0') % line.sequence)
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
                if not line.inv_id and tax and not tax_rate:
                    # 税额不为0时，税率不允许为0
                    raise ValidationError(_('When the tax amount is not 0, the tax rate is not allowed to be 0'))

                # 下推单据，则计算原单下推金额
                if is_convert and line.source_line1_id and line.source_line1_model:
                    src_line_obj = self.env[line.source_line1_model]
                    src_line = src_line_obj.browse(line.source_line1_id)
                    # 按照来源单明细进行汇总（行拆分可能会出现多行对同一行来源单明细）
                    src_line_amount = src_line_amount_dict.get(src_line, MIN_AMOUNT)
                    src_line_amount_dict[src_line] = self._round(src_line_amount + exp_amount, currency_id)

            # 判断是否超过来源单据(费用申请单)的金额
            for src_line, src_line_amount in src_line_amount_dict.items():
                if self._float_compare(src_line_amount, src_line.unpush_reimb_amount, currency_id) == 1:
                    # 本次申请报销金额不能大于来源单据对应行的可下推报销金额
                    raise ValidationError(_('The request reimbursement amount cannot be greater than the pushable reimbursement amount of the corresponding line of the source document'))
  
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
        
    def hook_after_save_clear_src_doc_data(self, *args, **kwargs):
        """
        保存后，清空来源单据数据(复制的单据来源单据数据会有值,下推后又复制的单据)
        """
        records = kwargs.get('record_ids', [])
        for record in records:
            if not record.is_convert:
                lines = record.line1_expense_ids.filtered(lambda line: line.source_number)
                lines.write({
                    'source_number': None,
                    'source_id': None,
                    'source_model': None,
                    'source_line1_id': None,
                    'source_line1_model': None,
                    'src_doc_type_id': None,
                    'src_recon_amount': 0
                })
    
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

    def hook_after_audit_generate_payable_bill(self, *args, **kwargs):        
        """
        @desc: 费用报销单审核自动下推付款单
        @params: self: 对象
        @return: 下推提示信息
        """
        records = kwargs.get('record_ids', None)
        sys_biz_params_obj = self.env['sys.business.params']
        module_obj = self.env['ir.module.module']
        module_id = module_obj.search([('name', '=', 'ps_er')])
        rules_obj = self.env['studio.botp.rule']
        for record in records:
            param_result = sys_biz_params_obj.p_get_params(module_id=module_id.id, org_id=record.apply_org_id.id, key='is_generate_payment_audit')
            if param_result and len(param_result) == 1:
                is_generate_payment_audit = param_result[0].get('value', False)

            if is_generate_payment_audit == 'True':  #参数配置自动生成付款单
                rule = rules_obj.search([
                    ('source_model_key', '=', 'er.expense'),
                    ('target_model_key', '=', 'cm.payable.bill'),
                    ('rule_key', '=', 'Rn0q2U'),
                    ('forbid_state', '=', False),
                    ('delete_state', '=', False)
                ], limit=1)
                if rule:
                    with self.env.cr.savepoint():
                        doc_type = self.env.ref('ps_cm.cm_payable_bill_expense_reim_payment_document_type_data')  # 费用报销付款单
                        botp_wizard_obj = self.env['studio.botp.wizard']
                        return_info = botp_wizard_obj.with_context(
                            source_doc_ids=[record.id],
                            origin_source_dict=record.line1_collection_ids,
                            source_model='er.expense',
                            ignore_launch_condition=True,
                            botp_type='from_er_expense').create({
                            'source_doc': 'er.expense',
                            'target_doc': rule.target_model_key,
                            'rule_key': rule.rule_key,
                            'doc_type': doc_type.number,
                        }).studio_button_confirm_push(is_manual=True)

    def hook_after_audit_generate_other_payable(self, *args, **kwargs):
        '''
        费用报销单审核后自动生成其他应付单
        '''
        records = kwargs.get('record_ids', None)
        other_payable_obj = self.env['ap.other.payable']
        ap_detail_obj = self.env['ap.detail.record']
        # 校验是否有创建其他应付单的权限
        other_payable_obj.pre_create()
        document_type_id = self.env.ref('ps_ap.ap_other_expense_reimbursement_other_document_type_data').id
        for record in records:
            exp_org_id = record.exp_org_id.id
            # 获取应付模块对应组织的当期开始日期
            start_date = other_payable_obj.p_get_curr_start_date(exp_org_id)
            if not start_date:
                # 审核失败，费用承担组织%s未启用应付管理，当前单据无法自动生成其他应付单
                raise ValidationError(
                    _('Failed to approve. The expense bearing organization %s has not enabled account payable management and the current document cannot automatically generate other account payable documents')
                    % record.exp_org_id.name
                )
            lines = []
            for sequence, line in enumerate(record.line1_expense_ids, START_INDEX):
                line_data = (0, 0, {
                    'sequence': sequence,  # 序号
                    'accting_state': line.accting_state,  # 核算状态
                    'allocate_complete': False,  # 分配完成
                    'amount': line.exp_amount,  # 不含税金额
                    'amount_abs': line.exp_amount,  # 不含税金额(显示)
                    'applied_amount': 0,  # 已申请金额
                    'applied_amount_lc': 0,  # 已申请金额本位币
                    'exp_bear_dept_id': line.exp_dept_id.id,  # 费用承担部门
                    'exp_item_id': line.exp_item_id.id,  # 费用项目
                    'number': line.exp_item_id.number,  # 费用项目编号
                    'inv_type_id': line.inv_type_id.id,  # 发票类型
                    'inv_id': line.inv_id.id,  # 发票
                    'non_vat_num': line.non_vat_num,  # 非增值税票号
                    'is_declare': line.is_declare,  # 已申报
                    'declare_date': line.declare_date,  # 申报日期
                    'participation_cost_sharing': False,  # 参与费用分配
                    'sett_amount': 0,  # 已结算金额
                    'sett_apply_amount': 0,  # 已结算申请金额
                    'source_id': record.id,  # 来源单id
                    'source_line1_id': line.id,  # 来源单分录id
                    'source_line1_model': 'er.expense.line1.expense',  # 来源单表体模型key
                    'source_model': 'er.expense',  # 来源单模型key
                    'source_number': record.number,  # 来源单编号
                    'tax': line.tax,  # 税额
                    'tax_abs': line.tax,    # 税额
                    })
                lines.append(line_data)
            # 1、当源单的审核日期早于其他应付单费用承担组织的当前期间的开始日期时，则取其他应付单当期开始日期作为单据业务日期；
            # 2、当源单的审核日期大于等于其他应付单费用承担组织的当前期间的开始日期时，则取源单审核日期作为单据的业务日期；
            biz_date = max(start_date, record.audit_date.date())
            target_doc = other_payable_obj.with_context(pass_authorize_check=True).studio_orm_create({
                'applied_amount': 0,  # 已申请金额
                'applied_amount_lc': 0,  # 已申请金额本位币
                'apply_dept_id': record.exp_dept_id.id,  # 申请部门
                'audit_date': fields.Datetime.now(),  # 审核日期
                'biz_date': biz_date,  # 业务日期
                'contact_dept': record.contact_dept._name + ',' + str(record.contact_dept.id),  # 往来单位
                'curr_rate': record.curr_rate,  # 汇率
                'currency_id': record.currency_id.id,  # 币别
                'document_type': 'other_payable',  # 单据类型：蓝单
                'document_type_id': document_type_id,  # 单据类型
                'due_date': biz_date,  # 到期日期
                'include_tax_to_cos': False,  # 税额计入成本
                'is_convert': True,  # 下推单据
                'is_curr_rate_modify': False,  # 汇率是否可修改
                'is_init_document': False,  # 期初单据
                'is_red': False,  # 是否红单
                'local_currency_id': record.local_currency_id.id,  # 本位币
                'pay_org_id': record.pay_org_id.id,  # 付款组织
                'resale_state': 0,  # 转销状态
                'sett_lc_total': 0,  # 已结算金额合计本位币
                'sett_org_id': exp_org_id,  # 结算组织
                'sett_type_id': record.settle_type_id.id,  # 结算方式
                'source_doc_ids': record.id,  # 来源单id
                'source_model_key': 'er.expense',  # 来源单模型key
                'state': 'audit',  # 状态
                'audit_uid': self.env.uid,   # 审核人
                'source_doc_type_number': record.document_type_id.number, # 单据类型编号
                'note': record.reason,  # 报销事由
                'project_id': record.project_id.id,  # 项目
                'line_ids': lines,  # 明细
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
            # 更新后台余额表: 创建应付款明细表数据
            ap_detail_obj.p_set_data('ap.other.payable', [target_doc])

    def hook_after_audit_cancel(self, *args, **kwargs):
        """
        反审核，满足以下条件可进行反审核：
        1. 未下推生成费用报销付款单（已在studio.base中实现）
        2. 费用报销其他应付单没有生成凭证
        """
        link_obj = self.env['studio.botp.record']
        other_payable_obj = self.env['ap.other.payable']
        ap_detail_obj = self.env['ap.detail.record']
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
                    # 更新后台余额表: 删除应付款明细表数据
                    ap_detail_obj.p_delete_data('ap.other.payable', [other_payable])

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

    @api.model
    def p_check_responsive_popup(self, form_data):
        """
        费用报销单校验报销管控标准的控制
        """
        record = self.new(form_data)
        ctrl_standard_obj = self.env['mdm.reimb.ctrl.standard']
        result = ctrl_standard_obj.p_check_reimb_ctrl_standard(record, record.apply_org_id, record.biz_type_id, record.currency_id, record.apply_date)
        if result.get('errors'):
            return {
                'type': 'error',
                'check_result': True,
                'info': result['errors']
            }
        elif result.get('warnings'):
            return {
                'check_result': True,
                'info': result['warnings']
            }
        else:
            return {
                'check_result': False,
            }

    ################################  公共方法区  end    ################################


    ################################  覆盖基类方法区  start  ################################
    
    ################################  覆盖基类方法区  end    ################################


    ################################  其他方法区  start  ################################
    
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
            if record and push_doc == 'cm.payment.requisition':
                curr_org_id = self.env.user.ps_curr_org_id # 当前登录组织
                if not curr_org_id.p_judge_org_fun_domain(curr_org_id.id, "demand"):
                    # 当前登录组织不具有需求领域，无法下推形成付款申请单
                    filter_num_notice_dict[record.number] = _('The current login organization does not have a requirement domain, payment requisition cannot be generated')
                else:
                    new_source_docs.append(source_doc)

        return new_source_docs, filter_num_notice_dict

    def hook_filter_source_data(self, source_docs=None, push_doc=None):
        """
        下推各单据私有方法
        1、当前用户是否有来源单据下付款组织中创建付款单的权限
        2、判断主组织是否已启用
        :param:
            self: 当前模型记录(obj)
            source_docs: 源单记录集(list)
            push_doc: 下推单据(str)
        :return:
            满足下推条件的单据
        """
        # 满足下推条件的单据
        new_source_docs = []
        # 不满足下推条件的过滤数据提示信息 
        notice_data = {}
        # 获取已启用的组织列表
        period_params_obj = self.env['sys.period.params']
        cm_params_data = period_params_obj.p_get_params(key=['CM_ACTIVATION_DATE'])
        active_org_ids = [param['org_id'][READ_ID_INDEX] for param in cm_params_data if param.get('org_id')]

        # 获取报销单支付时启用付款申请流程的组织列表
        module_obj = self.env['ir.module.module']
        module_id = module_obj.search([('name', '=', 'ps_er')], limit=1)
        biz_params_obj = self.env['sys.business.params']
        er_params_data = biz_params_obj.p_get_params(module_id=module_id.id, key=['is_enable_pay_process_paid'])
        need_req_org_ids = []
        for param in er_params_data:
            if param.get('org_id') and param.get('value', 'False') == 'True':
                need_req_org_ids.append(param['org_id'][READ_ID_INDEX])
        for source_doc in source_docs: # 多条来源单据
            record = source_doc.get('er.expense', []) # 一条主表单据记录
            if record:
                # 判断付款组织是否已启用日期设置
                if record.pay_org_id.id not in active_org_ids:
                    # 付款组织未启用,请检查
                    notice_data[record.number] = _('The payment org is not enable, please check')
                # 判断是否勾选付款申请流程
                elif record.apply_org_id.id in need_req_org_ids:
                    # 系统已启用付款申请流程，不能直接下推付款单
                    notice_data[record.number] = _('The system has activated the payment application process, and the payment slip cannot be directly pushed down')
                else:
                    new_source_docs.append(source_doc)

        return new_source_docs, notice_data
                
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
        return self.env.user.ps_curr_org_id.id # 当前登录组织

    def hook_push_sett_curr_rate(self, source_doc_header=None, source_doc_line=None, target_model=None, target_field_name=None, **kw):
        """
        计算目标单据结算汇率
        @param source_doc_header: 来源单据表头数据对象
        @param source_doc_line: 来源单据表体数据对象
        @param target_model: 目标单据模型名称
        @param target_field_name: 目标单据字段名称
        @return 结算汇率值
        """
        org_obj = self.env['sys.admin.orgs']
        sett_curr_id = source_doc_header.currency_id.id
        if target_model == 'cm.payment.requisition': 
            org_id = source_doc_header.exp_org_id.id
            biz_date = fields.Date.today()

        if target_model == 'cm.payable.bill': # 付款组织、业务日期
            org_id = source_doc_header.pay_org_id.id
            biz_date = self.hook_push_biz_date(source_doc_header=source_doc_header, source_doc_line=source_doc_line, target_model=target_model, target_field_name='biz_date')
        result = org_obj.p_get_org_all_curr(org_id=org_id, currency_id=sett_curr_id, biz_date=biz_date) or {}
        return result.get('curr_rate', 0)

    def hook_push_recv_dept(self, **kw):
        """
        @desc: 下推 目标单据收款单位 自定义方法
        @param: target_model: 目标单据模型名称
        @return: 表体收款单位
        """
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
        # 默认SFKYT015实报实付，不可修改
        reimbursement = self.env.ref('ps_mdm.mdm_payment_purpose_data_SFKYT015', None)
        return reimbursement.id if reimbursement else None

    def hook_push_relate_num(self, **kw):
        """
        下推 付款明细子表关联单据 字段自定义方法
        :param: 
            self: 当前模型记录(obj)
            source_doc_header: 源单表头对象(obj)
            source_doc_line: 源单明细对象(obj)
            target_model: 目标单模型(str)
            target_field_name: 目标单字段名(str)
        :return:
            单据编码-付款计划明细行单据行号
        """
        source_doc_line = kw.get('source_doc_line', None)
        number = kw.get('source_doc_header', None).number
        return '%s-%s' % (number, source_doc_line.sequence) if number and source_doc_line.sequence else None
    
    def hook_push_biz_date(self, **kw):
        """
        下推 目标单据-付款单-业务日期 自定义方法
        :param: 
            self: 当前模型记录(obj)
            source_doc_header: 源单表头对象(obj)
            source_doc_line: 源单明细对象(obj)
            target_model: 目标单模型(str)
            target_field_name: 目标单字段名(str)
        :return:
            若当前系统日期在未结账日期范围内，则取当前系统日期；若当前系统日期小于最小未结账日期，则取最小未结账日期；若当前系统日期大于最大未结账日期，则取最大未结账日期
        """
        source_doc_header = kw.get('source_doc_header', None)
        pay_org_id =source_doc_header.pay_org_id.id
        org_obj = self.env['sys.admin.orgs']
        accting_data = org_obj.p_get_org_accting_policy_all(org_id=pay_org_id)
        cm_common_obj = self.env['cm.function.common']
        # 获取当期开始日期
        curr_start_date = cm_common_obj.p_get_curr_period_start_date(org_id=pay_org_id)

        biz_date = fields.Date.today()
        if isinstance(accting_data, dict) and accting_data.get('calendar_id', None):
            calendar_obj = self.env['mdm.account.calendar']
            calendar_id = calendar_obj.browse(accting_data['calendar_id'])
            biz_date = max(curr_start_date or calendar_id.start_date, biz_date)
            biz_date = min(calendar_id.end_date, biz_date)
        return biz_date   

    def hook_push_bank_acct_id(self, source_doc_header=None, source_doc_line=None, target_model=None, target_field_name=None, **kw):
        """
        计算银行账号：结算方式为银行时，取付款组织的默认银行账号属性为“收支”或“支出”且能核算该单据对应的“结算币别”(或未设置结算币别)
        @param source_doc_header: 来源单据表头数据对象
        @param source_doc_line: 来源单据表体数据对象
        @param target_model: 目标单据模型名称
        @param target_field_name: 目标单据字段名称
        @return 银行账号
        """
        bank_acct_id = None
        if source_doc_header.settle_type_id.buss_type == 'bank':
            bank_acct_obj = self.env['mdm.bank.acct.number']
            bank_acct_id = bank_acct_obj.search([
                ('use_org_id', '=', source_doc_header.pay_org_id.id), 
                ('is_default', '=', True),
                ('acct_number_attr', 'in', ('both', 'expend')),
                '|',
                ('currency_ids', '=', False),
                ('currency_ids', 'in', source_doc_header.currency_id.id),
                ('state', '=', 'audit'), 
                ('forbid_state', '=', 'normal'), 
                ('delete_state', '=', 'normal')
            ], limit=1).id
        return bank_acct_id    

    def hook_push_cash_acct_id(self, source_doc_header=None, source_doc_line=None, target_model=None, target_field_name=None, **kw):
        """
        计算现金账号：结算方式为现金时，取付款组织的默认现金账号
        @param source_doc_header: 来源单据表头数据对象
        @param source_doc_line: 来源单据表体数据对象
        @param target_model: 目标单据模型名称
        @param target_field_name: 目标单据字段名称
        @return 现金账号
        """
        cash_acct_id = None
        if source_doc_header.settle_type_id.buss_type == 'cash':
            cash_acct_obj = self.env['mdm.cash.acct.number']
            cash_acct_id = cash_acct_obj.search([
                ('use_org_id', '=', source_doc_header.pay_org_id.id), 
                ('is_default', '=', True),
                ('state', '=', 'audit'), 
                ('forbid_state', '=', 'normal'), 
                ('delete_state', '=', 'normal')
                ], limit=1).id
        return cash_acct_id     

    ################################  其他方法区  end    ################################
    