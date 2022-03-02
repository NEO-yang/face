def _conduct_simulation_audit(self, domain_fields):
        """
        @desc: 进行模拟审核过程，根据条件，从各个单据中查找相关数据
        @params: self: 当前示例对象
        @params: domain_fields: 字段选择过滤条件

        @return: cash_income_expense_analog_data_list: 组织好的模拟审核数据列表，里面有多个dict数据（由各个业务单据直接获取）
        """
        # 获取当前查询条件中的所选组织的启用日期（查询各个单据的未审核数据的开始日期）
        start_date = self._get_activation_date(domain_fields)

        # 根据查询条件中的结束日期获取（查询各个单据的未审核数据的开始日期）
        end_date = domain_fields['end_date']

        # 定义模拟数据字典组成的列表，（各个业务单据，模拟审核过程组织的数据）
        cash_income_expense_analog_data_list = list()

        # 定义模拟数据字典，将组织好的列表循环获取组织出以（账号、币别）为维度的key-value对应的dict
        unaudit_data_dict = dict()

        # 根据查询条件字典cash_income_expense_search_dict，获取现金收支表查询的条件数据

        for key in DOC_MODEL_DICT:
            source_parent_model = key  # 来源单据主表模型名
            record_id_list = []  # 当单据的主表对应多张子表时，会出现重复查询，这里定义一个列表，用于记录每个数据集合的id
            cash_income_expense_list = []  # 组织需要被模拟审核的每一种单据的所有记录
            for value in DOC_MODEL_DICT[key]:
                source_model = value  # 来源单据明细行模型名
                # 注意：这里需要先取出各个单据明细行中，（现金账号+币别）维度的数据，返向找出符合条件的单据主表对象数据集
                record = self.env[source_parent_model].search([
                    ('state', 'in', ['save', 'submit']),
                    ('delete_state', '=', 'normal'),
                    ('biz_date', '>=', start_date),
                    ('biz_date', '<=', end_date)
                ])
                for res in record:
                    # 获取循环的每个明细行模型得到的模拟审核数据列表
                    if res.id in record_id_list:
                        # 当记录在record_id_list中，说明已经查询过，不再查询数据
                        cash_income_expense_list = []
                        continue
                    else:
                        record_id_list.append(res.id)
                        cash_income_expense_list.append(res)

                # 由于性能优化，重构cm.cash.income.expense模型中的p_set_data，因此可将所有的res合并在一个list中一起进行模拟审核过程
                analog_data_list = self.env['cm.cash.income.expense'].p_set_data(
                    source_model, cash_income_expense_list, flag=True)
                if len(analog_data_list) > 0:
                    cash_income_expense_analog_data_list.extend(
                        analog_data_list)

        for res in cash_income_expense_analog_data_list:
            # 组织字典的key
            # 组织key时，以（账号id、币别id）为纬度进行分组
            key_acct_number_id = str(
                res['cash_acct_number_id'].id) if res['cash_acct_number_id'] else str(0)
            key_currency_id = str(
                res['currency_id'].id) if res['currency_id'] else str(0)
            key_biz_date = str(res['biz_date']) if res['biz_date'] else str(0)
            key = 'acct_number_id_' + key_acct_number_id + '_currency_id_' + \
                key_currency_id + '_biz_date_' + key_biz_date

            # 这里按照（账号id、币别id、业务日期）为维度进行分组，因为会出现相同维度的多条数据，因此需要存储再同一个key中的value中，因此使用list来组织value数据
            if not unaudit_data_dict.get(key):
                unaudit_data_dict[key] = list()

            unaudit_data_dict[key].append(res)
        return unaudit_data_dict