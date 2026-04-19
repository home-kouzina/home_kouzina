# -*- coding: utf-8 -*-
#################################################################################
#    Copyright (c) 2018-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#    You should have received a copy of the License along with this program.
#    If not, see <https://store.webkul.com/license.html/>
#################################################################################
from . import models
from . import wizard
from . import controllers
from . import tools

from logging import getLogger
_logger = getLogger(__name__)

def pre_init_check(cr):
    from odoo.service import common
    from odoo.exceptions import UserError
    version_info = common.exp_version()
    server_serie = float(version_info.get('server_serie'))
    if not 17.0 < server_serie < 19.0:
        raise UserError(f'Module supports Odoo series 18.x but found {server_serie}.')

