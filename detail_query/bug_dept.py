   def _get_lines_dict(self, line, line_parent_dict, state_dict, dept_dict):
      '''
      @desc: 获取明细行及表头数据
      @params: self: 当前示例对象
      @params: line: 表体数据
      @params: line_parent_dict: 表头数据
      @params: state_dict: 状态字典，用于翻译
      @params: dept_dict: 往来单位字典
      @return: 每条明细行展示（用到）在报表中的数据
      '''
      doc_name = _('Expense Record Doc')  # 单据名称仅为Expense Record Doc
      apply_month = datetime.strftime(line_parent_dict['apply_date'], APPLY_MONTH)
      line_dict = {
         'exp_item_id': line['exp_item_id'][READ_VALUE_INDEX],
         'exp_amount': line['exp_amount'],
         'tax_amount': line['tax_amount'],
         'reimb_amount': line['reimb_amount'],
         'exp_amount_local': line['exp_amount_local'],
         'tax_amount_local': line['tax_amount_local'],
         'reimb_amount_local': line['reimb_amount_local'],
         'exp_org_id': line_parent_dict['exp_org_id'][READ_VALUE_INDEX],  # 费用承担组织
         'exp_dept_id': line['exp_dept_id'][READ_VALUE_INDEX],  # 子表费用承担部门
         'contact_dept': dept_dict[line_parent_dict['contact_dept']],
         'doc_name': doc_name,
         'doc_type_id': line_parent_dict['doc_type_id'][READ_VALUE_INDEX],
         'doc_num': line_parent_dict['number'],
         'apply_day': str(line_parent_dict['apply_date']),
         'apply_month': apply_month,
         'reason': line_parent_dict['reason'],
         'currency_id': line_parent_dict['currency_id'][READ_VALUE_INDEX] or '',  # 币别
         'currency_id_id': line_parent_dict['currency_id'][READ_ID_INDEX],  # 币别id
         'apply_dept_id': line_parent_dict['apply_dept_id'][READ_VALUE_INDEX],
         'apply_emp_id': line_parent_dict['apply_emp_id'][READ_VALUE_INDEX],
         'state': state_dict[line_parent_dict['state']],
         'source_parent_doc_id': line_parent_dict['id'],
         'parent_id': line_parent_dict['id'],
         'local_currency_id': line_parent_dict['local_currency_id'][READ_VALUE_INDEX] or '',
         'local_currency_id_id': line_parent_dict['local_currency_id'][READ_ID_INDEX]
         }
      return line_dict

   def _get_record_data(self, domain_fields):
      '''
      @desc: 表体数据查询
      @params: self: 当前示例对象
      @params: domain_fields: 筛选字段
      @return: lines_data表体数据，parent_id_dict表头数据字典，state_dict单据状态字典
      '''
      domain = [
         ('exp_org_id', '=', domain_fields['exp_org_id']),
         ('currency_id', 'in', domain_fields['currency_ids']),
         ('delete_state', '=', 'normal'),
         ('apply_date', '>=', domain_fields['start_date']),
         ('apply_date', '<=', domain_fields['end_date'])
         ]
      if not domain_fields['is_include_unaudit_doc']:
         domain.append(('state', '=', 'audit'))  # 不勾选包含未审核，只取已审核数据
      else:
         domain.append(('state', 'in', ['audit', 'save', 'submit']))  #勾选后包含保存，审核中，已审核的数据
      pay_dept_domain = self._get_dept_domain(domain_fields) # 获取往来单位的过滤
      domain.append(pay_dept_domain)
      expense_reimb_obj = self.env['amb.expense.reimb']
      if domain_fields['is_total']:  #勾选合计后按币别排序
         expense_records = expense_reimb_obj.search(domain, order='currency_id asc, apply_date asc, id asc')
      else:
         expense_records = expense_reimb_obj.search(domain, order='apply_date asc, id asc')
      # 表头展示数据查询
      parent_data = expense_records.query_read( 
         fields=['exp_org_id', 'contact_dept', 'doc_type_id', 
         'number', 'apply_date', 'reason', 'currency_id', 'apply_dept_id', 
         'apply_emp_id', 'state', 'local_currency_id'])
      record_ids = expense_records.ids
      # 单据排序的字典
      order_dict = {}
      for index, record_id in enumerate(record_ids):
         order_dict[record_id] = index
      expense_reimb_line_obj = self.env['amb.expense.reimb.line1']
      # 组织明细行过滤条件,从费用汇总表穿透过来的查询需要控制费用项目，增加明细行判断
      line_domain = [
         ('parent_id', 'in', record_ids),
         ('exp_dept_id', 'in', domain_fields['exp_dept_ids'])
         ]
      if domain_fields.get('exp_item_id', None):
         line_domain.append(('exp_item_id', '=', domain_fields['exp_item_id']))
      expense_lines = expense_reimb_line_obj.search(line_domain)
      lines_data = expense_lines.query_read(
         fields=['exp_dept_id', 'exp_item_id', 'exp_amount', 'tax_amount', 'reimb_amount', 
         'exp_amount_local', 'tax_amount_local', 'reimb_amount_local', 'parent_id', 'sequence'])
      lines_data.sort(key=lambda x: (order_dict[x['parent_id']], x['sequence']))  # 对表体数据按照表头进行排序
      parent_id_dict = {}  # 存放表头数据的字典，下面组装数据时根据parent_id添加表头数据
      for res in parent_data:
         parent_id_dict[res['id']] = res
      state_dict = dict(expense_records.fields_get(['state'])['state']['selection'])

      return lines_data, parent_id_dict, state_dict