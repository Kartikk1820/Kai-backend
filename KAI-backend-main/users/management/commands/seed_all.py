"""
seed_all — full company snapshot seed
======================================
Targets:
  - 10 managers, 50 employees, 5 HR staff, 100 client users
  - 100 client companies
  - 500 bid opportunities
  - ~1 000 client bids
  - 20 sprints (10-20 tasks each)
  - 200 backlog tasks
  - 1 year of attendance per employee (with sessions)
  - 30 pending leave applications + ~180 approved/rejected historical ones
  - ~4 notifications per internal user

All passwords: Demo@1234
"""
import random
import string
from datetime import date, timedelta, time
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction

User = get_user_model()

# ── Name pools ────────────────────────────────────────────────────────────────

FIRST_NAMES = [
    "James","Mary","Robert","Patricia","John","Jennifer","Michael","Linda",
    "William","Barbara","David","Elizabeth","Richard","Susan","Joseph","Jessica",
    "Thomas","Sarah","Charles","Karen","Christopher","Lisa","Daniel","Nancy",
    "Matthew","Betty","Anthony","Margaret","Mark","Sandra","Donald","Ashley",
    "Steven","Kimberly","Paul","Emily","Andrew","Donna","Joshua","Michelle",
    "Kenneth","Dorothy","Kevin","Carol","Brian","Amanda","George","Melissa",
    "Timothy","Deborah","Ronald","Stephanie","Edward","Rebecca","Jason","Sharon",
    "Jeffrey","Laura","Ryan","Cynthia","Jacob","Kathleen","Gary","Amy",
    "Nicholas","Angela","Eric","Shirley","Jonathan","Anna","Stephen","Brenda",
    "Larry","Pamela","Justin","Emma","Scott","Nicole","Brandon","Helen",
    "Benjamin","Samantha","Samuel","Katherine","Raymond","Christine","Gregory",
    "Debra","Frank","Rachel","Alexander","Carolyn","Patrick","Janet","Jack","Maria",
    "Aisha","Omar","Priya","Ravi","Mei","Kenji","Yusuf","Fatima","Kofi","Amara",
    "Liam","Aria","Noah","Zoe","Ethan","Chloe","Mason","Lily","Logan","Ella",
]

LAST_NAMES = [
    "Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis",
    "Rodriguez","Martinez","Hernandez","Lopez","Gonzalez","Wilson","Anderson",
    "Thomas","Taylor","Moore","Jackson","Martin","Lee","Perez","Thompson","White",
    "Harris","Sanchez","Clark","Ramirez","Lewis","Robinson","Walker","Young",
    "Allen","King","Wright","Scott","Torres","Nguyen","Hill","Flores","Green",
    "Adams","Nelson","Baker","Hall","Rivera","Campbell","Mitchell","Carter",
    "Roberts","Osei","Patel","Sharma","Khan","Ahmed","Hassan","Okonkwo","Diallo",
    "Kimura","Tanaka","Watanabe","Nakamura","Suzuki","Chen","Wang","Li","Zhang",
    "Liu","Yang","Huang","Zhao","Wu","Zhou","Sun","Ma","Zhu","Hu","Guo","Lin",
    "He","Gao","Liang","Zheng","Luo","Song","Xie","Tang","Xu","Han","Feng",
    "Deng","Cao","Peng","Zeng","Xiao","Tian","Jiang","Yin","Ye","Fu",
    "Washington","Jefferson","Monroe","Harrison","Tyler","Polk","Pierce","Buchanan",
]

SUB_POSITIONS = [
    "Proposal Writer","Senior VP","Team Lead","Associate",
    "Administrative Assistant","Program Coordinator","Data Collection Staff",
]

# Real entities: KQT Test Entity (domestic/Karnataka), KC LLC (US/abroad entity).
# Remaining three are fictional seed entities for variety.
# get_or_create keyed on 'code' so re-runs don't create duplicates if name changes.
ENTITY_DATA = [
    ("KQT Test Entity", "KQT",   "Karnataka"),
    ("KC LLC",          "KCLLC", ""),
    ("KC Federal",      "KCFED", "Virginia"),
    ("KC Analytics",    "KCAN",  "Maryland"),
    ("KC Solutions",    "KCSOL", "Texas"),
]

