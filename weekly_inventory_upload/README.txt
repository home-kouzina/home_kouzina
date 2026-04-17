Weekly Inventory Upload
=======================

Features
- Download Sample Template
- Product and location dropdowns in the sample Excel template
- Upload weekly stock by Excel
- Success notification
- Error report download
- Weekly upload history
- Upload logs
- Undo last upload

Excel columns
- Product
- Location
- Quantity

Install
1. Copy this module into your custom addons path.
2. Restart Odoo.
3. Update Apps List.
4. Install 'Weekly Inventory Upload'.

Usage
1. Inventory -> Weekly Inventory Upload
2. Create a record
3. Download Sample Template with product and location dropdowns
4. Fill Excel and use the dropdowns where needed
5. Upload file
6. Click Process Inventory
7. Download Error Report if any failures
8. Use Undo Last Upload to restore previous quantities

Notes
- Product matches by Product Name first, then Internal Reference.
- Location matches by Full Location Name first, then Barcode, then Location Name.
- Duplicate Product + Location rows use the last row quantity.
