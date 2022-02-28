# -*- coding: utf-8 -*-
'''
==================================================
@创建人: 郑兆涵
@当前维护人: 郑兆涵
@Desc: 进项发票明细表
==================================================
'''

import re
import os

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.addons.ps_admin.sys_ele.sys_ele_ctrl import sys_ele_ctrl
from odoo.addons.ps_admin.precision import get_sys_precision
from odoo.addons.ps_query.ps_query_control.models.spreadjs_query import QueryTable, QueryCell, ClickEvent
from odoo.addons.ps_query.ps_query_control.models.spreadjs_query import PrecisionType


# 允许双击的单元格的字体背景色设置
CLICK_STYLE = {
    'foreColor': '#1D8EE8'
}
# 农银金科跳转动作字典
ENTER_TYPE_DICT = {
            'action_business_trip': ['SYS_EXP_000111', 'SYS_EXP_000112', 'SYS_EXP_000113', 'SYS_EXP_000114', 'SYS_EXP_000115', 'SYS_EXP_000116'],
            'action_hold_meeting': ['SYS_EXP_000121', 'SYS_EXP_000122', 'SYS_EXP_000123', 'SYS_EXP_000124', 'SYS_EXP_000125', 'SYS_EXP_000126'],
            'action_official_reception': ['SYS_EXP_000131'],
            'action_vehicle_use': ['SYS_EXP_000141'],
            'action_annual_inspection_and_group_membership_fees': ['SYS_EXP_000151'],

            'action_business_marketing_entertainment': ['SYS_EXP_000211', 'SYS_EXP_000212'],
            'action_buy_marketing_supplies': ['SYS_EXP_000221', 'SYS_EXP_000222', 'SYS_EXP_000223'],
            'action_other_marketing_activities': ['SYS_EXP_000231'],

            'action_staff_recruitment': ['SYS_EXP_000311'],
            'action_staff_training': ['SYS_EXP_000321'],

            'action_party_building_activities': ['SYS_EXP_000411', 'SYS_EXP_000412', 'SYS_EXP_000413', 'SYS_EXP_000414'],

            'action_used_for_business_management': ['SYS_EXP_000511', 'SYS_EXP_000512', 'SYS_EXP_000513', 'SYS_EXP_000514', 'SYS_EXP_000515', 'SYS_EXP_000516', 'SYS_EXP_000517'],
            'action_for_project_research_and_development': ['SYS_EXP_000521', 'SYS_EXP_000522'],
            'action_for_employees': ['SYS_EXP_000531', 'SYS_EXP_000532', 'SYS_EXP_000533'],
            'action_for_the_employee_collective': ['SYS_EXP_000541', 'SYS_EXP_000542', 'SYS_EXP_000543', 'SYS_EXP_000532'],

            'action_serve_for_business_management': ['SYS_EXP_000611', 'SYS_EXP_000612', 'SYS_EXP_000613', 'SYS_EXP_000614', 'SYS_EXP_000615', 'SYS_EXP_000616', 'SYS_EXP_000617', 'SYS_EXP_000618', 'SYS_EXP_000619'],
            'action_serve_for_project_research_and_development': ['SYS_EXP_000621', 'SYS_EXP_000622', 'SYS_EXP_000623', 'SYS_EXP_000624'],
            'action_serving_employees_collectively': ['SYS_EXP_000631', 'SYS_EXP_000632', 'SYS_EXP_000633'],

            'action_pay_taxe_or_administrative_fees': ['SYS_EXP_000711', 'SYS_EXP_000712'],
            'action_non_operating_expenses': ['SYS_EXP_000721', 'SYS_EXP_000722', 'SYS_EXP_000723', 'SYS_EXP_000724'],
            'action_employees_visit_relatives': ['SYS_EXP_000731']
        }


