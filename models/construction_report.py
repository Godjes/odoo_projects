from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ConstructionReport(models.Model):
    _name = 'construction.report'
    _description = 'Отчет о проделанной работе'
    _inherit = ['mail.thread',]

    date = fields.Date(
        'Дата отчета',
        default=fields.Date.today()
    )
    responsible_user_id = fields.Many2one(
        'res.users',
        string='Ответственный',
        default=lambda self: self.env.user
    )
    weather_conditions = fields.Selection([
        ('sunny', 'Ясно'),
        ('partly_cloudy', 'Пасмурно'),
        ('rain', 'Дождь'),
        ('snow', 'Снег'),
        ('fog', 'Туман'),
    ], string='Погодные условия')

    customer = fields.Char('Заказчик')
    work_line_ids = fields.One2many(
        'construction.report.lines',
        'report_id'
    )
    stage_id = fields.Many2one(
        'construction.report.stage',
        default=lambda self:
        self.env.ref('construction.stage_new'),
        tracking=True
    )

    def action_submit_for_approval(self):
        review_stage = self.env.ref('construction.stage_review')
        self.write({'stage_id': review_stage.id})

    def action_approve_report(self):
        approved_stage = self.env.ref('construction.stage_approved')
        self.write({'stage_id': approved_stage.id})

    @api.constrains('work_line_ids')
    def _check_time_intervals(self):
        """
        Валидация для правильного заполнения времени работ
        """
        for rec in self:
            time_slots = [0] * 24 * 60
            total_time = 0

            for work in rec.work_line_ids:
                if work.time_from < 0.0 or work.time_to > 24.0:
                    raise ValidationError(
                        "Время от и время до должны быть в диапазоне "
                        "от 0.0 до 24.0"
                    )

                if work.time_from >= work.time_to:
                    raise ValidationError(
                        "Время начала работы должно быть меньше "
                        "времени окончания работы"
                    )

                start_minutes = int(work.time_from * 60)
                end_minutes = int(work.time_to * 60)

                for minute in range(start_minutes, end_minutes):
                    if time_slots[minute] != 0:
                        raise ValidationError(
                            "Пересечение временных интервалов не допускается"
                        )
                    time_slots[minute] = 1

                total_time += (work.time_to - work.time_from) * 60

            if total_time != 24 * 60:
                raise ValidationError(
                    "Суммарное время работы должно быть 24 часа"
                )

    def name_get(self):
        """
        Возвращет название отчета в формате:
        Отчет за (2024-01-01)
        """
        result = []
        for record in self:
            rec_name = "Отчет за (%s) (%s)" % (
                record.date, record.stage_id.name)
            result.append((record.id, rec_name))
        return result


class ConstructionReportLines(models.Model):

    _name = 'construction.report.lines'
    _description = 'Строки заполнения отчета'

    report_id = fields.Many2one(
        'construction.report',
        'Отчёт'
    )
    work_id = fields.Many2one(
        'construction.work',
        'Название работы',
        required=True
    )
    time_from = fields.Float(
        'Время от',
        digits=(2, 1),
        store=True
    )
    time_to = fields.Float(
        'Время до',
        digits=(2, 1),
        store=True
    )
    time_total = fields.Float(
        'Итого часов',
        compute='_compute_time_total',
        store=True)

    work_category_id = fields.Many2one(
        related='work_id.category_id',
        store=True)

    date = fields.Date(related='report_id.date')

    @api.depends('time_from', 'time_to')
    def _compute_time_total(self):
        """Суммарное время выполнения работы"""
        for work in self:
            work.time_total = work.time_to - work.time_from


class ConstructionsWork(models.Model):

    _name = 'construction.work'
    _description = 'Перечень работ'

    name = fields.Char(
        'Наименование работы',
        required=True
    )
    description = fields.Text('Описание работы')
    category_id = fields.Many2one(
        'construction.category',
        string='Категория работы',
    )


class ConstructionReportStage(models.Model):

    _name = 'construction.report.stage'
    _description = 'Этапы отчета'
    _order = 'sequence, name'

    name = fields.Char()
    sequence = fields.Integer()
    fold = fields.Boolean()
    report_state = fields.Selection([
        ('new', 'Новый'),
        ('review', 'На согласовании'),
        ('approved', 'Согласован'),
    ], 'State', default='new')
