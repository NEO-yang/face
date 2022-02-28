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
                    doc_key = tuple(document.get(field, None) for field in merge_fields) if merge_fields else doc_id
                    # 如果不存在凭证，则新增一个
                    line_ids = data.pop('line_ids')
                    if doc_key not in merge_mapping:
                        merge_mapping[doc_key] = (len(voucher_vals), {})
                        voucher_vals.append({
                            'accting_org_id': accting_org_id,
                            'acct_book_id': accting_book.id,
                            'acct_period_id': accting_period_id,
                            'voucher_word_id': accting_book.voucher_word_id.id,
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
                            'trackings': [],
                            'docs': []
                        })

                    # 凭证明细行合并
                    voucher_index, line_mapping = merge_mapping[doc_key]
                    if template_id.is_combine:
                        self._merge_voucher_lines(voucher_vals[voucher_index]['line_ids'], line_mapping, line_ids, accting_book.currency_id.id)
                    else:
                        voucher_vals[voucher_index]['line_ids'].extend(line_ids)
                    # 增加一个追踪记录
                    voucher_vals[voucher_index]['trackings'].append(tacking_data)
                    voucher_vals[voucher_index]['docs'].append((doc_id, document['number']))