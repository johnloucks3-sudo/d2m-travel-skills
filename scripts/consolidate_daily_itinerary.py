#!/usr/bin/env python3
"""
MISSION-275: Consolidate Daily Itinerary sub-tabs into main tab.

Reads Daily Itinerary A, B, and Bucket; finds rows with Booking_IDs not
already in the main Daily Itinerary tab; maps columns to main schema; appends
unique rows; then deletes the sub-tabs.

Main schema: Booking_ID, Day_Number, Date, Port_Location, Arrive, Depart,
             Romance_Narrative, Description, Source_Tab
"""

import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, '/home/john/Thunderbird')
from core.booking.booking_master import BookingMasterClient

REPORT_PATH = '/home/john/Thunderbird/OpsCenter/state/itinerary_consolidation_report.txt'
MAIN_TAB = 'Daily Itinerary'
SUB_TABS = ['Daily Itinerary A', 'Daily Itinerary B', 'Daily Itinerary Bucket']

# Column mapping: source header -> main schema field
# Main schema: Booking_ID, Day_Number, Date, Port_Location, Arrive, Depart, Romance_Narrative, Description, Source_Tab
MAIN_COLS = ['Booking_ID', 'Day_Number', 'Date', 'Port_Location', 'Arrive', 'Depart', 'Romance_Narrative', 'Description', 'Source_Tab']

# Known header aliases -> main column name
HEADER_MAP = {
    # Exact matches
    'Booking_ID': 'Booking_ID',
    'Day_Number': 'Day_Number',
    'Date': 'Date',
    'Port_Location': 'Port_Location',
    'Arrive': 'Arrive',
    'Depart': 'Depart',
    'Romance_Narrative': 'Romance_Narrative',
    'Description': 'Description',
    # Sub-tab aliases
    'Day Number': 'Day_Number',
    'Port/Location': 'Port_Location',
    'Port_Location': 'Port_Location',
    'Romance/Narrative': 'Romance_Narrative',
    'Desription ': 'Description',      # misspelled w/ trailing space
    'Desription': 'Description',
    'Description ': 'Description',     # trailing space
    'Docking Time': 'Arrive',
    'Departure Time': 'Depart',
}


def normalize_id(bid):
    return bid.strip() if bid else ''


def build_row_dict(headers, row):
    """Build {main_col: value} from a source row using header mapping."""
    d = {}
    for i, h in enumerate(headers):
        main_col = HEADER_MAP.get(h.strip())
        if main_col and i < len(row):
            # Don't overwrite if already set (first mapping wins)
            if main_col not in d:
                d[main_col] = row[i].strip() if row[i] else ''
    return d


def row_to_main_list(d, source_tab):
    """Convert a dict to a list in main column order."""
    result = []
    for col in MAIN_COLS:
        if col == 'Source_Tab':
            result.append(source_tab)
        else:
            result.append(d.get(col, ''))
    return result


