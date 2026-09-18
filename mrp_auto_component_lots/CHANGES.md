# mrp_auto_component_lots — Production Date rename + Requested Date field (2026-09-17)

Two changes, both on the Manufacturing Order (MO) form. In plain terms:
one just relabels an existing date, the other adds a brand-new date that
gets filled in automatically — neither one changes how the MO itself
actually works (confirming, producing, approving, etc. all behave exactly
as before).

## 1. Renamed the date label to "Production Date"

**What:** the MO form has always had a date field for "when is this batch
scheduled/happening" — but Odoo's own screen confusingly showed **two
different names for the exact same field** depending on the order's stage:
"Scheduled Date" while it's still in early stages, then "Start Date" once
it moves into production. Both names, same field, same data — just an
inconsistent label.

**Why:** confusing to read a report or the form and see the date called
two different things for no real reason. Renamed both to one consistent
name: **"Production Date"**.

**How:** `views/mrp_production_views.xml` — added two small `<xpath>`
overrides that only change the *label text*, nothing else. The field
itself, what it stores, and when it's editable are all completely
untouched.

**Impact:** purely cosmetic. Nobody's data changes, no button or workflow
changes. Only the text on screen is different.

**A wrinkle worth knowing about:** Odoo's view system won't let you target
which of two same-named things to change by their text (i.e. you can't
say "the one that says Scheduled Date") — it only lets you target them by
their position in the file (1st one, 2nd one). So the fix relies on the
order these two labels appear in Odoo's own core file, which is unlikely
to change, but if a future Odoo upgrade reorders them, this rename could
silently apply to the wrong one. Low risk, but worth remembering if this
ever looks wrong again after an Odoo version upgrade.

## 2. New field: "Requested Date"

**What:** a brand new field that didn't exist before. It automatically
records the exact date and time someone clicks the **"Submit for
Approval"** button on an MO. Nobody can type into it or edit it — it's
read-only, set entirely by the system.

**Why:** there was no way before to see *when* an MO was actually
submitted for approval — only that it eventually got approved. This gives
a real timestamp for that specific moment, useful for tracking how long
approvals take.

**How:**
- `models/mrp_production.py` — added the `requested_date` field, and one
  line inside the existing `action_approved_submit` method (the code that
  already runs when that button is clicked) to stamp the current date/time
  into it.
- `views/mrp_production_views.xml` — added the field to the form, placed
  next to the other date fields (Production Date, Scheduled End).

**Impact:** purely additive. No existing field, button, or method's
behavior changed — this only adds one new column of data and displays it
in one new spot on the form. Existing MOs that were never submitted for
approval simply show this as blank, which is factually correct (it
genuinely never happened for them).

**A real bug hit and fixed while building this:** the first attempt placed
the new field using an xpath that (unknowingly) matched the *wrong* one of
two hidden-vs-visible fields with the same technical name in Odoo's core
view — so the date was being correctly recorded in the database the whole
time, but nothing showed up on screen. Fixed by pointing at the correct
(2nd, visible) one instead. Left a comment in the code explaining exactly
this trap, so nobody re-introduces it by "simplifying" the xpath later.

## Also touched, for these two changes to be usable elsewhere

The **Production Report** (`mo_cost_report` module) was separately updated
to show this same "Requested Date" as its own column, and to rename its
own "Scheduled Date" column to "Production Date" too, so both screens use
the same names. See that module's own `CHANGES.md` for details — that
module now also depends on this one, since it reads `requested_date`
directly.
