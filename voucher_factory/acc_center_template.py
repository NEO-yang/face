@sys_ele_ctrl()
    def svc_run_forbid(self):
        """
        修改状态 start --> forbid
        """
        lines_info = []  # 提示信息列表
        operation = _('Forbid: %s') # 禁用: %s
        log_opt = _('Forbid')
        for rec in self:
            state = FAILED_STATE
            level = LogLevel.ERROR
            if rec.delete_state == 'normal' and rec.forbid_state == 'normal':
                template = self.env['acc.center.voucher.generation.line1'].search([('template_id', '=', rec.id)])
                if template:
                    acct_book_ids = template.parent_id.acct_book_id
                    book_name = [acct_book_id.name for acct_book_id in acct_book_ids]
                    info = _('The selected voucher scheme has been selected by account book: %s , please disable it after removing the selection relationship in the voucher factory.') % book_name
                else:
                    rec.write({'forbid_state': 'forbid'})
                    state = SUCCESS_STATE
                    level = LogLevel.INFO
                    info = _('Successfully forbid')  # 禁用成功
            elif rec.delete_state == 'normal' and rec.forbid_state == 'forbid':
                info = _('The current voucher scheme has been disabled')  # 当前凭证方案已经被禁用
            else:
                info = _('Forbid failure')  # 禁用失败
            lines_info.append(LineInfo(operation=operation % rec.name, state=state, info=info))
            self.biz_logs.append(BizLogItem(cls=rec, operation=log_opt, message=info,  level=level, category=LogCategory.OPERATE, tenant_id=rec.tenant_id))
        return InfoWindow.info(lines_info)
