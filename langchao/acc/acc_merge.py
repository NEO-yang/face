# -*- coding: utf-8 -*-
'''
==================================================
@创建人 ：杨兴财
@当前维护人 ：杨兴财
@Desc ：会计中心凭证工厂接口
==================================================
'''

from collections import defaultdict

from odoo import http,fields,_
from odoo.http import request
from odoo.tools.float_utils import float_round
from odoo.exceptions import ValidationError


DIGITS = 2  # 百分比精度
LIMIT_NUM = 1


class VoucherFactoryCtrl(http.Controller):

   @http.route('/ps_acc_center/voucher_factory/authority', type='json', auth='user', methods=['POST'])
   def voucher_authority(self):
      '''
      凭证工厂权限控制接口
      '''
      args = [
         {'attrs': {'name': 'create_scheme', 'type':'object'}, 'tag':'button'},
         {'attrs': {'name': 'delete_scheme', 'type':'object'}, 'tag':'button'},
         {'attrs': {'name': 'add_card', 'type':'object'}, 'tag':'button'},
         {'attrs': {'name': 'delete_card', 'type':'object'}, 'tag':'button'},
         {'attrs': {'name': 'voucher_generation', 'type':'object'}, 'tag':'button'},
         {'attrs': {'name': 'get_vouchers', 'type':'object'}, 'tag':'button'},
         {'attrs': {'name': 'voucher_generation_batch', 'type':'object'}, 'tag':'button'},
         ]
      data = {
            'create_scheme' : False,  # 新增方案
            'delete_scheme' : False,  # 删除方案
            'add_card' : False,  #  新增卡片
            'delete_card' : False,  # 删除卡片
            'voucher_generation' : False,  # 凭证生成
            'get_vouchers' : False,  # 凭证查看
            'voucher_generation_batch' : False,  # 批量生成凭证
            }
      model = 'acc.center.voucher.generation'
      voucher_generation_obj = request.env[model]
      results = voucher_generation_obj.button_access_check(model, args)
      for result in results:
         data[result['attrs']['name']] = True
      return {
         'code': 200,
         'data': data 
         }

   @http.route('/ps_acc_center/voucher_factory/orgs', type='json', auth='user', methods=['POST'])
   def get_orgs(self):
      '''
      获取结算组织及其账簿的基本信息
      '''
      # 获取当前用户有权限的组织
      org_and_role_obj = request.env['sys.admin.org.and.role.for.user']
      role_org_ids = org_and_role_obj.search([('user_id', '=', request.uid)]).filtered(
         lambda r: r.role_id.forbid_state == 'normal' and r.role_id.delete_state == 'normal')
      org_ids = role_org_ids.org_id.ids
      orgs_with_access = []
      for org in org_ids:
         if self._check_org_access(org_id=org, func_name='read'):
            orgs_with_access.append(org)
      book_obj = request.env['mdm.account.book']
      books = book_obj.search([('accting_org_id', 'in', orgs_with_access)])
      mapping = defaultdict(list)
      for book in books:
         mapping[book.accting_org_id].append(book)
      data = [{
         'id': org.id,  # 组织信息
         'name': org.name, 
         'type': 'org', 
         'children': [{  # 账簿信息
            'id': book.id, 
            'name': book.name, 
            'type': 'account_book'
            } for book in books]} 
         for org, books in mapping.items()] #遍历组织，页面信息按组织编码排序

      return {
         'code':200, 
         "data": sorted(data, key=lambda x: x['id'])}
   
   @http.route('/ps_acc_center/voucher_factory/cards', type='json', auth='user', methods=['POST'])
   def get_cards(self, accting_book_id, start_date, end_date):
      '''
      点击账簿后，获取右侧卡片界面的信息及卡片内部方案信息
      @param accting_book_id: 账簿ID
      @param start_date: 开始时间
      @param end_date: 结束时间
      @return: 返回选定账簿的卡片及方案与单据数量信息
      '''
      start_date = fields.Date.to_date(start_date)
      end_date = fields.Date.to_date(end_date)
      card_list = request.env['acc.center.voucher.generation'].search(
         [('delete_state', '=', 'normal'), 
         ('acct_book_id', '=', accting_book_id)]) 
      data_list = []  # 界面数据
      for card in card_list:
         template_data_list = []
         sum_doc = 0  # 单据数量和
         sum_vou = 0  # 凭证数量和
         for line in card.line_ids:
            template = line.template_id
            count = self._get_doc_count(card.acct_org_id.id, start_date, end_date, accting_book_id, template)
            sum_doc += count['doc_num']
            sum_vou += count['vou_num']
            template_data_list.append({
               'template_name': template.name, 
               'template_id': template.id,
               'doc_num': count['doc_num'],
               'vou_num': count['vou_num'],
               'module_id': card.module_id.id,
               'line_id': line.id
               })
         radio = float_round(
            sum_vou/(sum_vou + sum_doc)*100 if sum_doc or sum_vou else 0, precision_digits=DIGITS)
         radio_str = '{:.2f}'.format(radio)  # 精度确保为两位
         data_list.append({
            'accting_book_id': accting_book_id, 
            'template_data_list': template_data_list, 
            'icon': card.module_id.icon,
            'module_name': card.module_id.display_name,
            'module_id': card.module_id.id,
            'radio': radio_str
            })

      return {
         'code':200, 
         'data': data_list}

   @http.route('/ps_acc_center/voucher_factory/org/schemes', type='json', auth='user', methods=['POST'])
   def get_org_schemes(self, org_id, start_date, end_date, offset, limit):
      """
      获取组织的列表信息
      @param org_id: 组织ID
      @param start_date: 开始时间
      @param end_date: 结束时间
      @param offset: 忽略行数（分页）
      @param limit: 每页数量
      @return: 返回选定组织的账簿及凭证数量信息
      """
      start_date = fields.Date.to_date(start_date)
      end_date = fields.Date.to_date(end_date)
      cards = request.env['acc.center.voucher.generation'].search(
         [('delete_state', '=', 'normal'), 
         ('acct_org_id', '=', org_id)])
      templates = request.env['acc.center.voucher.generation.line1'].search(
         [('parent_id', 'in', cards.ids)], 
         limit=limit, 
         offset=offset, 
         order='parent_id')
      data_list = []
      for line in templates:
         accting_book_id = line.parent_id.acct_book_id
         module = line.parent_id.module_id
         doc_num = self._get_doc_count(
            org_id, start_date, end_date, accting_book_id.id, line.template_id)['doc_num']
         data_list.append({
            'accting_book': accting_book_id.name,
            'accting_book_id': accting_book_id.id,
            'template': line.template_id.name, 
            'template_id': line.template_id.id,
            'domain': module.ps_domain_id.name, 
            'module': module.display_name, 
            'module_id': module.id, 
            'doc_num': doc_num,
            'line_id': line.id,
            })
      template_total = request.env['acc.center.voucher.generation.line1'].search_count(
         [('parent_id', 'in', cards.ids)])
      return {
         'code':200, 
         'tableData': {
            'rows': data_list, 
            'total': template_total, 
            'totalNotFiltered':template_total,
      }}

   @http.route('/ps_acc_center/voucher_factory/schemes', type='json', auth='user', methods=['POST'])
   def get_schemes(self, accting_book_id, module_id, offset, limit):
      '''
      新增凭证方案时，列表界面接口
      @param accting_book_id: 账簿ID
      @param module_id: 卡片ID（模块ID）
      @param offset: 忽略行数（分页）
      @param limit: 每页数量
      @return: 返回选定账簿的模块中已经启用的但未选用的方案
      '''
      voucher_generation_obj = request.env['acc.center.voucher.generation']
      card_list = voucher_generation_obj.search([
         ('delete_state', '=', 'normal'), 
         ('acct_book_id', '=', accting_book_id), 
         ('module_id', '=', module_id)
         ], limit=1)
      acct_table_id = card_list.acct_book_id.acct_table_id.id
      template_list = card_list.line_ids.template_id.ids
      domain = [
         ('id', 'not in', template_list), 
         ('source_doc_id.ps_module_id', '=', module_id), 
         ('acct_table_id', '=', acct_table_id),
         ('forbid_state', '=', 'normal'),
         ('delete_state', '=', 'normal')]
      template_obj = request.env['acc.center.template']
      templates = template_obj.search(domain, limit=limit, offset=offset, order='number')
      templates_total = template_obj.search_count(domain)
      return {
         'code':200, 
         'tableData': {
            'rows': [{
               'template_name': rec.name, 
               'source_doc_name': rec.source_doc_id.name, 
               'acct_table_id': rec.acct_table_id.name,
               'template_id': rec.id
               } for rec in templates], 
            'total': templates_total, 
            'totalNotFiltered':templates_total,
      }}

   @http.route('/ps_acc_center/voucher_factory/scheme/create', type='json', auth='user', methods=['POST'])
   def create_scheme(self, accting_book_id, module_id, templates):
      '''
      新增凭证方案时，确定接口
      @param accting_book_id: 账簿ID
      @param module_id: 卡片ID（模块ID）
      @param templates: 选择方案的id列表： []
      @return: 在凭证生成表明细表中插入所选的方案
      '''
      is_book_access = self._check_book_access(book_id=accting_book_id, func_name='create_scheme')
      if not is_book_access:
         return {
            'code': 403,
            # 您没有%s的权限，请联系管理员
            'message': _("You don't have %s access, please contact the administrator") % _('Create Voucher Scheme')
         }
      else:
         templates_obj = request.env['acc.center.template']
         templates_data = templates_obj.browse(templates)
         card_obj = request.env['acc.center.voucher.generation']
         card_id = card_obj.search(
            [('delete_state', '=', 'normal'), 
            ('acct_book_id', '=', accting_book_id), 
            ('module_id', '=', module_id)],
            limit=LIMIT_NUM).id
         for template in templates_data:
            voucher_generation_line1_obj = request.env['acc.center.voucher.generation.line1']
            scheme_id = voucher_generation_line1_obj.search([
               ('parent_id', '=', card_id),
               ('source_doc_id', '=', template.source_doc_id.id),
               ('source_doc_model', '=', template.source_doc_id.model),
               ('template_id', '=', template.id)
            ])
            if scheme_id:
               # 该方案已被添加，请刷新页面查看
               raise ValidationError(_('The scheme has been added, please refresh the page to view'))
            else:
               voucher_generation_line1_obj.create({
                  'parent_id': card_id,
                  'source_doc_id': template.source_doc_id.id,
                  'source_doc_model': template.source_doc_id.model,
                  'template_id': template.id
                  })
         return {'code': 200}

   @http.route('/ps_acc_center/voucher_factory/scheme/delete', type='json', auth='user', methods=['POST'])
   def delete_scheme(self, accting_book_id, module_id, template_id):
      '''
      删除凭证方案时，接口
      @param accting_book_id: 账簿ID
      @param module_id: 卡片ID（模块ID）
      @param template_id: 选择删除方案的id
      @return: 在凭证生成表明细表中插入所选的方案
      '''
      is_book_access = self._check_book_access(book_id=accting_book_id, func_name='delete_scheme')
      if not is_book_access:
         return {
            'code': 403,
            # 您没有%s的权限，请联系管理员
            'message': _("You don't have %s access, please contact the administrator") % _('Delete Voucher Scheme')
         }
      else:
         voucher_generation_obj = request.env['acc.center.voucher.generation']
         card_id = voucher_generation_obj.search(
            [('delete_state', '=', 'normal'), 
            ('acct_book_id', '=', accting_book_id), 
            ('module_id', '=', module_id)],
            limit=LIMIT_NUM).id
         voucher_generation_line1_obj = request.env['acc.center.voucher.generation.line1']
         lines = voucher_generation_line1_obj.search(
            [('parent_id', '=', card_id), 
            ('template_id', '=', template_id)])
         lines.unlink()
         return {'code': 200}

   @http.route('/ps_acc_center/voucher_factory/modules', type='json', auth='user', methods=['POST'])
   def get_modules(self, accting_book_id, offset, limit):
      '''
      新建卡片查询模块列表接口
      @param accting_book_id: 账簿ID
      @param offset: 忽略行数（分页）
      @param limit: 每页数量
      @return: 具有凭证模板的模块的列表
      '''
      modules = request.env['acc.center.voucher.generation'].search(
         [('delete_state', '=', 'normal'), 
         ('acct_book_id', '=', accting_book_id)]).module_id.ids
      template = request.env['acc.center.template'].search(
         [('forbid_state', '=', 'normal'), 
         ('delete_state', '=', 'normal'), 
         ('source_doc_id.ps_module_id', 'not in', modules)])
      modules_total = 0
      if template:
         modules = request.env['ir.module.module'].search(
            [('id', 'in', template.source_doc_id.ps_module_id.ids)], 
            limit=limit, 
            offset=offset, 
            order='ps_domain')
         modules_total = request.env['ir.module.module'].search_count(
            [('id', 'in', template.source_doc_id.ps_module_id.ids)])
         data_list = [{
            'module_name': module.display_name,
            'module_id': module.id,
            'module_domain': module.ps_domain_id.name,
            } for module in modules]
      else:
         data_list = []
      return {
         'code':200, 
         'tableData': {
            'rows': data_list, 
            'total': modules_total, 
            'totalNotFiltered':modules_total
      }}

   @http.route('/ps_acc_center/voucher_factory/card/create', type='json', auth='user', methods=['POST'])
   def create_card(self, accting_book_id, modules):
      '''
      新建卡片-确定保存
      @param accting_book_id: 账簿ID
      @param modules: 模块ID列表
      @return: 在凭证生成表中插入所选的模块
      '''

      is_book_access = self._check_book_access(book_id=accting_book_id, func_name='add_card')
      if not is_book_access:
         return {
            'code': 403,
            # 您没有%s的权限，请联系管理员
            'message': _("You don't have %s access, please contact the administrator") % _('Add Card')
         }
      else:
         voucher_generation_obj = request.env['acc.center.voucher.generation']
         for module in modules:
            card_id = voucher_generation_obj.search([
               ('acct_book_id', '=', accting_book_id),
               ('module_id', '=', module),
               ('delete_state', '=', 'normal'),
               ])
            if card_id:
               # 该卡片已被添加，请刷新页面查看
               raise ValidationError(_('The card has been added, please refresh the page to view'))
            else:
               voucher_generation_obj.create({
                  'acct_book_id': accting_book_id,  # 会计账簿
                  'module_id': module,
                  })

         return {'code': 200}

   @http.route('/ps_acc_center/voucher_factory/card/delete', type='json', auth='user', methods=['POST'])
   def delete_card(self, accting_book_id, module_id):
      '''
      删除卡片
      @param accting_book_id: 账簿ID
      @param module_id: 模块ID
      @return: 在凭证生成表中删除所选的模块
      '''

      is_book_access = self._check_book_access(book_id=accting_book_id, func_name='delete_card')
      if not is_book_access:
         return {
            'code': 403,
            # 您没有%s的权限，请联系管理员
            'message': _("You don't have %s access, please contact the administrator") % _('Delete Card')
         }
      else:
         voucher_generation_obj = request.env['acc.center.voucher.generation']
         card = voucher_generation_obj.search([
            ('module_id', '=', module_id), 
            ('delete_state', '=', 'normal'), 
            ('acct_book_id', '=', accting_book_id)])
         if card.line_ids:
            # 该卡片内存在凭证方案，不允许删除，请清空方案后再次删除
            raise ValidationError(_("There is at least one voucher scheme in the card and it is not allowed to delete it.Please clear the scheme and delete it again"))
         else:
            card.write({
               'delete_state': 'delete',
               'delete_uid': request.env.uid,
               'delete_date': fields.Datetime.now()
            })
         return {'code': 200}


   @http.route('/ps_acc_center/voucher_factory/voucher/show_docs', type='json', auth='user', methods=['POST'])
   def show_docs(self, line_id, start_date, end_date, accting_book_id = None,):
      '''
      选单按钮
      @param accting_book_id: 账簿ID
      @param module_id: 模块ID
      @return: 在凭证生成表中删除所选的模块
      '''
      start_date = fields.Date.to_date(start_date)
      end_date = fields.Date.to_date(end_date)
      voucher_generation_line1_obj = request.env['acc.center.voucher.generation.line1']
      line_record = voucher_generation_line1_obj.browse(line_id)
      template = line_record.template_id
      org_id = line_record.parent_id.acct_org_id.id
      accting_book_id = line_record.parent_id.acct_book_id.id #可直接传入
      count = self._get_doc_count(org_id, start_date, end_date, accting_book_id, template)
      doc_ids = count.get('doc_ids', None)


      return {
         'code': 200,
         'data':{
            'model_key': template.source_doc_model,
            'domain':[('id', 'in', doc_ids)]
            }
         }
      
      


   @http.route('/ps_acc_center/voucher_factory/voucher/generation', type='json', auth='user', methods=['POST'])
   def voucher_generation(self, line_id, start_date, end_date, doc_ids = None):
      '''
      生成凭证接口 与批量生成凭证共用一个接口
      @param start_date: 开始日期
      @param end_date: 结束日期
      @param line_id: 凭证选择表明细行ID
      @return: 跳转至凭证界面
      '''
      org_with_access = []
      voucher_generation_line1_obj = request.env['acc.center.voucher.generation.line1']
      if isinstance(line_id, int):
         org_id = voucher_generation_line1_obj.browse(line_id).parent_id.acct_org_id.id
         is_org_access = self._check_org_access(org_id=org_id, func_name='voucher_generation')
         if not is_org_access:
            return {
               'code': 403,
               # 您没有%s的权限，请联系管理员
               'message': _("You don't have %s access, please contact the administrator") % _('Generate Vouchers')
            }
         else:
            org_with_access.append(org_id)
      else:
         org_ids = voucher_generation_line1_obj.browse(line_id).parent_id.acct_org_id.ids
         for org in org_ids:
            is_org_access = self._check_org_access(org_id=org, func_name='voucher_generation_batch')
         if is_org_access:
            org_with_access.append(org)
      if not org_with_access:
         return {
               'code': 403,
               # 您没有%s的权限，请联系管理员
               'message': _("You don't have %s access, please contact the administrator") % _('Batch Voucher Generation')
            }
      else:
         start_date = fields.Date.to_date(start_date)
         end_date = fields.Date.to_date(end_date)
         lines = voucher_generation_line1_obj.browse(line_id)
         line = lines.filtered(lambda r: r.parent_id.acct_org_id.id in org_with_access)
         return {
            'code': 200,
            'action': request.env['acc.center.voucher.generation'].p_generate_vouchers(line, start_date, end_date)
         }

   @http.route('/ps_acc_center/voucher_factory/vouchers', type='json', auth='user', methods=['POST'])
   def get_vouchers(self, start_date, end_date, accting_book_id, template_id):
      '''
      查看凭证接口
      @param start_date: 开始日期
      @param end_date: 结束日期
      @param accting_book_id: 会计账簿
      @param template_id: 模板ID
      @return: 跳转至凭证界面
      '''

      is_book_access = self._check_book_access(book_id=accting_book_id, func_name='get_vouchers')
      if not is_book_access:
         return {
            'code': 403,
            # 您没有%s的权限，请联系管理员
            'message': _("You don't have %s access, please contact the administrator") % _('Watch Vouchers')
         }
      else:
         template_obj = request.env['acc.center.template']
         template = template_obj.browse(template_id)
         voucher_obj = request.env['gl.voucher']
         voucher_ids = voucher_obj.search([
            ('delete_state', '=', 'normal'),
            ('acct_book_id', '=', accting_book_id),
            ('business_date', '>=', start_date), 
            ('business_date', '<=', end_date),
            ('voucher_source', '=', template.source_doc_id.model)
            ]) 
         action = {
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'views': [(request.env.ref('ps_gl.view_gl_voucher_tree').id, 'list'), 
                  (request.env.ref('ps_gl.view_gl_voucher_form').id, 'form')],
            'res_model': voucher_ids._name,
            'domain': [('id', 'in', voucher_ids.ids), ('delete_state', '=', 'normal')],
            'context': {'flex_apply_model': 'line_ids'}, 
            'ref': 'ps_gl.action_gl_voucher',
            }
         if len(voucher_ids) == 1:
            action.update({
               'res_id': voucher_ids.id,
               'view_type': 'form',
            })
         return {
            'code': 200, 
            'action': action}

   def _get_doc_count(self, accting_org_id, start_date, end_date, accting_book_id, template):
      """
      获取未生成凭证单据数量
      @param accting_org_id: 核算组织
      @param start_date: 开始日期
      @param end_date: 结束日期
      @param accting_book_id: 会计账簿
      @param template: 凭证方案
      @return: 返回生成的凭证数量与单据数量
      """
      source_doc_model = template.source_doc_model
      # 获取已生成的凭证ID
      voucher_ids = request.env['gl.voucher'].search([
         ('acct_book_id', '=', accting_book_id),
         ('voucher_source', '=', source_doc_model),
         ('business_date', '>=', start_date), 
         ('business_date', '<=', end_date), 
         ('source_module_id', '=', template.source_module_id.id),
         ('delete_state', '=', 'normal')
         ]).ids
      source_doc_ids = []
      if voucher_ids:
         # 获取link表内的来原单据的ID
         source_doc_ids = [
            rec['source_doc_id'] 
            for rec in request.env['studio.botp.record'].search_read([
               ('record_type', '=', 'acct_center'),
               ('delete_state', '=', False), 
               ('source_model_key', '=', source_doc_model),
               ('target_model_key', '=', 'gl.voucher'),
               ('target_doc_id', 'in', voucher_ids)
               ], fields=['source_doc_id']) 
            if rec.get('source_doc_id', None)]
      # 检查当前模型是否存在业务日期和主组织字段，用于过滤，如果不存在提示报错
      source_doc_model_obj = request.env[source_doc_model]
      fields = source_doc_model_obj._fields

      accting_book_obj = request.env['mdm.account.book']
      accting_book = accting_book_obj.browse(accting_book_id)
      org_ids = accting_book.accting_sys_id.accting_org_ids.filtered(
         lambda org: org.org_id.id == accting_org_id).accting_org_line_ids.org_id.ids
      if accting_org_id not in org_ids:
         org_ids.append(accting_org_id)
      # TODO:改造更改处：未改（兼容处理，待模板字段必填后，去除biz_date）
      # date = template.vou_date_field_name
      date_field = template.vou_date_field_name or 'biz_date'
      domain_doc = [
         ('id', 'not in', source_doc_ids),
         (date_field, '>=', start_date), 
         (date_field, '<=', end_date), 
         (template.acct_org_field_name, 'in', org_ids)
         ]
      if 'delete_state' in fields:
         domain_doc.append(('delete_state', '=', 'normal'))

      # 未生成凭证的单据数量
      doc_ids = source_doc_model_obj.search(domain_doc).ids
      return {
         'doc_num': len(doc_ids), 
         'vou_num': len(voucher_ids),
         'doc_ids': doc_ids
         }

   def _check_org_access(self, org_id, func_name):
      '''
      多组织权限检查 
      '''
      org_and_role_for_user_obj = request.env['sys.admin.org.and.role.for.user']
      role_ids = org_and_role_for_user_obj.search([
         ('user_id', '=', request.uid), 
         ('org_id', '=', org_id)]).filtered(
            lambda r: r.role_id.forbid_state == 'normal' 
            and r.role_id.delete_state == 'normal').role_id.ids
      access_sec_obj = request.env['sys.admin.access.sec']
      records = access_sec_obj.search([
         ('role_id', 'in', role_ids), 
         ('func_name', '=', func_name), 
         ('model', '=', 'acc.center.voucher.generation')
         ])
      func_sec_yes_list = [record.is_func_sec_yes for record in records]
      func_sec_ban_list = [record.is_func_sec_ban for record in records]
      if any(func_sec_ban_list) or not any(func_sec_yes_list):
         # 若禁止，无权      若角色都无权，无权
         return False
      else:
         return True

   def _check_book_access(self, book_id, func_name):
      '''
      校验用户对于账簿的权限
      '''
      book_obj = request.env['mdm.account.book']
      org_id = book_obj.browse(book_id).accting_org_id.id
      return self._check_org_access(org_id=org_id, func_name=func_name)