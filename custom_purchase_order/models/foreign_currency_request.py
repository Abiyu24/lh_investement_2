from odoo import models, fields, api, _
from odoo.exceptions import UserError
from num2words import num2words

class ForeignCurrencyRequest(models.Model):
    _name = 'foreign.currency.request'
    _description = 'Foreign Currency Request'
    _inherit = ["mail.thread", "mail.activity.mixin", "analytic.mixin"]
    _rec_name = 'foreign_currency_request_reference'

    # Fields and status definitions
    foreign_rfq_reference = fields.Many2one('foreign.create.rfq', string="Foreign RFQ", readonly=True)    
    foreign_rfq_id = fields.Char(related='foreign_rfq_reference.foreign_reference', string="Foreign RFQ Reference", readonly=True, store=True)
    
    foreign_currency_request_reference = fields.Char(string='REFERENCE', required=True, copy=False, readonly=True, default=lambda self: _("New"))
    purchase_order_id = fields.Many2one(comodel_name='purchase.order',string='Purchase Order',ondelete='cascade')
    
    name = fields.Char(string='Payment Request')
    proforma_invoice = fields.Many2one('account.analytic.account', string="Cost Center", help="Select the cost center associated with this RFQ")   
    requested_by = fields.Many2one('res.users', string="Requested By",tracking=True)
    request_department = fields.Many2one('hr.department', string='Department')
    request_date = fields.Date(string="Request Date",tracking=True)
    currency_id = fields.Many2one('res.currency', string="Currency", required=True, default=lambda self: self.env.ref('base.USD', raise_if_not_found=False),tracking=True)
    purpose = fields.Char(string="Purpose",tracking=True)
    nbe_number = fields.Float(string="NBE", default=1.00)
    vendor_id = fields.Many2one('res.partner', string='Supplier', required=True,tracking=True)  
    payment_due_date = fields.Date(string="Payment Due Date",tracking=True)
    price_amount = fields.Float(string='Total Amount USD', required=True,tracking=True)
    exchange_rate = fields.Float(string="Exchange Rate", readonly=True)
    total_amount_etb = fields.Float(string='Total Amount ETB', required=True, compute='_compute_total_amount_etb', readonly=True)
    amount_in_word = fields.Char(string="Amount In Words", compute='_compute_amount_in_words', readonly=True)
    approved_date = fields.Date(string="Approved Date")
    bank = fields.Many2one('res.bank', string="Bank",tracking=True)
    branch = fields.Char(string="Branch",tracking=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('queued', 'Queued'),  
        ('on_progress', 'On Progress'),      
        ('approved', 'Approved'),       
        ('cancelled', 'Cancelled'),
    ], default='draft', string='Status',tracking=True)

    # In your exchange.rate model, ensure you have:
    class ExchangeRate(models.Model):
        _name = 'exchange.rate'
        _description = 'Currency Exchange Rates'

        name = fields.Many2one('res.currency', string='Currency', required=True)
        exchange_rate = fields.Float(string='Rate', digits=(12, 6), required=True)
        date = fields.Date(string='Date', default=fields.Date.today)

        _sql_constraints = [
            ('currency_date_unique', 'unique(name, date)',
             'Only one exchange rate per currency per date allowed!'),
        ]
    @api.onchange('currency_id')
    def _onchange_currency_id(self):
        if self.currency_id:
            company_currency = self.env.company.currency_id

            # First try custom exchange rate table
            exchange_rate_rec = self.env['exchange.rate'].search(
                [('name', '=', self.currency_id.id)],
                limit=1
            )

            if exchange_rate_rec:
                self.exchange_rate = exchange_rate_rec.exchange_rate
            else:
                # Fallback to Odoo's built-in rates
                try:
                    self.exchange_rate = self.currency_id._get_conversion_rate(
                        company_currency,
                        self.currency_id,
                        self.env.company,
                        fields.Date.today()
                    )
                except:
                    # Final fallback to 1.0 with warning
                    warning = {
                        'title': _('Exchange Rate Missing'),
                        'message': _(
                            "No exchange rate defined for %s. Using default rate of 1.0") % self.currency_id.name
                    }
                    self.exchange_rate = 1.0
                    return {'warning': warning}

    @api.constrains('exchange_rate')
    def _check_exchange_rate(self):
        for record in self:
            if record.state in ['approved'] and record.exchange_rate <= 0:
                raise ValidationError(_("Exchange rate must be positive before approval"))
    @api.depends('price_amount', 'exchange_rate')
    def _compute_total_amount_etb(self):
        for record in self:
            record.total_amount_etb = record.price_amount * record.exchange_rate if record.exchange_rate else record.price_amount

    def action_refresh_exchange_rate(self):
        for record in self:
            if record.currency_id:
                record._onchange_currency_id()

    @api.depends('total_amount_etb')
    def _compute_amount_in_words(self):
        for record in self:
            if record.total_amount_etb:
                record.amount_in_word = num2words(record.total_amount_etb, lang='en').capitalize()
            else:
                record.amount_in_word = ""

    @api.model_create_multi
    def create(self, vals_list):
        """Create ForeignCurrencyRequest records with unique references.
        Handles both single record and batch creation efficiently.
        """
        # Normalize input to always work with a list
        if isinstance(vals_list, dict):
            vals_list = [vals_list]

        # Process records that need sequence numbers
        needs_sequence = [
            (i, vals) for i, vals in enumerate(vals_list)
            if vals.get('foreign_currency_request_reference', _('New')) == _('New')
        ]

        # Generate sequence numbers in batch for better performance
        if needs_sequence:
            sequence = self.env['ir.sequence']
            refs = sequence.next_by_code('foreign.currency.request', len(needs_sequence)) or []

            # Apply generated references
            for (i, vals), ref in zip(needs_sequence, refs):
                vals['foreign_currency_request_reference'] = ref or _('New')

        return super().create(vals_list)

    def action_submit(self):
        self.ensure_one()
        self.write({'state': 'queued'})
        

    # def action_queue(self):
    #     self.ensure_one()
    #     self.write({'state': 'approved'})

    def action_approve(self):
        self.ensure_one()
        
        self.write({'state': 'approved'})

    def action_cancel(self):
        self.ensure_one()
        self.write({'state': 'cancelled'})

    def action_reset_to_draft(self):
        """ Resets the Payment back to draft state. """
        self.ensure_one()
        self.write({'state': 'draft'})
        
    def create_foreign_currency_from_foreign_rfq(self, foreign_rfq_id):
        """ Creates a foreign currency request from the given Foreign RFQ. """
        request = self.env['foreign.create.rfq'].browse(foreign_rfq_id)
        if not request:
            return

        # Prepare the values to create a Foreign Currency Request
        vals = {
            'rfq_foreign_request_id': request.id,  # Link to the Foreign RFQ
            'foreign_rfq_reference': request.foreign_reference,
            'vendor_id': request.vendor_id.id,  # Vendor from RFQ
            'price_amount': request.price_total,  # Total Amount from RFQ
            'currency_id': self.env.company.currency_id.id,  # Default currency of the company
            'requested_by': self.env.user.id,  # Requestor is the current user
            'request_date': fields.Date.today(),
        }

        # Create the Foreign Currency Request
        foreign_currency_request = self.create(vals)

        # Return the created record's action
        return {
            'type': 'ir.actions.act_window',
            'name': 'Foreign Currency Request',
            'view_mode': 'form',
            'res_model': 'foreign.currency.request',
            'res_id': foreign_currency_request.id,  # Open the created record
            'target': 'new',  # Opens in a new modal window
        }

    def open_form(self):
        """Open the form view of the current Foreign Currency Request."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Foreign Currency Request',
            'res_model': 'foreign.currency.request',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }
#class PurchaseOrder(models.Model):
 #   _inherit = 'purchase.order'

  #  foreign_currency_request_ids = fields.One2many('foreign.currency.request', 'purchase_order_id', string='Foreign Currency Requests')

#    def action_open_foreign_currency_request(self):
 #       """Open a new Foreign Currency Request form linked to this Purchase Order."""
  #      self.ensure_one()
   #     return {
    #        'type': 'ir.actions.act_window',
     #       'name': 'Foreign Currency Request',
      #      'res_model': 'foreign.currency.request',
       #     'view_mode': 'form',
        #    'target': 'current',
         #   'context': {
          #      'default_purchase_order_id': self.id,
           #     'default_vendor_id': self.partner_id.id,
        #    },
       # }