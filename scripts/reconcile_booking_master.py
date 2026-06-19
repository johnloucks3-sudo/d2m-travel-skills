#!/usr/bin/env python3
"""
MISSION-276: Reconcile z_MIGRATED booking IDs into main Booking Master.

Reads all 3 z_MIGRATED tabs, finds rows whose Booking_ID (col D) is NOT in
the main Booking Master tab, flags them with [MIGRATED_SOURCE: {tab}] in the
Notes column, and appends them to main.

CRITICAL: 2984034 is McLeod Regent Grandeur — FPD $11,943.15 due Jul 22, 2026.
This booking MUST land in main.

z_MIGRATED tabs are NOT deleted automatically — Commander reviews before deletion.
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, '/home/john/Thunderbird')
from core.booking.booking_master import BookingMasterClient

REPORT_PATH = '/home/john/Thunderbird/OpsCenter/state/booking_reconciliation_report.txt'
MAIN_TAB = 'Booking Master'
Z_TABS = [
    'z_MIGRATED_Booking Master Bucket',
    'z_MIGRATED_Booking Master A',
    'z_MIGRATED_Booking Master B',
]
CRITICAL_ID = '2984034'

# Column index of Booking_ID in both main and z_MIGRATED tabs (0-indexed = col D = index 3)
BID_COL = 3
# Column index of Notes in main tab (index 32 per audit)
NOTES_COL_MAIN = 32


def normalize_id(bid):
    return bid.strip() if bid else ''


def main():
    report_lines = [
        'BOOKING MASTER RECONCILIATION REPORT',
        f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S MT")}',
        '',
        'MISSION: Migrate z_MIGRATED rows with Booking_IDs not in main Booking Master.',
        f'CRITICAL: {CRITICAL_ID} (McLeod Regent Grandeur — FPD $11,943.15 due 2026-07-22) MUST land in main.',
        '',
    ]

    bmc = BookingMasterClient()
    ws = bmc._worksheet()
    spreadsheet = ws.spreadsheet

    # Step 1: Read main Booking Master — get all Booking_IDs (col D = index 3)
    print(f'Reading main tab: {MAIN_TAB}...')
    main_wks = spreadsheet.worksheet(MAIN_TAB)
    main_rows = main_wks.get_all_values()
    main_headers = main_rows[0] if main_rows else []
    main_col_count = len(main_headers)

    main_ids = set()
    for r in main_rows[1:]:
        bid = normalize_id(r[BID_COL]) if len(r) > BID_COL else ''
        if bid:
            main_ids.add(bid)

    print(f'Main tab: {len(main_ids)} unique Booking_IDs, {len(main_rows)-1} data rows, {main_col_count} columns')
    report_lines.append(f'Main "{MAIN_TAB}" tab: {len(main_ids)} unique Booking_IDs, {len(main_rows)-1} data rows')
    report_lines.append(f'Existing IDs: {sorted(main_ids)}')
    report_lines.append('')

    # Step 2: Process each z_MIGRATED tab
    # We de-duplicate across tabs: once a Booking_ID is queued for append,
    # skip it from subsequent tabs (use best source = Bucket, then A, then B order)
    all_rows_to_append = []
    queued_ids = set()
    tab_summaries = {}

    for tab_name in Z_TABS:
        print(f'\nProcessing: {tab_name}...')
        try:
            wks = spreadsheet.worksheet(tab_name)
        except Exception as e:
            print(f'  WARNING: Could not open {tab_name}: {e}')
            report_lines.append(f'WARNING: Could not open "{tab_name}": {e}')
            continue

        all_tab_rows = wks.get_all_values()
        if not all_tab_rows:
            print(f'  Tab empty.')
            tab_summaries[tab_name] = {'total': 0, 'unique': 0, 'unique_ids': []}
            continue

        tab_headers = all_tab_rows[0]
        data_rows = all_tab_rows[1:]
        non_empty = [r for r in data_rows if any(c.strip() for c in r)]

        print(f'  Non-empty rows: {len(non_empty)}')
        print(f'  Headers: {tab_headers[:8]}')

        # Build header->index map for this tab
        tab_col_map = {h.strip(): i for i, h in enumerate(tab_headers)}

        unique_rows = []
        unique_ids = []
        skipped_in_main = 0
        skipped_queued = 0
        skipped_no_id = 0

        for row in non_empty:
            bid = normalize_id(row[BID_COL]) if len(row) > BID_COL else ''
            if not bid:
                skipped_no_id += 1
                continue
            if bid in main_ids:
                skipped_in_main += 1
                continue
            if bid in queued_ids:
                skipped_queued += 1
                continue

            # Build a row in main schema: pad/trim to main_col_count
            # Map by header name where headers match; fill blanks otherwise
            mapped = [''] * main_col_count
            for main_idx, main_col in enumerate(main_headers):
                if main_idx >= main_col_count:
                    break
                col_name = main_col.strip()
                if col_name in tab_col_map:
                    src_idx = tab_col_map[col_name]
                    if src_idx < len(row):
                        mapped[main_idx] = row[src_idx].strip()

            # Always set Booking_ID (col 3) explicitly
            mapped[BID_COL] = bid

            # Flag Notes column with migration source
            if NOTES_COL_MAIN < main_col_count:
                existing_notes = mapped[NOTES_COL_MAIN]
                flag = f'[MIGRATED_SOURCE: {tab_name}]'
                if existing_notes:
                    mapped[NOTES_COL_MAIN] = f'{flag} {existing_notes}'
                else:
                    mapped[NOTES_COL_MAIN] = flag

            unique_rows.append(mapped)
            unique_ids.append(bid)
            queued_ids.add(bid)

        print(f'  Unique rows to append: {len(unique_rows)}')
        print(f'  Unique IDs: {unique_ids}')
        print(f'  Skipped (in main): {skipped_in_main}, (already queued): {skipped_queued}, (no ID): {skipped_no_id}')

        tab_summaries[tab_name] = {
            'total': len(non_empty),
            'unique': len(unique_rows),
            'unique_ids': unique_ids,
            'skipped_in_main': skipped_in_main,
            'skipped_queued': skipped_queued,
            'skipped_no_id': skipped_no_id,
        }

        report_lines.append(f'Tab: "{tab_name}"')
        report_lines.append(f'  Non-empty rows: {len(non_empty)}')
        report_lines.append(f'  Unique rows to append: {len(unique_rows)}')
        report_lines.append(f'  Unique IDs: {unique_ids}')
        report_lines.append(f'  Skipped (in main): {skipped_in_main}, (already queued): {skipped_queued}, (no ID): {skipped_no_id}')
        report_lines.append('')

        all_rows_to_append.extend(unique_rows)

    # Step 3: Append unique rows to main Booking Master
    print(f'\nTotal rows to append: {len(all_rows_to_append)}')
    report_lines.append('APPEND PHASE')
    report_lines.append(f'Total rows to append: {len(all_rows_to_append)}')
    report_lines.append(f'IDs to append: {sorted(queued_ids)}')
    report_lines.append('')

    if all_rows_to_append:
        print(f'Appending {len(all_rows_to_append)} rows to main Booking Master...')
        main_wks.append_rows(all_rows_to_append, value_input_option='USER_ENTERED')
        print('Append complete.')
        report_lines.append(f'Appended {len(all_rows_to_append)} rows successfully.')

        # Step 4: Verify — re-read main and confirm all appended IDs are present
        print('Verifying...')
        verify_rows = main_wks.get_all_values()
        verify_ids = set()
        for r in verify_rows[1:]:
            bid = normalize_id(r[BID_COL]) if len(r) > BID_COL else ''
            if bid:
                verify_ids.add(bid)

        missing = [bid for bid in queued_ids if bid not in verify_ids]
        if missing:
            print(f'ERROR: IDs missing after append: {missing}')
            report_lines.append(f'ERROR: IDs missing after append: {missing}')
            write_report(report_lines)
            sys.exit(1)
        else:
            print('Verification PASSED — all appended IDs confirmed.')
            report_lines.append('Verification PASSED — all appended IDs confirmed in main tab.')

        # Critical check: 2984034
        if CRITICAL_ID in verify_ids:
            print(f'CRITICAL CHECK PASSED: {CRITICAL_ID} (McLeod Regent Grandeur) is present in main Booking Master.')
            report_lines.append(f'CRITICAL CHECK PASSED: {CRITICAL_ID} (McLeod Regent Grandeur — FPD $11,943.15 due 2026-07-22) confirmed in main.')
        else:
            # It was already there or got missed
            if CRITICAL_ID in main_ids:
                print(f'CRITICAL CHECK: {CRITICAL_ID} was already in main before this run.')
                report_lines.append(f'CRITICAL CHECK: {CRITICAL_ID} was already in main before this run (no append needed).')
            else:
                print(f'CRITICAL FAILURE: {CRITICAL_ID} NOT in main after append!')
                report_lines.append(f'CRITICAL FAILURE: {CRITICAL_ID} NOT found in main after append — manual intervention required!')
    else:
        print('No unique rows found — main already contains all z_MIGRATED Booking_IDs.')
        report_lines.append('No unique rows to append — all z_MIGRATED Booking_IDs already in main.')
        # Still do critical check
        if CRITICAL_ID in main_ids:
            print(f'CRITICAL CHECK: {CRITICAL_ID} already present in main Booking Master.')
            report_lines.append(f'CRITICAL CHECK PASSED: {CRITICAL_ID} (McLeod Regent Grandeur) already in main.')
        else:
            print(f'WARNING: {CRITICAL_ID} NOT in main and NOT in z_MIGRATED unique rows — investigate!')
            report_lines.append(f'WARNING: {CRITICAL_ID} NOT found in main and not in z_MIGRATED unique rows.')

    # Step 5: Commander review note — do NOT delete z_MIGRATED tabs
    report_lines.append('')
    report_lines.append('z_MIGRATED TAB STATUS')
    report_lines.append('The z_MIGRATED tabs have NOT been deleted automatically.')
    report_lines.append('Commander should review before deletion:')
    for tab_name in Z_TABS:
        report_lines.append(f'  - {tab_name}')
    report_lines.append('')
    report_lines.append('To delete after review, run: spreadsheet.del_worksheet(spreadsheet.worksheet(<tab_name>))')
    report_lines.append('Or delete manually from Google Sheets.')

    # Summary
    report_lines.append('')
    report_lines.append('FINAL SUMMARY')
    for tab_name, summary in tab_summaries.items():
        report_lines.append(f'  {tab_name}: {summary.get("unique", 0)} unique rows migrated')
    report_lines.append(f'Total migrated: {len(all_rows_to_append)} rows')
    report_lines.append(f'Completed: {datetime.now().strftime("%Y-%m-%d %H:%M:%S MT")}')

    write_report(report_lines)
    print(f'\nReport written to: {REPORT_PATH}')


def write_report(lines):
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, 'w') as f:
        f.write('\n'.join(lines) + '\n')


if __name__ == '__main__':
    main()
