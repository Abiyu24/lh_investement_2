from odoo import models, fields, api, _,exceptions
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class WithoutRFQLocalPurchase(models.Model):
    _name = 'without.rfq.local.purchase'
    _description = 'Without RFQ Local Purchase'
    _inherit = ["mail.thread", "mail.activity.mixin", "analytic.mixin"]
    _rec_name = 'reference_wrfq'
    _order = 'reference_wrfq desc'

    name = fields.Char(string='Direct purchase Name')
    reference_wrfq = fields.Char(string='REFERENCE', required=True, copy=False, readonly=True,default=lambda self: _('New'))

    @api.model
    def create(self, vals):
        if vals.get('reference_wrfq', _('New')) == _('New'):
            vals['reference_wrfq'] = self.env['ir.sequence'].next_by_code('without.rfq.local.purchase') or _('New')
        return super(WithoutRFQLocalPurchase, self).create(vals)

    request_department = fields.Many2one('hr.department', string='Department', compute='_compute_request_department', store=True)
    requested_by = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user)
    approved_by = fields.Many2one('res.users', string='Approved By')
    request_date = fields.Date(string='Request Date', default=fields.Date.today)
    vendor_id = fields.Many2one('res.partner', string="Vendor")
    line_ids = fields.One2many('without.rfq.local.purchase.line', 'request_id', string='Products')
    purpose = fields.Char(string="Purpose")
    order_id = fields.Many2one('purchase.order', string='Order Reference', ondelete='cascade')
    budgetary_position = fields.Many2one('budget.budget', string='Budget Category')
    budget_liness = fields.Many2one('budget.lines', string='Budget Line')
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account")
    date_from = fields.Date(string='Start Date', required=True)
    date_to = fields.Date(string='End Date', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Verfied'),
        ('budget', 'Budget Approved'), 
        ('pmapproved', 'PM Approved'),        
        ('done', 'CEO Approved'),
        ('cancelled', 'Cancelled'),
    ], default='draft', string='Status',tracking=True)
    

    #purchase_type = fields.Selection(
     # [('goods', 'Goods'), ('service', 'Service')],
      #string="Purchase Type", required=True, default='goods',
    #)
    purchase_type = fields.Selection([
        ('local', 'Local Purchase'),
        ('foreign', 'Foreign Purchase'),
        ('direct', 'Direct Purchase')

    ], string='Purchase Type', default='direct')
    withoutpo_ids = fields.One2many('purchase.order', 'without_rfq_request_ids', string='POs')
    show_purchase_order_button = fields.Boolean(compute="_compute_show_purchase_order_button", string="Show Purchase Order Button")
    show_create_po_button = fields.Boolean(string="Show Create PO Button", default=True)
    local_po_created = fields.Boolean(string="PO Created", default=False)
    count_withoutrfq_po = fields.Integer(string=".", compute='_compute_po_count')

    
    product_details = fields.Char(string="Product Details", compute="_compute_product_details", store=True)
    store_request_id = fields.Many2one('store.request.request', string='Store Request')

    # store_request_approved = fields.Boolean(string='Store Request Approved', compute='_compute_store_request_approved', store=True)
    product_id = fields.Many2one('product.product', string="Product")
    description = fields.Text(string="Description")
    pin_number = fields.Char(string="PIN Number")
    quantity = fields.Float(string="Quantity", default=1.0)
    order_type = fields.Selection(
        [('standard', 'Standard'), ('urgent', 'Urgent')],
        string="Order Type"
    )
    @api.depends('line_ids.product_id', 'line_ids.quantity')
    def _compute_product_details(self):
        for record in self:
            details = []
            for line in record.line_ids:
                if line.product_id and line.quantity:
                    details.append(f"{line.product_id.name} ({line.quantity})")
            record.product_details = ', '.join(details) if details else ''

    @api.depends('state', 'rfq_ids_foreign')
    def _compute_show_create_rfq_button(self):
        """ Compute whether the Create RFQ button should be shown """
        for record in self:
            record.show_create_rfq_button = (record.state == 'approved')

    # Compute the count of related RFQs
    @api.depends('rfq_ids_foreign')
    def _compute_rfq_count(self):
        for record in self:
            record.rfq_count = len(record.rfq_ids_foreign)

    @api.depends('store_request_id', 'store_request_id.state')
    def _compute_store_request_approved(self):
        try:
            for record in self:
                if not record.store_request_id:
                    record.store_request_approved = False
                    continue

                record.store_request_approved = record.store_request_id.state == 'storekeeper'
        except Exception as e:
            _logger.error(f"Error computing store_request_approved: {str(e)}")
            for record in self:
                record.store_request_approved = False
            return False
        return True

    # @api.constrains('store_request_id')
    # def _check_store_request_approved(self):
    # for record in self:
    ##   if record.store_request_id and not record.store_request_approved:
    #    raise ValidationError(_('The store request must be approved by storekeeper before creating a local purchase request.'))

    @api.depends('store_request_id', 'store_request_id.state')
    def _compute_store_request_approved(self):
        for record in self:
            record.store_request_approved = bool(
                record.store_request_id
                and hasattr(record.store_request_id, 'state')
                and record.store_request_id.state == 'storekeeper'
            )

    

    def button_confirm(self):
        for order in self:
            if not order.store_request_id:
                raise ValidationError(_("A Store Request is required before confirming the Purchase Order."))
            if not order.store_request_approved:
                raise ValidationError(
                    _("The store request must be approved by the storekeeper before confirming the purchase order."))
        return super(WithoutRFQLocalPurchase, self).button_confirm()
    @api.depends('line_ids.product_id', 'line_ids.quantity')
    def _compute_product_details(self):
        for record in self:
            details = []
            for line in record.line_ids:
                if line.product_id and line.quantity:
                    details.append(f"{line.product_id.name} ({line.quantity})")
            record.product_details = ', '.join(details) if details else ''
    
    
    @api.depends('withoutpo_ids')
    def _compute_po_count(self):
        """ Compute the count of related POs. """
        for record in self:
            record.count_withoutrfq_po = len(record.withoutpo_ids)

    @api.model_create_multi
    def create(self, vals_list):
        """Create withoutrfqlocalPurchaseRequest records with proper reference numbering"""
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
            if vals.get('reference_wrfq', _('New')) == _('New')
        ]
        if needs_sequence:
            seq_refs = self.env['ir.sequence'].next_by_code(
                'without.rfq.local.purchase',
            ) or []

            # Handle single reference case
            if isinstance(seq_refs, str):
                seq_refs = [seq_refs]
            elif not seq_refs:
                seq_refs = [_('New')] * len(needs_sequence)

            for (i, vals), ref in zip(needs_sequence, seq_refs):
                vals['reference_wrfq'] = ref

        # Rest of your store request processing...
        return super().create(vals_list)


    @api.depends('requested_by')
    def _compute_request_department(self):
        """ Auto-assign the department based on the user making the request. """
        for record in self:
            employee = self.env['hr.employee'].search([('user_id', '=', record.requested_by.id)], limit=1)
            record.request_department = employee.department_id.id if employee else False


    @api.depends('state')
    def _compute_show_purchase_order_button(self):
        """ Control the visibility of the 'Create PO' button based on the state. """
        for record in self:
            record.show_purchase_order_button = record.state == 'approved' and not record.local_po_created

    
    def action_submit(self):
        self.ensure_one()
        if not self.line_ids:
            raise ValidationError(_("Please add at least one product line before submitting the request."))
        self.write({'state': 'submitted'})
        
    def schedule_activity_for_group(self, group_xml_id, summary, note):
        group = self.env.ref(group_xml_id)
        for user in group.users:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=user.id,
                summary=summary,
                note=note,
            )

    # Action to approve the request
    def action_approve(self):
        self.ensure_one()
        if not self.approved_by:
            self.write({'approved_by': self.env.user.id})
        self.write({'state': 'approved'})
        
    def action_budget_approve(self):
        self.ensure_one()

        # Step 1: Log the record and field values for debugging
        _logger.debug("Processing without.rfq.local.purchase ID: %s, budgetary_position: %s",
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
        requests = self.env['without.rfq.local.purchase'].search([
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
            'custom_purchase_order.group_without_rfq_local_purchase_ceo',
            summary='Budget Approved',
            note='The budget has been approved and is awaiting final approval from the CEO.'
        )
        
     # Action approve budget
    def action_pm_approve(self):
        self.ensure_one()
        self.write({'state': 'pmapproved'})

    # Action to mark the request as done
    def action_done(self):
        self.ensure_one()
        self.write({'state': 'done'})

    # Action to cancel the request
    def action_cancel(self):
        self.ensure_one()
        self.write({'state': 'cancelled'})
        
     # Action to reset to draft
    def action_reset_to_draft(self):
        self.ensure_one()
        self.write({'state': 'draft'})

    def action_create_dpo(self):
        """ Create a Purchase Order for the vendor. """
        self.ensure_one()
        if not self.line_ids:
            raise ValidationError(_("You cannot create a PO without product lines."))

        # Prepare the purchase order values
        po_values = {
            'without_rfq_request_ids': self.id,  # Link to this model
            'partner_id': self.vendor_id.id,  # Vendor ID
            'date_order': fields.Date.today(),
            'purchase_type': 'direct',  # Explicitly setting the purchase type to 'direct'
            'order_line': [(0, 0, {
                'product_id': line.product_id.id,
                'product_qty': line.quantity,
                'price_unit': line.price_unit,
                'name': line.product_id.name or '',  # Product name
                'date_planned': fields.Date.today(),  # Planned date
            }) for line in self.line_ids],  # Lines from this request
            'without_rfq_reference': self.reference_wrfq,  # Reference link
        }

        # Create the purchase order
        po = self.env['purchase.order'].create(po_values)

        # Mark the request as PO created
        self.local_po_created = True
        self.order_id = po.id  # Link the created PO to the request




    def action_view_dpo(self):
        """ Opens the list of related Purchase Orders. """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Purchase Orders'),
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('without_rfq_request_ids', '=', self.id)],
            'target': 'current',
        }
    
    def action_cancel(self):
        """ Mark the request as cancelled. """
        self.ensure_one()
        self.write({'state': 'cancelled'})

    def action_reset_draft(self):
        """ Reset the request back to draft state. """
        self.ensure_one()
        self.write({'state': 'draft'})
        self.local_po_created = False


