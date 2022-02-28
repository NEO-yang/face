# -*- coding: utf-8 -*-
'''
==================================================
@创建人: 杨兴财
@当前维护人: 杨兴财
@Desc: 经营会计费用明细表
==================================================
'''
from datetime import datetime
from collections import defaultdict

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

from odoo.addons.ps_query.ps_query_control.models.spreadjs_query import QueryTable, QueryCell, ClickEvent
from odoo.tools.profiler import profile
# @profile


COLUMN_COUNT = 20  # 列数
TOTAL_COLUMN = 8  # 合计摘要所在列数
START_COLUMN = 0  # 起始列数
LOCAL_COLUMN_COUNT = 4  # 本位币相关列数
HIDDEN_LOCAL_COLS = [13, 14, 15, 16]  # 本位币相关列，用于数据隐藏
START_ROW = 0  # 起始行数
READ_ID_INDEX = 0
READ_VALUE_INDEX = 1
LAST_DATA_INDEX = -1 
TITLE_ROW = 0
TITLE_COLUMN = 0
ROW_STEP = 1
COLUMN_STEP = 1
EVENT_DATA_ALL = -1
APPLY_MONTH = '%Y-%m'
TO_AMB_EXPENSE_REIMB_FORM = 'to_amb_expense_reimb_form'  # 穿透至费用报销单id
BILL_ACTION = 'amb.action_amb_expense_reimb'


