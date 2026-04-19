# -*- coding: utf-8 -*-
#################################################################################
#
#    Copyright (c) 2019-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#
#################################################################################
from . import models
from . import wizard
def pre_init_check(cr):
	from odoo.service import common
	from odoo.exceptions import UserError
	version_info = common.exp_version()
	server_serie = version_info.get('server_serie')
	if not 16 < float(server_serie) <= 18:
		raise UserError(f'Module support Odoo series 17.0 found {server_serie}.')
