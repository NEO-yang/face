# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.tools import float_compare


class Lesson(models.Model):
    _name = 'training.lesson'
    _description = 'Lesson'

    name = fields.Char('Name', required=True)
    credit = fields.Float('Credit')
    period = fields.Integer('Period')
    category = fields.Selection(selection=[('required', 'Required'), ('not_required', 'Not Required')],
                                string='Category', default='not_required')

    subject_id = fields.Many2one('training.subject', string='Subject', ondelete='cascade')
    teacher_ids = fields.Many2many('training.teacher', 'teacher_lesson_rel', 'lesson_id', 'teacher_id',
                                   string='Teachers')
    student_ids = fields.Many2many('training.student', 'student_lesson_rel', 'lesson_id', 'student_id',
                                   string='Students')

    state = fields.Selection(selection=[('unaudited', 'UnAudited'), ('audited', 'Audited')],
                             default='unaudited', string='State')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'The lesson name must be unique !')
    ]

    def button_audit(self):
        self.state = 'audited'

    @api.onchange('credit', 'period')
    def onchange_category(self):
        """
        如果学分大于5分或者课时大于32学时，则将其种类置为必修课
        """
        if float_compare(self.credit, 5.0, precision_digits=2) != -1 or self.period >= 32:
            self.category = 'required'
        else:
            self.category = 'not_required'

