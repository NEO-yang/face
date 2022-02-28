# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Student(models.Model):
    _name = 'training.student'
    _description = 'Student'

    name = fields.Char('Name')
    age = fields.Integer('Age')
    sex = fields.Selection(selection=[('male', 'Male'), ('female', 'Female')], string='Sex',
                           default='male', required=True)
    grade = fields.Selection(selection=[('freshman', 'Freshman'),
                                        ('sophomore', 'Sophomore'),
                                        ('junior', 'Junior'),
                                        ('senior', 'Senior')],
                             string='Grade', default='freshman', required=True)
    cclass = fields.Selection(selection=[('1', '1'), ('2', '2'), ('3', '3'), ('4', '4')], string='Class',
                              default='1', required=True)
    address = fields.Text('Address')
    lesson_ids = fields.Many2many('training.lesson', 'student_lesson_rel', 'student_id', 'lesson_id', string='Lessons',
                                  domain="[('state', '=', 'audited')]", ondelete='restrict')


