# -*- coding: utf-8 -*-
'''
==================================================
@创建人 ：李政
@当前维护人 ：Vic Sun
@Desc ：会计中心凭证生成逻辑代码
==================================================
'''
from collections import defaultdict
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, MissingError
from odoo.tools import float_compare, float_round
from odoo.tools.safe_eval import safe_eval
from odoo.addons.ps_admin.sys_ele.sys_ele_ctrl import sys_ele_ctrl
from odoo.addons.ps_mdm.common import mdm_currency as curr
from odoo.addons.ps_admin.info_window.info_window import InfoWindow, LineInfo, SUCCESS_STATE, FAILED_STATE


DEFAULT_AMOUNT = 0 # 默认金额
DEFAULT_DIGITS = 2 # 默认精度
DIGIT_LENGTH = 2 # 浮点数设置长度
DIGIT_PRECISION_INDEX = 1 # 浮点数小数精度索引
DEFAULT_ROUND_METHOD = 'HALF-UP' # 默认舍入类型
READ_ID_INDEX = 0 # many2one字段read结果id索引
READ_VALUE_INDEX = 1 # many2one字段read结果value索引
CURRENCY_RATE_PRECISION = 6 # 汇率精度位数
DOMAIN_LENGTH = 3 # domain长度
DOMAIN_FIELD_INDEX = 0 # domain字段索引
DOMAIN_OPT_INDEX = 1 # domain操作符索引
DOMAIN_VALUE_INDEX = 2 # domain值索引
DOMAIN_FIELD_SPLIT_NUM = 1 # domain字段split次数
DOMAIN_FIELD_SPLIT_LENGTH = 2 # domain字段包含的字段数量
DOMAIN_FIELD_SPLIT_CHILD_INDEX = 0 # domain字段中表体字段的索引
DOMAIN_FIELD_SPLIT_OTHER_INDEX = 1 # domain字段中其他字段的索引
START_INDEX = 1 # 凭证方案明细循环/凭证行sequence开始的索引
SEQUENCE_STEP_COUNT = 1 # 凭证行sequence增加的步长
QTY_FIELDS = (
    ('uom_field_model', 'uom_field_name'), 
    ('spec_field_model', 'spec_field_name'), 
    ('qty_field_model', 'qty_field_name'), 
    ('price_field_model', 'price_field_name')
) # 数量核算模型和字段


