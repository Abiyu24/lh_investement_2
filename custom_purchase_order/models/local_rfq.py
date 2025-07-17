from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError



class LocalCreateRFQ(models.Model):
    _name = 'local.create.rfq'
    _description = 'Local RFQ'
    _inherit = ["mail.thread", "mail.activity.mixin", "analytic.mixin"]
    _rec_name = 'reference'

    name = fields.Char(string='RFQ Name')
    purchase_request_id = fields.Many2one('local.purchase.request', string="Purchase Request", readonly=True)
    reference = fields.Char(string='REFERENCE', required=True, copy=False, readonly=True,default=lambda self: _('New'))
    request_date = fields.Date(string="Request Date")
    request_department = fields.Many2one('hr.department', string='Department')
    requested_by = fields.Many2one('res.users', string="Requested By")
    approved_by = fields.Many2one('res.users', string="Approved By")
    line_ids = fields.One2many('local.create.rfq.line', 'rfq_id', string="Products")
    remark = fields.Char(string="Remark")
    technical_remark = fields.Char(string="Technical Remark")
    company_id= fields.Many2one('res.company', string="Company")
    prepared_by = fields.Many2one('res.users', string="Prepared By")
    #checked_by = fields.Many2one('res.users', string="Checked By")
   # authorized_by = fields.Many2one('res.users', string="Authorized By")
    order_id = fields.Many2one('purchase.order', string='Order Reference', ondelete='cascade') 
    rfq_date = fields.Date(string='RFQ Date', default=fields.Date.context_today, required=True)
    vendor_id = fields.Many2one('res.partner', string='Vendor')
    total_amount = fields.Float(string='Total Amount', compute='_compute_total_amount', store=True)
    po_count = fields.Integer(string=".", compute='_compute_po_count')
    show_create_po_button = fields.Boolean(string="Show Create PO Button", default=True)
    winner_detail_ids = fields.One2many(
        'rfq.winner.detail', 'purchase_request_id', string="Winner Details", compute="_compute_winner_details", store=True
    )

    @api.depends('vendor_id')
    def _compute_winner_details(self):
        for rfq in self:
            rfq.winner_detail_ids = [(5, 0, 0)]  # Clear existing rows
            for detail in self.env['rfq.winner.detail'].search([('purchase_request_id', '=', rfq.id)]):
                rfq.winner_detail_ids += [(4, detail.id)]
   
   
   



    state = fields.Selection([
        ('preparedby', 'Prepare RFQ'),
        ('approverfq', 'Approve RFQ'),
        ('draft', 'Print RFQ'),
        ('confirmed', 'Confirmed'),
        ('sent', 'Approved'),
        ('cancelled', 'Cancelled'),
    ], string='State', default='preparedby')

    po_ids = fields.One2many('purchase.order', 'rfq_request_id', string='POs')
    local_po_created = fields.Boolean(string="PO Created", default=False)
    po_count = fields.Integer(string="PO Count", compute='_compute_po_count')
    
    
    product_details = fields.Char(string="Product Details", compute="_compute_product_details", store=True)

    @api.depends('line_ids.product_id', 'line_ids.quantity', 'line_ids.winner')
    def _compute_product_details(self):
        for record in self:
            details = []
            for line in record.line_ids.filtered(lambda l: l.winner == 'win'):
                if line.product_id and line.quantity:
                    details.append(f"{line.product_id.name} ({line.quantity})")
            record.product_details = ', '.join(details) if details else ''
    
   
    
    #purchase_type = fields.Selection([
    #('goods', 'Goods'),
    #('service', 'Service')
    #], string="Purchase Type", readonly=True)
    purchase_type = fields.Selection([
        ('local', 'Local Purchase'),
        ('foreign', 'Foreign Purchase'),
        ('direct', 'Direct Purchase')

       ], string='Purchase Type', default='local')

    @api.onchange('purchase_request_id')
    def _onchange_purchase_request_id(self):
        if self.purchase_request_id:
            self.purchase_type = self.purchase_request_id.purchase_type
        else:
            self.purchase_type = False

    @api.depends('line_ids.price_total')
    def _compute_total_amount(self):
        """ Compute the total amount of the RFQ. """
        for rfq in self:
            rfq.total_amount = sum(line.price_total for line in rfq.line_ids)
   
    @api.depends('po_ids')
    def _compute_po_count(self):
        """ Compute the count of related POs. """
        for record in self:
            record.po_count = len(record.po_ids)



    @api.model_create_multi
    def create(self, vals_list):
        """Create LocalPurchaseRequest records with proper reference numbering"""
        if not vals_list:
            return super().create(vals_list)

        if isinstance(vals_list, dict):
            vals_list = [vals_list]

    

        # Process sequence numbers in batch with date context
        needs_sequence = [
            (i, vals) for i, vals in enumerate(vals_list)
            if vals.get('reference', _('New')) == _('New')
        ]
        if needs_sequence:
            seq_refs = self.env['ir.sequence'].next_by_code(
                'local.create.rfq',
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
    
    
    
    def action_confirm(self):
        self.ensure_one()
        if not self.line_ids:
            raise ValidationError(_("You cannot confirm an RFQ without product lines."))
        
        # Check that each line has a vendor set
        for line in self.line_ids:
            if not line.vendor_id:
                raise UserError(_("Please enter a vendor for each line before confirming."))
            if not line.price_unit:
                raise UserError(_("Please enter a price unit for each line before confirming."))
        

        # If all checks pass, update the state
        self.write({'state': 'confirmed'})
        self.schedule_activity_for_group(
            'custom_purchase_order.group_local_purchase_request_pm_manager',
            summary="Local Purchase Request Submitted",
            note="A local RFQ has been Confirmed and requires review."
        )
        
        return True



    def action_send(self):
        self.ensure_one()
        
        # Ensure a winner has been selected before sending
        if not any(line.winner == 'win' for line in self.line_ids):
            raise ValidationError(_("You must pick a winner before approving the RFQ."))

        if self.state != 'confirmed':
            raise ValidationError(_("Only confirmed RFQs can be sent."))

        self.write({'state': 'sent'})

        self.schedule_activity_for_group(
            'custom_purchase_order.group_local_purchase_request_user',
            summary="Local Purchase Request Submitted",
            note="A local RFQ has been Approved and Create PO."
        )

        return True


    def action_cancel(self):
        self.ensure_one()
        self.write({'state': 'cancelled'})

    def action_reset_to_draft(self):
        """ Resets the RFQ back to draft state and resets the winners. """
        self.ensure_one()
        self.write({'state': 'draft'})
        self.line_ids.write({'winner': False})
        
    def action_reset_to_prepare_rfq(self):
        """ Resets the RFQ back to draft state and resets the winners. """
        self.ensure_one()
        self.write({'state': 'preparedby'})
        
    
    def action_prepare_rfq(self):
        self.ensure_one()
        self.write({'state': 'approverfq'})
        self.schedule_activity_for_group(
            'custom_purchase_order.group_local_purchase_request_pm_manager',
            summary="Local Purchase Request Submitted",
            note="A local RFQ request has been submitted and requires review."
        )
        
        return True
        
    def action_approve_rfq(self):
        self.ensure_one()
        self.write({'state': 'draft'})
        self.schedule_activity_for_group(
            'custom_purchase_order.group_local_purchase_request_user',
            summary="Local Purchase Request Submitted",
            note="A local RFQ request has been submitted and requires review."
        )
        
        return True
        
    @api.model
    def get_report_action(self, docids, data=None):
        """
        Restrict report execution if state is not 'approverfq'.
        """
        records = self.browse(docids)
        # Check the state of each record
        if any(record.state != 'approverfq' for record in records):
            raise UserError("You cannot print the RFQ unless the state is 'Approved RFQ'.")
        
        # Proceed with the report if all records meet the condition
        return super(LocalCreateRFQ, self).get_report_action(docids, data)
        
    
        
    def action_create_po(self):
        """ Create Purchase Orders from the RFQ for each vendor with winning lines, if the state is 'approved'. """
        self.ensure_one()

        # Check if the state is 'approved'
        if self.state != 'sent':
            raise ValidationError(_("You Cannot Create a PO Which is Not Approved"))

        # Filter lines with 'win' status
        winning_lines = self.line_ids.filtered(lambda line: line.winner == 'win')

        if not winning_lines:
            raise ValidationError(_("You cannot create a PO without any winning lines."))

        # Group winning lines by vendor
        vendors = winning_lines.mapped('vendor_id')

        # Create a PO for each vendor with all their respective winning lines
        for vendor in vendors:
            # Filter the winning lines for the current vendor
            vendor_lines = winning_lines.filtered(lambda line: line.vendor_id == vendor)

            # Prepare the values for the Purchase Order with all lines for this vendor
            po_values = {
                'rfq_request_id': self.id,  # Link the PO to the RFQ
                'partner_id': vendor.id,  # Set the vendor from the winning lines
                'purchase_type': 'local',
                'date_order': fields.Date.today(),  # Set the order date
                'order_line': [(0, 0, {
                    'product_id': line.product_id.id,
                    'product_qty': line.quantity,
                    'price_unit': line.price_unit,
                    'name': line.product_id.name or '',  # Add product description
                    'date_planned': fields.Date.today(),  # Set planned date
                }) for line in vendor_lines],  # Combine all the vendor's winning lines as order lines
                'rfq_reference': self.reference,  # Pass the RFQ reference to the PO
            }
            
            po = self.env['purchase.order'].create(po_values)
            self.local_po_created = True
            self.order_id = po.id

            # Create the Purchase Order for the vendor (only one per vendor)
        # self.env['purchase.order'].create(po_values)

        # # Mark the RFQ as PO created
        # self.local_po_created = True

        # # Optionally hide the 'Create PO' button after creating the POs
        # self.show_create_po_button = False
        
        

        return True
    
   
   
   
   
   

        
    
    

    def action_view_po(self):
        """ Opens the list of related Purchase Orders. """
        self.ensure_one()

        # Check if there are any related Purchase Orders
        po_count = self.env['purchase.order'].search_count([('rfq_request_id', '=', self.id)])

        if po_count == 0:
            # Raise an error if no related Purchase Orders are found
            raise UserError(_("There are no Purchase Orders created yet."))

        # Return the action to view the related Purchase Orders if they exist
        return {
            'type': 'ir.actions.act_window',
            'name': _('Purchase Orders'),
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('rfq_request_id', '=', self.id)],
            'target': 'current',
        }
        
        
        
        # Action to return the list of related po
    def return_list(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Related PO',
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('rfq_request_id', '=', self.id)],  # Filter by related purchase request
            'target': 'current',
        }
        
   
    def action_compute_winner(self):
        """ Automatically mark the line with the lowest unit price as the winner for each product. """
        for record in self:
            # Check if vendor and price_unit are set on all lines
            for line in record.line_ids:
                if not line.vendor_id:
                    raise UserError("Please enter a vendor for each line before computing the winner.")
                if line.price_unit <= 0:
                    raise UserError("Please enter a valid unit price for each line before computing the winner.")

            product_winner_map = {}  # Dictionary to track the lowest price per product

            # Loop through each line in the RFQ
            for line in record.line_ids:
                product = line.product_id

                # If this product hasn't been checked yet, or if the current line has a lower price, update the map
                if product not in product_winner_map or line.price_unit < product_winner_map[product].price_unit:
                    product_winner_map[product] = line

            # Mark the winner lines and others as 'lost'
            for product, winning_line in product_winner_map.items():
                winning_line.action_accept()  # Mark this line as the winner
                # Mark all other lines for the same product as 'lost'
                record.line_ids.filtered(lambda l: l.product_id == product and l != winning_line).action_refuse()

                # Create winner details for each vendor that has won a product
                vendors = winning_line.vendor_id
                for vendor in vendors:
                    self.env['rfq.winner.detail'].create({
                        'purchase_request_id': record.id,
                        'vendor_id': vendor.id,
                        'product_id': winning_line.product_id.id,
                        'quantity': winning_line.quantity
                    })

        return True
   
   
   
   
   
   
    
    
    def action_pick_winner(self):
        """Mark the line with the highest combined score of technical and financial as the winner."""
        for record in self:
            # Check if all lines have a vendor assigned
            if any(not line.vendor_id for line in record.line_ids):
                raise UserError("Please enter a vendor for each line before picking the winner.")

            # Check if both technical and financial fields are entered
            for line in record.line_ids:
                if line.technical_by_percent is None or line.technical_by_percent == 0:
                    raise UserError("Please enter a valid technical score for each line before picking the winner.")
                if line.financial is None or line.financial == 0:
                    raise UserError("Please enter a valid financial score for each line before picking the winner.")

            highest_score_map = {}  # Dictionary to track the highest combined score per product

            # Loop through each line in the RFQ
            for line in record.line_ids:
                combined_score = line.technical_by_percent + line.financial
                product = line.product_id

                # If the current score is higher, update the highest score map
                if product not in highest_score_map or combined_score > highest_score_map[product][0]:
                    highest_score_map[product] = (combined_score, line)

            # Mark the highest scoring lines as winners and others as 'lost'
            for product, (score, winning_line) in highest_score_map.items():
                winning_line.action_accept()
                record.line_ids.filtered(lambda l: l.product_id == product and l != winning_line).action_refuse()

        return True
    
    
    line_count = fields.Integer(string="Line Count", compute='_compute_line_count', store=True)
    
    @api.depends('line_ids')
    def _compute_line_count(self):
        for record in self:
            record.line_count = len(record.line_ids)

