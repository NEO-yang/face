# -*- coding: utf-8 -*-
#  天和堂凭证打印默认制单人为登录用户
'''
==================================================
@创建人 ：程相燊
@当前维护人 ：程相燊
@Desc ：凭证打印参数设置
==================================================
'''
import json
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

from odoo.addons.ps_mdm.common import mdm_currency as curr
from odoo.addons.ps_admin.sys_ele.sys_ele_ctrl import sys_ele_ctrl
from odoo.addons.ps_admin.biz_log.models.biz_log_item import LogCategory, LogLevel
from odoo.addons.ps_admin.biz_log.models.biz_log_item import BizLogItem


DEFAULT_CODE_LENGTH = 5 # 默认的凭证编码规则长度


class GlVoucherPrintSettings(models.TransientModel):
    _name = 'gl.voucher.print.settings'
    _inherit = 'config.settings.base'
    _description = 'Voucher Print Settings' # 凭证打印参数


    ################################  默认值区 start  ################################

    def _default_org_id(self):
        """
        默认组织
        """
        org_id = self.env.user.ps_curr_org_id
        domain = self.env['sys.admin.orgs'].p_get_main_org_domain(self._name, option='read')
        access_org = self.env['sys.admin.orgs'].search(domain) if domain else None
        if len(org_id) == 1 and org_id.account_organization != 'empty' and org_id.state == 'audit' and org_id.id in access_org.ids:
            return org_id.id

    def _default_voucher_create_uids(self):
        """
        默认制单人，仅对第一次打开有效
        """
        return [self.env.user.id]

    ################################  默认值区 end   ################################


    ################################  字段定义区 start  ################################
    
    org_domains = fields.One2many('sys.admin.orgs',compute='_compute_org_domains')  # 组织过滤
    org_id = fields.Many2one('sys.admin.orgs', string="Organization", domain="[('id','in',org_domains)]", 
        default=lambda self: self._default_org_id())  # 组织
    act_book_id = fields.Many2one('mdm.account.book', string='Account Book',
        domain = "[('accting_org_id', '=', org_id), ('forbid_state', '=', 'normal')]")  # 账簿
    acct_table_id = fields.Many2one('mdm.account.table', related='act_book_id.acct_table_id', string='Account Charts')  # 科目表

    # ----凭证打印格式
    print_template_id = fields.Many2one('print.template',string="Print Template", 
        domain = "[('use_org_id', '=', org_id), ('delete_state', '=', 'normal'), ('is_published', '=', True), ('model', '=', 'gl.voucher')]")  # 凭证输出格式
    combine_rule_id = fields.Many2one('gl.voucher.combine.rule',string='Combine Rule',
        domain = "[('use_org_id', '=', org_id), ('acct_book_id', '=', act_book_id), ('state', '=', 'audit'), ('forbid_state', '=', 'normal'), ('delete_state', '=', 'normal')]")  # 分录合并规则

    # ----凭证打印范围  
    voucher_word_ids = fields.Many2many('mdm.voucher.word', string='Voucher Word', 
        domain = "[('use_org_id', '=', org_id), ('acct_table_id', '=', acct_table_id)]")  # 凭证字
    voucher_num_limits = fields.Char(string='Voucher Number Limits',store=True)  # 凭证编号范围
    voucher_create_uids = fields.Many2many('res.users', string="Creater", domain="[('ps_forbid_state', '=', 'normal')]",
        default=lambda self: self._default_voucher_create_uids())  # 制单人
    
    ################################  字段定义区 end   ################################
    

    ################################  计算方法区 start  ################################

    @api.depends('org_id')
    def _compute_org_domains(self):
        domain = self.env['sys.admin.orgs'].p_get_main_org_domain(self._name, option='pre_write') or []
        domain.append(('account_organization', '!=', 'empty'))  # 过滤非核算组织
        self.org_domains = self.env['sys.admin.orgs'].search(domain)

    ################################  计算方法区 end   ################################

    ################################  onchange方法区  start  ################################

    @api.onchange('org_id')
    def _onchange_org_id(self):
        """
        获取参数值
        """
        self.ensure_one()
        if self.org_id:
            act_book_id = self.env['mdm.account.book'].search([('accting_sys_id.is_major_accting_sys', '=', True),('book_type', '=', 'main'), ('accting_org_id', '=', self.org_id.id)], limit=1)
            if act_book_id.accting_sys_id.is_major_accting_sys:
                self.act_book_id = act_book_id.id
            else:
                self.act_book_id = None
        else:
            self.act_book_id = None
        
    @api.onchange('act_book_id')
    def _onchange_act_book_id(self):
        """
        获取参数值
        """
        self.ensure_one()
        self._get_values()
        if self.org_id and self.act_book_id:
            # 默认打印模板
            if not self.print_template_id:
                self.print_template_id = self.env['print.template'].search([
                    ('model', '=', 'gl.voucher'),
                    ('use_org_id', '=', self.org_id.id), 
                    ('is_published', '=', True), 
                    ('delete_state', '=', 'normal')
                ], limit=1).id
            
            # 默认分录合并
            if not self.combine_rule_id:
                self.combine_rule_id = self.env['gl.voucher.combine.rule'].search([
                    ('use_org_id', '=', self.org_id.id), 
                    ('acct_book_id', '=', self.act_book_id.id), 
                    ('state', '=', 'audit'), 
                    ('forbid_state', '=', 'normal'), 
                    ('delete_state', '=', 'normal')
                ], limit=1).id

    @api.onchange('voucher_num_limits')
    def _onchange_voucher_num_limits(self):
        """
        校验编号参数
        """
        # 为空或者存在非法字符
        if not self._is_valid(self.voucher_num_limits):
            self.voucher_num_limits = '0'
            return {
                'warning': {
                    'title': _('Something went wrong !'),
                    'message': _('Only numbers、- 、and , are allowed'),
                    'type': 'warning'
                },
            }
      
    ################################  onchange方法区  end   ################################


    ################################  约束方法区  start  ################################

    ################################  约束方法区  end   ################################


    ################################  服务器动作区  start  ################################

    ################################  服务器动作区  end   ################################


    ################################  按钮动作区  start  ################################

    ################################  按钮动作区  end   ################################


    ################################  私有方法区  start  ################################

    def _is_valid(self, number_limit):
        """
        判断编号设置是合法的
        """
        letters = ['0','1','2','3','4','5','6','7','8','9','0','-',',']
        # 为空或者存在非法字符
        if not number_limit or not isinstance(number_limit, str) or [ch for ch in number_limit if ch not in letters]:
            return False
        return True

    # 返回对应的参数
    def _get_fields_dict(self):
        """
        返回字段 name + 默认值 的列表
        :param:
            self: 当前模型对象(obj)
        :return: fields_dict --> dict
        """
        return {
            'print_template_id': False, 
            'combine_rule_id': False, 
            'voucher_word_ids': False, 
            'voucher_num_limits': '0',
            'voucher_create_uids': [self.env.ref('ps_admin.1001_super_admin_role_roles_ps_admin').id],
        }

    def _get_voucher_max_number(self, print_setting, code_length):
        """
        获取凭证的最大编号
        @param print_setting: 打印设置
        @param code_length: 流水号编号长度
        """
        number = self.env['gl.voucher'].search([
            ('acct_book_id', '=', print_setting.act_book_id.id),
            ('voucher_word_id', 'in', print_setting.voucher_word_ids.ids),
            ('create_uid', 'in', print_setting.voucher_create_uids.ids),
            ('number', '!=', False),
            ('delete_state', '=', 'normal')
        ], order='id desc', limit=1).number
        number = number[-code_length:] if number else ''
        return int(number) if number.isdigit() else 0

    def _is_match_conditions(self, voucher_data, number_limits, print_setting, code_length):
        '''
         判断是否满足打印条件
        @param voucher_data: 凭证表头打印数据
        @param number_limits: 打印范围, 如果为None，代表没有限制
        @param print_setting: 打印设置
        @param code_length: 流水号编号长度
        '''
        for field_name in ('accting_org_id', 'acct_book_id', 'voucher_word_id', 'create_uid', 'number'):
            if field_name not in voucher_data:
                return False
        number = voucher_data['number'][-code_length:] if voucher_data.get('number', None) else None
        if voucher_data['accting_org_id'] == print_setting.org_id.id \
            and voucher_data['acct_book_id'] == print_setting.act_book_id.id \
            and voucher_data['voucher_word_id'] in print_setting.voucher_word_ids.ids \
            and voucher_data['create_uid'] in print_setting.voucher_create_uids.ids \
            and (number_limits is None or number in number_limits):
            return True
        return False

    def _get_voucher_print_data(self, print_data, print_setting):
        '''
         根据打印设置中的凭证打印范围，过滤打印数据
        :param print_data(dic): 打印数据
        :param print_setting: 打印设置
        '''
        if not print_setting.voucher_num_limits:
            return {
                'gl_voucher': [],
                'gl_voucher_line1': []
            }
        # 根据默认编码规则，补齐生成编号列表
        model_id = self.env['ir.model'].search([('model', '=', 'gl.voucher')]).id
        code_length = self.env['ps.code.rule.line'].search([
            ('parent_id.code_model_id', '=', model_id), 
            ('parent_id.is_default_rule', '=', True),
            ('parent_id.state', '=', 'audit'), 
            ('parent_id.forbid_state', '=', 'normal'), 
            ('is_coding_element', '=', True),
            ('code_type', '=', 'serial_number'),
            ('delete_state', '=', 'normal')], limit=1).code_length or DEFAULT_CODE_LENGTH
        voucher_num_limits = print_setting.voucher_num_limits.replace(' ', '')
        number_limits = []
        # 如果设置为空，则不打印
        if not self._is_valid(voucher_num_limits):
            pass
        # 如果设置中有逗号或短线
        elif '-' in voucher_num_limits or ',' in voucher_num_limits:
            number_ranges = voucher_num_limits.split(',')
            for number_range in number_ranges:
                numbers = number_range.split('-')
                if len(numbers) == 1:
                    number_limits.extend(numbers)
                else:
                    start = int(numbers[0]) if numbers[0] else 1
                    end = int(numbers[-1]) if numbers[-1] else self._get_voucher_max_number(print_setting, code_length)
                    number_limits.extend([str(n) for n in range(start, end + 1)])     
        # 如果为0，代表没有限制，否则为单条
        else:
            number_limits = None if voucher_num_limits == '0' else [voucher_num_limits]
        
        # 根据编号长度，补齐编号
        if number_limits:
            number_limits = [n.zfill(code_length) for n in number_limits]
        
        vouchers = []
        voucher_ids = []
        for voucher in print_data.get('gl_voucher', []):
            if voucher.get('id') and self._is_match_conditions(voucher, number_limits, print_setting, code_length):
                voucher_ids.append(voucher['id'])
                vouchers.append(voucher)

        # 筛选后的凭证表头和表体
        return {
            'gl_voucher': vouchers,
            'gl_voucher_line1': [line for line in print_data.get('gl_voucher_line1', []) if line.get('parent_id', None) in voucher_ids]
        }

    def _add_float_str(self, str1, str2, currency_id):
        """
        将两个float的字符串，根据币别进行格式化、相加，返回格式化后的字符串（含千分位）
        """
        precision = self.env['mdm.currency'].p_get_all_currency_precision().get(currency_id, {}).get('amount_precision', 2)
        float1 = tools.float_round(float(str1.replace(',', '')), precision_digits=precision)
        float2 = tools.float_round(float(str2.replace(',', '')), precision_digits=precision)
        float_value = tools.float_round(float1 + float2, precision_digits=precision)
        float_format = '{:,.%sf}' % precision
        return float_format.format(float_value)


    def _combine_voucher(self, voucher_lines, line_index_mapping, line_data, account_id, account_name, local_curr_id_mapping):
        """
        合并凭证
        @param voucher_lines: 合并凭证列表
        @param line_index_mapping: 合并key及凭证行数的对应关系
        @param line_data: 需要合并处理的凭证行
        @param account_id: 合并后的科目id
        @param account_name: 合并后的科目名称
        """
        currency_id = line_data['currency_id']
        # 同一凭证中，按照摘要、币别、汇率、科目、辅助核算、借贷方向进行合并
        debit = float(line_data.get('debit', '0').replace(',', ''))
        is_debit = not self.env['mdm.currency'].p_amount_float_is_zero(debit, currency_id)
        parent_id = line_data.get('parent_id', None) # 凭证头id
        combine_key = (parent_id, line_data['summary'], line_data['currency_id'], line_data['curr_rate'], account_id, line_data['auxiliary'], is_debit)

        if combine_key in line_index_mapping:
            combine_data = voucher_lines[line_index_mapping[combine_key]]
            amount = self._add_float_str(combine_data.get('amount', '0'), line_data.get('amount', '0'), currency_id)
            local_currency_id = local_curr_id_mapping.get(parent_id, None)
            debit_local = self._add_float_str(combine_data.get('debit_local', '0'), line_data.get('debit_local', '0'), local_currency_id)
            credit_local = self._add_float_str(combine_data.get('credit_local', '0'), line_data.get('credit_local', '0'), local_currency_id)
            # 合并
            combine_data.update({
                'amount': amount,
                'debit': amount if is_debit else 0,
                'debit_local': debit_local,
                'credit': 0 if is_debit else amount,
                'credit_local': credit_local
            })
        else:
            line_index_mapping[combine_key] = len(voucher_lines)
            line_data['account_id'] = account_id
            line_data['account_id_name'] = account_name
            voucher_lines.append(line_data)

    ################################  私有方法区  end   ################################


    ################################  公共方法区  start  ################################
  
    ################################  公共方法区  end   ################################


    ################################  覆盖基类方法区  start  ################################

    @api.model
    @sys_ele_ctrl()
    def pre_write(self, res):
        return super(GlVoucherPrintSettings, self).pre_write(res)

    @sys_ele_ctrl()
    def read(self, fields=None, load='_classic_read'):
         return super(GlVoucherPrintSettings, self).read(fields, load)

    @sys_ele_ctrl()
    def execute(self):
        """
        点击保存按钮，执行打印预览
        :param:
            self: 当前模型对象(obj)
        :return:
        """
        if self.env.context.get('open') == 'setting':
            self._set_values()
            return self._get_return_view()
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'print_preview',
                'name': _('Print Preview'),
                'display_name': _('Print Preview'),
                'params': {
                    'template_id': self.print_template_id.id,
                    'res_ids': json.dumps(self.env.context.get('id', [])),
                    'res_model': 'gl.voucher',
                    'hook_model': 'gl.voucher.print.settings', 
                    'hook_method': 'hook_print_vouchers', 
                    'hook_method_kw': json.dumps({'rec_id':self.id}),
                }
            }
        
    ################################  覆盖基类方法区  end   ################################


    ################################  其他方法区  start  ################################
                
    def hook_print_vouchers(self, print_data, hook_method_kw):
        '''
         根据打印设置中的分录合并规则，对打印数据进行重组
        :param print_data(dic): 打印数据
        :param hook_method_kw(dic): 其中包含了设置记录的id
        '''
        if 'rec_id' not in hook_method_kw:
            return {}
        print_setting = self.browse(hook_method_kw['rec_id'])  # 获取运行时设置
        print_data = self._get_voucher_print_data(print_data, print_setting)  # 根据凭证范围设置对打印数据进行过滤

        combine_config = print_setting.combine_rule_id.get_combine_rule_line()  # 分录合并规则明细字典,若不合并，则为空
        # 如果合并规则为空，则不合并直接返回，否则根据配置进行合并
        if not combine_config:
            return print_data
        else:
            local_curr_id_mapping = {v['id']: v.get('local_currency_id', None) for v in print_data.get('gl_voucher', [])}
            voucher_lines_temp = [] # 重组后的凭证分录打印数据列表
            line_index_mapping = {}
            for line_data in print_data.get('gl_voucher_line1', []):
                account_id = line_data.get('account_id', None)  # 该行科目的id
                # 如果没有在合并配置中，则代表不需要合并，直接更新voucher_lines_temp；否则，更新到voucher_line_data中进行合并
                if account_id not in combine_config:
                    voucher_lines_temp.append(line_data)
                else:
                    account_id, account_name = combine_config.get(account_id)
                    self._combine_voucher(voucher_lines_temp, line_index_mapping, line_data, account_id, account_name, local_curr_id_mapping)

            # 合并后可能会有明细行借贷都为0的情况，需要去除这种明细行，及空表头
            # 去除合并后的空表头
            parent_ids = set()
            voucher_lines = []
            for line_data in voucher_lines_temp:
                amount = float(line_data.get('amount', '0').replace(',', ''))
                if not self.env['mdm.currency'].p_amount_float_is_zero(amount, line_data['currency_id']):
                    voucher_lines.append(line_data)
                    parent_ids.add(line_data['parent_id'])
            return {
                'gl_voucher': [voucher for voucher in print_data.get('gl_voucher', []) if voucher['id'] in parent_ids],
                'gl_voucher_line1': voucher_lines
            }

    ################################  其他方法区  end   ################################