class AccCenterVoucherGeneration(models.Model):
    _name = 'acc.center.voucher.generation'
    _rec_name = 'acct_book_id'
    _description = 'Account Center Voucher Factory'  # 会计中心凭证工厂

    ################################  default start  ################################

    ################################  default end    ################################


    ################################  字段定义区 start  ################################

    tenant_id = fields.Integer(string='Tenant', default=lambda self: self.env.user.tenant_id)  #租户
    acct_book_id = fields.Many2one('mdm.account.book', default=1, string='Account Book')  # 会计账簿
    acct_sys_id = fields.Many2one('mdm.accounting.system', string='Account System', related='acct_book_id.accting_sys_id', store=True)  # 会计核算体系
    acct_org_id = fields.Many2one('sys.admin.orgs', string='Account Organization', related='acct_book_id.accting_org_id', store=True)  # 核算组织
    module_id = fields.Many2one('ir.module.module', string='Document Module') # 来源单据模块
    acct_period_id = fields.Many2one('mdm.account.calendar.line1', string='Account Period')  #会计期间 弃用
    calendar_id = fields.Many2one('mdm.account.calendar', string='Account Calendar', related='acct_book_id.calendar_id', store=True)  # 会计日历 弃用
    line_ids = fields.One2many('acc.center.voucher.generation.line1', 'parent_id', string='Voucher Generation Line')  # 凭证生成表体
    delete_state = fields.Selection([
        ("normal", "Normal"),
        ("delete", "Delete")], string="Delete State", default="normal")  # 删除状态(正常/删除)
    delete_uid = fields.Many2one('res.users', string='Delete User')  # 删除人
    delete_date = fields.Datetime(string='Delete Date') # 删除日期

    ################################  字段定义区 end    ################################


    ################################  计算方法区  start  ################################

    ################################  计算方法区  end    ################################


    ################################  onchange方法区  start  ################################

    ################################  onchange方法区  end    ################################


    ################################  约束方法区  start  ################################

    ################################  约束方法区  end  ################################


    ################################  服务器动作区  start  ################################

    ################################  服务器动作区  end  ################################


    ################################  按钮动作区  start  ################################

    ################################  按钮动作区  end  ################################


    ################################  私有方法区  start  ################################        

    def _get_source_docs(self, org_ids, accting_book_id, template_id, start_date, end_date):
        """
        筛选符合条件的来源单据：默认条件为：单据业务期间为选择的会计期间、核算组织为账簿的核算组织;并且如果设置了单据范围字段，再增加单据范围的筛选条件
        @param org_ids: 业务组织id列表
        @param accting_book_id: 账簿id
        @param template_id: 模板
        @param start_date: 单据过滤开始日期
        @param end_date: 单据过滤结束日期
        @return: 返回原单据id列表
        """
        model_obj = self.env[template_id.source_doc_model]
        org_field = template_id.acct_org_field_name
        fields = model_obj._fields

        voucher_obj = self.env['gl.voucher']
        voucher_obj.pre_create()
        voucher_ids = voucher_obj.search([
            ('acct_book_id', '=', accting_book_id),
            ('voucher_source', '=', model_obj._name),
            ('source_module_id', '=', template_id.source_module_id.id),
            ('delete_state', '=', 'normal')]).ids
        source_doc_ids = []
        if voucher_ids:
            relation_obj = self.env['studio.botp.record']
            relation_domain = [
                ('record_type', '=', 'acct_center'),
                ('delete_state', '=', False), 
                ('source_model_key', '=', model_obj._name),
                ('target_model_key', '=', 'gl.voucher'),
                ('target_doc_id', 'in', voucher_ids)
            ]
            relations = relation_obj.search_read(relation_domain, fields=['source_doc_id'])
            source_doc_ids = [rec['source_doc_id'] for rec in relations if rec.get('source_doc_id', None)]
        # TODO:改造更改处：未改（兼容处理，待模板字段必填后，去除biz_date）
        # date = template_id.vou_date_field_name
        date_field = template_id.vou_date_field_name or 'biz_date'
        domain = [
            ('id', 'not in', source_doc_ids),
            (date_field, '>=', start_date), 
            (date_field, '<=', end_date), 
            (org_field, 'in', org_ids)
        ]
        if 'delete_state' in fields:
            domain.append(('delete_state', '=', 'normal'))
        return model_obj.search(domain)
    
    def _round(self, value, curr_id):
        """
        金额精度处理
        """
        currency_obj = self.env['mdm.currency']
        return currency_obj.p_amount_float_round(value, curr_id)
    
    def _round_price(self, value, currency_id):
        """
        单价精度处理
        """
        currency_obj = self.env['mdm.currency']
        return currency_obj.p_price_float_round(value, currency_id)
    
    def _round_qty(self, value, unit_id):
        """
        数量精度处理
        """
        unit_obj = self.env['mdm.unit']
        return unit_obj.p_qty_float_round(value, unit_id)
    
    def _is_zero(self, value, curr_id):
        """
        判断金额是否为0
        """
        currency_obj = self.env['mdm.currency']
        return currency_obj.p_amount_float_is_zero(value, curr_id)

    def _float_compare(self, value1, value2, curr_id):
        """
        金额比较
        """
        currency_obj = self.env['mdm.currency']
        return currency_obj.p_amount_float_compare(value1, value2, curr_id)

    def _get_amount_data(self, origin_data, config_data, currency_id):
        """
        获取金额数据
        @param origin_data: 单据源数据
        @param config_data: 凭证方案配置数据
        @param currency_id: 原币币别
        @return 原币金额和本位币金额
        """
        amount_model = config_data['amount_model']
        amount_model_data = origin_data.get(amount_model, {})
        local_currency_id = config_data['local_currency_id']
        amount = amount_local = 0
        # 根据是否配置了计算公式，分别取数
        if config_data['template_id'].is_formula:
            amount_model_obj = self.env[amount_model]
            record = amount_model_obj.new(amount_model_data)
            formula_engine_obj = self.env['ps.formula.engine'].browse()
            amount = formula_engine_obj.p_calculate(config_data['amount_formula'], record=record)
            amount_local = formula_engine_obj.p_calculate(config_data['amount_local_formula'], record=record)
        else:
            amount = amount_model_data.get(config_data['amount_field'], DEFAULT_AMOUNT)
            amount_local = amount_model_data.get(config_data['standard_amount_field'], DEFAULT_AMOUNT)
        
        if self._is_zero(amount, currency_id):
            return None, None
        else:
            return self._round(amount, currency_id), self._round(amount_local, local_currency_id)

    def _get_float_value(self, document, field, value):
        """
        获取浮点数的值的字符串
        """
        precision = DEFAULT_DIGITS
        round_type = DEFAULT_ROUND_METHOD
        if hasattr(field, 'precision_field') and hasattr(field, 'precision_type'):
            precision_field = field.precision_field
            precision_field_value = document.get(precision_field, None)
            if precision_field_value and isinstance(precision_field_value, tuple):
                precision_field_id = precision_field_value[READ_ID_INDEX]

                precision_type = field.precision_type
                if precision_type in ('amount_precision', 'price_precision'):
                    currency_obj = self.env['mdm.currency']
                    precision = currency_obj.p_get_all_currency_precision().get(precision_field_id, {}).get(precision_type, DEFAULT_DIGITS)
                elif precision_type == 'qty_precision':
                    unit_obj = self.env['mdm.unit']
                    unit_precision = unit_obj.p_get_all_unit_precision().get(precision_field_id, {})
                    precision = unit_precision.get('qty_precision', DEFAULT_DIGITS)
                    round_type = unit_precision.get('round_type', DEFAULT_ROUND_METHOD)
        else:
            digit = field.get_digits(self.env)
            if isinstance(digit, tuple) and len(digit) == DIGIT_LENGTH:
                precision = digit[DIGIT_PRECISION_INDEX] 

        float_format = '{:.%sf}' % precision
        return float_format.format(float_round(value, precision_digits=precision, rounding_method=round_type))

    def _get_summary(self, document, summary_text, summary_fields, fields):
        """
        获取凭证行摘要
        @param document: 来源单据
        @param summary_text: 摘要内容，包含占位符
        @param summary_fields: 摘要关联字段
        @return 摘要内容
        """
        if not summary_text:
            return ''
        else:
            for field_name in summary_fields:
                field = fields.get(field_name, None)
                if not field or field.type in ('one2many', 'many2many', 'boolean'):
                    continue
                if document.get(field_name, None):
                    origin_value = document[field_name]
                    if field.type == 'many2one':
                        value = str(origin_value[READ_VALUE_INDEX])
                    elif field.type == 'reference':
                        r_model, r_id = document[field_name].split(',')
                        value = str(self.env[r_model].browse(int(r_id)).display_name)
                    elif field.type == 'selection':
                        selection = field.get_description(self.env)['selection']
                        if isinstance(selection, list):
                            value = dict(selection).get(origin_value, '')
                        else:
                            value = ''
                    elif field.type == 'float':
                        value = self._get_float_value(document, field, origin_value)
                    else:
                        value = str(origin_value)
                else:
                    value = ''
                summary_text = summary_text.replace('$(%s)' % field_name, value)
            return summary_text

    def _get_currency_rate(self):
        """
        根据原币、目标币种、业务时间、汇率类别获取汇率，调用`mdm.currency.rate`获取汇率方法，增加缓存
        @param src_curr_id: 原币id
        @param target_curr_id: 目标币种id
        @param biz_date: 业务日期
        @param curr_rate_ctg_id: 汇率类型
        @return 汇率
        """
        # 不能使用ormcache，因为汇率更新不会更新缓存
        cache = {}
        def get(src_curr_id, target_curr_id, biz_date, curr_rate_ctg_id):
            key = (src_curr_id, target_curr_id, biz_date, curr_rate_ctg_id)
            try:
                return cache[key]
            except KeyError:
                curr_rate_obj = self.env['mdm.currency.rate']
                curr_rate =  curr_rate_obj.get_direct_curr_rate(
                    original_currency_id=src_curr_id,
                    target_currency_id=target_curr_id,
                    business_date=biz_date,
                    curr_rate_ctg_id=curr_rate_ctg_id)
                cache[key] = curr_rate
                return curr_rate
        return get

    def _get_currency_data(self, origin_data, source_doc_model, config_data, account_id):
        """
        获取币别、汇率信息
        @param origin_data: 来源单据数据
        @param source_doc_model: 来源单据模型名称
        @param config_data: 凭证方案配置数据
        @param account_id: 科目
        @return 币别id,对应汇率
        """
        # 币别、汇率
        curr_model = config_data['curr_model']
        curr_field = config_data['curr_field']
        record_data = origin_data.get(curr_model, None)
        # 如果币别不能过滤到对应的数据，则直接返回
        if not record_data:
            return None, None
        
        curr_field_value = record_data.get(curr_field, None)
        if curr_field_value:
            curr_id, curr_name = curr_field_value
        else:
            # 未从单据上获取到币别
            raise ValidationError(_('Currency not obtained from the document'))
        # 支持本位币及科目上的外币设置
        local_currency_id = config_data['local_currency_id']
        if curr_id != local_currency_id and curr_id not in account_id.currency_ids.currency_id.ids:
            # 币别 %s 转换异常，请检查：1、账簿默认本位币是否正确；2、科目 %s 币别是否配置正确；3、凭证方案配置中科目 %s 选用是否正确
            account_name = account_id.display_name
            raise ValidationError(_('Abnormal conversion of currency %s, please check: ' +
                '1. Whether the default standard currency of account books is correct; ' +
                '2. Whether the currency of subject %s is correctly allocated; ' +
                '3. Is the subject %s selected correctly in the configuration of the certificate template') % (curr_name, account_name, account_name))
        
        get_curr_rate = config_data['curr_rate_getter']
        curr_rate_field = config_data['curr_rate_field']
        if curr_rate_field:
            curr_rate = record_data.get(curr_rate_field, 0)
        else:
            template = config_data.get('template_id', None)
            # TODO:改造更改处：未改（兼容处理，待模板字段必填后，去除biz_date）
            date_field = template.vou_date_field_name or "biz_date"
            biz_date = origin_data.get(source_doc_model, {}).get(date_field, None)
            curr_rate = get_curr_rate(local_currency_id, curr_id, biz_date, config_data['curr_rate_ctg_id'])

        if float_compare(curr_rate, 0, CURRENCY_RATE_PRECISION) <= 0:
            # 汇率配置有误，请检查凭证方案或基础资料汇率配置
            raise ValidationError(_('The currency rate setting is wrong, please check the voucher scheme or basic data currency rate configuration'))
        return curr_id, curr_rate

    def _get_auxiliary(self, origin_data, config_data, acct_set_line):
        """
        获取辅助核算
        @param origin_data: 来源单据数据
        @param config_data: 凭证方案配置数据
        @param acct_set_line: 科目设置
        @return 返回辅助核算flex数据及显示字符串
        """
        flex_name_mapping = config_data['flex_name_mapping']
        auxiliary_set_ids = acct_set_line.auxiliary_set_ids
        account_id = acct_set_line.account_id
        gov_auxiliary_set_ids = acct_set_line.gov_auxiliary_set_ids
        account_id = acct_set_line.account_id

        # ir_model对象
        ir_model_obj = self.env['ir.model']

        flex = {}
        auxiliary_list = []
        gov_auxiliary_list = []
        for auxiliary_set in auxiliary_set_ids:
            dimension_model = auxiliary_set.dimension_model_name # 辅助核算对应模型
            flex_value = dimension_value = None # 辅助核算值
            if auxiliary_set.method == 'fixed_value':
                flex_value = auxiliary_set.fixed_value_id
            elif auxiliary_set.method == 'source_field':
                model = auxiliary_set.source_field_model
                field_name = auxiliary_set.source_field_name
                relation = origin_data.get(model, {}).get(field_name, None)
                try:            
                    if isinstance(relation, tuple):
                        # 辅助核算取值字段为many2one字段
                        flex_value, dimension_value = relation
                    elif isinstance(relation, str):
                        # 辅助核算取值字段为reference字段
                        r_model, r_id = relation.split(',')
                        flex_value = int(r_id) if r_model == dimension_model else None
                except ValueError:
                    # 防止字段对应数据格式不正确
                    pass
            
            dimension_name = auxiliary_set.dimension_id.display_name # 辅助核算显示名称
            if not flex_value:
                # 凭证方案[%(name)s]分录行第%(index)s行，科目[%(account_name)s]设置的辅助核算[%(dimension_name)s]未从单据上取到值，请检查设置
                raise ValidationError(_('The line %(index)s of voucher scheme [%(name)s], auxiliary accounting [%(dimension_name)s] setting ' +
                    'in account [%(account_name)s] did not get the value from the document, please check the settings') % {
                        'index': config_data['line_index'],
                        'name': config_data['template_id'].name,
                        'dimension_name': dimension_name,
                        'account_name': account_id.display_name
                    })
            if not dimension_value:
                dimension_model_obj = self.env[dimension_model]
                try:
                    dimension_value = dimension_model_obj.browse(flex_value).display_name # 对应辅助核算的值
                # 存在以下场景：用户没有维护凭证方案中必须的核算维度资料，就开始进行凭证生成
                # 此时，直接browse会查不到记录，在browse().display_name时会提示：记录不存在或已删除
                # 导致用户当前操作被中断
                except MissingError as miss_e:
                    # 考虑到正常情况下不会存在model重复的数据，因此这里没有加limit=1控制
                    # 而且由于核算维度资料已经建立，不会存在search为空，查询不到数据的情况
                    # 凭证方案[%(name)s]分录行第%(index)s行，科目[%(account_name)s]设置的辅助核算[%(dimension_name)s]固定值id=[%(id)s]未找到对应记录，请先维护对应数据
                    raise ValidationError(_('The line %(index)s of voucher scheme [%(name)s], auxiliary accounting [%(dimension_name)s] setting ' +
                    'in account [%(account_name)s] did not mapping the correct record which id = %(id)s, please check the settings') % {
                        'index': config_data['line_index'],
                        'name': config_data['template_id'].name,
                        'dimension_name': dimension_name,
                        'account_name': account_id.display_name,
                        'id':flex_value
                    })
            auxiliary_list.append('%s:%s' % (dimension_name, dimension_value))
            flex_name = flex_name_mapping.get(dimension_model) # 辅助核算名称（如mdm_account_account_1）
            flex[flex_name] = flex_value
        # 参考凭证录入时核算维度的生成(platform/ps_fmf/static/src/js/flex/flex_fields.js#commitChanges方法)：
        # 如果只有一个核算维度，则最后不带【/】和空格
        # 如果多个核算维度，每个核算维度后都带【/】和空格
        auxiliary = '/ '.join(auxiliary_list)
        if len(auxiliary_list) > 1:
            auxiliary += '/ '

        for gov_auxiliary_set in gov_auxiliary_set_ids:
            dimension_model = gov_auxiliary_set.dimension_model_name # 辅助核算对应模型
            flex_value = dimension_value = None # 辅助核算值
            if gov_auxiliary_set.method == 'fixed_value':
                flex_value = gov_auxiliary_set.fixed_value_id
            elif gov_auxiliary_set.method == 'source_field':
                model = gov_auxiliary_set.source_field_model
                field_name = gov_auxiliary_set.source_field_name
                relation = origin_data.get(model, {}).get(field_name, None)
                try:            
                    if isinstance(relation, tuple):
                        # 辅助核算取值字段为many2one字段
                        flex_value, dimension_value = relation
                    elif isinstance(relation, str):
                        # 辅助核算取值字段为reference字段
                        r_model, r_id = relation.split(',')
                        flex_value = int(r_id) if r_model == dimension_model else None
                except ValueError:
                    # 防止字段对应数据格式不正确
                    pass
            
            dimension_name = gov_auxiliary_set.dimension_id.display_name # 辅助核算显示名称
            if not flex_value:
                # 凭证方案[%(name)s]分录行第%(index)s行，科目[%(account_name)s]设置的辅助核算[%(dimension_name)s]未从单据上取到值，请检查设置
                raise ValidationError(_('The line %(index)s of voucher scheme [%(name)s], gov_auxiliary accounting [%(dimension_name)s] setting ' +
                    'in account [%(account_name)s] did not get the value from the document, please check the settings') % {
                        'index': config_data['line_index'],
                        'name': config_data['template_id'].name,
                        'dimension_name': dimension_name,
                        'account_name': account_id.display_name
                    })
            if not dimension_value:
                dimension_model_obj = self.env[dimension_model]
                try:
                    dimension_value = dimension_model_obj.browse(flex_value).display_name # 对应辅助核算的值
                # 存在以下场景：用户没有维护凭证方案中必须的核算维度资料，就开始进行凭证生成
                # 此时，直接browse会查不到记录，在browse().display_name时会提示：记录不存在或已删除
                # 导致用户当前操作被中断
                except MissingError as miss_e:
                    # 考虑到正常情况下不会存在model重复的数据，因此这里没有加limit=1控制
                    # 而且由于核算维度资料已经建立，不会存在search为空，查询不到数据的情况
                    # 凭证方案[%(name)s]分录行第%(index)s行，科目[%(account_name)s]设置的辅助核算[%(dimension_name)s]固定值id=[%(id)s]未找到对应记录，请先维护对应数据
                    raise ValidationError(_('The line %(index)s of voucher scheme [%(name)s], gov_auxiliary accounting [%(dimension_name)s] setting ' +
                    'in account [%(account_name)s] did not mapping the correct record which id = %(id)s, please check the settings') % {
                        'index': config_data['line_index'],
                        'name': config_data['template_id'].name,
                        'dimension_name': dimension_name,
                        'account_name': account_id.display_name,
                        'id':flex_value
                    })
            gov_auxiliary_list.append('%s:%s' % (dimension_name, dimension_value))
            flex_name = flex_name_mapping.get(dimension_model) # 辅助核算名称（如mdm_account_account_1）
            flex[flex_name] = flex_value
        # 参考凭证录入时核算维度的生成(platform/ps_fmf/static/src/js/flex/flex_fields.js#commitChanges方法)：
        # 如果只有一个核算维度，则最后不带【/】和空格
        # 如果多个核算维度，每个核算维度后都带【/】和空格
        gov_auxiliary = '/ '.join(gov_auxiliary_list)
        if len(gov_auxiliary_list) > 1:
            gov_auxiliary += '/ '

        return flex, auxiliary, gov_auxiliary
    
    def _get_qty_account_data(self, origin_data, config_data, acct_set_line, currency_id, currency_rate, is_debit):
        """
        获取数量核算数据
        @param origin_data: 来源单据数据
        @param config_data: 凭证方案配置数据
        @param acct_set_line: 科目设置
        @param currency_id: 币别id，用于处理单价精度
        @param currency_rate: 汇率，用于计算单价本位币
        @param is_debit: 是借方
        @return 返回数量核算的数据字典
        """
        # 如果启用的数量核算，则根据配置更新数量核算
        account_id = acct_set_line.account_id
        if account_id.is_qty_acct:
            qty_field_model = acct_set_line.qty_field_model
            price_field_model = acct_set_line.price_field_model
            if not qty_field_model or not price_field_model:
                # 凭证方案[%(name)s]分录行第%(index)s行，科目[%(account_name)s]启用数量核算但是未配置数量或单价取值，请检查设置
                raise ValidationError(_('The line %(index)s of voucher scheme [%(name)s], account [%(account_name)s] enables quantity accounting, but quantity or unit price is not configured, please check the settings') % {
                        'index': config_data['line_index'],
                        'name': config_data['template_id'].name,
                        'account_name': account_id.display_name
                    })
                
            # 单位
            uom_data = origin_data.get(acct_set_line.uom_field_model, {}).get(acct_set_line.uom_field_name, None)
            if uom_data:
                uom_id = uom_data[READ_ID_INDEX]
            else:
                uom_id = account_id.uom_id.id
            # 规格型号
            specification = origin_data.get(acct_set_line.spec_field_model, {}).get(acct_set_line.spec_field_name, None)
            # 数量(单位为空，数量也为空)
            qty = origin_data.get(qty_field_model, {}).get(acct_set_line.qty_field_name, 0) if uom_id else 0
            # 数量/单价
            price = origin_data.get(price_field_model, {}).get(acct_set_line.price_field_name, 0)
            price_round = self._round_price(price, currency_id)
            price_local = self._round_price(price_round * currency_rate, config_data['local_currency_id'])
            qty_data = {
                'uom_id': uom_id, # 单位
                'specification': specification or account_id.specification, # 规格型号
                'qty': qty, # 数量
                'debit_qty': qty if is_debit else 0, # 借方数量
                'credit_qty': 0 if is_debit else qty, # 贷方数量
                'price': price_round, # 价格
                'price_local': price_local # 价格本位币
            }
        else:
            qty_data = {
                'uom_id': None, # 单位
                'specification': None, # 规格型号
                'qty': 0, # 数量
                'debit_qty': 0, # 借方数量
                'credit_qty': 0, # 贷方数量
                'price': 0, # 价格
                'price_local': 0 # 价格本位币
            }
        
        return qty_data

    def _get_fields_dict(self, documents, config_data, acct_set_line):
        """
        获取生成凭证所需各个模型中所需的字段
        @param document: 来源单据对象
        @param config_data: 凭证方案配置数据
        @param acct_set_line: 科目设置
        """
        # 获取各模型的字段列表：为减少查询的数据量（列），只获取生成凭证涉及到的数据列
        fields_dict = defaultdict(list)
        # 表头必须的字段
        source_doc_fields = []
        template_id = config_data['template_id']
        # TODO:改造更改处：未改（兼容处理，待模板字段必填后，去除biz_date）
        date_field = template_id.vou_date_field_name or 'biz_date'
        for field in ['number', date_field, 'state']:
            if field in documents:
                source_doc_fields.append(field)
        for name, field in documents._fields.items():
            if field.type == 'many2one' and field.comodel_name in ('mdm.currency', 'mdm.unit'):
                source_doc_fields.append(name)
        fields_dict[documents._name] = source_doc_fields + config_data['merge_fields'] + config_data['summary_fields']

        # 更新币别/汇率字段
        currency_model = config_data['curr_model']
        fields_dict[currency_model].append(config_data['curr_field'])
        if config_data['curr_rate_field']:
            fields_dict[currency_model].append(config_data['curr_rate_field'])
        
        # 更新金额字段：根据是否使用计算公式分别增加字段列表
        amount_model = config_data['amount_model']
        if template_id.is_formula:
            formula_engine_obj = self.env['ps.formula.engine']
            amount_fields = formula_engine_obj.p_get_all_fields(config_data['amount_formula'])
            fields_dict[amount_model].extend(amount_fields)
            amount_local_fields = formula_engine_obj.p_get_all_fields(config_data['amount_local_formula'])
            fields_dict[amount_model].extend(amount_local_fields)
        else:
            fields_dict[amount_model].extend([config_data['amount_field'], config_data['standard_amount_field']])

        # 更新数量核算字段
        if acct_set_line.account_id.is_qty_acct:
            for model_field, name_field in QTY_FIELDS:
                field_model = acct_set_line[model_field]
                field_name = acct_set_line[name_field]
                if field_model and field_name:
                    fields_dict[field_model].append(field_name)
        # 更新辅助核算的字段
        for auxiliary_set in acct_set_line.auxiliary_set_ids:
            fields_dict[auxiliary_set.source_field_model].append(auxiliary_set.source_field_name)
        
        return fields_dict

    def _get_document_data(self, documents, document_lines, config_data, acct_set_line):
        """
        根据凭证方案中出现的字段，查询数据库数据，获取单据及对应明细行的数据
        @param document: 来源单据对象
        @param document_lines: 来源单据明细行对象
        @param config_data: 凭证方案配置数据
        @param acct_set_line: 科目设置
        """
        fields_dict = self._get_fields_dict(documents, config_data, acct_set_line)
        
        # 获取原始数据
        source_doc_model = documents._name
        documents_data = documents.read(fields_dict[source_doc_model]) # 表头数据
        lines_dict = defaultdict(list) # 表体数据:key为表头的id, value为明细列表
        relations_dict = defaultdict(list) # 第三方模型数据: key为明细id,value为关联表数据列表
        entry_model = config_data['entry_model']
        rel_model = config_data['relation_model']
        if entry_model and document_lines:
            # 获取明细行数据，根据parent_id进行分组汇总
            parent_field = config_data['parent_field_name']
            fields_dict[entry_model].append(parent_field)
            for line in document_lines.read(fields_dict[entry_model]):
                parent_id = line[parent_field][READ_ID_INDEX]
                lines_dict[parent_id].append(line)
            
            if rel_model:
                # 获取第三方表数据，根据关联字段进行分组汇总
                rel_model_obj = self.env[rel_model]
                rel_field_name = config_data['relation_field_name']
                rels = rel_model_obj.search([(rel_field_name, 'in', document_lines.ids)] + config_data['relation_domain'])
                fields_dict[rel_model].append(rel_field_name)
                for rel in rels.read(fields_dict[rel_model]):
                    rel_field_value = rel[rel_field_name]
                    line_id = rel_field_value[READ_ID_INDEX] if isinstance(rel_field_value, tuple) else rel_field_value
                    relations_dict[line_id].append(rel)
        
        # 因为需要从至多三个表中获取原始数据（如果单据需要很多表去生成凭证，都可以把表头及表体以外的表汇成三方表）
        # 且单据 -> 单据明细 -> 第三方模型一定都是one2many的关系
        # 所以原始数据是三次方非线性的，这里将三维数据转化为线性方便获取数据
        result = []
        for doc in documents_data:
            lines = lines_dict.get(doc['id'], [])
            # 如果不存在明细，则直接将单据头作为源数据；否则，则进一步将单据明细铺开，并加入表头数据
            if not lines:
                result.append({
                    source_doc_model: doc
                })
            else:
                for line in lines:
                    relations = relations_dict.get(line['id'], [])
                    # 如果不存在第三方数据，则直接将单据明细作为源数据；
                    # 否则，则进一步将第三方数据铺开，并加入单据单据头和单据明细数据
                    if relations:
                        result.extend([{
                            source_doc_model: doc,
                            entry_model: line,
                            rel_model: rel
                        } for rel in relations])
                    else:
                        result.append({
                            source_doc_model: doc,
                            entry_model: line
                        })  
        return result

    def _update_origin_data(self, origin_data, documents, document_lines, config_data, acct_set_line):
        """
        组装凭证数据，包括凭证表头数据、表体数据、以及辅助核算等信息
        @param origin_data: 待生成凭证的原始数据
        @param documents: 来源单据列表
        @param document_lines: 来源单据明细列表
        @param config_data: 凭证方案配置
        @param acct_set_line: 模板分录条件、科目
        """
        template = config_data['template_id'] # 凭证方案
        doc_model, doc_fields = documents._name, documents._fields # 来源单据模型/字段
        documents_data = self._get_document_data(documents, document_lines, config_data, acct_set_line) # 单据/表体/第三方表的数据
        for data in documents_data:
            document = data[doc_model]
            doc_id = document['id']
            # 如果此单据没有处理过，则增加一个key；否则，如果失败过已经失败则跳过
            if doc_id not in origin_data:
                origin_data[doc_id] = {
                    'document_data': document,
                    'fail_reason': False,
                    'model': doc_model,
                    'line_ids': [],
                    'line_gov_ids': [],
                }
            
            if not origin_data[doc_id]['fail_reason']:
                try:
                    # 计算凭证日期
                    if not origin_data[doc_id].get('business_date', None):
                        # 计算凭证日期
                        biz_date = fields.Date.today() if template.is_sys_date else document.get(template.vou_date_field_name, None)
                        if not biz_date:
                            # 业务日期字段值未从来源单据上取到，请重新设置凭证方案上的业务日期字段的配置
                            raise ValidationError(_('The business date field value was not retrieved from the source document. ' \
                                + 'Reset the configuration of the business date field on the credential template'))
                        origin_data[doc_id]['business_date'] = biz_date

                    account_id = acct_set_line.account_id
                    # 币别/汇率
                    curr_id, curr_rate = self._get_currency_data(data, doc_model, config_data, account_id)
                    # 如果币别为空，则跳过，不进行生成
                    if curr_id:
                        # 金额
                        amount, amount_local  = self._get_amount_data(data, config_data, curr_id)
                        # 如果金额为0则跳过，否则生成凭证时会因为借贷方都为0而报错（比如收款单中，手续费、折扣都是非必填，可能出现某一行明细金额为0）
                        if amount:
                            # 摘要
                            summary = self._get_summary(document, config_data['summary_text'], config_data['summary_fields'], doc_fields)
                            # 辅助核算
                            flex, auxiliary, gov_auxiliary = self._get_auxiliary(data, config_data, acct_set_line) 
                            is_debit = config_data['direction'] == 'debit'
                            # 数量核算
                            qty_data = self._get_qty_account_data(data, config_data, acct_set_line, curr_id, curr_rate, is_debit)
                            # 更新凭证明细数据
                            origin_data[doc_id]['line_ids'].append({
                                'amount': amount,
                                'debit': amount if is_debit else 0,
                                'credit': amount if not is_debit else 0,
                                'debit_local': amount_local if is_debit else 0,
                                'credit_local': amount_local if not is_debit else 0,
                                'account_id': account_id.id,
                                'summary': summary, # 摘要
                                'currency_id': curr_id, # 币别
                                'curr_rate': curr_rate, # 汇率
                                'flex': flex,
                                'auxiliary': auxiliary,
                                # 'gov_auxiliary': gov_auxiliary,
                                **qty_data
                            })
                    gov_account_id = acct_set_line.gov_account_id
                    if gov_account_id:
                        # 币别/汇率
                        gov_curr_id, gov_curr_rate = self._get_currency_data(data, doc_model, config_data, gov_account_id)
                        # 如果币别为空，则跳过，不进行生成
                        if gov_curr_id:
                            # 金额
                            gov_amount, gov_amount_local  = self._get_amount_data(data, config_data, gov_curr_id)
                            # 如果金额为0则跳过，否则生成凭证时会因为借贷方都为0而报错（比如收款单中，手续费、折扣都是非必填，可能出现某一行明细金额为0）
                            if gov_amount:
                                # 摘要
                                gov_summary = self._get_summary(document, config_data['summary_text'], config_data['summary_fields'], doc_fields)
                                # 辅助核算
                                gov_flex, auxiliary, gov_auxiliary = self._get_auxiliary(data, config_data, acct_set_line) 
                                is_debit = config_data['direction'] == 'debit'
                                # 数量核算
                                qty_data = self._get_qty_account_data(data, config_data, acct_set_line, gov_curr_id, gov_curr_rate, is_debit)
                                # 更新凭证明细数据
                                origin_data[doc_id]['line_gov_ids'].append({
                                    'amount': gov_amount,
                                    'debit': gov_amount if is_debit else 0,
                                    'credit': gov_amount if not is_debit else 0,
                                    'debit_local': gov_amount_local if is_debit else 0,
                                    'credit_local': gov_amount_local if not is_debit else 0,
                                    'account_id': gov_account_id.id,
                                    'summary': gov_summary, # 摘要
                                    'currency_id': gov_curr_id, # 币别
                                    'curr_rate': gov_curr_rate, # 汇率
                                    'flex': gov_flex,
                                    # 'auxiliary': auxiliary,
                                    'gov_auxiliary': gov_auxiliary,
                                    **qty_data
                                })
                except ValidationError as e:
                    # 捕获异常则记录失败信息
                    origin_data[doc_id]['fail_reason'] = e.name

    def _get_line_domain(self, domain, src_doc_ids, parent_field, child_field):
        """
        将来源单据domain，转化为明细行domain
        @param domain: 来源单据domain
        @param src_doc_ids: 来源单据id列表
        @param child_field: 来源单据表体对应的字段
        @return 返回来源单据明细行domain
        """
        result = [(parent_field, 'in', src_doc_ids)]
        for item in domain:
            if isinstance(item, (list, tuple)) and len(item) == DOMAIN_LENGTH:
                fields = item[DOMAIN_FIELD_INDEX].split('.', DOMAIN_FIELD_SPLIT_NUM)
                # 如果domain是当前表体字段, 则去掉字段前缀
                if len(fields) == DOMAIN_FIELD_SPLIT_LENGTH and child_field == fields[DOMAIN_FIELD_SPLIT_CHILD_INDEX]:
                    left = fields[DOMAIN_FIELD_SPLIT_OTHER_INDEX]
                else: 
                    left = '.'.join([parent_field, item[DOMAIN_FIELD_INDEX]])
                result.append((left, item[DOMAIN_OPT_INDEX], item[DOMAIN_VALUE_INDEX]))
            else:
                result.append(item)
        return result

    def _get_relation_model(self, source_doc_model, is_fetch_other_model, template_line):
        """
        获取明细或第三方模型的模型名称
        @param 来源单据模型
        @param is_fetch_other_model: 是否配置关联模型
        @param template_line: 凭证方案明细
        """
        entry_model = rel_model = None
        model = template_line.amount_model
        # 如果配置了第三方模型，需要判断金额字段是否从第三方模型上获取;否则，明细模型就是金额字段对应的模型
        if is_fetch_other_model:
            fetch_id = template_line.fetch_id
            # 如果金额字段模型是第三方模型，则更新明细、第三方模型；否则逻辑中不会用到第三方模型，只配置
            if model == fetch_id.rel_model:
                entry_model = fetch_id.entry_model
                rel_model = fetch_id.rel_model
            else:
                entry_model = model
        elif model != source_doc_model:
            entry_model = model
        return entry_model, rel_model

    def _get_origin_data(self, template, documents, template_data):
        """
        根据分录条件和科目取值，过滤单据（或单据明细行），组装生成凭证所需数据
        TODO: 目前分录条件、科目取值都是domain过滤，描述性比较强（如like）等，所以需要先生成domain,根据domain从数据库取值；
        如果后期优化过滤控件，考虑先根据单据范围过滤全部单据，减少数据库的交互，根据过滤条件筛选
        @param template: 凭证方案
        @param documents: 根据单据范围过滤得到的单据
        @param template_data: 凭证方案配置字典
        @return 生成凭证所需数据
        """
        origin_data = {}
        o2m_data = {field.comodel_name: (name, field.inverse_name) for name, field in documents._fields.items() if field.type == 'one2many'}
        is_fetch_other_model = template.is_fetch_other_model
        # TODO: 后期需要根据过滤选择界面的优化进行调整
        # 1、若模板分录的金额设置取的是表头字段，模板分录的其它要素（科目影响因素、核算维度、币别、摘要、分录行生成条件）也应该设置成取表头字段；
        # 若金额取表头字段，其它要素取表体字段，可能会导致取不到值甚至引起凭证生成中断。
        # 2、若模板分录的金额取的是表体字段，模板分录的其它要素（科目影响因素、核算维度、币别、摘要、分录行生成条件）可以设置成取表头字段可以设置成表体字段。
        for index, template_line in enumerate(template.line_ids, START_INDEX):
            # 凭证方案明细行对应的来源单据/来源单据明细/第三方模型
            entry_model, rel_model = self._get_relation_model(documents._name, is_fetch_other_model, template_line)
            # 获取表体的映射字段
            field_name, inverse_name = o2m_data.get(entry_model, (None, None))
            # 获取第三方模型的过滤
            fetch_id = template_line.fetch_id
            relation_domain = []
            if is_fetch_other_model and fetch_id.filter_domain:
                relation_domain = safe_eval(fetch_id.filter_domain)

            summary = template_line.summary_id
            temp_line_data = {
                'line_index': index,
                'direction': template_line.direction,  # 借贷方向
                'curr_field': template_line.curr_field_name, # 来源单据币别字段
                'curr_rate_field': template_line.curr_rate_field_name, # 来源单据汇率字段
                'curr_model': template_line.curr_field_model, # 币别/汇率字段所在模型
                'amount_field': template_line.amount_field_name, # 原币字段
                'standard_amount_field': template_line.standard_amount_field_name, # 本位币字段
                'amount_formula': template_line.amount_formula, # 原币计算公式
                'amount_local_formula': template_line.amount_local_formula, # 本位币计算公式
                'amount_model': template_line.amount_model, # 金额字段所在模型
                'entry_model': entry_model, # 来源单据明细行对应模型（可能与来源单据模型一样）
                'parent_field_name': inverse_name, # 明细行关联字段
                'relation_model': rel_model, # 关联模型（第三方模型）
                'relation_domain': relation_domain, # 关联模型（第三方模型）的过滤条件
                'relation_field_name':  fetch_id.rel_field_name, #关联模型（第三方模型）关联字段
                'summary_text': summary.summary, # 摘要text内容
                'summary_fields': summary.source_doc_fields.mapped('name'), # 摘要涉及到的字段（都是表头的）
                **template_data
            }
            # 分录规则domain
            filter_domain = template_line.condition_id.filter_domain
            line_domain = safe_eval(filter_domain) if filter_domain else []
            for acct_set_line in template_line.account_setting_id.line_ids:
                # 科目取值规则domain
                account_filter_domain = acct_set_line.account_condition_id.filter_domain
                account_domain = safe_eval(account_filter_domain) if account_filter_domain else []

                # 筛选源单据
                filter_docs = None
                filter_lines = None
                if line_domain or account_domain:
                    source_doc_ids = documents.ids
                    domain = line_domain + account_domain
                    # 如果field_name为空，则过滤原单据；否则代表需要获取表体数据
                    if not field_name:
                        filter_docs = documents.with_context(disable_state_filter=True).search([('id', 'in', source_doc_ids)] + domain)
                    else:
                        # 将源单据domain,转化为明细行domain
                        domain = self._get_line_domain(domain, source_doc_ids, inverse_name, field_name)
                        entry_model_obj = self.env[entry_model]
                        filter_lines = entry_model_obj.with_context(disable_state_filter=True).search(domain)
                        filter_docs = filter_lines[inverse_name]
                else:
                    filter_docs = documents
                    filter_lines = documents[field_name] if field_name else None
                
                # 如果没有符合条件的数据，直接跳过
                if filter_docs:
                    self._update_origin_data(origin_data, filter_docs, filter_lines, temp_line_data, acct_set_line)
        return origin_data

    def _update_tracking_vals(self, tracking_vals, pending_vals, fail_info=None, voucher=None):
        """
        更新追踪数据列表，在待处理的追踪数据列表中增加失败信息或凭证信息
        @param tracking_vals: 已存在的追踪数据列表
        @param pending_vals: 待处理的数据列表
        @param fail_info: 失败信息
        @param voucher: 凭证对象
        """
        for val in pending_vals:
            if fail_info:
                val['fail_reason'] = fail_info
            else:
                val.update({
                    'voucher_id_id': voucher.id,
                    'voucher_number': voucher.voucher_word_and_number,
                    'local_currency_id': voucher.local_currency_id.id
                })
            tracking_vals.append(val)
    
    def _merge_voucher_lines(self, exist_lines, exist_mapping, pending_lines, local_currency_id):
        """
        合并凭证明细行
        @param exist_lines: 已有的凭证明细行
        @param exist_mapping: 已有凭证行的坐标映射（{摘要-科目-辅助核算-币别组成的key: 在列表（exist_lines）中的位置}）
        @param pending_lines: 待处理的明细行列表
        @param local_currency_id: 本位币id
        """
        for line in pending_lines:
            currency_id = line['currency_id']
            uom_id = line.get('uom_id')
            # 根据摘要、科目、辅助核算、币别、单位、规格型号、单价进行合并
            line_key = (line['summary'], line['account_id'], line['auxiliary'], currency_id, uom_id, line.get('specification'), line.get('price'))
            if line_key in exist_mapping:
                currency_id = line['currency_id']
                exist_line = exist_lines[exist_mapping[line_key]]
                exist_line['debit'] = self._round(exist_line['debit'] + line['debit'], currency_id)
                exist_line['credit'] = self._round(exist_line['credit'] + line['credit'], currency_id)
                exist_line['debit_local'] = self._round(exist_line['debit_local'] + line['debit_local'], local_currency_id)
                exist_line['credit_local'] = self._round(exist_line['credit_local'] + line['credit_local'], local_currency_id)
                if uom_id:
                    exist_line['debit_qty'] = self._round_qty(exist_line['debit_qty'] + line['debit_qty'], uom_id)
                    exist_line['credit_qty'] = self._round_qty(exist_line['credit_qty'] + line['credit_qty'], uom_id)
            else:
                exist_mapping[line_key] = len(exist_lines)
                exist_lines.append(line)

    def _merge_voucher(self, origin_data, merge_fields, accting_org_id, accting_book, template_id, is_merge_voucher, voucher_word_id):
        """
        合并凭证
        @param origin_data: 原始数据
        @param merge_fields: 合并依据字段列表
        @param accting_org_id: 核算组织id
        @param accting_book_id: 账簿
        @param template_id: 凭证模板对象
        @param is_merge_voucher： 是否选单合并生成凭证标志位 
        @param voucher_word_id: 凭证字
        """
        # 合并时的映射关系
        # {
        #     voucher_key1: (voucher_index1, {
        #         line_key1: line_index1,
        #         line_key2: line_index2
        #     }),
        #     voucher_key2: (voucher_index2, {
        #         line_key3: line_index3,
        #         line_key4: line_index4
        #     }),
        # }
        merge_mapping = {}
        period_cache = {} # 日期及期间的映射关系
        voucher_vals = [] # 合并后的凭证数据
        tracking_vals = [] # 待创建追踪数据列表

        calendar_obj = self.env['mdm.account.calendar']
        calendar_id = accting_book.calendar_id.id
        module_id_id = template_id.source_module_id.id
        # TODO:改造更改处：未改（兼容处理，待模板字段必填后，去除biz_date）
        date_field = template_id.vou_date_field_name or "biz_date"
        if is_merge_voucher:
            merge_doc_key = tuple(origin_data.keys())
        for doc_id, data in origin_data.items():
            business_date = data.get('business_date', None)
            # 业务日期为空时，期间也为空
            if not business_date:
                accting_period_id = None
            else:
                if business_date not in period_cache:
                    period_cache[business_date] = calendar_obj.get_period_by_biz_date(business_date, calendar_id).id
                accting_period_id = period_cache[business_date]

            document = data['document_data']
            tacking_data = {
                'template_id': template_id.id, # 凭证方案
                'domain_id': template_id.source_domain_id.id, # 来源单据领域
                'res_model_id': template_id.source_doc_id.id, # 来源单据
                'res_model': template_id.source_doc_model, # 来源单据模型
                'res_id_id': doc_id, # 单据id
                'res_number': document.get('number', ''), # 单据编号
                'biz_date': document.get(date_field, ''), # 业务日期
                'state': document.get('state', ''), # 单据状态
                'accting_org_id': accting_org_id, # 核算组织
                'accting_book_id': accting_book.id, # 账簿
                'accting_period_id': accting_period_id, # 期间
            }
            if data['fail_reason']:
                # 更新跟踪数据
                self._update_tracking_vals(tracking_vals, [tacking_data], data['fail_reason'])
            else:
                # 单据合并 & 分录合并
                if is_merge_voucher:
                    doc_key = merge_doc_key
                else:
                    doc_key = tuple(document.get(field, None) for field in merge_fields) if merge_fields else doc_id
                # 如果不存在凭证，则新增一个
                line_ids = data.pop('line_ids')
                line_gov_ids = data.pop('line_gov_ids')
                if doc_key not in merge_mapping:
                    merge_mapping[doc_key] = (len(voucher_vals), {})
                    voucher_vals.append({
                        'accting_org_id': accting_org_id,
                        'acct_book_id': accting_book.id,
                        'acct_period_id': accting_period_id,
                        'voucher_word_id': voucher_word_id or accting_book.voucher_word_id.id,
                        'gov_voucher_word_id': accting_book.gov_voucher_word_id.id or accting_book.voucher_word_id.id,  #预算凭证字
                        'voucher_source': data['model'], # 凭证来源
                        'source_module_id': module_id_id, # 系统来源-模块名称
                        'system_source': 'account_center',
                        'business_date': data['business_date'], # 凭证日期
                        'state': 'save',
                        'document_type_id': None,
                        'cancel_state': 'normal',
                        'delete_state': 'normal',
                        'number_state': 'generate',
                        'is_convert': False,
                        'is_cash_set': False,
                        'is_adjustment_period': False,
                        'cashier_review_state': 'uncompleted',
                        'is_acct_type': False,
                        'post_state': '00',
                        'line_ids': [],
                        'line_gov_ids': [],
                        'trackings': [],
                        'docs': []
                    })

                # 凭证明细行合并
                voucher_index, line_mapping = merge_mapping[doc_key]
                if template_id.is_combine:
                    self._merge_voucher_lines(voucher_vals[voucher_index]['line_ids'], line_mapping, line_ids, accting_book.currency_id.id)
                else:
                    voucher_vals[voucher_index]['line_ids'].extend(line_ids)
                    voucher_vals[voucher_index]['line_gov_ids'].extend(line_gov_ids)
                # 增加一个追踪记录
                voucher_vals[voucher_index]['trackings'].append(tacking_data)
                voucher_vals[voucher_index]['docs'].append((doc_id, document['number']))        
        return voucher_vals, tracking_vals

    def _get_real_voucher_lines(self, voucher_lines, is_combine):
        """
        获取凭证明细行，对借贷合并后的金额进行处理（明细行合并时可能会出现借贷相抵的情况，此类凭证不能生成）
        并给新的凭证明细行分配序号
        @param voucher_lines: 待处理的凭证明细行
        @param is_combine: 是否合并明细（不合并的则不需要判断借贷方，只生成序号即可）
        """
        result = []
        sequence = START_INDEX
        for voucher_line in voucher_lines:
            if is_combine:
                currency_id = voucher_line['currency_id']
                debit = voucher_line['debit']
                credit = voucher_line['credit']
                # 如果借贷相等，则抵消
                if self._float_compare(debit, credit, currency_id) == 0:
                    continue
                
                debit_local = voucher_line['debit_local']
                credit_local = voucher_line['credit_local']
                debit_qty = voucher_line['debit_qty']
                credit_qty = voucher_line['credit_qty']
                # 1. 如果借贷同号，将最终展示根据原值统计（正/负数）放在借贷双方中绝对值大的方向
                #   例如：借50，贷100，最终展示：贷50；借-50，贷-100，最终展示：贷-50
                # 2. 如果借贷异号，最终展示根据原值统计（正数）放在借贷双方中数值为正数的方向
                #   例如：借50，贷-100，最终展示：借150
                # 3. 如果借贷一方为0，则无需处理
                # 4. 数量的合并方式和金额一致
                to_update = None # 字段顺序：借方金额、贷方金额、借方金额本位币、贷方金额本位币、借方数量、贷方数量
                if debit * credit > 0:
                    # 绝对值大的一方作为被减数，绝对值小的一方作为减数，差值结果作为绝对值大的一方的值，绝对值小的一方为0
                    to_update = (debit - credit, 0, debit_local - credit_local, 0, debit_qty - credit_qty, 0) \
                        if self._float_compare(abs(debit), abs(credit), currency_id) > 0 \
                        else (0, credit - debit, 0, credit_local - debit_local, 0, credit_qty - debit_qty)
                elif debit * credit < 0:
                    to_update = (debit - credit, 0, debit_local - credit_local, 0, debit_qty - credit_qty, 0) \
                        if self._float_compare(debit, credit, currency_id) > 0 \
                        else (0, credit - debit, 0, credit_local - debit_local, 0, credit_qty - debit_qty)
                if to_update:
                    debit, credit, debit_local, credit_local, debit_qty, credit_qty = to_update

                voucher_line.update({
                    'amount': debit or credit,
                    'debit': debit,
                    'credit': credit,
                    'debit_local': debit_local,
                    'credit_local': credit_local,
                    'qty': debit_qty or credit_qty,
                    'debit_qty': debit_qty,
                    'credit_qty': credit_qty
                })
            # 生成序号
            voucher_line['sequence'] = sequence
            result.append((0, 0, voucher_line))
            sequence += SEQUENCE_STEP_COUNT
        return result

    def _get_missing_trackings(self, accting_org_id, accting_book_id, template_id, missing_doc_ids):
        """
        获取缺失部门的错误提示（有一些单据可能被过滤条件过滤掉）
        @param template_id: 凭证模板
        @param missing_doc_ids: 缺少的单据的id列表
        """
        # 已执行生成凭证，不符合生成凭证条件
        fail_reason = _('Generated voucher has been executed and does not meet the conditions for generating vouchers')
        model_obj = self.env[template_id.source_doc_model]
        # TODO:改造更改处：未改（兼容处理，待模板字段必填后，去除biz_date）
        date_field = template_id.vou_date_field_name or "biz_date"
        read_list = []
        for rec in ['number', date_field, 'state']:
            if rec in model_obj._fields:
                read_list.append(rec)

        missing_docs = model_obj.browse(missing_doc_ids).read(read_list) 
        return [{
            'template_id': template_id.id, # 凭证方案
            'domain_id': template_id.source_domain_id.id, # 来源单据领域
            'res_model_id': template_id.source_doc_id.id, # 来源单据
            'res_model': template_id.source_doc_model, # 来源单据模型
            'res_id_id': doc['id'], # 单据id
            'res_number': doc.get('number', ''), # 单据编号
            'biz_date': doc.get(date_field, ''), # 业务日期
            'state': doc.get('state', ''), # 单据状态
            'accting_org_id': accting_org_id, # 核算组织
            'accting_book_id': accting_book_id, # 账簿
            'fail_reason': fail_reason
        } for doc in missing_docs]

    def _create_gov_voucher(self, documents, origin_data, merge_fields, accting_org_id, accting_book, template_id, is_merge_voucher, voucher_word_id):
        """
        对凭证及分录进行合并，并生产预算凭证
        @param documents: 全部的未生成凭证的来源单据列表
        @param origin_data: 单据原始数据
        @param merge_fields: 单据合并依据
        @param accting_org_id: 核算组织id
        @param accting_book: 账簿
        @param template_id: 凭证模板对象
        @param is_merge_voucher： 是否选单合并生成凭证标志位
        @param voucher_word_id: 凭证字
        """
        # 对单据及分录按照配置进行合并
        voucher_vals, tracking_vals = self._merge_voucher(
            origin_data, merge_fields, accting_org_id, accting_book, template_id, is_merge_voucher, voucher_word_id)
        
        # voucher_obj = self.env['gl.voucher']
        voucher_obj = self.env['gl.gov.voucher']
        # 已执行生成凭证，汇总模式导致凭证金额为0
        fail_info = _('Generated voucher has been executed and the summary mode results in a voucher amount of 0')
        link_vals = []
        voucher_ids = []
        # 创建凭证
        for data in voucher_vals:
            trackings = data.pop('trackings')
            docs = data.pop('docs')
            # 借贷相抵，获取凭证的明细行数据
            line_ids = self._get_real_voucher_lines(data.pop('line_ids'), template_id.is_combine)
            line_gov_ids = self._get_real_voucher_lines(data.pop('line_gov_ids'), template_id.is_combine)
            if not line_ids:
                # 如果借贷相抵为0，更新为生成失败
                self._update_tracking_vals(tracking_vals, trackings, fail_info)
            else:
                data['line_fin_ids'] = line_ids
                data['line_gov_ids'] = line_gov_ids
                # 创建凭证
                try:
                    # 创建保存点，如果创建失败自动回滚
                    with self.env.cr.savepoint():
                        voucher = voucher_obj.with_context(account_center=True, pass_authorize_check=True).create(data)
                except ValidationError as e:
                    # 更新生成失败原因
                    self._update_tracking_vals(tracking_vals, trackings, e.name)
                else:
                    # 更新成功信息，增加link表数据
                    self._update_tracking_vals(tracking_vals, trackings, voucher=voucher)
                    link_vals.extend([{
                        'source_doc_id': doc_id,
                        'source_model_key': template_id.source_doc_model,
                        'source_doc_num': doc_num,
                        'target_doc_id': voucher.id,
                        'target_doc_num': voucher.number,
                        'target_model_key': 'gl.voucher',
                        'record_type': 'acct_center',
                    } for doc_id, doc_num in docs])
                    voucher_ids.append(voucher.id)
        
        accting_book_id = accting_book.id
        # 对于未生成的单据（即被过滤条件过滤掉的的单据）生成追踪记录
        all_doc_ids = documents.ids
        tracking_vals.extend(self._get_missing_trackings(accting_org_id, accting_book_id, template_id, set(all_doc_ids) - set(origin_data.keys())))
        # 删除当前账簿，待生成凭证的单据列表的生成记录
        tacking_obj = self.env['acc.center.voucher.generation.tracking']
        tacking_obj.search([
            ('accting_book_id', '=', accting_book_id),
            ('res_model_id', '=', template_id.source_doc_id.id),
            ('res_id_id', 'in', all_doc_ids)
        ]).write({'delete_state': 'delete'})
        # 创建新的生成记录表
        if tracking_vals:
            tacking_obj.create(tracking_vals)
        # 创建link表数据
        if link_vals:
            relation_obj = self.env['studio.botp.record']
            relation_obj.create(link_vals)
    
        # 组织提示信息
        line_infos = []
        opt = _('Voucher Generation: %s') # 凭证生成: %s
        # 凭证生成成功  
        success_info = _('Successfully voucher generate')
        temporary_info = _('Temporary')
        for tracking_val in tracking_vals:
            state, info = SUCCESS_STATE, success_info
            if tracking_val.get('fail_reason'):
                state, info = FAILED_STATE, tracking_val['fail_reason']
            res_number = tracking_val.get('res_number', False)
            # 暂存单据无编码，生成凭证时提示信息编码位置显示暂存
            if not res_number:
                res_number = temporary_info
            line_infos.append(LineInfo(operation=opt % res_number, state=state, info=info))
        
        return line_infos, voucher_ids

    def _create_voucher(self, documents, origin_data, merge_fields, accting_org_id, accting_book, template_id, is_merge_voucher, voucher_word_id):
        """
        对凭证及分录进行合并，并生产凭证
        @param documents: 全部的未生成凭证的来源单据列表
        @param origin_data: 单据原始数据
        @param merge_fields: 单据合并依据
        @param accting_org_id: 核算组织id
        @param accting_book: 账簿
        @param template_id: 凭证模板对象
        @param is_merge_voucher： 是否选单合并生成凭证标志位
        @param voucher_word_id: 凭证字
        """
        # 对单据及分录按照配置进行合并
        voucher_vals, tracking_vals = self._merge_voucher(
            origin_data, merge_fields, accting_org_id, accting_book, template_id, is_merge_voucher, voucher_word_id)

        voucher_obj = self.env['gl.voucher']
        # 已执行生成凭证，汇总模式导致凭证金额为0
        fail_info = _('Generated voucher has been executed and the summary mode results in a voucher amount of 0')
        link_vals = []
        voucher_ids = []
        # 创建凭证
        for data in voucher_vals:
            trackings = data.pop('trackings')
            docs = data.pop('docs')
            # 借贷相抵，获取凭证的明细行数据
            line_ids = self._get_real_voucher_lines(data.pop('line_ids'), template_id.is_combine)
            if not line_ids:
                # 如果借贷相抵为0，更新为生成失败
                self._update_tracking_vals(tracking_vals, trackings, fail_info)
            else:
                data['line_ids'] = line_ids
                # 创建凭证
                try:
                    # 创建保存点，如果创建失败自动回滚
                    with self.env.cr.savepoint():
                        voucher = voucher_obj.with_context(account_center=True, pass_authorize_check=True).create(data)
                except ValidationError as e:
                    # 更新生成失败原因
                    self._update_tracking_vals(tracking_vals, trackings, e.name)
                else:
                    # 更新成功信息，增加link表数据
                    self._update_tracking_vals(tracking_vals, trackings, voucher=voucher)
                    link_vals.extend([{
                        'source_doc_id': doc_id,
                        'source_model_key': template_id.source_doc_model,
                        'source_doc_num': doc_num,
                        'target_doc_id': voucher.id,
                        'target_doc_num': voucher.number,
                        'target_model_key': 'gl.voucher',
                        'record_type': 'acct_center',
                    } for doc_id, doc_num in docs])
                    voucher_ids.append(voucher.id)
        
        accting_book_id = accting_book.id
        # 对于未生成的单据（即被过滤条件过滤掉的的单据）生成追踪记录
        all_doc_ids = documents.ids
        tracking_vals.extend(self._get_missing_trackings(accting_org_id, accting_book_id, template_id, set(all_doc_ids) - set(origin_data.keys())))
        # 删除当前账簿，待生成凭证的单据列表的生成记录
        tacking_obj = self.env['acc.center.voucher.generation.tracking']
        tacking_obj.search([
            ('accting_book_id', '=', accting_book_id),
            ('res_model_id', '=', template_id.source_doc_id.id),
            ('res_id_id', 'in', all_doc_ids)
        ]).write({'delete_state': 'delete'})
        # 创建新的生成记录表
        if tracking_vals:
            tacking_obj.create(tracking_vals)
        # 创建link表数据
        if link_vals:
            relation_obj = self.env['studio.botp.record']
            relation_obj.create(link_vals)
    
        # 组织提示信息
        line_infos = []
        opt = _('Voucher Generation: %s') # 凭证生成: %s
        # 凭证生成成功  
        success_info = _('Successfully voucher generate')
        temporary_info = _('Temporary')
        for tracking_val in tracking_vals:
            state, info = SUCCESS_STATE, success_info
            if tracking_val.get('fail_reason'):
                state, info = FAILED_STATE, tracking_val['fail_reason']
            res_number = tracking_val.get('res_number', False)
            # 暂存单据无编码，生成凭证时提示信息编码位置显示暂存
            if not res_number:
                res_number = temporary_info
            line_infos.append(LineInfo(operation=opt % res_number, state=state, info=info))
        
        return line_infos, voucher_ids
        
    ################################  私有方法区  end  ################################


    ################################  公共方法区  start  ################################

    def p_create_generation(self, account_book):
        """
        账簿初始化成功时调用该方法，当账簿初始化成功后创建一个凭证生成账簿数据，并且查询所有的凭证方案，将其中账簿为本账簿的以及账簿为空的凭证方案筛选出来
        然后将筛选出来的凭证方案，创建到凭证生成行上面去。
        """
        if self.search_count([('acct_book_id', '=', account_book.id), ('delete_state', '=', 'normal')]):
            return False
        templates = self.env['acc.center.template'].search([
            '|', ('acct_book_id', '=', False), ('acct_book_id', '=', account_book.id),
            ('forbid_state', '=', 'normal'),
            ('delete_state', '=', 'normal')
            ])
        self.create({
            'acct_book_id': account_book.id,
            'line_ids': [(0, 0, {
                    'source_doc_id': template.source_doc_id.id,
                    'source_doc_model': template.source_doc_id.model,
                    'template_id': template.id
                }) for template in templates]
            })
        return True

    def p_delete_generation(self, book_id):
        """
        账簿反初始化成功时调用该方法，删除当前账簿下对应的凭证生成数据。
        """
        voucher_generation = self.search([('acct_book_id', '=', book_id.id), ('delete_state', '=', 'normal')])
        voucher_generation_lines = self.env['acc.center.voucher.generation.line1'].search([('parent_id', '=', voucher_generation.id)])
        uid = self.env.user.id
        if voucher_generation_lines:
            voucher_generation_lines.unlink()
        voucher_generation.write({
            'delete_state': 'delete',
            'delete_uid': uid,
            'delete_date': fields.Datetime.now()
        })

    def p_generate_vouchers(self, lines, start_date, end_date, is_merge_voucher, voucher_word_id, doc_ids=None):
        """
        生成凭证
        @param lines: 凭证生成明细
        @param start_date: 开始日期
        @param end_date: 结束日期
        @param is_merge_voucher: 是否合并生成凭证
        @param voucher_word_id: 凭证字
        @param doc_ids： 待合并单据ID列表
        """
        curr_rate_getter = self._get_currency_rate()
        flex_obj = self.env['ir.model.flex.fields']
        flex_name_mapping = {f.relation: f.name for f in flex_obj.search([('model', '=', 'gl.voucher.line1')])}

        line_infos = [] # 提示信息
        voucher_ids = [] # 凭证id列表
        for line in lines:
            parent = line.parent_id
            accting_org_id = parent.acct_org_id.id
            # 根据核算组织获取其包含的业务组织列表
            org_ids = parent.acct_sys_id.accting_org_ids.filtered(
                lambda org: org.org_id.id == accting_org_id).accting_org_line_ids.org_id.ids
            if accting_org_id not in org_ids:
                org_ids.append(accting_org_id)
            accting_book = parent.acct_book_id
            template_id = line.template_id
            if doc_ids:
                documents = self.env[line.source_doc_model].browse(doc_ids)
            else:
                # 获取根据开始日期和结束日期获取方案对应的来源单据列表
                documents = self._get_source_docs(org_ids, accting_book.id, template_id, start_date, end_date)
            
            # 如果无符合条件来源单据则跳过
            if documents:
                temp_data = {
                    'local_currency_id': accting_book.currency_id.id, # 默认(本位)币种
                    'curr_rate_ctg_id': accting_book.curr_rate_ctg_id.id, # 汇率类别
                    'curr_rate_getter': curr_rate_getter, # 汇率获取
                    'flex_name_mapping': flex_name_mapping, # 弹性域名称对应关系
                    'template_id': template_id, # 凭证方案
                    'merge_fields': [], # 单据合并依据（TODO: 目前已去掉，后续可能会增加）
                }
                # 获取单据原始数据
                orgin_data = self._get_origin_data(template_id, documents, temp_data)
                # 创建凭证
                if template_id.is_gov:
                    infos, ids = self._create_gov_voucher(documents, orgin_data, temp_data['merge_fields'], accting_org_id, accting_book, template_id, is_merge_voucher, voucher_word_id)
                else:
                    infos, ids = self._create_voucher(documents, orgin_data, temp_data['merge_fields'], accting_org_id, accting_book, template_id, is_merge_voucher, voucher_word_id)
                line_infos.extend(infos)
                voucher_ids.extend(ids)
            
        if not line_infos:
            # 未根据条件找到符合条件的单据请重新检查条件设置，或者您选择的单据已经生成过凭证，无法重复生成凭证
            raise ValidationError(_('No matching documents are found according to the conditions, please recheck the condition settings'))
        to_return = on_close = None
        if template_id.is_gov:
            views = [(self.env.ref('ps_gl.view_gl_gov_voucher_tree').id, 'list'), (self.env.ref('ps_gl.view_gl_gov_voucher_form').id, 'form')]
            res_model = 'gl.gov.voucher'
            ref = 'ps_gl.action_gl_gov_voucher'
        else:
            views = [(self.env.ref('ps_gl.view_gl_voucher_tree').id, 'list'), (self.env.ref('ps_gl.view_gl_voucher_form').id, 'form')]
            res_model = 'gl.voucher'
            ref = 'ps_gl.action_gl_voucher'
        if voucher_ids:
            action = {
                'type': 'ir.actions.act_window',
                'view_mode': 'list,form',
                'views': views,
                'res_model': res_model,
                'domain': [('id', 'in', voucher_ids), ('delete_state', '=', 'normal')],
                'context': {'flex_apply_model': 'line_ids'},
                'ref': ref,
            }
            # 如果只有一张凭证，则直接跳转至form界面
            if len(voucher_ids) == 1:
                action.update({
                    'res_id': voucher_ids[0],
                    'view_type': 'form',
                })
            to_return = on_close = action
        # 创建生成凭证，并返回创建成功的凭证页面
        return InfoWindow.info(line_infos, to_return=to_return, on_close=on_close)

    ################################  公共方法区  end  ################################


    ################################  覆盖基类方法区  start  ################################

    @sys_ele_ctrl()
    @api.model
    def pre_write(self,res):
        return super(AccCenterVoucherGeneration, self).pre_write(res)

    @sys_ele_ctrl()
    def read(self, fields=None, load='_classic_read'):
        return super(AccCenterVoucherGeneration, self).read(fields, load)

    ################################  覆盖基类方法区  end  ################################


    ################################  其他方法区  start  ################################

    ################################  其他方法区  end  ################################