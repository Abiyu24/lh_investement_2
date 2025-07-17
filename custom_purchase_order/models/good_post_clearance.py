from odoo import models, fields, api

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    mode_of_transport = fields.Char(string="Mode Of Shipment")
    good_arrival_final_destination = fields.Date(string="Arrival Date to Fin Dest")
    freight_payment_by_air = fields.Float(string="Freight Amout ETB")
    freight_payment_date = fields.Date(string="Estimated Production Completion Date")
    freight_settlement_advise_to_finance = fields.Date(string="Freight Settlement")
    container_deposit_amount = fields.Float(string="Container Deposit")
    shipping_doc_to_transitor = fields.Date(string="Ship Doc & Settlement?")    
    declaration_number = fields.Float(string="Declaration Number")
    custom_duty_tax_amount = fields.Float(string="Custom Duty Tax")
    custom_duty_withholding_tax = fields.Float(string="Withholding Tax")
    customs_clearance_document = fields.Binary(
        string='Customs Clearance Document',
        attachment=True,
        help='Upload the Customs Release Order or Declaration Form from ECS.'
    )
    duty_tax_receipt = fields.Binary(
        string='Duty and Tax Payment Receipt',
        attachment=True,
        help='Upload the receipt proving payment of customs duties and taxes.'
    )
    duty_tax_receipt_filename = fields.Char(string='Duty and Tax Receipt Filename')
    port_of_entry = fields.Char(
        string='Port of Entry',
        help='Port or airport where goods enter Ethiopia (e.g., Djibouti Port, Bole Airport).'
    )
    customs_clearance_document_filename = fields.Char(string='Customs Clearance Document Filename')
    clearance_date = fields.Date(
        string='Clearance Date',
        help='Date when goods are cleared by ECS.'
    )
    
    custom_duty_tax_paid_date = fields.Date(string="Tax Paid Date")
    custom_tax_acceptance = fields.Boolean(string="Accep of the Duty Tax")  # Changed to Float
    custom_duty_tax_additional_amount = fields.Float(string="Additional Duty Tax")  # Changed to Float
    custom_actual_tax_additional_amount = fields.Date(string="Actual Duty Tax Paid")
    release_permit_applied_to_fda = fields.Date(string="Release Permit FDA")
    release_permit_received_from_fda = fields.Date(string="Release Permit")
    storage_cost = fields.Float(string="Storage Cost")  # Changed to Float
    demurrage_cost = fields.Float(string="Demurrage Cost")
    local_transport_cost = fields.Float(string="Local Transport Cost")
    loading_unloading_cost = fields.Float(string="Loading & Unloading")
    release_date_from_customs_delivery = fields.Date(string="Delivery to Warehouse")
    
   
    
    
class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    paking_list_shared_with_inventory = fields.Char(string="Packing List")
    good_arrival_date = fields.Date(string="Warehouse Arrival Date")
    grn_reconcile_from_received_date = fields.Float(string="GRN Rec ")
    reconcile_disperancy = fields.Boolean(string="Rec Discrepancy")
    grn_submitted_to_finance = fields.Date(string="GRN to Finance")
    stamped_declaration_received_date = fields.Float(string="Declaration Receive")
    delinquent_settlement_date = fields.Date(string="Delinquent Sett Date?")    
    transistor_service_payment_amount = fields.Float(string="Transitor Payment")
    container_deposited_reimpursed_date = fields.Float(string="Container Deposit")
    transistor_service_payment_done_date = fields.Float(string="Transitor Payment Done")

    post_clearance_audit_report = fields.Binary(
        string='Post-Clearance Audit Report',
        attachment=True,
        help='Upload the audit report issued by ECS/ERCA.'
    )
    post_clearance_audit_report_filename = fields.Char(string='Audit Report Filename')
    additional_duty_tax_receipt = fields.Binary(
        string='Additional Duty/Tax Payment Receipt',
        attachment=True,
        help='Upload the receipt for additional duties/taxes from post-clearance audits.'
    )
    additional_duty_tax_receipt_filename = fields.Char(string='Additional Duty/Tax Receipt Filename')
    final_import_closure_date = fields.Date(
        string='Final Import Closure Date',
        help='Date when all import obligations are completed.'
    )
    nbe_final_approval_reference = fields.Char(
        string='NBE Final Approval Reference',
        help='NBE reference confirming import process completion.'
    )
    packing_list_filename = fields.Char(string='Packing List Filename')
    additional_packing_list = fields.Binary(
        string='Additional Packing List',
        attachment=True,
        help='Upload supplementary packing list documents, if any.'
    )
    additional_packing_list_filename = fields.Char(string='Additional Packing List Filename')
    package_count = fields.Integer(
        string='Package Count',
        help='Total number of packages in the shipment.'
    )
    total_weight = fields.Float(
        string='Total Weight (kg)',
        help='Total weight of the shipment in kilograms.'
    )
    