/** @odoo-module */
import { ListController } from "@web/views/list/list_controller";
import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';
import { useService } from "@web/core/utils/hooks";

export class SaleListController extends ListController {
    setup() {
        super.setup();
        this.orm = useService("orm");
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
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".xlsx";

    input.onchange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        if (!file.name.toLowerCase().endsWith(".xlsx")) {
            this.notification.add("Upload error: Only .xlsx files are allowed!", {
                type: "danger",
                title: "Validation Error",
            });
            return;
        }

        try {
            const arrayBuffer = await file.arrayBuffer();
            const uint8Array = new Uint8Array(arrayBuffer);

            // Convert to Base64
            let binary = "";
            for (let i = 0; i < uint8Array.byteLength; i++) {
                binary += String.fromCharCode(uint8Array[i]);
            }
            const base64File = btoa(binary);

            // Call backend with base64
            const res = await this.orm.call(
                "sale.order",
                "action_import_from_xlsx",
                [base64File]
            );

            this.notification.add(res.message, {
                type: res.success ? "success" : "danger",
                title: res.success ? "Upload Complete" : "Upload Failed",
            });

            if (res.success) {
                this.reload();
            }
        } catch (err) {
            this.notification.add("Unexpected error while importing.", {
                type: "danger",
                title: "Upload Failed",
            });
        }
    };

    input.click();
}
}
registry.category("views").add("button_in_tree", {
    ...listView,
    Controller: SaleListController,
    buttonTemplate: "button_sale.ListView.Buttons",
});
