# -*- coding: utf-8 -*-
'''
==================================================
@创建人: 杨兴财
@当前维护人: 杨兴财
@Desc: 经营会计费用报表基类
==================================================
'''
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

from odoo.addons.ps_admin.sys_ele.sys_ele_ctrl import sys_ele_ctrl
from odoo.addons.ps_query.ps_query_control.models.spreadjs_query import QueryTable, QueryCell, ClickEvent


class AmbExpenseQueryBase(models.TransientModel):
   _name = 'amb.expense.query.base'
   _description = 'Expense Query Base'  # 费用报表基础

   ################################  default start  ################################

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
      orgs_obj = self.env['sys.admin.orgs']
      major_accting_sys = orgs_obj.p_get_buss_org_in_major_accting_sys()
      orgs_target_ids = orgs_obj.p_get_fun_orgs('settle')
      exp_org_id_list = [org_id for org_id in major_accting_sys if org_id in orgs_target_ids]
      return exp_org_id_list

   ################################  default end    ################################


   ################################  字段定义区 start  ################################

   # 费用承担组织
   exp_org_id = fields.Many2one(
      comodel_name='sys.admin.orgs', store=True, string='Expense Bearing Org',
      default=lambda self: self._get_default_exp_org(),
      domain=lambda self: self._get_exp_org_domain())
   # 费用承担部门
   exp_dept_ids = fields.Many2many(
      comodel_name='mdm.department', string='Expense Bearing Dept', relation='amb_expense_query_expense_department_rel')
   # 往来单位类型(客户/供应商/部门/员工)
   contact_dept = fields.Selection(
      selection=[('customer', 'Customer'), ('supplier', 'Supplier'), ('employee', 'Employee'), ('department', 'Department')], 
      default='customer', string='Reciprocal Unit Type') 
   # 客户
   customer_ids = fields.Many2many('mdm.customer', string='Customer')  
   # 供应商
   supplier_ids = fields.Many2many('mdm.supplier', string='Supplier')
   # 员工
   employee_ids = fields.Many2many('mdm.employee', string='Employee')  
   # 部门
   department_ids = fields.Many2many('mdm.department', string='Department')   
   # 币别
   currency_ids = fields.Many2many(
      comodel_name='mdm.currency', string='Currency', 
      default=lambda self: [(6, 0, [self.env.ref('ps_mdm.mdm_currency_data_zg_0000').id])],
      domain=lambda self: [('id', '!=', self.env.ref('ps_mdm.mdm_currency_data_zg_9999').id)])
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
   
   ################################  字段定义区 end    ################################


   ################################  计算方法区 start  ################################


   ################################  计算方法区 end    ################################


   ################################  onchange方法区  start  ################################

   @api.onchange('exp_org_id')
   def _onchange_exp_org_id(self):
      """
      切换费用承担组织，清空部门和单位
      """
      self.exp_dept_ids = None
      self.customer_ids = None
      self.supplier_ids = None
      self.employee_ids = None
      self.department_ids = None
            
   ################################  onchange方法区  end    ################################


   ################################  约束方法区  start  ################################

   ################################  约束方法区  end    ################################


   ################################  服务器动作区  start  ################################
   
   ################################  服务器动作区  end    ################################


   ################################  按钮动作区  start  ################################

   ################################  按钮动作区  end    ################################


   ################################  私有方法区  start  ################################

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
      @desc: 获取币别查询列表
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
         currency_obj = self.env['mdm.currency']
         currency_id_list = currency_obj.search([
            ('id', 'not in', [all_currency_id.id, self.env.ref('ps_mdm.mdm_currency_data_zg_9999').id])
         ]).ids
      
      return currency_id_list
  
   def _get_dept_domain(self, domain_fields):
      """
      @desc: 查询的往来单位 list
      @params: self: 当前示例对象
      @params: domain_fields: 字段选择过滤条件
      @return: dept_domain: 查询的往来单位 
      """
      dept_domain = tuple()
      contact_dept = domain_fields.get('contact_dept')
      contact_dept_ids = domain_fields.get(contact_dept + '_ids', False)
      if contact_dept_ids:
         dept_domain = ('contact_dept', 'in', 
            ['mdm.%s,%d' % (contact_dept, dept_id) for dept_id in contact_dept_ids])
      else:
         dept_domain = ('contact_dept', 'like', 'mdm.%s' % contact_dept)
      
      return dept_domain
   
   def _round(self, value, currency_id):
      """
      根据currency_id对value进行精度格式化
      """
      return self.env['mdm.currency'].p_amount_float_round(value, currency_id)
   ################################  私有方法区  end    ################################


   ################################  公共方法区  start  ################################
   
   ################################  公共方法区  end    ################################


   ################################  覆盖基类方法区  start  ################################
   
   @sys_ele_ctrl()
   def read(self, fields=None, load='_classic_read'):
      return super(AmbExpenseDetailQuery, self).read(fields, load)

   ################################  覆盖基类方法区  end    ################################


   ################################  其他方法区  start  ################################

   ################################  其他方法区  end    ################################