class AmbExpenseDetailQuery(models.TransientModel):
   _name = 'amb.expense.detail.query'
   _inherit = 'amb.expense.query.base'
   _description = 'Expense Details' # 费用明细表


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
  
   def _insert_total_data(self, domain_fields, query_cells, row, total_dict, time_unit, total_data):
      """
      @desc: 插入本日合计、本月合计、所有累计数据
      @params: self: 当前示例对象
      @params: domain_fields: 字段选择过滤条件
      @params: query_cells: 报表最终数据组织列表
      @params: row: 当前行
      @params: total_dict: 组织好的本日合计、本月合计、累计数据字典
      @params: time_unit: day/month/all标志
      """
      total_dict['summary'] = total_data
      # 合计对应报销事由列
      column = TOTAL_COLUMN
      for key in ('summary', 'currency_id'):
         query_cells.append(QueryCell(row, column, total_dict.get(key, None)))
         column += COLUMN_STEP
      currency_id = total_dict.get('currency_id_id', None)
      for key in (time_unit + '_exp_total', time_unit + '_tax_total', time_unit + '_reimb_total'):
         query_cells.append(QueryCell(
            row, column, total_dict.get(key, 0), currency_id=currency_id))
         column += COLUMN_STEP
      if domain_fields['is_local_currency']:
         local_currency_id = total_dict.get('local_currency_id_id', None)
         query_cells.append(QueryCell(row, column, total_dict.get('local_currency_id', None)))  # 本位币：币别
         column += COLUMN_STEP
         for key in (time_unit + '_exp_total_local', time_unit + '_tax_total_local', time_unit + '_reimb_total_local'):
            query_cells.append(QueryCell(
               row, column, total_dict.get(key, 0), currency_id=local_currency_id))
            column += COLUMN_STEP
      else:
         column += LOCAL_COLUMN_COUNT
   
   def _clear_data(self, domain_fields, total_dict, time_unit):
      """
      使用后清零合计数据，方便下次取用
      """
      for fee in ['_exp', '_tax', '_reimb']:
         for total in ['_total', '_total_local']:
            total_dict[time_unit + fee + total] = 0

   def _insert_query_data(self, domain_fields, query_detail_data_dict, query_cells, row, event_data):
      """
      @desc: 循环插入明细行数据
      @params: self: 当前示例对象
      @params: domain_fields: 字段选择过滤条件
      @params: query_detail_data_dict: 组织好的明细行数据字典
      @params: query_cells: 报表最终数据组织列表
      @params: row: 当前行
      @params: event_data: 跳转事件
      """
      event_data[row] = {
         EVENT_DATA_ALL: {
            TO_AMB_EXPENSE_REIMB_FORM: {
               'res_id': query_detail_data_dict['source_parent_doc_id'],
               'ref': BILL_ACTION,
               'domain': [('delete_state', '=', 'normal')],
               'context': {
                  'search_default_group_by_doc_type': 1,
                  'search_default_group_by_pay_org_id': 1,
                  'search_default_group_by_document_type': 1,
                  'search_default_group_by_recv_org_id': 1,
               },
            }
         }
      }
      column = START_COLUMN
      for key in (
         'exp_org_id', 'exp_dept_id', 'contact_dept', 'exp_item_id', 
         'doc_name', 'doc_type_id', 'doc_num', 'apply_day', 'reason', 'currency_id'
         ):
         query_cells.append(QueryCell(row, column, query_detail_data_dict.get(key, None)))
         column += COLUMN_STEP
      currency_id = query_detail_data_dict.get('currency_id_id', None)
      for key in ('exp_amount', 'tax_amount', 'reimb_amount'):
         value = query_detail_data_dict.get(key, None)
         query_cells.append(QueryCell(row, column, value, currency_id=currency_id))
         column += COLUMN_STEP
      if domain_fields['is_local_currency']:
         local_currency_id = query_detail_data_dict.get('local_currency_id_id', None)
         for key in ('local_currency_id', 'exp_amount_local', 'tax_amount_local', 'reimb_amount_local'):
            value = query_detail_data_dict.get(key, None)
            query_cells.append(QueryCell(row, column, value, currency_id=local_currency_id))
            column += COLUMN_STEP
      else:
         column += LOCAL_COLUMN_COUNT
      
      for key in ('apply_dept_id', 'apply_emp_id', 'state'):
         query_cells.append(QueryCell(row, column, query_detail_data_dict.get(key, None)))
         column += COLUMN_STEP
   #@profile
   def _update_fee_sum(self, total_dict, query_detail_data_dict, total, amount, currency_id):
      '''
      @desc: 总计求和函数
      @params: self: 当前示例对象
      @params: query_detail_data_dict: 组织好的明细行数据字典
      @params: total_dict: 合计数据字典
      @params: total: 合计后缀是否是本位币
      @params: amount: 金额后缀是否是本位币
      @params: currency_id: 币别
      '''
      for period in ['day', 'month', 'all']:
         for fee in ['exp', 'tax', 'reimb']:
            key = period + '_' + fee + total
            total_dict[key] += query_detail_data_dict[fee + amount]
            total_dict[key] = self._round(total_dict[key], currency_id)  # 去除这行代码2000数据可由5.17---2.84

   # def _update_fee_sum1(self, total_dict, query_detail_data_dict, total, amount, currency_id):
   #    '''
   #    @desc: 总计求和函数
   #    @params: self: 当前示例对象
   #    @params: query_detail_data_dict: 组织好的明细行数据字典
   #    @params: total_dict: 合计数据字典
   #    @params: total: 合计后缀是否是本位币
   #    @params: amount: 金额后缀是否是本位币
   #    @params: currency_id: 币别
   #    '''
   #    for period in ['day', 'month', 'all']:
   #       for fee in ['exp', 'tax', 'reimb']:
   #          key = period + '_' + fee + total
   #          total_dict[key] += query_detail_data_dict[fee + amount]
   #          total_dict[key] = self._round(total_dict[key], currency_id)  # 去除这行代码2000数据可由5.17---2.84
   #@profile
   def _update_total_dict(self, domain_fields, query_detail_data_dict, total_dict):
      """
      @desc: 更新合计数据
      @params: self: 当前示例对象
      @params: domain_fields: 字段选择过滤条件
      @params: query_detail_data_dict: 组织好的明细行数据字典
      @params: total_dict: 合计数据字典
      """
      total_dict.update({
         'apply_day': query_detail_data_dict['apply_day'],  # 业务日期（日）
         'apply_month': query_detail_data_dict['apply_month'],  # 业务日期（月）
         'currency_id': query_detail_data_dict['currency_id'],  # 币别
         'currency_id_id': query_detail_data_dict['currency_id_id'],  # 币别id
         'local_currency_id': query_detail_data_dict['local_currency_id'],
         'local_currency_id_id': query_detail_data_dict['local_currency_id_id'],
      })
      self._update_fee_sum(total_dict, query_detail_data_dict, '_total', '_amount', total_dict['currency_id_id'])  # 更新原币总计数据
      if domain_fields['is_local_currency']:
         self._update_fee_sum(total_dict, query_detail_data_dict, '_total_local', '_amount_local', total_dict['local_currency_id_id'])  # 更新本位币总计数据
   

   def _update_total_dict1(self, domain_fields, query_detail_data_dict, total_dict, dict3):
      """
      @desc: 更新合计数据
      @params: self: 当前示例对象
      @params: domain_fields: 字段选择过滤条件
      @params: query_detail_data_dict: 组织好的明细行数据字典
      @params: total_dict: 合计数据字典
      """
      total_dict.update({
         'apply_day': query_detail_data_dict['apply_day'],  # 业务日期（日）
         'apply_month': query_detail_data_dict['apply_month'],  # 业务日期（月）
         'currency_id': query_detail_data_dict['currency_id'],  # 币别
         'currency_id_id': query_detail_data_dict['currency_id_id'],  # 币别id
         'local_currency_id': query_detail_data_dict['local_currency_id'],
         'local_currency_id_id': query_detail_data_dict['local_currency_id_id'],
      })
      for key, value in dict3.items():
        total_dict[key] = total_dict[key] + dict3[key]
      for local in ['', '_local']:
         for fee in ['exp', 'tax', 'reimb']:
            key_m = 'month' + '_' + fee + '_total' + local
            key_d = 'day' + '_' + fee + '_total' + local
            total_dict[key_m] = self._round(total_dict[key_m] + total_dict[key_d], query_detail_data_dict['currency_id_id'])
      # for local in ['', '_local']:
      #    for fee in ['exp', 'tax', 'reimb']:
      #       key_m = 'month' + '_' + fee + '_total' + local
            key_all = 'all' + '_' + fee + '_total' + local
            total_dict[key_all] = self._round(total_dict[key_all] + total_dict[key_m], query_detail_data_dict['currency_id_id'])
   
   def _get_total_init_data(self):
      '''
      定义合计金额相关数据的初始字典
      '''
      total_dict = {
         'apply_day': '',  # 定义日（日变化时，需先添加本日合计）
         'apply_month': '',  # 定义月（月变化时，需先添加本月合计）
         'currency_id': '',  # 定义币别
         'summary': '',  # 定义统计维度
         'day_exp_total': 0,  # 定义本日合计费用
         'month_exp_total': 0,  # 定义本月合计费用
         'all_exp_total': 0, 
         'day_tax_total': 0,  # 定义本日合计税额
         'month_tax_total': 0,  # 定义本月合计税额
         'all_tax_total': 0,
         'day_reimb_total': 0,  # 定义本日合计报销金额
         'month_reimb_total': 0,  # 定义本月合计报销金额
         'all_reimb_total': 0,
         'exp_total': 0,  # 定义合计费用
         'tax_total': 0,  # 定义本合计税额
         'reimb_total': 0,  # 定义合计报销金额
         'local_currency_id': '',  # 定义本位币
         'day_exp_total_local': 0,  # 定义本日费用合计本位币
         'day_tax_total_local': 0,   # 定义本日税额合计本位币
         'day_reimb_total_local': 0,  # 定义本日报销金额合计本位币
         'month_exp_total_local': 0,  # 定义本月费用合计本位币
         'month_tax_total_local': 0,  # 定义本月税额合计本位币
         'month_reimb_total_local': 0,  # 定义本月报销合计本位币
         'all_exp_total_local': 0,  # 费用合计本位币
         'all_tax_total_local': 0,  # 税额合计本位币
         'all_reimb_total_local': 0,  # 报销合计本位币
      }
      return total_dict
   
   def _get_lines_dict(self, line, line_parent_dict, state_dict, dept_dict):
      '''
      @desc: 获取明细行及表头数据
      @params: self: 当前示例对象
      @params: line: 表体数据
      @params: line_parent_dict: 表头数据
      @params: state_dict: 状态字典，用于翻译
      @params: dept_dict: 往来单位字典
      @return: 每条明细行展示（用到）在报表中的数据
      '''
      doc_name = _('Expense Record Doc')  # 单据名称仅为Expense Record Doc
      apply_month = datetime.strftime(line_parent_dict['apply_date'], APPLY_MONTH)
      line_dict = {
         'exp_item_id': line['exp_item_id'][READ_VALUE_INDEX],
         'exp_amount': line['exp_amount'],
         'tax_amount': line['tax_amount'],
         'reimb_amount': line['reimb_amount'],
         'exp_amount_local': line['exp_amount_local'],
         'tax_amount_local': line['tax_amount_local'],
         'reimb_amount_local': line['reimb_amount_local'],
         'exp_org_id': line_parent_dict['exp_org_id'][READ_VALUE_INDEX],  # 费用承担组织
         'exp_dept_id': line['exp_dept_id'][READ_VALUE_INDEX],  # 子表费用承担部门
         'contact_dept': dept_dict[line_parent_dict['contact_dept']],
         'doc_name': doc_name,
         'doc_type_id': line_parent_dict['doc_type_id'][READ_VALUE_INDEX],
         'doc_num': line_parent_dict['number'],
         'apply_day': str(line_parent_dict['apply_date']),
         'apply_month': apply_month,
         'reason': line_parent_dict['reason'],
         'currency_id': line_parent_dict['currency_id'][READ_VALUE_INDEX] or '',  # 币别
         'currency_id_id': line_parent_dict['currency_id'][READ_ID_INDEX],  # 币别id
         'apply_dept_id': line_parent_dict['apply_dept_id'][READ_VALUE_INDEX],
         'apply_emp_id': line_parent_dict['apply_emp_id'][READ_VALUE_INDEX],
         'state': state_dict[line_parent_dict['state']],
         'source_parent_doc_id': line_parent_dict['id'],
         'parent_id': line_parent_dict['id'],
         'local_currency_id': line_parent_dict['local_currency_id'][READ_VALUE_INDEX] or '',
         'local_currency_id_id': line_parent_dict['local_currency_id'][READ_ID_INDEX]
         }
      return line_dict

   def _get_record_data(self, domain_fields):
      '''
      @desc: 表体数据查询
      @params: self: 当前示例对象
      @params: domain_fields: 筛选字段
      @return: lines_data表体数据，parent_id_dict表头数据字典，state_dict单据状态字典
      '''
      domain = [
         ('exp_org_id', '=', domain_fields['exp_org_id']),
         ('currency_id', 'in', domain_fields['currency_ids']),
         ('delete_state', '=', 'normal'),
         ('apply_date', '>=', domain_fields['start_date']),
         ('apply_date', '<=', domain_fields['end_date'])
         ]
      if not domain_fields['is_include_unaudit_doc']:
         domain.append(('state', '=', 'audit'))  # 不勾选包含未审核，只取已审核数据
      else:
         domain.append(('state', 'in', ['audit', 'save', 'submit']))  #勾选后包含保存，审核中，已审核的数据
      pay_dept_domain = self._get_dept_domain(domain_fields) # 获取往来单位的过滤
      domain.append(pay_dept_domain)
      expense_reimb_obj = self.env['amb.expense.reimb']
      if domain_fields['is_total']:  #勾选合计后按币别排序
         expense_records = expense_reimb_obj.search(domain, order='currency_id asc, apply_date asc, id asc')
      else:
         expense_records = expense_reimb_obj.search(domain, order='apply_date asc, id asc')
      # 表头展示数据查询
      parent_data = expense_records.query_read( 
         fields=['exp_org_id', 'contact_dept', 'doc_type_id', 
         'number', 'apply_date', 'reason', 'currency_id', 'apply_dept_id', 
         'apply_emp_id', 'state', 'local_currency_id'])
      record_ids = expense_records.ids
      # 单据排序的字典
      order_dict = {}
      for index, record_id in enumerate(record_ids):
         order_dict[record_id] = index
      expense_reimb_line_obj = self.env['amb.expense.reimb.line1']
      # 组织明细行过滤条件,从费用汇总表穿透过来的查询需要控制费用项目，增加明细行判断
      line_domain = [
         ('parent_id', 'in', record_ids),
         ('exp_dept_id', 'in', domain_fields['exp_dept_ids'])
         ]
      if domain_fields.get('exp_item_id', None):
         line_domain.append(('exp_item_id', '=', domain_fields['exp_item_id']))
      expense_lines = expense_reimb_line_obj.search(line_domain)
      lines_data = expense_lines.query_read(
         fields=['exp_dept_id', 'exp_item_id', 'exp_amount', 'tax_amount', 'reimb_amount', 
         'exp_amount_local', 'tax_amount_local', 'reimb_amount_local', 'parent_id', 'sequence'])
      lines_data.sort(key=lambda x: (order_dict[x['parent_id']], x['sequence']))  # 对表体数据按照表头进行排序
      parent_id_dict = {}  # 存放表头数据的字典，下面组装数据时根据parent_id添加表头数据
      for res in parent_data:
         parent_id_dict[res['id']] = res
      state_dict = dict(expense_records.fields_get(['state'])['state']['selection'])

      return lines_data, parent_id_dict, state_dict

   def _get_sum_for_day(self, dict2, total_dict):
      day_dict = {}
      line = dict2[0]
      # total_dict.update({
      #    'apply_day': query_detail_data_dict['apply_day'],  # 业务日期（日）
      #    'apply_month': query_detail_data_dict['apply_month'],  # 业务日期（月）
      #    'currency_id': query_detail_data_dict['currency_id'],  # 币别
      #    'currency_id_id': query_detail_data_dict['currency_id_id'],  # 币别id
      #    'local_currency_id': query_detail_data_dict['local_currency_id'],
      #    'local_currency_id_id': query_detail_data_dict['local_currency_id_id'],
      # })
      currency_id = [line['currency_id_id'], line['local_currency_id_id']]
      for local in ['', '_local']:
         for fee in ['exp', 'tax', 'reimb']:
            key = 'day' + '_' + fee + '_total' + local
            day_dict[key] = sum(item[fee + '_amount' + local] for item in dict2)
            if local:
               day_dict[key] = self._round(day_dict[key], currency_id[1])
            else:
               day_dict[key] = self._round(day_dict[key], currency_id[0])
      return day_dict




   # @profile
   def _get_query_cells(self, domain_fields):
      """
      @desc: 组织查询数据，并插入报表
      @params: self: 当前示例对象
      @params: domain_fields: 字段选择过滤条件
      @return: 返回表格数据，跳转动作
      """
      lines_data, parent_id_dict, state_dict = self._get_record_data(domain_fields)   #40        465.58
      contact_dept_model = 'mdm.' + domain_fields['contact_dept']
      depts_obj = self.env[contact_dept_model]
      depts = depts_obj.search([])
      dept_dict = {}
      for dept in depts:
         dept_dict_key = contact_dept_model + ',' + str(dept.id)
         dept_dict[dept_dict_key] = dept.name
      query_cells = list()
      event_data = dict()
      row = START_ROW
      total_dict = self._get_total_init_data()
      total_date_dict = {
         'day': _('Day Total'),
         'month': _('Month Total'),
         'all': _('All Total')
         }
      dict1 = defaultdict(list)
      dict2 = {}
      dict3 = {}
      all_lines_data = []
      for line in lines_data:
         line_parent_dict = parent_id_dict[line['parent_id']]
         line_dict = self._get_lines_dict(line, line_parent_dict, state_dict, dept_dict)  # 935.58 组装明细行与表头数据成字典
         all_lines_data.append(line_dict)
         if not domain_fields['is_total']:
            self._insert_query_data(domain_fields, line_dict, query_cells, row, event_data)
            row += ROW_STEP 
         else:
            # self._insert_query_data(domain_fields, line_dict, query_cells, row, event_data) # 1705.84 2000
            # row += ROW_STEP
            # # 币别+日期
            # curr = line_dict['currency_id']
            # ddday = line_dict['apply_day']
            # len_dict1 = len(dict1)
            dict1[line_dict['currency_id'], line_dict['apply_day'], line_dict['apply_month']].append(line_dict)
            # sum_for_day = self._get_sum_for_day(dict1[line_dict['currency_id'], line_dict['apply_day'], line_dict['apply_month']], total_dict)


            # if len(dict1) != len_dict1:
            #    self._insert_total_data(domain_fields, query_cells, row, total_dict, 'day', total_date_dict['day'])
      for key, value in dict1.items():
         dict2[key] = len(value)
         dict3[key] = self._get_sum_for_day(value, total_dict)

      if domain_fields['is_total']:
         i = 1
         for line_dict in all_lines_data:
            # line_parent_dict = parent_id_dict[line['parent_id']]
            # line_dict = self._get_lines_dict(line, line_parent_dict, state_dict, dept_dict)  # 935.58 组装明细行与表头数据成字典
            if total_dict['currency_id']:
               is_diff_day = total_dict['apply_day'] != line_dict['apply_day']
               is_diff_month = total_dict['apply_month'] != line_dict['apply_month']
               is_diff_currency = total_dict['currency_id'] != line_dict['currency_id']
               if is_diff_day or is_diff_currency:
                  # sum_for_day = self._get_sum_for_day(dict1[line_dict['currency_id'], '2021-03-15', line_dict['apply_month']], total_dict)
                  self._insert_total_data(domain_fields, query_cells, row, total_dict, 'day', total_date_dict['day'])
                  row += ROW_STEP
                  self._clear_data(domain_fields, total_dict, 'day')
                  total_dict['apply_day'] = line_dict['apply_day']
               if is_diff_month or is_diff_currency:
                  self._insert_total_data(domain_fields, query_cells, row, total_dict, 'month', total_date_dict['month'])
                  row += ROW_STEP
                  self._clear_data(domain_fields, total_dict, 'month')
                  total_dict['apply_month'] = line_dict['apply_month']
               if is_diff_currency:
                  self._insert_total_data(domain_fields, query_cells, row, total_dict, 'all', total_date_dict['all'])
                  row += ROW_STEP
                  self._clear_data(domain_fields, total_dict, 'all')
                  total_dict['currency_id'] = line_dict['currency_id']
            # 插完合计，然后插入下一天（月）明细行数据
            self._insert_query_data(domain_fields, line_dict, query_cells, row, event_data) # 1705.84 2000
            row += ROW_STEP
            # dict1[line_dict['currency_id'], line_dict['apply_day'], line_dict['apply_month']].append(line_dict)
            
            
            if i == dict2[line_dict['currency_id'], line_dict['apply_day'], line_dict['apply_month']]:
               self._update_total_dict1(domain_fields, line_dict, total_dict, dict3[line_dict['currency_id'], line_dict['apply_day'], line_dict['apply_month']])
               i = 0
            i= i + 1
            # self._update_total_dict(domain_fields, line_dict, total_dict)  # 5542
            if  line_dict == all_lines_data[LAST_DATA_INDEX]:
               # 在所有明细数据插入结束后，插入本日合计、本月合计、累计
               for key in ['day', 'month', 'all']:
                  self._insert_total_data(domain_fields, query_cells, row, total_dict, key, total_date_dict[key])
                  row += ROW_STEP
                  self._clear_data(domain_fields, total_dict, key)

      return query_cells, event_data
   
   def _get_events(self):
      """
      双击事件，跳转动作
      """
      return [
         # 查看费用报销单
         ClickEvent(
            TO_AMB_EXPENSE_REIMB_FORM, 
            _('Expense Record Doc'), 
            {
               'type': 'ir.actions.act_window',
               'name': _('Expense Record Doc'), 
               'res_model': 'amb.expense.reimb',
               'view_mode': 'list,form',
               'view_type': 'form',
               'domain': [('delete_state', '=', 'normal')],
               'views': [
                  (False, 'list'),
                  (self.env.ref('ps_amb.view_amb_expense_reimb_form').id, 'form')
                  ],
               'ref': 'ps_amb.action_amb_expense_reimb'
            }, ClickEvent.DC)
         ]

   ################################  私有方法区  end    ################################


   ################################  公共方法区  start  ################################
   
   ################################  公共方法区  end    ################################


   ################################  覆盖基类方法区  start  ################################
   #@profile
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
      display_name = _('Expense Details')  
      if not context_fields and first_render:
         # 第一次访问报表页面（不包含穿透过来的情况）,则直接返回一个空的报表页面
         return self._get_default_domains(render_type, display_name, domain_fields)
      domain_fields = domain_fields or context_fields
      # 校验日期
      self._check_date(domain_fields)
      # 处理过滤条件中币别字段
      domain_fields['currency_ids'] = self._get_currency_ids(domain_fields)
      # 组织查询数据
      query_cells, event_data = self._get_query_cells(domain_fields)   # 8482
      # 根据条件获取副标题
      date = str(domain_fields['start_date']).replace('-', '') + '-' + str(domain_fields['end_date']).replace('-', '')
      query_cells.append(QueryCell(TITLE_ROW, TITLE_COLUMN, (_('Date: ')) + date, category=QueryCell.TITLE))
      # 获取跳转事件
      click_events = self._get_events()
      # 根据条件是否勾选包含本本位币，动态修改隐藏默认列（默认隐藏本位币的币别、费用金额、税额、报销金额四列）
      hidden_cols = [] if domain_fields.get('is_local_currency', False) else HIDDEN_LOCAL_COLS
      query_tables= [QueryTable(query_cells=query_cells, col_count=COLUMN_COUNT, blank_row_count=0, event_data=event_data)]

      return self._get_spreadjs_query_data(display_name, domain_fields, query_tables, hidden_cols=hidden_cols, click_events=click_events, frozen_row_count=3, frozen_col_count=5)

   ################################  覆盖基类方法区  end    ################################


   ################################  其他方法区  start  ################################

   ################################  其他方法区  end    ################################