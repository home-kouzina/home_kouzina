from datetime import date
from collections import Counter

# ==================== CONFIG — change dates here only ====================
FROM_DAY = '2025-07-01'          # include cancellations ON/AFTER this date
TO_DAY   = '2026-07-01'          # EXCLUDE cancellations on/after this (i.e. up to 2026-06-30)

# Shopify fetch window on updated_at — kept wider than the range to catch late-updated orders
FETCH_UPDATED_MIN = '2025-07-01T00:00:00+05:30'
FETCH_UPDATED_MAX = '2026-07-21T00:00:00+05:30'

DRY_RUN    = True                # True = report only, NO ledger writes. Flip to False to actually run.
REASON_TAG = 'Order cancelled in Shopify \u2014 no payment collected (Jul 2025\u2013Jun 2026 backfill)'
# =========================================================================

# ---- 1. Pull cancelled orders from Shopify ----
instance = env['shopify.instance.ept'].search([], limit=1)
instance.connect_in_shopify()

all_orders = []
page = shopify_lib.Order.find(status='cancelled',
                              updated_at_min=FETCH_UPDATED_MIN,
                              updated_at_max=FETCH_UPDATED_MAX,
                              limit=250)
while page:
    all_orders.extend(page)
    page = shopify_lib.Order.find(from_=page.next_page_url) if page.next_page_url else None
print('Total cancelled orders pulled from Shopify:', len(all_orders))

# ---- 2. Keep only those cancelled within the range; map name -> cancel date ----
cancel_date_map = {}
for o in all_orders:
    d = o.to_dict()
    ca = d.get('cancelled_at')
    if not ca:
        continue
    day = ca[:10]                       # 'YYYY-MM-DD'
    if FROM_DAY <= day < TO_DAY:
        cancel_date_map[d.get('name')] = day

print('Cancelled orders within range %s .. %s : %d' % (FROM_DAY, TO_DAY, len(cancel_date_map)))
# per-month breakdown, useful for reconciliation
by_month = Counter(v[:7] for v in cancel_date_map.values())
for m in sorted(by_month):
    print('   %s : %d' % (m, by_month[m]))

all_names = list(cancel_date_map.keys())

# ---- 3. Which of those are cancelled in Odoo ----
env.cr.execute("""
    SELECT id, name FROM sale_order
    WHERE name = ANY(%s) AND state = 'cancel'
""", (all_names,))
cancelled_rows = env.cr.fetchall()
print('Cancelled sale orders found in Odoo:', len(cancelled_rows))

# ---- 4. Has a posted invoice AND no posted refund yet ----
needs_fix = []
for so_id, so_name in cancelled_rows:
    env.cr.execute("""
        SELECT id FROM account_move
        WHERE invoice_origin = %s AND move_type = 'out_invoice' AND state = 'posted'
    """, (so_name,))
    posted_invoices = env.cr.fetchall()

    env.cr.execute("""
        SELECT id FROM account_move
        WHERE invoice_origin = %s AND move_type = 'out_refund' AND state = 'posted'
    """, (so_name,))
    has_refund = env.cr.fetchall()

    if posted_invoices and not has_refund:
        needs_fix.append((so_id, so_name, [p[0] for p in posted_invoices], cancel_date_map.get(so_name)))

print()
print('Total orders needing a credit note:', len(needs_fix))

# ---- 5. Fiscal-lock pre-check (a full year WILL cross closed periods) ----
lock_date = env.company.fiscalyear_lock_date      # date or False (hard lock)
soft_lock = env.company.period_lock_date          # date or False (advisers-only lock)
print('Fiscal year lock date:', lock_date, '| period lock date:', soft_lock)

runnable, locked = [], []
for so_id, so_name, invoice_ids, cancel_date in needs_fix:
    cdate = fields.Date.from_string(cancel_date)
    if lock_date and cdate <= lock_date:
        locked.append((so_name, cancel_date))
    else:
        runnable.append((so_id, so_name, invoice_ids, cancel_date))

if locked:
    print('!! %d orders fall in a LOCKED period and will be skipped:' % len(locked))
    for r in locked:
        print('   LOCKED', r)

# ---- 6. Totals to be reversed (runnable only) ----
total_amount = 0
for so_id, so_name, invoice_ids, cancel_date in runnable:
    invoices = env['account.move'].browse(invoice_ids)
    total_amount += sum(invoices.mapped('amount_total'))
print()
print('Runnable now:', len(runnable), '| Total amount to be reversed:', total_amount)
for r in runnable:
    print('   ', r)

# ---- 7. Execute (only when DRY_RUN = False) ----
if DRY_RUN:
    print()
    print('DRY RUN — nothing written. Review the list above, then set DRY_RUN = False and re-run.')
else:
    results = []
    for so_id, so_name, invoice_ids, cancel_date in runnable:
        try:
            invoices = env['account.move'].browse(invoice_ids)
            reversal = env['account.move.reversal'].with_context(
                active_model='account.move', active_ids=invoices.ids
            ).create({
                'reason': REASON_TAG,
                'journal_id': invoices[0].journal_id.id,
                'date': cancel_date,
            })
            reversal.reverse_moves()
            new_moves = getattr(reversal, 'new_move_ids', env['account.move'])
            results.append((so_name, 'CREATED', cancel_date,
                            new_moves.mapped('name'), new_moves.mapped('state')))
            env.cr.commit()
        except Exception as e:
            env.cr.rollback()
            results.append((so_name, 'FAILED: ' + str(e), cancel_date, [], []))

    print('Done. Results:')
    for r in results:
        print(r)