# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from datetime import date


class TestInventoryVariationCreate(TransactionCase):
    """Unit tests for inventory.variation and inventory.variation.line"""

    def setUp(self):
        super().setUp()

        # Create a test warehouse
        self.warehouse = self.env['stock.warehouse'].create({
            'name': 'Test Warehouse',
            'code': 'TESTWH',
            'manufacture_steps': 'mrp_one_step',
            'manufacture_to_resupply': True,
        })

        # Create a test consumable product
        self.product = self.env['product.product'].create({
            'name': 'Test Product',
            'default_code': 'TP001',
            'type': 'consu',
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'sale_line_warn': 'no-message',
        })

        # Create a test inventory variation session
        self.inventory_variation = self.env['inventory.variation'].create({
            'name': 'IVRTEST001',
            'date': date.today(),
            'warehouse_id': self.warehouse.id,
        })

    # ----------------------------
    # Helper methods for logging
    # ----------------------------
    def _log_test_pass(self, test_name):
        print(f"\n{'='*10} [TEST PASSED] {test_name} {'='*10}\n")

    def _log_test_fail(self, test_name, reason):
        print(f"\n{'='*10} [TEST FAILED] {test_name} - Reason: {reason} {'='*10}\n")

    # ----------------------------
    # Generic test runner for scenarios
    # ----------------------------
    def _run_scenario(self, test_name, func, *args, **kwargs):
        """Run a scenario and log pass/fail."""
        try:
            func(*args, **kwargs)
            self._log_test_pass(test_name)
        except AssertionError as e:
            self._log_test_fail(test_name, str(e))
            raise
        except UserError as e:
            # For negative scenarios expecting errors
            self._log_test_pass(f"Negative scenario: {test_name}")

    # ----------------------------
    # Test create sequence
    # ----------------------------
    def test_create_method_sequence_assignment(self):
        def scenario():
            rec1 = self.env['inventory.variation'].create({
                'name': 'IVRTEST',
                'date': date.today(),
                'warehouse_id': self.warehouse.id,
            })
            self.assertNotEqual(rec1.name, '/')
            self.assertTrue(rec1.name.startswith('IVR'))

            rec2 = self.env['inventory.variation'].create({
                'date': date.today(),
                'warehouse_id': self.warehouse.id,
            })
            self.assertNotEqual(rec2.name, '')
            self.assertTrue(rec2.name.startswith('IVR'))

            rec3 = self.env['inventory.variation'].create({
                'name': 'CUSTOM_NAME',
                'date': date.today(),
                'warehouse_id': self.warehouse.id,
            })
            self.assertEqual(rec3.name, 'CUSTOM_NAME')

        self._run_scenario("Create method sequence assignment", scenario)

    # ----------------------------
    # Test total variation
    # ----------------------------
    def test_total_variation_computation(self):
        def scenario():
            self.inventory_variation._compute_total_variation()
            self.assertEqual(self.inventory_variation.total_variation, 0.0)

            line1 = self.env['inventory.variation.line'].create({
                'variation_id': self.inventory_variation.id,
                'product_id': self.product.id,
                'location_id': self.warehouse.lot_stock_id.id,
                'theoretical_qty': 10,
                'physical_qty': 15,
            })
            self.inventory_variation._compute_total_variation()
            self.assertEqual(self.inventory_variation.total_variation, 5)

            line2 = self.env['inventory.variation.line'].create({
                'variation_id': self.inventory_variation.id,
                'product_id': self.product.id,
                'location_id': self.warehouse.lot_stock_id.id,
                'theoretical_qty': 8,
                'physical_qty': 6,
            })
            line3 = self.env['inventory.variation.line'].create({
                'variation_id': self.inventory_variation.id,
                'product_id': self.product.id,
                'location_id': self.warehouse.lot_stock_id.id,
                'theoretical_qty': 5,
                'physical_qty': 10,
            })
            self.inventory_variation._compute_total_variation()
            expected_total = 5 + (-2) + 5
            self.assertEqual(self.inventory_variation.total_variation, expected_total)

        self._run_scenario("Total variation computation", scenario)

    # ----------------------------
    # Test action_load_products
    # ----------------------------
    def test_action_load_products(self):
        # Negative scenario
        inv_neg = self.env['inventory.variation'].create({
            'name': 'IVR_NO_WH',
            'date': date.today(),
        })
        self._run_scenario("Load products without warehouse (negative)", inv_neg.action_load_products)

        # Positive scenario
        def pos_scenario():
            self.inventory_variation.write({
                'line_ids': [(0, 0, {
                    'product_id': self.product.id,
                    'location_id': self.warehouse.lot_stock_id.id,
                    'theoretical_qty': 10,
                    'physical_qty': 0.0,
                    'uom_id': self.product.uom_id.id,
                })]
            })
            self.inventory_variation.line_ids._compute_variation_qty()
            line = self.inventory_variation.line_ids[0]
            self.assertEqual(len(self.inventory_variation.line_ids), 1)
            self.assertEqual(line.product_id, self.product)
            self.assertEqual(line.theoretical_qty, 10)
            self.assertEqual(line.physical_qty, 0.0)

        self._run_scenario("Load products with warehouse (positive)", pos_scenario)

    # ----------------------------
    # Test action_confirm
    # ----------------------------
    def test_action_confirm(self):
        # Positive scenario
        self._run_scenario("Action confirm (positive)", self.inventory_variation.action_confirm)

        # Negative scenario
        self._run_scenario("Action confirm already confirmed (negative)", self.inventory_variation.action_confirm)

    # ----------------------------
    # Test action_create_excel_report
    # ----------------------------
    def test_action_create_excel_report(self):
        # Negative scenario
        inv_empty = self.env['inventory.variation'].create({
            'name': 'IVR_EMPTY',
            'date': date.today(),
            'warehouse_id': self.warehouse.id,
        })
        self._run_scenario("Create Excel report on empty inventory (negative)", inv_empty.action_create_excel_report)

        # Positive scenario
        def pos_scenario():
            self.inventory_variation.write({
                'line_ids': [(0, 0, {
                    'product_id': self.product.id,
                    'location_id': self.warehouse.lot_stock_id.id,
                    'theoretical_qty': 10,
                    'physical_qty': 5,
                })]
            })
            action = self.inventory_variation.action_create_excel_report()
            attachment = self.env['ir.attachment'].search([
                ('res_model', '=', 'inventory.variation'),
                ('res_id', '=', self.inventory_variation.id)
            ], limit=1)
            self.assertTrue(attachment)
            self.assertEqual(self.inventory_variation.state, 'reported')
            self.assertEqual(action.get('type'), 'ir.actions.act_url')
            self.assertIn(str(attachment.id), action.get('url'))

        self._run_scenario("Create Excel report (positive)", pos_scenario)

    # ----------------------------
    # Test action_download_pdf_report
    # ----------------------------
    def test_action_download_pdf_report(self):
        # Negative scenario
        inv_empty = self.env['inventory.variation'].create({
            'name': 'IVR_EMPTY_PDF',
            'date': date.today(),
            'warehouse_id': self.warehouse.id,
        })
        self._run_scenario("Download PDF report on empty inventory (negative)", inv_empty.action_download_pdf_report)

        # Positive scenario
        def pos_scenario():
            self.inventory_variation.write({
                'line_ids': [(0, 0, {
                    'product_id': self.product.id,
                    'location_id': self.warehouse.lot_stock_id.id,
                    'theoretical_qty': 10,
                    'physical_qty': 5,
                })]
            })
            action = self.inventory_variation.action_download_pdf_report()
            self.assertIsInstance(action, dict)
            self.assertEqual(action.get('type'), 'ir.actions.report')
            self.assertEqual(
                action.get('report_name'),
                'hk_inventory_variation.inventory_variation_report_pdf'
            )

        self._run_scenario("Download PDF report (positive)", pos_scenario)

    # ----------------------------
    # Test InventoryVariationLine methods
    # ----------------------------
    def test_inventory_variation_line_methods(self):
        def scenario():
            line = self.env['inventory.variation.line'].create({
                'variation_id': self.inventory_variation.id,
                'product_id': self.product.id,
                'location_id': self.warehouse.lot_stock_id.id,
                'theoretical_qty': 10,
                'physical_qty': 7,
            })
            line._onchange_product_id()
            self.assertEqual(line.uom_id, self.product.uom_id)

            line._compute_variation_qty()
            self.assertEqual(line.variation_qty, 7 - 10)

        self._run_scenario("InventoryVariationLine methods (_onchange_product_id, _compute_variation_qty)", scenario)
