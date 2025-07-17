from odoo import models, fields, api, _,exceptions
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class LocalPurchaseRequest(models.Model):
    _name = 'local.purchase.request'
    _description = 'Local Purchase Request'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'analytic.mixin']
    _rec_name = 'reference'
    _order = 'reference desc'

    name = fields.Char(string='PR Name')
    rfq_ids = fields.One2many('local.create.rfq','purchase_request_id', string='RFQs')
    rfq_count = fields.Integer(string='RFQ Count', compute='_compute_rfq_count', store=True)
    reference = fields.Char(string='REFERENCE', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    request_department = fields.Many2one('hr.department', string='Department', store=True, compute='_compute_request_department')
    requested_by = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user)
    approved_by = fields.Many2one('res.users', string='Approved By')
    request_date = fields.Date(string='Request Date', default=fields.Date.today)
    line_ids = fields.One2many('local.purchase.request.line', 'request_id', string='Products')
    local_rfq_created = fields.Boolean(string='RFQ Created', default=False)
    purpose = fields.Char(string='Purpose')
    reason_for_cancel = fields.Char(string='Reason For Cancel')
    cost_center = fields.Many2one('account.analytic.account', string='Cost Center', requird='True')
    image = fields.Image(string='Image', attachment=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Verified'),
        ('budget', 'Budget Approved'),
        ('pmapproved', 'Procurement Approved'),
        ('done', 'CEO Approved'),
        ('cancelled', 'Cancelled'),
    ], default='draft', string='Status', tracking=True)
    #purchase_type = fields.Selection([
     #  ('goods', 'Goods'),
     #('service', 'Service'),
    #], string='Purchase Type', required=True, default='goods')
    store_request_id = fields.Many2one('store.request.request', string='Store Request')
    store_request_approved = fields.Boolean(string='Store Request Approved', compute='_compute_store_request_approved', store=True)
    show_create_rfq_button = fields.Boolean(compute='_compute_show_create_rfq_button', string='Show Create RFQ Button')
    total_price = fields.Float(string='Total Price', compute='_compute_total_price', store=True)
    product_line_count = fields.Integer(string='Product Line Count', compute='_compute_product_line_count', store=True)
    budgetary_position = fields.Many2one('budget.budget', string='Budget Category')
    budget_liness=fields.Many2one('budget.lines',string='Budget Line')
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account")
    date_from = fields.Date(string='Start Date', required=True)
    date_to = fields.Date(string='End Date', required=True)

    purchase_type = fields.Selection([
        ('local', 'Local Purchase'),
        ('foreign', 'Foreign Purchase'),
        ('direct', 'Direct Purchase')

    ], string='Purchase Type', default='local')
    

    @api.constrains('state')
    def _update_reference_on_state_change(self):
        for record in self:
            if record.state != 'draft' and record.reference == _('New'):
                record.reference = self.env['ir.sequence'].next_by_code(
                    'local.purchase.request',
                    sequence_date=fields.Date.context_today(self)
                ) or _('New')

    @api.depends('line_ids.price_subtotal')
    def _compute_total_price(self):
        for record in self:
            record.total_price = sum(line.price_subtotal for line in record.line_ids)

    def action_pm_approve(self):
        for record in self:
            if record.state == 'budget':
                if record.total_price <= 100000:
                    record.state = 'done'
                else:
                    record.state = 'pmapproved'
            else:
                raise UserError('Cannot approve: Request must be in Budget Approved state.')

    def action_ceo_approve(self):
        for record in self:
            if record.state == 'pmapproved':
                if record.total_price > 100000:
                    record.state = 'done'
                else:
                    raise UserError('CEO approval not required for requests <= 100,000 Birr.')
            else:
                raise UserError('Cannot approve: Request must be in Procurement Approved state.')

    @api.depends('store_request_id')
    def _compute_store_request_approved(self):
        for record in self:
            record.store_request_approved = bool(
                record.store_request_id and
                record.store_request_id._fields.get('state') and
                record.store_request_id.state == 'storekeeper'
            )

    @api.constrains('store_request_id')
    def _check_store_request_approved(self):
        for record in self:
            if record.store_request_id and not record.store_request_approved:
                raise ValidationError(_('The store request must be approved by storekeeper before creating a local purchase request.'))

    @api.model_create_multi
    def create(self, vals_list):
        """Create LocalPurchaseRequest records with proper reference numbering"""
        if not vals_list:
            return super().create(vals_list)

        if isinstance(vals_list, dict):
            vals_list = [vals_list]

        # Batch fetch all referenced store requests
        store_request_ids = [
            vals['store_request_id'] for vals in vals_list
            if vals.get('store_request_id')
        ]
        store_requests = self.env['store.request.request'].browse(store_request_ids).exists()

        # Process sequence numbers in batch with date context
        needs_sequence = [
            (i, vals) for i, vals in enumerate(vals_list)
            if vals.get('reference', _('New')) == _('New')
        ]
        if needs_sequence:
            seq_refs = self.env['ir.sequence'].next_by_code(
                'local.purchase.request',
            ) or []

            # Handle single reference case
            if isinstance(seq_refs, str):
                seq_refs = [seq_refs]
            elif not seq_refs:
                seq_refs = [_('New')] * len(needs_sequence)

            for (i, vals), ref in zip(needs_sequence, seq_refs):
                vals['reference'] = ref

        # Rest of your store request processing...
        return super().create(vals_list)

    def button_confirm(self):
        for order in self:
            if not order.store_request_id:
                raise ValidationError(_('A Store Request is required before confirming the Purchase Order.'))
            if not order.store_request_approved:
                raise ValidationError(_('The store request must be approved by the storekeeper before confirming the purchase order.'))
        # Assuming this method is meant to transition state
        self.write({'state': 'submitted'})
        return True

    @api.depends('state', 'rfq_ids')
    def _compute_show_create_rfq_button(self):
        for record in self:
            record.show_create_rfq_button = record.state == 'approved'

    @api.depends('rfq_ids')
    def _compute_rfq_count(self):
        for record in self:
            record.rfq_count = len(record.rfq_ids)

    @api.depends('line_ids')
    def _compute_product_line_count(self):
        for record in self:
            record.product_line_count = len(record.line_ids)

    def custom_create_function(self):
        self.ensure_one()
        if self.state != 'done':
            raise ValidationError(_('You Cannot Create a RFQ Which is Not Approved'))
        rfq_values = {
            'request_date': self.request_date,
            'requested_by': self.requested_by.id,
            'approved_by': self.approved_by.id,
            'request_department': self.request_department.id,
            'purchase_type': self.purchase_type,
            'purchase_request_id': self.id,
        }
        rfq = self.env['local.create.rfq'].create(rfq_values)
        for line in self.line_ids:
            self.env['local.create.rfq.line'].create({
                'rfq_id': rfq.id,
                'product_id': line.product_id.id,
                'uom_id': line.uom_id.id,
                'quantity': line.quantity,
            })
        self.local_rfq_created = True
        return True

    def return_list(self):
        self.ensure_one()
        rfq_count = self.env['local.create.rfq'].search_count([('purchase_request_id', '=', self.id)])
        if rfq_count == 0:
            raise UserError(_('There are no RFQs created yet.'))
        return {
            'type': 'ir.actions.act_window',
            'name': 'Related RFQs',
            'res_model': 'local.create.rfq',
            'view_mode': 'list,form',
            'domain': [('purchase_request_id', '=', self.id)],
            'target': 'current',
        }

    def schedule_activity_for_group(self, group_xml_id, summary, note):
        group = self.env.ref(group_xml_id)
        for user in group.users:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=user.id,
                summary=summary,
                note=note,
            )

    def action_submit(self):
        self.ensure_one()
        if not self.line_ids:
            raise ValidationError(_('Please add at least one product line before submitting the request.'))
        self.write({'state': 'submitted'})
        self.schedule_activity_for_group(
            'custom_purchase_order.group_local_purchase_request_pm_manager',
            summary='Local Purchase Request Submitted',
            note='A local purchase request has been submitted and requires review.'
        )

    def action_approve(self):
        self.ensure_one()
        if not self.approved_by:
            self.write({'approved_by': self.env.user.id})
        self.write({'state': 'approved'})
        self.schedule_activity_for_group(
            'custom_purchase_order.group_local_purchase_request_finance_manager',
            summary='Request Verified',
            note='The request has been verified and needs budget approval.'
        )

    #def action_budget_approve(self):
     #   self.ensure_one()
      #  self.write({'state': 'budget'})
       # self.schedule_activity_for_group(
        #    'custom_purchase_order.group_local_purchase_request_ceo',
         #   summary='Budget Approved',
          #  note='The budget has been approved and is awaiting final approval from the CEO.'
        #)

    def action_budget_approve(self):
        self.ensure_one()

        # Step 1: Log the record and field values for debugging
        _logger.debug("Processing local.purchase.request ID: %s, budgetary_position: %s",
                      self.id, self.budgetary_position)

        # Step 2: Validate that budget category is selected
        if not self.budgetary_position:
            raise exceptions.ValidationError("No budget category selected. Please select a budget category.")

        # Step 3: Define fields
        budgetary_position = self.budgetary_position  # Many2one to account.budget.post
        date_from = self.date_from
        date_to = self.date_to
        _logger.debug("Fields - budgetary_position: %s, date_from: %s, date_to: %s",
                      budgetary_position.id, date_from, date_to)

        # Step 4: Calculate total requested amount for the same budget category and time period
        requests = self.env['local.purchase.request'].search([
            #('budgetary_position_id', '=', budgetary_position.id),
            ('date_from', '>=', date_from),
            ('date_to', '<=', date_to),
            ('state', '!=', 'cancel'),
        ])
        total_requested_amount = sum(request.amount_total for request in requests)
        _logger.debug("Found %s requests, total requested amount: %s", len(requests), total_requested_amount)

        # Step 5: Get the allowed budget for the category and period
        budget_line = self.env['budget.lines'].search([
            ('date_from', '<=', date_from),
            ('date_to', '>=', date_to),
            ('general_budget_id', '=', budgetary_position.id),  # Link to account.budget.post
        ], limit=1)
        _logger.debug("Budget line found: %s", budget_line)

        # Step 6: Approve and schedule activity
        self.write({'state': 'budget'})
        self.schedule_activity_for_group(
            'custom_purchase_order.group_local_purchase_request_ceo',
            summary='Budget Approved',
            note='The budget has been approved and is awaiting final approval from the CEO.'
        )
    def action_pm_approve(self):
        self.ensure_one()
        self.write({'state': 'pmapproved'})
        self.schedule_activity_for_group(
            'custom_purchase_order.group_local_purchase_request_user',
            summary='PM Approval Completed',
            note='The PM has approved the request. The process can now proceed.'
        )

    def action_done(self):
        self.ensure_one()
        self.write({'state': 'done'})
        self.schedule_activity_for_group(
            'custom_purchase_order.group_local_purchase_request_user',
            summary='Request Finalized',
            note='The request has been finalized and approved by the CEO.'
        )

    def action_cancel(self):
        self.write({'state': 'cancell'})  # Fix typo in state name

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})

    @api.depends('requested_by')
    def _compute_request_department(self):
        for record in self:
            if record.requested_by:
                employee = record.requested_by.employee_ids[:1]
                record.request_department = employee.department_id.id if employee else False

