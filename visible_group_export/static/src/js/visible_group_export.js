import { _t } from "@web/core/l10n/translation";
import { download } from "@web/core/network/download";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { useBus } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { STATIC_ACTIONS_GROUP_NUMBER } from "@web/search/action_menus/action_menus";
import { ListController } from "@web/views/list/list_controller";

import { Component } from "@odoo/owl";

const cogMenuRegistry = registry.category("cogMenu");

function cleanCellText(cell) {
    if (!cell) {
        return "";
    }
    const clone = cell.cloneNode(true);
    clone
        .querySelectorAll(
            ".o_group_caret, .o_group_buttons, .o_pager, button, input, .o_optional_columns_dropdown"
        )
        .forEach((el) => el.remove());
    return (clone.textContent || "").replace(/\s+/g, " ").trim();
}

function getGroupLevel(row) {
    const caret = row.querySelector(".o_group_caret");
    if (!caret) {
        return 0;
    }
    const inlineLevel = caret.style.getPropertyValue("--o-list-group-level");
    const computedLevel = window.getComputedStyle(caret).getPropertyValue("--o-list-group-level");
    const level = parseInt(inlineLevel || computedLevel || "0", 10);
    return Number.isFinite(level) ? level : 0;
}

function normalizeTitle(title) {
    return (title || _t("Grouped Export")).replace(/[\\/:*?"<>|]+/g, "-").trim();
}

patch(ListController.prototype, {
    setup() {
        super.setup(...arguments);
        if (this.env.searchModel) {
            useBus(
                this.env.searchModel,
                "direct-export-visible-grouped-data",
                this.onExportVisibleGroupedData.bind(this)
            );
        }
    },

    getVisibleGroupedExportPayload() {
        const table = this.rootRef.el?.querySelector(".o_list_renderer table.o_list_table");
        if (!table) {
            throw new Error(_t("No list table found to export."));
        }

        const headerCells = Array.from(table.querySelectorAll("thead tr > th"));
        const tableSlots = headerCells.map((th, index) => ({
            index,
            name: th.dataset.name || null,
            label: cleanCellText(th),
        }));
        const fieldSlots = tableSlots.filter((slot) => slot.name && slot.label);
        const outputIndexByTableIndex = new Map(
            fieldSlots.map((slot, outputIndex) => [slot.index, outputIndex])
        );
        const outputIndexByFieldName = new Map(
            fieldSlots.map((slot, outputIndex) => [slot.name, outputIndex])
        );

        const columns = fieldSlots.map((slot) => ({
            name: slot.name,
            label: slot.label,
            type: this.props.fields[slot.name]?.type || "char",
        }));

        const rows = [];
        const bodyRows = Array.from(table.querySelectorAll("tbody tr"));

        for (const row of bodyRows) {
            if (row.classList.contains("o_group_header")) {
                const values = Array(columns.length).fill("");
                const level = getGroupLevel(row);
                const groupNameCell = row.querySelector(".o_group_name") || row.children[0];
                values[0] = cleanCellText(groupNameCell);

                let tableIndex = 0;
                for (const cell of Array.from(row.children)) {
                    const colspan = cell.colSpan || 1;
                    if (!cell.classList.contains("o_group_name")) {
                        const text = cleanCellText(cell);
                        if (text) {
                            for (let i = tableIndex; i < tableIndex + colspan; i++) {
                                if (outputIndexByTableIndex.has(i)) {
                                    values[outputIndexByTableIndex.get(i)] = text;
                                    break;
                                }
                            }
                        }
                    }
                    tableIndex += colspan;
                }

                rows.push({ type: "group", level, values });
            } else if (row.classList.contains("o_data_row")) {
                const values = Array(columns.length).fill("");
                for (const cell of Array.from(row.querySelectorAll("td[name]"))) {
                    const outputIndex = outputIndexByFieldName.get(cell.getAttribute("name"));
                    if (outputIndex !== undefined) {
                        values[outputIndex] = cleanCellText(cell);
                    }
                }
                rows.push({ type: "record", level: 0, values });
            }
        }

        const footerRow = table.querySelector("tfoot tr");
        if (footerRow) {
            const values = Array(columns.length).fill("");
            let tableIndex = 0;
            for (const cell of Array.from(footerRow.children)) {
                const colspan = cell.colSpan || 1;
                const text = cleanCellText(cell);
                if (text) {
                    for (let i = tableIndex; i < tableIndex + colspan; i++) {
                        if (outputIndexByTableIndex.has(i)) {
                            values[outputIndexByTableIndex.get(i)] = text;
                            break;
                        }
                    }
                }
                tableIndex += colspan;
            }
            if (values.some((value) => value)) {
                rows.push({ type: "footer", level: 0, values });
            }
        }

        return {
            title: `${normalizeTitle(this.props.info?.displayName || this.props.displayName || this.env.config?.displayName)} - Grouped Export.xlsx`,
            model: this.model.root.resModel,
            domain: this.model.root.domain,
            groupBy: this.model.root.groupBy,
            columns,
            rows,
        };
    },

    async onExportVisibleGroupedData() {
        const payload = this.getVisibleGroupedExportPayload();
        await download({
            data: {
                data: JSON.stringify(payload),
            },
            url: "/web/export/visible_grouped_xlsx",
        });
    },
});

export class VisibleGroupedExportMenu extends Component {
    static template = "visible_group_export.VisibleGroupedExportMenu";
    static components = { DropdownItem };

    async onExportVisibleGroupedData() {
        this.env.searchModel.trigger("direct-export-visible-grouped-data");
    }
}

export const visibleGroupedExportItem = {
    Component: VisibleGroupedExportMenu,
    groupNumber: STATIC_ACTIONS_GROUP_NUMBER,
    isDisplayed: async (env) => {
        const root = env.model?.root;
        const rootContext = root?.context || {};
        return (
            env.config.viewType === "list" &&
            root &&
            !root.selection.length &&
            Boolean(rootContext.visible_group_export) &&
            (await user.hasGroup("base.group_allow_export"))
        );
    },
};

cogMenuRegistry.add("visible-grouped-export-menu", visibleGroupedExportItem, { sequence: 11 });
