from odoo import models, fields, api, _,exceptions
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class ForeignPurchaseRequest(models.Model):
    _name = 'foreign.purchase.request'
    _description = 'Foreign Purchase Request'
    _inherit = ["mail.thread", "mail.activity.mixin", "analytic.mixin"]
    _rec_name = 'reference'
    _order = 'reference desc'

    rfq_ids_foreign = fields.One2many('foreign.create.rfq', 'purchase_request_id', string='RFQs')  # Link to related RFQs
    rfq_count = fields.Integer(string="", compute="_compute_rfq_count")
    reference = fields.Char(string='REFERENCE', required=True, copy=False, readonly=True,  default=lambda self: _('New'))
    request_department = fields.Many2one('hr.department', string='Department', store=True, compute='_compute_request_department')
    requested_by = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user)
    approved_by = fields.Many2one('res.users', string='Approved By')
    cost_center = fields.Many2one('account.analytic.account', string='Cost Center')
    #purchase_type = fields.Char(string="Purchase Type")
    request_date = fields.Date(string='Request Date', default=fields.Date.today)
    line_ids = fields.One2many('foreign.purchase.request.line', 'request_id', string='Products')
    foreign_rfq_created = fields.Boolean(string="RFQ Created", default=False)
    purpose = fields.Char(string="Purpose")
   #customer_order_id = fields.One2many('customer.order', string='Customer Order')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Verfied'),
        ('budget', 'Budget Approved'), 
        ('pmapproved', 'PM Approved'),        
        ('done', 'CEO Approved'),
        ('cancelled', 'Cancelled'),
    ], default='draft', string='Status',tracking=True)
    show_create_rfq_button = fields.Boolean(compute="_compute_show_create_rfq_button", string="Show Create RFQ Button")
    product_details = fields.Char(string="Product Details", compute="_compute_product_details", store=True)
    store_request_id = fields.Many2one('store.request.request', string='Store Request')
    vendor_id = fields.Many2one('res.partner', string='Vendor')
    budgetary_position = fields.Many2one('budget.budget', string='Budget Category')
    budget_liness = fields.Many2one('budget.lines', string='Budget Line')
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account")
    date_from = fields.Date(string='Start Date', required=True)
    date_to = fields.Date(string='End Date', required=True)

    purchase_type = fields.Selection([
        ('local', 'Local Purchase'),
        ('foreign', 'Foreign Purchase'),
        ('direct', 'Direct Purchase')

    ], string='Purchase Type', default='foreign')

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

    @api.depends('store_request_id', 'store_request_id.state')
    def _compute_store_request_approved(self):
        for record in self:
            record.store_request_approved = bool(
                record.store_request_id
                and hasattr(record.store_request_id, 'state')
                and record.store_request_id.state == 'storekeeper'
            )
    @api.model_create_multi
    def create(self, vals_list):
        """Create foreignPurchaseRequest records with proper reference numbering"""
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
                'foreign.purchase.request',
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


    #@api.model_create_multi
    #def create(self, vals_list):
     #   """Create ForeignPurchaseRequest records with automatic reference numbering,
      #  store request validation, and auto-populated lines.

       # Args:
        #    vals_list (list/dict): List of dictionaries or single dict of field values

        #Returns:
         #   recordset: Newly created records

       # Raises:
        #    ValidationError: If store request is not in 'storekeeper' state or if required fields are missing
       # """
        # Normalize input to always work with a list
        #if isinstance(vals_list, dict):
         #   vals_list = [vals_list]

        # Identify records needing sequence numbers
       # needs_sequence = [
        #    (i, vals) for i, vals in enumerate(vals_list)
         #   if vals.get('reference', _('New')) == _('New')
        #]

        # Generate sequence numbers in batch for better performance
       # if needs_sequence:
        #    sequence_refs = self.env['ir.sequence'].next_by_code(
         #       'foreign.purchase.request',
          #      len(needs_sequence)
           # ) or []

            # Apply generated references
            #for (i, vals), ref in zip(needs_sequence, sequence_refs):
             #   vals['reference'] = ref or _('New')

        # Pre-fetch all needed store requests for better performance
        #store_request_ids = [
         #   vals['store_request_id'] for vals in vals_list
          #  if vals.get('store_request_id')
       # ]
        #store_requests = self.env['store.request.request'].browse(store_request_ids)

        # Process each record's values
       # for vals in vals_list:
        #    if vals.get('store_request_id'):
         #       store_request = store_requests.filtered(
          #          lambda r: r.id == vals['store_request_id'])

                # Validate store request state
           #     if not hasattr(store_request, 'state') or store_request.state != 'storekeeper':
            #        raise ValidationError(
             #           _("The store request must be approved by the storekeeper before creating a purchase order."))

                # Auto-populate order lines if none provided
              #  if not vals.get('order_line'):
               #     vals['order_line'] = [
                #        (0, 0, {
                 #           'product_id': line.product_id.id,
                  #          'product_qty': line.quantity,
                   #         'product_uom': line.uom_id.id,
                    #        'name': line.product_id.name,
                     #       'price_unit': 0.0,
                      #  })
                       # for line in store_request.line_ids
                    #]

        #return super().create(vals_list)
    
    def button_confirm(self):
        for order in self:
            if not order.store_request_id:
                raise ValidationError(_("A Store Request is required before confirming the Purchase Order."))
            if not order.store_request_approved:
                raise ValidationError(
                    _("The store request must be approved by the storekeeper before confirming the purchase order."))
        return super(ForeignPurchaseRequest, self).button_confirm()

    def custom_create_function(self):
        self.ensure_one()
        if self.state != 'done':
            raise ValidationError(_("You cannot create an RFQ unless the request is fully approved (CEO Approved)."))
        if not self.line_ids:
            raise ValidationError(_("No product lines available to create an RFQ."))
        rfq_values = {
            'request_date': self.request_date,
            'requested_by': self.requested_by.id,
            'approved_by': self.approved_by.id,
            'request_department': self.request_department.id,
            'purchase_request_id': self.id,
            'vendor_id': self.vendor_id.id,
        }
        rfq = self.env['foreign.create.rfq'].create(rfq_values)
        for line in self.line_ids:
            self.env['foreign.create.rfq.line'].create({
                'foreign_rfq_id': rfq.id,
                'product_id': line.product_id.id,
                'uom_id': line.uom_id.id,
                'quantity': line.quantity,
            })
        self.foreign_rfq_created = True
        self.schedule_activity_for_group(
            'custom_purchase_order.group_foreign_purchase_request_user',
            summary=f"RFQ Created on {fields.Date.today()} at 11:02 AM EAT",
            note=f"An RFQ has been created from this request with reference {rfq.foreign_reference}."
        )
        return True
   # def custom_create_function(self):
    #    self.ensure_one()

        # Create the RFQ record and copy fields
