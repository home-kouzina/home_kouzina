import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { TagsList } from "@web/core/tags_list/tags_list";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class LotPillsField extends Component {
    static template = "hk_purchase_report.LotPillsField";
    static components = { TagsList };
    static props = { ...standardFieldProps };

    get tags() {
        const value = this.props.record.data[this.props.name];
        if (!value) {
            return [];
        }
        return value
            .split(",")
            .map((lot) => lot.trim())
            .filter((text) => text)
            .map((text, index) => ({
                id: index,
                text,
                colorIndex: this.getColorIndex(text),
            }));
    }

    getColorIndex(text) {
        let hash = 0;
        for (let i = 0; i < text.length; i++) {
            hash = (hash * 31 + text.charCodeAt(i)) >>> 0;
        }
        return (hash % 11) + 1;
    }
}

export const lotPillsField = {
    component: LotPillsField,
    supportedTypes: ["char"],
};

registry.category("fields").add("lot_pills", lotPillsField);
