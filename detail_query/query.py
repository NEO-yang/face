# -*- coding: utf-8 -*-
'''
==================================================
@创建人: 杨兴财
@当前维护人: 杨兴财
@Desc: 经营会计费用明细表
==================================================
'''

from collections import defaultdict
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

from odoo.addons.ps_query.ps_query_control.models.spreadjs_query import QueryTable, QueryCell, ClickEvent


COLUME_COUNT = 20 # 列数
COLUME_SIZE = 72 # 列宽

TO_AMB_VOUCHER_FORM = 'to_amb_expense_reimb_form' # 穿透至经营流水的动作id

BILL_ACTION = 'amb.action_amb_expense_reimb'
DAY_TOTAL = _('Day Total')
MONTH_TOTAL = _('Month Total')
ALL_TOTAL = _('All Total')
DOC_NAME = _('Expense Record Doc')


class AmbExpenceDetailQuery(models.TransientModel):
   _name = 'amb.expence.detail.query'
   _inherit = 'amb.expence.query.base'
   _description = 'Expense Details' # 费用明细表


   ################################  default start  ################################
   '''
   def _get_exp_org_domain(self):
      """
      获取组织过滤条件
      """
      exp_org_id_list = self._get_default_exp_org_list()
      return [('id', 'in', exp_org_id_list)] or []

   def _get_default_exp_org(self):
      """
      获取当前登陆用户的组织符合条件则设为默认值
      """
      login_user_org_id = self.env.user.ps_curr_org_id.id
      if login_user_org_id in self._get_default_exp_org_list():
         return login_user_org_id

   def _get_default_exp_org_list(self):
      """
      可选范围为状态为已审核的、具有结算职能的、在主会计核算体系中的组织列表
      """
      major_accting_sys = self.env['sys.admin.orgs'].p_get_buss_org_in_major_accting_sys()
      orgs_target_ids = self.env['sys.admin.orgs'].p_get_fun_orgs('settle')
      exp_org_id_list = [org_id for org_id in major_accting_sys if org_id in orgs_target_ids]
      return exp_org_id_list
   '''
   ################################  default end    ################################


   ################################  字段定义区 start  ################################
   '''
   # 费用承担组织
   exp_org_id = fields.Many2one(
      comodel_name='sys.admin.orgs', store=True, string='Expense Bearing Org',
      default=lambda self: self._get_default_exp_org(),
      domain=lambda self: self._get_exp_org_domain())
   # 费用承担部门
   exp_dept_ids = fields.Many2many(
      comodel_name='mdm.department', string='Expense Bearing Dept')
   # 单位类型(客户/供应商)
   contact_dept = fields.Selection(
      selection=[('customer', 'Customer'), ('supplier', 'Supplier')], 
      default='customer', string='Reciprocal Unit Type') 
   # 客户
   customer_ids = fields.Many2many('mdm.customer', string='Customer')  
   # 供应商
   supplier_ids = fields.Many2many('mdm.supplier', string='Supplier')  
   # 币别
   currency_ids = fields.Many2many(comodel_name='mdm.currency', string='Currency', 
      default=lambda self: [(6, 0, [self.env.ref('ps_mdm.mdm_currency_data_zg_0000').id])])
   # 开始日期
   start_date = fields.Date(string='Start Date', default=fields.Date.today())  
   # 结束日期 
   end_date = fields.Date(string='End Date', default=fields.Date.today())  
   # 显示合计数
   is_total = fields.Boolean(string='Is Total')  
   # 显示本位币
   is_local_currency = fields.Boolean(string='Is Local Currency')  
   # 包含未审核单据
   is_include_unaudit_doc = fields.Boolean(string='Is Include Unapproved Doc')  
   '''
   ################################  字段定义区 end    ################################


   ################################  计算方法区 start  ################################


   ################################  计算方法区 end    ################################


   ################################  onchange方法区  start  ################################
   '''
   @api.onchange('exp_org_id')
   def _onchange_exp_org_id(self):
      """
      切换费用承担组织，清空部门和单位
      """
      exp_dept_org = self.exp_dept_ids.use_org_id.ids
      if {self.exp_org_id.id} != set(exp_dept_org):
         self.exp_dept_ids = None
      customer_org = self.customer_ids.use_org_id.ids
      if {self.exp_org_id.id} != set(customer_org):
         self.customer_ids = None
      supplier_org = self.supplier_ids.use_org_id.ids
      if {self.exp_org_id.id} != set(supplier_org):
         self.supplier_ids = None
   '''         
   ################################  onchange方法区  end    ################################


   ################################  约束方法区  start  ################################

   ################################  约束方法区  end    ################################


   ################################  服务器动作区  start  ################################
   
   ################################  服务器动作区  end    ################################


   ################################  按钮动作区  start  ################################

   ################################  按钮动作区  end    ################################


   ################################  私有方法区  start  ################################
   '''
   def _check_date(self, domain_fields):
      """
      校验查询日期
      """      
      start_date = domain_fields['start_date']
      end_date = domain_fields['end_date']
      if start_date and end_date and start_date > end_date:
         # 开始日期不能大于结束日期
         raise ValidationError(_('The start date cannot be greater than the end date'))
      
   def _get_currency_ids(self, domain_fields):
      """
      @desc: 组织动态隐藏列
      @params: self: 当前示例对象
      @params: domain_fields: 字段选择过滤条件
      @return: currency_id_list: 币别id列表
      """
      # 定义币别为用户选择的币别
      currency_id_list = domain_fields['currency_ids']
      # 从币别预置数据中获取所有币别
      all_currency_id = self.env.ref('ps_mdm.mdm_currency_data_zg_0000')
      # 如果所选列表中包含所有币别，查询范围为已审核币别
      if all_currency_id.id in currency_id_list:
         currency_id_list = self.env['mdm.currency'].search([
            ('id', 'not in', [all_currency_id.id, self.env.ref('ps_mdm.mdm_currency_data_zg_9999').id])
         ]).ids
      
      return currency_id_list
   '''
   def _insert_total_data(self, domain_fields, query_cells, row, total_dict, time_unit):
      """
      @desc: 插入本日合计、本月合计、所有累计数据
      @params: self: 当前示例对象
      @params: domain_fields: 字段选择过滤条件
      @params: query_cells: 报表最终数据组织列表
      @params: row: 当前行
      @params: total_dict: 组织好的本日合计、本月合计、累计数据字典
      @params: time_unit: day/month/all标志
      @return: row: 下一行
      """
      if time_unit == 'day':
         total_dict['summary'] = DAY_TOTAL  # 摘要：本日合计
      elif time_unit == 'month':
         total_dict['summary'] = MONTH_TOTAL  # 摘要：本月合计
      else:
         total_dict['summary'] = ALL_TOTAL  # 摘要：总计
      # 合计对应报销事由列
      column = 8
      for key in ('summary', 'currency_id'):
         query_cells.append(QueryCell(row, column, total_dict[key] if key and key in total_dict else ''))
         column += 1
        
      currency_id = total_dict.get('currency_id_id', None)
      for key in (time_unit + '_exp_total', time_unit + '_tax_total', time_unit + '_reimb_total'):
         query_cells.append(QueryCell(row, column, total_dict[key] if key and key in total_dict else '', currency_id=currency_id))
         column += 1

      if domain_fields['is_local_currency']:
         query_cells.append(QueryCell(row, column, total_dict['local_currency_id']))  # 本位币：币别
         column += 1
         query_cells.append(QueryCell(row, column, total_dict[time_unit + '_exp_total_local'], currency_id=total_dict.get('local_currency_id_id', None))) 
         column += 1
         query_cells.append(QueryCell(row, column, total_dict[time_unit + '_tax_total_local'], currency_id=total_dict.get('local_currency_id_id', None)))  
         column += 1
         query_cells.append(QueryCell(row, column, total_dict[time_unit + '_reimb_total_local'], currency_id=total_dict.get('local_currency_id_id', None)))  
         column += 1
      else:
         column += 4
      
      return row + 1
   
   def _clear_date(self, domain_fields, total_dict, time_unit):
      """
      使用后清零合计数据，方便下次取用
      """
      total_dict[time_unit + '_exp_total'] = 0
      total_dict[time_unit + '_tax_total'] = 0
      total_dict[time_unit + '_reimb_total'] = 0

      if domain_fields['is_local_currency']:
         total_dict[time_unit + '_exp_total_local'] = 0
         total_dict[time_unit + '_tax_total_local'] = 0
         total_dict[time_unit + '_reimb_total_local'] = 0


   def _insert_query_data(self, domain_fields, query_detail_data_dict, query_cells, row, event_data):
      """
      @desc: 循环插入明细行数据
      @params: self: 当前示例对象
      @params: domain_fields: 字段选择过滤条件
      @params: query_detail_data_dict: 组织好的明细行数据字典
      @params: query_cells: 报表最终数据组织列表
      @params: row: 当前行
      @params: event_data: 跳转事件
      @return: row: 下一行 
      """
      event_data[row] = {
            -1: {
               TO_AMB_VOUCHER_FORM: {
                  'res_id': query_detail_data_dict['source_parent_doc_id'],
                  'ref': BILL_ACTION,
                  'domain': [('delete_state','=','normal')],
                  'context': {
                        'search_default_group_by_doc_type': 1,
                        'search_default_group_by_pay_org_id': 1,
                        'search_default_group_by_document_type': 1,
                        'search_default_group_by_recv_org_id': 1,
                  },
               }
            }
      }

      column = 0
      for key in (
         'exp_org_id', 'exp_dept_id', 'contact_dept', 'exp_item_id', 
         'doc_name', 'doc_type_id', 'doc_num', 'apply_date', 'reason', 
         'currency_id', 'exp_amount', 'tax_amount', 'reimb_amount'
         ):
         query_cells.append(QueryCell(row, column, query_detail_data_dict[key] if key in query_detail_data_dict else ''))
         column += 1

      if domain_fields['is_local_currency']:
         for key in ('local_currency_id', 'exp_amount_local', 'tax_amount_local', 'reimb_amount_local'):
               query_cells.append(QueryCell(row, column, query_detail_data_dict[key] if key in query_detail_data_dict else ''))
               column += 1
      else:
         column += 4
      
      for key in ('apply_dept_id', 'apply_emp_id', 'state'):
         query_cells.append(QueryCell(row, column, query_detail_data_dict[key] if key in query_detail_data_dict else ''))
         column += 1
      
      return row + 1   

   def _get_total_dict(self, domain_fields, query_detail_data_dict, total_dict):
      """
      更新合计数据
      """
      total_dict.update({
         'day_date': query_detail_data_dict['apply_date'],  # 业务日期（日）
         'month_date': query_detail_data_dict['apply_date'][:7:],  # 业务日期（月）
         'currency_id': query_detail_data_dict['currency_id'],  # 币别
         'currency_id_id': query_detail_data_dict['currency_id_id'],  # 币别id
      })
      # 费用金额合计
      total_dict['day_exp_total'] += query_detail_data_dict['exp_amount']  
      total_dict['month_exp_total'] += query_detail_data_dict['exp_amount']
      total_dict['all_exp_total'] += query_detail_data_dict['exp_amount']
      # 税额合计
      total_dict['day_tax_total'] += query_detail_data_dict['tax_amount']  
      total_dict['month_tax_total'] += query_detail_data_dict['tax_amount']
      total_dict['all_tax_total'] += query_detail_data_dict['tax_amount']
      # 报销金额合计
      total_dict['day_reimb_total'] += query_detail_data_dict['reimb_amount']  
      total_dict['month_reimb_total'] += query_detail_data_dict['reimb_amount']
      total_dict['all_reimb_total'] += query_detail_data_dict['reimb_amount']

      if domain_fields['is_local_currency']:
         total_dict['local_currency_id'] = query_detail_data_dict['local_currency_id']  
         total_dict['local_currency_id_id'] = query_detail_data_dict['local_currency_id_id']

         total_dict['day_exp_total_local'] += query_detail_data_dict['exp_amount_local']  
         total_dict['month_exp_total_local'] += query_detail_data_dict['exp_amount_local']
         total_dict['all_exp_total_local'] += query_detail_data_dict['exp_amount_local']

         total_dict['day_tax_total_local'] += query_detail_data_dict['tax_amount_local']  
         total_dict['month_tax_total_local'] += query_detail_data_dict['tax_amount_local']
         total_dict['all_tax_total_local'] += query_detail_data_dict['tax_amount_local']

         total_dict['day_reimb_total_local'] += query_detail_data_dict['reimb_amount_local']  
         total_dict['month_reimb_total_local'] += query_detail_data_dict['reimb_amount_local']
         total_dict['all_reimb_total_local'] += query_detail_data_dict['reimb_amount_local']

      return total_dict

   def _get_query_cells(self, domain_fields):
      """
      @desc: 组织查询数据
      @params: self: 当前示例对象
      @params: domain_fields: 字段选择过滤条件
      
      @return: 返回调用组织数据到表格中
      """
      query_detail_dict = self._get_query_detail_dict(domain_fields)  # 从费用报销单中获取相应的明细行
      return self._organize_query_cells(domain_fields, query_detail_dict)
   '''
   def _get_dept_domain(self, domain_fields):
      """
      @desc: 查询的往来单位 list
      @params: self: 当前示例对象
      @params: domain_fields: 字段选择过滤条件

      @return: dept_domain: 查询的往来单位 list
      """
      dept_field_name = 'contact_dept'
      dept_domain = tuple()
      if domain_fields.get('contact_dept') == 'customer' and domain_fields.get('customer_ids'):
         dept_domain = (dept_field_name, 'in', 
               [ 'mdm.customer,' + str(customer_id) for customer_id in domain_fields['customer_ids'] ]
         )
      elif domain_fields.get('contact_dept') == 'supplier' and domain_fields.get('supplier_ids'):
         dept_domain = (dept_field_name, 'in', 
               [ 'mdm.supplier,' + str(supplier_id) for supplier_id in domain_fields['supplier_ids'] ]
         )
      elif not domain_fields.get('customer_ids') and not domain_fields.get('supplier_ids'):
         dept_domain = (dept_field_name, 'like', 
               'mdm.customer,' if domain_fields['contact_dept'] == 'customer' else 'mdm.supplier,'
         )
      return dept_domain
   '''
   def _get_query_detail_dict(self, domain_fields):
      """
      @desc: 从费用报销单中获取查询期间内的数据，并组织在query_detail_dict中
      @params: self: 当前示例对象
      @params: domain_fields: 字段选择过滤条件

      @return: query_detail_dict: 组织好的查询期间内的数据
      """
      query_detail_list = []
      domain = [
         ('exp_org_id', '=', domain_fields['exp_org_id']),
         ('exp_dept_id', 'in', domain_fields['exp_dept_ids']),
         ('currency_id', 'in', domain_fields['currency_ids']),
         ('delete_state', '=', 'normal'),
         ('apply_date', '>=', domain_fields['start_date']),
         ('apply_date', '<=', domain_fields['end_date'])]
      # 不勾选包含未审核，只取已审核数据
      if not domain_fields['is_include_unaudit_doc']:
         domain.append(('state', '=', 'audit'))
      else:
         domain.append(('state', 'in', ['audit', 'save', 'submit']))
      # 获取往来单位的过滤
      pay_dept_domain = self._get_dept_domain(domain_fields)
      domain.append(pay_dept_domain)

      if domain_fields['is_total']:
         records = self.env['amb.expense.reimb'].search(domain, order='currency_id asc, apply_date asc, id asc')
      else:
         records = self.env['amb.expense.reimb'].search(domain, order='apply_date asc, id asc')
      record_ids = records.ids
      # 表头数据查询
      parent_data = records.query_read( 
         fields=['exp_org_id', 'exp_dept_id', 'contact_dept', 'doc_type_id', 
         'number', 'apply_date', 'reason', 'currency_id', 'apply_dept_id', 
         'apply_emp_id', 'state', 'local_currency_id'])
        
      line_records = self.env['amb.expense.reimb.line1'].search([('parent_id', 'in', record_ids)])
      # 表体数据查询
      lines_data = line_records.query_read(
         fields=['exp_item_id', 'exp_amount', 'tax_amount', 'reimb_amount', 
         'exp_amount_local', 'tax_amount_local', 'reimb_amount_local', 'parent_id', 'id'])
      lines_dict = defaultdict(list) # 存放parent_id及表体的对应关系，即根据parent_id进行分组
      for line in lines_data:
         if line['parent_id']:
            lines_dict[line['parent_id']].append(line)
      
      for parent in parent_data:
         # 对于查询到的往来单位，返回格式是字符串'mdm.customer,1'
         # 逗号前是模型，后一位是ID
         model = parent['contact_dept'][0:-2]
         contact_dept_id = int(parent['contact_dept'][-1])
         contact_dept = self.env[model].browse(contact_dept_id)
         parent_dict = {
            'exp_org_id': parent['exp_org_id'][1] if parent['exp_org_id'] else '',  # 费用承担组织
            'exp_dept_id': parent['exp_dept_id'][1],
            'contact_dept': contact_dept.name,
            'doc_name': DOC_NAME,
            'doc_type_id': parent['doc_type_id'][1],
            'doc_num': parent['number'],
            'apply_date': str(parent['apply_date']),
            'reason': parent['reason'],
            'currency_id': parent['currency_id'][1] or '',  # 币别
            'currency_id_id': parent['currency_id'][0],  # 币别id
            'apply_dept_id': parent['apply_dept_id'][1],
            'apply_emp_id': parent['apply_emp_id'][1],
            'state': parent['state'],
            'source_parent_doc_id': parent['id'],
            'parent_id': parent['id'],
            'local_currency_id': parent['local_currency_id'][1] or '',
            'local_currency_id_id': parent['local_currency_id'][0]
            }
         for line in lines_dict.get(parent['id'], []):
            new_dict = {
               'exp_item_id': line['exp_item_id'][1],
               'exp_amount': line['exp_amount'],
               'tax_amount': line['tax_amount'],
               'reimb_amount': line['reimb_amount'],
               'exp_amount_local': line['exp_amount_local'],
               'tax_amount_local': line['tax_amount_local'],
               'reimb_amount_local': line['reimb_amount_local'],
               'line_id': line['id'],
               **parent_dict
            }
            query_detail_list.append(new_dict)
      query_detail_list.sort(key=lambda x: (record_ids.index(x['parent_id']), x['line_id']))

      return query_detail_list

   def _organize_query_cells(self, domain_fields, query_detail_list):
      """
      @desc: 将组织好的数据，插入到表格中
      @params: self: 当前示例对象
      @params: domain_fields: 字段选择过滤条件
      @params: query_detail_dict: 组织好的查询期间内的数据
      @return: query_cells
      """
      query_cells = list()
      event_data = dict()
      if domain_fields['is_total']:
         row = 0
         total_dict = {
            'day_date': '',  # 定义日（日变化时，需先添加本日合计）
            'month_date': '',  # 定义月（月变化时，需先添加本月合计）
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
         }
         if domain_fields['is_local_currency']:
            total_dict['local_currency_id'] = ''  # 定义本位币
            total_dict['day_exp_total_local'] = 0  # 定义本日费用合计本位币
            total_dict['day_tax_total_local'] = 0   # 定义本日税额合计本位币
            total_dict['day_reimb_total_local'] = 0  # 定义本日报销金额合计本位币
            
            total_dict['month_exp_total_local'] = 0  # 定义本月费用合计本位币
            total_dict['month_tax_total_local'] = 0  # 定义本月税额合计本位币
            total_dict['month_reimb_total_local'] = 0  # 定义本月报销合计本位币

            total_dict['all_exp_total_local'] = 0  # 合计
            total_dict['all_tax_total_local'] = 0  
            total_dict['all_reimb_total_local'] = 0

         for value in query_detail_list:
            if total_dict['day_date'] and total_dict['month_date'] and total_dict['currency_id']:
               if total_dict['currency_id'] != value['currency_id']:
                  row = self._insert_total_data(domain_fields, query_cells, row, total_dict, 'day')
                  self._clear_date(domain_fields, total_dict, 'day')
                  row = self._insert_total_data(domain_fields, query_cells, row, total_dict, 'month')
                  self._clear_date(domain_fields, total_dict, 'month')
                  row = self._insert_total_data(domain_fields, query_cells, row, total_dict, 'all')
                  self._clear_date(domain_fields, total_dict, 'all')
                  # 更新币别
                  total_dict['currency_id'] = value['currency_id']
               # 如果用户勾选了显示合计，则需要组织本日合计、本月合计
               elif total_dict['day_date'] != value['apply_date']:
                  # 如果day_date发生变化，则添加本日合计
                  row = self._insert_total_data(domain_fields, query_cells, row, total_dict, 'day')
                  self._clear_date(domain_fields, total_dict, 'day')
                  # 更新本日
                  total_dict['day_date'] = value['apply_date']

                  if total_dict['month_date'] != value['apply_date'][:7:]:
                     # 如果month_date发生变化，则添加本月合计
                     row = self._insert_total_data(domain_fields, query_cells, row, total_dict, 'month')
                     self._clear_date(domain_fields, total_dict, 'month')
                     # 更新本月
                     total_dict['month_date'] = value['apply_date'][:7:]

               
            # 判断完是否插入合计（如果日期发生变化，则要先插入合计）
            # 然后插入下一天（月）明细行数据
            row = self._insert_query_data(domain_fields, value, query_cells, row, event_data)
            total_dict = self._get_total_dict(domain_fields, value, total_dict)
                     
         # 在每组明细数据（币别分组）插入结束后，插入本日合计、本月合计、累计
         row = self._insert_total_data(domain_fields, query_cells, row, total_dict, 'day')
         self._clear_date(domain_fields, total_dict, 'day')
         row = self._insert_total_data(domain_fields, query_cells, row, total_dict, 'month')
         self._clear_date(domain_fields, total_dict, 'month')
         row = self._insert_total_data(domain_fields, query_cells, row, total_dict, 'all')
         self._clear_date(domain_fields, total_dict, 'all')
      else:
         # 不勾选累计，直接往明细表里面插入数据
         row = 0
         for data in query_detail_list:
            row = self._insert_query_data(domain_fields, data, query_cells, row, event_data)

      return query_cells, event_data
   '''
   def _organize_query_cells_1(self, domain_fields, query_detail_dict):
      """
      @desc: 将组织好的数据，插入到表格中
      @params: self: 当前示例对象
      @params: domain_fields: 字段选择过滤条件
      @params: query_detail_dict: 组织好的查询期间内的数据
      @return: query_cells
      """
      query_cells = list()
      event_data = dict()
      currency_group_dict = defaultdict(list)
      if domain_fields['is_total']:
         # 获取返回结果中的币别参数，作为币别字典的KEY，
         # 将同一币别的数据字典的KEY(res.currency_id.id, res.apply_date)作为value
         # currency_group_dict = {
         #     币别1：[币别1，日期1]，[币别1，日期2]
         #     币别2：[币别2，日期1]，[币别2，日期2]
         # }
         for key in sorted(query_detail_dict.keys()):
            currency = key[0]
            currency_group_dict[currency].append(key)

         row = 0
         for key, value in sorted(currency_group_dict.items(), key=lambda item: item[0]):
            total_dict = {
                  'day_date': '',  # 定义日（日变化时，需先添加本日合计）
                  'month_date': '',  # 定义月（月变化时，需先添加本月合计）
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
                  
            }
            if domain_fields['is_local_currency']:
                  total_dict['local_currency_id'] = ''  # 定义本位币
                  total_dict['day_exp_total_local'] = 0  # 定义本日费用合计本位币
                  total_dict['day_tax_total_local'] = 0   # 定义本日税额合计本位币
                  total_dict['day_reimb_total_local'] = 0  # 定义本日报销金额合计本位币
                  
                  total_dict['month_exp_total_local'] = 0  # 定义本月费用合计本位币
                  total_dict['month_tax_total_local'] = 0  # 定义本月税额合计本位币
                  total_dict['month_reimb_total_local'] = 0  # 定义本月报销合计本位币

                  total_dict['all_exp_total_local'] = 0  # 合计
                  total_dict['all_tax_total_local'] = 0  
                  total_dict['all_reimb_total_local'] = 0
            for currency_data_key in value:
               # 按照币别 分组
               for query_detail_data_dict in query_detail_dict[currency_data_key]:
                  # 循环这些包含日期维度的key分别从明细行dict中获取数据，插入到query_cells中
                  if domain_fields['is_total'] and total_dict['day_date'] and total_dict['month_date']:
                     # 如果用户勾选了显示合计，则需要组织本日合计、本月合计
                     if total_dict['day_date'] != query_detail_data_dict['apply_date']:
                        # 如果day_date发生变化，则添加本日合计
                        row = self._insert_total_data(domain_fields, query_cells, row, total_dict, 'day')
                        self._clear_date(domain_fields, total_dict, 'day')
                        # 更新本日
                        total_dict['day_date'] = query_detail_data_dict['apply_date']

                     if total_dict['month_date'] != query_detail_data_dict['apply_date'][:7:]:
                        # 如果month_date发生变化，则添加本月合计
                        row = self._insert_total_data(domain_fields, query_cells, row, total_dict, 'month')
                        self._clear_date(domain_fields, total_dict, 'month')
                        # 更新本月
                        total_dict['month_date'] = query_detail_data_dict['apply_date'][:7:]
                  # 判断完是否插入合计（如果日期发生变化，则要先插入合计）
                  # 然后插入下一天（月）明细行数据
                  row = self._insert_query_data(domain_fields, query_detail_data_dict, query_cells, row, event_data)
                  total_dict = self._get_total_dict(domain_fields, query_detail_data_dict, total_dict)
                     
            # 在每组明细数据（币别分组）插入结束后，插入本日合计、本月合计、累计
            if domain_fields['is_total']:
                  row = self._insert_total_data(domain_fields, query_cells, row, total_dict, 'day')
                  self._clear_date(domain_fields, total_dict, 'day')
                  row = self._insert_total_data(domain_fields, query_cells, row, total_dict, 'month')
                  self._clear_date(domain_fields, total_dict, 'month')
                  row = self._insert_total_data(domain_fields, query_cells, row, total_dict, 'all')
                  self._clear_date(domain_fields, total_dict, 'all')
      else:
         row = 0
         for key, value in sorted(query_detail_dict.items(), key=lambda item: item[0]):
            for data in value:
               row = self._insert_query_data(domain_fields, data, query_cells, row, event_data)

      return query_cells, event_data
   '''
   def _get_events(self):
      """
      双击事件，跳转动作
      """
      return [
         # 查看费用报销单
         ClickEvent(TO_AMB_VOUCHER_FORM, _('Expense Record Doc'), {
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
      query_cells, event_data = self._get_query_cells(domain_fields)
      # 根据条件获取副标题
      date = str(domain_fields['start_date']).replace('-', '') + '-' + str(domain_fields['end_date']).replace('-', '')
      query_cells.append(QueryCell(0, 0, (_('Date: ')) + date, category=QueryCell.TITLE))
      # 获取跳转事件
      click_events = self._get_events()
      # 根据条件是否勾选包含本本位币，动态修改隐藏默认列（默认隐藏本位币的币别、费用金额、税额、报销金额四列）
      hidden_cols = [] if domain_fields.get('is_local_currency', False) else [13, 14, 15, 16]
      query_tables= [QueryTable(query_cells=query_cells, col_count=COLUME_COUNT, blank_row_count=0, event_data=event_data)]
      return self._get_spreadjs_query_data(display_name, domain_fields, query_tables, hidden_cols=hidden_cols, click_events=click_events, frozen_row_count=3, frozen_col_count=9, column_sizes=[COLUME_SIZE] * COLUME_COUNT)

   ################################  覆盖基类方法区  end    ################################


   ################################  其他方法区  start  ################################

   ################################  其他方法区  end    ################################