class LocalPurchaseRequestLine(models.Model):
    _name = 'local.purchase.request.line'
    _description = 'Local Purchase Request Line'

    #product_id = fields.Many2one('product.product', string='Product', required=True)
    request_id = fields.Many2one('local.purchase.request', string='Request Reference', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    quantity = fields.Float(string='Quantity', required=True)
    price_unit = fields.Float(string='Unit Price', required=True, default=0.0)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', compute='_compute_uom_id', store=True, readonly=True)
    budgetary_position = fields.Many2one('account.budget.post', string='Budget Category')
    price_subtotal = fields.Float(string='Subtotal', compute='_compute_price_subtotal', store=True)
    available_product_ids = fields.Many2many('product.product', string='Available Products', compute='_compute_available_product_ids', store=False)
    product_with_quantity = fields.Char(string='Product with Quantity', compute='_compute_product_with_quantity', store=True)
    #price_unit = fields.Float(string="Unit Price")
    #price_total = fields.Float(string='Total Price', compute='_compute_price_total', store=True)
    budget_liness = fields.Many2one('budget.lines', string='Budget Line')

    @api.onchange('product_id')
    def _onchange_product_id_set_price(self):
        if self.product_id:
            # Set from standard cost (internal valuation)
            self.price_unit = self.product_id.standard_price
            # Or if you prefer sales price: self.product_id.list_price

    @api.depends('quantity', 'price_unit')
    def _compute_price_subtotal(self):
        for line in self:
            line.price_subtotal = line.quantity * line.price_unit

    @api.depends('product_id', 'quantity')
    def _compute_product_with_quantity(self):
        for line in self:
            if line.product_id and line.quantity:
                line.product_with_quantity = f'{line.product_id.name} ({line.quantity})'
            else:
                line.product_with_quantity = ''

    @api.depends('product_id')
    def _compute_uom_id(self):
        for rec in self:
            rec.uom_id = rec.product_id.uom_id if rec.product_id else False

    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_('The quantity of the product must be greater than zero.'))

    def unlink(self):
        for line in self:
            if line.request_id.state != 'draft':
                raise ValidationError(_('You can only delete lines when the PR is in draft state.'))
        return super(LocalPurchaseRequestLine, self).unlink()

    @api.depends('request_id.store_request_id')
    def _compute_available_product_ids(self):
        for line in self:
            if line.request_id.store_request_id:
                line.available_product_ids = line.request_id.store_request_id.line_ids.mapped('product_id')
            else:
                line.available_product_ids = self.env['product.product'].browse()

    def action_budget_approve(self):
        self.ensure_one()

        # Validate we have a budget line selected
        if not self.budget_liness:
            raise exceptions.ValidationError("Please select a budget line before approval.")

        # Get the budget line and planned amount
        budget_line = self.budget_liness
        planned_amount = budget_line.planned_amount

        # Calculate total practical amount used (including this request)
        practical_amount = budget_line.practical_amount + self.total_price

        # Calculate remaining budget
        remaining_budget = planned_amount - budget_line.practical_amount

        # Validate budget
        if practical_amount > planned_amount:
            raise exceptions.ValidationError(
                _("Budget Exceeded!\n"
                  "Planned Budget: %(planned)s\n"
                  "Already Used: %(used)s\n"
                  "This Request: %(request)s\n"
                  "Remaining Budget: %(remaining)s") % {
                    'planned': planned_amount,
                    'used': budget_line.practical_amount,
                    'request': self.total_price,
                    'remaining': remaining_budget
                })

        # If validation passes, approve
        self.write({'state': 'budget'})
        self.schedule_activity_for_group(
            'custom_purchase_order.group_local_purchase_request_ceo',
            summary='Budget Approved',
            note='The budget has been approved and is awaiting final approval from the CEO.'
        )

    @api.constrains('budget_liness', 'price_subtotal')
    def _check_budget_availability(self):
        for line in self:
            if not line.budget_liness or line.request_id.state in ('draft', 'cancelled'):
                continue

            budget_line = line.budget_liness
            planned_amount = budget_line.planned_amount
            practical_amount = budget_line.practical_amount + line.price_subtotal

            if practical_amount > planned_amount:
                raise exceptions.ValidationError(
                    _("Line item would exceed budget!\n"
                      "Product: %(product)s\n"
                      "Amount: %(amount)s\n"
                      "Budget Line: %(budget)s\n"
                      "Available: %(available)s") % {
                        'product': line.product_id.name,
                        'amount': line.price_subtotal,
                        'budget': budget_line.display_name,
                        'available': planned_amount - budget_line.practical_amount
                    })