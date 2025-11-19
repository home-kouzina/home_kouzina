/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { CogMenu } from "@web/search/cog_menu/cog_menu";
import { useService } from "@web/core/utils/hooks";

patch(CogMenu.prototype, {
    setup() {
        super.setup();
        this.action = useService("action");
    },

    get cogItems() {
        // Safely copy existing items
        const items = super.cogItems ? [...super.cogItems] : [];

        // 1. Get current model info
        const searchModel = this.env.searchModel;
        const resModel = searchModel?.resModel;

        // 2. Define Inventory Models
        const inventoryModels = [
            'stock.picking',       
            'stock.quant',         
            'stock.valuation.layer', 
            'product.template',    
            'product.product'      
        ];

        // 3. Check if we are in an Inventory Model (No Admin Check)
        if (inventoryModels.includes(resModel)) {
            items.push({
                key: "inventory_custom_action",
                description: "Inventory Stock Update",
                icon: "fa fa-cubes",
                groupNumber: 99,
                callback: () => {
                    this.action.doAction("hk_stock_update.action_inventory_custom_wizard", {
                        additional_context: {
                            active_ids: searchModel.resIds, 
                            active_model: resModel,
                        }
                    });
                },
            });
        }

        return items;
    },
});