AGENCIES = [
    "Department of Defense","Department of Health and Human Services",
    "General Services Administration","Department of Veterans Affairs",
    "Department of Homeland Security","Environmental Protection Agency",
    "Department of Education","Transportation Security Administration",
    "Department of Justice","Department of Energy","NASA","Department of Labor",
    "Department of Agriculture","Department of Commerce","Department of Interior",
    "Department of State","Department of Treasury","Department of Transportation",
    "Social Security Administration","Office of Personnel Management",
    "Small Business Administration","Federal Emergency Management Agency",
    "Centers for Disease Control","National Institutes of Health",
    "Food and Drug Administration","Bureau of Land Management",
    "Army Corps of Engineers","Naval Facilities Engineering Command",
    "Air Force Materiel Command","Defense Logistics Agency",
    "Defense Information Systems Agency","Defense Contract Audit Agency",
    "National Security Agency","Central Intelligence Agency",
    "Federal Bureau of Investigation","Drug Enforcement Administration",
    "Customs and Border Protection","Immigration and Customs Enforcement",
    "Secret Service","Bureau of Alcohol Tobacco Firearms",
    "Federal Aviation Administration","Federal Railroad Administration",
    "Federal Highway Administration","Federal Transit Administration",
    "National Park Service","Fish and Wildlife Service",
    "Bureau of Indian Affairs","Bureau of Reclamation",
    "Office of Inspector General — HHS","Office of Inspector General — DoD",
]

CATEGORIES = [
    "IT Services","Data Analytics","Administrative","Healthcare IT",
    "Cybersecurity","Training & Education","Engineering","Environmental",
    "Logistics","Financial Management","Program Management","Research & Development",
    "Construction","Professional Services","Communications","Legal Services",
    "Human Resources","Supply Chain","Intelligence Support","Medical Support",
]

STATES_LIST = [
    "AL","AK","AZ","AR","CA","CO","CT","DC","DE","FL","GA","HI","ID","IL","IN",
    "IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH",
    "NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT",
    "VT","VA","WA","WV","WI","WY",
]

SUBMISSION_METHODS = ["email","portal","physical","portal_and_physical","email_and_physical"]
BID_STATUSES = ["in_progress","submitted","no_go","unsubmitted","cancelled","postponed"]
BID_STATUS_WEIGHTS = [30, 25, 15, 10, 10, 10]

CORP_TYPES = ["LLC","Corporation","S-Corp","Partnership","Sole Proprietorship","Non-Profit"]
INCORP_STATES = ["Virginia","Maryland","DC","Delaware","Texas","California","New York","Florida"]

TASK_TITLES = [
    "Draft technical approach for {agency} bid",
    "Compile past performance writeups — {category}",
    "Review management plan — {agency}",
    "Price volume analysis for {category} contract",
    "Subcontractor teaming agreement — {agency}",
    "Orals preparation — {category}",
    "Build compliance checklist for {category}",
    "Update resumes for key personnel",
    "Review and finalize solicitation amendments",
    "Conduct competitor analysis — {agency}",
    "Prepare executive summary — {category}",
    "Coordinate with subcontractors for {agency}",
    "Submit SAM.gov registration renewal",
    "Draft data management plan — {category}",
    "Quality review pass — {agency} proposal",
    "Set up CI/CD pipeline for {category} portal",
    "Fix authentication bug in client dashboard",
    "Integrate API for opportunity sync",
    "Add PDF export for {category} reports",
    "Automate compliance checklist generation",
    "Redesign notification email templates",
    "Implement HMAC webhook signature verification",
    "Dashboard analytics — win rate by {agency}",
    "Archive completed bids — {category}",
    "WCAG 2.1 accessibility audit",
    "Write onboarding docs for new writers",
    "Quarterly performance review workflow",
    "Multi-entity payroll support — phase 2",
    "Mobile responsiveness fixes — {category} module",
    "Add bulk-import for {category} opportunities",
    "Refactor bid status FSM for clarity",
    "Write unit tests for proposal scoring engine",
    "Security penetration test findings remediation",
    "Set up staging environment for {agency}",
    "Database query optimisation — board view",
    "Research {agency} procurement history",
    "Map {category} requirements matrix",
    "Identify teaming partners for {agency}",
    "Prepare questions for pre-bid conference",
    "Debrief analysis — lost bid to {agency}",
    "Update win/loss tracker with Q2 data",
    "Create proposal style guide",
    "Standardise section templates — {category}",
    "Review small-business set-aside eligibility",
    "Kickoff meeting prep — {agency} award",
    "Coordinate BAFO response — {agency}",
    "Budget reconciliation — {category} project",
    "Develop risk register for active bids",
    "Update CPARS ratings database",
    "Onboard new proposal writer — orientation tasks",
]

