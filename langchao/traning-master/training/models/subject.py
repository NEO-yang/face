# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Subject(models.Model):
    _name = 'training.subject'
    _description = 'Subject'

    name = fields.Char('Name', required=True)
    teacher_ids = fields.Many2many('training.teacher', 'teacher_subject_rel', 'subject_id', 'teacher_id',
                                   string='Teachers')
    lesson_ids = fields.One2many('training.lesson', 'subject_id', string='Lessons')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'The subject name must be unique !')
    ]

