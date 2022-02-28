# -*- coding: utf-8 -*-
'''
==================================================
@创建人: 杨兴财
@当前维护人: 杨兴财
@Desc: 费用报销单监听者
==================================================
'''
from odoo import _, fields
from datetime import datetime


from odoo.tools import float_compare
from odoo.addons.component.core import Component
from odoo.addons.component_event.components.event import skip_if
from odoo.exceptions import ValidationError


ID_FIRST_INDEX = 0 # id第一个的索引值


class ErExpenseListener(Component):
    _name = "er.expnse.listener"
    _inherit = "base.event.listener"
    _apply_on = [
        # 付款申请单及明细 付款单及明细
        'cm.payment.requisition', 'cm.payment.requisition.line1', # 付款申请单
        'cm.payable.bill', 'cm.payable.bill.line1', # 付款单
    ]

    
    ################################  目标单据为付款申请单，监听者模式，单据转换服务区  start   ################################

    @skip_if(lambda self, reverse_amount, source_doc_ids, time, source_model_key: not(source_model_key == 'er.expense'))
    def on_cm_requisition_apply_pay_amount_listen(self, time, reverse_amount, source_doc_ids, **kwargs):
        """
        函数传入参数：
            kwargs:
                    record： 单据记录
                    time： 反写时机
        函数功能描述：
            监听下推下游付款申请单单据保存、删除后的hook函数
            进行金额回写

        函数返回值:

        """
        if source_doc_ids:
            str_ids = source_doc_ids.split(',')
            source_doc_ids = [int(i) for i in str_ids]
        expense_obj = self.env['er.expense']
        records = expense_obj.browse(source_doc_ids)
        for record in records:
            currency_id = record.currency_id.id

            # 调用原回写逻辑
            if time =='save':
                for line in record.line1_expense_ids:
                    unpush_amount = line.unpush_amount
                    if unpush_amount and reverse_amount:
                        if float_compare(unpush_amount, reverse_amount, currency_id) < 0:
                            line.push_amount = unpush_amount
                            reverse_amount = self._round(reverse_amount - unpush_amount, currency_id)   
                        else:
                            line.push_amount = self._round(reverse_amount + line.push_amount, currency_id)
                            reverse_amount = 0
            elif time =='delete':
                for line in reversed(record.line1_expense_ids):
                    push_amount = line.push_amount
                    if push_amount and reverse_amount:
                        if float_compare(push_amount, reverse_amount, currency_id) < 0:
                            reverse_amount = self._round(reverse_amount - push_amount, currency_id)
                            line.push_amount = 0
                        else:
                            line.push_amount = self._round(push_amount - reverse_amount, currency_id)
                            reverse_amount = 0
            
    @skip_if(lambda self, source_model_key, source_doc_ids, target_doc, time, amount: source_model_key != 'er.expense')
    def on_update_er_pay_amount_and_recon_amount(self, source_model_key, source_doc_ids, target_doc, time, amount):
        """
        付款单审核/反审核时，更新费用报销单费用明细表已付款金额
        @param source_model_key: 来源单据模型
        @param source_doc_ids: 来源单据id列表(目前只有一个)
        @param target_doc: 目标单据（付款单）
        @param time: reverse（反写）或者reverse_cancel（取消反写）
        @param amount: 待更新的金额
        """
        er_expense_obj = self.env['er.expense']
        if source_doc_ids:
            er_expense = er_expense_obj.browse(source_doc_ids[ID_FIRST_INDEX])
            # 更新费用费报销单费用明细已付款金额
            recon_vals = []
            self._update_pay_amount_and_recon_vals(er_expense, time, amount, recon_vals)
            # 查询对应的自动生成的其他应付单
            link_obj = self.env['studio.botp.record']
            other_payable_id = link_obj.search([
                ('source_model_key', '=', source_model_key),
                ('source_doc_id', '=', er_expense.id),
                ('target_model_key', '=', 'ap.other.payable'),
                ('record_type', '=', 'audit_auto_generate'),
                ('delete_state', '=', False)
            ], limit=1).target_doc_id
            other_payable_obj = self.env['ap.other.payable']
            other_payable = other_payable_obj.browse(other_payable_id)
            # 更新对应其他应付单明细已结算金额
            self._update_other_payable_sett_amount(other_payable, time, amount, recon_vals)
            # 创建/删除核销记录（费用报销单-其他应付单-付款单）
            if time == 'reverse':
                # 创建核销记录
                self._create_recon_record(er_expense, other_payable, target_doc, recon_vals)
            else:
                # 删除核销记录
                self._delete_recon_record(target_doc)

    def _update_pay_amount_and_recon_vals(self, record, time, amount, recon_vals):
        """
        更新已付款金额
        @param record: 费用报销单
        @param time: 反写/取消反写
        @param amount: 待更新的付款金额
        @param recon_vals: 核销记录数据
        """
        currency_id = record.currency_id.id        
        if time == 'reverse':
            biz_date = record.apply_date
            biz_doc_id = record.id
            doc_num = record.number
            document_type_id = record.document_type_id.id
            # 反写时，累加已付款金额
            for line in record.line1_expense_ids:
                if not self._is_zero(amount, currency_id):
                    # 如果amount不是0，则依次更新费用明细行已付款金额
                    unpay_amount = line.unpay_amount
                    if not self._is_zero(unpay_amount, currency_id):
                        # 如果未付款金额不是0，则更新此费用明细行已付款金额
                        if self._float_compare(unpay_amount, amount, currency_id) <= 0:
                            # 如果未付款金额小于等于待更新的金额，则此行已付款金额=未付款金额
                            line.pay_amount = self._round(line.pay_amount + unpay_amount, currency_id)
                            curr_recon_amount = unpay_amount
                            amount = self._round(amount - unpay_amount, currency_id)
                        else:
                            # 如果未付款金额大于待更新的金额，则此行已付款金额=当前已付款金额 + 待更新的金额
                            line.pay_amount = self._round(line.pay_amount + amount, currency_id)
                            curr_recon_amount = amount
                            amount = 0
                        # 更新核销记录的数据列表
                        recon_vals.append({
                            'biz_date': biz_date,  # 业务日期(申请日期)
                            'biz_doc_id': biz_doc_id,  # 业务单据id
                            'doc_num': doc_num,  # 单据编号
                            'document_type_id': document_type_id,  # 单据类型
                            'exp_item_id': line.exp_item_id.id,  # 费用项目
                            'recon_amount': curr_recon_amount,  # 本次核销金额
                            'reconed_amount': line.recon_amount,  # 已核销金额
                            'unrecon_amount': line.unrecon_amount,  # 未核销金额
                        })
                else:
                    # 如果待更新的金额（amount）变为0，则跳出循环
                    break
        elif time == 'reverse_cancel':
            # 取消反写时，减少已付款金额
            for line in reversed(record.line1_expense_ids):
                if not self._is_zero(amount, currency_id):
                    # 如果amount不是0，则依次更新费用明细行已付款金额
                    pay_amount = line.pay_amount
                    if not self._is_zero(pay_amount, currency_id):
                        # 如果已付款金额不是0，则更新此费用明细行已付款金额
                        if self._float_compare(pay_amount, amount, currency_id) <= 0:
                            # 如果已付款金额小于等于待更新的金额，则已付款金额=0
                            line.pay_amount = 0
                            amount = self._round(amount - pay_amount, currency_id)
                        else:
                            # 如果已付款金额大于待更新的金额，则已付款金额=当前已付款金额 - 待更新的金额
                            line.pay_amount = self._round(pay_amount - amount, currency_id)
                            amount = 0
                else:
                    # 如果待更新的金额（amount）变为0，则跳出循环
                    break

    def _update_other_payable_sett_amount(self, record, time, amount, recon_vals):
        """
        更新其他应付单的已结算金额
        @param record: 其他应付单
        @param time: 反写/取消反写
        @param amount: 待更新的付款金额
        @param recon_vals: 核销记录数据
        """
        currency_id = record.currency_id.id
        if time == 'reverse':
            biz_date = record.biz_date
            biz_doc_id = record.id
            doc_num = record.number
            document_type_id = record.document_type_id.id

            # 反写时，累加已结算金额
            for line in record.line_ids:
                if not self._is_zero(amount, currency_id):
                    # 如果amount不是0，则依次更新明细行已结算金额
                    unrecon_amount = line.unrecon_amount
                    if not self._is_zero(unrecon_amount, currency_id):
                        # 如果未核销金额不是0，则更新此明细行已结算金额
                        if self._float_compare(unrecon_amount, amount, currency_id) <= 0:
                            # 如果未核销金额小于等于待更新的金额，则此行已结算金额=未核销金额
                            line.sett_amount = self._round(line.sett_amount + unrecon_amount, currency_id)
                            curr_recon_amount = unrecon_amount
                            amount = self._round(amount - unrecon_amount, currency_id)
                        else:
                            # 如果未核销金额大于待更新的金额，则此行已结算金额=当前已结算金额 + 待更新的金额
                            line.sett_amount = self._round(line.sett_amount + amount, currency_id)
                            curr_recon_amount = amount
                            amount = 0
                        # 更新核销记录的数据列表
                        recon_vals.append({
                            'biz_date': biz_date,  # 业务日期(申请日期)
                            'biz_doc_id': biz_doc_id,  # 业务单据id
                            'doc_num': doc_num,  # 单据编号
                            'document_type_id': document_type_id,  # 单据类型
                            'exp_item_id': line.exp_item_id.id,  # 费用项目
                            'recon_amount': curr_recon_amount,  # 本次核销金额
                            'reconed_amount': line.sett_amount,  # 已核销(结算)金额
                            'unrecon_amount': line.unrecon_amount,  # 未核销金额
                        })
                else:
                    # 如果待更新的金额（amount）变为0，则跳出循环
                    break
        elif time == 'reverse_cancel':
            # 取消反写时，减少已结算金额
            for line in reversed(record.line_ids):
                if not self._is_zero(amount, currency_id):
                    # 如果amount不是0，则依次更新费用明细行已结算金额
                    sett_amount = line.sett_amount
                    if not self._is_zero(sett_amount, currency_id):
                        # 如果已结算金额不是0，则更新此明细行已结算金额
                        if self._float_compare(sett_amount, amount, currency_id) <= 0:
                            # 如果已结算金额小于等于待更新的金额，则结算款金额=0
                            line.sett_amount = 0
                            amount = self._round(amount - sett_amount, currency_id)
                        else:
                            # 如果已结算金额大于待更新的金额，则已结算金额=当前结算款金额 - 待更新的金额
                            line.sett_amount = self._round(sett_amount - amount, currency_id)
                            amount = 0
                else:
                    # 如果待更新的金额（amount）变为0，则跳出循环
                    break

    def _create_recon_record(self, er_expense, other_payable, payable_bill, recon_vals):
        """
        创建核销记录（目前不会合单，但考虑存在合单的情况）
        @param er_expenses: 费用报销单
        @param other_payable: 其他应付单
        @param payable_bill: 付款单
        @param recon_vals: 核销记录数据@
        """
        # 往来单位（类型）
        contact_dept = er_expense.contact_dept
        contact_dept_type = contact_dept._name if contact_dept else None
        contact_dept_str = '%s,%s' % (contact_dept_type, contact_dept.id) if contact_dept else None
        # 公共的数据
        base_data = {
            'recon_date': fields.Date.today(),  # 核销日期
            'recon_uid': self.env.uid,  # 核销人
            'recon_type': 'auto',  # 核销类型：自动核销
            'exp_org_id': er_expense.exp_org_id.id,  # 费用承担组织
            'pay_org_id': er_expense.pay_org_id.id,  # 付款组织
            'currency_id': er_expense.currency_id.id,  # 币别
            'contact_dept_type': contact_dept_type,  # 往来单位类型
            'contact_dept': contact_dept_str,  # 往来单位
            'project_id': er_expense.project_id.id,  # 项目
            'settle_type_id': er_expense.settle_type_id.id,  # 结算方式
        }
        for recon_val in recon_vals:
            recon_val.update(base_data)

        payable_bill_data = {
            'biz_date': payable_bill.biz_date,  # 业务日期(申请日期)
            'biz_doc_id': payable_bill.id,  # 业务单据id
            'doc_num': payable_bill.number,  # 单据编号
            'document_type_id': payable_bill.document_type_id.id,  # 单据类型
        }
        for line in payable_bill.line_ids:
            recon_vals.append({
                'payment_purpose_id': line.pay_type_id.id,  # 收付款用途
                'recon_amount': line.pay_amount,  # 本次核销金额
                'reconed_amount': line.pay_amount,  # 已核销金额
                'unrecon_amount': 0,  # 未核销金额
                **payable_bill_data,
                **base_data
            })

        # 创建核销记录
        recon_record_obj = self.env['er.recon.record']
        recon_record_obj.create(recon_vals)

        # 判断参数启用应付调汇是否启用
        module_obj = self.env['ir.module.module']
        module_id = module_obj.search([('name', '=', 'ps_ap')])
        sys_biz_params_obj = self.env['sys.business.params']

        param_result = sys_biz_params_obj.p_get_params(module_id=module_id.id, org_id=other_payable.sett_org_id.id, key='is_enable_ap_exchange_revaluation')
        if param_result and len(param_result) == 1:
            is_enable_ap_exchange_revaluation = param_result[0].get('value', False)
            if is_enable_ap_exchange_revaluation == 'False':
                return
        
        
        ap_exchange_revaluation_obj = self.env['ap.exchange.revaluation']
        recon_date = datetime.today()
        contact_dept_top = self._get_reference_to_str(other_payable.contact_dept)
        contact_dept_bot = self._get_reference_to_str(payable_bill.contact_dept)
        recon_amount_bot = payable_bill.pay_amount # 目标单原币金额
        
        recon_amount_top = recon_amount_bot  # 源单原币金额
        recon_amount_top_lc = recon_amount_bot * other_payable.curr_rate  # 源单本位币金额 
        recon_amount_bot_lc = payable_bill.pay_amount_local  # 目标单本位币金额
        exchange_amount_lc = recon_amount_bot_lc - recon_amount_top_lc # 调汇金额
        document_type_id = self.env.ref('ps_ap.mdm_document_type_ap_exchange_revaluation')  # 单据类型 应付调汇
        is_check = False
        # 判断是否进行调汇单的处理
        if other_payable.local_currency_id.id == other_payable.local_currency_id.id and other_payable.local_currency_id.id != other_payable.currency_id.id and other_payable.local_currency_id.id != other_payable.currency_id.id and self.env['mdm.currency'].p_amount_float_compare(abs(recon_amount_top_lc), abs(recon_amount_bot_lc), other_payable.local_currency_id.id) != 0:
            is_check = True

        if is_check:
            er_record = ap_exchange_revaluation_obj.create(
                {
                'biz_date': recon_date,  # 业务日期
                'biz_org_id': other_payable.sett_org_id.id,  # 业务组织
                'contact_dept': contact_dept_top,  # 往来单位
                'currency_id': other_payable.currency_id.id,  # 币别
                'local_currency_id': other_payable.local_currency_id.id,  # 本位币币别
                'source_amount': recon_amount_top,  # 源单原币金额
                'target_amount': recon_amount_bot,  # 目标单原币金额
                'source_amount_lc': recon_amount_top_lc,  # 源单本位币金额
                'target_amount_lc': recon_amount_bot_lc,  # 目标单本位币金额
                'exchange_amount_lc': exchange_amount_lc,  # 调汇金额
                'document_type_id': document_type_id.id,  # 单据类型
                'source_doc_ids' : payable_bill.id,
                'source_model_key': payable_bill._name,
                'line1_ids': [(0, 0, {
                    'src_doc_type_id': other_payable.document_type_id.name,  # 源单类型
                    'src_number': other_payable.number,  # 单据编号
                    'sett_org_id': other_payable.sett_org_id.id,  # 结算组织
                    'contact_dept': contact_dept_top,  # 往来单位
                    'currency_id': other_payable.currency_id.id,  # 币别
                    'curr_rate': other_payable.curr_rate,  # 汇率
                    'recon_amount': recon_amount_top,  # 核销原币金额
                    'recon_amount_lc': recon_amount_top_lc,  # 核销本位币金额
                })],
                'line2_ids': [(0, 0, {
                    'target_doc_type_id': payable_bill.document_type_id.name,  # 目标单类型
                    'target_number': payable_bill.number,   # 单据编号
                    'recpay_org_id': payable_bill.pay_org_id.id,  # 收付组织
                    'contact_dept': contact_dept_bot,  # 往来单位
                    'currency_id': payable_bill.sett_curr_id.id,  # 币别
                    'curr_rate': payable_bill.sett_curr_rate,  # 汇率
                    'recon_amount': recon_amount_bot,  # 核销原币金额
                    'recon_amount_lc': recon_amount_bot_lc,  # 核销本位币金额
                })],
                }
            )

    def _get_reference_to_str(self, reference):
        """
        将 reference 字段转为 string
        """
        contect_model = str(reference).split('(')[0]
        contect_temp = str(reference).split('(')[1]
        cotect_id = contect_temp.split(',')[0]
        return '%s,%s' % (contect_model, cotect_id)

    def _delete_recon_record(self, target_doc):
        """
        删除核销记录
        @param target_doc: 目标单对象（付款单）
        """
        recon_record_obj = self.env['er.recon.record']
        # 根据目标单，查询核销记录number
        recon_record_number = recon_record_obj.search([
            ('biz_doc_model', '=', target_doc._name),
            ('biz_doc_id', '=', target_doc.id),
            ('recon_type', '=', 'auto')
        ], limit=1).number
        # 根据number删除核销记录
        recon_record_obj.search([
            ('number', '=', recon_record_number)
        ]).unlink()

        ap_exchange_revaluation_obj = self.env['ap.exchange.revaluation']
        ap_exchange_revaluation_obj.search([('source_doc_ids', '=', target_doc.id),
                ('source_model_key', '=', target_doc._name,)]).unlink()
    
    def _round(self, value, currency_id):
        """
        根据currency_id对value进行精度格式化
        """
        mdm_currency_obj = self.env['mdm.currency']
        return mdm_currency_obj.p_amount_float_round(value, currency_id)

    def _is_zero(self, value, currency_id):
        """
        返回是否为0的布尔值
        @params value: float
        @params currency_id: int
        @rtype boolean
        """
        currency_obj = self.env['mdm.currency']
        return currency_obj.p_amount_float_is_zero(value, currency_id)

    def _float_compare(self, value1, value2, currency_id):
        """
        返回两个数值的比较结果
        @params value1: float
        @params value2: float
        @params currency_id: int
        @rtype float_compare
        @return (resp.) -1, 0 or 1, if ``value1`` is (resp.) lower than,
           equal to, or greater than ``value2``, at the given precision.
        """
        currency_obj = self.env['mdm.currency']
        return currency_obj.p_amount_float_compare(value1, value2, currency_id)