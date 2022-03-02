# -*- coding: utf-8 -*-

'''
==================================================
@创建人 ：马新成
@当前维护人 ：马新成
@Desc ：业务单据对账方案设置
==================================================
'''
import base64
from odoo import tools, api, fields, models, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.addons.ps_admin.sys_ele.sys_ele_ctrl import sys_ele_ctrl
from odoo.addons.ps_acc_center.tools import generate_tools_1

class AccCenterReconciliationScheme(models.Model):
    _inherit = 'acc.center.reconciliation.scheme'
    _rec_name = 'name'
    _order = 'number'

    ################################  default start  ################################

    def _default_org_id(self):
        """
        获取默认组织
        :param:
            self: 当前模型对象(obj)
        :return: 
            org_id: 组织对象(obj)
        """
        org_id = self.env.user.ps_curr_org_id
        domain = self.env['sys.admin.orgs'].p_get_main_org_domain(self._name)
        if domain:
            # p_get_main_org_domain 返回doamin可能为False
            access_org = self.env['sys.admin.orgs'].search(domain)
            if len(org_id) == 1 and org_id.account_organization != "empty" and org_id.state == "audit" and org_id.id in access_org.ids:
                return org_id

    ################################  default end    ################################

    ################################  字段定义区 start  ################################

    acct_book_id = fields.Many2one(
        domain="[('accting_org_id', '=', acct_org_id), ('init_state', '=', 'finish'), ('forbid_state', '=', 'normal')]")
    acct_org_id = fields.Many2one(default=lambda self: self._default_org_id())
    acct_org_id_domains = fields.Many2many(compute="_compute_acct_org_domains")

    ################################  字段定义区 end    ################################

    ################################  计算方法区 start  ################################

    @api.depends("acct_org_id")
    def _compute_acct_org_domains(self):
        domain = self.env['sys.admin.orgs'].p_get_main_org_domain(self._name)
        if domain:
            domain.append(('account_organization', '!=', 'empty'))
        for res in self:
            res.acct_org_id_domains = [(6, 0, self.env['sys.admin.orgs'].search(domain).ids if domain else [])]

    ################################  计算方法区 end    ################################

    ################################  onchange方法区  start  ################################

    @api.onchange("acct_book_id")
    def _onchange_acct_book_id(self):
        """
        账簿更换，清空明细
        """
        for res in self:
            res.line1_ids = None

    @api.onchange("acct_org_id")
    def _onchange_acct_org_id(self):
        """
        核算组织更换，清空明细
        """
        self.line1_ids = None
        self.acct_book_id = None
        if self.acct_org_id:
            domain = [('accting_org_id', '=', self.acct_org_id.id),
                      ('init_state', '=', 'finish'),
                      ('book_type', '=', 'main'),
                      ('forbid_state', '=', 'normal')]
            books = self.env['mdm.account.book'].search(domain)
            # 按常理来讲一个组织只有一个主账簿, 保险起见, 使用books[0]
            self.acct_book_id = books[0].id if books else None

    @api.onchange('line1_ids')
    def _onchange_line1_ids(self):
        """
        生成行号sequence
        """
        for index, line in enumerate(self.line1_ids):
            line.sequence = index + 1

    ################################  onchange方法区  end    ################################

    ################################  约束方法区  start  ################################

    @api.constrains('line1_ids','line1_ids.biz_line_ids')
    def _check_account_id_dimension_id(self):
        res_set = set()
        for line in self.line1_ids:
            if res_set.issuperset({str(line.account_id.id) + '_' + str(line.dimension_id.id)}):
                raise ValidationError(
                    _('The accounting dimension corresponding to the reconciliation account %s: %s is duplicate, please modify') % (line.account_id.number, line.account_id.name))  # 对账科目s% 对应的核算维度重复, 请修改
        
            res_set.add(str(line.account_id.id) + '_' + str(line.dimension_id.id))
            if line.gl_increase_field_id == line.gl_decrease_field_id:
                raise ValidationError(
                    _('The addition and decrease items of general ledger retrieval cannot be the same field, please modify'))  # 总账取数的增加项与减少项不能为同一字段，请修改
            for line1 in line.biz_line_ids:
                if line.dimension_model_name != line1.d_corr_filed_model_id.model:
                    raise ValidationError(
                        _('The auxiliary is inconsistent with the document field, unable to reconcile, please modify'))  # 对账科目核算维度与单据字段对应资料不一致，无法对账，请修改

        # 校验对账单据设置子表（Line2）中的是否存在完全重复的明细行
        for line1 in self.line1_ids:  
            field_value_key_list = []
            for line2 in line1.biz_line_ids:
                field_value_list = []
                field_value_list.append(str(line2.parent_id.id if line2.parent_id else 0))
                field_value_list.append(str(line2.account_id.id if line2.account_id else 0))
                field_value_list.append(str(line2.condition_id.id if line2.condition_id else 0))
                field_value_list.append(str(line2.curr_field_id.id if line2.curr_field_id else 0))
                field_value_list.append(str(line2.d_corr_doc_field_id.id if line2.d_corr_doc_field_id else 0))
                field_value_list.append(str(line2.d_corr_filed_model_id.id if line2.d_corr_filed_model_id else 0))
                field_value_list.append(str(line2.doc_date_field_id.id if line2.doc_date_field_id else 0))
                field_value_list.append(str(line2.doc_field_id.id if line2.doc_field_id else 0))
                field_value_list.append(str(line2.doc_filed_model_id.id if line2.doc_filed_model_id else 0))
                field_value_list.append(str(line2.sett_org_field_id.id if line2.sett_org_field_id else 0))
                field_value_list.append(str(line2.model_id.id if line2.model_id else 0))
                field_value_list.append(str(line2.dimension_id.id if line2.dimension_id else 0))
                field_value_list.append(line2.biz_data_type if line2.biz_data_type else '')
                field_value_list.append(line2.curr_field_model if line2.curr_field_model else '')
                field_value_list.append(line2.curr_field_name if line2.curr_field_name else '')
                field_value_list.append(line2.description if line2.description else '')
                field_value_list.append(line2.sett_org_field_model if line2.sett_org_field_model else '')
                field_value_list.append(line2.sett_org_field_name if line2.sett_org_field_name else '')
                field_value_key_list.append('_'.join(field_value_list))
            if len(set(field_value_key_list)) != len(line1.biz_line_ids):
                # 业务单据设置存在重复数据，请修改
                raise ValidationError(_('Duplicate data exists in business document reconciliation settings, please modify'))

    @api.constrains("name")
    def _check_scheme_name(self):
        name_list = [x.name for x in self.env["acc.center.reconciliation.scheme"].search([('acct_book_id','=',self.acct_book_id.id)])]            
        if len(name_list) > len(set(name_list)):
            raise ValidationError(_('Scheme name must be only one'))  # 方案名称必须唯一

    ################################  约束方法区  end    ################################

    ################################  服务器动作区  start  ################################
    @sys_ele_ctrl()
    def svc_generate_template_file(self):
        """
        生成模板文件
        """
        self.env = self.env(context=dict(self.env.context, lang='en_US'))
        data = self.env['acc.center.template.data.export.wizard'].sudo().create({
            'name': 'ps_acc_center_reconciliation_data.xml',
            'data': base64.encodebytes(generate_tools_1.generate(self)),
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

    def _create_sequence(self):
        """
        sequence自动生成
        """
        for index, line in enumerate(self.line1_ids):
            line.sequence = index + 1

    ################################  私有方法区  end    ################################

    ################################  公共方法区  start  ################################

    ################################  公共方法区  end    ################################

    ################################  覆盖基类方法区  start  ################################

    @sys_ele_ctrl()
    def after_create(self, res):
        """
        子表生成行号
        """
        # 更新明细行sequence
        for rec in res:
            rec._create_sequence()
        return super(AccCenterReconciliationScheme, self).after_create(res)

    @sys_ele_ctrl()
    def after_write(self, vals):
        """
        子表生成行号
        """
        for rec in self:
            # 更新明细行sequence
            rec._create_sequence()
        return super(AccCenterReconciliationScheme, self).after_write(vals)
    
    ################################  覆盖基类方法区  end    ################################

    ################################  其他方法区  start  ################################

    ################################  其他方法区  end    ################################