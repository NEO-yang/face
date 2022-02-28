# -*- coding: utf-8 -*-
'''
==================================================
@创建人 ：王琨鹏
@当前维护人 ：王琨鹏
@Desc ：单据类型参数配置向导
==================================================
'''
import datetime
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

from odoo.addons.ps_admin.sys_ele.sys_ele_ctrl import sys_ele_ctrl
from odoo.addons.ps_admin.biz_log.models.biz_log_item import BizLogItem, LogCategory, LogLevel
from odoo.addons.ps_admin.info_window.info_window import InfoWindow, LineInfo, SUCCESS_STATE


class MdmDocConfigSettings(models.TransientModel):
    _name = 'mdm.doc.config.settings'
    _inherit = 'config.settings.base'
    _description = 'Mdm Document Config Settings'  # 单据参数配置向导

    ################################  default start  ################################

    def _default_biz_type_id(self):
        """
        获取默认业务类型
        """
        biz_type_id = self.env.context.get('biz_type_id', False)
        return biz_type_id

    def _default_corespond_doc_id(self):
        """
        获取默认单据
        """
        corespond_doc_id = self.env.context.get('corespond_doc_id', False)
        return corespond_doc_id

    def _default_document_type_id(self):
        """
        获取默认单据
        """
        document_type_id = self.env.context.get('document_type_id', False)
        return document_type_id
        
    def _default_state(self):
        """
        获取默认单据状态
        """
        state = self.env.context.get('config_state', False)
        return state

    ################################  default end    ################################

    ################################  字段定义区 start  ################################

    corespond_doc_id = fields.Many2one(
        'mdm.document.list', string='Document List', default=_default_corespond_doc_id)  # 对应单据
    params_visible_mark = fields.Char(
        string='Visible Mark', compute="_get_visible_mark", store=True)  # 对应单据
    # TODO: 两个调拨, 需要确认保留哪一个
    add_option = fields.Selection(related='corespond_doc_id.add_option', readonly=True, store=True)
    document_type_id = fields.Many2one('mdm.document.type',string='Document Type', default=_default_document_type_id)  # 单据类型
    business_type = fields.Selection([('standard_pur','Standard Purchase'),
                ('standard_sal','Standard Sale'),
                ('standard_trans','Standard Transfer'),
                ('standard_stock_miscellaneous_in','Standard Stock Miscellaneous In'),
                ('standard_stock_miscellaneous_out','Standard Stock Miscellaneous Out'),
                ('standard_stock_direct_transfer','Standard Stock Direct Transfer'),
                ('standard_stock_init','Standard Stock Init')], string='Business Type')  # 业务类型（标准采购/标准销售/标准调拨/标准其他入库/标准其他出库/标准销售退库/标准直接调拨/标准库存初始）
    biz_type_id = fields.Many2one('mdm.business.type', string='Business Type', default=_default_biz_type_id) # 业务类型（many2one）
    is_delivery_ref = fields.Boolean(
        string='Execute delivery details with reference', default=False)  # 参考交货明细执行
    is_can_edit_quant = fields.Boolean(
        string='Allow to modify delivery quantity', default=False)  # 允许修改交货数量
    is_can_edit_time = fields.Boolean(
        string='Allow to modify time control', default=False)  # 允许修改时间控制
    is_rel_generate = fields.Boolean(
        string='Related generated', default=False)  # 关联生成
    is_add_entry = fields.Boolean(
        string='Allow to add entries after related generated', default=False)  # 是否允许关联生成后手工添加分录
    auth_warehouse_status_ids = fields.Many2many(comodel_name='mdm.stock.state', readonly=False, 
        required=False, store=True, string='Authorized Warehouse State', translate=True)  # 授权仓库状态
    state = fields.Selection([('creating','Creat'),('temporary','Temporary'),('save','Save'),('submit','Submit'),('audit','Audit')], string='Data Status', default=_default_state)
    # ----------------------- 委外订单字段 -----------------------
    is_sub_order_auto_dispatch = fields.Boolean(
        string='Subcontract Order is automatically dispatch when it is approved', default=False)  # 委外订单审核时自动下达
    is_sub_order_auto_close = fields.Boolean(
        string='Subcontract Order Auto Close', default=False)  # 委外订单自动关闭
    backflush_type = fields.Selection([
                ('back_backflush','Backstage Backflush'),
                ('interactive_backflush','Interactive backflush')], default="back_backflush", string='Backflush Type')  # 倒冲方式（后台倒冲/交互式倒冲）
    ctrl_type = fields.Selection([
            ("no_ctrl","No Control"),  # 不控制
            ("warning","Warning"),  # 警告
            ('strict_ctrl',"Strict Control")  # 严格控制
        ], default="no_ctrl", string="Control Type")  # 控制类型
    # ----------------------- 委外订单字段 -----------------------
    # ----------------------- 计划订单字段 -----------------------
    planning_strategy = fields.Selection([('mrp','MRP'),('mps','MPS')], string='Planning Strategy', default='mrp')  # 计划策略
    # ----------------------- 计划订单字段 -----------------------
    # ----------------------- 生产订单字段 -----------------------
    backflush_time_point = fields.Selection([('instock_backflush','Instock Backflush'),('report_backflush','Report Backflush')], string='Backflush Time Point', default='instock_backflush')
    backflush_mode = fields.Selection([('backstage_backflush','Backstage Backflush'),('interactive_backflush','Interactive Backflush')], string='Backflush Mode', default='backstage_backflush')
    # ----------------------- 生产订单字段 -----------------------

    # ----------------------- 费用报销字段 -----------------------
    # 是否项目管控
    is_project_ctrl = fields.Boolean(string='Project Contorl', default=False)
    # 是否事前申请管控
    is_request_ctrl = fields.Boolean(string='Request Contorl', default=False)  
    # 费用项目范围
    reimb_item_option = fields.Selection([('all', 'All'), ('include', 'Include'), ('exclude', 'Exclude')], string='Reimb Item Option', default='all')  
    # 费用项目
    exp_item_ids = fields.Many2many(comodel_name='mdm.expense.item', readonly=False, 
        required=False, store=True, string='Expense Items') 
    # ----------------------- 费用报销字段 -----------------------
    
    ################################  字段定义区 end    ################################

    ################################  计算方法区 start  ################################
    @api.depends('corespond_doc_id', 'biz_type_id')
    def _get_visible_mark(self):
        for line in self:
            model_data = self.env['ir.model.data'].search(
                [('res_id', '=', line.corespond_doc_id.id), ('model', '=', 'mdm.document.list')], limit=1)
            line.params_visible_mark = model_data.complete_name if len(
                model_data) == 1 else ''

    ################################  计算方法区 end    ################################

    ################################  onchange方法区  start  ################################

    ################################  onchange方法区  end    ################################

    ################################  约束方法区  start  ################################

    ################################  约束方法区  end    ################################

    ################################  服务器动作区  start  ################################

    ################################  服务器动作区  end    ################################

    ################################  按钮动作区  start  ################################
    @sys_ele_ctrl()
    def save_doc_params(self):
        """
        点击保存按钮，向后台表写入参数值
        并重载视图
        :param:
            self: 当前模型对象(obj)
        :return:
        """
        corespond_doc_id = self.env.context.get('corespond_doc_id', False)
        biz_type_id = self.env.context.get('biz_type_id', False)
        document_type_id = self.env.context.get('document_type_id', False)
        self._set_doc_params(corespond_doc_id, biz_type_id, document_type_id)
        self.biz_logs.append(BizLogItem(cls=self, operation=_('Save'), message=_('Save success.'), level=LogLevel.INFO, category=LogCategory.OPERATE))
        #  TODO 不返回任何视图，直接关闭当前页面，暂时先注释掉 
        # return_view = self._get_return_view() or {
        #     'type': 'ir.actions.client',
        #     'tag': 'reload',
        # }
        line_info = LineInfo(operation=_('Save'), state=SUCCESS_STATE, info=_('Save success.'))
        return InfoWindow.info([line_info])

    ################################  按钮动作区  end    ################################

    ################################  私有方法区  start  ################################

    def _get_field_value(self, param_result):
        """
        返回字段的值
        :param:
            param_result: 参数键值对
        :return: field_value
        """
        field_type = param_result.get('data_type', '')
        field_value = param_result.get('value')
        field_key = param_result.get('key')
        if field_type == 'Boolean':
            if field_value == 'True':
                field_value = True
            elif field_value == 'False':
                field_value = False
        if field_type == 'Float':
            field_value = float(field_value)
        if field_type in ['Integer', 'Many2one']:
            field_value = int(field_value)
        if field_type == 'Date':
            field_value = datetime.datetime.strptime(
                field_value, '%Y-%m-%d').date()
        if field_type == 'Datetime':
            field_value = datetime.datetime.strptime(
                field_value, '%Y-%m-%d %H:%M:%S')
        if field_type == 'Many2many':
            # 将 str 重新转换为 int, 并为 many2many 字段赋值
            field_value = field_value.split('~')
            if field_key == 'exp_item_ids':
                field_num = [val for val in field_value if len(val)]
                item_obj = self.env['mdm.expense.item']
                field_value = item_obj.search([('number', 'in', field_num)]).ids
            else:
                field_value = [int(val) for val in field_value if len(val)]

        return field_value

    def _get_fields_dict(self):
        if self.env['ir.module.module'].search_count([('name', '=', 'ps_sub'), ('state', '=', 'installed')]) \
            and self._context.get('corespond_doc_id',False) == self.env.ref('ps_sub.mdm_document_list_sub_order_data').id:
            return {
                # 委外订单参数
                'is_sub_order_auto_dispatch': False,
                'is_sub_order_auto_close': False,
                'backflush_type': 'back_backflush',
                'ctrl_type': 'no_ctrl',
            }
        elif self.env['ir.module.module'].search_count([('name', '=', 'ps_plan_manager'), ('state', '=', 'installed')]) \
            and self._context.get('corespond_doc_id',False) == self.env.ref('ps_plan_manager.mdm_document_list_plan_order_data').id:
            return {
                # 计划订单参数
                'planning_strategy':self.planning_strategy
            }
        elif self.env['ir.module.module'].search_count([('name', '=', 'ps_product_manager'), ('state', '=', 'installed')]) \
            and self._context.get('corespond_doc_id',False) == self.env.ref('ps_product_manager.product_document_list_data1').id:
            return {
                # 生产订单参数
                'backflush_time_point': 'instock_backflush',
                'backflush_mode': 'backstage_backflush',
            }
        # TODO：ref后的ID需要根据单据类型列表对应的值进行调整
        elif self.env['ir.module.module'].search_count([('name', '=', 'ps_amb'), ('state', '=', 'installed')]) \
            and self._context.get('corespond_doc_id',False) == self.env.ref('ps_amb.mdm_document_list_amb_expense_reimb').id:
            return {
                # 费用报销单参数
                'is_request_ctrl': False,
                'is_project_ctrl': False,
                'reimb_item_option': False,
                'exp_item_ids': False,
            }           
        else:
            return {
                # 采购订单参数
                'is_delivery_ref': False,
                'is_can_edit_quant': False,
                'is_can_edit_time': False,
                'is_rel_generate': False,
                'is_add_entry': False,
                'auth_warehouse_status_ids': False,
            }

    def _get_data_type(self):
        """
        返回字段的类型
        :param:
            field: field 对象
        :return: fields_type --> char
        """
        return {'boolean': 'Boolean', 'integer': 'Integer', 'float': 'Float', 'char': 'Char', 'date': 'Date',
                'datetime': 'Datetime', 'many2one': 'Many2one', 'selection': 'Selection', 'many2many': 'Many2many'}

    def _set_doc_params(self, corespond_doc_id, biz_type_id, document_type_id):
        value_list = []
        rec_num = []
        fields_dict = self._get_fields_dict()
        fields_list = fields_dict.keys()
        data_type = self._get_data_type()
        if not set(fields_list).issubset(self._fields.keys()):
            raise ValidationError(_("Illegal parameter"))
        for name in fields_list:
            field = self._fields[name]
            value = str(self[name])
            value_info = {'key': name, 'value': value,
                          'data_type': data_type[field.type], 'relation_model': '', 'biz_type_id': biz_type_id}
            if field.type == 'many2one':
                value_info.update({'relation_model': field.comodel_name})
                value_info.update({'value': str(self[name].id)})
            if field.type == 'many2many':
                value_info.update({'relation_model': field.comodel_name})
                if name == 'exp_item_ids':
                    item_obj = self.env['mdm.expense.item']
                    item_ids = item_obj.browse(self[name].ids)
                    for rec in item_ids:
                        rec_num.append(rec.number)
                    rec_ids = rec_num
                else:
                    rec_ids = [str(rec) for rec in self[name].ids]
                # rec_value 值范例 "1_2", 为 id 值转化为 str 时的拼接
                rec_value = "~".join(rec_ids)
                value_info.update({'value': rec_value})
            value_list.append(value_info)
        self.env['mdm.document.params'].p_set_params(document_type_id=document_type_id,
            corespond_doc_id=corespond_doc_id, biz_type_id=biz_type_id, value_list=value_list)

    def _get_return_view(self):
        """
        返回跳转视图
        :param:
            self: 当前模型对象(obj)
        :return: dict
        """
        view_id = self.env.ref('ps_mdm.mdm_document_type_form').id
        return {
                'type': 'ir.actions.act_window',
                'res_model': self.document_type_id._name,
                'view_mode': 'form',
                'target': 'main',
                'res_id': self.document_type_id.id,
                'views': [(view_id, 'form')],
            }

    ################################  私有方法区  end    ################################

    ################################  公共方法区  start  ################################

    ################################  公共方法区  end    ################################

    ################################  覆盖基类方法区  start  ################################

    @api.model
    def default_get(self, fields_list):
        """
        重写 default_get 方法
        :param:
            self: 当前模型对象（obj）
        :return: 
            defaults: 返回需要展示的数据（list）——这里的数据未被存储
        """
        result = {}
        defaults = super(MdmDocConfigSettings, self).default_get(fields_list)
        biz_type_id = self.env.context.get('biz_type_id', False)
        corespond_doc_id = self.env.context.get('corespond_doc_id', False)
        document_type_id = self.env.context.get('document_type_id', False)
        fields_dict = self._get_fields_dict()
        fields_list = fields_dict.keys()
        doc_params = self.env['mdm.document.params'].p_get_params(document_type_id=document_type_id,
            corespond_doc_id=corespond_doc_id, biz_type_id=biz_type_id, key=fields_list)
        for param in doc_params:
            field_name = param.get('key', False)
            if not field_name:
                continue
            field_value = self._get_field_value(param)
            result[field_name] = field_value
        defaults.update(result)
        return defaults

    ################################  覆盖基类方法区  end    ################################