class WithoutRFQLocalPurchaseLine(models.Model):
    _name = 'without.rfq.local.purchase.line'
    _description = 'Without RFQ Local Purchase Line'

    request_id = fields.Many2one('without.rfq.local.purchase', string="Request Reference", required=True)
    product_id = fields.Many2one('product.product', string="Product", required=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', related='product_id.uom_id', readonly=True, store=True)
    quantity = fields.Float(string="Quantity", required=True)
    price_unit = fields.Float(string="Unit Price", required=True)
    price_total = fields.Float(string='Total Price', compute='_compute_price_total', store=True)
    state = fields.Selection(related='request_id.state', string="Status", store=True)
    budgetary_position = fields.Many2one('account.budget.post', string='Budget Category')
    price_subtotal = fields.Float(string='Subtotal', compute='_compute_price_subtotal', store=True)
    available_product_ids = fields.Many2many('product.product', string='Available Products',
                                             compute='_compute_available_product_ids', store=False)
    product_with_quantity = fields.Char(string='Product with Quantity', compute='_compute_product_with_quantity',
                                        store=True)
    budget_liness = fields.Many2one('budget.lines', string='Budget Line')

    @api.depends('quantity', 'price_unit')
    def _compute_price_total(self):
        """ Compute the total price of the line. """
        for line in self:
            line.price_total = line.quantity * line.price_unit

    @api.onchange('product_id')
    def _onchange_product_id_set_price(self):
        if self.product_id:
            # Set from standard cost (internal valuation)
            self.price_unit = self.product_id.standard_price
            # Or if you prefer sales price: self.product_id.list_price

    @api.depends('request_id.store_request_id')
    def _compute_available_product_ids(self):
        for line in self:
            if line.request_id.store_request_id:
                line.available_product_ids = line.request_id.store_request_id.line_ids.mapped('product_id')
            else:
                line.available_product_ids = self.env['product.product'].browse()

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
            'custom_purchase_order.group_without_rfq_local_purchase_ceo',
            summary='Budget Approved',
            note='The budget has been approved and is awaiting final approval from the CEO.'
        )
        # Replace schedule_activity_for_group with activity_schedule

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