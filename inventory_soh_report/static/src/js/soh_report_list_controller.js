/** @odoo-module **/
import { onWillStart, useState } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";

/**
 * Inventory SOH Report list: adds "Upload Physical Inventory",
 * "Close Week" and "History" (opens SOH Weekly History) next to the
 * gear icon.
 */
export class SohReportListController extends ListController {
    static template = "inventory_soh_report.ListView";

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.dialogService = useService("dialog");
        this.notification = useService("notification");
        // has_upload: Close Week is shown only after a count was applied this week.
        this.sohWeek = useState({ name: "", start: "", has_upload: false });
        onWillStart(() => this.loadSohWeek());
    }

    async loadSohWeek() {
        const info = await this.orm.call("soh.week", "get_open_week_info", []);
        Object.assign(this.sohWeek, info);
    }

    async reloadSohReport() {
        await this.loadSohWeek();
        await this.model.load();
    }

    async onClickUploadPhysicalInventory() {
        await this.actionService.doAction(
            "inventory_soh_report.action_soh_physical_inventory_wizard",
            {
                onClose: async (infos) => {
                    if (infos && infos.soh_message) {
                        this.notification.add(infos.soh_message, { type: "success" });
                    }
                    await this.reloadSohReport();
                },
            }
        );
    }

    async onClickWeeklyHistory() {
        await this.actionService.doAction("inventory_soh_report.action_soh_week");
    }

    onClickCloseWeek() {
        this.dialogService.add(ConfirmationDialog, {
            title: _t("Close Week"),
            body: _t(
                "Close %s and save the full report to SOH Weekly History? A new week starts now, with today's Actual SOH as Opening. This cannot be undone.",
                this.sohWeek.name
            ),
            confirmLabel: _t("Close Week"),
            confirm: async () => {
                const result = await this.orm.call("soh.week", "action_close_current_week", []);
                this.notification.add(
                    _t("%s closed and saved to SOH Weekly History. %s has started.", result.closed, result.opened),
                    { type: "success" }
                );
                await this.reloadSohReport();
            },
            cancel: () => {},
        });
    }
}

registry.category("views").add("soh_report_list", {
    ...listView,
    Controller: SohReportListController,
});
