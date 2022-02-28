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


class VoucherFactoryCtrl(http.Controller):

   @http.route('/ps_acc_center/voucher_factory/orgs', type='json', auth='user', methods=['POST'])
   def get_orgs(self):
      '''
      获取结算组织及其账簿的基本信息
      '''
      books = request.env['mdm.account.book'].search([])
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
         data_list.append({
            'accting_book_id': accting_book_id, 
            'template_data_list': template_data_list, 
            'icon': card.module_id.icon,
            'module_name': card.module_id.display_name,
            'module_id': card.module_id.id,
            'radio': radio
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
      card_list = request.env['acc.center.voucher.generation'].search([
         ('delete_state', '=', 'normal'), 
         ('acct_book_id', '=', accting_book_id), 
         ('module_id', '=', module_id)
         ])
      template_list = card_list.line_ids.template_id.ids
      domain = [
         ('id', 'not in', template_list), 
         ('source_doc_id.ps_module_id', '=', module_id), 
         ('forbid_state', '=', 'normal'),
         ('delete_state', '=', 'normal')]
      templates = request.env['acc.center.template'].search(domain, limit=limit, offset=offset, order='number')
      templates_total = request.env['acc.center.template'].search_count(domain)
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
      templates_data = request.env['acc.center.template'].browse(templates)
      card_id = request.env['acc.center.voucher.generation'].search(
         [('delete_state', '=', 'normal'), 
         ('acct_book_id', '=', accting_book_id), 
         ('module_id', '=', module_id)]).id
      for template in templates_data:
         request.env['acc.center.voucher.generation.line1'].create({
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
      card_id = request.env['acc.center.voucher.generation'].search(
         [('delete_state', '=', 'normal'), 
         ('acct_book_id', '=', accting_book_id), 
         ('module_id', '=', module_id)]).id
      lines = request.env['acc.center.voucher.generation.line1'].search(
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
      for module in modules:
         request.env['acc.center.voucher.generation'].create({
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
      card = request.env['acc.center.voucher.generation'].search([
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


   @http.route('/ps_acc_center/voucher_factory/voucher/generation', type='json', auth='user', methods=['POST'])
   def voucher_generation(self, line_id, start_date, end_date):
      '''
      生成凭证接口
      @param start_date: 开始日期
      @param end_date: 结束日期
      @param line_id: 凭证选择表明细行ID
      @return: 跳转至凭证界面
      '''
      start_date = fields.Date.to_date(start_date)
      end_date = fields.Date.to_date(end_date)
      line = request.env['acc.center.voucher.generation.line1'].browse(line_id)
      infos = request.env['acc.center.voucher.generation'].p_generate_vouchers(line, start_date, end_date)
      return {
         'code': 200,
         'action': infos['notify_dialog']['to_return'] #跳转动作预留，代码完善后放开
      }

      # TODO:前端更改完生成凭证提示框后，直接返回调用结果
      # return request.env['acc.center.voucher.generation'].p_generate_vouchers(line, start_date, end_date)
      
   @http.route('/ps_acc_center/voucher_factory/voucher/batch', type='json', auth='user', methods=['POST'])
   def voucher_generation_batch(self, data, start_date, end_date):
      '''
      批量生成凭证接口
      @param start_date: 开始日期
      @param end_date: 结束日期
      @param data: []凭证选择表明细行ID列表
      @return: 跳转至凭证界面
      '''
      start_date = fields.Date.to_date(start_date)
      end_date = fields.Date.to_date(end_date)
      lines = request.env['acc.center.voucher.generation.line1'].browse(data)
      infos = request.env['acc.center.voucher.generation'].p_generate_vouchers(lines, start_date, end_date)
      return {
         'code': 200,
         'action': infos['notify_dialog']['to_return'] #跳转动作预留，代码完善后放开
      }

      # TODO:前端更改完生成凭证提示框后，直接返回调用结果
      # return request.env['acc.center.voucher.generation'].p_generate_vouchers(line, start_date, end_date)

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
      template = request.env['acc.center.template'].browse(template_id)
      voucher_ids = request.env['gl.voucher'].search([
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
      source_doc_model_obj = request.env[source_doc_model]
      # 获取已生成的凭证ID
      voucher_ids = request.env['gl.voucher'].search([
         ('acct_book_id', '=', accting_book_id),
         ('voucher_source', '=', source_doc_model),
         ('business_date', '>=', start_date), 
         ('business_date', '<=', end_date), 
         ('system_source', '=', source_doc_model_obj._module),
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
      domain_doc = [
         ('id', 'not in', source_doc_ids),
         ('delete_state', '=', 'normal'), 
         ('biz_date', '>=', start_date), 
         ('biz_date', '<=', end_date), 
         (template.acct_org_field_name, '=', accting_org_id)
         ]
      # 未生成凭证的单据数量
      doc_num = source_doc_model_obj.search_count(domain_doc)
      return {
         'doc_num': doc_num, 
         'vou_num': len(voucher_ids)}