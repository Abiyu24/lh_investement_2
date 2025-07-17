{
    'name': 'Credit and Cash Sales',
    'version': '16.0.1.0.0',
    'category': 'Sales',
    'summary': 'Classify sales orders as Cash or Credit with custom menu views',
    'depends': ['sale_management', 'account'],
    'data': [
        'security/group.xml',
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
        'views/sale_to_invoice_views.xml',
        'views/sale_to_upsell_views.xml',
        'views/sale_menu.xml',
        'data/hide_default_menu.xml',
    ],
    'installable': True,
    'application': False,
}
