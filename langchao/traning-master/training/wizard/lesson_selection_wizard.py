# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.tools import float_compare
from odoo.exceptions import ValidationError


class LessonSelection(models.TransientModel):
    _name = 'training.lesson.selection.wizard'
    _description = 'Lesson Selection'

    student_id = fields.Many2one('training.student', string='Student', required=True)
    lesson_ids = fields.Many2many('training.lesson', 'lesson_selection_rel', 'selection_id', 'lesson_id', string='Lessons')
    total = fields.Float('Total Credits', readonly=True, compute='_compute_total')

    @api.depends('lesson_ids')
    def _compute_total(self):
        total = 0.0
        for lesson in self.lesson_ids:
            total += lesson.credit
        self.total = total

    def button_confirm(self):
        if float_compare(self.total, 20.0, precision_digits=2) == -1 \
                or float_compare(30.0, self.total, precision_digits=2) == -1:
            raise ValidationError('The total credits of the lessons must be greater than 20 and less than 30')
        else:
            self.student_id.write({
                'lesson_ids': [(6, 0, self.lesson_ids.ids)]
            })

            return {
                'type': 'ir.actions.act_window',
                'res_model': 'training.student',
                'view_mode': 'form',
                'res_id': self.student_id.id,
                'target': 'main',
                'view_id': self.env.ref('training.view_training_student_form').id
            }

