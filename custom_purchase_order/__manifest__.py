{
    'name': 'Custom Purchase Request',
    'version': '1.0',
    'summary': 'Manage Local and Foreign Purchase Orders and RFQs separately.',
    'depends': ['purchase', 'stock', 'account', 'hr_employee_self_service'],  # Ensure this module is installed
    'data': [

        'security/local_purchase_request_security.xml',
        'security/without_rfq_local_purchase_security.xml',
        'security/foreign_purchase_request_security.xml',
        'security/payment_request_securtiy.xml',
        'security/ir.model.access.csv',

        'data/purchase_order_sequence.xml',
        'data/local_purchase_request.xml',
        'data/local_rfq_sequence.xml',
        'data/foreign_rfq_sequence.xml',
        'data/foreign_purchase_request.xml',
        'data/without_rfq_purchase_request_sequence.xml',
        'data/payment_request_sequence.xml',
        'data/foreign_currency_request_sequence.xml',
        # 'data/foreign_email_template.xml',
        # 'data/email_templates.xml',


        'views/purchase_menu.xml',
        'views/local_purchase_request_views.xml',
        'views/local_rfq.xml',
        'views/withoutrfq_purchase_request.xml',
        'views/foreign_purchase_request_view.xml',
        'views/foreign_rfq.xml',
        'views/local_payment_request.xml',
        'views/lc_view.xml',
        'views/purchase_margin_views.xml',
        'views/shippment_view.xml',
        'views/good_clearance_post_clerance_view.xml',
        'views/port_of_loading_views.xml',
        'views/foreign_currency_request.xml',
        'views/exchange_rate_menu.xml',
        'views/amount_threshold_required_ceo.xml',
        'views/mail_views.xml',
        'views/hs_code.xml',
        #'views/customer_order_views.xml',

        # 'wizard/foreign_rfq_send_email.xml',
       # 'wizard/proforma_invoice_wizard_view.xml',
        #'wizard/customer_order_line_wizard.xml',

        'reports/rfq_report_template.xml',
        'reports/rfq_report_template_foreign.xml',
        'reports/rfq_report.xml',
        'reports/local_purchase_request_report.xml',
        'reports/foreign_purchase_request_report.xml',
        'reports/direct_purchase_request_report.xml',
        'reports/local_rfq_report.xml',
        'reports/foreign_rfq_report.xml',
        'reports/lc_foreign_report.xml',
        'reports/purchase_orders_report.xml',

        # 'views/res_config_settings_views.xml',
        # 'views/res_users_views.xml',

        # 'views/foreign_purchase_order_added_pages.xml',
        'views/purchase_order_views.xml',

        # 'report/rfq_report_template.xml',
        # 'report/rfq_report.xml',

    ],
    'assets': {
    },
    'installable': True,
    'application': False,
    "license": "LGPL-3",
}
