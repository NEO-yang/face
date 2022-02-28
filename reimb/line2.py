# -*- coding: utf-8 -*-
'''
==================================================
@创建人: Vic Sun
@当前维护人: Vic Sun
@Desc: 差旅费报销单
==================================================
'''
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import float_compare

from .er_travel import MIN_AMOUNT, MIN_TAX_RATE, MAX_TAX_RATE, TAX_RATE_PERCISION


DEFAULT_TAX = 0 # 默认税额


class ErTravelLine1Line2(models.Model):
    _inherit = 'er.travel.line1.line2'
    _order = 'sequence'

    ################################  default start  ################################

    def _selection_accting_state(self):
        """
        核算状态，与费用项目保持一致
        """
        # TODO: 需要重新适配项目
        return []

    ################################  default end    ################################


    ################################  字段定义区 start  ################################

    delete_state = fields.Selection(related='parent_id.delete_state', readonly=True)
    # 申请/核定报销金额
    req_amount = fields.Float(compute='_compute_req_amount_and_aprv_amount')
    req_amount_lc = fields.Float(compute='_compute_req_amount_and_aprv_amount')
    aprv_amount = fields.Float(compute='_compute_req_amount_and_aprv_amount')
    aprv_amount_lc = fields.Float(compute='_compute_req_amount_and_aprv_amount')
    # 税额
    tax_lc = fields.Float(compute='_compute_tax_lc')
    # 费用金额
    exp_amount = fields.Float(compute='_compute_exp_amount')
    exp_amount_lc = fields.Float(compute='_compute_exp_amount')
    

    ################################  字段定义区 end    ################################


    ################################  计算方法区 start  ################################

    @api.depends('amount')
    def _compute_req_amount_and_aprv_amount(self):
        """
        计算申请/核定报销金额 = 差旅费金额
        """
        for rec in self:
            amount = rec.amount
            rec.req_amount = amount
            rec.aprv_amount = amount

            curr_rate = rec.parent_id.parent_id.curr_rate
            local_currency_id = rec.parent_id.parent_id.local_currency_id.id
            amount_lc = self._round(amount * curr_rate, local_currency_id)
            rec.req_amount_lc = amount_lc
            rec.aprv_amount_lc = amount_lc
    
    @api.depends('tax')
    def _compute_tax_lc(self):
        """
        计算税额本位币
        """
        for rec in self:
            curr_rate = rec.parent_id.parent_id.curr_rate
            local_currency_id = rec.parent_id.parent_id.local_currency_id.id
            rec.tax_lc = self._round(rec.tax * curr_rate, local_currency_id)

    @api.depends('aprv_amount', 'tax')
    def _compute_exp_amount(self):
        """
        计算费用金额 = 核定金额 - 税额
        """
        for rec in self:
            currency_id = rec.parent_id.parent_id.currency_id.id
            rec.exp_amount = self._round(rec.aprv_amount - rec.tax, currency_id)
            local_currency_id = rec.parent_id.parent_id.local_currency_id.id
            rec.exp_amount_lc = self._round(rec.aprv_amount_lc - rec.tax_lc, local_currency_id)

    ################################  计算方法区 end    ################################


    ################################  onchange方法区  start  ################################

    def _default_exp_date(self):
        """
        获取费用日期默认值
        """
        apply_date = self.parent_id.parent_id.apply_date
        project_id = self.parent_id.parent_id.project_id
        self.exp_date = None
        # 判断申请日期是否超出项目日期范围
        if self._is_valid_exp_date(project_id, apply_date):
            self.exp_date = apply_date
        else:
            # 申请日期超出项目日期范围，考虑带出当前日期
            today = fields.Date.today()
            if self._is_valid_exp_date(project_id, today):
                self.exp_date = today
    
    def _onchange_exp_date(self):
        """
        费用日期变更时，校验费用日期是否超出项目日期范围，更新核算状态
        """
        project_id = self.parent_id.parent_id.project_id
        if not self._is_valid_exp_date(project_id, self.exp_date):
            # 费用日期已超出所选项目的时间范围，请检查
            raise ValidationError(_('The expense date is out of the selected project time range, please check'))
        self.accting_state = self._get_accting_state(project_id, self.exp_date)

    def _onchange_exp_item_id(self):
        """
        费用项目（报销事项）变更时，修改发票类型的过滤范围和默认值
        """
        default_inv_type_id, domain = self._get_default_inv_type_and_domain()
        self.inv_type_id = default_inv_type_id
        return {
            'domain': {
                'inv_type_id': domain
            }
        }
    
    def _onchange_exp_type_id(self):
        """
        差旅费类型变更时，修改发票类型的过滤范围和默认值、交通工具可选范围、是否实名
        """
        # 发票类型的过滤范围和默认值
        default_inv_type_id, inv_type_domain = self._get_default_inv_type_and_domain()
        self.inv_type_id = default_inv_type_id
        # 更新税率税额
        self._onchange_inv_type_id()
        # 交通工具可选范围
        if self.exp_type_id.is_traffic_tool_required:
            traffic_tool_domain = [('id', 'in', self.exp_type_id.traffic_tool_ids.ids)]
        else:
            traffic_tool_domain = []
        # 更新是否实名默认值
        if self.exp_type_id.is_name_required:
            self.whether_real_name = 'yes'
        else:
            self.whether_real_name = None
        return {
            'domain': {
                'inv_type_id': inv_type_domain,
                'traffic_tool_id': traffic_tool_domain
            }
        }
    
    def _onchange_exp_type_id_copy(self):
        """
        复制时，更新发票类型、交通工具可选范围
        """
        # 发票类型可选范围
        default_inv_type_id, inv_type_domain = self._get_default_inv_type_and_domain()
        # 交通工具可选范围
        exp_type_id = self.exp_type_id
        if exp_type_id.is_traffic_tool_required:
            traffic_tool_domain = [('id', 'in', exp_type_id.traffic_tool_ids.ids)]
        else:
            traffic_tool_domain = []
        return {
            'domain': {
                'inv_type_id': inv_type_domain,
                'traffic_tool_id': traffic_tool_domain
            }
        }
    
    def _onchange_inv_type_id(self):
        """
        切换发票类型时，更新税率和税额
        """
        # 更新税率
        self._update_tax_rate()
        # 更新税额
        self._update_tax()
    
    def _onchange_whether_real_name(self):
        """
        切换是否实名，更新税率
        """
        # 更新税率
        self._update_tax_rate()
        # 更新税额
        self._update_tax()
    
    def _onchange_amount(self):
        """
        校验差旅费金额不能小于0
        """
        if self._float_compare(self.amount, MIN_AMOUNT, self.parent_id.parent_id.currency_id.id) == -1:
            # 差旅费金额不能小于0
            raise ValidationError(_('The amount of travel expenses shall not be less than 0'))
        # 更新税额
        self._update_tax()
    
    def _onchange_ticket_amount(self):
        """
        校验票价金额不能小于0
        """
        if self._float_compare(self.ticket_amount, MIN_AMOUNT, self.parent_id.parent_id.currency_id.id) == -1:
            # 票价金额不能小于0
            raise ValidationError(_('The amount of travel expenses shall not be less than 0'))
        # 更新税额
        self._update_tax()
    
    def _onchange_dev_fund(self):
        """
        校验民航发展基金不能小于0
        """
        if self._float_compare(self.dev_fund, MIN_AMOUNT, self.parent_id.parent_id.currency_id.id) == -1:
            # 民航发展基金不能小于0
            raise ValidationError(_('The amount of civil aviation development fund shall not be less than 0'))
    
    def _onchange_fuel_surcharge(self):
        """
        校验燃油附加费金额不能小于0
        """
        if self._float_compare(self.fuel_surcharge, MIN_AMOUNT, self.parent_id.parent_id.currency_id.id) == -1:
            # 燃油附加费金额不能小于0
            raise ValidationError(_('The amount of fuel surcharge shall not be less than 0'))
        # 更新税额
        self._update_tax()

    def _onchange_other_tax(self):
        """
        校验其他税费不能小于0
        """
        if self._float_compare(self.other_tax, MIN_AMOUNT, self.parent_id.parent_id.currency_id.id) == -1:
            # 其他税费不能小于0
            raise ValidationError(_('The amount of other taxes shall not be less than 0'))
    
    def _onchange_other_amount(self):
        """
        校验机票其他金额不能小于0
        """
        if self._float_compare(self.other_amount, MIN_AMOUNT, self.parent_id.parent_id.currency_id.id) == -1:
            # 机票其他金额不能小于0
            raise ValidationError(_('The other amount of air ticket shall not be less than 0'))
    
    def _onchange_tax_rate(self):
        """
        校验税率0-100
        """
        if float_compare(self.tax_rate, MIN_TAX_RATE, TAX_RATE_PERCISION) == -1 or \
            float_compare(self.tax_rate, MAX_TAX_RATE, TAX_RATE_PERCISION) == 1:
            # 税率必须介于0~100
            raise ValidationError(_('The tax rate must be between 0 and 100'))
        # 更新税额
        self._update_tax()
    
    def _onchange_tax(self):
        """
        校验税额不能小于0
        """
        if float_compare(self.tax, MIN_AMOUNT, self.parent_id.parent_id.currency_id.id) == -1:
            # 税额不能小于0
            raise ValidationError(_('The amount of taxes shall not be less than 0'))

    ################################  onchange方法区  end    ################################


    ################################  约束方法区  start  ################################
    
    ################################  约束方法区  end    ################################


    ################################  服务器动作区  start  ################################
    
    ################################  服务器动作区  end    ################################


    ################################  按钮动作区  start  ################################

    ################################  按钮动作区  end    ################################


    ################################  私有方法区  start  ################################

    def _is_valid_exp_date(self, project_id, exp_date):
        """
        校验费用日期是否超出项目时间范围
        """
        if project_id and exp_date:
            establish_date = project_id.establish_date
            # 结项日期为空时使用当前日期
            closing_date = project_id.closing_time or fields.Date.today()
            if establish_date and not establish_date <= exp_date <= closing_date:
                return False
        return True

    def _get_accting_state(self, project_id, exp_date):
        """
        根据项目和费用日期获取核算状态
        """
        accting_state = None
        if project_id and exp_date:
            for project_line in project_id.line1_ids:
                start_date = project_line.start_date
                end_date = project_line.end_date
                # 如果费用日期在此项目明细中，则核算状态为项目明细核算状态，并跳出循环
                if start_date <= exp_date <= end_date:
                    accting_state = project_line.accting_state
                    break
        return accting_state

    def _get_default_inv_type_and_domain(self):
        """
        获取发票类型的默认值和过滤
        """
        if self.exp_item_id and self.exp_type_id:
            default_inv_type_id = self.exp_type_id.inv_type_id.id
            inv_type_ids = self.exp_item_id.invoice_types.ids
            if not inv_type_ids:
                # 如果费用项目对应的可选发票类型为空，代表可选范围为全部，且默认发票类型一定在可选范围内
                domain = []
            else:
                # 如果费用项目对应的可选发票类型不为空，需判断默认发票类型是否在可选范围内，不在这默认为空
                if default_inv_type_id not in inv_type_ids:
                    default_inv_type_id = None
                domain = [('id', 'in', inv_type_ids)]
        else:
            default_inv_type_id = None
            domain = [('id', 'in', [])]
        
        return default_inv_type_id, domain

    def _update_tax_rate(self):
        """
        更新税率
        a. 如果选择的发票类型为飞机票、火车票时，税率自动携带
        b. 如果选择的发票类型为客运发票时，且当“是否实名”为“是”时携带税率
        c. 其他情况税率默认为0
        """
        inv_type_num = self.inv_type_id.number
        if inv_type_num in ('000007', '000008') or inv_type_num == '000009' and self.whether_real_name == 'yes':
            self.tax_rate = self.inv_type_id.defaul_tax_rate
        else:
            self.tax_rate = MIN_TAX_RATE
    
    def _update_tax(self):
        """
        更新税额
        """
        rate = self.tax_rate / 100
        if self.inv_type_id.number =='000008':
            # 飞机票：税额 =（票价+燃油附加费）/ (1 + 税率/100) * 税率/100
            self.tax = (self.ticket_amount + self.fuel_surcharge) / (1 + rate) * rate 
        else:
            # 其他：税额 = 差旅费金额 / (1 + 税率/100) * 税率/100
            self.tax = self.amount / (1 + rate) * rate
    
    ################################  私有方法区  end    ################################


    ################################  公共方法区  start  ################################
    
    ################################  公共方法区  end    ################################


    ################################  覆盖基类方法区  start  ################################
    
    ################################  覆盖基类方法区  end    ################################


    ################################  其他方法区  start  ################################

    ################################  其他方法区  end    ################################
    