# -*- coding: utf-8 -*-
# Order matters: the inventory.soh.report SQL view reads the soh_week and
# soh_week_line tables, so those models must be created first.
from . import soh_week
from . import soh_upload
from . import inventory_soh_report