#        rfq_values = {
 #           'request_date': self.request_date,
  #          'requested_by': self.requested_by.id,
   #         'approved_by': self.approved_by.id,
    #        'request_department' : self.request_department.id,
     #       'purchase_request_id': self.id,  # Link to the purchase request
    #}

     #   rfq = self.env['foreign.create.rfq'].create(rfq_values)

        # Copy line items from the purchase request to the RFQ, including the UOM and quantity
      #  for line in self.line_ids:
       #     self.env['foreign.create.rfq.line'].create({
        #        'foreign_rfq_id': rfq.id,
         #       'product_id': line.product_id.id,
          #      'uom_id': line.uom_id.id,  # Copy the UOM from the purchase request line
           #     'quantity': line.quantity,  # Copy the quantity from the purchase request line
       # })

        # Mark the purchase request as having an RFQ created
       # self.foreign_rfq_created = True

    # Action to return the list of related RFQs
    def return_list(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Related RFQs',
            'res_model': 'foreign.create.rfq',
            'view_mode': 'list,form',
            'domain': [('purchase_request_id', '=', self.id)],  # Filter by related purchase request
            'target': 'current',
        }

     # Reusable method to schedule activity
    def schedule_activity_for_group(self, group_xml_id, summary, note):
        """Schedule an activity for all users in the specified group."""
        group = self.env.ref(group_xml_id)
        for user in group.users:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=user.id,
                summary=summary,
                note=note,
            )

    # Action to submit the request
    def action_submit(self):
        self.ensure_one()
        if not self.line_ids:
            raise ValidationError(_("Please add at least one product line before submitting the request."))
        self.write({'state': 'submitted'})
        self.schedule_activity_for_group(
            'custom_purchase_order.group_foreign_purchase_request_pm_manager',
            summary="Foreign Purchase Request Submitted",
            note="A Foreign purchase request has been submitted and requires review."
        )
        
    

    # Action to approve the request
    def action_approve(self):
        self.ensure_one()
        if not self.approved_by:
            self.write({'approved_by': self.env.user.id})
        self.write({'state': 'approved'})
        self.schedule_activity_for_group(
            'custom_purchase_order.group_foreign_purchase_request_finance_manager',
            summary="Request Verified",
            note="The request has been verified and needs budget approval."
        )
        
    # Action approve budget
    #def action_budget_approve(self):
     #   self.ensure_one()
      #  self.write({'state': 'budget'})
       # self.schedule_activity_for_group(
        #    'custom_purchase_order.group_foreign_purchase_request_ceo',
         #   summary="Budget Approved",
          #  note="The budget has been approved and is awaiting final approval from the CEO."
        #)
    def action_budget_approve(self):
        self.ensure_one()

        # Step 1: Log the record and field values for debugging
        _logger.debug("Processing foreign.purchase.request ID: %s, budgetary_position: %s",
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
        requests = self.env['foreign.purchase.request'].search([
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

        #Step 6: Validate budget line existence
        #if not budget_line:
         #   raise exceptions.ValidationError(
          #      "No budget line found for the selected budget category and period."
           # )

        #allowed_amount = budget_line.planned_amount
        #_logger.debug("Allowed amount: %s for budget line ID: %s", allowed_amount, budget_line.id)

        # Step 7: Compare and validate requested amount against allowed budget
        #if total_requested_amount > allowed_amount:
         #   error_msg = f"Total purchase request amount ({total_requested_amount}) exceeds the allocated budget ({allowed_amount})."
          #  _logger.error("Validation error: %s", error_msg)
           # raise exceptions.ValidationError(error_msg)

        # Step 8: Approve and schedule activity
        self.write({'state': 'budget'})
        self.schedule_activity_for_group(
            'custom_purchase_order.group_foreign_purchase_request_ceo',
            summary='Budget Approved',
            note='The budget has been approved and is awaiting final approval from the CEO.'
        )
     # Action approve budget
    def action_pm_approve(self):
        self.ensure_one()
        self.write({'state': 'pmapproved'})
        self.schedule_activity_for_group(
            'custom_purchase_order.group_foreign_purchase_request_pm_manager',
            summary="PM Approval Completed",
            note="The PM has approved the request. The process can now proceed."
        )

    # Action to mark the request as done
    def action_done(self):
        self.ensure_one()
        self.write({'state': 'done'})
        self.schedule_activity_for_group(
            'custom_purchase_order.group_foreign_purchase_request_user',
            summary="PM Approval Completed",
            note="The PM has approved the request. The process can now proceed."
        )

    # Action to cancel the request
    def action_cancel(self):
        self.ensure_one()
        self.write({'state': 'cancelled'})
        
     # Action to reset to draft
    def action_reset_to_draft(self):
        self.ensure_one()
        self.write({'state': 'draft'})
        
    @api.depends('requested_by')
    def _compute_request_department(self):
        """ Automatically compute the department based on the 'requested_by' user """
        for record in self:
            if record.requested_by:
                # Get the first department of the related employee(s) linked to the user
                employee = record.requested_by.employee_ids[:1]
                record.request_department = employee.department_id.id if employee else False



class ForeignPurchaseRequestLine(models.Model):
    _name = 'foreign.purchase.request.line'
    _description = 'Foreign Purchase Request Line'

    request_id = fields.Many2one('foreign.purchase.request', string='Request Reference', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    quantity = fields.Float(string='Quantity', required=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', compute='_compute_uom_id', store=True, readonly=True)
    budgetary_position = fields.Many2one('account.budget.post', string="Budget Category")
    budget_liness = fields.Many2one('budget.lines', string='Budget Line')
    price_subtotal = fields.Float(string='Total', compute='_compute_price_subtotal', store=True)
    available_product_ids = fields.Many2many('product.product', string='Available Products',
                                             compute='_compute_available_product_ids', store=False)
    product_with_quantity = fields.Char(string='Product with Quantity', compute='_compute_product_with_quantity',
                                        store=True)
    price_unit = fields.Float(string='Unit Price', required=True, default=0.0)

    @api.onchange('product_id')
    def _onchange_product_id_set_price(self):
        if self.product_id:
            # Set from standard cost (internal valuation)
            self.price_unit = self.product_id.standard_price
            # Or if you prefer sales price: self.product_id.list_price

    @api.depends('product_id', 'quantity')
    def _compute_product_with_quantity(self):
        for line in self:
            if line.product_id and line.quantity:
                line.product_with_quantity = f'{line.product_id.name} ({line.quantity})'
            else:
                line.product_with_quantity = ''

    @api.depends('quantity', 'price_unit')
    def _compute_price_subtotal(self):
        for line in self:
            line.price_subtotal = line.quantity * line.price_unit

    @api.depends('product_id')
    def _compute_uom_id(self):
        for rec in self:
            if rec.product_id:
                rec.uom_id = rec.product_id.uom_id
            else:
                rec.uom_id = False 
    
    # Constraint to ensure the quantity is positive
    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_("The quantity of the product must be greater than zero."))
            
    def unlink(self):
        for line in self:
            if line.request_id.state != 'draft':
                raise ValidationError(_("You can only delete lines when the PR is in draft state."))
        return super(ForeignPurchaseRequestLine, self).unlink()

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
            'custom_purchase_order.group_foreign_purchase_request_ceo',
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