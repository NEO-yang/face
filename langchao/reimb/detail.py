# -*- coding: utf-8 -*-
'''
==================================================
@创建人: 杨兴财
@当前维护人: 杨兴财
@Desc: 费用报销费用明细表
==================================================
'''
from datetime import datetime
from collections import defaultdict

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

from odoo.addons.ps_query.ps_query_control.models.spreadjs_query import QueryTable, ClickEvent
from fin.ps_er.er_base.models.er_query_base import FIRST_ROW, COLUME_SIZE, SPAN_LENGTH, CONTACT_DEPT_INDEX


EXP_ITEM_INDEX = 6  # 报销事项
DOC_NAME_INDEX = 7  # 单据名称 7
DOC_TYPE_INDEX = 8  # 单据类型8
DOC_NUM_INDEX = 9  # 单据编号 9
APPLY_DATE_INDEX = 10  # 申请日期 10
REASON_INDEX = 11 # 报销事由 11
CURRENCY_INDEX = 12  # 币别 12
EXP_AMOUNT_INDEX = 13  # 费用金额 13
TAX_AMOUNT_INDEX = 14  # 税额 14
REQ_AMOUNT_INDEX = 15  # 申请报销金额 15
APRV_AMOUNT_INDEX = 16  # 核定报销金额 16
APPLY_DEPT_INDEX = 17  # 申请部门 17
APPLY_EMP_INDEX = 18  # 申请人 18
STATE_INDEX = 19  # 单据状态 19
DOC_TYPE_DIFF = 2  # 单据类型区别符
DEFAULT_AMOUNT = 0  # 默认金额
CONTACT_INDEX = 0  # 往来单位类型
COL_COUNT = 20  # 列数
BLANK_ROW_COUNT = 0
FROZEN_ROW_COUNT = 2
ID_INDEX = 0 
VALUE_INDEX = 1 
EVENT_DATA = -1
STEP = 1
LAST_KEY_INDEX = -1
LAST_DATA_INDEX = -1
# 字段映射字典
FIELDS_DICT = {
    EXP_ITEM_INDEX: 'exp_item_name', 
    DOC_NAME_INDEX: 'doc_name', # 单据名称 7
    DOC_TYPE_INDEX: 'document_type_name', # 单据类型 8
    DOC_NUM_INDEX: 'doc_num',  # 单据编号 9
    APPLY_DATE_INDEX: 'apply_date',  # 申请日期 10
    REASON_INDEX: 'reason',  # 报销事由 11
    CURRENCY_INDEX: 'currency_name',  # 币别 12
    EXP_AMOUNT_INDEX: 'exp_amount',  # 费用金额 13
    TAX_AMOUNT_INDEX: 'tax',  # 税额 14
    REQ_AMOUNT_INDEX: 'req_amount',  # 申请报销金额 15
    APRV_AMOUNT_INDEX: 'aprv_amount',  # 核定报销金额 16
    APPLY_DEPT_INDEX: 'apply_dept_name',  # 申请部门 17
    APPLY_EMP_INDEX: 'apply_emp_name',  # 申请人 18
    STATE_INDEX: 'state',  # 单据状态 19
    }


