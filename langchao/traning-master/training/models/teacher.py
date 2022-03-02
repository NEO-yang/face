# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Teacher(models.Model):
    _name = 'training.teacher'
    _description = 'Teacher'

    name = fields.Char('Name', required=True)
    age = fields.Integer('Age')
    sex = fields.Selection(selection=[('male', 'Male'), ('female', 'Female')], string='Sex',
                           default='male', required=True)
    title = fields.Selection(selection=[('lecturer', 'Lecturer'),
                                        ('ass_professor', 'Associate Professor'),
                                        ('professor', 'Professor')],
                             string='Title', default='lecturer', required=True)
    description = fields.Text('Description')
    subject_ids = fields.Many2many('training.subject', 'teacher_subject_rel', 'teacher_id', 'subject_id',
                                   string='Subjects')
    lesson_ids = fields.Many2many('training.lesson', 'teacher_lesson_rel', 'teacher_id', 'lesson_id', string='Lessons',
                                  domain="[('subject_id', 'in', subject_ids), ('state', '=', 'audited')]")
