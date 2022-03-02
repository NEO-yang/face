# -*- coding: utf-8 -*-
'''
==================================================
@创建人 ：杨兴财
@当前维护人 ：杨兴财
@Desc ：创建银行存款期初性能数据Controller
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
VALUE_INDEX = 1
LINE_NUMBER = 4
CURR_RATE = 1
ENT_OPENING_BALANCE = 1
ENT_OPENING_BALANCE_LC = 1
ENT_ANN_EXPEND_TOTAL = 0
ENT_ANN_EXPEND_TOTAL_LC = 0
ENT_ANN_INCOME_TOTAL = 0
ENT_ANN_INCOME_TOTAL_LC = 0
BALANCE_STATE = True
BANK_OPENING_BALANCE = 1
BANK_OUTSTAN_ACCT_TOTAL = 0
ENT_OUTSTAN_ACCT_TOTAL = 0


class CreateProfileDataController(http.Controller):
    @http.route('/api/ps_cm/cm_opening_bank_balance/perf_data_gen', csrf=False, type='http', auth='none', methods=['GET'])
    def cm_opening_bank_balance_perf_data_gen(self, **kwargs):
        '''
        创建数据—银行存款期初
        '''
        try:
            record_length = int(kwargs.get('record_length'))
        except Exception as e:
            return BadRequest('Parms exception, %s' %e)
        recv_org_ids = self._get_recv_org()
        if not recv_org_ids:
            return BadRequest('There no Receive Organization')
        currency_ids = self._get_currency_id()
        org_date_dict = {}
        org_currency_dict = {}
        org_bank_num_dict = {}
        opening_bank_balance_obj = request.env['cm.opening.bank.balance'].with_context({'pass_authorize_check': True})  # 跳过权限控制
        for i in range(record_length):
            recv_org_id = random.choice(recv_org_ids)
            # 获取日期（有结账取当期，无结账取启用）
            if org_date_dict.get(recv_org_id, None):
                biz_date = org_date_dict.get(recv_org_id)
            else:
                biz_date = self._get_biz_date(recv_org_id)
                org_date_dict[recv_org_id] = biz_date
            # 获取组织本位币
            if org_currency_dict.get(recv_org_id, None):
                currency_id = org_currency_dict.get(recv_org_id)
            else:
                currency_id = self._get_local_currency_id(recv_org_id)
                org_currency_dict[recv_org_id] = currency_id
            # 获取组织下的银行账号
            if org_bank_num_dict.get(recv_org_id, None):
                bank_dict = org_bank_num_dict.get(recv_org_id)
            else:
                bank_dict = self._get_bank_acct_number_id(recv_org_id)
                org_bank_num_dict[recv_org_id] = bank_dict

            if not org_bank_num_dict.get(recv_org_id, None):
                return BadRequest('There no useable bank acct number')
            bank_acct_number_ids = list(org_bank_num_dict[recv_org_id].keys())
            random.shuffle(currency_ids)  # 打乱币别顺序，后续明细行取值
            line_ids = []
            line_number = min(len(currency_ids), LINE_NUMBER)
            for line in range(line_number):
                bank_acct_number_id = random.choice(bank_acct_number_ids)
                bank_id = bank_dict.get(bank_acct_number_id, None)
                line_curr_id = currency_ids[line]
                
                line_ids.append(
                    (0, 0, {
                        'bank_acct_number_id': bank_acct_number_id, 
                        'bank_id': bank_id,
                        'sequence': line + 1,
                        'currency_id': line_curr_id,
                        'curr_rate': CURR_RATE,
                        'ent_opening_balance': ENT_OPENING_BALANCE,
                        'ent_opening_balance_lc': ENT_OPENING_BALANCE_LC,
                        'ent_ann_expend_total': ENT_ANN_EXPEND_TOTAL,
                        'ent_ann_expend_total_lc': ENT_ANN_EXPEND_TOTAL_LC,
                        'ent_ann_income_total': ENT_ANN_INCOME_TOTAL,
                        'ent_ann_income_total_lc': ENT_ANN_INCOME_TOTAL_LC,
                        'balance_state': BALANCE_STATE,
                        'bank_opening_balance': BANK_OPENING_BALANCE,
                        'bank_outstan_acct_total': BANK_OUTSTAN_ACCT_TOTAL,
                        'ent_outstan_acct_total': ENT_OUTSTAN_ACCT_TOTAL,
                    })
                    )
            opening_bank_balance_obj.create(
                {'recv_org_id': recv_org_id,
                'local_currency_id': currency_id,
                'activation_date': biz_date,
                'line_ids': line_ids,
                }
            )
        return_dict = {
            'code': SUCCESS_CODE,
            'result': '{} records were created'.format(record_length),
        }
        return request.make_response(json.dumps(return_dict))

    def _get_local_currency_id(self, recv_org_id):
        '''
        获取本位币
        '''
        org_obj = request.env['sys.admin.orgs']
        result = org_obj.p_get_org_accting_policy_all(org_id=recv_org_id) 
        return result.get('local_currency_id')

    def _get_biz_date(self, org_id):
        '''
        获取启用日期
        '''
        period_params_obj = request.env['sys.period.params']
        biz_date = period_params_obj.search([('org_id', '=', org_id), ('key', '=', 'CM_ACTIVATION_DATE')]).value
        date_with_time = datetime.datetime.strptime(biz_date, DEFAULT_SERVER_DATE_FORMAT)
        date = datetime.datetime.date(date_with_time)
        return date

    def _get_currency_id(self):
        '''
        获取币别数据
        '''
        curr_list = [request.env.ref('ps_mdm.mdm_currency_data_zg_0000').id, 
                request.env.ref('ps_mdm.mdm_currency_data_zg_9999').id]
        currency_obj = request.env['mdm.currency']
        currency_ids = currency_obj.search([('id', 'not in', curr_list)]).ids
        return currency_ids

    def _get_bank_acct_number_id(self, org_id):
        '''
        获取银行账号
        '''
        bank_acct_number_obj = request.env['mdm.bank.acct.number']
        bank_acct_number_ids = bank_acct_number_obj.search([('use_org_id', '=', org_id)])
        bank_dict = {}
        for bank_num in bank_acct_number_ids:
            bank_dict[bank_num.id] = bank_num.bank_id.id
        return bank_dict

    def _get_recv_org(self):
        '''
        收款组织过滤
        只能选择已设置启用日期，未设置结束初始化日期的组织
        '''
        module_obj = request.env['ir.module.module']
        module_id = module_obj.search([('name', '=', 'ps_cm')], limit=1) 
        sys_period_params_obj = request.env['sys.period.params']
        # 找到设置启用的组织
        sys_period_params_ids = sys_period_params_obj.p_get_params(module_id=module_id.id, key=['CM_ACTIVATION_DATE'])
        active_org_ids = []
        for params_id in sys_period_params_ids:
            if isinstance(params_id.get('org_id', None), (list, tuple)):
                active_org_ids.append(params_id['org_id'][ID_INDEX])
        # 去除已经结束初始化的组织
        sys_period_params_init_ids = sys_period_params_obj.p_get_params(
            module_id=module_id.id, 
            org_id=active_org_ids, 
            key=['CM_INIT_DATE'])
        for params_id in sys_period_params_init_ids:
            if isinstance(params_id.get('org_id', None), (list, tuple)):
                active_org_ids.remove(params_id['org_id'][ID_INDEX])
        return active_org_ids
