"""
Management command: import portal credentials from the Master Bid Tracker Excel.

Usage:
    python manage.py import_credentials --file=/path/to/tracker.xlsx
    python manage.py import_credentials --file=... --clear          # wipe existing before import
    python manage.py import_credentials --file=... --sheet=HQ       # single sheet only
    python manage.py import_credentials --file=... --dry-run        # preview without saving

Credential sheets are any sheet whose name is NOT in BID_SHEETS.
Each sheet name becomes the Client shortcode. Client is created if it doesn't exist.
"""

import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, DatabaseError

from bids.models import Client, PortalCredential

# Sheets that contain bid data — skip these
BID_SHEETS = {'2026 Bids', '2024 Bids', '2025 Bids', 'Sheet17'}


def _find(cols, *candidates):
    """Return first column name that matches any candidate (case-insensitive, strip)."""
    normalised = {c.strip().lower(): c for c in cols}
    for cand in candidates:
        if cand.strip().lower() in normalised:
            return normalised[cand.strip().lower()]
    return None


def _clean(val) -> str:
    """Return string or '' for NaN / None."""
    if val is None:
        return ''
    s = str(val).strip()
    return '' if s.lower() in ('nan', 'none', 'nat') else s


def _map_row(row, cols) -> dict | None:
    """
    Map a DataFrame row to PortalCredential field dict.
    Returns None if the row has no usable data.

    Handles five column layouts found in the tracker:
      Standard  : State, Agency, Portal Name, ID, Password, Link/Portal Link
      UHCS      : State, Link, Username, Password, Customer/Vendor Number
      FCH       : same as standard but 'Password ' (trailing space)
      Connvertex: Name of States, Portal URL, URL Login Status, Bid URL,
                  User ID, Password, Email Id, Notes, Security Question Answer
    """
    get = lambda *cands: _clean(row.get(_find(cols, *cands), ''))

    username = get('ID', 'User ID', 'Username')
    password = get('Password', 'Password ')       # FCH has trailing space
    state    = get('State', 'Name of States')
    agency   = get('Agency')
    portal   = get('Portal Name')
    link     = get('Link', 'Portal Link', 'Portal URL')

    # Aggregate extra metadata columns into notes
    notes_parts = []
    for cand, label in [
        ('URL Login Status',        'login_status'),
        ('Email Id',                'email'),
        ('Security Question Answer','security_qa'),
        ('Customer/Vendor Number',  'vendor_no'),
        ('Bid URL',                 'bid_url'),
        ('Notes',                   'notes'),
    ]:
        col = _find(cols, cand)
        if col:
            v = _clean(row.get(col, ''))
            if v:
                notes_parts.append(f"{label}: {v}")

    # Skip entirely empty rows
    if not any([username, password, state, agency, portal, link]):
        return None

    return {
        'state':       state,
        'agency':      agency,
        'portal_name': portal,
        'username':    username,
        'password':    password,
        'link':        link,
        'notes':       '\n'.join(notes_parts),
    }


class Command(BaseCommand):
    help = 'Import portal credentials from Master Bid Tracker Excel into PortalCredential table'

    def add_arguments(self, parser):
        parser.add_argument('--file', required=True, help='Path to the .xlsx file')
        parser.add_argument('--sheet', default=None, help='Import only this sheet (default: all credential sheets)')
        parser.add_argument('--clear', action='store_true', help='Delete existing credentials for affected clients before import')
        parser.add_argument('--dry-run', action='store_true', dest='dry_run', help='Preview rows without saving')

    def handle(self, *args, **options):
        path     = options['file']
        only     = options['sheet']
        clear    = options['clear']
        dry_run  = options['dry_run']

        try:
            xl = pd.ExcelFile(path)
        except Exception as e:
            raise CommandError(f"Cannot open file: {e}")

        sheets = xl.sheet_names
        credential_sheets = [s for s in sheets if s.strip() not in BID_SHEETS]

        if only:
            if only not in credential_sheets:
                raise CommandError(
                    f"Sheet '{only}' not found or is a bid sheet.\n"
                    f"Available credential sheets: {credential_sheets}"
                )
            credential_sheets = [only]

        self.stdout.write(f"\nFound {len(credential_sheets)} credential sheet(s): {credential_sheets}\n")

        total_created = total_skipped = total_errors = 0

        for sheet_name in credential_sheets:
            shortcode = sheet_name.strip()
            self.stdout.write(self.style.HTTP_INFO(f"\n── Sheet: {sheet_name!r} (shortcode={shortcode!r}) ──"))

            try:
                df = xl.parse(sheet_name, header=0)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  Cannot parse sheet: {e}"))
                total_errors += 1
                continue

            # Drop fully-empty rows and normalise column names
            df = df.dropna(how='all')
            cols = list(df.columns)
            self.stdout.write(f"  Columns: {cols}")
            self.stdout.write(f"  Rows (non-empty): {len(df)}")

            if dry_run:
                # Show first 3 mapped rows
                preview_count = 0
                for _, row in df.iterrows():
                    mapped = _map_row(row, cols)
                    if mapped and preview_count < 3:
                        self.stdout.write(f"  [preview] {mapped}")
                        preview_count += 1
                continue

            with transaction.atomic():
                # Get or create the Client
                client, client_created = Client.objects.get_or_create(
                    shortcode=shortcode,
                    defaults={'name': shortcode}
                )
                if client_created:
                    self.stdout.write(self.style.SUCCESS(f"  Created client: {shortcode}"))
                else:
                    self.stdout.write(f"  Using existing client: {client.name} ({shortcode})")

                if clear:
                    deleted, _ = PortalCredential.objects.filter(client=client).delete()
                    self.stdout.write(self.style.WARNING(f"  Cleared {deleted} existing credentials"))

                created = skipped = errors = 0
                for idx, row in df.iterrows():
                    mapped = _map_row(row, cols)
                    if mapped is None:
                        skipped += 1
                        continue

                    sid = transaction.savepoint()
                    try:
                        # Upsert on (client, portal_name, username) — avoids duplicates on re-run
                        lookup = {'client': client}
                        if mapped['portal_name']:
                            lookup['portal_name'] = mapped['portal_name']
                        if mapped['username']:
                            lookup['username'] = mapped['username']

                        if len(lookup) == 1:
                            PortalCredential.objects.create(client=client, **mapped)
                        else:
                            existing = PortalCredential.objects.filter(**lookup).first()
                            update_fields = {k: v for k, v in mapped.items()
                                             if k not in ('portal_name', 'username')}
                            if existing:
                                for k, v in update_fields.items():
                                    setattr(existing, k, v)
                                existing.save()
                            else:
                                PortalCredential.objects.create(client=client, **mapped)
                        transaction.savepoint_commit(sid)
                        created += 1
                    except Exception as e:
                        transaction.savepoint_rollback(sid)
                        self.stdout.write(self.style.ERROR(f"  Row {idx}: {e}"))
                        errors += 1

                self.stdout.write(
                    self.style.SUCCESS(f"  ✓ created/updated: {created}") +
                    (f"  skipped (empty): {skipped}" if skipped else '') +
                    (self.style.ERROR(f"  errors: {errors}") if errors else '')
                )
                total_created += created
                total_skipped += skipped
                total_errors  += errors

        self.stdout.write('\n' + '─' * 50)
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — nothing saved."))
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Done.  Created/updated: {total_created}  "
                                   f"Skipped: {total_skipped}  Errors: {total_errors}")
            )