class IvInputInvoiceDetailQuery(models.TransientModel):
    _name = 'iv.input.inv.detail.query'
    _description = 'Input Invoice Detail Query'

    ################################  default start  ################################

    def _get_default_sett_org_id(self):
        """
        获取默认结算组织
        :param:
            self: 当前实例对象
        :return: 
            (int) - 结算组织 id
        """
        return self._get_default_main_org('sett_org_id')

    def _get_default_currency_ids(self):
        """
        获取默认币别（人民币）
        :param:
            self: 当前实例对象
        :return: 
            (int) - 币别（人民币）id
        """
        currency_id = self.env.ref('ps_mdm.mdm_currency_data_zg_0001').id
        return [currency_id]

    ################################  default end    ################################


    ################################  字段定义区 Start   ################################

    # 发票日期从
    inv_start_date = fields.Date(string='Invoice Start Date', default=fields.Date.context_today)
    # 发票日期至
    inv_end_date = fields.Date(string='Invoice End Date', default=fields.Date.context_today)
    # 勾选日期从
    check_start_date = fields.Date(string='Check Start Date')
    # 勾选日期至
    check_end_date = fields.Date(string='Check End Date')
    # 申报日期从
    declare_start_date = fields.Date(string='Declare Start Date')
    # 申报日期至
    declare_end_date = fields.Date(string='Declare End Date')
    # 结算组织
    sett_org_id = fields.Many2one('sys.admin.orgs', string='Settle Organization', default=_get_default_sett_org_id)
    # 结算组织下拉过滤
    sett_org_id_domains = fields.Many2many('sys.admin.orgs', string='Settle Organization Domains', compute='_compute_sett_org_id_domains')
    # 项目名称
    project_ids = fields.Many2many('mdm.project.file', string='Project Name')
    # 往来单位类型
    contact_dept_type = fields.Selection([('supplier', 'Supplier'), ('customer', 'Customer'), ('employee', 'Employee')], string="Contact Department Type", default='supplier')  
    # 供应商
    supplier_ids = fields.Many2many('mdm.supplier', string='Supplier')
    # 客户
    customer_ids = fields.Many2many('mdm.customer', string='Customer')
    # 员工
    employee_ids = fields.Many2many('mdm.employee', string='Employee')
    # 凭证号
    voucher_number = fields.Char(string='Voucher Number')
    # 发票类型
    inv_type_ids = fields.Many2many('mdm.invoice.type', string='Invoice Type')
    # 发票代码
    inv_code = fields.Char(string='Invoice Code')
    # 发票号（非增值税票号）
    inv_number = fields.Char(string='Non VAT Invoice Number')
    # 不含税金额
    amount_total = fields.Float(string='Amount Total')
    # 税额
    tax_total = fields.Float(string='Tax Total')
    # 价税合计
    amount_tax_total = fields.Float(string='Amount Tax Total')
    # 抵扣勾选
    is_deduction = fields.Selection([('t', 'True'), ('f', 'False')], string='Is Deduction')
    # 已申报
    is_declare = fields.Selection([('t', 'True'), ('f', 'False')], string='Is Declare')
    # 是否异常
    is_error = fields.Selection([('t', 'True'), ('f', 'False')], string='Is Error')
    # 按发票明细展示
    is_show_detail = fields.Boolean(string='Show Invoice Detail')
    # 按发票类型汇总
    is_type_total = fields.Boolean(string='Summary by invoice type')
    # 包含未审核单据
    is_include_unaudit_doc = fields.Boolean(string='Is Include Unapproved Doc')
    # 币别
    currency_ids = fields.Many2many('mdm.currency', string='Currency', default=_get_default_currency_ids)

    ################################  字段定义区 end    ################################


    ################################  计算方法区 start  ################################

    @api.depends('sett_org_id')
    def _compute_sett_org_id_domains(self):
        """
        获取主组织下拉过滤domain
        :param:
            self: 当前实例对象
        :return:
        """
        # 提取公共表 obj
        org_obj = self.env['sys.admin.orgs']

        for res in self:
            # 获取用户有查询权限的组织
            authority_org_domain = org_obj.p_get_main_org_domain(res._name, option='read')
            if authority_org_domain:
                authority_org_record = org_obj.search(authority_org_domain)
                authority_org_ids = authority_org_record.ids
                res.sett_org_id_domains = [(6, 0, authority_org_ids)]
            else:
                res.sett_org_id_domains = [(6, 0, [])]

    ################################  计算方法区 end    ################################


    ################################  onchange方法区  start  ################################

    @api.onchange('inv_code')
    def _onchange_inv_code(self):
        """
        发票代码变更时进行校验
            1、当用户录入的发票代码不是10或12位数值时，赋值失败，在失焦时弹出提示：“增值税发票代码仅能为10或12位数值”（The VAT invoice code can only be 10 or 12 digits）
        :param:
            self: 当前模型对象(obj)
        :return:
        """
        # 提取公共变量
        inv_code = self.inv_code

        if inv_code:
            re_match = r'^([0-9]{10}|[0-9]{12})$'
            result = re.match(re_match, inv_code)  # 进行正则匹配
            if not result:
                self.inv_code = None
                return {
                    'warning': {
                        'title': _('Error!'),
                        'message': _('The VAT invoice code can only be 10 or 12 digits'),
                        'type': 'warning',
                        'sticky': False
                    }
                }

    @api.onchange('sett_org_id')
    def _onchange_sett_org_id(self):
        """
        清空项目名称和往来单位
        :param:
            self: 当前模型对象(obj)
        :return:
        """
        self.project_ids = None
        self.supplier_ids = None
        self.customer_ids = None
        self.employee_ids = None
        

    ################################  onchange方法区  end    ################################


    ################################  约束方法区  start  ################################
    
    ################################  约束方法区  end    ################################


    ################################  服务器动作区  start  ################################
    
    ################################  服务器动作区  end    ################################


    ################################  按钮动作区  start  ################################

    ################################  按钮动作区  end    ################################


    ################################  私有方法区  start  ################################

    def _get_translate_info(self, select_key):
        """
        定义code翻译函数
        :param:
            self: 当前实例对象
            select_key: 不同的翻译key
        :return:
            Selection: 返回不同的翻译字典
        """
        if not select_key: return
            
        if select_key == 'State_Selection':
            # 定义单据状态翻译
            Selection = {
                'creating': _('Creating'),
                'save': _('Save'),
                'submit': _('Submit'),
                'audit': _('Audit'),
            }

        return Selection

    def _check_domain_fields(self, domain_fields):
        """
        校验条件字段
        :param:
            self: 当前实例对象
        :return:
        """
        # 提取公共变量
        inv_start_date = domain_fields.get('inv_start_date')  # 发票日期从
        inv_end_date = domain_fields.get('inv_end_date')  # 发票日期至
        check_start_date = domain_fields.get('check_start_date')  # 勾选日期从
        check_end_date = domain_fields.get('check_end_date')  # 勾选日期至
        declare_start_date = domain_fields.get('declare_start_date')  # 申报日期从
        declare_end_date = domain_fields.get('declare_end_date')  # 申报日期至
        voucher_number = domain_fields.get('voucher_number')  # 凭证号
        is_show_detail = domain_fields.get('is_show_detail')  # 按发票明细展示

        # 点击筛选时校验-发票日期从不能晚于发票日期至
        # 当发票日期从大于发票日期至时提示：发票日期从不能晚于发票日期至（The invoice start date cannot be later than the invoice end date）
        if inv_start_date > inv_end_date:
            raise ValidationError(_('The invoice start date cannot be later than the invoice end date'))  # 发票日期从不能晚于发票日期至

        # 点击筛选时校验-勾选日期从不能晚于勾选日期至
        # 当勾选日期从大于勾选日期至时提示：勾选日期从不能晚于勾选日期至（The check start date cannot be later than the check end date）
        if check_start_date and check_end_date:
            if check_start_date > check_end_date:
                raise ValidationError(_('The check start date cannot be later than the check end date'))  # 勾选日期从不能晚于勾选日期至

        # 点击筛选时校验-申报日期从不能晚于申报日期至
        # 当申报日期从大于申报日期至时提示：申报日期从不能晚于申报日期至（The tax declaration start date cannot be later than the tax declaration end date）
        if declare_start_date and declare_end_date:
            if declare_start_date > declare_end_date:
                raise ValidationError(_('The tax declaration start date cannot be later than the tax declaration end date'))  # 申报日期从不能晚于申报日期至

        # 点击筛选时校验-凭证号与按发票明细展示不共存
        # 当凭证号与按发票明细展示共存时提示：按明细发票展示时，无法按凭证号查找数据（When displaying by detailed invoice, data cannot be found by voucher number）
        if is_show_detail and voucher_number:
            raise ValidationError(_('When displaying by detailed invoice, data cannot be found by voucher number'))  # 按明细发票展示时，无法按凭证号查找数据

    def _organization_domain_fields(self, domain_fields):
        """
        domain_fields过滤条件重组织
        :param:
            self: 当前实例对象
            domain_fields: 字段选择过滤条件
        :return:
            (dict): 重新组织好的 domain_fields 数据字典
        """
        # 重新组织过滤条件： currency_ids
        if not domain_fields.get('currency_ids'):
            currency_ids = self._get_default_currency_ids()
            domain_fields['currency_ids'] = currency_ids

        return domain_fields

    def _get_query_cell_title(self, domain_fields):
        """
        组织副表头数据
        :param:
            self: 当前实例对象
            domain_fields: 字段选择过滤条件
        :return:
            (dict): 副表头数据字典
        """
        # 组织表头：结算组织
        sett_org_name = self.env['sys.admin.orgs'].browse(int(domain_fields['sett_org_id'])).name

        # 组织表头：发票日期
        inv_start_date = domain_fields.get('inv_start_date')
        inv_end_date = domain_fields.get('inv_end_date')
        inv_date = str(inv_start_date.replace('-', '') + '-' + inv_end_date.replace('-', '')) 

        # 返回副表头数据字典
        return {
            'sett_org_id': (_('Settle Organization: ')) + sett_org_name,  # 结算组织：
            'inv_date': (_('Invoice Date: ')) + inv_date,  # 发票日期：
        }

    def _deal_with_config_json_file(self, file_suffix):
        """
        处理表头json中英文
            1、处理表头json中英文
            2、处理两套不同的报表展示数据json模板
        :param:
            self: 当前实例对象
            child_ma_joint_by_prod: 区别两套不同的报表展示数据json模板
        :return:
            config_json_file: json文件名
        """
        file_name = self._name.replace('.', '_')
        config_json_file = os.path.join(os.path.dirname(__file__), '%s_%s_%s.json' % (file_name, file_suffix, self.env.context.get('lang', '')))
        if not os.path.exists(config_json_file):
            config_json_file = os.path.join(os.path.dirname(__file__), '%s.json' % file_name)
        return config_json_file

    def _get_default_main_org(self, org_field_name):
        """
        获取主组织默认值
        :param:
            self: 当前模型对象(obj)
            org_field_name: 组织字段名
        :return:
        """
        main_org = self.env['ir.model'].p_get_main_org_fields(self._name)
        if main_org and main_org.name == org_field_name:  #配置表中设置了主组织
            result= self.env['sys.admin.orgs'].p_get_org_domain_and_default_pname(self._name, org_field_name)
            if result.get('default_org_id') in self.env['sys.admin.orgs'].p_get_buss_org_in_major_accting_sys():
                return result.get('default_org_id')

    def _get_is_to_search_biz_doc(self, domain_fields):
        """
        判断是否需要查询除发票外业务单据的数据
        :param:
            self: 当前实例对象
            domain_fields: 字段选择过滤条件
        :return:
            (boolean) - 是/否
        """
        # 提取公共变量
        inv_code = domain_fields.get('inv_code')  # 发票代码
        check_start_date = domain_fields.get('check_start_date')  # 勾选日期从
        check_end_date = domain_fields.get('check_end_date')  # 勾选日期至
        is_deduction = domain_fields.get('is_deduction')  # 抵扣勾选
        is_error = domain_fields.get('is_error')  # 是否异常

        # 如果查询条件有如下控制，则不需要进行业务单据的查询
        if inv_code:
            return False
        if check_start_date:
            return False
        if check_end_date:
            return False
        if is_deduction == 't':
            return False
        if is_error == 't':
            return False
        return True

    def _get_voucher_number(self, source_id, source_model_name):
        """
        获取进项税发票引用发票页签下业务单据的生成凭证的凭证号
        获取差旅费报销单、费用报销单、其他应付单生成凭证的凭证号
        :param:
            self: 当前实例对象
            source_id: 单据id
            source_model_name： 单据模型名
        :return:
            voucher_number: 凭证号
            voucher_id: 凭证id
        """
        # 定义需要返回的凭证号
        voucher_number = None
        voucher_id = None

        if source_id and source_model_name:
            
            # 提取公共表名obj
            source_model_obj = self.env[source_model_name]
            studio_botp_obj = self.env['studio.botp.record']
            gl_voucher_obj = self.env['gl.voucher']

            # 获取引用发票业务单据obj
            source_model_record = source_model_obj.browse(source_id)
            
            # 差旅费报销单、费用报销单需要从下推关系表中找到下推对应的其他应付单，取该其他应付单生成的凭证号
            # 付款单、付款退款单、其他应付单直接获取生成的凭证号即可
            if source_model_name in ['er.travel', 'er.expense']:
                # 根据下推关系表找到差旅费报销单、费用报销单生成的其他应付单记录
                ap_other_ids = self.env['studio.botp.record'].studio_get_botp_record(current_obj=source_model_record, model_key='ap.other.payable', direction='target')
                source_id = ap_other_ids[0] if ap_other_ids and len(ap_other_ids) == 1 else None
            
            if source_id and source_model_name:
                # 从下推关系表中找到业务单据与凭证相关的记录
                studio_botp_record = studio_botp_obj.search([
                    ('source_model_key', '=', source_model_name),
                    ('source_doc_id', '=', source_id),
                    ('target_model_key', '=', 'gl.voucher'),
                    ('delete_state', '=', True)
                ])

                # 根据找到的下推关系记录找到对应的凭证
                if studio_botp_record:
                    gl_voucher_record = gl_voucher_obj.browse(studio_botp_record.target_doc_id)
                    if gl_voucher_record:
                        voucher_number = str(gl_voucher_record.voucher_word_id.name) + '-' + str(gl_voucher_record.number)
                        voucher_id = gl_voucher_record.id

        return voucher_number, voucher_id

    def _get_query_cells(self, domain_fields):
        """
        组织查询数据
        :param:
            self: 当前实例对象
            domain_fields: 字段选择过滤条件
        :return:
            返回调用组织数据到表格中以及双击事件参数
        """
        # 定义并组织数据汇总字典
        # 定义并组织数据汇总字典的key排序列表
        data_dict, data_key_list = self._get_data_dict_key_list(domain_fields)

        # 如果没有记录则返回空数据
        if len(data_dict) <= 0:
            return [], {}, {}

        # 将组织好的数据插入到表格中，并组织双击穿透事件
        return self._organization_query_cells(domain_fields, data_dict, data_key_list)

    def _get_data_dict_key_list(self, domain_fields):
        """
        定义并组织数据汇总字典
        :param:
            self: 当前实例对象
            domain_fields: 字段选择过滤条件
        :return:
            返回组织好的汇总字典
        """
        data_dict = dict()  # 定义数据汇总字典（后续会将查询的数据组织到该字典中）
        data_key_list = list()  # 定义数据汇总key列表（后续将会把key存入，并进行排序处理）

        """
        需要注意
            不管是按照明细还是不按照明细展示，获取发票、业务单据的对应数据集obj方式一样
            不同点在于对数据的整理操作不同
            （1）对于按照明细展示和不按照明细展示，发票的数据组织字典 data_dict不同
            （2）对于按照明细展示和不按照明细展示，业务单据的数据组织字典 data_dict 相同
        """
        # 根据搜索框中的相关数据获取 进项发票模型 相关记录
        inv_records = self._get_inv_records(domain_fields)
        # 组织整理 进项发票模型 创建所需相关数据
        if domain_fields['is_show_detail']:
            data_dict = self._get_inv_detail_data(inv_records, data_dict, domain_fields)
        else:
            data_dict = self._get_inv_doc_data(inv_records, data_dict, domain_fields)

        # 判断是否需要查询除发票外业务单据的数据
        is_to_search_biz_doc = self._get_is_to_search_biz_doc(domain_fields)

        if is_to_search_biz_doc:
            # 这里已将组织整理所需数据字典三个函数抽为一个统一函数，通过调用获取公共变量方法，获取不同表的不同数据，进行相同操作
            # 根据搜索框中的相关数据获取 差旅费报销单模型 相关记录
            travel_line_records = self._get_travel_line_records(domain_fields)
            # 组织整理 差旅费报销单模型 所需数据字典
            if travel_line_records:
                data_dict = self._get_travel_expense_payable_line_data(travel_line_records, data_dict, domain_fields, model_name_key='travel')

            # 根据搜索框中的相关数据获取 费用报销单模型 相关记录
            expense_line_records = self._get_expense_line_records(domain_fields)
            # 组织整理 费用报销单模型 所需数据字典
            if expense_line_records:
                data_dict = self._get_travel_expense_payable_line_data(expense_line_records, data_dict, domain_fields, model_name_key='expense')

            # 根据搜索框中的相关数据获取 其他应付单模型 相关记录
            other_payable_line_records = self._get_other_payable_line_records(domain_fields)
            # 组织整理 其他应付单模型 所需数据字典
            if other_payable_line_records:
                data_dict = self._get_travel_expense_payable_line_data(other_payable_line_records, data_dict, domain_fields, model_name_key='payable')

        # 对所需的key进行排序
        data_key_list = [key for key in data_dict]
        data_key_list.sort()

        return data_dict, data_key_list

    def _get_inv_records(self, domain_fields):
        """
        根据搜索框中的相关数据获取 进项发票模型 相关记录
        :param:
            self: 当前实例对象
            domain_fields: 字段选择过滤条件
        :return:
            records: 进项发票模型相关记录
        """
        # 提取公共表 obj
        inv_obj = self.env['iv.input.vat.inv']
        mdm_invoice_type_obj = self.env['mdm.invoice.type']
        mdm_supplier_obj = self.env['mdm.supplier']
        mdm_customer_obj = self.env['mdm.customer']
        mdm_employee_obj = self.env['mdm.employee']

        # 提取公共变量
        inv_start_date = domain_fields.get('inv_start_date')  # 发票日期从
        inv_end_date = domain_fields.get('inv_end_date')  # 发票日期至
        check_start_date = domain_fields.get('check_start_date')  # 勾选日期从
        check_end_date = domain_fields.get('check_end_date')  # 勾选日期至
        declare_start_date = domain_fields.get('declare_start_date')  # 申报日期从
        declare_end_date = domain_fields.get('declare_end_date')  # 申报日期至
        sett_org_id = domain_fields.get('sett_org_id')  # 结算组织
        project_ids = domain_fields.get('project_ids')  # 项目名称
        contact_dept_type = domain_fields.get('contact_dept_type')  # 往来单位类型
        supplier_ids = domain_fields.get('supplier_ids')  # 供应商
        customer_ids = domain_fields.get('customer_ids')  # 客户
        employee_ids = domain_fields.get('employee_ids')  # 员工
        inv_type_ids = domain_fields.get('inv_type_ids')  # 发票类型
        inv_code = domain_fields.get('inv_code')  # 发票代码
        inv_number = domain_fields.get('inv_number')  # 发票号（非增值税票号）
        amount_total = domain_fields.get('amount_total')  # 不含税金额
        tax_total = domain_fields.get('tax_total')  # 税额
        amount_tax_total = domain_fields.get('amount_tax_total')  # 价税合计
        is_deduction = domain_fields.get('is_deduction')  # 抵扣勾选
        is_declare = domain_fields.get('is_declare')  # 已申报
        is_error = domain_fields.get('is_error')  # 是否异常
        is_include_unaudit_doc = domain_fields.get('is_include_unaudit_doc')  # 包含未审核单据
        currency_ids = domain_fields.get('currency_ids')  # 币别

        # 组织domain过滤
        domain = [
            ('sett_org_id', '=', sett_org_id),
            ('inv_date', '>=', inv_start_date),
            ('inv_date', '<=', inv_end_date),
            ('delete_state', '=', 'normal'),
            ('currency_id', 'in', currency_ids),
        ]

        # 根据特殊的过滤字段，补充domain过滤
        # 勾选日期从
        if check_start_date:
            domain.append(('check_date', '>=', check_start_date))

        # 勾选日期至
        if check_end_date:
            domain.append(('check_date', '<=', check_end_date))

        # 申报日期从
        if declare_start_date:
            domain.append(('declare_date', '>=', declare_start_date))

        # 申报日期至
        if declare_end_date:
            domain.append(('declare_date', '<=', declare_end_date))

        # 项目名称
        if project_ids:
            domain.append(('project_id', 'in', project_ids))

        # 往来单位（销方）
        if contact_dept_type == 'supplier':
            contact_dept_name = 'mdm.supplier,'
            if supplier_ids:
                mdm_supl_cust_empl_ids = supplier_ids
            else:
                mdm_supl_cust_empl_ids = mdm_supplier_obj.search([('use_org_id', '=', sett_org_id)]).ids
        elif contact_dept_type == 'customer':
            contact_dept_name = 'mdm.customer,'
            if customer_ids:
                mdm_supl_cust_empl_ids = customer_ids
            else:
                mdm_supl_cust_empl_ids = mdm_customer_obj.search([('use_org_id', '=', sett_org_id)]).ids
        else:
            contact_dept_name = 'mdm.employee,'
            if employee_ids:
                mdm_supl_cust_empl_ids = employee_ids
            else:
                mdm_supl_cust_empl_ids = mdm_employee_obj.search([('use_org_id', '=', sett_org_id)]).ids
        domain_contact_dept = [contact_dept_name + str(r) for r in mdm_supl_cust_empl_ids]
        domain.append(('contact_dept', 'in', domain_contact_dept))

        # 发票类型
        if inv_type_ids:
            domain.append(('inv_type_id', 'in', inv_type_ids))
        else:
            inv_type_records = mdm_invoice_type_obj.search([
                '|', '&',
                ('type', '=', 'other'),
                ('deduction_type', '=', 'other_deduction'),
                ('type', 'in', ['vat_invoice', 'vat_general_invoice'])
            ])
            domain.append(('inv_type_id', 'in', inv_type_records.ids))

        # 发票代码
        if inv_code:
            domain.append(('inv_code', '=', inv_code))

        # 发票号
        if inv_number:
            domain.append(('inv_number', '=', inv_number))

        # 不含税金额
        if amount_total:
            domain.append(('amount_total', '=', amount_total))

        # 税额
        if tax_total:
            domain.append(('tax_total', '=', tax_total))

        # 价税合计
        if amount_tax_total:
            domain.append(('amount_tax_total', '=', amount_tax_total))

        # 抵扣勾选
        if is_deduction == 't':
           domain.append(('is_deduction', '=', True))
        elif is_deduction == 'false':
           domain.append(('f', '=', False))

        # 已申报
        if is_declare == 't':
           domain.append(('is_declare', '=', True))
        elif is_declare == 'f':
           domain.append(('is_declare', '=', False))

        # 是否异常
        if is_error == 't':
           domain.append(('is_error', '=', True))
        elif is_error == 'f':
           domain.append(('is_error', '=', False))

        # 包含未审核单据
        if is_include_unaudit_doc:
            domain.append(('state', '!=', 'temporary'))
        else:
            domain.append(('state', '=', 'audit'))
            
        # 获取进项增值税发票相关数据记录
        records = inv_obj.search(domain)
        return records

    def _get_travel_line_records(self, domain_fields):
        """
        根据搜索框中的相关数据获取 差旅费报销单模型 相关记录
        :param:
            self: 当前实例对象
            domain_fields: 字段选择过滤条件
        :return:
            records: 差旅费报销单模型相关记录
        """
        # 提取公共表 obj
        travel_line1_line2_obj = self.env['er.travel.line1.line2']
        mdm_invoice_type_obj = self.env['mdm.invoice.type']

        # 提取公共变量
        inv_start_date = domain_fields.get('inv_start_date')  # 发票日期从
        inv_end_date = domain_fields.get('inv_end_date')  # 发票日期至
        declare_start_date = domain_fields.get('declare_start_date')  # 申报日期从
        declare_end_date = domain_fields.get('declare_end_date')  # 申报日期至
        sett_org_id = domain_fields.get('sett_org_id')  # 结算组织
        project_ids = domain_fields.get('project_ids')  # 项目名称
        inv_type_ids = domain_fields.get('inv_type_ids')  # 发票类型
        inv_number = domain_fields.get('inv_number')  # 发票号（非增值税票号）
        amount_total = domain_fields.get('amount_total')  # 不含税金额
        tax_total = domain_fields.get('tax_total')  # 税额
        amount_tax_total = domain_fields.get('amount_tax_total')  # 价税合计
        is_declare = domain_fields.get('is_declare')  # 已申报
        is_include_unaudit_doc = domain_fields.get('is_include_unaudit_doc')  # 包含未审核单据
        currency_ids = domain_fields.get('currency_ids')  # 币别

        # 组织domain过滤
        domain = [
            ('exp_date', '<=', inv_end_date),
            ('exp_date', '>=', inv_start_date),
            ('inv_type_id.deduction_type', '=', 'other_deduction'),
            ('parent_id.parent_id.delete_state', '=', 'normal'),
            ('parent_id.parent_id.exp_org_id', '=', sett_org_id),
            ('parent_id.parent_id.currency_id', 'in', currency_ids)
        ]

        # 根据特殊的过滤字段，补充domain过滤
        # 申报日期从
        if declare_start_date:
            domain.append(('declare_date', '>=', declare_start_date))

        # 申报日期至
        if declare_end_date:
            domain.append(('declare_date', '<=', declare_end_date))

        # 发票类型
        if inv_type_ids:
            domain.append(('inv_type_id', 'in', inv_type_ids))
        else:
            inv_type_records = mdm_invoice_type_obj.search([
                '|', '&',
                ('type', '=', 'other'),
                ('deduction_type', '=', 'other_deduction'),
                ('type', 'in', ['vat_invoice', 'vat_general_invoice'])
            ])
            domain.append(('inv_type_id', 'in', inv_type_records.ids))

        # 发票号
        if inv_number:
            domain.append(('ticket_number', '=', inv_number))

        # 不含税金额
        if amount_total:
            domain.append(('exp_amount', '=', amount_total))

        # 税额
        if tax_total:
            domain.append(('tax', '=', tax_total))

        # 价税合计
        if amount_tax_total:
            domain.append(('aprv_amount', '=', amount_tax_total))

        # 已申报
        if is_declare == 't':
           domain.append(('is_declare', '=', True))
        elif is_declare == 'f':
           domain.append(('is_declare', '=', False))

        # 包含未审核单据
        state_list = []
        if is_include_unaudit_doc:
            state_list = ['creating', 'save', 'submit', 'audit']
        else:
            state_list = ['audit']
        domain.append(('parent_id.parent_id.state', 'in', state_list))

        # 项目名称
        if project_ids:
            domain.append(('parent_id.parent_id.project_id', 'in', project_ids))

        # 获取差旅费报销单相关数据记录
        records = travel_line1_line2_obj.search(domain)

        return records

    def _get_expense_line_records(self, domain_fields):
        """
        根据搜索框中的相关数据获取 费用报销单模型 相关记录
        :param:
            self: 当前实例对象
            domain_fields: 字段选择过滤条件
        :return:
            records: 费用报销单模型相关记录
        """
        # 提取公共表 obj
        expense_line1_obj = self.env['er.expense.line1.expense']
        mdm_invoice_type_obj = self.env['mdm.invoice.type']

        # 提取公共变量
        inv_start_date = domain_fields.get('inv_start_date')  # 发票日期从
        inv_end_date = domain_fields.get('inv_end_date')  # 发票日期至
        declare_start_date = domain_fields.get('declare_start_date')  # 申报日期从
        declare_end_date = domain_fields.get('declare_end_date')  # 申报日期至
        sett_org_id = domain_fields.get('sett_org_id')  # 结算组织
        project_ids = domain_fields.get('project_ids')  # 项目名称
        inv_type_ids = domain_fields.get('inv_type_ids')  # 发票类型
        inv_number = domain_fields.get('inv_number')  # 发票号（非增值税票号）
        amount_total = domain_fields.get('amount_total')  # 不含税金额
        tax_total = domain_fields.get('tax_total')  # 税额
        amount_tax_total = domain_fields.get('amount_tax_total')  # 价税合计
        is_declare = domain_fields.get('is_declare')  # 已申报
        is_include_unaudit_doc = domain_fields.get('is_include_unaudit_doc')  # 包含未审核单据
        currency_ids = domain_fields.get('currency_ids')  # 币别

        # 组织domain过滤
        domain = [
            ('exp_date', '<=', inv_end_date),
            ('exp_date', '>=', inv_start_date),
            ('inv_type_id.deduction_type', '=', 'other_deduction'),
            ('parent_id.delete_state', '=', 'normal'),
            ('parent_id.exp_org_id', '=', sett_org_id),
            ('parent_id.currency_id', 'in', currency_ids)
        ]

        # 根据特殊的过滤字段，补充domain过滤
        # 申报日期从
        if declare_start_date:
            domain.append(('declare_date', '>=', declare_start_date))

        # 申报日期至
        if declare_end_date:
            domain.append(('declare_date', '<=', declare_end_date))

        # 发票类型
        if inv_type_ids:
            domain.append(('inv_type_id', 'in', inv_type_ids))
        else:
            inv_type_records = mdm_invoice_type_obj.search([
                '|', '&',
                ('type', '=', 'other'),
                ('deduction_type', '=', 'other_deduction'),
                ('type', 'in', ['vat_invoice', 'vat_general_invoice'])
            ])
            domain.append(('inv_type_id', 'in', inv_type_records.ids))

        # 发票号
        if inv_number:
            domain.append(('non_vat_num', '=', inv_number))

        # 不含税金额
        if amount_total:
            domain.append(('exp_amount', '=', amount_total))

        # 税额
        if tax_total:
            domain.append(('tax', '=', tax_total))

        # 价税合计
        if amount_tax_total:
            domain.append(('aprv_amount', '=', amount_tax_total))

        # 已申报
        if is_declare == 't':
           domain.append(('is_declare', '=', True))
        elif is_declare == 'f':
           domain.append(('is_declare', '=', False))

        # 包含未审核单据
        state_list = []
        if is_include_unaudit_doc:
            state_list = ['creating', 'save', 'submit', 'audit']
        else:
            state_list = ['audit']
        domain.append(('parent_id.state', 'in', state_list))

        # 项目名称
        if project_ids:
            domain.append(('parent_id.project_id', 'in', project_ids))

        # 获取费用报销单模型相关数据记录
        records = expense_line1_obj.search(domain)

        return records

    def _get_other_payable_line_records(self, domain_fields):
        """
        根据搜索框中的相关数据获取 其他应付单模型 相关记录
        :param:
            self: 当前实例对象
            domain_fields: 字段选择过滤条件
        :return:
            records: 其他应付单模型相关记录
        """
        # 提取公共表 obj
        other_payable_line1_line2_obj = self.env['ap.other.payable.line1']
        mdm_invoice_type_obj = self.env['mdm.invoice.type']
        mdm_supplier_obj = self.env['mdm.supplier']
        mdm_customer_obj = self.env['mdm.customer']
        mdm_employee_obj = self.env['mdm.employee']

        # 提取公共变量
        inv_start_date = domain_fields.get('inv_start_date')  # 发票日期从
        inv_end_date = domain_fields.get('inv_end_date')  # 发票日期至
        declare_start_date = domain_fields.get('declare_start_date')  # 申报日期从
        declare_end_date = domain_fields.get('declare_end_date')  # 申报日期至
        sett_org_id = domain_fields.get('sett_org_id')  # 结算组织
        project_ids = domain_fields.get('project_ids')  # 项目名称
        contact_dept_type = domain_fields.get('contact_dept_type')  # 往来单位类型
        supplier_ids = domain_fields.get('supplier_ids')  # 供应商
        customer_ids = domain_fields.get('customer_ids')  # 客户
        employee_ids = domain_fields.get('employee_ids')  # 员工
        inv_type_ids = domain_fields.get('inv_type_ids')  # 发票类型
        inv_number = domain_fields.get('inv_number')  # 发票号（非增值税票号）
        amount_total = domain_fields.get('amount_total')  # 不含税金额
        tax_total = domain_fields.get('tax_total')  # 税额
        amount_tax_total = domain_fields.get('amount_tax_total')  # 价税合计
        is_declare = domain_fields.get('is_declare')  # 已申报
        is_include_unaudit_doc = domain_fields.get('is_include_unaudit_doc')  # 包含未审核单据
        currency_ids = domain_fields.get('currency_ids')  # 币别

        # 单据类型（其他应付单）
        ap_other_payable_other_document_type_data = self.env.ref('ps_ap.ap_other_payable_other_document_type_data').id

        # 组织domain过滤
        domain = [
            ('inv_type_id.deduction_type', '=', 'other_deduction'),
            ('parent_id.document_type_id', 'in', [ap_other_payable_other_document_type_data]),
            ('parent_id.delete_state', '=', 'normal'),
            ('parent_id.sett_org_id', '=', sett_org_id),
            ('parent_id.currency_id', 'in', currency_ids),
            ('parent_id.biz_date', '<=', inv_end_date),
            ('parent_id.biz_date', '>=', inv_start_date)
        ]

        # 根据特殊的过滤字段，补充domain过滤
        # 申报日期从
        if declare_start_date:
            domain.append(('declare_date', '>=', declare_start_date))

        # 申报日期至
        if declare_end_date:
            domain.append(('declare_date', '<=', declare_end_date))

        # 发票类型
        if inv_type_ids:
            domain.append(('inv_type_id', 'in', inv_type_ids))
        else:
            inv_type_records = mdm_invoice_type_obj.search([
                '|', '&',
                ('type', '=', 'other'),
                ('deduction_type', '=', 'other_deduction'),
                ('type', 'in', ['vat_invoice', 'vat_general_invoice'])
            ])
            domain.append(('inv_type_id', 'in', inv_type_records.ids))

        # 发票号
        if inv_number:
            domain.append(('non_vat_num', '=', inv_number))

        # 不含税金额
        if amount_total:
            domain.append(('amount', '=', amount_total))

        # 税额
        if tax_total:
            domain.append(('tax', '=', tax_total))

        # 价税合计
        if amount_tax_total:
            domain.append(('subtotal', '=', amount_tax_total))

        # 已申报
        if is_declare == 't':
           domain.append(('is_declare', '=', True))
        elif is_declare == 'f':
           domain.append(('is_declare', '=', False))

        # 包含未审核单据
        state_list = []
        if is_include_unaudit_doc:
            state_list = ['creating', 'save', 'submit', 'audit']
        else:
            state_list = ['audit']
        domain.append(('parent_id.state', 'in', state_list))

        # 往来单位（销方）
        if contact_dept_type == 'supplier':
            contact_dept_name = 'mdm.supplier,'
            if supplier_ids:
                mdm_supl_cust_empl_ids = supplier_ids
            else:
                mdm_supl_cust_empl_ids = mdm_supplier_obj.search([('use_org_id', '=', sett_org_id)]).ids
        elif contact_dept_type == 'customer':
            contact_dept_name = 'mdm.customer,'
            if customer_ids:
                mdm_supl_cust_empl_ids = customer_ids
            else:
                mdm_supl_cust_empl_ids = mdm_customer_obj.search([('use_org_id', '=', sett_org_id)]).ids
        else:
            contact_dept_name = 'mdm.employee,'
            if employee_ids:
                mdm_supl_cust_empl_ids = employee_ids
            else:
                mdm_supl_cust_empl_ids = mdm_employee_obj.search([('use_org_id', '=', sett_org_id)]).ids
        domain_contact_dept = [contact_dept_name + str(r) for r in mdm_supl_cust_empl_ids]
        domain.append(('parent_id.contact_dept', 'in', domain_contact_dept))
        # 项目名称
        if project_ids:
            domain.append(('parent_id.project_id', 'in', project_ids))
        
        # 获取其他应付单相关数据记录
        records = other_payable_line1_line2_obj.search(domain)

        return records

    def _get_inv_detail_data(self, records, data_dict, domain_fields):
        """
        组织整理 进项发票模型（发票明细） 所需相关数据
        :param:
            self: 当前实例对象
            records: 进项发票模型相关记录
            data_dict: 数据汇总字典（含汇总key）
            domain_fields: 字段选择过滤条件
        :return:
            data_dict: 组织好的数据创建相关记录（含汇总key）
        """
        # 提取公共变量
        is_type_total = domain_fields['is_type_total']
        total_amount = 0  # 不含税金额（合计）
        total_tax = 0  # 税额（合计）
        total_amount_tax = 0  # 价税合计（合计）
        total_amount_total = 0  # 不含税金额（合计）
        total_tax_total = 0  # 税额（合计）
        total_amount_tax_total = 0  # 价税合计（合计）

        # 判断是否按发票类型汇总
        if is_type_total:
            for record in records:

                # 提取公共变量
                inv_type_record = record.inv_type_id  # 发票类型obj
                contact_dept_record = record.contact_dept  # 往来单位（销方）obj
                sett_org_record = record.sett_org_id  # 结算组织obj
                project_record = record.project_id  # 项目名称obj
                src_record = record  # 单据obj
                currency_record = record.currency_id  # 币别obj

                document_number = record.number  # 单据编号
                state = self._get_translate_info('State_Selection')[record.state]  # 单据状态
                inv_type_name = inv_type_record.name  # 发票类型（展示）
                inv_date = record.inv_date  # 发票日期
                inv_code = record.inv_code  # 发票代码
                inv_number = record.inv_number  # 发票号
                contact_dept = contact_dept_record.name  # 往来单位（销方）
                is_deduction = _('True') if record.is_deduction else _('False')  # 抵扣勾选
                check_date = record.check_date if record.check_date else None  # 勾选日期
                is_declare = _('True') if record.is_declare else _('False')  # 已申报
                declare_date = record.declare_date if record.declare_date else None  # 申报日期
                is_error = _('True') if record.is_error else _('False')  # 是否异常
                sett_org_name = sett_org_record.name  # 结算组织（展示）
                project_name = project_record.name if project_record else None  # 项目名称（展示）
                project_number = project_record.number if project_record else None  # 项目编号
                
                doc_id = src_record.id  # 单据id
                doc_model_name = record._name  # 单据模型名
                currency_id = currency_record.id  # 币别id
                inv_type_id = inv_type_record.id  # 发票类型id
                amount_total = record.amount_total  # 不含税金额
                tax_total = record.tax_total  # 税额
                amount_tax_total = record.amount_tax_total  # 价税合计

                # 定义报表穿透到单据的ref_to_doc
                record_type = record.type  # 分类
                ref_to_doc = None
                if record_type == 'vat_invoice':
                    ref_to_doc = 'ps_iv.action_input_vat_invoice'
                elif record_type == 'vat_general_invoice':
                    ref_to_doc = 'ps_iv.action_common_input_vat_invoice'

                # 根据增值税发票数据组织相关数据
                # 按照发票类型id、发票日期、模型（进项发票模型、差旅费报销单、费用报销单、其他应付单的模型顺序）排序
                # 需要注意如果在差旅费报销单、费用报销单、其他应付单模型下可能出现一张单据引用两次相同的发票，则需要汇总【当出现相同模型、相同单据编号、相同发票代码、相同发票号（非增值税票号）的数据时，需要进行汇总展示】
                key_inv_type_id = 'inv_type_id_' + str(inv_type_id).zfill(8)
                key_inv_date = 'inv_date_' + str(inv_date)
                key_model_sequence = 'model_sequence_1'
                key_doc_id = 'doc_id_' + str(doc_id).zfill(8)
                key = 'key_' + key_inv_type_id + '_' + key_inv_date + '_' + key_model_sequence + '_' + key_doc_id

                # 因为是按照发票明细展示数据，因此需要循环发票表头的 line1_detail_ids 获取发票明细数据
                for line in record.line1_detail_ids:

                    # 提取公共变量
                    material_name = line.material_name if line.material_name else None  # 发票项目
                    specification = line.specification if line.specification else None  # 规格型号
                    unit_name = line.unit_id.name if line.unit_id else None  # 计价单位（展示）
                    qty = line.qty  # 计价数量
                    unit_price_tax = line.unit_price_tax  # 含税单价
                    unit_price = line.unit_price  # 单价
                    amount = line.amount  # 不含税金额
                    tax_rate = line.tax_rate  # 税率（%）
                    tax = line.tax  # 税额
                    amount_tax = line.amount_tax  # 价税合计
                    line_id = line.id  # 明细行id

                    # 这里需要在之前组织好的key的基础上加上 detail明细行 id key
                    key_doc_detail_id = 'doc_detail_id_' + str(line_id).zfill(8)
                    line_key = key + '_' + key_doc_detail_id

                    # 这里组织 data_dict 时先取公共的 inv_dict ，再补充其中缺少的需要循环的 detail明细行 部分
                    data_dict[line_key] = {
                        'document_number': document_number,  # 单据编号
                        'state': state,  # 单据状态
                        'inv_type_name': inv_type_name,  # 发票类型（展示）
                        'inv_date': inv_date,  # 发票日期
                        'inv_code': inv_code,  # 发票代码
                        'inv_number': inv_number,  # 发票号
                        'contact_dept': contact_dept,  # 往来单位（销方）
                        'material_name': material_name,  # 发票项目
                        'specification': specification,  # 规格型号
                        'unit_name': unit_name,  # 计价单位（展示）
                        'qty': qty,  # 计价数量
                        'unit_price_tax': unit_price_tax,  # 含税单价
                        'unit_price': unit_price,  # 单价
                        'amount': amount,  # 不含税金额
                        'tax_rate': tax_rate,  # 税率（%）
                        'tax': tax,  # 税额
                        'amount_tax': amount_tax,  # 价税合计
                        'is_deduction': is_deduction,  # 抵扣勾选
                        'check_date': check_date,  # 勾选日期
                        'is_declare': is_declare,  # 已申报
                        'declare_date': declare_date,  # 申报日期
                        'is_error': is_error,  # 是否异常
                        'sett_org_name': sett_org_name,  # 结算组织（展示）
                        'project_name': project_name,  # 项目名称（展示）
                        'project_number': project_number,  # 项目编号
                        'doc_id': doc_id,  # 单据id
                        'doc_model_name': doc_model_name,  # 单据模型名
                        'currency_id': currency_id,  # 币别id
                        'ref_to_doc': ref_to_doc,  # 穿透到单据action
                        'amount_total': 0,  # 不含税金额
                        'tax_total': 0,  # 税额
                        'amount_tax_total': 0,  # 价税合计
                        'is_subtotal': False,  # 是否小计
                        'is_total': False,  # 是否合计
                    }

                    # 组织小计数据
                    sub_key = 'key_' + key_inv_type_id + '_subtotal'
                    
                    if data_dict.get(sub_key):
                        data_dict[sub_key]['amount'] += amount  # 不含税金额
                        data_dict[sub_key]['tax'] += tax  # 税额
                        data_dict[sub_key]['amount_tax'] += amount_tax  # 价税合计
                    else:
                        data_dict[sub_key] = {
                            'document_number': None,  # 单据编号
                            'state': None,  # 单据状态
                            'inv_type_name': inv_type_name + _('subtotal'),  # 发票类型（展示）
                            'inv_date': None,  # 发票日期
                            'inv_code': None,  # 发票代码
                            'inv_number': None,  # 发票号
                            'contact_dept': None,  # 往来单位（销方）
                            'material_name': None,  # 发票项目
                            'specification': None,  # 规格型号
                            'unit_name': None,  # 计价单位（展示）
                            'qty': None,  # 计价数量
                            'unit_price_tax': None,  # 含税单价
                            'unit_price': None,  # 单价
                            'amount': amount,  # 不含税金额
                            'tax_rate': None,  # 税率（%）
                            'tax': tax,  # 税额
                            'amount_tax': amount_tax,  # 价税合计
                            'is_deduction': None,  # 抵扣勾选
                            'check_date': None,  # 勾选日期
                            'is_declare': None,  # 已申报
                            'declare_date': None,  # 申报日期
                            'is_error': None,  # 是否异常
                            'sett_org_name': None,  # 结算组织（展示）
                            'project_name': None,  # 项目名称（展示）
                            'project_number': None,  # 项目编号
                            'doc_id': None,  # 单据id
                            'doc_model_name': None,  # 单据模型名
                            'currency_id': None,  # 币别id
                            'ref_to_doc': None,  # 穿透到单据action
                            'amount_total': 0,  # 不含税金额
                            'tax_total': 0,  # 税额
                            'amount_tax_total': 0,  # 价税合计
                            'is_subtotal': True,  # 是否小计
                            'is_total': False,  # 是否合计
                        }

                    # 组织合计数据
                    total_amount += amount  # 不含税金额（合计）
                    total_tax += tax  # 税额（合计）
                    total_amount_tax += amount_tax  # 价税合计（合计）

                # 这里需要注意，按照明细展示时，合计展示的是发票明细行的合计
                # 这里需要把表头的也汇总一下，因为后续业务单据的这几个金额是直接展示业务单据明细行对应的发票占用金额
                total_amount_total += amount_total  # 不含税金额（合计）
                total_tax_total += tax_total  # 税额（合计）
                total_amount_tax_total += amount_tax_total  # 价税合计（合计）

        else:
            for record in records:

                # 提取公共变量
                inv_type_record = record.inv_type_id  # 发票类型obj
                contact_dept_record = record.contact_dept  # 往来单位（销方）obj
                sett_org_record = record.sett_org_id  # 结算组织obj
                project_record = record.project_id  # 项目名称obj
                src_record = record  # 单据obj
                currency_record = record.currency_id  # 币别obj

                document_number = record.number  # 单据编号
                state = self._get_translate_info('State_Selection')[record.state]  # 单据状态
                inv_type_name = inv_type_record.name  # 发票类型（展示）
                inv_date = record.inv_date  # 发票日期
                inv_code = record.inv_code  # 发票代码
                inv_number = record.inv_number  # 发票号
                contact_dept = contact_dept_record.name  # 往来单位（销方）
                is_deduction = _('True') if record.is_deduction else _('False')  # 抵扣勾选
                check_date = record.check_date if record.check_date else None  # 勾选日期
                is_declare = _('True') if record.is_declare else _('False')  # 已申报
                declare_date = record.declare_date if record.declare_date else None  # 申报日期
                is_error = _('True') if record.is_error else _('False')  # 是否异常
                sett_org_name = sett_org_record.name  # 结算组织（展示）
                project_name = project_record.name if project_record else None  # 项目名称（展示）
                project_number = project_record.number if project_record else None  # 项目编号
                
                doc_id = src_record.id  # 单据id
                doc_model_name = record._name  # 单据模型名
                currency_id = currency_record.id  # 币别id
                amount_total = record.amount_total  # 不含税金额
                tax_total = record.tax_total  # 税额
                amount_tax_total = record.amount_tax_total  # 价税合计

                # 定义报表穿透到单据的ref_to_doc
                record_type = record.type  # 分类
                ref_to_doc = None
                if record_type == 'vat_invoice':
                    ref_to_doc = 'ps_iv.action_input_vat_invoice'
                elif record_type == 'vat_general_invoice':
                    ref_to_doc = 'ps_iv.action_common_input_vat_invoice'

                # 根据增值税发票数据组织相关数据
                # 按照发票类型id、发票日期、模型（进项发票模型、差旅费报销单、费用报销单、其他应付单的模型顺序）、表头id、表体发票号
                # 需要注意如果在差旅费报销单、费用报销单、其他应付单模型下可能出现一张单据引用两次相同的发票，则需要汇总【当出现相同模型、相同单据编号、相同发票代码、相同发票号（非增值税票号）的数据时，需要进行汇总展示】
                key_inv_date = 'inv_date_' + str(inv_date)
                key_model_sequence = 'model_sequence_1'
                key_doc_id = 'doc_id_' + str(doc_id).zfill(8)
                key = 'key_' + key_inv_date + '_' + key_model_sequence + '_' + key_doc_id

                # 因为是按照发票明细展示数据，因此需要循环发票表头的 line1_detail_ids 获取发票明细数据
                for line in record.line1_detail_ids:

                    # 提取公共变量
                    material_name = line.material_name if line.material_name else None  # 发票项目
                    specification = line.specification if line.specification else None  # 规格型号
                    unit_name = line.unit_id.name if line.unit_id else None  # 计价单位（展示）
                    qty = line.qty  # 计价数量
                    unit_price_tax = line.unit_price_tax  # 含税单价
                    unit_price = line.unit_price  # 单价
                    amount = line.amount  # 不含税金额
                    tax_rate = line.tax_rate  # 税率（%）
                    tax = line.tax  # 税额
                    amount_tax = line.amount_tax  # 价税合计
                    line_id = line.id  # 明细行id

                    # 这里需要在之前组织好的key的基础上加上 detail明细行 id key
                    key_doc_detail_id = 'doc_detail_id_' + str(line_id).zfill(8)
                    line_key = key + '_' + key_doc_detail_id

                    data_dict[line_key] = {
                        'document_number': document_number,  # 单据编号
                        'state': state,  # 单据状态
                        'inv_type_name': inv_type_name,  # 发票类型（展示）
                        'inv_date': inv_date,  # 发票日期
                        'inv_code': inv_code,  # 发票代码
                        'inv_number': inv_number,  # 发票号
                        'contact_dept': contact_dept,  # 往来单位（销方）
                        'material_name': material_name,  # 发票项目
                        'specification': specification,  # 规格型号
                        'unit_name': unit_name,  # 计价单位（展示）
                        'qty': qty,  # 计价数量
                        'unit_price_tax': unit_price_tax,  # 含税单价
                        'unit_price': unit_price,  # 单价
                        'amount': amount,  # 不含税金额
                        'tax_rate': tax_rate,  # 税率（%）
                        'tax': tax,  # 税额
                        'amount_tax': amount_tax,  # 价税合计
                        'is_deduction': is_deduction,  # 抵扣勾选
                        'check_date': check_date,  # 勾选日期
                        'is_declare': is_declare,  # 已申报
                        'declare_date': declare_date,  # 申报日期
                        'is_error': is_error,  # 是否异常
                        'sett_org_name': sett_org_name,  # 结算组织（展示）
                        'project_name': project_name,  # 项目名称（展示）
                        'project_number': project_number,  # 项目编号
                        'doc_id': doc_id,  # 单据id
                        'doc_model_name': doc_model_name,  # 单据模型名
                        'currency_id': currency_id,  # 币别id
                        'ref_to_doc': ref_to_doc,  # 穿透到单据action
                        'amount_total': 0,  # 不含税金额
                        'tax_total': 0,  # 税额
                        'amount_tax_total': 0,  # 价税合计
                        'is_subtotal': False,  # 是否小计
                        'is_total': False,  # 是否合计
                    }

                    # 组织合计数据
                    total_amount += amount  # 不含税金额（合计）
                    total_tax += tax  # 税额（合计）
                    total_amount_tax += amount_tax  # 价税合计（合计）

                # 这里需要注意，按照明细展示时，合计展示的是发票明细行的合计
                # 这里需要把表头的也汇总一下，因为后续业务单据的这几个金额是直接展示业务单据明细行对应的发票占用金额
                total_amount_total += amount_total  # 不含税金额（合计）
                total_tax_total += tax_total  # 税额（合计）
                total_amount_tax_total += amount_tax_total  # 价税合计（合计）
        
        if data_dict:
            data_dict['total_all'] = {
                'document_number': None,  # 单据编号
                'state': None,  # 单据状态
                'inv_type_name': _('total'),  # 发票类型（展示）
                'inv_date': None,  # 发票日期
                'inv_code': None,  # 发票代码
                'inv_number': None,  # 发票号
                'contact_dept': None,  # 往来单位（销方）
                'material_name': None,  # 发票项目
                'specification': None,  # 规格型号
                'unit_name': None,  # 计价单位（展示）
                'qty': None,  # 计价数量
                'unit_price_tax': None,  # 含税单价
                'unit_price': None,  # 单价
                'amount': total_amount,  # 不含税金额
                'tax_rate': None,  # 税率（%）
                'tax': total_tax,  # 税额
                'amount_tax': total_amount_tax,  # 价税合计
                'is_deduction': None,  # 抵扣勾选
                'check_date': None,  # 勾选日期
                'is_declare': None,  # 已申报
                'declare_date': None,  # 申报日期
                'is_error': None,  # 是否异常
                'sett_org_name': None,  # 结算组织（展示）
                'project_name': None,  # 项目名称（展示）
                'project_number': None,  # 项目编号
                'doc_id': None,  # 单据id
                'doc_model_name': None,  # 单据模型名
                'currency_id': None,  # 币别id
                'ref_to_doc': None,  # 穿透到单据action
                'amount_total': total_amount_total,  # 不含税金额
                'tax_total': total_tax_total,  # 税额
                'amount_tax_total': total_amount_tax_total,  # 价税合计
                'effective_tax': 0,  # 有效税额
                'occupy_inv_amount': 0,  # 已占用金额
                'is_subtotal': False,  # 是否小计
                'is_total': True,  # 是否合计
            }

        return data_dict

    def _get_inv_doc_data(self, records, data_dict, domain_fields):
        """
        组织整理 进项发票模型（引用发票） 所需相关数据
        :param:
            self: 当前实例对象
            records: 进项发票模型相关记录
            data_dict: 数据汇总字典（含汇总key）
            domain_fields: 字段选择过滤条件
        :return:
            data_dict: 组织好的数据创建相关记录（含汇总key）
        """
        # 提取公共变量
        is_type_total = domain_fields['is_type_total']
        total_amount_total = 0  # 不含税金额（合计）
        total_tax_total = 0  # 税额（合计）
        total_amount_tax_total = 0  # 价税合计（合计）
        total_effective_tax = 0  # 有效税额（合计）
        total_occupy_inv_amount = 0  # 已占用金额（合计）

        # 判断是否按发票类型汇总
        if is_type_total:
            for record in records:

                # 提取公共变量
                inv_type_record = record.inv_type_id  # 发票类型obj
                contact_dept_record = record.contact_dept  # 往来单位（销方）obj
                sett_org_record = record.sett_org_id  # 结算组织obj
                project_record = record.project_id  # 项目名称obj
                src_record = record  # 单据obj
                currency_record = record.currency_id  # 币别obj

                document_number = record.number  # 单据编号
                state = self._get_translate_info('State_Selection')[record.state]  # 单据状态
                inv_type_name = inv_type_record.name  # 发票类型（展示）
                inv_date = record.inv_date  # 发票日期
                inv_code = record.inv_code  # 发票代码
                inv_number = record.inv_number  # 发票号
                contact_dept = contact_dept_record.name  # 往来单位（销方）
                amount_total = record.amount_total  # 不含税金额
                tax_total = record.tax_total  # 税额
                amount_tax_total = record.amount_tax_total  # 价税合计
                doc_occupy_inv_amount = record.occupy_inv_amount # 已占用金额（表头）
                is_deduction = _('True') if record.is_deduction else _('False')  # 抵扣勾选
                check_date = record.check_date if record.check_date else None  # 勾选日期
                is_declare = _('True') if record.is_declare else _('False')  # 已申报
                declare_date = record.declare_date if record.declare_date else None  # 申报日期
                is_error = _('True') if record.is_error else _('False')  # 是否异常
                sett_org_name = sett_org_record.name  # 结算组织（展示）
                project_name = project_record.name if project_record else None  # 项目名称（展示）
                project_number = project_record.number if project_record else None  # 项目编号

                # 特殊处理有效税额字段取值
                is_che_duc = inv_type_record.is_che_duc  # 发票类型（允许抵扣勾选字段）
                if is_che_duc:
                    # 发票类型（允许抵扣勾选=1）
                    effective_tax = record.effective_tax
                else:
                    # 发票类型（允许抵扣勾选=0）
                    effective_tax = record.tax_total
                
                doc_id = src_record.id  # 单据id
                doc_model_name = record._name  # 单据模型名
                currency_id = currency_record.id  # 币别id
                inv_type_id = inv_type_record.id  # 发票类型id

                # 定义报表穿透到单据的ref_to_doc
                record_type = record.type  # 分类
                ref_to_doc = None
                if record_type == 'vat_invoice':
                    ref_to_doc = 'ps_iv.action_input_vat_invoice'
                elif record_type == 'vat_general_invoice':
                    ref_to_doc = 'ps_iv.action_common_input_vat_invoice'

                # 根据增值税发票数据组织相关数据
                # 按照发票类型id、发票日期、模型（进项发票模型、差旅费报销单、费用报销单、其他应付单的模型顺序）排序
                # 需要注意如果在差旅费报销单、费用报销单、其他应付单模型下可能出现一张单据引用两次相同的发票，则需要汇总【当出现相同模型、相同单据编号、相同发票代码、相同发票号（非增值税票号）的数据时，需要进行汇总展示】
                key_inv_type_id = 'inv_type_id_' + str(inv_type_id).zfill(8)
                key_inv_date = 'inv_date_' + str(inv_date)
                key_model_sequence = 'model_sequence_1'
                key_doc_id = 'doc_id_' + str(doc_id).zfill(8)
                key = 'key_' + key_inv_type_id + '_' + key_inv_date + '_' + key_model_sequence + '_' + key_doc_id

                if record.line1_doc_ids:
                    # 如果发票有引用，则按照引用展示

                    # 因为是按照发票明细展示数据，因此需要循环发票表头的 line1_doc_ids 获取发票明细数据
                    for index, line in enumerate(record.line1_doc_ids):

                        # 提取公共变量
                        occupy_inv_amount = line.occupy_inv_amount # 已占用金额
                        src_doc_number = line.document_number if line.document_number else None  # 引用单据
                        source_id = line.source_id  # 来源单据id
                        source_model_name = line.source_model_name  # 来源单据表名
                        voucher_number, voucher_id = self._get_voucher_number(source_id, source_model_name)   # 凭证号/凭证id
                        voucher_model_name = 'gl.voucher'  # 凭证模型名
                        line_id = line.id  # 明细行id
                        source_doc_type_num = line.src_doc_type_id.number

                        # 这里需要在之前组织好的key的基础上加上 doc明细行 id key
                        key_doc_detail_id = 'doc_detail_id_' + str(line_id).zfill(8)
                        line_key = key + '_' + key_doc_detail_id

                        if index == 0:

                            data_dict[line_key] = {
                                'document_number': document_number,  # 单据编号
                                'state': state,  # 单据状态
                                'inv_type_name': inv_type_name,  # 发票类型（展示）
                                'inv_date': inv_date,  # 发票日期
                                'inv_code': inv_code,  # 发票代码
                                'inv_number': inv_number,  # 发票号
                                'contact_dept': contact_dept,  # 往来单位（销方）
                                'amount_total': amount_total,  # 不含税金额
                                'tax_total': tax_total,  # 税额
                                'amount_tax_total': amount_tax_total,  # 价税合计
                                'is_deduction': is_deduction,  # 抵扣勾选
                                'check_date': check_date,  # 勾选日期
                                'effective_tax': effective_tax,  # 有效税额
                                'is_declare': is_declare,  # 已申报
                                'declare_date': declare_date,  # 申报日期
                                'is_error': is_error,  # 是否异常
                                'sett_org_name': sett_org_name,  # 结算组织（展示）
                                'project_name': project_name,  # 项目名称（展示）
                                'project_number': project_number,  # 项目编号
                                'occupy_inv_amount': occupy_inv_amount,  # 已占用金额
                                'src_doc_number': src_doc_number,  # 引用单据
                                'voucher_number': voucher_number,  # 凭证号
                                'doc_id': doc_id,  # 单据id
                                'doc_model_name': doc_model_name,  # 单据模型名
                                'source_id': source_id,  # 引用单据id
                                'source_model_name': source_model_name,  # 引用单据模型名
                                'voucher_id': voucher_id,  # 凭证id
                                'voucher_model_name': voucher_model_name,  # 凭证模型名
                                'currency_id': currency_id,  # 币别id
                                'ref_to_doc': ref_to_doc,  # 穿透到单据action
                                'is_subtotal': False,  # 是否小计
                                'is_total': False,  # 是否合计
                                'source_doc_type_num': source_doc_type_num,
                            }
                        else:
                            data_dict[line_key] = {
                                'document_number': None,  # 单据编号
                                'state': None,  # 单据状态
                                'inv_type_name': None,  # 发票类型（展示）
                                'inv_date': None,  # 发票日期
                                'inv_code': None,  # 发票代码
                                'inv_number': None,  # 发票号
                                'contact_dept': None,  # 往来单位（销方）
                                'amount_total': None,  # 不含税金额
                                'tax_total': None,  # 税额
                                'amount_tax_total': None,  # 价税合计
                                'is_deduction': None,  # 抵扣勾选
                                'check_date': None,  # 勾选日期
                                'effective_tax': None,  # 有效税额
                                'is_declare': None,  # 已申报
                                'declare_date': None,  # 申报日期
                                'is_error': None,  # 是否异常
                                'sett_org_name': None,  # 结算组织（展示）
                                'project_name': None,  # 项目名称（展示）
                                'project_number': None,  # 项目编号
                                'occupy_inv_amount': occupy_inv_amount,  # 已占用金额
                                'src_doc_number': src_doc_number,  # 引用单据
                                'voucher_number': voucher_number,  # 凭证号
                                'doc_id': None,  # 单据id
                                'doc_model_name': None,  # 单据模型名
                                'source_id': source_id,  # 引用单据id
                                'source_model_name': source_model_name,  # 引用单据模型名
                                'voucher_id': voucher_id,  # 凭证id
                                'voucher_model_name': voucher_model_name,  # 凭证模型名
                                'currency_id': currency_id,  # 币别id
                                'ref_to_doc': ref_to_doc,  # 穿透到单据action
                                'is_subtotal': False,  # 是否小计
                                'is_total': False,  # 是否合计
                                'source_doc_type_num': source_doc_type_num,
                            }

                    # 组织小计数据
                    sub_key = 'key_' + key_inv_type_id + '_subtotal'
                    
                    if data_dict.get(sub_key):
                        data_dict[sub_key]['amount_total'] += amount_total  # 不含税金额
                        data_dict[sub_key]['tax_total'] += tax_total  # 税额
                        data_dict[sub_key]['amount_tax_total'] += amount_tax_total  # 价税合计
                        data_dict[sub_key]['effective_tax'] += effective_tax  # 有效税额
                        data_dict[sub_key]['occupy_inv_amount'] += doc_occupy_inv_amount  # 已占用金额
                    else:
                        data_dict[sub_key] = {
                            'document_number': None,  # 单据编号
                            'state': None,  # 单据状态
                            'inv_type_name': inv_type_name + _('subtotal'),  # 发票类型（展示）
                            'inv_date': None,  # 发票日期
                            'inv_code': None,  # 发票代码
                            'inv_number': None,  # 发票号
                            'contact_dept': None,  # 往来单位（销方）
                            'amount_total': amount_total,  # 不含税金额
                            'tax_total': tax_total,  # 税额
                            'amount_tax_total': amount_tax_total,  # 价税合计
                            'is_deduction': None,  # 抵扣勾选
                            'check_date': None,  # 勾选日期
                            'effective_tax': effective_tax,  # 有效税额
                            'is_declare': None,  # 已申报
                            'declare_date': None,  # 申报日期
                            'is_error': None,  # 是否异常
                            'sett_org_name': None,  # 结算组织（展示）
                            'project_name': None,  # 项目名称（展示）
                            'project_number': None,  # 项目编号
                            'doc_id': None,  # 单据id
                            'doc_model_name': None,  # 单据模型名
                            'source_id': None,  # 引用单据id
                            'source_model_name': None,  # 引用单据模型名
                            'voucher_id': None,  # 凭证id
                            'voucher_model_name': None,  # 凭证模型名
                            'currency_id': None,  # 币别id
                            'occupy_inv_amount': doc_occupy_inv_amount,  # 已占用金额
                            'src_doc_number': None,  # 引用单据
                            'voucher_number': None,  # 凭证号
                            'ref_to_doc': None,  # 穿透到单据action
                            'is_subtotal': True,  # 是否小计
                            'is_total': False,  # 是否合计
                        }

                    # 组织合计数据
                    total_amount_total += amount_total  # 不含税金额（合计）
                    total_tax_total += tax_total  # 税额（合计）
                    total_amount_tax_total += amount_tax_total  # 价税合计（合计）
                    total_effective_tax += effective_tax  # 有效税额（合计）
                    total_occupy_inv_amount += doc_occupy_inv_amount  # 已占用金额（合计）

                else:
                    # 发票没有引用，则按照整单展示

                    # 提取公共变量
                    occupy_inv_amount = doc_occupy_inv_amount # 已占用金额
                    src_doc_number = document_number  # 引用单据

                    data_dict[key] = {
                        'document_number': document_number,  # 单据编号
                        'state': state,  # 单据状态
                        'inv_type_name': inv_type_name,  # 发票类型（展示）
                        'inv_date': inv_date,  # 发票日期
                        'inv_code': inv_code,  # 发票代码
                        'inv_number': inv_number,  # 发票号
                        'contact_dept': contact_dept,  # 往来单位（销方）
                        'amount_total': amount_total,  # 不含税金额
                        'tax_total': tax_total,  # 税额
                        'amount_tax_total': amount_tax_total,  # 价税合计
                        'is_deduction': is_deduction,  # 抵扣勾选
                        'check_date': check_date,  # 勾选日期
                        'effective_tax': effective_tax,  # 有效税额
                        'is_declare': is_declare,  # 已申报
                        'declare_date': declare_date,  # 申报日期
                        'is_error': is_error,  # 是否异常
                        'sett_org_name': sett_org_name,  # 结算组织（展示）
                        'project_name': project_name,  # 项目名称（展示）
                        'project_number': project_number,  # 项目编号
                        'occupy_inv_amount': occupy_inv_amount,  # 已占用金额
                        'src_doc_number': None,  # 引用单据
                        'voucher_number': None,  # 凭证号
                        'doc_id': doc_id,  # 单据id
                        'doc_model_name': doc_model_name,  # 单据模型名
                        'source_id': None,  # 引用单据id
                        'source_model_name': None,  # 引用单据模型名
                        'voucher_id': None,  # 凭证id
                        'voucher_model_name': None,  # 凭证模型名
                        'currency_id': currency_id,  # 币别id
                        'ref_to_doc': ref_to_doc,  # 穿透到单据action
                        'is_subtotal': False,  # 是否小计
                        'is_total': False,  # 是否合计
                    }

                    # 组织小计数据
                    sub_key = 'key_' + key_inv_type_id + '_subtotal'
                    
                    if data_dict.get(sub_key):
                        data_dict[sub_key]['amount_total'] += amount_total  # 不含税金额
                        data_dict[sub_key]['tax_total'] += tax_total  # 税额
                        data_dict[sub_key]['amount_tax_total'] += amount_tax_total  # 价税合计
                        data_dict[sub_key]['effective_tax'] += effective_tax  # 有效税额
                        data_dict[sub_key]['occupy_inv_amount'] += doc_occupy_inv_amount  # 已占用金额
                    else:
                        data_dict[sub_key] = {
                            'document_number': None,  # 单据编号
                            'state': None,  # 单据状态
                            'inv_type_name': inv_type_name + _('subtotal'),  # 发票类型（展示）
                            'inv_date': None,  # 发票日期
                            'inv_code': None,  # 发票代码
                            'inv_number': None,  # 发票号
                            'contact_dept': None,  # 往来单位（销方）
                            'amount_total': amount_total,  # 不含税金额
                            'tax_total': tax_total,  # 税额
                            'amount_tax_total': amount_tax_total,  # 价税合计
                            'is_deduction': None,  # 抵扣勾选
                            'check_date': None,  # 勾选日期
                            'effective_tax': effective_tax,  # 有效税额
                            'is_declare': None,  # 已申报
                            'declare_date': None,  # 申报日期
                            'is_error': None,  # 是否异常
                            'sett_org_name': None,  # 结算组织（展示）
                            'project_name': None,  # 项目名称（展示）
                            'project_number': None,  # 项目编号
                            'doc_id': None,  # 单据id
                            'doc_model_name': None,  # 单据模型名
                            'source_id': None,  # 引用单据id
                            'source_model_name': None,  # 引用单据模型名
                            'voucher_id': None,  # 凭证id
                            'voucher_model_name': None,  # 凭证模型名
                            'currency_id': None,  # 币别id
                            'occupy_inv_amount': doc_occupy_inv_amount,  # 已占用金额
                            'src_doc_number': None,  # 引用单据
                            'voucher_number': None,  # 凭证号
                            'ref_to_doc': None,  # 穿透到单据action
                            'is_subtotal': True,  # 是否小计
                            'is_total': False,  # 是否合计
                        }

                    # 组织合计数据
                    total_amount_total += amount_total  # 不含税金额（合计）
                    total_tax_total += tax_total  # 税额（合计）
                    total_amount_tax_total += amount_tax_total  # 价税合计（合计）
                    total_effective_tax += effective_tax  # 有效税额（合计）
                    total_occupy_inv_amount += doc_occupy_inv_amount  # 已占用金额（合计）

        else:
            for record in records:

                # 提取公共变量
                inv_type_record = record.inv_type_id  # 发票类型obj
                contact_dept_record = record.contact_dept  # 往来单位（销方）obj
                sett_org_record = record.sett_org_id  # 结算组织obj
                project_record = record.project_id  # 项目名称obj
                src_record = record  # 单据obj
                currency_record = record.currency_id  # 币别obj

                document_number = record.number  # 单据编号
                state = self._get_translate_info('State_Selection')[record.state]  # 单据状态
                inv_type_name = inv_type_record.name  # 发票类型（展示）
                inv_date = record.inv_date  # 发票日期
                inv_code = record.inv_code  # 发票代码
                inv_number = record.inv_number  # 发票号
                contact_dept = contact_dept_record.name  # 往来单位（销方）
                amount_total = record.amount_total  # 不含税金额
                tax_total = record.tax_total  # 税额
                amount_tax_total = record.amount_tax_total  # 价税合计
                doc_occupy_inv_amount = record.occupy_inv_amount # 已占用金额（表头）
                is_deduction = _('True') if record.is_deduction else _('False')  # 抵扣勾选
                check_date = record.check_date if record.check_date else None  # 勾选日期
                is_declare = _('True') if record.is_declare else _('False')  # 已申报
                declare_date = record.declare_date if record.declare_date else None  # 申报日期
                is_error = _('True') if record.is_error else _('False')  # 是否异常
                sett_org_name = sett_org_record.name  # 结算组织（展示）
                project_name = project_record.name if project_record else None  # 项目名称（展示）
                project_number = project_record.number if project_record else None  # 项目编号

                # 特殊处理有效税额字段取值
                is_che_duc = inv_type_record.is_che_duc  # 发票类型（允许抵扣勾选字段）
                if is_che_duc:
                    # 发票类型（允许抵扣勾选=1）
                    effective_tax = record.effective_tax
                else:
                    # 发票类型（允许抵扣勾选=0）
                    effective_tax = record.tax_total
                
                doc_id = src_record.id  # 单据id
                doc_model_name = record._name  # 单据模型名
                currency_id = currency_record.id  # 币别id

                # 定义报表穿透到单据的ref_to_doc
                record_type = record.type  # 分类
                ref_to_doc = None
                if record_type == 'vat_invoice':
                    ref_to_doc = 'ps_iv.action_input_vat_invoice'
                elif record_type == 'vat_general_invoice':
                    ref_to_doc = 'ps_iv.action_common_input_vat_invoice'

                # 根据增值税发票数据组织相关数据
                # 按照发票类型id、发票日期、模型（进项发票模型、差旅费报销单、费用报销单、其他应付单的模型顺序）、表头id、表体发票号
                # 需要注意如果在差旅费报销单、费用报销单、其他应付单模型下可能出现一张单据引用两次相同的发票，则需要汇总【当出现相同模型、相同单据编号、相同发票代码、相同发票号（非增值税票号）的数据时，需要进行汇总展示】
                key_inv_date = 'inv_date_' + str(inv_date)
                key_model_sequence = 'model_sequence_1'
                key_doc_id = 'doc_id_' + str(doc_id).zfill(8)
                key = 'key_' + key_inv_date + '_' + key_model_sequence + '_' + key_doc_id

                if record.line1_doc_ids:
                    # 如果发票有引用，则按照引用展示

                    # 因为是按照发票明细展示数据，因此需要循环发票表头的 line1_doc_ids 获取发票明细数据
                    for index, line in enumerate(record.line1_doc_ids):

                        # 提取公共变量
                        occupy_inv_amount = line.occupy_inv_amount  # 已占用金额
                        src_doc_number = line.document_number if line.document_number else None  # 引用单据
                        source_id = line.source_id  # 来源单据id
                        source_model_name = line.source_model_name  # 来源单据表名
                        voucher_number, voucher_id = self._get_voucher_number(source_id, source_model_name)   # 凭证号/凭证id
                        voucher_model_name = 'gl.voucher'  # 凭证模型名
                        line_id = line.id  # 明细行id
                        source_doc_type_num = line.src_doc_type_id.number

                        # 这里需要在之前组织好的key的基础上加上 doc明细行 id key
                        key_doc_detail_id = 'doc_detail_id_' + str(line_id).zfill(8)
                        line_key = key + '_' + key_doc_detail_id

                        if index == 0:

                            data_dict[line_key] = {
                                'document_number': document_number,  # 单据编号
                                'state': state,  # 单据状态
                                'inv_type_name': inv_type_name,  # 发票类型（展示）
                                'inv_date': inv_date,  # 发票日期
                                'inv_code': inv_code,  # 发票代码
                                'inv_number': inv_number,  # 发票号
                                'contact_dept': contact_dept,  # 往来单位（销方）
                                'amount_total': amount_total,  # 不含税金额
                                'tax_total': tax_total,  # 税额
                                'amount_tax_total': amount_tax_total,  # 价税合计
                                'is_deduction': is_deduction,  # 抵扣勾选
                                'check_date': check_date,  # 勾选日期
                                'effective_tax': effective_tax,  # 有效税额
                                'is_declare': is_declare,  # 已申报
                                'declare_date': declare_date,  # 申报日期
                                'is_error': is_error,  # 是否异常
                                'sett_org_name': sett_org_name,  # 结算组织（展示）
                                'project_name': project_name,  # 项目名称（展示）
                                'project_number': project_number,  # 项目编号
                                'occupy_inv_amount': occupy_inv_amount,  # 已占用金额
                                'src_doc_number': src_doc_number,  # 引用单据
                                'voucher_number': voucher_number,  # 凭证号
                                'doc_id': doc_id,  # 单据id
                                'doc_model_name': doc_model_name,  # 单据模型名
                                'source_id': source_id,  # 引用单据id
                                'source_model_name': source_model_name,  # 引用单据模型名
                                'voucher_id': voucher_id,  # 凭证id
                                'voucher_model_name': voucher_model_name,  # 凭证模型名
                                'currency_id': currency_id,  # 币别id
                                'ref_to_doc': ref_to_doc,  # 穿透到单据action
                                'is_subtotal': False,  # 是否小计
                                'is_total': False,  # 是否合计
                                'source_doc_type_num': source_doc_type_num,
                            }
                        else:
                            data_dict[line_key] = {
                                'document_number': None,  # 单据编号
                                'state': None,  # 单据状态
                                'inv_type_name': None,  # 发票类型（展示）
                                'inv_date': None,  # 发票日期
                                'inv_code': None,  # 发票代码
                                'inv_number': None,  # 发票号
                                'contact_dept': None,  # 往来单位（销方）
                                'amount_total': None,  # 不含税金额
                                'tax_total': None,  # 税额
                                'amount_tax_total': None,  # 价税合计
                                'is_deduction': None,  # 抵扣勾选
                                'check_date': None,  # 勾选日期
                                'effective_tax': None,  # 有效税额
                                'is_declare': None,  # 已申报
                                'declare_date': None,  # 申报日期
                                'is_error': None,  # 是否异常
                                'sett_org_name': None,  # 结算组织（展示）
                                'project_name': None,  # 项目名称（展示）
                                'project_number': None,  # 项目编号
                                'occupy_inv_amount': occupy_inv_amount,  # 已占用金额
                                'src_doc_number': src_doc_number,  # 引用单据
                                'voucher_number': voucher_number,  # 凭证号
                                'doc_id': None,  # 单据id
                                'doc_model_name': None,  # 单据模型名
                                'source_id': source_id,  # 引用单据id
                                'source_model_name': source_model_name,  # 引用单据模型名
                                'voucher_id': voucher_id,  # 凭证id
                                'voucher_model_name': voucher_model_name,  # 凭证模型名
                                'currency_id': currency_id,  # 币别id
                                'ref_to_doc': ref_to_doc,  # 穿透到单据action
                                'is_subtotal': False,  # 是否小计
                                'is_total': False,  # 是否合计
                                'source_doc_type_num': source_doc_type_num,
                            }

                    # 组织合计数据
                    total_amount_total += amount_total  # 不含税金额（合计）
                    total_tax_total += tax_total  # 税额（合计）
                    total_amount_tax_total += amount_tax_total  # 价税合计（合计）
                    total_effective_tax += effective_tax  # 有效税额（合计）
                    total_occupy_inv_amount += doc_occupy_inv_amount  # 已占用金额（合计）

                else:
                    # 发票没有引用，则按照整单展示

                    # 提取公共变量
                    occupy_inv_amount = doc_occupy_inv_amount # 已占用金额
                    src_doc_number = document_number  # 引用单据
                    source_id = doc_id  # 来源单据id
                    source_model_name = doc_model_name  # 来源单据表名

                    data_dict[key] = {
                        'document_number': document_number,  # 单据编号
                        'state': state,  # 单据状态
                        'inv_type_name': inv_type_name,  # 发票类型（展示）
                        'inv_date': inv_date,  # 发票日期
                        'inv_code': inv_code,  # 发票代码
                        'inv_number': inv_number,  # 发票号
                        'contact_dept': contact_dept,  # 往来单位（销方）
                        'amount_total': amount_total,  # 不含税金额
                        'tax_total': tax_total,  # 税额
                        'amount_tax_total': amount_tax_total,  # 价税合计
                        'is_deduction': is_deduction,  # 抵扣勾选
                        'check_date': check_date,  # 勾选日期
                        'effective_tax': effective_tax,  # 有效税额
                        'is_declare': is_declare,  # 已申报
                        'declare_date': declare_date,  # 申报日期
                        'is_error': is_error,  # 是否异常
                        'sett_org_name': sett_org_name,  # 结算组织（展示）
                        'project_name': project_name,  # 项目名称（展示）
                        'project_number': project_number,  # 项目编号
                        'occupy_inv_amount': occupy_inv_amount,  # 已占用金额
                        'src_doc_number': None,  # 引用单据
                        'voucher_number': None,  # 凭证号
                        'doc_id': doc_id,  # 单据id
                        'doc_model_name': doc_model_name,  # 单据模型名
                        'source_id': None,  # 引用单据id
                        'source_model_name': None,  # 引用单据模型名
                        'voucher_id': None,  # 凭证id
                        'voucher_model_name': None,  # 凭证模型名
                        'currency_id': currency_id,  # 币别id
                        'ref_to_doc': ref_to_doc,  # 穿透到单据action
                        'is_subtotal': False,  # 是否小计
                        'is_total': False,  # 是否合计
                    }

                    # 组织合计数据
                    total_amount_total += amount_total  # 不含税金额（合计）
                    total_tax_total += tax_total  # 税额（合计）
                    total_amount_tax_total += amount_tax_total  # 价税合计（合计）
                    total_effective_tax += effective_tax  # 有效税额（合计）
                    total_occupy_inv_amount += doc_occupy_inv_amount  # 已占用金额（合计）
        
        if data_dict:
            data_dict['total_all'] = {
                'document_number': None,  # 单据编号
                'state': None,  # 单据状态
                'inv_type_name': _('total'),  # 发票类型（展示）
                'inv_date': None,  # 发票日期
                'inv_code': None,  # 发票代码
                'inv_number': None,  # 发票号
                'contact_dept': None,  # 往来单位（销方）
                'amount_total': total_amount_total,  # 不含税金额
                'tax_total': total_tax_total,  # 税额
                'amount_tax_total': total_amount_tax_total,  # 价税合计
                'is_deduction': None,  # 抵扣勾选
                'check_date': None,  # 勾选日期
                'effective_tax': total_effective_tax,  # 有效税额
                'is_declare': None,  # 已申报
                'declare_date': None,  # 申报日期
                'is_error': None,  # 是否异常
                'sett_org_name': None,  # 结算组织（展示）
                'project_name': None,  # 项目名称（展示）
                'project_number': None,  # 项目编号
                'doc_id': None,  # 单据id
                'currency_id': None,  # 币别id
                'doc_model_name': None,  # 单据模型名
                'source_id': None,  # 引用单据id
                'source_model_name': None,  # 引用单据模型名
                'voucher_id': None,  # 凭证id
                'voucher_model_name': None,  # 凭证模型名
                'occupy_inv_amount': total_occupy_inv_amount,  # 已占用金额
                'src_doc_number': None,  # 引用单据
                'voucher_number': None,  # 凭证号
                'ref_to_doc': None,  # 穿透到单据action
                'is_subtotal': False,  # 是否小计
                'is_total': True,  # 是否合计
            }

        return data_dict

    def _get_travel_expense_payable_line_data(self, records, data_dict, domain_fields, model_name_key=None):
        """
        组织整理相关模型数据字典
            差旅费报销单模型
            费用报销单模型
            其他应付单模型
        :param:
            self: 当前实例对象
            records: 进项发票模型相关记录
            data_dict: 数据汇总字典（含汇总key）
            domain_fields: 字段选择过滤条件
            model_name_key: ['travel', 'expense', 'payable'] 根据不同的 model_name_key 获取不同的公共变量
        :return:
            data_dict: 组织好的数据创建相关记录（含汇总key）
        """
        # 提取公共变量
        is_type_total = domain_fields['is_type_total']
        total_amount_total = data_dict['total_all']['amount_total'] if data_dict.get('total_all') else 0  # 不含税金额（合计）
        total_tax_total = data_dict['total_all']['tax_total'] if data_dict.get('total_all') else 0  # 税额（合计）
        total_amount_tax_total = data_dict['total_all']['amount_tax_total'] if data_dict.get('total_all') else 0  # 价税合计（合计）
        total_effective_tax = data_dict['total_all']['effective_tax'] if data_dict.get('total_all') else 0  # 有效税额（合计）
        total_occupy_inv_amount = data_dict['total_all']['occupy_inv_amount'] if data_dict.get('total_all') else 0  # 已占用金额（合计）

        # 判断是否按发票类型汇总
        if is_type_total:
            for record in records:

                # 提取公共变量
                com_dict = self._get_travel_expense_payable_com_variable(record, model_name_key)
                document_number = com_dict['document_number']  # 单据编号
                state = self._get_translate_info('State_Selection')[com_dict['state']]  # 单据状态
                inv_type_name = com_dict['inv_type_name']  # 发票类型（展示）
                inv_date = com_dict['inv_date']  # 发票日期
                inv_code = com_dict['inv_code']  # 发票代码
                inv_number = com_dict['inv_number']  # 发票号
                contact_dept = com_dict['contact_dept']  # 往来单位（销方）
                amount_total = com_dict['amount_total']  # 不含税金额
                tax_total = com_dict['tax_total']  # 税额
                tax_rate = com_dict['tax_rate']  # 税率（%）
                amount_tax_total = com_dict['amount_tax_total']  # 价税合计
                effective_tax = com_dict['effective_tax']  # 有效税额
                is_declare = com_dict['is_declare']  # 已申报
                declare_date = com_dict['declare_date']  # 申报日期
                sett_org_name = com_dict['sett_org_name']  # 结算组织（展示）
                project_name = com_dict['project_name']  # 项目名称（展示）
                project_number = com_dict['project_number']  # 项目编号
                occupy_inv_amount = com_dict['occupy_inv_amount']  # 已占用金额
                src_doc_number = com_dict['src_doc_number']  # 引用单据
                voucher_number = com_dict['voucher_number']  # 凭证号
                doc_id = com_dict['doc_id']  # 单据id
                doc_model_name = com_dict['doc_model_name']  # 单据模型名
                source_id = com_dict['source_id']  # 引用单据id
                source_model_name = com_dict['source_model_name']  # 引用单据模型名
                voucher_id = com_dict['voucher_id']  # 凭证id
                voucher_model_name = com_dict['voucher_model_name']  # 凭证模型名
                currency_id = com_dict['currency_id']  # 币别id
                inv_type_id = com_dict['inv_type_id']  # 发票类型id
                ref_to_doc = com_dict['ref_to_doc']  # 定义报表穿透到单据的ref_to_doc
                model_sequence = com_dict['model_sequence']  # 差旅费报销单模型、费用报销单模型、其他应付单模型，分别对应2、3、4

                # 根据增值税发票数据组织相关数据
                # 按照发票类型id、发票日期、模型（进项发票模型、差旅费报销单、费用报销单、其他应付单的模型顺序）排序
                # 需要注意如果在差旅费报销单、费用报销单、其他应付单模型下可能出现一张单据引用两次相同的发票，则需要汇总【当出现相同模型、相同单据编号、相同发票代码、相同发票号（非增值税票号）的数据时，需要进行汇总展示】
                key_inv_type_id = 'inv_type_id_' + str(inv_type_id).zfill(8)
                key_inv_date = 'inv_date_' + str(inv_date)
                key_model_sequence = model_sequence
                key_doc_id = 'doc_id_' + str(doc_id).zfill(8)
                key_inv_number = 'inv_number_' + inv_number
                key = 'key_' + key_inv_type_id + '_' + key_inv_date + '_' + key_model_sequence + '_' + key_doc_id + '_' + key_inv_number

                if data_dict.get(key):
                    data_dict[key]['amount_total'] += amount_total  # 不含税金额
                    data_dict[key]['tax_total'] += tax_total  # 税额
                    data_dict[key]['amount_tax_total'] += amount_tax_total  # 价税合计
                    data_dict[key]['effective_tax'] += effective_tax  # 有效税额
                    data_dict[key]['occupy_inv_amount'] += occupy_inv_amount  # 已占用金额
                
                data_dict[key] = {
                    'document_number': document_number,  # 单据编号
                    'state': state,  # 单据状态
                    'inv_type_name': inv_type_name,  # 发票类型（展示）
                    'inv_date': inv_date,  # 发票日期
                    'inv_code': inv_code,  # 发票代码
                    'inv_number': inv_number,  # 发票号
                    'contact_dept': contact_dept,  # 往来单位（销方）
                    'material_name': None,  # 发票项目
                    'specification': None,  # 规格型号
                    'unit_name': None,  # 计价单位
                    'qty': None,  # 计价数量
                    'unit_price_tax': None,  # 含税单价
                    'unit_price': None,  # 单价
                    'amount': amount_total,  # 不含税金额
                    'tax': tax_total,  # 税额
                    'amount_tax': amount_tax_total,  # 价税合计
                    'tax_rate': tax_rate,  # 税率（%）
                    'amount_total': amount_total,  # 不含税金额
                    'tax_total': tax_total,  # 税额
                    'amount_tax_total': amount_tax_total,  # 价税合计
                    'is_deduction': _('False'),  # 抵扣勾选
                    'check_date': None,  # 勾选日期
                    'effective_tax': effective_tax,  # 有效税额
                    'is_declare': is_declare,  # 已申报
                    'declare_date': declare_date,  # 申报日期
                    'is_error': _('False'),  # 是否异常
                    'sett_org_name': sett_org_name,  # 结算组织（展示）
                    'project_name': project_name,  # 项目名称（展示）
                    'project_number': project_number,  # 项目编号
                    'occupy_inv_amount': occupy_inv_amount,  # 已占用金额
                    'src_doc_number': src_doc_number,  # 引用单据
                    'voucher_number': voucher_number,  # 凭证号
                    'doc_id': doc_id,  # 单据id
                    'doc_model_name': doc_model_name,  # 单据模型名
                    'source_id': source_id,  # 引用单据id
                    'source_model_name': source_model_name,  # 引用单据模型名
                    'voucher_id': voucher_id,  # 凭证id
                    'voucher_model_name': voucher_model_name,  # 凭证模型名
                    'currency_id': currency_id,  # 币别id
                    'ref_to_doc': ref_to_doc,  # 穿透到单据action
                    'is_subtotal': False,  # 是否小计
                    'is_total': False,  # 是否合计
                }

                # 组织小计数据
                sub_key = 'key_' + key_inv_type_id + '_subtotal'
                
                if data_dict.get(sub_key):
                    data_dict[sub_key]['amount_total'] += amount_total  # 不含税金额
                    data_dict[sub_key]['tax_total'] += tax_total  # 税额
                    data_dict[sub_key]['amount_tax_total'] += amount_tax_total  # 价税合计
                    data_dict[sub_key]['effective_tax'] += effective_tax  # 有效税额
                    data_dict[sub_key]['occupy_inv_amount'] += occupy_inv_amount  # 已占用金额
                else:
                    data_dict[sub_key] = {
                        'document_number': None,  # 单据编号
                        'state': None,  # 单据状态
                        'inv_type_name': inv_type_name + _('subtotal'),  # 发票类型（展示）
                        'inv_date': None,  # 发票日期
                        'inv_code': None,  # 发票代码
                        'inv_number': None,  # 发票号
                        'contact_dept': None,  # 往来单位（销方）
                        'material_name': None,  # 发票项目
                        'specification': None,  # 规格型号
                        'unit_name': None,  # 计价单位
                        'qty': None,  # 计价数量
                        'unit_price_tax': None,  # 含税单价
                        'unit_price': None,  # 单价
                        'amount': amount_total,  # 不含税金额
                        'tax': tax_total,  # 税额
                        'amount_tax': amount_tax_total,  # 价税合计
                        'tax_rate': None,  # 税率（%）
                        'amount_total': amount_total,  # 不含税金额
                        'tax_total': tax_total,  # 税额
                        'amount_tax_total': amount_tax_total,  # 价税合计
                        'is_deduction': None,  # 抵扣勾选
                        'check_date': None,  # 勾选日期
                        'effective_tax': effective_tax,  # 有效税额
                        'is_declare': None,  # 已申报
                        'declare_date': None,  # 申报日期
                        'is_error': None,  # 是否异常
                        'sett_org_name': None,  # 结算组织（展示）
                        'project_name': None,  # 项目名称（展示）
                        'project_number': None,  # 项目编号
                        'occupy_inv_amount': occupy_inv_amount,  # 已占用金额
                        'src_doc_number': None,  # 引用单据
                        'voucher_number': None,  # 凭证号
                        'doc_id': None,  # 单据id
                        'doc_model_name': None,  # 单据模型名
                        'source_id': None,  # 引用单据id
                        'source_model_name': None,  # 引用单据模型名
                        'voucher_id': None,  # 凭证id
                        'voucher_model_name': None,  # 凭证模型名
                        'currency_id': None,  # 币别id
                        'ref_to_doc': None,  # 穿透到单据action
                        'is_subtotal': True,  # 是否小计
                        'is_total': False,  # 是否合计
                    }

                # 组织合计数据
                total_amount_total += amount_total  # 不含税金额（合计）
                total_tax_total += tax_total  # 税额（合计）
                total_amount_tax_total += amount_tax_total  # 价税合计（合计）
                total_effective_tax += effective_tax  # 有效税额（合计）
                total_occupy_inv_amount += occupy_inv_amount  # 已占用金额（合计）

        else:
            for record in records:

                # 提取公共变量
                com_dict = self._get_travel_expense_payable_com_variable(record, model_name_key)
                document_number = com_dict['document_number']  # 单据编号
                state = self._get_translate_info('State_Selection')[com_dict['state']]  # 单据状态
                inv_type_name = com_dict['inv_type_name']  # 发票类型（展示）
                inv_date = com_dict['inv_date']  # 发票日期
                inv_code = com_dict['inv_code']  # 发票代码
                inv_number = com_dict['inv_number']  # 发票号
                contact_dept = com_dict['contact_dept']  # 往来单位（销方）
                amount_total = com_dict['amount_total']  # 不含税金额
                tax_total = com_dict['tax_total']  # 税额
                tax_rate = com_dict['tax_rate']  # 税率（%）
                amount_tax_total = com_dict['amount_tax_total']  # 价税合计
                effective_tax = com_dict['effective_tax']  # 有效税额
                is_declare = com_dict['is_declare']  # 已申报
                declare_date = com_dict['declare_date']  # 申报日期
                sett_org_name = com_dict['sett_org_name']  # 结算组织（展示）
                project_name = com_dict['project_name']  # 项目名称（展示）
                project_number = com_dict['project_number']  # 项目编号
                occupy_inv_amount = com_dict['occupy_inv_amount']  # 已占用金额
                src_doc_number = com_dict['src_doc_number']  # 引用单据
                voucher_number = com_dict['voucher_number']  # 凭证号
                doc_id = com_dict['doc_id']  # 单据id
                doc_model_name = com_dict['doc_model_name']  # 单据模型名
                source_id = com_dict['source_id']  # 引用单据id
                source_model_name = com_dict['source_model_name']  # 引用单据模型名
                voucher_id = com_dict['voucher_id']  # 凭证id
                voucher_model_name = com_dict['voucher_model_name']  # 凭证模型名
                currency_id = com_dict['currency_id']  # 币别id
                inv_type_id = com_dict['inv_type_id']  # 发票类型id
                ref_to_doc = com_dict['ref_to_doc']  # 定义报表穿透到单据的ref_to_doc
                model_sequence = com_dict['model_sequence']  # 差旅费报销单模型、费用报销单模型、其他应付单模型，分别对应2、3、4
                doc_type_num = com_dict.get('doc_type_num','')
                # 根据增值税发票数据组织相关数据
                # 按照发票类型id、发票日期、模型（进项发票模型、差旅费报销单、费用报销单、其他应付单的模型顺序）、表头id、表体发票号
                # 需要注意如果在差旅费报销单、费用报销单、其他应付单模型下可能出现一张单据引用两次相同的发票，则需要汇总【当出现相同模型、相同单据编号、相同发票代码、相同发票号（非增值税票号）的数据时，需要进行汇总展示】
                key_inv_date = 'inv_date_' + str(inv_date)
                key_model_sequence = model_sequence
                key_doc_id = 'doc_id_' + str(doc_id).zfill(8)
                key_inv_number = 'inv_number_' + inv_number
                key = 'key_' + key_inv_date + '_' + key_model_sequence + '_' + key_doc_id + '_' + key_inv_number

                data_dict[key] = {
                    'document_number': document_number,  # 单据编号
                    'state': state,  # 单据状态
                    'inv_type_name': inv_type_name,  # 发票类型（展示）
                    'inv_date': inv_date,  # 发票日期
                    'inv_code': inv_code,  # 发票代码
                    'inv_number': inv_number,  # 发票号
                    'contact_dept': contact_dept,  # 往来单位（销方）
                    'material_name': None,  # 发票项目
                    'specification': None,  # 规格型号
                    'unit_name': None,  # 计价单位
                    'qty': None,  # 计价数量
                    'unit_price_tax': None,  # 含税单价
                    'unit_price': None,  # 单价
                    'amount': amount_total,  # 不含税金额
                    'tax': tax_total,  # 税额
                    'amount_tax': amount_tax_total,  # 价税合计
                    'tax_rate': tax_rate,  # 税率（%）
                    'amount_total': amount_total,  # 不含税金额
                    'tax_total': tax_total,  # 税额
                    'amount_tax_total': amount_tax_total,  # 价税合计
                    'is_deduction': _('False'),  # 抵扣勾选
                    'check_date': None,  # 勾选日期
                    'effective_tax': effective_tax,  # 有效税额
                    'is_declare': is_declare,  # 已申报
                    'declare_date': declare_date,  # 申报日期
                    'is_error': _('False'),  # 是否异常
                    'sett_org_name': sett_org_name,  # 结算组织（展示）
                    'project_name': project_name,  # 项目名称（展示）
                    'project_number': project_number,  # 项目编号
                    'occupy_inv_amount': occupy_inv_amount,  # 已占用金额
                    'src_doc_number': src_doc_number,  # 引用单据
                    'voucher_number': voucher_number,  # 凭证号
                    'doc_id': doc_id,  # 单据id
                    'doc_model_name': doc_model_name,  # 单据模型名
                    'source_id': source_id,  # 引用单据id
                    'source_model_name': source_model_name,  # 引用单据模型名
                    'voucher_id': voucher_id,  # 凭证id
                    'voucher_model_name': voucher_model_name,  # 凭证模型名
                    'currency_id': currency_id,  # 币别id
                    'ref_to_doc': ref_to_doc,  # 穿透到单据action
                    'is_subtotal': False,  # 是否小计
                    'is_total': False,  # 是否合计
                    'source_doc_type_num': doc_type_num,
                }

                # 组织合计数据
                total_amount_total += amount_total  # 不含税金额（合计）
                total_tax_total += tax_total  # 税额（合计）
                total_amount_tax_total += amount_tax_total  # 价税合计（合计）
                total_effective_tax += effective_tax  # 有效税额（合计）
                total_occupy_inv_amount += occupy_inv_amount  # 已占用金额（合计）
        
        if data_dict:
            data_dict['total_all'] = {
                'document_number': None,  # 单据编号
                'state': None,  # 单据状态
                'inv_type_name': _('total'),  # 发票类型（展示）
                'inv_date': None,  # 发票日期
                'inv_code': None,  # 发票代码
                'inv_number': None,  # 发票号
                'contact_dept': None,  # 往来单位（销方）
                'material_name': None,  # 发票项目
                'specification': None,  # 规格型号
                'unit_name': None,  # 计价单位
                'qty': None,  # 计价数量
                'unit_price_tax': None,  # 含税单价
                'unit_price': None,  # 单价
                'amount': total_amount_total,  # 不含税金额
                'tax': total_tax_total,  # 税额
                'amount_tax': total_amount_tax_total,  # 价税合计
                'tax_rate': None,  # 税率（%）
                'amount_total': total_amount_total,  # 不含税金额
                'tax_total': total_tax_total,  # 税额
                'amount_tax_total': total_amount_tax_total,  # 价税合计
                'is_deduction': None,  # 抵扣勾选
                'check_date': None,  # 勾选日期
                'effective_tax': total_effective_tax,  # 有效税额
                'is_declare': None,  # 已申报
                'declare_date': None,  # 申报日期
                'is_error': None,  # 是否异常
                'sett_org_name': None,  # 结算组织（展示）
                'project_name': None,  # 项目名称（展示）
                'project_number': None,  # 项目编号
                'occupy_inv_amount': total_occupy_inv_amount,  # 已占用金额
                'src_doc_number': None,  # 引用单据
                'voucher_number': None,  # 凭证号
                'doc_id': None,  # 单据id
                'doc_model_name': None,  # 单据模型名
                'source_id': None,  # 引用单据id
                'source_model_name': None,  # 引用单据模型名
                'voucher_id': None,  # 凭证id
                'voucher_model_name': None,  # 凭证模型名
                'currency_id': None,  # 币别id
                'ref_to_doc': None,  # 穿透到单据action
                'is_subtotal': False,  # 是否小计
                'is_total': True,  # 是否合计
            }

        return data_dict
    
    def _get_expense_action(self, doc_type_num):
        """
        差旅费报销单模型、费用报销单模型返回跳转动作
        农银金科
        :param:
            self: 当前实例对象
            doc_type_num: 单据类型编码
        :return:
            key: 单据类型编码对应跳转动作
        """
        for key, value in ENTER_TYPE_DICT.items():
            if doc_type_num in value:
                return key

    def _get_travel_expense_payable_com_variable(self, record, model_name_key=None):
        """
        差旅费报销单模型、费用报销单模型、其他应付单模型，公共变量提取函数
        :param:
            self: 当前实例对象
            record: 差旅费报销单模型、费用报销单模型、其他应付单模型单条记录
            model_name_key: ['travel', 'expense', 'payable'] 根据不同的 model_name_key 获取不同的公共变量
        :return:
            common_variable_dict: 组织好的不同模型的公共变量
        """
        common_variable_dict = dict()

        if model_name_key == 'travel':
            # 提取公共变量
            parent_record = record.parent_id.parent_id  # 关联表头obj
            inv_type_record = record.inv_type_id  # 发票类型obj
            sett_org_record = parent_record.exp_org_id  # 结算组织obj
            project_record = parent_record.project_id  # 项目名称obj
            src_record = parent_record  # 单据obj
            currency_record = parent_record.currency_id  # 币别obj

            # 特殊处理凭证号获取逻辑
            voucher_number, voucher_id = self._get_voucher_number(parent_record.id, parent_record._name)   # 凭证号/凭证id
            voucher_model_name = 'gl.voucher'  # 凭证模型名

            common_variable_dict = {
                'parent_record': record.parent_id.parent_id,  # 关联表头obj
                'inv_type_record': record.inv_type_id,  # 发票类型obj
                'sett_org_record': parent_record.exp_org_id,  # 结算组织obj
                'project_record': parent_record.project_id,  # 项目名称obj
                'src_record': parent_record,  # 单据obj
                'currency_record': parent_record.currency_id,  # 币别obj
                'document_number': parent_record.number,  # 单据编号
                'state': parent_record.state,  # 单据状态
                'inv_type_name': inv_type_record.name,  # 发票类型（展示）
                'inv_date': record.exp_date,  # 发票日期
                'inv_code': record.inv_code if record.inv_code else None,  # 发票代码
                'inv_number': record.ticket_number if record.ticket_number else None,  # 发票号
                'contact_dept': None,  # 往来单位（销方）
                'amount_total': record.exp_amount,  # 不含税金额
                'tax_total': record.tax,  # 税额
                'tax_rate': record.tax_rate,  # 税率（%）
                'amount_tax_total': record.aprv_amount,  # 价税合计
                'effective_tax': record.tax,  # 有效税额
                'is_declare': _('True') if record.is_declare else _('False'),  # 已申报
                'declare_date': record.declare_date if record.declare_date else None,  # 申报日期
                'sett_org_name': sett_org_record.name,  # 结算组织（展示）
                'project_name': project_record.name if project_record else None,  # 项目名称（展示）
                'project_number': project_record.number if project_record else None,  # 项目编号
                'occupy_inv_amount': record.req_amount,  # 已占用金额
                'src_doc_number': parent_record.number,  # 引用单据
                'voucher_number': voucher_number,  # 凭证号
                'doc_id': src_record.id,  # 单据id
                'doc_model_name': parent_record._name,  # 单据模型名
                'source_id': src_record.id,  # 引用单据id
                'source_model_name': parent_record._name,  # 引用单据模型名
                'voucher_id': voucher_id,  # 凭证id
                'voucher_model_name': voucher_model_name,  # 凭证模型名
                'currency_id': currency_record.id,  # 币别id
                'inv_type_id': inv_type_record.id,  # 发票类型id
                # 'ref_to_doc': 'ps_er.action_er_travel',  # 定义报表穿透到单据的ref_to_doc
                'ref_to_doc': 'ps_er.action_business_trip',
                'model_sequence': 'model_sequence_2',  # 差旅费报销单模型、费用报销单模型、其他应付单模型，分别对应2、3、4
            }

        elif model_name_key == 'expense':
            # 提取公共变量
            parent_record = record.parent_id  # 关联表头obj
            inv_type_record = record.inv_type_id  # 发票类型obj
            sett_org_record = parent_record.exp_org_id  # 结算组织obj
            project_record = parent_record.project_id  # 项目名称obj
            src_record = parent_record  # 单据obj
            currency_record = parent_record.currency_id  # 币别obj

            # # TODO 单据类型
            doc_type_num = parent_record.doc_type_num
            # # 特殊处理根据单据类型找到不同的action进行跳转
            # # TODO:
            action = self._get_expense_action(doc_type_num)


            # 特殊处理凭证号获取逻辑
            voucher_number, voucher_id = self._get_voucher_number(parent_record.id, parent_record._name)   # 凭证号/凭证id
            voucher_model_name = 'gl.voucher'  # 凭证模型名

            common_variable_dict = {
                'parent_record': parent_record,  # 关联表头obj
                'inv_type_record': inv_type_record,  # 发票类型obj
                'sett_org_record': sett_org_record,  # 结算组织obj
                'project_record': project_record,  # 项目名称obj
                'src_record': src_record,  # 单据obj
                'currency_record': currency_record,  # 币别obj
                'document_number': parent_record.number,  # 单据编号
                'state': parent_record.state,  # 单据状态
                'inv_type_name': inv_type_record.name,  # 发票类型（展示）
                'inv_date': record.exp_date,  # 发票日期
                'inv_code': record.inv_code if record.inv_code else None,  # 发票代码
                'inv_number': record.non_vat_num if record.non_vat_num else None,  # 发票号
                'contact_dept': None,  # 往来单位（销方）
                'amount_total': record.exp_amount,  # 不含税金额
                'tax_total': record.tax,  # 税额
                'tax_rate': record.tax_rate,  # 税率（%）
                'amount_tax_total': record.aprv_amount,  # 价税合计
                'effective_tax': record.tax,  # 有效税额
                'is_declare': _('True') if record.is_declare else _('False'),  # 已申报
                'declare_date': record.declare_date if record.declare_date else None,  # 申报日期
                'sett_org_name': sett_org_record.name,  # 结算组织（展示）
                'project_name': project_record.name if project_record else None,  # 项目名称（展示）
                'project_number': project_record.number if project_record else None,  # 项目编号
                'occupy_inv_amount': record.req_amount,  # 已占用金额
                'src_doc_number': parent_record.number,  # 引用单据
                'voucher_number': voucher_number,  # 凭证号
                'doc_id': src_record.id,  # 单据id
                'doc_model_name': parent_record._name,  # 单据模型名
                'source_id': src_record.id,  # 引用单据id
                'source_model_name': parent_record._name,  # 引用单据模型名
                'voucher_id': voucher_id,  # 凭证id
                'voucher_model_name': voucher_model_name,  # 凭证模型名
                'currency_id': currency_record.id,  # 币别id
                'inv_type_id': inv_type_record.id,  # 发票类型id
                'ref_to_doc': 'ps_er.' + action,  # 定义报表穿透到单据的ref_to_doc
                'model_sequence': 'model_sequence_3',  # 差旅费报销单模型、费用报销单模型、其他应付单模型，分别对应2、3、4
                'doc_type_num': doc_type_num
            }

        elif model_name_key == 'payable':

            # 提取公共变量
            parent_record = record.parent_id  # 关联表头obj
            inv_type_record = record.inv_type_id  # 发票类型obj
            contact_dept_record = parent_record.contact_dept  # 往来单位（销方）obj
            sett_org_record = parent_record.sett_org_id  # 结算组织obj
            project_record = parent_record.project_id  # 项目名称obj
            src_record = parent_record  # 单据obj
            currency_record = parent_record.currency_id  # 币别obj

            # 特殊处理凭证号获取逻辑
            voucher_number, voucher_id = self._get_voucher_number(parent_record.id, parent_record._name)   # 凭证号/凭证id
            voucher_model_name = 'gl.voucher'  # 凭证模型名

            common_variable_dict = {
                'parent_record': parent_record,  # 关联表头obj
                'inv_type_record': inv_type_record,  # 发票类型obj
                'contact_dept_record': contact_dept_record,  # 往来单位（销方）obj
                'sett_org_record': sett_org_record,  # 结算组织obj
                'project_record': project_record,  # 项目名称obj
                'src_record': src_record,  # 单据obj
                'currency_record': parent_record.currency_id,  # 币别obj
                'document_number': parent_record.number,  # 单据编号
                'state': parent_record.state,  # 单据状态
                'inv_type_name': inv_type_record.name,  # 发票类型（展示）
                'inv_date': parent_record.biz_date,  # 发票日期
                'inv_code': record.inv_code if record.inv_code else None,  # 发票代码
                'inv_number': record.non_vat_num if record.non_vat_num else None,  # 发票号
                'contact_dept': contact_dept_record.name if contact_dept_record else None,  # 往来单位（销方）
                'amount_total': record.amount,  # 不含税金额
                'tax_total': record.tax,  # 税额
                'tax_rate': record.tax_rate,  # 税率（%）
                'amount_tax_total': record.subtotal,  # 价税合计
                'effective_tax': record.tax,  # 有效税额
                'is_declare': _('True') if record.is_declare else _('False'),  # 已申报
                'declare_date': record.declare_date if record.declare_date else None,  # 申报日期
                'sett_org_name': sett_org_record.name,  # 结算组织（展示）
                'project_name': project_record.name if project_record else None,  # 项目名称（展示）
                'project_number': project_record.number if project_record else None,  # 项目编号
                'occupy_inv_amount': record.subtotal,  # 已占用金额
                'src_doc_number': parent_record.number,  # 引用单据
                'voucher_number': voucher_number,  # 凭证号                
                'doc_id': src_record.id,  # 单据id
                'doc_model_name': parent_record._name,  # 单据模型名
                'source_id': src_record.id,  # 引用单据id
                'source_model_name': parent_record._name,  # 引用单据模型名
                'voucher_id': voucher_id,  # 凭证id
                'voucher_model_name': voucher_model_name,  # 凭证模型名
                'currency_id': currency_record.id,  # 币别id
                'inv_type_id': inv_type_record.id,  # 发票类型id
                'ref_to_doc': 'ps_er.action_ap_other_payable',  # 定义报表穿透到单据的ref_to_doc
                'model_sequence': 'model_sequence_4',  # 差旅费报销单模型、费用报销单模型、其他应付单模型，分别对应2、3、4
            }

        return common_variable_dict

    def _organization_query_cells(self, domain_fields, data_dict, data_key_list):
        """
        将组织好的数据插入到表格中
        :param:
            self: 当前实例对象
            domain_fields: 字段选择过滤条件
            data_dict: 数据汇总字典
            data_key_list: 数据汇总字典的key排序列表
        :return:
            records: 进项发票模型相关记录
        """
        query_cells = list()  # 定义需要组织的表格
        event_data = dict()  # 定义穿透、右键等操作事件
        model_list = list()  # 模型列表
        double_click_params = self._get_double_click_params(domain_fields)

        if domain_fields['is_show_detail']:
            # 将组织好的数据汇总字典插入到表格中
            for index, key in enumerate(data_key_list):
                query_cells.append(QueryCell(index, 0, data_dict[key]['document_number'], style=CLICK_STYLE))  # 单据编号
                query_cells.append(QueryCell(index, 1, data_dict[key]['state']))  # 单据状态
                query_cells.append(QueryCell(index, 2, data_dict[key]['inv_type_name']))  # 发票类型（展示）
                query_cells.append(QueryCell(index, 3, data_dict[key]['inv_date']))  # 发票日期
                query_cells.append(QueryCell(index, 4, data_dict[key]['inv_code']))  # 发票代码
                query_cells.append(QueryCell(index, 5, data_dict[key]['inv_number']))  # 发票号
                query_cells.append(QueryCell(index, 6, data_dict[key]['contact_dept']))  # 往来单位（销方）
                query_cells.append(QueryCell(index, 7, data_dict[key]['material_name']))  # 发票项目
                query_cells.append(QueryCell(index, 8, data_dict[key]['specification']))  # 规格型号
                query_cells.append(QueryCell(index, 9, data_dict[key]['unit_name']))  # 计价单位（展示）
                query_cells.append(QueryCell(index, 10, data_dict[key]['qty']))  # 计价数量
                query_cells.append(QueryCell(index, 11, data_dict[key]['unit_price_tax']))  # 含税单价
                query_cells.append(QueryCell(index, 12, data_dict[key]['unit_price']))  # 单价
                query_cells.append(QueryCell(index, 13, data_dict[key]['amount']))  # 不含税金额
                query_cells.append(QueryCell(index, 14, data_dict[key]['tax_rate']))  # 税率（%）
                query_cells.append(QueryCell(index, 15, data_dict[key]['tax']))  # 税额
                query_cells.append(QueryCell(index, 16, data_dict[key]['amount_tax']))  # 价税合计
                query_cells.append(QueryCell(index, 17, data_dict[key]['is_deduction']))  # 抵扣勾选
                query_cells.append(QueryCell(index, 18, data_dict[key]['check_date']))  # 勾选日期
                query_cells.append(QueryCell(index, 19, data_dict[key]['is_declare']))  # 已申报
                query_cells.append(QueryCell(index, 20, data_dict[key]['declare_date']))  # 申报日期
                query_cells.append(QueryCell(index, 21, data_dict[key]['is_error']))  # 是否异常
                query_cells.append(QueryCell(index, 22, data_dict[key]['sett_org_name']))  # 结算组织（展示）
                query_cells.append(QueryCell(index, 23, data_dict[key]['project_number']))  # 项目编号
                query_cells.append(QueryCell(index, 24, data_dict[key]['project_name']))  # 项目名称（展示）

                # 拼装报表穿透联查的参数
                if not (data_dict[key]['is_subtotal'] or data_dict[key]['is_total']):
                    self._get_event_data(event_data, data_dict[key], index, model_list, double_click_params)
                
        else:
            # 将组织好的数据汇总字典插入到表格中
            for index, key in enumerate(data_key_list):

                query_cells.append(QueryCell(index, 0, data_dict[key]['document_number'], style=CLICK_STYLE))  # 单据编号
                query_cells.append(QueryCell(index, 1, data_dict[key]['state']))  # 单据状态
                query_cells.append(QueryCell(index, 2, data_dict[key]['inv_type_name']))  # 发票类型（展示）
                query_cells.append(QueryCell(index, 3, data_dict[key]['inv_date']))  # 发票日期
                query_cells.append(QueryCell(index, 4, data_dict[key]['inv_code']))  # 发票代码
                query_cells.append(QueryCell(index, 5, data_dict[key]['inv_number']))  # 发票号
                query_cells.append(QueryCell(index, 6, data_dict[key]['contact_dept']))  # 往来单位（销方）
                query_cells.append(QueryCell(index, 7, data_dict[key]['amount_total']))  # 不含税金额
                query_cells.append(QueryCell(index, 8, data_dict[key]['tax_total']))  # 税额
                query_cells.append(QueryCell(index, 9, data_dict[key]['amount_tax_total']))  # 价税合计
                query_cells.append(QueryCell(index, 10, data_dict[key]['is_deduction']))  # 抵扣勾选
                query_cells.append(QueryCell(index, 11, data_dict[key]['check_date']))  # 勾选日期
                query_cells.append(QueryCell(index, 12, data_dict[key]['effective_tax']))  # 有效税额
                query_cells.append(QueryCell(index, 13, data_dict[key]['is_declare']))  # 已申报
                query_cells.append(QueryCell(index, 14, data_dict[key]['declare_date']))  # 申报日期
                query_cells.append(QueryCell(index, 15, data_dict[key]['is_error']))  # 是否异常
                query_cells.append(QueryCell(index, 16, data_dict[key]['sett_org_name']))  # 结算组织（展示）
                query_cells.append(QueryCell(index, 17, data_dict[key]['project_number']))  # 项目编号
                query_cells.append(QueryCell(index, 18, data_dict[key]['project_name']))  # 项目名称（展示）
                query_cells.append(QueryCell(index, 19, data_dict[key]['occupy_inv_amount']))  # 已占用金额
                query_cells.append(QueryCell(index, 20, data_dict[key]['src_doc_number'], style=CLICK_STYLE))  # 引用单据
                query_cells.append(QueryCell(index, 21, data_dict[key]['voucher_number'], style=CLICK_STYLE))  # 凭证号

                # 拼装报表穿透联查的参数
                if not (data_dict[key]['is_subtotal'] or data_dict[key]['is_total']):
                    self._get_event_data(event_data, data_dict[key], index, model_list, double_click_params)

        return query_cells, event_data, model_list

    def _get_double_click_params(self, domain_fields):
        """
        配置双击穿透所需要的列、模型名、记录id
        :param:
            self: 当前实例对象
            domain_fields: 字段选择过滤条件
        :return:
            double_click_params: 双击穿透所需参数值
        """
        # 提取公共变量
        is_show_detail = domain_fields['is_show_detail']
        doc_col = 0  # 单据编号所在列
        src_doc_col = 20  # 引用单据所在列
        voucher_number_col = 21  # 凭证号所在列

        double_click_params = [
            {
                'col': doc_col,
                'model_name_field': 'doc_model_name',
                'doc_id_field': 'doc_id',
            }
        ]
        if not is_show_detail:
            double_click_params.extend([
                {
                    'col': src_doc_col,
                    'model_name_field': 'source_model_name',
                    'doc_id_field': 'source_id',
                },
                {
                    'col': voucher_number_col,
                    'model_name_field': 'voucher_model_name',
                    'doc_id_field': 'voucher_id',
                },
            ])

        return double_click_params

    def _get_inv_action(self, ref):
        """
        根据ref获取进项税发票动作信息列表
        :param:
            self: 当前实例对象
            ref: action的xml id
        :return:
            (dict): 动作信息列表
        """
        action = self.env.ref(ref)
        return {
            'id': action.id,
            'xml_id': action.xml_id,
            'views': {view.view_mode: view.view_id.id for view in action.view_ids},
            'name': action.name,
            'domain': action.domain,
        }

    def _get_er_action(self, source_doc_type_num):
        """
        根据单据类型编码返回跳转视图信息
        农银金科
        :param:
            self: 当前实例对象
            source_doc_type_num: 单据类型编码
        :return:
            (dict): 动作信息列表
        """
        if source_doc_type_num:
            type_num_list = list(ENTER_TYPE_DICT.values())
            action_list = list(ENTER_TYPE_DICT.keys())
            for index, value in enumerate(type_num_list):
                if source_doc_type_num in value:
                    form_id = action_list[index]
                    break
            action = self.env.ref('ps_er.'+form_id)
            return {
                'id': action.id,
                'xml_id': action.xml_id,
                'views': {view.view_mode: view.view_id.id for view in action.view_ids},
                'name': action.name,
                'domain': action.domain,
            }

    def _get_voucher_action(self, ref):
        """
        根据ref获取凭证动作信息列表
        :param:
            self: 当前实例对象
            ref: action的xml id
        :return:
            (dict): 动作信息列表
        """
        action = self.env.ref(ref)
        return {
            'id': action.id,
            'xml_id': action.xml_id,
            'views': {
                'list': self.env.ref('ps_gl.view_gl_voucher_tree').id,
                'form': self.env.ref('ps_gl.view_gl_voucher_form').id,
                'pssearch': self.env.ref('ps_gl.view_gl_voucher_pssearch').id,
            },
            'name': action.name,
            'domain': [('delete_state','=','normal')],
        }

    def _get_event_data(self, event_data, value_dict, row, model_list, double_click_params):
        """
        组织查询条件所需的event_data数据
        :param:
            self: 当前实例对象
            event_data: event_data数据字典
            value_dict: 查询组件组织的数据
            row: 当前单元格所在的行
            model_list: 用于组织模型对应的action
            double_click_params: 双击穿透所需参数值
        :return: 
        """
        if not(value_dict and double_click_params):
            return 
        act_window_obj = self.env['ir.actions.act_window']
        for line in double_click_params:
            col = line.get('col', 0)
            model_name_field = line.get('model_name_field', '')
            doc_id_field = line.get('doc_id_field', '')
            if not(model_name_field and doc_id_field):
                continue
            
            model_name = value_dict.get(model_name_field, '')
            doc_id = value_dict.get(doc_id_field, 0)
            if not(model_name and doc_id):
                continue

            if model_name == 'iv.input.vat.inv':
                ref_to_doc = value_dict.get('ref_to_doc', 0)
                action_data = self._get_inv_action(ref_to_doc)
            elif model_name == 'gl.voucher':
                ref_to_voucher = 'ps_gl.action_gl_voucher'
                action_data = self._get_voucher_action(ref_to_voucher)
            elif model_name == 'er.expense':
                source_doc_type_num = value_dict.get('source_doc_type_num', 0)
                action_data = self._get_er_action(source_doc_type_num)
            else:
                # 使用公用方法获取action,view_id,display_name
                action_data = act_window_obj.p_get_first_action(model_name)
                if not action_data:
                    continue

            action = action_data.get('xml_id', '')
            if not action:
                continue

            display_name = action_data.get('name', '')
            views = action_data.get('views', {})
            if views:
                view_id = views.get('form', 0)
            else:
                continue

            if not view_id:
                continue
            domain = action_data.get('domain', '')

            # 用于组织模型对应的action
            model_list.append({
                'model_name': model_name,
                'view_id': view_id,
                'display_name': display_name,
                'domain': domain,
                'action': action
            })

            # 组织查询条件所需的event_data数据
            click_event = model_name + '.click.event'
            if event_data.get(row, {}):
                if model_name == 'er.expense':
                    event_data[row][col] = {
                        action: {
                            'res_id': doc_id,
                            'ref': action,
                            'domain': domain
                        },
                    }
                else:
                    event_data[row][col] = {
                        click_event: {
                            'res_id': doc_id,
                            'ref': action,
                            'domain': [('delete_state', '=', 'normal')]
                        },
                    }
            else:
                if model_name == 'er.expense':
                    event_data[row] = {
                        col: {
                            action: {
                                'res_id': doc_id,
                                'ref': action,
                                'domain': domain
                            },
                        }}
                else:
                    event_data[row] = {
                        col: {
                            click_event: {
                                'res_id': doc_id,
                                'ref': action,
                                'domain': [('delete_state', '=', 'normal')]
                            },
                        },
                    }

    def _get_click_events(self, model_list):
        """
        明细行记录对应的报表穿透联查事件
        :param:
            self: 当前实例对象
            model_list: 用于组织模型对应的action
        :return: 
            click_events: 报表缠头联查事件列表
        """
        click_events = []
        for line in model_list:
            model_name = line.get('model_name', '')
            view_id = line.get('view_id', [])
            display_name = line.get('display_name', '')
            action = line.get('action', '')
            domain = line.get('domain', '')
            if model_name and view_id and display_name:
                if model_name == 'er.expense':
                    click_events.append(
                        ClickEvent(action, display_name, {
                            'type': 'ir.actions.act_window',
                            'name': display_name,  
                            'res_model': model_name,
                            'view_mode': 'list,form',
                            'view_type': 'form',
                            'domain': domain,
                            'views': [
                                (False, 'list'),
                                (view_id, 'form')
                            ],
                        })
                    )
                else:
                    click_events.append(
                        ClickEvent(model_name + '.click.event', display_name, {
                            'type': 'ir.actions.act_window',
                            'name': display_name,  
                        'name': display_name,  
                            'name': display_name,  
                        'name': display_name,  
                            'name': display_name,  
                        'name': display_name,  
                            'name': display_name,  
                            'res_model': model_name,
                            'view_mode': 'list,form',
                            'view_type': 'form',
                            'views': [
                                (False, 'list'),
                                (view_id, 'form')
                            ],
                        })
                    )

        return click_events

    ################################  私有方法区  end    ################################


    ################################  公共方法区  start  ################################
    
    ################################  公共方法区  end    ################################


    ################################  覆盖基类方法区  start  ################################

    @sys_ele_ctrl()
    def read(self, fields=None, load='_classic_read'):
        """
        对查询方法，添加权限
        :param:
            self: 当前实例对象
            fields: None
            load: _classic_read, str类型
        :return: 
            (super) - 返回调用父类的 read 方法
        """
        return super(IvInputInvoiceDetailQuery, self).read(fields, load)

    @api.model
    def get_ps_query_data(self, render_type='spreadjs', domain_fields={}, context_fields={}, first_render=False):
        """
        覆盖基类get_ps_query_data方法，组织报表数据
        :param:
            self: 当前实例对象
            render_type: 使用控件类型，默认为spreadjs
            domain_fields: 字段选择过滤条件
            context_fields: 上下文过滤条件
            first_render: 是否为第一次访问报表页面（从菜单或者其他视图打开报表，而不是报表点击查询按钮）
        :return: 
            (func) - 返回调用报表数据展示
        """
        domain_fields = context_fields if first_render else domain_fields
        display_name = _("Input Invoice Detail Query")  # 生产订单执行明细表
        
        if render_type == 'spreadjs':
            if (not context_fields and first_render) or not domain_fields:
                # 第一次访问报表页面（从菜单或者其他视图打开报表，而不是报表点击查询按钮）
                # 则直接返回一个空的报表页面
                return self._get_default_domains(render_type, display_name, domain_fields)

            # 定义默认隐藏列
            hidden_cols=[]

            # domain_fields过滤条件校验
            self._check_domain_fields(domain_fields)

            # domain_fields过滤条件重组织
            domain_fields = self._organization_domain_fields(domain_fields)
            
            # 定义报表需要返回的变量           
            query_tables = list()  # 考虑明细表，可能一个sheet页多个表格
            query_cells = list()  # 定义需要组织的表格
            event_data = dict()  # 定义穿透、右键等操作事件
            double_click_event_params = dict()  # 定义穿透事件参数字典
            click_events = []  # 双击穿透事件
            double_click_event = {}  # 双击事件跳转action
            groups = []  # 此表格分组的行号，书写规则：（数据所处行坐标，行数）
            col_count = 0  # 定义页面展示多少列

            # 组织查询数据
            query_cells, event_data, model_list = self._get_query_cells(domain_fields)

            # 根据条件获取副标题
            query_cell_title = self._get_query_cell_title(domain_fields)
            query_cells.append(QueryCell(0, 0, query_cell_title['sett_org_id'], category=QueryCell.TITLE))
            query_cells.append(QueryCell(0, 5, query_cell_title['inv_date'], category=QueryCell.TITLE))

            if domain_fields['is_show_detail']:
                # 定义页面展示多少列
                col_count = 25
                # 定义报表展示的模板
                config_json_file = self._deal_with_config_json_file('detail')
            
            else:
                # 定义页面展示多少列
                col_count = 22
                # 定义报表展示的模板
                config_json_file = self._deal_with_config_json_file('doc')

            # 报表穿透联查事件列表
            click_events = self._get_click_events(model_list)

            # 组装一个表格
            query_tables.append(QueryTable(query_cells=query_cells, col_count=col_count, groups=groups, double_click_event_params=double_click_event_params, blank_row_count=0,  event_data=event_data))
            return self._get_spreadjs_query_data(display_name, domain_fields, query_tables, double_click_event, hidden_cols, click_events=click_events, frozen_row_count=2, frozen_col_count=7, config_source='json', config_json_file=config_json_file)

    ################################  覆盖基类方法区  end    ################################

    ################################  其他方法区  start  ################################
    
    ################################  其他方法区  end    ################################ 