class LocalCreateRFQLine(models.Model):
    _name = 'local.create.rfq.line'
    _description = 'Local RFQ Line'

    rfq_id = fields.Many2one('local.create.rfq', string="RFQ Reference", required=True)
    vendor_id = fields.Many2one('res.partner', string="Vendor")
    product_id = fields.Many2one('product.product', string="Product", required=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', related='product_id.uom_id', readonly=True, store=True)
    quantity = fields.Float(string="Quantity", required=True)
    price_unit = fields.Float(string="Unit Price")
    price_total = fields.Float(string='Total Price', compute='_compute_price_total', store=True)
    technical_by_percent = fields.Float(string="Technical(%)")
    financial = fields.Float(string="Financial (%)")
    winner = fields.Selection([('win', 'Win'), ('lost', 'Lost')], string="Winner")
    
    available_product_ids = fields.Many2many(
        'product.product', 
        string='Available Products', 
        compute='_compute_available_product_ids', 
        store=False
    )

    @api.depends('rfq_id.purchase_request_id')
    def _compute_available_product_ids(self):
        """ Compute the available products from the related Purchase Request. """
        for line in self:
            if line.rfq_id.purchase_request_id:
                line.available_product_ids = line.rfq_id.purchase_request_id.line_ids.mapped('product_id')
            else:
                line.available_product_ids = self.env['product.product'].browse()

    @api.depends('quantity', 'price_unit')
    def _compute_price_total(self):
        """ Compute the total price of the line. """
        for line in self:
            line.price_total = line.quantity * line.price_unit

    def action_accept(self):
        """Mark this line as the winner and other vendors as 'lost' for the same product."""
        self.ensure_one()
        
        # Check if RFQ state is draft; if so, do not proceed
        if self.rfq_id.state != 'confirmed':
            raise ValidationError(_("You cannot accept until approved"))

        # Check for missing fields
        missing_fields = []
        for line in self.rfq_id.line_ids:
            if not line.vendor_id:
                missing_fields.append(f"Vendor (Product: {line.product_id.name})")
            if not line.price_unit:
                missing_fields.append(f"Unit Price (Product: {line.product_id.name})")
            if line.technical_by_percent is None:
                missing_fields.append(f"Technical (%) (Product: {line.product_id.name})")
            if line.financial is None:
                missing_fields.append(f"Financial (%) (Product: {line.product_id.name})")

        if missing_fields:
            raise ValidationError(_("The following fields are missing for the products:\n%s" % "\n".join(missing_fields)))

        # Set current line as winner and others with same product as lost
        self.winner = 'win'
        self.sudo().search([
            ('rfq_id', '=', self.rfq_id.id),
            ('product_id', '=', self.product_id.id),
            ('id', '!=', self.id)
        ]).write({'winner': 'lost'})

    def action_refuse(self):
        """Mark this line as lost."""
        if self.rfq_id.state == 'draft':
            raise ValidationError(_("You cannot refuse until approved"))
        self.winner = 'lost'

    # def action_refuse(self):
    #     """ Mark this line as lost. """
    #     self.winner = 'lost'

    @api.constrains('winner')
    def _check_winner(self):
        """ Ensure that only one line is marked as 'Win' per product in the RFQ. """
        for line in self:
            if line.winner == 'win':
                win_count = self.env['local.create.rfq.line'].search_count([
                    ('rfq_id', '=', line.rfq_id.id),
                    ('product_id', '=', line.product_id.id),
                    ('winner', '=', 'win')
                ])
                if win_count > 1:
                    raise ValidationError(_("You cannot select more than one 'Win' for the same product in this RFQ."))
                
    def unlink(self):
        for line in self:
            if line.rfq_id.state != 'draft':
                raise ValidationError(_("You can only delete lines when the RFQ is in draft state."))
        return super(LocalCreateRFQLine, self).unlink()
    
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        """ Set the quantity automatically if the product already exists in the RFQ lines. """
        if self.product_id and self.rfq_id:
            # Get all the lines in the RFQ for this product
            existing_lines = self.rfq_id.line_ids.filtered(lambda line: line.product_id == self.product_id)

            # If the product already exists in another line, inherit its quantity
            if existing_lines:
                self.quantity = existing_lines[0].quantity
            else:
                # If no such product exists in the RFQ lines, fetch it from the related purchase request
                if self.rfq_id.purchase_request_id:
                    request_lines = self.rfq_id.purchase_request_id.line_ids.filtered(lambda rline: rline.product_id == self.product_id)
                    if request_lines:
                        self.quantity = request_lines[0].quantity
                    else:
                        self.quantity = 0.0






class RFQWinnerDetail(models.Model):
    _name = 'rfq.winner.detail'
    _description = 'RFQ Winner Detail'

    purchase_request_id = fields.Many2one('local.create.rfq', string="RFQ", required=True)
    vendor_id = fields.Many2one('res.partner', string="Vendor")
    product_id = fields.Many2one('product.product', string="Product")
    quantity = fields.Float(string="Quantity", required=True)