# -*- coding: utf-8 -*-
'''
==================================================
@创建人 ：杨兴财
@当前维护人 ：杨兴财
@Desc ：创建费用报销单性能数据Controller
==================================================
'''
import datetime
import json
import random

from odoo import http,fields,_
from odoo.http import request
from werkzeug.exceptions import BadRequest


SUCCESS_CODE = 200
DATE_START = 0
DATE_END = 60
LINE_NUMBER = 4
CURR_RATE = 1.0
REASON = 'expense reimb'  
INV_TYPE = 'general_invoice'
EXP_AMOUNT = 1
TAX_RATE = 0
LINE_AEQUENCE = 1


class CreateProfileDataController(http.Controller):
    @http.route('/api/ps_amb/amb_expense_reimb/perf_data_gen', csrf=False, type='http', auth='none', methods=['GET'])
    def amb_expense_reimb_perf_data_gen(self, **kwargs):
        '''
        创建数据—费用报销单
        '''
        try:
            record_length = int(kwargs.get('record_length'))
        except Exception as e:
            return BadRequest('Parms exception, %s' %e)
        doc_type_id = request.env.ref('ps_amb.mdm_document_type_amb_expense_reimb').id
        apply_org_ids = self._get_apply_org()
        if not apply_org_ids:
            return BadRequest('There no useable applying org, please check')
        # 获取申请组织与申请员工之间的对应关系
        apply_org_emp_dict = {}
        for org_id in apply_org_ids:
            employee_dict = self._get_apply_emp(org_id)
            if employee_dict:
                apply_org_emp_dict[org_id] = employee_dict
            else:
                apply_org_ids.remove(org_id)
        if not apply_org_emp_dict:
            return BadRequest('There no useable applicant, please check')
        # 获取费用承担组织，及其与部门，付款组织和币别的关系
        exp_org_ids = self._get_exp_org()
        if not exp_org_ids:
            return BadRequest('There no useable expense bearing org, please check')
        exp_org_dept_dict = {}  # 费用承担组织与部门数据
        exp_pay_org_dict ={}  # 费用承担组织与付款组织数据
        exp_curr_dict = {}  # 费用承担组织与币别数据
        for org_id in exp_org_ids:
            dept_ids = self._get_exp_dept(org_id)
            if dept_ids:
                exp_org_dept_dict[org_id] = dept_ids
            else:
                exp_org_ids.remove(org_id)
            pay_org_ids = self._get_pay_org(org_id)
            if pay_org_ids:
                exp_pay_org_dict[org_id] = pay_org_ids
            exp_curr_dict[org_id] = self._get_local_currency_id(org_id)
        # 无可用费用承担部门
        if not exp_org_dept_dict:
            return BadRequest('There no useable expense bearing dept, please check')
        # 无可用付款组织
        if not exp_pay_org_dict:
            return BadRequest('There no useable payment org, please check')
        date = fields.Date.today()
        exp_item_ids = self._get_exp_item()
        # 无可用费用项目
        if not exp_item_ids:
            return BadRequest('There no useable expense item, please check')

        expense_reimb_obj = request.env['amb.expense.reimb'].with_context({'pass_authorize_check': True})  # 跳过权限控制
        for rec in range(record_length):
            delta_date = random.randint(DATE_START, DATE_END)
            apply_date = date + datetime.timedelta(days=delta_date)  # 申请日期
            apply_org_id = random.choice(apply_org_ids)
            employee_dept_dict = apply_org_emp_dict[apply_org_id]
            apply_emp_ids = list(employee_dept_dict.keys())
            apply_emp_id = random.choice(apply_emp_ids)
            apply_dept_id = employee_dept_dict.get(apply_emp_id, None)
            exp_org_id = random.choice(exp_org_ids)
            pay_org_ids = exp_pay_org_dict[exp_org_id]
            pay_org_id = random.choice(pay_org_ids)
            dept_ids = exp_org_dept_dict[exp_org_id]
            dept_id = random.choice(dept_ids)
            contact_dept = 'mdm.department' + ',' + str(dept_id)
            local_currency_id = exp_curr_dict[exp_org_id]
            line1_ids = []
            for line in range(LINE_NUMBER):
                line_dept_id = random.choice(dept_ids)
                exp_item_id = random.choice(exp_item_ids)
                tax_amount = self._round(EXP_AMOUNT * TAX_RATE, local_currency_id)
                reimb_amount = self._round(EXP_AMOUNT + tax_amount, local_currency_id)
                line1_ids.append(
                    (0, 0, {
                        'exp_dept_id': line_dept_id,
                        'exp_item_id': exp_item_id,
                        'exp_amount': EXP_AMOUNT,
                        'inv_type': INV_TYPE,
                        'tax_rate': TAX_RATE,
                        'tax_amount': tax_amount,
                        'reimb_amount': reimb_amount,
                        'sequence': line + LINE_AEQUENCE
                    })
                    )
                reimb_amount_sum = self._round(reimb_amount_sum + reimb_amount, local_currency_id)
                reimb_amount_sum_local = self._round(reimb_amount_sum * CURR_RATE, local_currency_id)

            expense_reimb_obj.create(
                {'apply_date': apply_date,
                'contact_dept': contact_dept,
                'doc_type_id': doc_type_id,
                'apply_org_id': apply_org_id,
                'apply_emp_id': apply_emp_id,
                'apply_dept_id': apply_dept_id,
                'exp_org_id': exp_org_id,
                'pay_org_id': pay_org_id,
                'currency_id': local_currency_id,
                'local_currency_id': local_currency_id,
                'curr_rate': CURR_RATE,
                'reimb_amount_sum': reimb_amount_sum,
                'reimb_amount_sum_local': reimb_amount_sum_local,
                'reason': REASON,
                'line1_ids': line1_ids,
                }
            )
        return_dict = {
            'code': SUCCESS_CODE,
            'result': '{} records were created'.format(record_length),
        }
        return request.make_response(json.dumps(return_dict))
    
    def _get_local_currency_id(self, exp_org_id):
        '''
        获取本位币
        '''
        org_obj = request.env['sys.admin.orgs']
        result = org_obj.p_get_org_accting_policy_all(org_id=exp_org_id) 
        local_currency_id = result.get('local_currency_id')
        return local_currency_id

    def _get_exp_item(self):
        '''
        获取费用项目
        '''
        exp_item_obj = request.env['mdm.expense.item']
        exp_item_ids = exp_item_obj.search([])
        return exp_item_ids.ids

    def _get_exp_dept(self, exp_org_id):
        '''
        获取费用承担部门
        '''
        department_obj = request.env['mdm.department']
        exp_dept_ids = department_obj.search([('use_org_id', '=', exp_org_id)])
        return exp_dept_ids.ids

    def _get_apply_emp(self, apply_org_id):
        '''
        获取申请人
        '''
        employee_obj = request.env['mdm.employee']
        employee_ids = employee_obj.search([('use_org_id', '=', apply_org_id)])
        employee_dept_dict = {}
        for emp in employee_ids:
            employee_dept_dict[emp.id] = emp.department_id.id
        return employee_dept_dict

    def _get_exp_org(self):
        '''
        获取费用承担组织
        '''
        org_obj = request.env['sys.admin.orgs']
        major_accting_sys = org_obj.p_get_buss_org_in_major_accting_sys()
        orgs_target_ids = org_obj.p_get_fun_orgs('settle')
        exp_org_ids = [org_id for org_id in major_accting_sys if org_id in orgs_target_ids]
        return exp_org_ids

    def _get_pay_org(self, exp_org_id):
        '''
        获取付款组织
        '''
        org_obj = request.env['sys.admin.orgs']
        org_data = org_obj.p_get_org_domain_and_default_pname('amb.expense.reimb', 'pay_org_id', exp_org_id)
        if org_data:
            domain = org_data.get('domain',[])
            pay_org_ids = org_obj.search(domain)
        else:
            pay_org_ids = org_obj.browse([])
        return pay_org_ids.ids 

    def _get_apply_org(self):
        '''
        申请组织过滤
        '''
        user_id = request.env.context.get('uid', None)
        uesr_obj = request.env['res.users']
        user = uesr_obj.browse(user_id)
        env = request.env(user=user)
        org_obj = request.env['sys.admin.orgs'].with_env(env)
        domain = org_obj.p_get_main_org_domain('amb.expense.reimb', option="pre_create")
        apply_org_ids = org_obj.search(domain).ids
        return apply_org_ids

    def _round(self, value, curr_id):
        """
        金额精度处理
        """
        currency_obj = request.env['mdm.currency']
        return currency_obj.p_amount_float_round(value, curr_id)