class ErDetailQuery(models.TransientModel):
    _name = 'er.detail.query'
    _inherit = 'er.query.base'
    _description = 'Expense Detail' # 费用明细表


    ################################  default start  ################################
    
    ################################  default end    ################################


    ################################  字段定义区 start  ################################
    
    ################################  字段定义区 end    ################################


    ################################  计算方法区 start  ################################


    ################################  计算方法区 end    ################################


    ################################  onchange方法区  start  ################################
            
    ################################  onchange方法区  end    ################################


    ################################  约束方法区  start  ################################

    ################################  约束方法区  end    ################################


    ################################  服务器动作区  start  ################################
    
    ################################  服务器动作区  end    ################################


    ################################  按钮动作区  start  ################################

    ################################  按钮动作区  end    ################################


    ################################  私有方法区  start  ################################

    def _get_query_title(self, domain_fields):
        """
        获取副标题信息及表头信息
        """
        # 费用明细表表头信息
        fields_dict = {
            EXP_ITEM_INDEX: _("Expense Item"),  # 报销事项 7 
            DOC_NAME_INDEX: _("Doc Name"),  # 单据名称 7
            DOC_TYPE_INDEX: _("Doc Type"),  # 单据类型8
            DOC_NUM_INDEX: _("Doc Number"),  # 单据编号 9
            APPLY_DATE_INDEX: _("Apply Date"),  # 申请日期 10
            REASON_INDEX:  _("Reason"),  # 报销事由 11
            CURRENCY_INDEX: _("Currency"),  # 币别 12
            EXP_AMOUNT_INDEX: _("Expense Amount"),  # 费用金额 13
            TAX_AMOUNT_INDEX: _("Tax Amount"),  # 税额 14
            REQ_AMOUNT_INDEX: _("Requested Amount"),  # 申请报销金额 15
            APRV_AMOUNT_INDEX: _("Approved Amount"),  # 核定报销金额 16
            APPLY_DEPT_INDEX: _("Apply Dept"),  # 申请部门 17
            APPLY_EMP_INDEX: _("Applicant"),  # 申请人 18
            STATE_INDEX: _("State "),  # 单据状态 19
        }
        # 返回表头信息
        return self._get_query_title_by_fields(domain_fields, fields_dict)

    def _update_total_data(self, total_dict, keys, line, total_str):
        """
        计算每日合计，每月合计及总计
        @params: self: 当前示例对象
        @params: keys: [] 代表合计行的数据字典key 包括[每日合计，每月合计，总计（币别）]
        """
        # 组织数据字典
        amount_data = {}
        fields_list = ['tax', 'req_amount', 'aprv_amount', 'exp_amount']
        for amount_key in fields_list:
            amount_data[amount_key] = line.get(amount_key, DEFAULT_AMOUNT)
        
        for key in keys:
            # 如果有当日、月的数据存在，相同KEY下，做加和处理。
            if key in total_dict:
                self._update_exp_amount_data(total_dict, key, amount_data, fields_list)
            # 没有已有数据，则创建新的合计数据
            else:
                total_dict[key] = {
                    'reason': total_str.get(key[LAST_KEY_INDEX], None),
                    'currency_id': line.get('currency_id', None), 
                    'currency_name': line.get('currency_name', None), 
                    **amount_data
                }
   
    def _get_line_data(self, line, domain_fields):
        exp_org_obj = self.env['sys.admin.orgs']
        org_name = exp_org_obj.browse(domain_fields['exp_org_id']).name
        # 往来单位类型
        contact_dept_type = {
            'mdm.department': _("Department"), 
            'mdm.employee': _("Employee"), 
            'mdm.supplier': _("Supplier"), 
            'mdm.customer': _("Customer")
        }
        state_dict = {  # 翻译加载不出，需要在此处进行翻译
            'save': _('Save '),
            'submit': _('  Submit  '),
            'audit': _('Audit '),
        }
        er_str = _('Expense Record Doc')  # 费用报销单
        tr_str = _('Travel Expense Reimbursement')  # 差旅费报销单
        
        # 表头信息
        record = line.get('parent_id', {})
        doc_model = record.get('model', '')
        # 往来单位
        contact_dept = record.get('contact_dept', '')
        # 申请日期
        apply_date = record.get('apply_date', '')
        # 组装明细数据
        exp_lines_data = {
                'org_name': org_name,
                'exp_dept_id': record.get('exp_dept_id', ('', ''))[ID_INDEX], 
                'exp_dept_name': record.get('exp_dept_id', ('', ''))[VALUE_INDEX], 
                'project_num': record.get('project_num', ''),
                'project_name': record.get('project_id', ('', ''))[VALUE_INDEX], 
                'contact_type': contact_dept_type.get(contact_dept.split(",")[CONTACT_INDEX]), 
                'contact_dept': contact_dept,
                'exp_item_id': line.get('exp_item_id', ('', ''))[ID_INDEX],
                'doc_name': er_str if doc_model == 'er.expense' else tr_str,
                'document_type_name': record.get('document_type_id', ('', ''))[VALUE_INDEX],  # 单据类型
                'doc_num': record.get('number', ''),
                'apply_date': datetime.strftime(apply_date, '%Y-%m-%d'),
                'apply_month': datetime.strftime(apply_date, '%Y-%m'),
                'reason': record.get('reason', ''),
                'apply_dept_name': record.get('apply_dept_id', ('', ''))[VALUE_INDEX],
                'apply_emp_name': record.get('apply_emp_id', ('', ''))[VALUE_INDEX],
                'state': state_dict.get(record.get('state', ''), None),
                'exp_item_name': line.get('exp_item_id', ('', ''))[VALUE_INDEX],  # 费用项目
                'currency_id': record.get('currency_id', ('', ''))[ID_INDEX], 
                'currency_name': record.get('currency_id', ('', ''))[VALUE_INDEX], 
                'record_id': record.get('id', ''),
                'doc_model': doc_model,
                'tax': line.get('tax', DEFAULT_AMOUNT),
                'req_amount': line.get('req_amount', DEFAULT_AMOUNT),
                'aprv_amount': line.get('aprv_amount', DEFAULT_AMOUNT),
                'exp_amount': line.get('exp_amount', DEFAULT_AMOUNT),
                }
        return exp_lines_data
    
    def _get_query_cells(self, domain_fields):
        """
        @desc: 组织查询数据，并插入报表
        @params: self: 当前示例对象
        @params: domain_fields: 字段选择过滤条件
        @return: 返回表格数据，跳转动作
        """
        # 获取费用报销单明细行，表头数据
        lines_data = self._get_record_data_by_fields(domain_fields, 'detail')
        # 获取往来单位信息, 组织往来单位信息字典
        contact_dept_model = 'mdm.' + domain_fields['contact_dept']
        depts_obj = self.env[contact_dept_model]
        depts = depts_obj.search([]).read(['name'])
        dept_dict = {}
        for dept in depts:
            dept_dict_key = ','.join([contact_dept_model, str(dept['id'])])
            dept_dict[dept_dict_key] = (dept['id'], dept['name'])
        # 数据合计字典
        total_dict = {}
        query_cells = []
        # 双击跳转到费用明细行事件
        double_click_event_params = {}
        # 展示明细行数据
        row_index = FIRST_ROW
        # 合计字符
        total_str = {
            'day': _('Day Total'),
            'month': _('Month Total'),
            'total': _('Total'),
        }
        # 数据合计字典
        total_dict = {}

        is_total = domain_fields.get('is_total', False)
        if is_total:
            # 排序依据：申请日期升序排序——相同申请日期按单据ID升序排序——同一单据按行号升序排序
            # 合计时添加币别排序
            lines_data = sorted(lines_data, key=lambda x : 
            [x['parent_id']['currency_id'][ID_INDEX], x['parent_id']['apply_date'], x['parent_id']['id'], x['sequence']])
        else:
            lines_data = sorted(lines_data, key=lambda x : 
            [x['parent_id']['apply_date'], x['parent_id']['id'], x['sequence']])
        
        for rec in lines_data:
            line = self._get_line_data(rec, domain_fields)
            contact_dept = line.get('contact_dept', None)
            contact_dept_id, contact_dept_name = dept_dict.get(contact_dept, ('', ''))
            # 获取合计样式
            total_amount_style = self._get_total_style(line.get('currency_id', None))
            # 更新往来单位
            FIELDS_DICT[CONTACT_DEPT_INDEX] = 'contact_dept'
            line['contact_dept'] = contact_dept_name

            currency_id = line.get('currency_id', '')
            apply_month = line.get('apply_month', '')
            apply_date = line.get('apply_date', '')
            if is_total:
                # 按照日期、币别，更新合计
                day_key = (currency_id, apply_date, 'day')
                mon_key = (currency_id, apply_month, 'month')
                total_key = (currency_id, 'total')

                if total_dict:
                    is_diff_day = old_apply_date != apply_date
                    is_diff_month = old_apply_month != apply_month
                    is_diff_currency = old_currency_id != currency_id
                    if is_diff_day or is_diff_currency:
                        query_cells.extend(self._get_result_cell(row_index, FIELDS_DICT, total_dict[(old_currency_id, old_apply_date, 'day')], total_amount_style))
                        row_index += STEP
                    if is_diff_month or is_diff_currency:
                        query_cells.extend(self._get_result_cell(row_index, FIELDS_DICT, total_dict[(old_currency_id, old_apply_month, 'month')], total_amount_style))
                        row_index += STEP
                    if is_diff_currency:
                        query_cells.extend(self._get_result_cell(row_index, FIELDS_DICT, total_dict[(old_currency_id, 'total')], total_amount_style))
                        row_index += STEP
                
                # 更新合计金额
                self._update_total_data(total_dict, [day_key, mon_key, total_key], line, total_str)

            # 组织数据
            query_cells.extend(self._get_result_cell(row_index, FIELDS_DICT, line))
            # 组织双击事件,跳过合计行
            if contact_dept_id:
                if line.get('doc_model', None) == 'er.expense':
                    form_id = 'to_er_expense_reimb_form'
                else:
                    form_id = 'to_er_travel_reimb_form'
                double_click_event_params[row_index] = {
                    EVENT_DATA: {
                        form_id: {'res_id': line['record_id']}
                            }
                    }
            row_index += STEP
            if is_total:
                if rec == lines_data[LAST_DATA_INDEX]:
                    # 在所有明细数据插入结束后，插入本日合计、本月合计、累计
                    query_cells.extend(self._get_result_cell(row_index, FIELDS_DICT, total_dict[(currency_id, apply_date, 'day')], total_amount_style))
                    row_index += STEP
                    query_cells.extend(self._get_result_cell(row_index, FIELDS_DICT, total_dict[(currency_id, apply_month, 'month')], total_amount_style))
                    row_index += STEP
                    query_cells.extend(self._get_result_cell(row_index, FIELDS_DICT, total_dict[(currency_id, 'total')], total_amount_style))
                    row_index += STEP
                old_currency_id = currency_id
                old_apply_month = apply_month
                old_apply_date = apply_date
                
        return query_cells, double_click_event_params

    def _get_events(self):
        """
        双击事件，跳转动作
        """
        expense_name = _('Expense Record Doc')
        travel_name = _('Travel Expense Reimbursement')
        return [
            # 查看费用报销单
            ClickEvent(
                'to_er_expense_reimb_form',
                expense_name, 
                {
                    'type': 'ir.actions.act_window',
                    'name': expense_name, 
                    'res_model': 'er.expense',
                    'view_mode': 'list, form, pssearch',
                    'view_type': 'form',
                    'domain': [('delete_state', '=', 'normal')],
                    'views': [
                        (False, 'list'),
                        (self.env.ref('ps_er.er_expense_form').id, 'form'),
                        (False, 'pssearch')
                        ],
                    'ref': 'ps_er.action_er_expense'
                }, ClickEvent.DC),
            # 查看差旅费报销单
            ClickEvent(
                'to_er_travel_reimb_form',  
                travel_name, 
                {
                    'type': 'ir.actions.act_window',
                    'name': travel_name, 
                    'res_model': 'er.travel',
                    'view_mode': 'list, form, pssearch',
                    'view_type': 'form',
                    'domain': [('delete_state', '=', 'normal')],
                    'views': [
                        (False, 'list'),
                        (self.env.ref('ps_er.view_er_travel_form').id, 'form'),
                        (False, 'pssearch')
                        ],
                    'ref': 'ps_er.action_er_travel'
                }, ClickEvent.DC),

            ]

    ################################  私有方法区  end    ################################


    ################################  公共方法区  start  ################################
    
    ################################  公共方法区  end    ################################


    ################################  覆盖基类方法区  start  ################################

    @api.model
    def get_ps_query_data(self, render_type='spreadjs', domain_fields={}, context_fields={}, first_render=False):
        """
        覆盖基类get_ps_query_data方法，组织报表数据
        @params: render_type: 使用控件类型，默认为spreadjs
        @params: domain_fields: 字段选择过滤条件
        @params: context_fields: 上下文过滤条件
        @params: first_render: 是否为第一次访问报表页面（从菜单或者其他视图打开报表，而不是报表点击查询按钮）
        @return: 返回调用报表数据展示
        """
        display_name = _('Expense Detail')  
        if not context_fields and first_render:
            # 第一次访问报表页面（不包含穿透过来的情况）,则直接返回一个空的报表页面
            return self._get_default_domains(render_type, display_name, domain_fields)
        domain_fields = domain_fields or context_fields
        # 校验日期
        self._check_date(domain_fields)
        # 处理过滤条件中币别字段
        domain_fields['currency_ids'] = self._get_currency_ids(domain_fields)
        # 组装标题和表头
        query_cells = self._get_query_title(domain_fields)
        # 报表数据，双击事件穿透到费用明细表
        query_body, double_click_event_params = self._get_query_cells(domain_fields)
        query_cells.extend(query_body)
        # 获取跳转事件
        click_events = self._get_events()
        # 数据展示
        query_tables= [QueryTable(query_cells=query_cells, col_count=COL_COUNT, blank_row_count=BLANK_ROW_COUNT, event_data=double_click_event_params)]
        # 获取跳转事件
        return self._get_spreadjs_query_data(
            display_name, domain_fields, query_tables, 
            column_sizes=[COLUME_SIZE] * SPAN_LENGTH, click_events=click_events, frozen_row_count=FROZEN_ROW_COUNT)

    ################################  覆盖基类方法区  end    ################################


    ################################  其他方法区  start  ################################

    ################################  其他方法区  end    ################################