def _create_data_type_sale_receive_s(self, parent, lines, source_model_id, source_parent_model_id, source_parent_model, cash_sett_type_ids):
        """
        @desc: 创建销售业务收款单/其他业务收款单相关数据到后台表中
        @params: self: 实列
        @params: obj: 各个单据的明细行数据对象
        @params: source_model_id: 来源单据明细行模型id
        @params: source_parent_model_id: 来源单据主表模型id
        @return: 返回一个list，包含所有需要创建的记录的字典集合。
        """
        create_list = list()

        # 优化性能，将主表obj对象对应字段，提出到for循环外，提高性能
        doc_id = parent['id']  # 来源单据主表id
        tenant_id = parent['tenant_id']  # 租户
        number = parent['number']  # 单据编号
        create_uid = parent['create_uid']  # 创建人
        recpay_org_id = parent['recv_org_id'] # 收付组织
        biz_date = parent['biz_date']  # 业务日期
        state = parent['state']  # 单据状态
        currency_id = parent['currency_id'] # 币别
        local_currency_id = parent['local_curr_id']  # 本位币
        sett_org_id = parent['sett_org_id'] and parent['sett_org_id'][0]  # 结算组织
        contact_dept = parent['contact_dept']  # 往来单位
        for line in lines:
            sett_type_id = line['sett_type_id']
            # 取明细行数据，结算方式为现金业务的
            if sett_type_id and sett_type_id[0] in cash_sett_type_ids:
                cash_acct_number_id = line['cash_acct_id']  # 现金账号
                payment_purpose = line['biz_type_id']  # 收付款用途
                income_amount = abs(line['discount_amount'])  # 收入金额
                income_amount_local = abs(line['discount_amount_local'])  # 收入金额本位币
                expense_amount = abs(line['commission'])  # 支出金额
                expense_amount_local = abs(line['commission_local'])  # 支出金额本位币

                base_dict = {
                    'tenant_id': tenant_id,  # 租户
                    'source_create_uid': create_uid,  # 创建人
                    'number': number,  # 单据编号
                    'recpay_org_id': recpay_org_id,  # 收付组织
                    'biz_date': biz_date,  # 业务日期
                    'state': state,  # 单据状态
                    'currency_id': currency_id,  # 币别
                    'local_currency_id': local_currency_id,  # 本位币
                    'sett_org_id': sett_org_id,  # 结算组织
                    'contact_dept': contact_dept,  # 往来单位
                    'source_sequence': line['sequence'],  # 单据行号
                    'sett_number': line['sett_number'],  # 结算号
                    'summary': line['note'] or '',  # 摘要
                    'is_check': line['is_check'],  # 勾对
                    'source_model_id': source_model_id,  # 来源单据明细行模型id
                    'source_doc_id': line['id'],  # 来源单据明细行id
                    'source_parent_doc_id': doc_id,  # 来源单据主表id
                    'cash_acct_number_id': cash_acct_number_id,  # 现金账号
                    'payment_purpose': payment_purpose,  # 收付款用途
                    'sett_type_id': sett_type_id,  # 结算方式
                    'source_parent_model': source_parent_model # 来源单据主表模型
                }
                
                if expense_amount != 0 or expense_amount_local != 0:
                    # 如果收入金额/收入金额本位币/支出金额/支出金额本位币都为 0 ，则不进行数据创建
                    create_list.append({
                        'income_amount': 0,  # 收入金额
                        'expense_amount': expense_amount,  # 支出金额
                        'income_amount_local': 0,  # 收入金额本位币
                        'expense_amount_local': expense_amount_local,  # 支出金额本位币
                        **base_dict
                    })

                if income_amount != 0 or income_amount_local != 0:
                    # 如果收入金额/收入金额本位币/支出金额/支出金额本位币都为 0 ，则不进行数据创建
                    create_list.append({
                        'income_amount': income_amount,  # 收入金额
                        'expense_amount': 0,  # 支出金额
                        'income_amount_local': income_amount_local,  # 收入金额本位币
                        'expense_amount_local': 0,  # 支出金额本位币
                        **base_dict
                    })
        return create_list