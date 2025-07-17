{
    'name': 'Store Requestion',
    'version': '1.0',
    'summary': 'Manage Store Requestion.',
    'depends': ['base','stock','hr','custom_purchase_order','hr_employee_self_service'],  # Ensure this module is installed
    'data': [
        
        'security/store_request_security.xml',
        
        'security/ir.model.access.csv',
        
        'data/store_request_seq.xml',
        
        
        
        'views/store_request_view.xml',
      
        
        
      
    ],
    'assets': {
        
        
    },
    'installable': True,
    'application': False,
}