TASK_TYPES = ["task","story","bug","epic"]
TASK_TYPE_WEIGHTS = [45, 30, 15, 10]
PRIORITIES = ["highest","high","medium","low","lowest"]
PRIORITY_WEIGHTS = [10, 20, 40, 20, 10]
TASK_STATUSES_BOARD = ["todo","in_progress","review","done","blocked"]

SPRINT_GOALS = [
    "Ship compliance checklist and fix critical authentication bugs",
    "GSA IDIQ proposal delivery and API integration milestone",
    "Dashboard analytics v1 and notification email redesign",
    "Close DoD bid cycle — orals prep, BAFO, debrief",
    "Payroll multi-entity support and Q2 reporting",
    "Mobile responsiveness and accessibility audit completion",
    "Bulk import feature and staging environment setup",
    "HHS data analytics platform — technical approach milestone",
    "Security remediation sprint — penetration test findings",
    "Onboarding automation and proposal template standardisation",
    "VA healthcare IT proposal submission",
    "DHS border security bid — price volume and teaming",
    "EPA data contract orals and past performance compilation",
    "Performance optimisation — board view and payroll queries",
    "New writer onboarding and style guide completion",
    "Q3 planning and win-loss analysis",
    "Federal proposals refresh — key personnel resumes",
    "Client portal self-service module — phase 1",
    "DoEd STEM bid kickoff and requirements matrix",
    "TSA training programme proposal — management plan",
]

NOTIF_TEMPLATES = [
    lambda emp, mgr, task: dict(
        kind='task_assigned', is_read=random.random() > 0.45,
        title=f'You were assigned {task.key}',
        body=task.title, link=f'/tasks?task={task.id}',
    ),
    lambda emp, mgr, task: dict(
        kind='leave_submitted', is_read=random.random() > 0.5,
        title=f'{emp.first_name} {emp.last_name} submitted a leave request',
        body='Sick leave — 2 days. Please review.',
        link='/hrms/leaves',
    ),
    lambda emp, mgr, task: dict(
        kind='leave_approved', is_read=random.random() > 0.3,
        title='Your leave request was approved',
        body=f'Approved by {mgr.first_name} {mgr.last_name}.',
        link='/hrms/leaves',
    ),
    lambda emp, mgr, task: dict(
        kind='leave_rejected', is_read=random.random() > 0.6,
        title='Your leave request was declined',
        body='Insufficient staffing during the requested period.',
        link='/hrms/leaves',
    ),
    lambda emp, mgr, task: dict(
        kind='incentive_granted', is_read=random.random() > 0.2,
        title='Performance incentive granted',
        body=f'${random.randint(2,10)*500} incentive approved for this quarter.',
        link='/hrms/payroll',
    ),
    lambda emp, mgr, task: dict(
        kind='document_received', is_read=random.random() > 0.5,
        title='New document shared with you',
        body='Your updated offer letter is ready for review.',
        link='/documents',
    ),
    lambda emp, mgr, task: dict(
        kind='document_request', is_read=random.random() > 0.4,
        title=f'{emp.first_name} requested a document',
        body='Experience letter requested.',
        link='/documents',
    ),
]

LEAVE_TYPES = ['sick', 'casual', 'earned', 'unpaid']
LEAVE_TYPE_WEIGHTS = [30, 30, 30, 10]


def _rand_name():
    return random.choice(FIRST_NAMES), random.choice(LAST_NAMES)


def _rand_email(first, last, domain_suffix, existing):
    base = f"{first.lower()}.{last.lower()}"
    candidate = f"{base}@{domain_suffix}"
    n = 1
    while candidate in existing:
        candidate = f"{base}{n}@{domain_suffix}"
        n += 1
    existing.add(candidate)
    return candidate


def _rand_shortcode(name, existing):
    words = name.split()
    base = ''.join(w[0] for w in words[:4]).upper()
    if len(base) < 2:
        base = name[:4].upper()
    candidate = base
    n = 2
    while candidate in existing:
        candidate = f"{base}{n}"
        n += 1
    existing.add(candidate)
    return candidate


