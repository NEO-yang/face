# -*- coding: utf-8 -*-
'''
==================================================
@创建人 ：郑兆涵
@当前维护人 ：郑兆涵
@Desc ：查询报表 - 现金流水账
==================================================
'''
import re
import datetime

from odoo import models, fields, api, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.addons.ps_query.ps_query_control.models.spreadjs_query import QueryTable, QueryCell, ClickEvent
from odoo.addons.ps_admin.sys_ele.sys_ele_ctrl import sys_ele_ctrl
from odoo.tools.profiler import profile


# 定义未审核时需要查询的单据模型，以及单据模型对应的明细行模型
DOC_MODELS = [
    ('cm.cash.recycling', 'cm.cash.recycling.line', []),  # 现金存取单
    ('cm.transfer.settle', 'cm.transfer.order', [('document_type', '=', 'cash_transfer')]),  # 转账单
    ('cm.transfer.settle', 'cm.foreign.exchange', [('document_type', '=', 'foreign_cash')]),  # 购汇单
    ('cm.receivable.bill', 'cm.receivable.bill.line1.sale', []),  # 收款单
    ('cm.receivable.refund.bill', 'cm.receivable.refund.bill.line1.sale', []),  # 收款退款单
    ('cm.payable.bill', 'cm.payable.bill.line1', []),  # 付款单
    ('cm.payable.refund.bill', 'cm.payable.refund.bill.line1', []),  # 付款退款单
    ('cm.manual.journal', 'cm.manual.journal.line1', []),  # 现金手工日记账
]


# 各单据对应的action
BILL_ACTION = {
    'cm.cash.recycling': 'ps_cm.action_cm_cash_recycling',  # 现金存取单
    'cm.transfer.settle': 'ps_cm.action_cm_transfer_settle_order',  # 转账购汇单
    'cm.receivable.bill': 'ps_cm.action_cm_receivable_bill',  # 收款单
    'cm.receivable.refund.bill': 'ps_cm.action_cm_refund_bill',  # 收款退款单
    'cm.payable.bill': 'ps_cm.action_view_cm_payable_bill',  # 付款单
    'cm.payable.refund.bill': 'ps_cm.action_view_cm_refound_bill',  # 付款退款单
    'cm.manual.journal': 'ps_cm.action_cm_manual_journal',  # 现金手工日记账
}

# 各单据对应的穿透事件
CLICK_TYPE_DICT = {
    'cm.cash.recycling': 'cash_journal_to_cash_recycling',  # 现金存取单
    'cm.transfer.settle': 'cash_journal_to_transfer_settle_order',  # 转账购汇单
    'cm.receivable.bill': 'cash_journal_to_receivable_bill',  # 收款单
    'cm.receivable.refund.bill': 'cash_journal_to_receivable_bill_refund',  # 收款退款单
    'cm.payable.bill': 'cash_journal_to_payable_bill',  # 付款单
    'cm.payable.refund.bill': 'cash_journal_to_payable_refound_bill',  # 付款退款单
    'cm.manual.journal': 'cash_journal_to_manual_journal',  # 现金手工日记账
}


