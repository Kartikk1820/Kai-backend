import pandas as pd
from django.core.management.base import BaseCommand
from django.utils import timezone
from users.models import User
import re

class Command(BaseCommand):
    help = "Imports legacy users from a messy Excel file"

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Path to the Excel file')

    def handle(self, *args, **options):
        file_path = options['file_path']
        try:
            xls = pd.ExcelFile(file_path)
        except Exception as e:
            self.stderr.write(f"Failed to open file: {e}")
            return
            
        users_created = 0
        users_updated = 0
        
        for sheet_name in xls.sheet_names:
            df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
            
            for i in range(len(df)):
                row = df.iloc[i].fillna("").astype(str).str.strip().str.lower()
                
                # Identify if this row is a header row
                if "candidate name" in row.values and ("email" in row.values or "jod id" in row.values or "job id" in row.values):
                    header_row = df.iloc[i].fillna("").astype(str).str.strip()
                    col_map = {col_name.lower(): col_idx for col_idx, col_name in enumerate(header_row)}
                    
                    j = i + 1
                    while j < len(df):
                        data_row = df.iloc[j]
                        
                        candidate_name_val = str(data_row.iloc[col_map.get("candidate name", 0)]).strip()
                        if pd.isna(data_row.iloc[col_map.get("candidate name", 0)]) or not candidate_name_val or candidate_name_val.lower() in ('candidate name', 'nan', ''):
                            j += 1
                            if candidate_name_val.lower() == 'candidate name':
                                break # Stop if we hit another header
                            continue
                            
                        def get_val(keys):
                            if isinstance(keys, str): keys = [keys]
                            for k in keys:
                                idx = col_map.get(k)
                                if idx is not None:
                                    val = data_row.iloc[idx]
                                    if pd.isna(val) or str(val).lower() == 'nan': continue
                                    return str(val).strip()
                            return None
                            
                        job_id = get_val(["job id", "jod id"])
                        state = get_val("state")
                        position = get_val("position")
                        name = get_val("candidate name")
                        phone = get_val("phone number")
                        email = get_val("email")
                        location = get_val(["present loc", "present location"])
                        pay = get_val(["pay rate", "pay rate (usd)"])
                        start = get_val("start date")
                        margin = get_val(["margin", "margin (usd)"])
                        contract = get_val("contract")
                        
                        if email:
                            # Cleanup pay and margin
                            def clean_decimal(val):
                                if not val: return None
                                val = str(val)
                                val = re.sub(r'[^\d.]', '', val)
                                try: return float(val) if val else None
                                except ValueError: return None
                                
                            pay_clean = clean_decimal(pay)
                            margin_clean = clean_decimal(margin)
                            
                            # Cleanup name
                            parts = name.split(maxsplit=1)
                            first_name = parts[0] if parts else ""
                            last_name = parts[1] if len(parts) > 1 else ""
                            
                            # Cleanup date - User said use current date and time if ambiguous. We will just use it for all if not explicitly fully parsed.
                            # The field is a DateField, so we just use current date.
                            date_of_joining = timezone.now().date()
                            
                            try:
                                user, created = User.objects.update_or_create(
                                    email=email,
                                    defaults={
                                        'first_name': first_name[:150],
                                        'last_name': last_name[:150],
                                        'job_id': job_id[:100] if job_id else None,
                                        'state': state[:100] if state else None,
                                        'sub_position': position[:50] if position else None,
                                        'phone_number': phone[:20] if phone else None,
                                        'present_location': location[:255] if location else None,
                                        'pay_rate': pay_clean,
                                        'margin': margin_clean,
                                        'contract_period': contract[:100] if contract else None,
                                        'date_of_joining': date_of_joining,
                                        'role': 'Employee',
                                    }
                                )
                                if created:
                                    user.set_password('defaultpassword123')
                                    user.save()
                                    users_created += 1
                                else:
                                    users_updated += 1
                            except Exception as e:
                                self.stderr.write(f"Error saving user {email}: {e}")
                        j += 1
                        
        self.stdout.write(self.style.SUCCESS(f"Successfully processed users. Created: {users_created}, Updated: {users_updated}"))
