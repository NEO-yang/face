# -*- coding: utf-8 -*-
'''
==================================================
@创建人 ：杨兴财
@当前维护人 ：杨兴财
@Desc ：创建现金盘点单性能数据Controller
==================================================
'''


import datetime
import json
import random

from odoo import http,fields,_
from odoo.http import request
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from werkzeug.exceptions import BadRequest

SUCCESS_CODE = 200
ID_INDEX = 0
SHEET = 10  # 张数
LINE_NUMBER = 6
CARRYING_AMOUNT = 0  # 账面金额, 根据业务单据生成，与产品确认设置为0
SUPERVISOR_INDEX = 0
CASHIER_INDEX = 1
LINE_ID_INDEX = 0
CURRENCY_INDEX = 1
DAYDELTA = 1

class CreateProfileDataController(http.Controller):
    @http.route('/api/ps_cm/cm_cash_inventory/perf_data_gen', csrf=False, type='http', auth='none', methods=['GET'])
    def cm_cash_inventory_perf_data_gen(self, **kwargs):
        '''
        创建数据—现金盘点单
        '''
        try:
            record_length = int(kwargs.get('record_length'))
        except Exception as e:
            return BadRequest('Parms exception, %s' %e)

        recv_org_ids = self._get_recv_org()
        if not recv_org_ids:
            return BadRequest('There no Recevive Organization')
        user_ids = self._get_user()
        org_record_dict = {}
        face_value_ids, face_value_dict = self._get_face_value_id()
        if not face_value_ids:
            return BadRequest('There no Face Value')
        org_cash_dict = {}  # 组织与现金账号字典
        org_date_dict ={}  # 组织与日期字典
        cash_inventory_obj = request.env['cm.cash.inventory'].with_context({'pass_authorize_check': True})  # 跳过权限控制
        for rec in range(record_length):
            recv_org_id = random.choice(recv_org_ids)
            # 获取现金账号
            if org_cash_dict.get(recv_org_id, None):
                cash_acct_ids = org_cash_dict.get(recv_org_id)
            else:
                cash_acct_ids = self._get_cash_acct_id(recv_org_id)
                org_cash_dict[recv_org_id] = cash_acct_ids
            if not cash_acct_ids:
                return BadRequest('There no Cash Account')
            cash_acct_id = random.choice(cash_acct_ids)
            # 获取日期（有结账取当期，无结账取启用）
            if org_date_dict.get(recv_org_id, None):
                biz_date = org_date_dict.get(recv_org_id)
            else:
                biz_date = self._get_biz_date(recv_org_id)
                org_date_dict[recv_org_id] = biz_date
            
            face_value_id = random.choice(face_value_ids)
            face_value_line_dict = face_value_dict.get(face_value_id, None)
            face_value_line_ids = face_value_line_dict[LINE_ID_INDEX]
            currency_id = face_value_line_dict[CURRENCY_INDEX]
            random.shuffle(user_ids)
            supervisor_uid = user_ids[SUPERVISOR_INDEX]
            cashier_uid = user_ids[CASHIER_INDEX]
            inventory_date = biz_date + datetime.timedelta(days=rec)

            if not org_record_dict.get(recv_org_id, None):
                org_record_dict[recv_org_id] = self._get_record_dict(recv_org_id)
            org_record = org_record_dict.get(recv_org_id, None)
            if org_record:
                while [cash_acct_id, inventory_date, currency_id] in org_record:
                    inventory_date += datetime.timedelta(days=DAYDELTA)
                org_record.append([cash_acct_id, inventory_date, currency_id])

            line_ids = []
            for line in range(LINE_NUMBER):
                face_value_line = random.choice(face_value_line_ids)
                face_value_id = face_value_line.id
                curr_amount = face_value_line.curr_amount
                inventory_amount = self._round(curr_amount * SHEET, currency_id)  # 盘点金额，明细行
                line_ids.append(
                    (0, 0, {
                        'face_value_id': face_value_id, 
                        'sheet': SHEET,
                        'inventory_amount': inventory_amount
                    })
                    )
            cash_inventory_obj.create(
                {'inventory_date': inventory_date,
                'recv_org_id': recv_org_id,
                'cash_acct_id': cash_acct_id,
                'currency_id': currency_id,
                'carrying_amount': CARRYING_AMOUNT,
                'supervisor_uid': supervisor_uid,
                'cashier_uid': cashier_uid,
                'line_ids': line_ids,
                }
            )
        return_dict = {
            'code': SUCCESS_CODE,
            'result': '{} records were created'.format(record_length),
        }
        return request.make_response(json.dumps(return_dict))

    def _get_record_dict(self, recv_org_id):
        '''
        获取当前组织的盘点记录
        '''
        cash_inventory_obj = request.env['cm.cash.inventory']
        records = cash_inventory_obj.search([('recv_org_id', '=', recv_org_id), ('delete_state', '=', 'normal')])
        record_list = []
        for rec in records:
            record_list.append([rec.cash_acct_id.id, rec.inventory_date, rec.currency_id.id])
        return record_list

    def _get_biz_date(self, org_id):
        '''
        获取启用日期或当前期间日期
        '''
        period_params_obj = request.env['sys.period.params']
        init_date = period_params_obj.search([('org_id', '=', org_id), ('key', '=', 'CM_INIT_DATE')]).value
        current_start_date = period_params_obj.search([('org_id', '=', org_id), ('key', '=', 'CM_CURR_START_DATE')]).value
        if current_start_date:
            biz_date = current_start_date
        else:
            biz_date = init_date
        date_with_time = datetime.datetime.strptime(biz_date, DEFAULT_SERVER_DATE_FORMAT)
        date = datetime.datetime.date(date_with_time)
        return date

    def _get_user(self):
        '''
        获取用户
        '''
        user_obj = request.env['res.users']
        user_ids = user_obj.sudo().search([])
        return user_ids.ids

    def _get_face_value_id(self):
        '''
        获取面值定义
        '''
        face_value_obj = request.env['mdm.face.value'].with_context(disable_state_filter=True)
        face_value_ids = face_value_obj.search([('delete_state','=','normal')])
        face_value_dict = {}
        for value in face_value_ids:
            face_value_dict[value.id] = [value.line_ids, value.currency_id.id]
        return face_value_ids.ids, face_value_dict

    def _get_cash_acct_id(self, org_id):
        '''
        获取现金账号
        '''
        cash_acct_obj = request.env['mdm.cash.acct.number']
        cash_acct_ids = cash_acct_obj.search([
            ('use_org_id', '=', org_id)
            ])
        return cash_acct_ids.ids

    def _get_recv_org(self):
        '''
        收款组织过滤
        只能选择已设置结束初始化日期的组织
        '''
        module_obj = request.env['ir.module.module']
        module_id = module_obj.search([('name', '=', 'ps_cm')], limit=1) 
        sys_period_params_obj = request.env['sys.period.params']
        sys_period_params_ids = sys_period_params_obj.p_get_params(module_id=module_id.id, key=['CM_INIT_DATE'])
        active_org_ids = []
        for params_id in sys_period_params_ids:
            if isinstance(params_id.get('org_id', None), (list, tuple)):
                active_org_ids.append(params_id['org_id'][ID_INDEX])
        return active_org_ids

    def _round(self, value, curr_id):
        '''
        金额精度处理
        '''
        currency_obj = request.env['mdm.currency']
        return currency_obj.p_amount_float_round(value, curr_id)