class CmCashJournalQuery(models.TransientModel):
    _name = 'cm.cash.journal.query'
    _description = 'Cm Cash Journal Query'  # 查询 - 现金流水账

    ################################  default start  ################################

    def _get_recpay_org_domain(self):
        """
        获取收付组织过滤
        """
        return self.env['sys.admin.orgs'].p_get_main_org_domain(self._name, option='read') or []

    ################################  default end    ################################


    ################################  字段定义区 start  ################################

    recpay_org_id = fields.Many2one('sys.admin.orgs', string='Receivable Payable Organization', 
        domain=lambda self: self._get_recpay_org_domain())  # 收付组织
    cash_acct_number_ids = fields.Many2many('mdm.cash.acct.number', string='Cash Account Number')  # 现金账号
    currency_ids = fields.Many2many('mdm.currency', string='Currency', default=lambda self: [(6, 0, [self.env.ref('ps_mdm.mdm_currency_data_zg_0000').id])])  # 币别
    start_date = fields.Date(string='Start Date', default=fields.Date.today())  # 开始日期
    end_date = fields.Date(string='End Date', default=fields.Date.today())  # 结束日期
    is_day = fields.Boolean(string='Is Day')  # 本日
    is_week = fields.Boolean(string='Is Week')  # 本周
    is_month = fields.Boolean(string='Is Month')  # 本月
    is_total = fields.Boolean(string='Is Total')  # 显示合计数
    is_local_currency = fields.Boolean(string='Is Local Currency')  # 显示本位币
    is_include_unaudit_doc = fields.Boolean(string='Is Include Unaudit')  # 包含未审核单据

    ################################  字段定义区 end    ################################


    ################################  计算方法区 start  ################################
 
    ################################  计算方法区 end    ################################


    ################################  onchange方法区  start  ################################

    @api.onchange('recpay_org_id')
    def _onchange_recpay_org_id(self):
        """
        切换首付组织时，清空已选现金账号
        """
        for rec in self:
            org_ids = rec.cash_acct_number_ids.use_org_id.ids
            if {rec.recpay_org_id.id} != set(org_ids):
                rec.cash_acct_number_ids = None
        

    ################################  onchange方法区  end    ################################


    ################################  约束方法区  start  ################################
    
    ################################  约束方法区  end    ################################


    ################################  服务器动作区  start  ################################
    
    ################################  服务器动作区  end    ################################


    ################################  按钮动作区  start  ################################

    ################################  按钮动作区  end    ################################


    ################################  私有方法区  start  ################################

    def _get_default_org_id(self):
        """
        @desc: 获取默认的组织
        @params: self: 当前示例对象
        
        @return: org_id: 获取到的满足条件的组织id
        """
        # 定义获取到的且满足条件的组织id（后续会处理该字段）
        org_id = 0

        # 获取当前登陆用户的组织
        login_user_org_id = self.env.user.ps_curr_org_id.id
        
        # 获取用户有权限的组织
        org_id_domain = self.env['sys.admin.orgs'].p_get_main_org_domain(self._name,option='read')
        
        if not org_id_domain:
            return org_id

        default_org_id_list = self.env['sys.admin.orgs'].search(org_id_domain)
        if login_user_org_id in default_org_id_list.ids:
            org_id = login_user_org_id

        return org_id

    def _get_activation_date(self, domain_fields):
        """
        @desc: 获取当前查询条件中的所选组织的启用日期
        @params: self: 当前示例对象
        @params: domain_fields: 字段选择过滤条件

        @return: activation_date: 启用日期（str类型）
        """
        # 获取当前模块
        module_id = self.env['ir.module.module'].search([('name', '=', self._module)], limit=1) 

        # 获取出纳启用日期，判断查询条件开始日期大于等于启用日期
        sys_period_params_list = self.env['sys.period.params'].p_get_params(
            module_id = module_id.id,
            org_id = domain_fields['recpay_org_id'],
            key = 'CM_ACTIVATION_DATE'
        )

        if len(sys_period_params_list) == 0:
            raise ValidationError(_('The current organization has not set the activation date. Please set the activation date first!'))  # 当前组织未进行启用日期设置，请先设置启用日期！

        if len(sys_period_params_list) > 1:
            raise ValidationError(_('In the background system time parameter table, the activation date setting data is incorrect!'))  # 后台系统时间参数表中，启用日期设置数据有误！

        # 获取启用日期的key对应的value时间
        activation_date = str(sys_period_params_list[0]['value'])

        return activation_date

    def _get_currency_ids(self, domain_fields):
        """
        @desc: 组织动态隐藏列
        @params: self: 当前示例对象
        @params: domain_fields: 字段选择过滤条件

        @return: hidden_cols: 动态隐藏列list
        """
        # 定义币别为用户选择的币别
        currency_id_list = domain_fields['currency_ids']

        # 从币别预置数据中获取所有币别
        all_currency_id = self.env.ref('ps_mdm.mdm_currency_data_zg_0000')

        # 从币别预置数据中获取综合本位币币别
        zhbwb_currency_id = self.env.ref('ps_mdm.mdm_currency_data_zg_9999')

        if not all_currency_id:
            raise ValidationError(_('Not all currencies obtained from currency table!'))  # 未从币别表中获取到所有币别和综合本位币币别！
        if all_currency_id.id in currency_id_list:
            currency_id_list = [currency.id for currency in self.env['mdm.currency'].search([
                ('id', 'not in', [all_currency_id.id, zhbwb_currency_id.id])
            ])]
        
        return currency_id_list

    def _check_domain_fields(self, domain_fields):
        """
        @desc: 字段校验（必填、日期大小）
        @params: self: 当前示例对象
        @params: domain_fields: 字段选择过滤条件

        @return: None
        """
        if domain_fields['start_date'] > domain_fields['end_date']:
            raise ValidationError(_('Start date must be less than or equal to end date!'))  # 开始日期必须小于等于结束日期！

        # 获取当前查询条件中的所选组织的启用日期
        activation_date = self._get_activation_date(domain_fields)

        if str(domain_fields['start_date']) < str(activation_date):
            raise ValidationError(_('The start date cannot be earlier than the active date, please check!'))  # 开始日期不能小于组织启用日期，请检查！
        
    def _get_query_cell_title(self, domain_fields):
        """
        @desc: 组织副表头数据
        @params: self: 当前示例对象
        @params: domain_fields: 字段选择过滤条件

        @return: None
        """
        recpay_org_id = self.env['sys.admin.orgs'].browse(int(domain_fields['recpay_org_id']))
        acct_number_ids = self.env['mdm.cash.acct.number'].browse(domain_fields['cash_acct_number_ids'])
        date = str(domain_fields['start_date']).replace('-', '') + '-' + str(domain_fields['end_date']).replace('-', '')
        
        acct_number = ''
        for acct_number_id in acct_number_ids:
            acct_number += str(acct_number_id.cash_acct_number) + ' / '

        return {
            'recpay_org': (_('Recpay Org: ')) + recpay_org_id.name,  # 收付组织：
            'acct_number': (_('Acct Number: ')) + acct_number[:-3:],  # 现金账号：
            'date': (_('Date: ')) + date,  # 日期：
        }

    def _get_capital_balance_data(self, domain_fields, cash_acct_number_dict):
        """
        @desc: 获取并组织资金余额表相关数据记录到yesterday_balance_dict中
        @params: self: 当前示例对象
        @params: domain_fields: 字段选择过滤条件

        @return: yesterday_balance_dict: 组织好的昨日结存数据字典
        """
        # 昨日结存数据字典
        yesterday_balance_dict = dict()
        # 获取当前查询组织的启用日期
        '''
        这里需要注意：
            如果代码能够运行到这里，说明业务逻辑已经通过了组织校验，查询条件中一定存在收付组织字段
            且这个收付组织一定是已启用 + 已初始化状态
            因此我们一定能够从后台系统期间参数表中获取到出纳下 key 为 activation_date 的记录，并获取它的 value 值
        '''
        # 获取当前查询条件中的所选组织的启用日期
        activation_date = self._get_activation_date(domain_fields)
        recpay_org_id = self.env['sys.admin.orgs'].browse(domain_fields['recpay_org_id'])
        currencys = self.env['mdm.currency'].browse(domain_fields['currency_ids']).read(['name'])
        yesterday_balance = _('Yesterday Balance')

        for cash_acct_number_id, cash_acct_number_data in cash_acct_number_dict.items():
            cash_acct_number_str = 'mdm.cash.acct.number,%s' % cash_acct_number_id
            for currency in currencys:
                # 获取以（收付组织、账号、币别、结束日期）条件找出的数据中以不同币别区分，同收付组织、同账号、同结束日期下，不同币别的数据
                # 这里可能出现多条数据，我们取以结束日期end_date为基准的倒数第一条，则为最新一次的结账数据
                capital_balance = self.env['cm.capital.balance.record'].search([
                    ('recpay_org_id', '=', domain_fields['recpay_org_id']),
                    ('currency_id', '=', currency['id']),
                    ('acct_number_id', '=', cash_acct_number_str),
                    ('end_date', '<', domain_fields['start_date'])
                ], order='end_date desc', limit=1)
                cash_incomes = self.env['cm.cash.income.expense'].search([
                    ('recpay_org_id', '=', domain_fields['recpay_org_id']),
                    ('cash_acct_number_id', '=', cash_acct_number_id),
                    ('currency_id', '=', currency['id']),
                    ('biz_date', '>', capital_balance.end_date if capital_balance else datetime.datetime.strptime(activation_date, '%Y-%m-%d').date() - datetime.timedelta(days=1)),
                    ('biz_date', '<', domain_fields['start_date'])
                ])

                is_to_show = True if capital_balance else False
                end_period_balance = capital_balance.end_period_balance
                end_period_balance_local = capital_balance.end_period_balance_local
                local_currency_id = capital_balance.local_currency_id
                for cash_income in cash_incomes:
                    # 直接更新资金余额表中获取到的数据
                    end_period_balance += cash_income.income_amount - cash_income.expense_amount
                    end_period_balance_local += cash_income.income_amount_local - cash_income.expense_amount_local

                    if not local_currency_id:
                        local_currency_id = cash_income.local_currency_id
                    if not is_to_show:
                        # 这里意思是，因为yesterday_balance_dict里面有所有的收付组织维度和币别维度，所有有可能有一些是直接创建的dict，而不是通过资金余额表获取到的对象创建的
                        # 因此没有数据，则is_to_show这个key将会是False,但是当我们更新了这个key的value时，我们就需要把这个key更新为True，将来用于展示使用
                        is_to_show = True

                # 组织key时，以（账号id、币别id）为维度进行分组
                key = (cash_acct_number_id, currency['id'])
                # 如果该（组织、币别、现金账号、日期）维度下未获取到资金余额表数据，则直接组织一条空的数据（后续可能进行相关删除操作）
                yesterday_balance_dict[key] = {
                    'recpay_org_id': recpay_org_id.name,  # 收付组织
                    'acct_number_id': _('Acct Number:') + (cash_acct_number_data['cash_acct_number'] or '') + _(';Acct Name:') + (cash_acct_number_data['name'] or ''),  # 账号（账号：）（；账户名称：）
                    'biz_date': activation_date, # 业务日期（默认给当前查询组织的启用日期）
                    'summary': yesterday_balance, # 摘要（昨日结存）
                    'currency_id': currency['name'],  # 币别
                    'currency_id_id': currency['id'], # 币别id
                    'local_currency_id': local_currency_id.name or '', # 本位币
                    'local_currency_id_id': local_currency_id.id, # 本位币id
                    'end_period_balance': end_period_balance,
                    'end_period_balance_local': end_period_balance_local,
                    'is_to_show': is_to_show # 定义这个key是为了区别是否将来需要展示该数据，从而导致相关明细数据是否展示
                }

        return yesterday_balance_dict

    def _get_query_period_dict(self, domain_fields, yesterday_balance_dict):
        """
        @desc: 从现金收支表中获取查询期间内的数据，并组织在query_period_dict中
        @params: self: 当前示例对象
        @params: domain_fields: 字段选择过滤条件
        @params: yesterday_balance_dict: 组织好的昨日结存数据字典

        @return: query_period_dict: 组织好的查询期间内的数据
        """
        # 定义查询期间内的数据的字典query_period_dict
        query_period_dict = dict()

        record = self.env['cm.cash.income.expense'].search([
            ('recpay_org_id', '=', domain_fields['recpay_org_id']),
            ('cash_acct_number_id', 'in', domain_fields['cash_acct_number_ids']),
            ('currency_id', 'in', domain_fields['currency_ids']),
            ('biz_date', '>=', domain_fields['start_date']),
            ('biz_date', '<=', domain_fields['end_date'])
        ], order='cash_acct_number_id asc, currency_id asc, biz_date asc, number asc')
        
        # 如果未获取到数据，则该查询期间内，现金收支表没有数据发生，则不会进入for循环
        for res in record:
            local_currency_name = res.local_currency_id.name or ''
            local_currency_id_id = res.local_currency_id.id
            # 组织yesterday_balance_key用于查找yesterday_balance_dict内的key对应value中是否有is_to_show为False的数据
            # 这里不需要判断yesterday_balance_dict.get(yesterday_balance_key)，因为yesterday_balance_dict中的key一定是最全的
            # 因为这里是为了组织明细行数据，因此明细行数据存在，则要展示明细行数据，因此明细行对应的昨日结存数据也需要展示出来，因此更新is_to_show为True
            yesterday_balance_key = (res.cash_acct_number_id.id, res.currency_id.id)
            if not yesterday_balance_dict[yesterday_balance_key]['is_to_show']:
                yesterday_balance_dict[yesterday_balance_key]['is_to_show'] = True
                yesterday_balance_dict[yesterday_balance_key]['local_currency_id'] = local_currency_name  # 本位币
                yesterday_balance_dict[yesterday_balance_key]['local_currency_id_id'] = local_currency_id_id  # 本位币id

            '''
            定义每一个查询出来的现金收支表数据的数据组织字典new_dict
            这里的字典将会依据date的不同以key对应value（value为列表，value列表内有多个new_dict）这种形式
            
            注意：这里query_period_dict的形式：
            query_period_dict = {
                'acct_number_id_1_currency_id_1_biz_date_XXXX-XX-XX': [
                    {对应明细行当天发生的第一条数据信息},
                    {对应明细行当天发生的第二条数据信息},
                    {对应明细行当天发生的第三条数据信息}
                ],
                'acct_number_id_1_currency_id_3_biz_date_XXXX-XX-XX': [
                    {对应明细行当天发生的第一条数据信息},
                    {对应明细行当天发生的第二条数据信息}
                ]
            }
            '''
            new_dict = {
                'recpay_org_id': res.recpay_org_id.name if res.recpay_org_id else '',  # 收付组织
                'acct_number_id': _('Acct Number:') + res.cash_acct_number_id.cash_acct_number + _(';Acct Name:') + res.cash_acct_number_id.name if res.cash_acct_number_id else '',  # 账号（账号：）（；账户名称：）
                'biz_date': str(res.biz_date), # 业务日期
                'number': res.number,  # 单据编号
                'summary': res.summary if res.summary else '', # 摘要
                'currency_id': res.currency_id.name or '',  # 币别
                'currency_id_id': res.currency_id.id,  # 币别id
                'income_amount': res.income_amount,  # 收入金额
                'expense_amount': res.expense_amount,  # 收入金额
                'end_period_balance': 0,  # 期末余额
                'payment_purpose': res.payment_purpose.name if res.payment_purpose else '',  # 收付款用途
                'sett_type_id': res.sett_type_id.name if res.sett_type_id else '',  # 结算方式
                'source_create_uid': res.source_create_uid.name if res.source_create_uid else '',  # 制单人
                'state': self.tran_dict[res.state],  # 单据状态
                'source_parent_doc_id': res.source_parent_doc_id,  # 单据id
                'source_parent_model': res.source_parent_model_id.model if res.source_parent_model_id else '',  # 单据模型
            }
            
            if domain_fields['is_local_currency']:
                # 如果勾选了包含本位币，则需要在query_period_dict中添加本位比相关的数据
                new_dict['local_currency_id'] = local_currency_name  # 本位币
                new_dict['local_currency_id_id'] = local_currency_id_id  # 本位币
                new_dict['income_amount_local'] = res.income_amount_local  # 收入金额本位币
                new_dict['expense_amount_local'] = res.expense_amount_local  # 支出金额本位币
                new_dict['end_period_balance_local'] = 0  # 期末余额本位币

                yesterday_balance_dict[yesterday_balance_key]['local_currency_id'] = local_currency_name  # 本位币
                yesterday_balance_dict[yesterday_balance_key]['local_currency_id_id'] = local_currency_id_id  # 本位币id

            key = (res.cash_acct_number_id.id, res.currency_id.id, res.biz_date)
            if not query_period_dict.get(key):
                # 如果当前的key在查询期间内组织数据的dict中没有出现，则创建一个新的列表
                # 这里的列表会存储同一组织、同一账号、同一币别、同一天发生的所有数据
                query_period_dict[key] = list()

            query_period_dict[key].append(new_dict)

        return query_period_dict

    # @profile
    def _conduct_simulation_audit(self, domain_fields):
        """
        @desc: 进行模拟审核过程，根据条件，从各个单据中查找相关数据
        @params: self: 当前示例对象
        @params: domain_fields: 字段选择过滤条件

        @return: cash_income_expense_analog_data_list: 组织好的模拟审核数据列表，里面有多个dict数据（由各个业务单据直接获取）
        """
        # 获取当前查询条件中的所选组织的启用日期（查询各个单据的未审核数据的开始日期）
        start_date = self._get_activation_date(domain_fields)
        # 根据查询条件中的结束日期获取（查询各个单据的未审核数据的开始日期）
        end_date = domain_fields['end_date']
        # 定义模拟数据字典组成的列表，（各个业务单据，模拟审核过程组织的数据）
        cash_income_expense_analog_data_list = list()
        # 定义模拟数据字典，将组织好的列表循环获取组织出以（账号、币别）为维度的key-value对应的dict
        unaudit_data_dict = dict()

        # 根据查询条件字典cash_income_expense_search_dict，获取现金收支表查询的条件数据
        for parent_model, child_model, domain in DOC_MODELS:
            records = self.env[parent_model].search([
                ('state', 'in', ['save', 'submit']),
                ('delete_state', '=', 'normal'),
                ('biz_date', '>=', start_date),
                ('biz_date', '<=', end_date)
            ] + domain)
            # 由于性能优化，重构cm.cash.income.expense模型中的p_set_data，因此可将所有的res合并在一个list中一起进行模拟审核过程
            analog_data_list = self.env['cm.cash.income.expense'].p_set_data(child_model, records, flag=True)
            if analog_data_list:
                cash_income_expense_analog_data_list.extend(analog_data_list)
        
        for res in cash_income_expense_analog_data_list:
            if not res['cash_acct_number_id'] or not res['currency_id'] or not res['biz_date']:
                continue
            key = (res['cash_acct_number_id'][0], res['currency_id'][0], res['biz_date'])
            # 这里按照（账号id、币别id、业务日期）为维度进行分组，因为会出现相同维度的多条数据，因此需要存储再同一个key中的value中，因此使用list来组织value数据
            if not unaudit_data_dict.get(key):
                unaudit_data_dict[key] = list()

            unaudit_data_dict[key].append(res)
            
        return unaudit_data_dict

    def _organization_query_cells(self, domain_fields, query_period_dict, yesterday_balance_dict):
        """
        @desc: 将组织好的数据，插入到表格中
        @params: self: 当前示例对象
        @params: domain_fields: 字段选择过滤条件
        @params: query_period_dict: 组织好的查询期间内的数据
        @params: yesterday_balance_dict: 组织好的昨日结存数据字典

        @return: query_cells
        """
        # 定义最终查询数据的数据列表（后续会将昨日结存、明细数据、合计数据插入进来）
        query_cells = list()
        event_data = dict()
        # 定义明细行数据的字典yesterday_balance_dict的key的key排序（这里面的value存放了所有明细行的key，而key对应的是明细行key去掉日期部分）
        query_period_key_key_dict = dict()
        for key in sorted(query_period_dict.keys()):
            key_key = key[:2]
            if not query_period_key_key_dict.get(key_key):
                query_period_key_key_dict[key_key] = list()
            query_period_key_key_dict[key_key].append(key)

        row = 0
        for key, data in sorted(yesterday_balance_dict.items(), key=lambda item: item[0]):
            # 循环插入昨日结存（每个昨日结存再循环调用函数，插入明细数据）
            row = self._insert_yesterday_balance_data(domain_fields, data, query_cells, row)
            # 定义余额和本位币余额变量，用户后续明细行余额计算使用
            balance_amount = data['end_period_balance']
            balance_amount_local = data['end_period_balance_local'] if domain_fields['is_local_currency'] else 0

            if not query_period_key_key_dict.get(key):
                # 因为query_period_key_key_dict中存储了所有query_period_dict的key，且key进行了去掉date之后的key合并处理
                # 如果query_period_key_key_dict中找不到当前循环到的昨日结存的key，则不需要进行明细行的添加
                # 也不需要进行本日合计、本月合计、本年累计的处理
                continue
            
            total_dict = {
                'day_date': '',  # 定义日（日变化时，需先添加本日合计）
                'month_date': '',  # 定义月（月变化时，需先添加本月合计）
                'year_date': '',  # 定义年（年变化时，需先添加本年累计）
                'currency_id': '',  # 定义币别
                'recpay_org_id': '',  # 定义收付组织
                'acct_number_id': '',  # 定义现金账号
                'day_income_total': 0,  # 定义本日收入合计
                'day_expense_total': 0,  # 定义本日支出合计
                'month_income_total': 0,  # 定义本月收入合计
                'month_expense_total': 0,  # 定义本月支出合计
                'year_income_total': 0,  # 定义本年收入合计
                'year_expense_total': 0,  # 定义本年支出合计
                'day_balance_total': 0,  # 定义本日余额
                'month_balance_total': 0,  # 定义本月余额
                'year_balance_total': 0,  # 定义本年余额
            }
            if domain_fields['is_local_currency']:
                total_dict['local_currency_id'] = ''  # 定义本位币
                total_dict['day_income_total_local'] = 0  # 定义本日收入合计本位币
                total_dict['day_expense_total_local'] = 0  # 定义本日支出合计本位币
                total_dict['month_income_total_local'] = 0  # 定义本月收入合计本位币
                total_dict['month_expense_total_local'] = 0  # 定义本月支出合计本位币
                total_dict['year_income_total_local'] = 0  # 定义本年收入合计本位币
                total_dict['year_expense_total_local'] = 0  # 定义本年支出合计本位币
                total_dict['day_balance_total_local'] = 0  # 定义本日余额本位币
                total_dict['month_balance_total_local'] = 0  # 定义本月余额本位币
                total_dict['year_balance_total_local'] = 0  # 定义本年余额本位币
            
            for query_period_key in query_period_key_key_dict[key]:
                # 以当前昨日结存dict数据中循环到的key去获取query_period_key_key_dict中的数据
                # 得到了多个query_period_dict中key同一组织、同一账号、同一币别不同日期的key组合 
                for query_period_date_dict in query_period_dict[query_period_key]:
                    # 循环这些包含日期维度的key分别从明细行dict中获取数据，插入到query_cells中
                    if domain_fields['is_total'] and total_dict['day_date'] and total_dict['month_date'] and total_dict['year_date']:
                        # 如果用户勾选了显示合计，则需要组织本日合计、本月合计、本年累计行

                        if total_dict['day_date'] != query_period_date_dict['biz_date']:
                            # 如果day_date发生变化，则添加本日合计
                            row = self._insert_day_month_year_total_data(domain_fields, query_cells, row, total_dict, 'day')
                            # 更新本日
                            total_dict['day_date'] = query_period_date_dict['biz_date']

                        if total_dict['month_date'] != query_period_date_dict['biz_date'][:7:]:
                            # 如果month_date发生变化，则添加本月合计
                            row = self._insert_day_month_year_total_data(domain_fields, query_cells, row, total_dict, 'month')
                            # 更新本月
                            total_dict['month_date'] = query_period_date_dict['biz_date'][:7:]

                        if total_dict['year_date'] != query_period_date_dict['biz_date'][:4:]:
                            # 如果year_date发生变化，则添加本年合计
                            row = self._insert_day_month_year_total_data(domain_fields, query_cells, row, total_dict, 'year')
                            # 更新本年
                            total_dict['year_date'] = query_period_date_dict['biz_date'][:4:]

                    # 判断完是否插入合计（如果日期发生变化，则要先插入合计）
                    # 直接插入明细行数据
                    row, balance_amount, balance_amount_local = self._insert_query_period_data(domain_fields, query_period_date_dict, query_cells, row, total_dict, balance_amount, event_data, balance_amount_local)
                    
            # 在每组明细数据插入结束后，插入本日合计、本月合计、本年累计
            if domain_fields['is_total']:
                row = self._insert_day_month_year_total_data(domain_fields, query_cells, row, total_dict, 'day')
                row = self._insert_day_month_year_total_data(domain_fields, query_cells, row, total_dict, 'month')
                row = self._insert_day_month_year_total_data(domain_fields, query_cells, row, total_dict, 'year')

        return query_cells, event_data

    def _insert_yesterday_balance_data(self, domain_fields, data, query_cells, row):
        """
        @desc: 循环插入昨日结存（每个昨日结存再循环调用函数，插入明细数据）
        @params: self: 当前示例对象
        @params: domain_fields: 字段选择过滤条件
        @params: data: 组织好的昨日结存数据
        @params: query_cells: 报表最终数据组织列表
        @params: row: 当前行

        @return: row: 下一行
        """
        column = 0
        # 收付组织, 现金账号, 业务日期, 单据编号, 摘要, 原币：币别, 原币：收入金额, 原币：支出金额, 原币：余额
        for key in ('recpay_org_id', 'acct_number_id', None, None, 'summary', 'currency_id', None, None, 'end_period_balance'):
            kw = {'currency_id': data.get('currency_id_id', None)} if key == 'end_period_balance' else {}
            query_cells.append(QueryCell(row, column, data[key] if key and key in data else '', **kw))
            column += 1

        if domain_fields['is_local_currency']:
            # 本位币：币别, 收入金额, 支出金额, 余额
            for key in ('local_currency_id', None, None, 'end_period_balance_local'):
                kw = {'currency_id': data.get('local_currency_id_id', None)} if key == 'end_period_balance_local' else {}
                query_cells.append(QueryCell(row, column, data[key] if key and key in data else '', **kw))
                column += 1
        return row + 1

    def _insert_day_month_year_total_data(self, domain_fields, query_cells, row, total_dict, time_unit):
        """
        @desc: 插入本日合计、本月合计、本年累计数据
        @params: self: 当前示例对象
        @params: domain_fields: 字段选择过滤条件
        @params: query_cells: 报表最终数据组织列表
        @params: row: 当前行
        @params: total_dict: 组织好的本日合计、本月合计、本年累计数据字典
        @params: time_unit: day/month/year标志

        @return: row: 下一行
        """
        if time_unit == 'day':
            total_dict['summary'] = _('Day Total')  # 摘要：本日合计
        elif time_unit == 'month':
            total_dict['summary'] = _('Month Total')  # 摘要：本月合计
        else:
            total_dict['summary'] = _('Year Total')  # 摘要：本年累计
        
        column = 0
        # 收付组织, 现金账号, 业务日期, 单据编号, 摘要, 原币：币别, 原币：收入金额, 原币：支出金额, 原币：余额
        for key in ('recpay_org_id', 'acct_number_id', time_unit + '_date', None, 'summary', 'currency_id'):
            query_cells.append(QueryCell(row, column, total_dict[key] if key and key in total_dict else '', **kw))
            column += 1
        
        currency_id = total_dict.get('currency_id_id', None)
        for key in (time_unit + '_income_total', time_unit + '_expense_total', time_unit + '_balance_total'):
            
            query_cells.append(QueryCell(row, column, total_dict[key] if key and key in total_dict else '', currency_id=currency_id))
            column += 1

        if domain_fields['is_local_currency']:
            query_cells.append(QueryCell(row, column, total_dict['local_currency_id']))  # 本位币：币别
            column += 1
            query_cells.append(QueryCell(row, column, total_dict[time_unit + '_income_total_local'], currency_id=total_dict.get('local_currency_id_id', None)))  # 本位币：收入金额
            column += 1
            query_cells.append(QueryCell(row, column, total_dict[time_unit + '_expense_total_local'], currency_id=total_dict.get('local_currency_id_id', None)))  # 本位币：支出金额
            column += 1
            query_cells.append(QueryCell(row, column, total_dict[time_unit + '_balance_total_local'], currency_id=total_dict.get('local_currency_id_id', None)))  # 本位币：余额
            column += 1
        else:
            column += 4

        total_dict[time_unit + '_income_total'] = 0
        total_dict[time_unit + '_expense_total'] = 0

        if domain_fields['is_local_currency']:
            total_dict[time_unit + '_income_total_local'] = 0
            total_dict[time_unit + '_expense_total_local'] = 0
        
        return row + 1

    def _insert_query_period_data(self, domain_fields, query_period_date_dict, query_cells, row, total_dict, balance_amount,  event_data, balance_amount_local=0):
        """
        @desc: 循环插入明细行数据
        @params: self: 当前示例对象
        @params: domain_fields: 字段选择过滤条件
        @params: query_period_date_dict: 组织好的明细行数据字典
        @params: query_cells: 报表最终数据组织列表
        @params: balance_amount: 余额计算变量
        @params: balance_amount_local: 余额本位币计算变量
        @params: row: 当前行

        @return: row: 下一行
        @return: balance_amount: 新计算好的余额
        @return: balance_amount_local: 新计算好的余额本位币
        """
        source_parent_model = query_period_date_dict.get('source_parent_model', '')
        if source_parent_model:
            event_data[row] = {
                -1: {
                    CLICK_TYPE_DICT[source_parent_model]: {
                        'res_id': query_period_date_dict['source_parent_doc_id'],
                        'ref': BILL_ACTION[source_parent_model],
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
        # 收付组织, 现金账号, 业务日期, 单据编号, 摘要, 原币：币别, 原币：收入金额, 原币：支出金额, 原币：余额
        currency_id = query_period_date_dict.get('currency_id_id', None)
        for key in ('recpay_org_id', 'acct_number_id', 'biz_date', 'number', 'summary', 'currency_id', 'income_amount', 'expense_amount'):
            kw = {'currency_id': currency_id} if key in  ('income_amount', 'expense_amount') else {}
            query_cells.append(QueryCell(row, column, query_period_date_dict[key] if key in query_period_date_dict else '', **kw))
            column += 1
        balance_amount += (query_period_date_dict['income_amount'] - query_period_date_dict['expense_amount'])
        query_cells.append(QueryCell(row, column, balance_amount, currency_id=currency_id))  # 原币：余额
        column += 1

        if domain_fields['is_local_currency']:
            local_currency_id = query_period_date_dict.get('local_currency_id_id', None)
            # 本位币：币别, 收入金额, 支出金额
            for key in ('local_currency_id', 'income_amount_local', 'expense_amount_local'):
                kw = {'currency_id': local_currency_id} if key in ('income_amount_local', 'expense_amount_local') else {}
                query_cells.append(QueryCell(row, column, query_period_date_dict[key] if key in query_period_date_dict else '', **kw))
                column += 1
            balance_amount_local += (query_period_date_dict['income_amount_local'] - query_period_date_dict['expense_amount_local'])
            query_cells.append(QueryCell(row, column, balance_amount_local, currency_id=local_currency_id))  # 本位币：余额
            column += 1
        else:
            column += 4
        
        # 收付款用途, 结算方式, 制单人, 单据状态
        for key in ('payment_purpose', 'sett_type_id', 'source_create_uid', 'state'):
            query_cells.append(QueryCell(row, column, query_period_date_dict[key] if key in query_period_date_dict else ''))
            column += 1

        total_dict.update({
            'day_date': query_period_date_dict['biz_date'],  # 业务日期（日）
            'month_date': query_period_date_dict['biz_date'][:7:],  # 业务日期（月）
            'year_date': query_period_date_dict['biz_date'][:4:],  # 业务日期（年）
            'currency_id': query_period_date_dict['currency_id'],  # 币别
            'currency_id_id': query_period_date_dict['currency_id_id'],  # 币别
            'recpay_org_id': query_period_date_dict['recpay_org_id'],  # 收付组织
            'acct_number_id': query_period_date_dict['acct_number_id'],  # 账号
            'day_balance_total': balance_amount,  # 原币：余额（日）
            'month_balance_total': balance_amount,  # 原币：余额（月）
            'year_balance_total': balance_amount  # 原币：余额（年）
        })

        total_dict['day_income_total'] += query_period_date_dict['income_amount']  # 原币：收入金额（日）
        total_dict['day_expense_total'] += query_period_date_dict['expense_amount']  # 原币：支出金额（日）
        total_dict['month_income_total'] += query_period_date_dict['income_amount']  # 原币：收入金额（月）
        total_dict['month_expense_total'] += query_period_date_dict['expense_amount']  # 原币：支出金额（月）
        total_dict['year_income_total'] += query_period_date_dict['income_amount']  # 原币：收入金额（年）
        total_dict['year_expense_total'] += query_period_date_dict['expense_amount']  # 原币：支出金额（年）

        if domain_fields['is_local_currency']:
            total_dict['local_currency_id'] = query_period_date_dict['local_currency_id']  # 本位币
            total_dict['local_currency_id_id'] = query_period_date_dict['local_currency_id_id']  # 本位币
            total_dict['day_income_total_local'] += query_period_date_dict['income_amount_local']  # 本位币：收入金额（日）
            total_dict['day_expense_total_local'] += query_period_date_dict['expense_amount_local']  # 本位币：支出金额（日）
            total_dict['month_income_total_local'] += query_period_date_dict['income_amount_local']  # 本位币：收入金额（月）
            total_dict['month_expense_total_local'] += query_period_date_dict['expense_amount_local']  # 本位币：支出金额（月）
            total_dict['year_income_total_local'] += query_period_date_dict['income_amount_local']  # 本位币：收入金额（年）
            total_dict['year_expense_total_local'] += query_period_date_dict['expense_amount_local']  # 本位币：支出金额（年）

            total_dict['day_balance_total_local'] = balance_amount_local  # 本位币：余额（日）
            total_dict['month_balance_total_local'] = balance_amount_local  # 本位币：余额（月）
            total_dict['year_balance_total_local'] = balance_amount_local  # 本位币：余额（年）

        return row + 1, balance_amount, balance_amount_local

    def _del_is_to_show(self, yesterday_balance_dict):
        """
        @desc: 组织查询数据
        @params: self: 当前示例对象
        @params: yesterday_balance_dict: 组织好的昨日结存数据字典（未删除多余以账号、币别为维度的不需要展示的数据）

        @return: yesterday_balance_dict: 组织好的昨日结存数据字典（删除掉多余以账号、币别为维度的不需要展示的数据）
        """
        del_key_list = [key for key, value in yesterday_balance_dict.items() if not value['is_to_show']]
        for key in del_key_list:
            del yesterday_balance_dict[key]
        return yesterday_balance_dict

    def _add_unaudit_data(self, domain_fields, yesterday_balance_dict, query_period_dict, unaudit_data_dict, cash_acct_number_dict):
        """
        @desc: 添加未审核数据到昨日结存数据字典中，添加未审核数据到明细行数据字典中
        @params: self: 当前示例对象
        @params: domain_fields: 字段选择过滤条件
        @params: yesterday_balance_dict: 组织好的昨日结存数据字典（不包含未审核数据）
        @params: query_period_dict: 组织好的昨日结存数据字典（不包含未审核数据）
        @params: unaudit_data_dict: 组织好的未审核数据
        
        @return: yesterday_balance_dict: 组织好的明细行数据字典（包含未审核数据）
        @return: query_period_dict: 组织好的明细行数据字典（包含未审核数据）
        """
        for key, value_list in unaudit_data_dict.items():
            key_key = (1,key[:2][1].id)
            if not yesterday_balance_dict.get(key_key):
                # 如果当前key_key不在昨日结存数据字典yesterday_balance_dict中
                # 则说明当前的key不属于我们这次查询需要展示的数据，因此我们不使用这个数据
                continue

            for value in value_list:
                if str(value['biz_date']) < str(domain_fields['start_date']) and str(value['biz_date']) >= str(yesterday_balance_dict[key_key]['biz_date']):
                    # 直接更新资金余额表中获取到的数据
                    # 这里不需要判断当前key_key是否在yesterday_balance_dict中，因为yesterday_balance_dict一定包含了最全的以（账号id、币别id）为维度的key值
                    yesterday_balance_dict[key_key]['end_period_balance'] += (value['income_amount'] - value['expense_amount'])

                    if not yesterday_balance_dict[key_key]['is_to_show']:
                        # 这里意思是，因为yesterday_balance_dict里面有所有的收付组织维度和币别维度，所有有可能有没有的数据
                        # 没有的数据is_to_show这个key将会是False,但是当我们更新了这个key的value时，我们就需要把这个key更新为True，将来用于展示使用
                        yesterday_balance_dict[key_key]['is_to_show'] = True

                    if domain_fields['is_local_currency']:
                        # 如果勾选包含本位币，则需要更新本位币相关数据
                        yesterday_balance_dict[key_key]['local_currency_id'] = value['local_currency_id'][1] if value['local_currency_id'] else ''  # 本位币
                        yesterday_balance_dict[key_key]['local_currency_id_id'] = value['local_currency_id'][0] if value['local_currency_id'] else ''  # 本位币
                        yesterday_balance_dict[key_key]['end_period_balance_local'] += (value['income_amount_local'] - value['expense_amount_local'])
                
                if str(value['biz_date']) >= str(domain_fields['start_date']) and str(value['biz_date']) <= str(domain_fields['end_date']):
                    # 组织yesterday_balance_key用于查找yesterday_balance_dict内的key对应value中是否有is_to_show为False的数据
                    # 这里不需要判断yesterday_balance_dict.get(yesterday_balance_key)，因为yesterday_balance_dict中的key一定是最全的
                    # 
                    # 
                    # 
                    # 因为这里是为了组织明细行数据，因此明细行数据存在，则要展示明细行数据，因此明细行对应的昨日结存数据也需要展示出来，因此更新is_to_show为True
                    if not yesterday_balance_dict[key_key]['is_to_show']:
                        yesterday_balance_dict[key_key]['is_to_show'] = True
                        yesterday_balance_dict[key_key]['local_currency_id'] = value['local_currency_id'][1] if value['local_currency_id'] else ''  # 本位币
                        yesterday_balance_dict[key_key]['local_currency_id_id'] = value['local_currency_id'][0] if value['local_currency_id'] else ''  # 本位币

                    cash_acct_number = cash_acct_number_dict.get(value['cash_acct_number_id'][0], {}).get('cash_acct_number', '') if value['cash_acct_number_id'] else ''
                    cash_acct_name = cash_acct_number_dict.get(value['cash_acct_number_id'][0], {}).get('name', '') if value['cash_acct_number_id'] else ''
                    new_dict = {
                        'recpay_org_id': value['recpay_org_id'][1] if value['recpay_org_id'] else '',  # 收付组织
                        'acct_number_id': _('Acct Number:') + cash_acct_number + _(';Acct Name:') + cash_acct_name if value['cash_acct_number_id'] else '',  # 账号（账号：）（；账户名称：）
                        'biz_date': str(value['biz_date']), # 业务日期
                        'number': value['number'],  # 单据编号
                        'summary': value['summary'] if value['summary'] else '', # 摘要
                        'currency_id': value['currency_id'][1] if value['currency_id'] else '',  # 币别
                        'currency_id_id': value['currency_id'][0] if value['currency_id'] else '',  # 币别id
                        'income_amount': value['income_amount'],  # 收入金额
                        'expense_amount': value['expense_amount'],  # 收入金额
                        'end_period_balance': 0,  # 期末余额
                        'payment_purpose': value['payment_purpose'][1] if value['payment_purpose'] else '',  # 收付款用途
                        'sett_type_id': value['sett_type_id'][1] if value['sett_type_id'] else '',  # 结算方式
                        'source_create_uid': value['source_create_uid'][1] if value['source_create_uid'] else '',  # 制单人
                        'state': self.tran_dict[value['state']],  # 单据状态
                        'source_parent_doc_id': value['source_parent_doc_id'],  # 单据id
                        'source_parent_model': value['source_parent_model'],  # 单据模型
                    }
                    
                    if domain_fields['is_local_currency']:
                        # 如果勾选了包含本位币，则需要在query_period_dict中添加本位比相关的数据
                        new_dict['local_currency_id'] = value['local_currency_id'][1] if value['local_currency_id'] else ''  # 本位币
                        new_dict['local_currency_id_id'] = value['local_currency_id'][0] if value['local_currency_id'] else ''  # 本位币id
                        new_dict['income_amount_local'] = value['income_amount_local']  # 收入金额本位币
                        new_dict['expense_amount_local'] = value['expense_amount_local']  # 支出金额本位币
                        new_dict['end_period_balance_local'] = 0  # 期末余额本位币

                    if not query_period_dict.get(key):
                        # 如果当前的key在查询期间内组织数据的dict中没有出现，则创建一个新的列表
                        # 这里的列表会存储同一组织、同一账号、同一币别、同一天发生的所有数据
                        query_period_dict[key] = list()

                    query_period_dict[key].append(new_dict)

        return yesterday_balance_dict, query_period_dict

    # @profile
    def _get_query_cells(self, domain_fields):
        """
        @desc: 组织查询数据
        @params: self: 当前示例对象
        @params: domain_fields: 字段选择过滤条件
        
        @return: 返回调用组织数据到表格中
        """
        cash_acct_numbers = self.env['mdm.cash.acct.number'].search_read(
            [('id', 'in', domain_fields['cash_acct_number_ids'])], 
            fields=['cash_acct_number', 'name'])
        cash_acct_number_dict = {n['id']: n for n in cash_acct_numbers}

        # 获取资金余额表、现金收支表中的相关数据，用于计算昨日结存
        # 获取并组织资金余额表相关数据记录到昨日结存字典yesterday_balance_dict中
        yesterday_balance_dict = self._get_capital_balance_data(domain_fields, cash_acct_number_dict)

        # 整理开始日期到结束日期之间的行数据
        query_period_dict = self._get_query_period_dict(domain_fields, yesterday_balance_dict)

        if domain_fields['is_include_unaudit_doc']:
            # 如果用户勾选包含未审核，则需要处理未审核的相关单据的数据
            # 调用方法，获取所有的未审核数据
            unaudit_data_dict = self._conduct_simulation_audit(domain_fields)
            # 如果用户勾选包含未审核，则需要处理未审核的相关单据的数据
            yesterday_balance_dict, query_period_dict = self._add_unaudit_data(domain_fields, yesterday_balance_dict, query_period_dict, unaudit_data_dict, cash_acct_number_dict)

        # 整理删除掉昨日结存数据字典中yesterday_balance_dict多余的不需要展示的数据
        yesterday_balance_dict = self._del_is_to_show(yesterday_balance_dict)

        # 组织数据插入到表格中
        return self._organization_query_cells(domain_fields, query_period_dict, yesterday_balance_dict)

    def _get_click_events(self):
        """
        构造点击事件
        """
        return [
            ClickEvent('cash_journal_to_cash_recycling', _('Cash Recycling'), {
                'type': 'ir.actions.act_window',
                'name': _('Cash Recycling'),
                'res_model': 'cm.cash.recycling',
                'view_mode': 'list,form',
                'view_type': 'form',
                'views': [
                    (False, 'list'), 
                    (self.env.ref('ps_cm.view_cm_cash_recycling_form').id, 'form')
                ],
            }, ClickEvent.DC),
            ClickEvent('cash_journal_to_transfer_settle_order', _('Transfer or Settlement of Exchange'), {
                'type': 'ir.actions.act_window',
                'name': _('Transfer or Settlement of Exchange'),
                'res_model': 'cm.transfer.settle',
                'view_mode': 'list,form',
                'view_type': 'form',
                'views': [
                    (False, 'list'), 
                    (self.env.ref('ps_cm.view_transfer_settlement_form').id, 'form')
                ],
            }, ClickEvent.DC),
            ClickEvent('cash_journal_to_receivable_bill', _('Receivable Bill'), {
                'type': 'ir.actions.act_window',
                'name': _('Receivable Bill'),
                'res_model': 'cm.receivable.bill',
                'view_mode': 'list,form',
                'view_type': 'form',
                'views': [
                    (False, 'list'), 
                    (self.env.ref('ps_cm.view_cm_receivable_bill_form_receive').id, 'form')
                ],
            }, ClickEvent.DC),
            ClickEvent('cash_journal_to_receivable_bill_refund', _('Refund Bill'), {
                'type': 'ir.actions.act_window',
                'name': _('Refund Bill'),
                'res_model': 'cm.receivable.refund.bill',
                'view_mode': 'list,form',
                'view_type': 'form',
                'views': [
                    (False, 'list'), 
                    (self.env.ref('ps_cm.view_cm_receivable_bill_form_refund').id, 'form')
                ],
            }, ClickEvent.DC),
            ClickEvent('cash_journal_to_payable_bill', _('Payable Bill'), {
                'type': 'ir.actions.act_window',
                'name': _('Payable Bill'),
                'res_model': 'cm.payable.bill',
                'view_mode': 'list,form',
                'view_type': 'form',
                'views': [
                    (False, 'list'), 
                    (self.env.ref('ps_cm.view_cm_payable_bill_form').id, 'form')
                ],
            }, ClickEvent.DC),
            ClickEvent('cash_journal_to_payable_refound_bill', _('Payable Refound Bill'), {
                'type': 'ir.actions.act_window',
                'name': _('Payable Refound Bill'),
                'res_model': 'cm.payable.refund.bill',
                'view_mode': 'list,form',
                'view_type': 'form',
                'views': [
                    (False, 'list'), 
                    (self.env.ref('ps_cm.view_cm_payable_refund_bill_form').id, 'form')
                ],
            }, ClickEvent.DC),
            ClickEvent('cash_journal_to_manual_journal', _('Manual Journal'), {
                'type': 'ir.actions.act_window',
                'name': _('Manual Journal'),
                'res_model': 'cm.manual.journal',
                'view_mode': 'list,form',
                'view_type': 'form',
                'views': [
                    (False, 'list'), 
                    (self.env.ref('ps_cm.view_cm_manual_journal_form').id, 'form')
                ],
            }, ClickEvent.DC)]

    ################################  私有方法区  end    ################################


    ################################  公共方法区  start  ################################
    
    ################################  公共方法区  end    ################################


    ################################  覆盖基类方法区  start  ################################

    @sys_ele_ctrl()
    def read(self, fields=None, load='_classic_read'):
         return super(CmCashJournalQuery, self).read(fields, load)

    @api.model
    def get_ps_query_data(self, render_type='spreadjs', domain_fields={}, context_fields={}, first_render=False):
        """
        @desc: 覆盖基类get_ps_query_data方法，组织报表数据
        @params: self: 当前示例对象
        @params: render_type: 使用控件类型，默认为spreadjs
        @params: domain_fields: 字段选择过滤条件
        @params: context_fields: 上下文过滤条件
        @params: first_render: 是否为第一次访问报表页面（从菜单或者其他视图打开报表，而不是报表点击查询按钮）

        @return: 返回调用报表数据展示
        """
        # 定义单据状态字段对应翻译
        self.tran_dict = {
            'creating': _('Creating'), 
            'temporary': _('Temporary'), 
            'save': _('Saved'),  # 已保存
            'submit': _('In_Audit'), 
            'audit': _('Audited'),  # 已审核
        }
        
        domain_fields = context_fields if first_render else domain_fields
        display_name = _("Cm Cash Journal Query")  # 现金流水账

        if render_type == 'spreadjs':
            if first_render:
                # 第一次访问报表页面（从菜单或者其他视图打开报表，而不是报表点击查询按钮）
                # 则直接返回一个空的报表页面
                # 获取默认的组织
                default_org_id = self._get_default_org_id()
                if default_org_id: domain_fields['recpay_org_id'] = default_org_id
                return self._get_default_domains(render_type, display_name, domain_fields)

            # 字段校验
            self._check_domain_fields(domain_fields)

            # 处理过滤条件中金额字段
            domain_fields['currency_ids'] = self._get_currency_ids(domain_fields)
            # 组织查询数据
            query_cells, event_data = self._get_query_cells(domain_fields)
            # 构造点击事件
            click_events = self._get_click_events()
            # 根据条件是否勾选包含本本位币，动态修改隐藏默认列（默认隐藏本位币的币别、收入金额、支出金额、余额四列）
            hidden_cols = [] if domain_fields.get('is_local_currency', False) else [9, 10, 11, 12]

            # 根据条件获取副标题
            query_cell_title = self._get_query_cell_title(domain_fields)
            query_cells.append(QueryCell(0, 0, query_cell_title['recpay_org'], category=QueryCell.TITLE))
            query_cells.append(QueryCell(0, 3, query_cell_title['acct_number'], category=QueryCell.TITLE))
            query_cells.append(QueryCell(0, 6, query_cell_title['date'], category=QueryCell.TITLE))
            
            # 组装一个表格
            query_tables= [QueryTable(query_cells=query_cells, col_count=17, blank_row_count=0, event_data=event_data)]     
            return self._get_spreadjs_query_data(display_name, domain_fields, query_tables, hidden_cols=hidden_cols, click_events=click_events, frozen_row_count=3, frozen_col_count=3)

    ################################  覆盖基类方法区  end    ################################


    ################################  其他方法区  start  ################################
    
    ################################  其他方法区  end    ################################ 