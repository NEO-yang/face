# -*- coding: utf-8 -*-
'''
==================================================
@创建人 ：闫化强
@当前维护人 ：冯宇萧
@Desc ：会计日历
==================================================
'''
from odoo import fields, api, models, _
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
import datetime
from odoo.addons.ps_admin.info_window.info_window import InfoWindow, LineInfo, SUCCESS_STATE, FAILED_STATE
from odoo.addons.ps_admin.sys_ele.sys_ele_ctrl import sys_ele_ctrl
from odoo.addons.ps_admin.biz_log.models.biz_log_item import LogCategory, LogLevel, get_check_message
from odoo.addons.ps_admin.biz_log.models.biz_log_item import BizLogItem


class MdmAccountCalendar(models.Model):
    _inherit = 'mdm.account.calendar'
    _order = 'number'

    ################################  default start  ################################

    @api.model
    def _get_default_year(self):
        default_year = datetime.date.today().year
        return default_year

    ################################  default end    ################################

    ################################  字段定义区 start  ################################

    start_date = fields.Date(default=fields.Date.today)
    start_fiscal_year = fields.Char(default=_get_default_year)

    ################################  字段定义区 end    ################################

    ################################  计算方法区 start  ################################

    ################################  计算方法区 end    ################################

    ################################  onchange方法区  start  ################################

    @api.onchange('start_date', 'period_type', 'week_type')
    def _onchange_date_type(self):
        """
        当开始日期、期间类型、周类型改变时，清空子表
        """
        if self.line_ids:
            self.line_ids = [(2, res.id) for res in self.line_ids]

    ################################  onchange方法区  end    ################################

    ################################  约束方法区  start  ################################

    @sys_ele_ctrl()
    @api.constrains('number', 'name')
    def _check_uniqueness_check(self):
        """
        增加编码，名称唯一性校验
        """
        for record in self:
            if self.search_count([('number', '=', record.number), ("delete_state", '=', "normal")]) > 1:
                self.biz_logs.append(BizLogItem(cls=record, operation=_('Save'), checked_type=_(
                    "Unique"),  message=_('Number must be unique!'),  level=LogLevel.ERROR, category=LogCategory.CHECK))
                raise ValidationError(_("Number already exists."))
            if self.search_count([('name', '=', record.name), ("delete_state", '=', "normal")]) > 1:
                self.biz_logs.append(BizLogItem(cls=record, operation=_('Save'),  checked_type=_(
                    "Unique"), message=_('Name must be unique!'),  level=LogLevel.ERROR, category=LogCategory.CHECK))
                raise ValidationError(_("Name already exists."))
            self.biz_logs.append(BizLogItem(cls=record, operation=_('Save'), checked_type=_("Unique"), message=_(
                '[Number],[Name] unique check success!'), level=LogLevel.INFO, category=LogCategory.CHECK))

    @sys_ele_ctrl()
    @api.constrains('start_fiscal_year', 'start_date')
    def _check_calendar_date(self):
        """
        检查起始年度是否符合要求
        起始年度与开始日期必须同属于一个会计年度
        """
        if len(self.start_fiscal_year) != 4:
            self.biz_logs.append(BizLogItem(cls=self, operation=_('Save'), checked_type=_("Mismatch"),  message=_(
                'Fiscal year is not correct!'),  level=LogLevel.ERROR, category=LogCategory.CHECK))
            raise ValidationError(
                _('The fiscal year format is incorrect!'))  # 会计年度格式不正确
        if int(self.start_date.day) >= 28:
            self.biz_logs.append(BizLogItem(cls=self, operation=_('Save'), checked_type=_("Mismatch"),  message=_(
                'Start date can not later than 28!'),  level=LogLevel.ERROR, category=LogCategory.CHECK))
            raise ValidationError(_("date should not be later 28!"))
        if self.start_fiscal_year[:4] != str(self.start_date)[:4]:
            self.biz_logs.append(BizLogItem(cls=self, operation=_('Save'),  checked_type=_("Mismatch"), message=_(
                'Start Year must match with accounting year.'),  level=LogLevel.ERROR, category=LogCategory.CHECK))
            raise ValidationError(
                _("The start year and the start date must belong to the same accounting year."))
        self.biz_logs.append(BizLogItem(cls=self, operation=_('Save'), checked_type=_("Mismatch"), message=_(
            '[Start year],[Start date] match check success!'), level=LogLevel.ERROR, category=LogCategory.CHECK))

    @api.constrains('line_ids')
    def _check_line_date(self):
        """
        手工维护明细行时更新结束日期
        """
        if self.line_ids:
            max_end_date = max([record.end_date for record in self.line_ids])
            self.end_date = max_end_date

    ################################  约束方法区  end    ################################

    ################################  服务器动作区  start  ################################

    @sys_ele_ctrl()
    def pre_action_run_submit(self, opt=None):
        '''
        存在会计期间时，校验状态，不存在会计期间提示需要补充会计期间
        '''
        lines_info = []
        for res in self:
            operation = _('Submit: %s') % res.display_name
            if res.line_ids:
                if (res.state == 'save') and (res.forbid_state == 'normal'):
                    res.state = 'submit'
                    info = _('%s success to Submit!') % res.display_name
                    self.biz_logs.append(BizLogItem(cls=res, operation=_('Submit'), checked_type=_(
                        "Mismatch"), message=_('Submit Success!'), level=LogLevel.INFO, category=LogCategory.CHECK))
                    self.biz_logs.append(BizLogItem(cls=res, operation=_('Submit'), message=_(
                        'Submit Success!'), level=LogLevel.INFO, category=LogCategory.OPERATE))
                    line_info = LineInfo(
                        operation=operation, state=SUCCESS_STATE, info=info)
                else:
                    info = _(
                        '%s failed to submit because it is not on save and unforbidden state!') % res.display_name
                    self.biz_logs.append(BizLogItem(cls=res, operation=_('Submit'), checked_type=_(
                        "Mismatch"), message=_('State is not match!'), level=LogLevel.ERROR, category=LogCategory.CHECK))
                    self.biz_logs.append(BizLogItem(cls=res, operation=_('Submit'), message=_(
                        'State is not match!'), level=LogLevel.ERROR, category=LogCategory.OPERATE))
                    line_info = LineInfo(
                        operation=operation, state=FAILED_STATE, info=info)
            else:
                info = _(
                    '%s faild to Submit ,because it has no accounting periods.') % res.display_name
                self.biz_logs.append(BizLogItem(cls=res, operation=_('Periods Check'), checked_type=_("Mismatch"), message=_(
                    'Please Add accounting periods.'), level=LogLevel.ERROR, category=LogCategory.CHECK))
                self.biz_logs.append(BizLogItem(cls=res, operation=_('Submit'), message=_(
                    'State is not match!'), level=LogLevel.ERROR, category=LogCategory.OPERATE))
                line_info = LineInfo(operation=operation,
                                     state=FAILED_STATE, info=info)
                # raise ValidationError(_('Please  add accounting periods. ')) # 请生成会计期间
            lines_info.append(line_info)
        return InfoWindow.info(lines_info)

    ################################  服务器动作区  end    ################################

    ################################  按钮动作区  start  ################################

    def svc_submit(self):
        return self.action_server_run(opt="submit")

    def svc_submit_cancel(self):
        return self.action_server_run(opt="submit_cancel")

    def svc_audit(self):
        return self.action_server_run(opt="audit")

    def svc_audit_cancel(self):
        return self.action_server_run(opt="audit_cancel", check_ref=True, child_model=['mdm.account.calendar.line1', 'gl.account.book.view'])

    def svc_delete(self):
        return self.action_server_run(opt="delete")

    ################################  按钮动作区  end    ################################

    ################################  私有方法区  start  ################################

    @sys_ele_ctrl()
    def create_periods(self):
        """
        生成会计期间
        :return:
        """
        start_date = self.start_date
        self._create_periods(start_date, self.additional,
                             additional_state=False)

    def _update_line(self, additional_state, line_ids):
        """
        用于更新明细表，在创建或追加状态生成新得明细， 在编辑状态，删除原来数据，重新生成。
        """
        if not self.line_ids or additional_state:
            self.line_ids = line_ids
        elif self.line_ids and not additional_state:
            self.line_ids.unlink()
            self.line_ids = line_ids

    def _create_week(self, start_date, init_year, acct_period, additional_state, w_type, line_ids, record_id):
        """
        用于52，52周的期间生成。
        start_date： 开始日期
        init_year： 初始年
        acct_period： 期间
        additional_state： 追加状态
        w_type： 周类型
        line_ids： 列表，用于存放期间数据
        """
        weeks = int(self.week_type)
        while weeks > 0:
            end_date = start_date + relativedelta(weeks=1, days=-1)

            weeks -= 1
            acct_week = int(self.week_type) - weeks
            # 13,26,39,65%52(下一年的13周)...计算会计季度
            if acct_week % 13 == 0 and acct_week % 52 != 0:
                quarter = acct_week % 52 // 13
            # 52,104(下一年的52周)...计算会计季度
            elif acct_week % 52 == 0 or acct_week == 53:
                quarter = 4
            elif acct_week % 13 != 0 and acct_week != 53:  # 01-12,14-25,...计算会计季度
                quarter = acct_week % 52 // 13 + 1

            acct_period_week = acct_period + acct_week

            add_acct_year = init_year
            max_calendar_year = self.env['mdm.account.calendar.line1'].search(
                [('parent_id', '=', record_id)], order='acct_year desc', limit=1).acct_year
            if max_calendar_year and additional_state:
                add_acct_year = int(max_calendar_year)+1

            line_ids.append((0, 0, {
                'acct_year': init_year if acct_week != 52 and additional_state != True else add_acct_year,
                'acct_period': str(acct_period_week % w_type if acct_period_week % w_type else w_type).zfill(2),
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'acct_quarter': quarter,
            }))
            start_date = end_date + relativedelta(days=1)
        self.end_date = end_date
        self._update_line(additional_state, line_ids)

    def _create_periods(self, start_date, account_year, **additional_state):
        """
        start_date: 开始日期
        account_year: 会计年数
        """
        line_ids = []
        init_year = int(str(start_date)[:4])
        additional_state = additional_state.get("additional_state")
        if additional_state:
            acct_period = max([int(i.acct_period) for i in self.line_ids.filtered(
                lambda x: not x.is_adjustment)] if self.line_ids else [0])
        else:
            if self.line_ids:
                self.line_ids.unlink()
            acct_period = max([int(i.acct_period) for i in self.line_ids]
                              if self.line_ids else [0])  # 获取最大会计期间

        if self.period_type == 'month':  # 期间类型为月份的创建期间逻辑
            self.end_date = start_date + \
                relativedelta(years=account_year, days=-1)  # 计算结束日期
            month_index = 0
            while start_date < self.end_date:  # 循环产生12个期间
                acct_year = str(init_year + month_index // 12)
                month_index += 1
                end_date = start_date + relativedelta(months=1, days=-1)

                if end_date > self.end_date:
                    end_date = self.end_date
                acct_period += 1
                # 03,06,09,15%12(下一年的03期间)...计算会计季度
                if acct_period % 3 == 0 and acct_period % 12 != 0:
                    quarter = acct_period % 12 // 3
                elif acct_period % 12 == 0:  # 12,24(下一年的12)...计算会计季度
                    quarter = 4
                # 01,02,04,05,...,13%12(下一年的01期间)...计算会计季度
                elif acct_period % 3 != 0:
                    quarter = acct_period % 12 // 3 + 1
                line_ids.append((0, 0, {
                    'acct_year': acct_year,
                    'acct_period': str(acct_period % 12 if acct_period % 12 else 12).zfill(2),
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d'),
                    'acct_quarter': quarter,
                }))
                start_date += relativedelta(months=1)
            self._update_line(additional_state, line_ids)

        elif self.period_type == 'week':  # 期间类型为月份的创建期间逻辑
            if self.week_type == '52':  # 一年52周的计算方法
                w_type = 52
                self._create_week(start_date, init_year, acct_period,
                                  additional_state, w_type, line_ids, self.id)

            elif self.week_type == '53':  # 一年53周的计算方法
                w_type = 53
                self._create_week(start_date, init_year, acct_period,
                                  additional_state, w_type, line_ids, self.id)

            elif self.week_type == '445':
                """
                445方式：一年中，4个季度，每个季度包含3个会计期间，期间长度分别是4周、4周和5周。
                开始日期起4周为第一个会计期间，5-8周为第二个会计期间，9-12周为第三个会计期间，
                这三个会计期间所在季度为第一季度；
                每次追加期间为一年：445*4；
                """

                add_acct_year = init_year
                max_calendar_year = self.env['mdm.account.calendar.line1'].search(
                    [('parent_id', '=', self.id)], order='acct_year desc', limit=1).acct_year
                if max_calendar_year and additional_state:
                    add_acct_year = int(max_calendar_year)+1

                quarter, period, acct_period = 0, 0, 0
                while quarter < 4:
                    for i in [4, 4, 5]:
                        period += 1
                        end_date = start_date + relativedelta(weeks=i, days=-1)
                        if additional_state and acct_period == '12':
                            init_year = int(str(start_date)[:4]) + 1

                        line_ids.append((0, 0, {
                            'acct_year': add_acct_year,
                            'acct_period': str(acct_period + period).zfill(2),
                            'start_date': start_date.strftime('%Y-%m-%d'),
                            'end_date': end_date.strftime('%Y-%m-%d'),
                            'acct_quarter': quarter + 1,
                        }))
                        start_date = end_date + relativedelta(days=1)
                    quarter += 1
                self.end_date = end_date
                self._update_line(additional_state, line_ids)

    @sys_ele_ctrl()
    def additional_peroids(self):
        """
        追加会计期间
        :return:
        """
        if self.end_date:
            start_date = self.end_date + relativedelta(days=1)
            self.end_date = self.end_date + \
                relativedelta(years=self.additional, days=-1)
            self._create_periods(
                start_date, self.additional, additional_state=True)
        else:
            self.biz_logs.append(BizLogItem(cls=self, operation=_('Add Periods'), checked_type=_(
                "Mismatch"), message=_('End Date Error!'), level=LogLevel.ERROR, category=LogCategory.CHECK))
            self.biz_logs.append(BizLogItem(cls=self, operation=_('Add Periods'), message=_(
                'End Date Error!'), level=LogLevel.ERROR, category=LogCategory.OPERATE))
            raise ValidationError(_("Please check end date!"))

    ################################  私有方法区  end    ################################

    ################################  公共方法区  start  ################################

    @api.model
    def get_all_period(self):
        '''
        获取所有期间
        :return:
        '''
        ids_data = []
        # 暂时返回空值
        return ids_data

    def get_period_by_biz_date(self, biz_date, calendar_id):
        domain = [('start_date', '<=', biz_date),
                  ('end_date', '>=', biz_date),
                  ('parent_id', '=', calendar_id)]
        current_periods = self.env['mdm.account.calendar.line1'].search(domain)
        return current_periods

    def get_period_by_biz_date_book(self, biz_date, acct_book_id):
        book = self.env['mdm.account.book'].browse(acct_book_id)
        if book:
            return self.get_period_by_biz_date(biz_date, book.calendar_id.id)
        else:
            return None

    def p_get_next_period_by_date_calendar(self, biz_date, calendar_id):
        '''
        return:若该日期在当前日历存在下一期间，则返回下一期间对象，否则返回false
        '''
        next_period = self.env['mdm.account.calendar.line1'].search([('parent_id', '=', calendar_id.id), (
            'is_adjustment', '=', False), ('start_date', '>', biz_date)], order='start_date', limit=1)
        return next_period if next_period else False

    ################################  公共方法区  end    ################################

    ################################  覆盖基类方法区  start  ################################

    @sys_ele_ctrl()
    def unlink(self):
        """
        增加逻辑删除
        """
        for record in self:
            if record.state in ['temporary', 'save']:
                record.delete_state = 'delete'
            else:
                raise ValidationError(
                    _("The period is not on temporary or save state"))

    ################################  覆盖基类方法区  end    ################################

    ################################  其他方法区  start  ################################

    def _create_periods(self, start_date, account_year, **additional_state):
        """
        start_date: 开始日期
        account_year: 会计年数
        """
        line_ids = []
        init_year = int(str(start_date)[:4])
        additional_state = additional_state.get("additional_state")
        if additional_state:
            acct_period = max([int(i.acct_period) for i in self.line_ids.filtered(
                lambda x: not x.is_adjustment)] if self.line_ids else [0])
        else:
            if self.line_ids:
                self.line_ids.unlink()
            acct_period = max([int(i.acct_period) for i in self.line_ids]
                              if self.line_ids else [0])  # 获取最大会计期间

        if self.period_type == 'month':  # 期间类型为月份的创建期间逻辑
            self.end_date = start_date + \
                relativedelta(years=account_year, days=-1)  # 计算结束日期
            month_index = 0
            while start_date < self.end_date:  # 循环产生12个期间
                acct_year = str(init_year + month_index // 12)
                month_index += 1
                end_date = start_date + relativedelta(months=1, days=-1)

                if end_date > self.end_date:
                    end_date = self.end_date
                acct_period += 1
                # 03,06,09,15%12(下一年的03期间)...计算会计季度
                if acct_period % 3 == 0 and acct_period % 12 != 0:
                    quarter = acct_period % 12 // 3
                elif acct_period % 12 == 0:  # 12,24(下一年的12)...计算会计季度
                    quarter = 4
                # 01,02,04,05,...,13%12(下一年的01期间)...计算会计季度
                elif acct_period % 3 != 0:
                    quarter = acct_period % 12 // 3 + 1
                line_ids.append((0, 0, {
                    'acct_year': acct_year,
                    'acct_period': str(acct_period % 12 if acct_period % 12 else 12).zfill(2),
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d'),
                    'acct_quarter': quarter,
                }))
                start_date += relativedelta(months=1)
            self._update_line(additional_state, line_ids)

        elif self.period_type == 'week':  # 期间类型为月份的创建期间逻辑
            if self.week_type == '52':  # 一年52周的计算方法
                w_type = 52
                self._create_week(start_date, init_year, acct_period,
                                  additional_state, w_type, line_ids, self.id)

            elif self.week_type == '53':  # 一年53周的计算方法
                w_type = 53
                self._create_week(start_date, init_year, acct_period,
                                  additional_state, w_type, line_ids, self.id)

            elif self.week_type == '445':
                """
                445方式：一年中，4个季度，每个季度包含3个会计期间，期间长度分别是4周、4周和5周。
                开始日期起4周为第一个会计期间，5-8周为第二个会计期间，9-12周为第三个会计期间，
                这三个会计期间所在季度为第一季度；
                每次追加期间为一年：445*4；
                """

                add_acct_year = init_year
                max_calendar_year = self.env['mdm.account.calendar.line1'].search(
                    [('parent_id', '=', self.id)], order='acct_year desc', limit=1).acct_year
                if max_calendar_year and additional_state:
                    add_acct_year = int(max_calendar_year)+1

                quarter, period, acct_period = 0, 0, 0
                while quarter < 4:
                    for i in [4, 4, 5]:
                        period += 1
                        end_date = start_date + relativedelta(weeks=i, days=-1)
                        if additional_state and acct_period == '12':
                            init_year = int(str(start_date)[:4]) + 1

                        line_ids.append((0, 0, {
                            'acct_year': add_acct_year,
                            'acct_period': str(acct_period + period).zfill(2),
                            'start_date': start_date.strftime('%Y-%m-%d'),
                            'end_date': end_date.strftime('%Y-%m-%d'),
                            'acct_quarter': quarter + 1,
                        }))
                        start_date = end_date + relativedelta(days=1)
                    quarter += 1
                self.end_date = end_date
                self._update_line(additional_state, line_ids)

    def _create_week(self, start_date, init_year, acct_period, additional_state, w_type, line_ids, record_id):
        """
        用于52，52周的期间生成。
        start_date： 开始日期
        init_year： 初始年
        acct_period： 期间
        additional_state： 追加状态
        w_type： 周类型
        line_ids： 列表，用于存放期间数据
        """
        weeks = int(self.week_type)
        while weeks > 0:
            end_date = start_date + relativedelta(weeks=1, days=-1)

            weeks -= 1
            acct_week = int(self.week_type) - weeks
            # 13,26,39,65%52(下一年的13周)...计算会计季度
            if acct_week % 13 == 0 and acct_week % 52 != 0:
                quarter = acct_week % 52 // 13
            # 52,104(下一年的52周)...计算会计季度
            elif acct_week % 52 == 0 or acct_week == 53:
                quarter = 4
            elif acct_week % 13 != 0 and acct_week != 53:  # 01-12,14-25,...计算会计季度
                quarter = acct_week % 52 // 13 + 1

            acct_period_week = acct_period + acct_week

            add_acct_year = init_year
            max_calendar_year = self.env['mdm.account.calendar.line1'].search(
                [('parent_id', '=', record_id)], order='acct_year desc', limit=1).acct_year
            if max_calendar_year and additional_state:
                add_acct_year = int(max_calendar_year)+1

            line_ids.append((0, 0, {
                'acct_year': init_year if acct_week != 52 and additional_state != True else add_acct_year,
                'acct_period': str(acct_period_week % w_type if acct_period_week % w_type else w_type).zfill(2),
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'acct_quarter': quarter,
            }))
            start_date = end_date + relativedelta(days=1)
        self.end_date = end_date
        self._update_line(additional_state, line_ids)

    def _update_line(self, additional_state, line_ids):
        """
        用于更新明细表，在创建或追加状态生成新得明细， 在编辑状态，删除原来数据，重新生成。
        """
        if not self.line_ids or additional_state:
            self.line_ids = line_ids
        elif self.line_ids and not additional_state:
            self.line_ids.unlink()
            self.line_ids = line_ids

    @api.model
    def get_all_period(self):
        '''
        获取所有期间
        :return:
        '''
        ids_data = []
        # 暂时返回空值
        return ids_data

    def get_period_by_biz_date(self, biz_date, calendar_id):
        domain = [('start_date', '<=', biz_date),
                  ('end_date', '>=', biz_date),
                  ('parent_id', '=', calendar_id)]
        current_periods = self.env['mdm.account.calendar.line1'].search(domain)
        return current_periods

    def get_period_by_biz_date_book(self, biz_date, acct_book_id):
        book = self.env['mdm.account.book'].browse(acct_book_id)
        if book:
            return self.get_period_by_biz_date(biz_date, book.calendar_id.id)
        else:
            return None

    ################################  其他方法区  end    ################################
