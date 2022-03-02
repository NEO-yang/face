################################  约束方法区  start  ################################

    @api.constrains('is_enable_pay_process_paid', 'is_generate_payment_audit')
    def _check_value(self):
        if self.is_enable_pay_process_paid and self.is_generate_payment_audit:
            # 报销支付启用付款申请流程时，不允许报销单审核时自动生成付款单
            raise ValidationError(_('The amount of a cash transaction cannot be 0.'))

    ################################  约束方法区  end   ################################