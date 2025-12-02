from . import wizard


def pre_init_check(cr):

    # Odoo Module
    from odoo.service import common
    from odoo.exceptions import ValidationError
    from odoo import _

    version_info = common.exp_version()
    server_serie = version_info.get('server_serie')
    if server_serie != '18.0':
        raise ValidationError(
            _(f'Module support Odoo series 18.0 found {server_serie}.'),
        )
