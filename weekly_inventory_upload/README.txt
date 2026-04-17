Weekly Inventory Upload
=======================

Features
- Download Sample Template
- Prefilled sample Excel with product reference, product, and one column per location
- Upload weekly stock by Excel
- Success notification
- Error report download
- Weekly upload history
- Upload logs
- Undo last upload

Excel columns
- Product Reference
- Product
- One column for each location in the system

Install
1. Copy this module into your custom addons path.
2. Restart Odoo.
3. Update Apps List.
4. Install 'Weekly Inventory Upload'.

Usage
1. Inventory -> Weekly Inventory Upload
2. Create a record
3. Download Sample Template with product rows and location columns
4. Enter quantities only in the location columns you want to update
5. Upload file
6. Click Process Inventory
7. Download Error Report if any failures
8. Use Undo Last Upload to restore previous quantities

Notes
- Product Reference contains the Internal Reference when available, otherwise `ID:<product_id>`.
- Product column shows the product variant display name.
- Only location values greater than 0 are updated. Zero and blank values are ignored.
- If a product does not already exist at the selected location, that row fails and the quantity is not updated.
- Location matches by Full Location Name first, then Barcode, then Location Name.
- If the same Product Reference + Location appears more than once, the last row quantity is used.