def main():
    report_lines = [
        f'DAILY ITINERARY CONSOLIDATION REPORT',
        f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S MT")}',
        f'',
    ]

    bmc = BookingMasterClient()
    ws = bmc._worksheet()
    spreadsheet = ws.spreadsheet

    # Step 1: Read main tab
    print(f'Reading main tab: {MAIN_TAB}...')
    main_wks = spreadsheet.worksheet(MAIN_TAB)
    main_rows = main_wks.get_all_values()
    main_headers = main_rows[0] if main_rows else []

    # Collect existing Booking_IDs from main
    main_ids = set()
    for r in main_rows[1:]:
        bid = normalize_id(r[0]) if r else ''
        if bid:
            main_ids.add(bid)

    print(f'Main tab has {len(main_ids)} unique Booking_IDs, {len(main_rows)-1} data rows')
    report_lines.append(f'Main "{MAIN_TAB}" tab: {len(main_ids)} unique Booking_IDs, {len(main_rows)-1} data rows')
    report_lines.append(f'Existing IDs: {sorted(main_ids)}')
    report_lines.append('')

    # Step 2: Process each sub-tab
    rows_to_append = []  # List of (row_list, source_tab)
    sub_tab_summaries = {}

    for tab_name in SUB_TABS:
        print(f'\nProcessing sub-tab: {tab_name}...')
        try:
            wks = spreadsheet.worksheet(tab_name)
        except Exception as e:
            print(f'  WARNING: Could not open {tab_name}: {e}')
            report_lines.append(f'WARNING: Could not open "{tab_name}": {e}')
            continue

        all_rows = wks.get_all_values()
        if not all_rows:
            print(f'  Tab is empty — no data')
            sub_tab_summaries[tab_name] = {'total': 0, 'unique': 0, 'unique_ids': []}
            continue

        headers = all_rows[0]
        data_rows = all_rows[1:]
        non_empty_rows = [r for r in data_rows if any(c.strip() for c in r)]

        print(f'  Headers: {headers[:8]}...' if len(headers) > 8 else f'  Headers: {headers}')
        print(f'  Non-empty data rows: {len(non_empty_rows)}')

        # Find rows with Booking_IDs not in main
        unique_rows = []
        unique_ids_found = set()
        skipped_no_id = 0
        skipped_already_in_main = 0

        for row in non_empty_rows:
            bid = normalize_id(row[0]) if row else ''
            if not bid:
                skipped_no_id += 1
                continue
            if bid in main_ids:
                skipped_already_in_main += 1
                continue
            # Unique row
            row_dict = build_row_dict(headers, row)
            row_dict['Booking_ID'] = bid
            mapped_row = row_to_main_list(row_dict, tab_name)
            unique_rows.append((mapped_row, bid))
            unique_ids_found.add(bid)

        print(f'  Unique rows (not in main): {len(unique_rows)}')
        print(f'  Skipped (no ID): {skipped_no_id}, Already in main: {skipped_already_in_main}')

        sub_tab_summaries[tab_name] = {
            'total': len(non_empty_rows),
            'unique': len(unique_rows),
            'unique_ids': sorted(unique_ids_found),
            'skipped_no_id': skipped_no_id,
            'skipped_in_main': skipped_already_in_main,
        }

        report_lines.append(f'Sub-tab: "{tab_name}"')
        report_lines.append(f'  Non-empty rows: {len(non_empty_rows)}')
        report_lines.append(f'  Unique rows (not in main): {len(unique_rows)}')
        report_lines.append(f'  Unique Booking_IDs: {sorted(unique_ids_found)}')
        report_lines.append(f'  Skipped (no ID): {skipped_no_id}')
        report_lines.append(f'  Already in main: {skipped_already_in_main}')
        report_lines.append('')

        rows_to_append.extend(unique_rows)
        # Update main_ids set in memory so subsequent tabs don't double-append
        main_ids.update(unique_ids_found)

    # Step 3: Append unique rows to main tab
    print(f'\nTotal unique rows to append: {len(rows_to_append)}')
    report_lines.append(f'APPEND PHASE')
    report_lines.append(f'Total unique rows to append: {len(rows_to_append)}')

    if rows_to_append:
        append_data = [r[0] for r in rows_to_append]
        append_ids = [r[1] for r in rows_to_append]
        print(f'Appending {len(append_data)} rows to main tab...')
        main_wks.append_rows(append_data, value_input_option='USER_ENTERED')
        print('Append complete.')
        report_lines.append(f'Appended {len(append_data)} rows. IDs: {append_ids}')

        # Step 4: Verify append — re-read main and confirm all IDs present
        print('Verifying append...')
        verify_rows = main_wks.get_all_values()
        verify_ids = set(normalize_id(r[0]) for r in verify_rows[1:] if r)
        missing_after = [bid for bid in append_ids if bid not in verify_ids]
        if missing_after:
            print(f'ERROR: These IDs were not found after append: {missing_after}')
            report_lines.append(f'ERROR: IDs missing after append: {missing_after}')
            report_lines.append('Sub-tabs NOT deleted due to verification failure.')
            write_report(report_lines)
            sys.exit(1)
        else:
            print('Verification passed — all appended IDs confirmed in main tab.')
            report_lines.append('Verification PASSED — all appended IDs confirmed in main tab.')
    else:
        print('No unique rows found — all sub-tab data already exists in main tab.')
        report_lines.append('No unique rows found — all sub-tab data already exists in main tab.')
        report_lines.append('Sub-tabs are safe to delete (no unique data).')

    # Step 5: Delete sub-tabs (only after confirming no unique data remains)
    report_lines.append('')
    report_lines.append('DELETE PHASE')
    for tab_name in SUB_TABS:
        summary = sub_tab_summaries.get(tab_name)
        if summary is None:
            print(f'Skipping delete of {tab_name} (could not open earlier)')
            report_lines.append(f'  SKIPPED delete: "{tab_name}" (could not open earlier)')
            continue

        unique_count = summary.get('unique', 0)
        if unique_count > 0 and len(rows_to_append) == 0:
            # This shouldn't happen if logic is correct, but be safe
            print(f'WARNING: {tab_name} had {unique_count} unique rows but none were appended — NOT deleting')
            report_lines.append(f'  WARNING: NOT deleting "{tab_name}" — {unique_count} unique rows but no append executed')
            continue

        try:
            wks = spreadsheet.worksheet(tab_name)
            spreadsheet.del_worksheet(wks)
            print(f'Deleted sub-tab: {tab_name}')
            report_lines.append(f'  DELETED: "{tab_name}"')
        except Exception as e:
            print(f'ERROR deleting {tab_name}: {e}')
            report_lines.append(f'  ERROR deleting "{tab_name}": {e}')

    # Final summary
    report_lines.append('')
    report_lines.append('SUMMARY')
    for tab_name, summary in sub_tab_summaries.items():
        report_lines.append(f'  {tab_name}: {summary.get("unique", 0)} unique rows migrated, tab deleted')
    report_lines.append(f'Completed: {datetime.now().strftime("%Y-%m-%d %H:%M:%S MT")}')

    write_report(report_lines)
    print(f'\nReport written to: {REPORT_PATH}')


def write_report(lines):
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, 'w') as f:
        f.write('\n'.join(lines) + '\n')


if __name__ == '__main__':
    main()
