def _get_cm_receivable_bill_line1_sale_data(self, records, parent_model, child_model):
        """
        @desc: 销售业务收款单/其他业务收款单数据汇集
        @params records: 表头对象
        @params parent_model: 表头模型名称
        @params child_model: 表体模型名称
        @return 返回数据列表
        """
        parent_list = records.query_read( 
            fields=['number', 'create_uid', 'biz_date', 'currency_id', 'local_curr_id', 'state', 'recv_org_id'])
        cash_sett_type_ids = self.env['mdm.settle.type'].with_context(disable_state_filter=True).search([('buss_type', '=', 'cash')]).ids
        lines_dict = self._get_line_dict(
            doc_ids=records.ids, 
            model=child_model,
            domain=[('sett_type_id', 'in', cash_sett_type_ids)],
            fields=['sett_type_id', 'sequence', 'cash_acct_id', 'discount_amount', 'discount_amount_local', 
                'commission', 'commission_local', 'biz_type_id', 'note', 'parent_id']
            )

        result = []
        for parent in parent_list:
            for line in lines_dict[parent['id']]:
                # 取明细行数据，结算方式为现金业务的
                income_amount = abs(line['discount_amount'])  # 收入金额
                income_amount_local = abs(line['discount_amount_local'])  # 收入金额本位币
                expense_amount = abs(line['commission'])  # 支出金额
                expense_amount_local = abs(line['commission_local'])  # 支出金额本位币
                base_dict = {
                    'recpay_org_id': parent['recv_org_id'],
                    'source_create_uid': parent['create_uid'],  # 创建人
                    'number': parent['number'],  # 单据编号
                    'biz_date': parent['biz_date'],  # 业务日期
                    'state': parent['state'],  # 单据状态
                    'currency_id': parent['currency_id'],  # 币别
                    'local_currency_id': parent['local_curr_id'],  # 本位币
                    'source_sequence': line['sequence'],  # 单据行号
                    'summary': line['note'] or '',  # 摘要
                    'source_doc_id': line['id'],  # 来源单据明细行id
                    'source_parent_doc_id': parent['id'],  # 来源单据主表id
                    'cash_acct_number_id': line['cash_acct_id'],  # 现金账号
                    'payment_purpose': line['biz_type_id'],  # 收付款用途
                    'sett_type_id': line['sett_type_id'],  # 结算方式
                    'source_parent_model': parent_model # 来源单据主表模型
                }
                    
                if expense_amount != 0 or expense_amount_local != 0:
                    # 如果支出金额/支出金额本位币都为 0 ，则不进行数据创建
                    result.append({
                        'income_amount': 0,  # 收入金额
                        'expense_amount': expense_amount,  # 支出金额
                        'income_amount_local': 0,  # 收入金额本位币
                        'expense_amount_local': expense_amount_local,  # 支出金额本位币
                        **base_dict
                    })

                if income_amount != 0 or income_amount_local != 0:
                    # 如果收入金额/收入金额本位币都为 0 ，则不进行数据创建
                    result.append({
                        'income_amount': income_amount,  # 收入金额
                        'expense_amount': 0,  # 支出金额
                        'income_amount_local': income_amount_local,  # 收入金额本位币
                        'expense_amount_local': 0,  # 支出金额本位币
                        **base_dict
                    })
        return result