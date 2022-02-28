# -*- coding: utf-8 -*-
"""
==================================================
@创建人 ：王琨鹏
@当前维护人 ：Vic Sun
@Desc ：凭证方案
==================================================
"""
import base64
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

from odoo.addons.ps_admin.sys_ele.sys_ele_ctrl import sys_ele_ctrl
from odoo.addons.ps_admin.biz_log.models.biz_log_item import BizLogItem
from odoo.addons.ps_admin.biz_log.models.biz_log_item import LogCategory, LogLevel
from odoo.addons.ps_admin.info_window.info_window import InfoWindow, LineInfo, SUCCESS_STATE, FAILED_STATE
from odoo.addons.ps_admin.sys_ele.models.net_control import ControlLevel,BeforeOperation,AfterOperation
from odoo.addons.ps_acc_center.acc_center_voucher_scheme.tools import generate_tools


# 明细行开始的行坐标
START_INDEX = 1
# 只有表头时，模型的数量
ONLY_HEADER_COUNT = 1
# 包含第三方模型时，模型的数量
INCLUDE_3RD_PARTY_COUNT = 3


class AccCenterTemplate(models.Model):
    _name = "acc.center.template"
    _description = "Voucher Scheme"  # 凭证方案


    ################################  default start  ################################

    ################################  default end    ################################


    ################################  字段定义区 start  ################################

    tenant_id = fields.Integer(string='Tenant', default=lambda self: self.env.user.tenant_id)  #租户
    number = fields.Char(string='Number', copy=False)  # 编号
    name = fields.Char(string='Name', translate=True)  # 名称

    acct_org_field_id = fields.Many2one('ir.model.fields', string='Account Organization')  # 核算组织字段
    acct_org_field_name = fields.Char(string='Account Organization Field Name', related='acct_org_field_id.name', store=True)  # 核算组织字段名称
    source_doc_id = fields.Many2one('ir.model', string='Source Document')  # 来源单据
    source_doc_model = fields.Char(string='Source Document Model', related='source_doc_id.model', store=True)  # 来源单据模型名称
    source_module_id = fields.Many2one('ir.module.module', string='Source Module', store=True, related='source_doc_id.ps_module_id')  # 来源单据模块
    source_domain_id = fields.Many2one('ps.ir.domain', string='Source Domain', store=True, related='source_doc_id.ps_module_id.ps_domain_id')  # 来源单据领域
    acct_table_id = fields.Many2one('mdm.account.table', string='Account Table')  # 科目表

    is_sys_date = fields.Boolean(string='Is Sys Date', default=False)  # 凭证日期是否取系统日期
    vou_date_field_id = fields.Many2one('ir.model.fields', string='Voucher Date')  # 凭证日期字段
    vou_date_field_name = fields.Char(string='Voucher Date Field Name', related='vou_date_field_id.name', store=True)  # 凭证日期字段名称
    is_combine = fields.Boolean(string='Is Combine', default=False)  # 分录合并
    is_fetch_other_model = fields.Boolean(string='Other Models Fetches', default=False)  # 从其他模型取数
    is_formula = fields.Boolean(string='Is Formula', default=False)  # 启用计算公式

    line_ids = fields.One2many('acc.center.template.line1' , 'parent_id', string='Voucher Scheme Line')  # 凭证方案明细
    forbid_state = fields.Selection([('normal', 'Normal'), ('forbid', 'Forbid')], string='Forbid State', default='forbid')  # 禁用状态(启用/禁用)
    delete_state = fields.Selection([('normal', 'Normal'), ('delete', 'Delete')], string='Delete State', default='normal')  # 删除状态(正常/删除)
    delete_uid = fields.Many2one('res.users', string='Delete User')  # 删除人
    delete_date = fields.Datetime(string='Delete Date') # 删除日期

    source_doc_rel = fields.Many2many('ir.model', string='Source Document Rel', store=False, deprecated=True)  # 来源单据字段模型，弃用
    acct_book_id = fields.Many2one('mdm.account.book', string='Account Book', deprecated=True)  # 适用账簿，弃用
    acct_org_id = fields.Many2one('sys.admin.orgs', string='Account organization', related='acct_book_id.accting_org_id', deprecated=True) # 账簿核算组织，弃用
    voucher_word_id = fields.Many2one('mdm.voucher.word', string='Voucher Word', store=True, deprecated=True)  # 凭证字，弃用
    is_book_vou_word = fields.Boolean(string='Is Book Voucher Word', default=True, deprecated=True)  # 是否取账簿凭证字，弃用
    act_window_id = fields.Many2one('ir.actions.act_window', string='Action Window', deprecated=True)  # 窗口动作，弃用

    ################################  字段定义区 end    ################################


    ################################  计算方法区 start  ################################

    ################################  计算方法区 end    ################################


    ################################  onchange方法区  start  ################################

    @api.onchange('source_doc_id', 'acct_table_id')
    def _onchange_acct_table_id(self):
        '''
        当科目表或来源单据发生变化的时候，清空明细
        '''
        self.line_ids = None
    
    @api.onchange('is_sys_date')
    def _onchange_is_sys_date(self):
        if not self.is_sys_date and self.source_doc_id:
            source_model = self.source_doc_id.model
            source_doc_obj = self.env[source_model]
            fields = source_doc_obj._fields
            field_obj = self.env['ir.model.fields']
            if 'biz_date' in fields:
                domain = [
                    ('model_id', '=', self.source_doc_id.id), 
                    # 改造更改处：已改
                    ('name', '=', 'biz_date'),
                    ('ttype', 'in', ('date', 'datetime'))
                ]
                self.vou_date_field_id = field_obj.search(domain, limit=1)
            else:
                self.vou_date_field_id = None
        else:
            self.vou_date_field_id = None
                
    @api.onchange('source_doc_id')
    def _onchange_source_doc_id(self):
        '''
        带出来源单据上主组织信息、凭证日期
        '''
        if self.source_doc_id:
            model_obj = self.env['ir.model']
            model = model_obj.browse(self.source_doc_id.id)
            org_id = model.orgs_config_ids.filtered(lambda x: x.is_main_org)
            self.acct_org_field_id = org_id.field_id.id
            source_doc_obj = self.env[model.model]
            fields = source_doc_obj._fields
            field_obj = self.env['ir.model.fields']
            if 'biz_date' in fields:
                domain = [
                    ('model_id', '=', self.source_doc_id.id), 
                    # 改造更改处：已改
                    ('name', '=', 'biz_date'),
                    ('ttype', 'in', ('date', 'datetime'))
                ]
                self.vou_date_field_id = field_obj.search(domain, limit=1) if not self.is_sys_date else None
            else:
                self.acct_org_field_id = None
        else:
            self.acct_org_field_id = None
            self.vou_date_field_id = None

    @api.onchange('line_ids')
    def _onchange_line_ids(self):
        """
        明细行更新，更新明细行sequence
        """
        for index, line in enumerate(self.line_ids, START_INDEX):
            line.sequence = index
    
    @api.onchange('is_fetch_other_model')
    def _onchange_is_fetch_other_model(self):
        """
        不勾选从其他模型取数清空时，将明细的获取其他模型配置清空
        """
        if not self.is_fetch_other_model:
            for line in self.line_ids:
                line.fetch_id = None

    @api.onchange('is_formula')
    def _onchange_is_formula(self):
        """
        是否启用公式，启用公式则清空金额模型字段列，否则清空金额公式列
        """
        if self.is_formula:
            for line in self.line_ids:
                line.amount_field_id = None
                line.standard_amount_field_id = None
        else:
            for line in self.line_ids:
                line.amount_model_id = None
                line.amount_formula = None
                line.amount_local_formula = None

    ################################  onchange方法区  end    ################################


    ################################  约束方法区  start  ################################

    @api.constrains('name', 'line_ids')
    def _check_line_ids(self):
        """
        1.校验明细行是否录入
        2.判断原币和本位币的模型是否一样
        3.判断辅助核算和本位币的模型关系
        """
        for rec in self:
            if not rec.line_ids:
                # 请录入凭证方案明细行
                raise ValidationError(_('Please enter the details line of the voucher scheme'))

            source_doc_model = rec.source_doc_model # 表头模型
            is_formula = rec.is_formula
            for index, line in enumerate(rec.line_ids, START_INDEX):
                # 校验金额配置
                self._check_amount_setting(is_formula, line, index)

                # 计算币别/汇率/核算维度的模型范围：
                # 1. 金额字段是三方表中数据，币别/汇率/核算维度可以取表头、表体、三方表
                # 2. 金额字段是表体中数据，币别/汇率/核算维度可以取表头、表体
                # 3. 金额字段是表头中数据，币别/汇率/核算维度可以取表头
                amount_model = line.amount_model
                models = {source_doc_model, amount_model}
                if rec.is_fetch_other_model and amount_model == line.fetch_id.rel_model:
                    models.add(line.fetch_id.entry_model)
                # 校验币别/汇率字段配置合法性
                self._check_currency_setting(models, line, index)
                # 校验辅助核算配置合法性
                self._check_account_setting(models, line, index)

    ################################  约束方法区  end    ################################


    ################################  服务器动作区  start  ################################

    @sys_ele_ctrl()
    def svc_run_enable(self):
        """
        修改状态 forbid --> normal
        """
        lines_info = []  # 提示信息列表
        opt = _('Enable: %s')  # 启用: %s
        for rec in self:
            if rec.delete_state != 'normal':
                # 当前凭证方案已经被删除
                lines_info.append(LineInfo(operation=opt % rec.name, state=FAILED_STATE, info=_('The current voucher scheme has been deleted')))
            elif rec.forbid_state == 'normal':
                # 当前凭证方案已经被启用
                lines_info.append(LineInfo(operation=opt % rec.name, state=FAILED_STATE, info=_('The current voucher scheme has been enabled')))
            else:            
                # 同一来源单据、科目表下只能有一个方案是启用状态
                templates = self.search([
                    ('source_doc_id', '=', rec.source_doc_id.id), 
                    ('acct_table_id', '=', rec.acct_table_id.id),
                    ('forbid_state', '=', 'normal'),
                    ('delete_state', '=', 'normal')], limit=1)
                if templates:
                    # 在同一科目表、来源单据下只能启用一个方案
                    info = _('Only one template can be enabled under the same account table and source document')
                    lines_info.append(LineInfo(operation=opt % rec.name, state=FAILED_STATE, info=info))
                else:
                    # 需要先更改状态，创建base_automation时会处理事务、刷新registry，导致修改状态失败
                    rec.write({'forbid_state': 'normal'})
                    # 单据删除时，删除关联数据
                    self._auto_unlink(rec.source_doc_id.model)
                    lines_info.append(LineInfo(operation=opt % rec.name, state=SUCCESS_STATE, info=_('Successfully enable'))) # 启用成功
            
        return InfoWindow.info(lines_info)
    
    @sys_ele_ctrl()
    def svc_run_forbid(self):
        """
        修改状态 start --> forbid
        """
        lines_info = []  # 提示信息列表
        opt = _('Forbid: %s') # 禁用: %s
        for rec in self:
            if rec.delete_state != 'normal':
                # 当前凭证方案已经被删除
                lines_info.append(LineInfo(operation=opt % rec.name, state=FAILED_STATE, info=_('The current voucher scheme has been deleted')))
            elif rec.forbid_state == 'forbid':
                # 当前凭证方案已经被禁用
                lines_info.append(LineInfo(operation=opt % rec.name, state=FAILED_STATE, info=_('The current voucher scheme has been disabled')))
            else:
                generation_line_obj = self.env['acc.center.voucher.generation.line1']
                refs = generation_line_obj.search([('template_id', '=', rec.id)])
                if refs:
                    books = '、'.join(refs.parent_id.acct_book_id.mapped('name'))
                    # 方案已被凭证工厂下的账簿 %s 选用，请去掉选用关系后禁用
                    info = _('The scheme has been selected by account books %s under Voucher Factory, ' 
                        + 'please disable it after removing the selection relationship') % books
                    lines_info.append(LineInfo(operation=opt % rec.name, state=FAILED_STATE, info=info))
                else:
                    rec.write({'forbid_state': 'forbid'})
                    # 禁用成功
                    lines_info.append(LineInfo(operation=opt % rec.name, state=SUCCESS_STATE, info=_('Successfully forbid')))
            
        return InfoWindow.info(lines_info)

    @sys_ele_ctrl()
    def svc_run_delete(self):
        """
        删除（逻辑删除）动作
        """
        if not self._context.get('confirm_delete'):
            names = [rec.name for rec in self]
            return InfoWindow.delete_confirm(names, self.ids, self._name, 'svc_run_delete')
        
        lines_info = []
        to_delete = self.browse()
        opt = _('Delete: %s') # 删除
        for rec in self:
            if rec.forbid_state == 'normal':
                # 该方案未禁用，请禁用方案后删除
                info = _('The scheme is not disabled, please delete it after disabling the program')
                lines_info.append(LineInfo(operation=opt % rec.name, state=FAILED_STATE, info=info))
            else:
                to_delete += rec
                # 删除成功
                lines_info.append(LineInfo(operation=opt % rec.name, state=SUCCESS_STATE, info=_('Successfully delete')))
        
        # 更新删除状态
        to_delete.write({
            'delete_state': 'delete',
            'delete_uid': self.env.user.id,
            'delete_date': fields.Datetime.now()
        })
        # 删除模板的时候，将模板对应的科目设置、科目设置明细行、科目核算维度状态置为删除状态
        # 获取待删除单据模板明细行的全部科目设置，去掉在其他单据模板中被用到的科目设置，就是需要删除掉的科目设置
        account_settings = to_delete.line_ids.account_setting_id
        template_line_obj = self.env['acc.center.template.line1']
        protected_account_settings = template_line_obj.search([
            ('account_setting_id', 'in', account_settings.ids),
            ('delete_state', '=', 'normal')]).account_setting_id
        account_settings -= protected_account_settings
        account_settings.write({'delete_state': 'delete'})
        return InfoWindow.info(lines_info)
    
    @sys_ele_ctrl()
    def svc_generate_template_file(self):
        """
        生成模板文件
        """
        self.env = self.env(context=dict(self.env.context, lang='en_US'))
        export_obj = self.env['acc.center.template.data.export.wizard']
        data = export_obj.sudo().create({
            'name': 'ps_acc_center_data.xml',
            'data': base64.encodebytes(generate_tools.generate(self)),
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'acc.center.template.data.export.wizard',
            'view_mode': 'form',
            'res_id': data.id,
            'views': [(False, 'form')],
            'target': 'new',
        }
    
    ################################  服务器动作区  end    ################################


    ################################  按钮动作区  start  ################################

    ################################  按钮动作区  end    ################################


    ################################  私有方法区  start  ################################
        
    @sys_ele_ctrl()
    def _auto_unlink(self, model):
        """
        创建自动动作，删除单据关联关系表中的数据
        之前是监控unlink函数，但是目前单据上使用的删除函数为自定义函数，尝试在base_automation增加一个新的trigger监控新的删除函数，
        但是在单据上的删除函数会调用另一个弹窗，用于确定删除，该弹窗调用另一个模型中的delete_confirm函数,如果监控delete_confirm函数，则无法确定是那个单据调用的删除，所以无法控制，
        最终修改为监控单据上的delete_state字段，如果该字段进行了修改，并且修改为delete那么则说明单据已经删除，执行自动化动作删除流单据关联关系数据。
        """
        name = model + ' document association relationship table logic deleted' # 单据关联关系表逻辑删除
        automation_obj = self.env['base.automation']
        domain = [
            ('model_id.model', '=', model), 
            ('name', '=', name), 
            ('trigger', '=', 'on_write'), 
            ('state', '=', 'code')
        ]
        automations = automation_obj.search(domain, limit=1)  # 自动删除动作
        field_obj = self.env['ir.model.fields']
        trigger_field_id = field_obj.search([('model', '=', model), ('name', '=', 'delete_state')], limit=1).ids  # 需要监控的单据字段delete_state
        # 如果已存在自动动作或者在单据上没有delete_state字段，则不创建自动动作
        if not automations and trigger_field_id:
            model_obj = self.env['ir.model']
            automation_obj.create({
                'name': name,
                'model_id': model_obj.search([('model', '=', model)]).id,
                'state': 'code',
                'trigger': 'on_write',
                'trigger_field_ids': [(6, 0, trigger_field_id)],
                'code': "env['acc.center.template']._unlink_process_instance(records)"
            })

    def _unlink_process_instance(self, records):
        """
        当删除单据时，也要删除流程实例表中的数据
        """
        if records:
            # 保险起见，只处理会计中心生成的数据
            relations = self.env['studio.botp.record'].search([
                ('record_type', '=', 'acct_center'),
                ('source_model_key', '=', records._name), 
                ('source_doc_id', 'in', records.ids), 
                ('delete_state', '=', False)])
            if relations:
                relations.write({'delete_state': True})  # 逻辑删除

    def _check_amount_setting(self, is_formula, line, index):
        """
        校验金额配置
        @param is_formula: 是否启用计算公式
        @param line: 凭证方案明细对象
        @param index: 行号
        """
        if is_formula:
            if not line.amount_model:
                # 请选择金额取数模型
                raise ValidationError(_('Please select the amount model'))
            fields = self.env[line.amount_model]._fields
            # 金额公式/本位币金额公式
            formula_engine_obj = self.env['ps.formula.engine']
            formula_fields = [('amount_formula', _('amount formula')), ('amount_local_formula', _('amount local formula'))]
            for formula_field, info in formula_fields:
                field_names = formula_engine_obj.p_get_all_fields(line[formula_field])
                for field_name in field_names:
                    if field_name not in fields or fields[field_name].type not in ('float', 'integer'):
                        # 第%s行%s存在非法内容，请检查：<br/>
                        # 1、公式中字段不存在<br/>2、表头取数模式配置表体字段<br/>3、公式中字段非数值类型
                        raise ValidationError(_('There is illegal content in the %(info)s in line %(index)s. Please check:<br/>' 
                            + '1. The formula in the field does not exist<br/>' 
                            + '2. The table header takes the number of mode configuration table body fields<br/>' 
                            + '3. The formula in the field is not a numerical type') % {'info': info, 'index': index})
        else:
            if line.amount_field_id.model != line.standard_amount_field_id.model:
                # 第%s行设置的原币金额字段和本位币金额字段需为同一模型的字段
                raise ValidationError(_('The amount field and amount local field setting in line %s shall be fields of the same model') % index)
    
    def _check_currency_setting(self, models, line, index):
        """
        校验币别/汇率字段配置合法性
        @param models: 模型的过滤集合
        @param line: 凭证方案明细对象
        @param index: 行号
        """
        if line.curr_field_model not in models:
            location = ''
            # 表头或金额字段所在表体
            location = _('source document or source document entry of the amount field')
            if len(models) == ONLY_HEADER_COUNT:
                # 表头
                location = _('source document')
            elif len(models) == INCLUDE_3RD_PARTY_COUNT:
                # 表头/表体或金额字段所在第三方模型
                location = _('source document/source document entry or third-party model of the amount field')
            # 第%s行分录设置的币别字段必须在%s
            raise ValidationError(_('The currency field in line %s must be a field in the %s model') % (index, location))
        if line.curr_rate_field_id.model and line.curr_field_id.model != line.curr_rate_field_id.model:
            # 第%s行设置的币别字段和汇率字段需为同一模型的字段
            raise ValidationError(_('The currency field and exchange rate field setting in line %s shall be fields of the same model') % index)
    
    def _check_account_setting(self, models, line, index):
        """
        校验辅助核算配置合法性
        @param models: 模型的过滤集合
        @param line: 凭证方案明细对象
        @param index: 行号
        """
        for acct_set_line in line.account_setting_id.line_ids:
            account_name = acct_set_line.account_id.name
            for auxiliary_set in acct_set_line.auxiliary_set_ids:
                if auxiliary_set.method == 'source_field' and auxiliary_set.source_field_model not in models:
                    # 第%s行分录设置的金额字段与%s科目设置核算维度字段无法匹配，请调整为以下3种模式之一:<br/>
                    # 1. 金额字段、核算维度字段均为表头字段<br/>
                    # 2. 金额字段为表体字段时，核算维度可设置表头、表体字段<br/>
                    # 3. 如果启用其他模型取数且本位币为第三方模型字段时，核算维度可设置表头、表体及第三方模型字段
                    raise ValidationError(_('The amount field setting in in line %s cannot match the account dimension field ' 
                        + 'in %s account setting. Please adjust to one of the following three modes:<br/>'
                        + '1. Amount field and account dimension field are all source document fields<br/>'
                        + '2. When the amount field is the source document entry field, the account dimension can be source document/source document entry fields<br/>' 
                        + '3. If other model fetches are enabled and the amount field is a third-party model field, ' 
                        + 'the account dimension can set the source document/source document entry/third-party model fields') % (index, account_name))
        
    ################################  私有方法区  end    ################################


    ################################  公共方法区  start  ################################
    
    ################################  公共方法区  end    ################################


    ################################  覆盖基类方法区  start  ################################

    @sys_ele_ctrl()
    @api.model
    def pre_create(self):
        res = super(AccCenterTemplate, self).pre_create()
        return res

    @api.model
    def create(self, vals):
        if (isinstance(vals,list) and 'number' in vals[0] and vals[0]['number']) or \
            (isinstance(vals,dict) and 'number' in vals and vals['number']):
            self = self.with_context(manual_input_number=True)
        # create
        res = super(AccCenterTemplate, self).create(vals)
        # after
        self.after_create(res)
        return res
    
    @sys_ele_ctrl()
    def after_create(self, res):
        number = res.number
        code_rule_obj = self.env['ps.code.rule']
        if not number:
            res.number = code_rule_obj.p_create_next_code_rule(model_name=self._name, values=res)
        # 如果存在编码，去尝试更新编码规则表中的最大编码
        elif self.env.context.get('manual_input_number'):
            self = self.with_context(manual_input_number=False)
            code_rule_obj.p_modify_max_number(res.number, model_name=self._name, values=res)

    @sys_ele_ctrl()
    @api.model
    def pre_write(self,res):
        return super(AccCenterTemplate, self).pre_write(res)
    
    def write(self, vals):
        # before
        self.before_write(vals)
        # write
        res = super(AccCenterTemplate, self).write(vals)
        return res

    @sys_ele_ctrl()
    @api.model
    def before_write(self, values):
        '''
        清空凭证日期和凭证字
        '''
        if 'is_sys_date' in values:
            if values['is_sys_date']:
                values['vou_date_field_id'] = None
    
    @sys_ele_ctrl()
    def read(self, fields=None, load='_classic_read'):
        return super(AccCenterTemplate, self).read(fields, load)

    ################################  覆盖基类方法区  end    ################################


    ################################  其他方法区  start  ################################
    
    ################################  其他方法区  end    ################################