class Command(BaseCommand):
    help = 'Seed full company snapshot — 10 mgrs, 50 emps, 100 clients, 500 bids, 20 sprints, attendance & leaves'

    def handle(self, *args, **options):
        from bids.models import Client, BidOpportunity, ClientBid
        from tasks.models import Team, Task, Sprint, TaskKeyCounter
        from hrms.models import (LeaveBalance, LeaveRequest, Attendance,
                                  AttendanceSession, CompensationVersion)
        from notifications.models import Notification
        from users.models import Entity

        today = date.today()
        year_ago = today - timedelta(days=365)

        # ── 0. Entities ───────────────────────────────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING('\n[0/7] Creating entities...'))
        entity_objs = []
        for name, code, state in ENTITY_DATA:
            obj, created = Entity.objects.get_or_create(
                code=code, defaults={'name': name, 'state': state}
            )
            entity_objs.append(obj)
            self.stdout.write(f"  {'Created' if created else 'Exists '} entity: {obj}")
        self.stdout.write(self.style.SUCCESS(f'  {len(entity_objs)} entities ready'))

        # ── 1. Users ──────────────────────────────────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING('\n[1/7] Creating users...'))
        existing_emails = set(User.objects.values_list('email', flat=True))

        managers, employees, hr_staff = [], [], []

        def _make_user(role, domain='kaiportal.com'):
            fn, ln = _rand_name()
            email = _rand_email(fn, ln, domain, existing_emails)
            doj = today - timedelta(days=random.randint(60, 1200))
            u = User(
                email=email, first_name=fn, last_name=ln,
                user_type=role,
                phone_number=f'+1-{random.randint(200,999)}-555-{random.randint(1000,9999)}',
                date_of_joining=doj,
                entity=random.choice(entity_objs),
                must_change_password=False, is_active=True,
            )
            u.set_password('Demo@1234')
            return u

        # Build user objects (not yet saved)
        mgr_objs = [_make_user('Manager') for _ in range(10)]
        emp_objs = [_make_user('Employee') for _ in range(50)]
        hr_objs  = [_make_user('Manager') for _ in range(5)]

        all_internal = mgr_objs + emp_objs + hr_objs
        User.objects.bulk_create(all_internal, ignore_conflicts=True)

        # Re-fetch saved users
        all_emails = {u.email for u in all_internal}
        saved_users = {u.email: u for u in User.objects.filter(email__in=all_emails)}

        managers  = [saved_users[u.email] for u in mgr_objs if u.email in saved_users]
        employees = [saved_users[u.email] for u in emp_objs if u.email in saved_users]
        hr_staff  = [saved_users[u.email] for u in hr_objs  if u.email in saved_users]
        internal  = managers + employees + hr_staff

        # Assign managers to employees
        with transaction.atomic():
            for u in employees + hr_staff:
                if not u.manager_id and managers:
                    u.manager = random.choice(managers)
                    u.save(update_fields=['manager'])

        # Assign RBAC Role bundles based on user_type
        from core.models import Role as RbacRole, UserRole
        role_map = {r.name: r for r in RbacRole.objects.all()}
        user_type_to_role = {'Manager': 'Manager', 'Employee': 'Employee'}
        for u in internal:
            rbac_name = user_type_to_role.get(u.user_type)
            if rbac_name and rbac_name in role_map:
                UserRole.objects.get_or_create(user=u, role=role_map[rbac_name])
        # HR staff get HR Manager role
        hr_role = role_map.get('HR Manager')
        if hr_role:
            for u in hr_staff:
                UserRole.objects.get_or_create(user=u, role=hr_role)
        self.stdout.write(self.style.SUCCESS('  RBAC roles assigned to internal users'))

        # Compensation + LeaveBalance
        from django.utils.timezone import now as tz_now
        _doj_default = today - timedelta(days=365)
        CompensationVersion.objects.bulk_create([
            CompensationVersion(
                employee=u,
                effective_from=u.date_of_joining or _doj_default,
                basic_salary=Decimal(str(random.randint(30, 120) * 1000)),
                hra=Decimal(str(random.randint(5, 20) * 1000)),
                special_allowance=Decimal(str(random.randint(2, 10) * 1000)),
            )
            for u in internal
        ], ignore_conflicts=True)
        LeaveBalance.objects.bulk_create([
            LeaveBalance(employee=u) for u in internal
        ], ignore_conflicts=True)

        self.stdout.write(self.style.SUCCESS(f'  {len(internal)} internal users created'))

        # ── 2. Teams ──────────────────────────────────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING('\n[2/7] Creating teams...'))
        team_defs = [
            ("Federal Proposals",   "Federal civilian and defense bid writing"),
            ("State & Local",       "State, county and city government pursuits"),
            ("Data & Analytics",    "Data collection, analysis and reporting"),
            ("Operations",          "Internal admin, HR and finance support"),
            ("IT & Engineering",    "Technical proposal writing and dev support"),
            ("Healthcare Division", "HHS, VA, CDC and NIH proposals"),
            ("Training & Learning", "DoEd, TSA, DHS training programme bids"),
            ("Environment & Energy","EPA, DOE and interior department pursuits"),
        ]
        created_teams = []
        emp_pool = list(employees)
        for tname, tdesc in team_defs:
            lead = random.choice(managers)
            team, _ = Team.objects.get_or_create(
                name=tname, defaults={'description': tdesc, 'lead': lead, 'is_active': True}
            )
            chunk = random.sample(emp_pool, k=min(random.randint(5, 10), len(emp_pool)))
            team.members.add(*chunk)
            created_teams.append(team)
        self.stdout.write(self.style.SUCCESS(f'  {len(created_teams)} teams created'))

        # ── 3. Clients (100) ─────────────────────────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING('\n[3/7] Creating 100 client companies...'))
        existing_codes = set(Client.objects.values_list('shortcode', flat=True))
        suffixes = ["Inc.","LLC","Corp.","Solutions","Group","Partners","Associates",
                    "Consulting","Services","Technologies","Dynamics","Systems","Federal",
                    "Government Solutions","Defense Contractors","Global","International"]
        client_objs = []
        client_existing_emails = set(User.objects.values_list('email', flat=True))
        used_names = set(Client.objects.values_list('name', flat=True))

        for _ in range(100):
            fn, ln = _rand_name()
            company = f"{ln} {random.choice(suffixes)}"
            if company in used_names:
                company = f"{fn} {ln} {random.choice(suffixes)}"
            used_names.add(company)
            sc = _rand_shortcode(company, existing_codes)
            client_objs.append(Client(
                name=company, shortcode=sc,
                corporation_type=random.choice(CORP_TYPES),
                state_of_incorporation=random.choice(INCORP_STATES),
                website=f"https://{sc.lower()}.com",
                address=f"{random.randint(100,9999)} {random.choice(['Main','Oak','Elm','Market','Commerce'])} "
                        f"{random.choice(['St','Ave','Blvd','Dr'])}, "
                        f"{random.choice(INCORP_STATES)} {random.randint(10000,99999)}",
                phone=f'+1-{random.randint(200,999)}-{random.randint(200,999)}-{random.randint(1000,9999)}',
                notes='Auto-generated seed client.',
            ))

        Client.objects.bulk_create(client_objs, ignore_conflicts=True)
        all_clients = list(Client.objects.all())
        self.stdout.write(self.style.SUCCESS(f'  {len(all_clients)} clients in DB'))

        # ── 4. Bid Opportunities (500) + Client Bids (~1 000) ─────────────────
        self.stdout.write(self.style.MIGRATE_HEADING('\n[4/7] Creating 500 opportunities + ~1 000 client bids...'))
        existing_sol = set(BidOpportunity.objects.values_list('solicitation_number', flat=True))

        opp_objs = []
        sol_counter = BidOpportunity.objects.count() + 1
        for i in range(500):
            agency = random.choice(AGENCIES)
            category = random.choice(CATEGORIES)
            sol_num = f"SOL-{sol_counter:05d}-{random.randint(100,999)}"
            while sol_num in existing_sol:
                sol_counter += 1
                sol_num = f"SOL-{sol_counter:05d}-{random.randint(100,999)}"
            existing_sol.add(sol_num)
            sol_counter += 1
            days_out = random.randint(-30, 180)
            opp_objs.append(BidOpportunity(
                agency=agency,
                title=f"{category} Support Services — {agency.split()[0]} {random.randint(2024,2027)}-{random.randint(1,99):02d}",
                solicitation_number=sol_num,
                state=random.choice(STATES_LIST),
                due_date=timezone.now() + timedelta(days=days_out),
                category=category,
                bid_link=f"https://sam.gov/opp/{sol_num}",
                pre_bid_info="Pre-bid conference details TBD." if random.random() > 0.6 else "",
            ))

        BidOpportunity.objects.bulk_create(opp_objs, ignore_conflicts=True)
        all_opps = list(BidOpportunity.objects.all())
        self.stdout.write(self.style.SUCCESS(f'  {len(all_opps)} opportunities in DB'))

        writers   = employees[:10]
        presales  = managers + employees[:15]

        bid_objs = []
        existing_bids = set(
            ClientBid.objects.values_list('opportunity_id', 'client_id')
        )
        random.shuffle(all_opps)
        bids_made = 0
        for opp in all_opps:
            n_bids = random.randint(1, 3)
            for client in random.sample(all_clients, k=min(n_bids, len(all_clients))):
                if (opp.id, client.id) in existing_bids:
                    continue
                existing_bids.add((opp.id, client.id))
                st = random.choices(BID_STATUSES, weights=BID_STATUS_WEIGHTS)[0]
                bid_objs.append(ClientBid(
                    opportunity=opp, client=client,
                    kc_brand=f"{client.shortcode}-{random.choice(['PRIME','SUB','JV'])}",
                    status=st,
                    internal_deadline=opp.due_date - timedelta(days=random.randint(3, 10)),
                    submission_method=random.choice(SUBMISSION_METHODS),
                    comments='Seeded.',
                ))
                bids_made += 1
                if bids_made >= 1000:
                    break
            if bids_made >= 1000:
                break

        ClientBid.objects.bulk_create(bid_objs, ignore_conflicts=True, batch_size=200)
        self.stdout.write(self.style.SUCCESS(f'  {bids_made} client bids created'))

        # ── 5. Sprints (20) + Tasks ───────────────────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING('\n[5/7] Creating 20 sprints + tasks...'))

        sprint_objs_saved = []
        sprint_start = today - timedelta(days=19 * 14)  # sprints go back ~9 months
        for i, goal in enumerate(SPRINT_GOALS):
            s_start = sprint_start + timedelta(days=i * 14)
            s_end   = s_start + timedelta(days=13)
            if s_end < today - timedelta(days=1):
                status = 'completed'
            elif s_start <= today <= s_end:
                status = 'active'
            else:
                status = 'planning'

            sprint, _ = Sprint.objects.get_or_create(
                name=f'Sprint {i+1} — {s_start.strftime("%b %Y")}',
                defaults={
                    'goal': goal,
                    'status': status,
                    'start_date': s_start,
                    'end_date': s_end,
                    'team': random.choice(created_teams) if created_teams else None,
                }
            )
            sprint_objs_saved.append(sprint)

        # Enforce at most 1 active sprint
        active_sprints = [s for s in sprint_objs_saved if s.status == 'active']
        for extra in active_sprints[1:]:
            extra.status = 'planning'
            extra.save(update_fields=['status'])

        self.stdout.write(f'  {len(sprint_objs_saved)} sprints created')

        # Tasks for sprints (10-20 each)
        task_count = 0
        position = float(Task.objects.count())

        def _make_task(title, sprint, status, assignee, team):
            nonlocal position
            task = Task(
                title=title,
                task_type=random.choices(TASK_TYPES, weights=TASK_TYPE_WEIGHTS)[0],
                priority=random.choices(PRIORITIES, weights=PRIORITY_WEIGHTS)[0],
                story_points=random.choice([1,2,3,5,8,13,None,None]),
                status=status,
                sprint=sprint,
                assignee=assignee,
                reporter=random.choice(managers) if managers else None,
                created_by=random.choice(managers) if managers else None,
                team=team,
                start_date=today - timedelta(days=random.randint(1,14)),
                due_date=timezone.now() + timedelta(days=random.randint(1,30)),
                position=position,
                labels=random.sample(['proposal','federal','data','urgent','review','blocked'], k=random.randint(0,2)),
                description='Auto-generated seed task.',
            )
            position += 1
            return task

        def _task_title():
            tmpl = random.choice(TASK_TITLES)
            return tmpl.format(
                agency=random.choice(AGENCIES).split()[0],
                category=random.choice(CATEGORIES),
            )[:255]

        for sprint in sprint_objs_saved:
            n = random.randint(10, 20)
            if sprint.status == 'completed':
                statuses = ['done'] * 7 + ['done', 'todo', 'in_progress']
            elif sprint.status == 'active':
                statuses = ['todo', 'in_progress', 'review', 'done', 'blocked',
                            'in_progress', 'todo', 'done', 'review', 'in_progress']
            else:
                statuses = ['todo'] * 8 + ['todo', 'todo']

            for _ in range(n):
                t = _make_task(
                    _task_title(),
                    sprint,
                    random.choice(statuses),
                    random.choice(internal) if internal else None,
                    random.choice(created_teams) if created_teams else None,
                )
                t.save()
                task_count += 1

        self.stdout.write(f'  {task_count} sprint tasks created')

        # Backlog tasks (200)
        self.stdout.write('  Creating 200 backlog tasks...')
        for _ in range(200):
            t = _make_task(
                _task_title(), None, 'todo',
                random.choice(internal) if internal else None,
                random.choice(created_teams) if created_teams else None,
            )
            t.save()
            task_count += 1

        self.stdout.write(self.style.SUCCESS(f'  Total tasks: {task_count}'))

        # ── 6. Attendance (1 year) + Leaves ───────────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING('\n[6/7] Seeding 1 year attendance + leave records...'))

        att_employees = employees + managers + hr_staff
        existing_att = set(Attendance.objects.values_list('employee_id', 'date'))

        att_batch, session_batch = [], []
        WORKDAY_STATUSES = ['present','present','present','present','present',
                            'present','half_day','sick_leave','absent']

        for emp in att_employees:
            for offset in range(365, 0, -1):
                att_date = today - timedelta(days=offset)
                if att_date.weekday() >= 5:
                    continue
                if (emp.id, att_date) in existing_att:
                    continue
                existing_att.add((emp.id, att_date))
                st = random.choice(WORKDAY_STATUSES)
                att = Attendance(employee=emp, date=att_date, status=st, source='admin_override')
                att_batch.append(att)

        Attendance.objects.bulk_create(att_batch, batch_size=500, ignore_conflicts=True)
        self.stdout.write(f'  {len(att_batch)} attendance records created')

        # Clock-in/out sessions for present/half_day records
        saved_atts = Attendance.objects.filter(
            employee__in=att_employees,
            status__in=['present', 'half_day'],
            date__gte=year_ago,
        ).exclude(sessions__isnull=False)  # skip ones that already have sessions

        for att in saved_atts:
            if att.status == 'present':
                cin  = time(random.randint(8, 9),  random.randint(0, 59))
                cout = time(random.randint(17, 18), random.randint(0, 59))
            else:
                cin  = time(random.randint(9, 10), random.randint(0, 59))
                cout = time(random.randint(13, 14), random.randint(0, 59))
            session_batch.append(AttendanceSession(attendance=att, clock_in_time=cin, clock_out_time=cout))

        AttendanceSession.objects.bulk_create(session_batch, batch_size=500, ignore_conflicts=True)
        self.stdout.write(f'  {len(session_batch)} clock-in/out sessions created')

        # Leave requests — approved/rejected (historical)
        leave_batch = []
        existing_leaves = set(LeaveRequest.objects.values_list('employee_id', 'from_date'))
        hist_statuses = ['approved'] * 6 + ['rejected'] * 2 + ['approved']

        for emp in att_employees:
            for _ in range(random.randint(3, 7)):
                from_date = today - timedelta(days=random.randint(10, 360))
                if from_date.weekday() >= 5:
                    from_date -= timedelta(days=from_date.weekday() - 4)
                to_date = from_date + timedelta(days=random.randint(1, 4))
                if (emp.id, from_date) in existing_leaves:
                    continue
                existing_leaves.add((emp.id, from_date))
                lt = random.choices(LEAVE_TYPES, weights=LEAVE_TYPE_WEIGHTS)[0]
                st = random.choice(hist_statuses)
                reviewer = emp.manager or (random.choice(managers) if managers else None)
                leave_batch.append(LeaveRequest(
                    employee=emp, leave_type=lt,
                    from_date=from_date, to_date=to_date,
                    total_days=(to_date - from_date).days + 1,
                    reason=f'{lt.capitalize()} leave.',
                    status=st,
                    reviewed_by=reviewer if st != 'pending' else None,
                    reviewed_on=timezone.now() - timedelta(days=random.randint(1,30)) if st != 'pending' else None,
                ))

        # 30 active (pending) leave applications
        pending_pool = random.sample(att_employees, k=min(30, len(att_employees)))
        for emp in pending_pool:
            from_date = today + timedelta(days=random.randint(1, 14))
            if from_date.weekday() >= 5:
                from_date += timedelta(days=7 - from_date.weekday())
            to_date = from_date + timedelta(days=random.randint(1, 3))
            if (emp.id, from_date) in existing_leaves:
                continue
            existing_leaves.add((emp.id, from_date))
            lt = random.choices(LEAVE_TYPES, weights=LEAVE_TYPE_WEIGHTS)[0]
            leave_batch.append(LeaveRequest(
                employee=emp, leave_type=lt,
                from_date=from_date, to_date=to_date,
                total_days=(to_date - from_date).days + 1,
                reason=f'Planned {lt} leave.',
                status='pending',
            ))

        LeaveRequest.objects.bulk_create(leave_batch, batch_size=200, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(f'  {len(leave_batch)} leave requests created (30 pending)'))

        # Recompute LeaveBalance used-day counters from ALL approved leaves (idempotent)
        from collections import defaultdict
        from django.db.models import Sum
        emp_ids = [e.id for e in att_employees]
        agg_rows = (
            LeaveRequest.objects
            .filter(employee_id__in=emp_ids, status='approved')
            .values('employee_id', 'leave_type')
            .annotate(total=Sum('total_days'))
        )
        bal_map = defaultdict(lambda: {'sick': 0, 'casual': 0, 'earned': 0, 'unpaid': 0})
        for row in agg_rows:
            lt = row['leave_type']
            if lt in bal_map[row['employee_id']]:
                bal_map[row['employee_id']][lt] = row['total'] or 0

        if bal_map:
            bals = list(LeaveBalance.objects.filter(employee_id__in=bal_map.keys()))
            for bal in bals:
                d = bal_map[bal.employee_id]
                bal.sick_used = min(bal.sick_total, d['sick'])
                bal.casual_used = min(bal.casual_total, d['casual'])
                bal.earned_used = min(bal.earned_total, d['earned'])
                bal.unpaid_used = d['unpaid']
            LeaveBalance.objects.bulk_update(bals, ['sick_used', 'casual_used', 'earned_used', 'unpaid_used'])
            self.stdout.write(self.style.SUCCESS(f'  Recalculated leave balances for {len(bals)} employees'))

        # ── 7. Notifications ──────────────────────────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING('\n[7/7] Seeding notifications...'))
        tasks_sample = list(Task.objects.all()[:50])
        notif_batch = []

        for emp in att_employees:
            mgr = emp.manager or (random.choice(managers) if managers else emp)
            task = random.choice(tasks_sample) if tasks_sample else None
            if not task:
                continue
            chosen = random.sample(NOTIF_TEMPLATES, k=random.randint(3, 6))
            for tmpl in chosen:
                try:
                    kw = tmpl(emp, mgr, task)
                    notif_batch.append(Notification(
                        recipient=emp if kw['kind'] not in ('leave_submitted', 'document_request') else mgr,
                        actor=mgr if kw['kind'] not in ('leave_submitted', 'document_request') else emp,
                        **kw,
                    ))
                except Exception:
                    pass

        Notification.objects.bulk_create(notif_batch, batch_size=500, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(f'  {len(notif_batch)} notifications created'))

        # ── Summary ───────────────────────────────────────────────────────────
        self.stdout.write(self.style.SUCCESS(
            f'\n{"="*55}\n'
            f'  Seed complete!\n'
            f'  Internal users : {len(internal)}\n'
            f'  Teams          : {len(created_teams)}\n'
            f'  Clients        : {Client.objects.count()}\n'
            f'  Opportunities  : {BidOpportunity.objects.count()}\n'
            f'  Client bids    : {ClientBid.objects.count()}\n'
            f'  Sprints        : {len(sprint_objs_saved)}\n'
            f'  Tasks          : {Task.objects.count()}\n'
            f'  Attendance rows: {Attendance.objects.count()}\n'
            f'  Leave requests : {LeaveRequest.objects.count()}\n'
            f'  Notifications  : {Notification.objects.count()}\n'
            f'  All passwords  : Demo@1234\n'
            f'{"="*55}'
        ))
