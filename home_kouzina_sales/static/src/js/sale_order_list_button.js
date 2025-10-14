/** @odoo-module **/
import { ListController } from "@web/views/list/list_controller";
import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';
import { useService } from "@web/core/utils/hooks";

export class SaleListController extends ListController {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
    }

    DownloadTemplate() {
        const url = "/home_kouzina_sales/static/src/files/sale_order_template.xlsx";

        const link = document.createElement("a");
        link.href = url;
        link.download = "sale_order_template.xlsx";
        link.click();
    }

    async OnUpload() {
        await this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "marketplace.order.import.wizard",
            views: [[false, "form"]],
            target: "new",
            context: {},
        });
    }
}
registry.category("views").add("button_in_tree", {
    ...listView,
    Controller: SaleListController,
    buttonTemplate: "button_sale.ListView.Buttons",
});
