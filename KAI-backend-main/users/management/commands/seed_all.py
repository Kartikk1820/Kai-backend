import random
from datetime import date, timedelta, datetime, time
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


USERS_DATA = [
    # Managers
    {"email": "sarah.mitchell@kaiportal.com",  "first_name": "Sarah",   "last_name": "Mitchell",  "role": "Manager",  "sub_position": "Senior VP",         "phone": "+1-202-555-0101"},
    {"email": "david.okonkwo@kaiportal.com",   "first_name": "David",   "last_name": "Okonkwo",   "role": "Manager",  "sub_position": "Team Lead",         "phone": "+1-202-555-0102"},
    {"email": "priya.sharma@kaiportal.com",    "first_name": "Priya",   "last_name": "Sharma",    "role": "Manager",  "sub_position": "Senior VP",         "phone": "+1-202-555-0103"},

    # Employees
    {"email": "james.carter@kaiportal.com",    "first_name": "James",   "last_name": "Carter",    "role": "Employee", "sub_position": "Proposal Writer",   "phone": "+1-202-555-0104"},
    {"email": "aisha.patel@kaiportal.com",     "first_name": "Aisha",   "last_name": "Patel",     "role": "Employee", "sub_position": "Proposal Writer",   "phone": "+1-202-555-0105"},
    {"email": "marcus.nguyen@kaiportal.com",   "first_name": "Marcus",  "last_name": "Nguyen",    "role": "Employee", "sub_position": "Associate",         "phone": "+1-202-555-0106"},
    {"email": "elena.vasquez@kaiportal.com",   "first_name": "Elena",   "last_name": "Vasquez",   "role": "Employee", "sub_position": "Program Coordinator","phone": "+1-202-555-0107"},
    {"email": "tyrone.brooks@kaiportal.com",   "first_name": "Tyrone",  "last_name": "Brooks",    "role": "Employee", "sub_position": "Data Collection Staff","phone": "+1-202-555-0108"},
    {"email": "mei.chen@kaiportal.com",        "first_name": "Mei",     "last_name": "Chen",      "role": "Employee", "sub_position": "Proposal Writer",   "phone": "+1-202-555-0109"},
    {"email": "omar.hassan@kaiportal.com",     "first_name": "Omar",    "last_name": "Hassan",    "role": "Employee", "sub_position": "Associate",         "phone": "+1-202-555-0110"},
    {"email": "jessica.kim@kaiportal.com",     "first_name": "Jessica", "last_name": "Kim",       "role": "Employee", "sub_position": "Administrative Assistant","phone": "+1-202-555-0111"},
    {"email": "rafael.morales@kaiportal.com",  "first_name": "Rafael",  "last_name": "Morales",   "role": "Employee", "sub_position": "Data Collection Staff","phone": "+1-202-555-0112"},
    {"email": "linda.washington@kaiportal.com","first_name": "Linda",   "last_name": "Washington","role": "Employee", "sub_position": "Program Coordinator","phone": "+1-202-555-0113"},
    {"email": "kevin.osei@kaiportal.com",      "first_name": "Kevin",   "last_name": "Osei",      "role": "Employee", "sub_position": "Associate",         "phone": "+1-202-555-0114"},

    # HR Manager
    {"email": "angela.foster@kaiportal.com",   "first_name": "Angela",  "last_name": "Foster",    "role": "Manager",  "sub_position": "Team Lead",         "phone": "+1-202-555-0115"},

    # Clients
    {"email": "contact@nexusgov.com",          "first_name": "Nexus",   "last_name": "Government","role": "Client",   "sub_position": None,                "phone": "+1-703-555-0201"},
    {"email": "procurement@alphatec.io",       "first_name": "Alpha",   "last_name": "Technologies","role": "Client", "sub_position": None,                "phone": "+1-703-555-0202"},
    {"email": "bids@vanguardsolutions.com",    "first_name": "Vanguard","last_name": "Solutions",  "role": "Client",  "sub_position": None,                "phone": "+1-703-555-0203"},
]

TEAMS_DATA = [
    {
        "name": "Federal Proposals",
        "description": "Handles federal bid writing and submission",
        "members": ["james.carter@kaiportal.com", "aisha.patel@kaiportal.com", "mei.chen@kaiportal.com", "tyrone.brooks@kaiportal.com"],
        "lead": "sarah.mitchell@kaiportal.com",
    },
    {
        "name": "State & Local",
        "description": "State and local government contract pursuit",
        "members": ["marcus.nguyen@kaiportal.com", "elena.vasquez@kaiportal.com", "jessica.kim@kaiportal.com"],
        "lead": "david.okonkwo@kaiportal.com",
    },
    {
        "name": "Data & Analytics",
        "description": "Data collection, analysis, and reporting",
        "members": ["omar.hassan@kaiportal.com", "rafael.morales@kaiportal.com", "kevin.osei@kaiportal.com"],
        "lead": "priya.sharma@kaiportal.com",
    },
    {
        "name": "Operations",
        "description": "Internal operations and admin support",
        "members": ["linda.washington@kaiportal.com", "jessica.kim@kaiportal.com"],
        "lead": "angela.foster@kaiportal.com",
    },
]

CLIENTS_DATA = [
    {"name": "Nexus Government Services",   "shortcode": "NGS",  "corporation_type": "LLC",          "state_of_incorporation": "Virginia",  "website": "https://nexusgov.com",          "address": "1400 Defense Blvd, Arlington, VA 22209"},
    {"name": "Alpha Technologies Inc.",     "shortcode": "ATI",  "corporation_type": "Corporation",  "state_of_incorporation": "Maryland",  "website": "https://alphatec.io",           "address": "700 Tech Parkway, Bethesda, MD 20814"},
    {"name": "Vanguard Solutions LLC",      "shortcode": "VSL",  "corporation_type": "LLC",          "state_of_incorporation": "Virginia",  "website": "https://vanguardsolutions.com", "address": "3250 Wilson Blvd, Arlington, VA 22201"},
    {"name": "Pinnacle Federal Group",      "shortcode": "PFG",  "corporation_type": "S-Corp",       "state_of_incorporation": "DC",        "website": "https://pinnaclefederal.com",   "address": "1800 K Street NW, Washington, DC 20006"},
    {"name": "Meridian Consulting Partners","shortcode": "MCP",  "corporation_type": "Partnership",  "state_of_incorporation": "Virginia",  "website": "https://meridianconsulting.com","address": "8270 Greensboro Drive, McLean, VA 22102"},
    {"name": "Horizon Defense Contractors","shortcode": "HDC",  "corporation_type": "Corporation",  "state_of_incorporation": "Maryland",  "website": "https://horizondefense.com",   "address": "7799 Leesburg Pike, Falls Church, VA 22043"},
]

OPPORTUNITIES_DATA = [
    {"agency": "Department of Defense", "title": "Cybersecurity Assessment and Risk Management Services", "solicitation_number": "DoD-CARMS-2026-001", "state": "VA", "category": "IT Services", "days_out": 45},
    {"agency": "Department of Health and Human Services", "title": "Public Health Data Analytics Platform", "solicitation_number": "HHS-PHDAP-2026-012", "state": "MD", "category": "Data Analytics", "days_out": 30},
    {"agency": "General Services Administration", "title": "Professional Administrative Support Services IDIQ", "solicitation_number": "GSA-PASS-2026-087", "state": "DC", "category": "Administrative", "days_out": 60},
    {"agency": "Department of Veterans Affairs", "title": "Healthcare IT Modernization and Support", "solicitation_number": "VA-HITS-2026-034", "state": "VA", "category": "Healthcare IT", "days_out": 20},
    {"agency": "Department of Homeland Security", "title": "Border Security Technology Integration", "solicitation_number": "DHS-BSTI-2026-056", "state": "TX", "category": "Security", "days_out": 90},
    {"agency": "Environmental Protection Agency", "title": "Environmental Data Collection and Reporting", "solicitation_number": "EPA-EDCR-2026-019", "state": "DC", "category": "Environmental", "days_out": 15},
    {"agency": "Department of Education", "title": "STEM Program Management and Evaluation", "solicitation_number": "DoEd-STEM-2026-042", "state": "DC", "category": "Education", "days_out": 55},
    {"agency": "Transportation Security Administration", "title": "Workforce Training Program Development", "solicitation_number": "TSA-WTPD-2026-003", "state": "VA", "category": "Training", "days_out": 35},
]

TASKS_DATA = [
    # Technical/dev tasks
    {"title": "Set up CI/CD pipeline for proposal portal", "task_type": "task", "priority": "high", "story_points": 8, "status": "done"},
    {"title": "Integrate GSA e-library API for opportunity sync", "task_type": "story", "priority": "highest", "story_points": 13, "status": "done"},
    {"title": "Build automated compliance checklist generator", "task_type": "story", "priority": "high", "story_points": 8, "status": "in_progress"},
    {"title": "Fix duplicate solicitation number validation bug", "task_type": "bug", "priority": "high", "story_points": 3, "status": "done"},
    {"title": "Add PDF export for bid opportunity reports", "task_type": "story", "priority": "medium", "story_points": 5, "status": "in_progress"},
    {"title": "Implement HMAC webhook signature verification", "task_type": "task", "priority": "highest", "story_points": 5, "status": "review"},
    {"title": "Dashboard analytics — win rate by agency", "task_type": "story", "priority": "medium", "story_points": 8, "status": "todo"},
    {"title": "User role assignment UI broken on Safari", "task_type": "bug", "priority": "high", "story_points": 2, "status": "todo"},

    # Proposal tasks
    {"title": "Draft technical approach for DoD-CARMS-2026-001", "task_type": "task", "priority": "highest", "story_points": 5, "status": "in_progress"},
    {"title": "Compile past performance writeups — HHS bid", "task_type": "task", "priority": "high", "story_points": 3, "status": "todo"},
    {"title": "Management plan review — GSA IDIQ", "task_type": "task", "priority": "medium", "story_points": 2, "status": "review"},
    {"title": "Subcontractor teaming agreement — VA modernization", "task_type": "task", "priority": "high", "story_points": 3, "status": "todo"},
    {"title": "Price volume analysis for DHS bid", "task_type": "task", "priority": "medium", "story_points": 5, "status": "todo"},
    {"title": "Orals preparation — EPA data contract", "task_type": "task", "priority": "high", "story_points": 3, "status": "in_progress"},

    # Epics / big items
    {"title": "Phase 2: Client portal self-service module", "task_type": "epic", "priority": "medium", "story_points": 40, "status": "todo"},
    {"title": "Multi-entity payroll support", "task_type": "epic", "priority": "low", "story_points": 21, "status": "todo"},

    # Bug / ops
    {"title": "Celery beat not running on container restart", "task_type": "bug", "priority": "high", "story_points": 2, "status": "done"},
    {"title": "Salary slip generation fails for December", "task_type": "bug", "priority": "highest", "story_points": 3, "status": "done"},
    {"title": "Attendance sync missing holiday entries", "task_type": "bug", "priority": "medium", "story_points": 2, "status": "in_progress"},
    {"title": "Write onboarding documentation for new writers", "task_type": "task", "priority": "low", "story_points": 3, "status": "todo"},
    {"title": "Quarterly performance review workflow", "task_type": "story", "priority": "medium", "story_points": 8, "status": "todo"},
    {"title": "Notification email templates redesign", "task_type": "task", "priority": "low", "story_points": 3, "status": "backlog"},
    {"title": "Archive completed bids older than 2 years", "task_type": "task", "priority": "low", "story_points": 2, "status": "backlog"},
    {"title": "WCAG 2.1 accessibility audit", "task_type": "task", "priority": "medium", "story_points": 5, "status": "backlog"},
]

SPRINTS_DATA = [
    {"name": "Sprint 3 — June 2026", "goal": "Ship HMAC webhook, fix critical bugs, and complete DoD technical approach", "status": "active", "offset_start": -7, "offset_end": 7},
    {"name": "Sprint 4 — July 2026", "goal": "Analytics dashboard, compliance checklist, GSA IDIQ management plan", "status": "planning", "offset_start": 8, "offset_end": 21},
    {"name": "Sprint 2 — May 2026", "goal": "CI/CD pipeline, API integration, past performance library", "status": "completed", "offset_start": -28, "offset_end": -14},
]


class Command(BaseCommand):
    help = 'Seeds the database with comprehensive dummy data (users, teams, clients, bids, tasks, attendance)'

    def handle(self, *args, **options):
        from bids.models import Client, BidOpportunity, ClientBid
        from tasks.models import Team, Task, Sprint, TaskKeyCounter
        from hrms.models import LeaveBalance, LeaveRequest, Attendance, AttendanceSession, Compensation

        self.stdout.write(self.style.MIGRATE_HEADING('=== KAI Portal — Full Data Seed ==='))

        # ── 1. Users ──────────────────────────────────────────────────────────
        self.stdout.write('\n[1/6] Creating users...')
        created_users = {}
        managers = []

        for ud in USERS_DATA:
            user, created = User.objects.get_or_create(
                email=ud['email'],
                defaults={
                    'first_name': ud['first_name'],
                    'last_name': ud['last_name'],
                    'role': ud['role'],
                    'sub_position': ud.get('sub_position'),
                    'phone_number': ud.get('phone'),
                    'must_change_password': False,
                    'date_of_joining': date.today() - timedelta(days=random.randint(90, 900)),
                    'entity': random.choice(['KC Group', 'KC Federal', 'KC Analytics']),
                    'is_active': True,
                }
            )
            if created:
                user.set_password('Demo@1234')
                if user.role in ('Manager',):
                    managers.append(user)
                if user.role == 'Employee':
                    comp, _ = Compensation.objects.get_or_create(
                        employee=user,
                        defaults={'monthly_base_salary': Decimal(str(random.randint(55, 120) * 100))}
                    )
                    LeaveBalance.objects.get_or_create(employee=user)
                user.save()
                self.stdout.write(f'  + {user.email} ({user.role})')
            else:
                self.stdout.write(self.style.WARNING(f'  ~ {user.email} already exists'))
            created_users[ud['email']] = user

        # Assign managers to employees
        mgr_list = [u for u in created_users.values() if u.role == 'Manager']
        for user in created_users.values():
            if user.role == 'Employee' and not user.manager_id and mgr_list:
                user.manager = random.choice(mgr_list)
                user.save(update_fields=['manager'])

        self.stdout.write(self.style.SUCCESS(f'  Done — {len(created_users)} users'))

        # ── 2. Teams ──────────────────────────────────────────────────────────
        self.stdout.write('\n[2/6] Creating teams...')
        created_teams = []
        for td in TEAMS_DATA:
            lead = created_users.get(td['lead'])
            team, created = Team.objects.get_or_create(
                name=td['name'],
                defaults={'description': td['description'], 'lead': lead, 'is_active': True}
            )
            if not created:
                self.stdout.write(self.style.WARNING(f'  ~ Team "{team.name}" already exists'))
            else:
                self.stdout.write(f'  + Team: {team.name}')
            for email in td['members']:
                member = created_users.get(email)
                if member:
                    team.members.add(member)
            created_teams.append(team)
        self.stdout.write(self.style.SUCCESS(f'  Done — {len(created_teams)} teams'))

        # ── 3. Clients ────────────────────────────────────────────────────────
        self.stdout.write('\n[3/6] Creating clients...')
        created_clients = []
        for cd in CLIENTS_DATA:
            client, created = Client.objects.get_or_create(
                shortcode=cd['shortcode'],
                defaults={
                    'name': cd['name'],
                    'corporation_type': cd['corporation_type'],
                    'state_of_incorporation': cd['state_of_incorporation'],
                    'website': cd['website'],
                    'address': cd['address'],
                }
            )
            if created:
                self.stdout.write(f'  + Client: {client.name}')
            else:
                self.stdout.write(self.style.WARNING(f'  ~ Client "{client.name}" already exists'))
            created_clients.append(client)
        self.stdout.write(self.style.SUCCESS(f'  Done — {len(created_clients)} clients'))

        # ── 4. Bids ───────────────────────────────────────────────────────────
        self.stdout.write('\n[4/6] Creating bid opportunities and client bids...')
        writers = [u for u in created_users.values() if u.role == 'Employee' and u.sub_position == 'Proposal Writer']
        presales = [u for u in created_users.values() if u.role in ('Manager', 'Employee')]
        bid_statuses = ['in_progress', 'submitted', 'no_go', 'unsubmitted', 'in_progress', 'in_progress']

        for od in OPPORTUNITIES_DATA:
            opp, created = BidOpportunity.objects.get_or_create(
                solicitation_number=od['solicitation_number'],
                defaults={
                    'agency': od['agency'],
                    'title': od['title'],
                    'state': od['state'],
                    'due_date': timezone.now() + timedelta(days=od['days_out']),
                    'category': od['category'],
                }
            )
            if created:
                self.stdout.write(f'  + Opportunity: {od["solicitation_number"]}')
            else:
                self.stdout.write(self.style.WARNING(f'  ~ Opp {od["solicitation_number"]} already exists'))

            # Create 1-3 client bids per opportunity
            for client in random.sample(created_clients, k=random.randint(1, 3)):
                if not ClientBid.objects.filter(opportunity=opp, client=client).exists():
                    ClientBid.objects.create(
                        opportunity=opp,
                        client=client,
                        kc_brand=client.shortcode + '-' + random.choice(['PRIME', 'SUB', 'JV']),
                        status=random.choice(bid_statuses),
                        presales_person=random.choice(presales) if presales else None,
                        writer=random.choice(writers) if writers else None,
                        internal_deadline=timezone.now() + timedelta(days=od['days_out'] - 5),
                        submission_method=random.choice(['sam_gov', 'email', 'portal', 'hand_delivery']),
                        comments='Auto-generated seed data.',
                    )
        self.stdout.write(self.style.SUCCESS(f'  Done — {len(OPPORTUNITIES_DATA)} opportunities seeded'))

        # ── 5. Sprints + Tasks ────────────────────────────────────────────────
        self.stdout.write('\n[5/6] Creating sprints and tasks...')
        today = date.today()
        sprint_objs = []
        for sd in SPRINTS_DATA:
            sprint, created = Sprint.objects.get_or_create(
                name=sd['name'],
                defaults={
                    'goal': sd['goal'],
                    'status': sd['status'],
                    'start_date': today + timedelta(days=sd['offset_start']),
                    'end_date': today + timedelta(days=sd['offset_end']),
                    'team': created_teams[0] if created_teams else None,
                }
            )
            if created:
                self.stdout.write(f'  + Sprint: {sprint.name} ({sprint.status})')
            else:
                self.stdout.write(self.style.WARNING(f'  ~ Sprint "{sprint.name}" already exists'))
            sprint_objs.append(sprint)

        active_sprint = next((s for s in sprint_objs if s.status == 'active'), None)
        planning_sprint = next((s for s in sprint_objs if s.status == 'planning'), None)
        completed_sprint = next((s for s in sprint_objs if s.status == 'completed'), None)

        employees = [u for u in created_users.values() if u.role in ('Employee', 'Manager')]
        position = 0

        for td in TASKS_DATA:
            if Task.objects.filter(title=td['title']).exists():
                continue

            # Assign sprint based on status hint
            if td.get('status') == 'backlog' or td['status'] == 'todo' and random.random() < 0.3:
                sprint = None
                task_status = 'todo'
            elif td['status'] in ('done', 'review') and completed_sprint:
                sprint = completed_sprint
                task_status = td['status']
            elif td['status'] in ('in_progress', 'review') and active_sprint:
                sprint = active_sprint
                task_status = td['status']
            elif td['status'] == 'done' and active_sprint:
                sprint = active_sprint
                task_status = 'done'
            elif td['status'] == 'todo' and planning_sprint and random.random() < 0.5:
                sprint = planning_sprint
                task_status = 'todo'
            else:
                sprint = None
                task_status = 'todo'

            assignee = random.choice(employees) if employees else None
            team = random.choice(created_teams) if created_teams else None

            due = timezone.now() + timedelta(days=random.randint(3, 30))
            start = (today - timedelta(days=random.randint(1, 7)))

            task = Task(
                title=td['title'],
                task_type=td['task_type'],
                priority=td['priority'],
                story_points=td.get('story_points'),
                status=task_status,
                sprint=sprint,
                assignee=assignee,
                reporter=random.choice(mgr_list) if mgr_list else None,
                created_by=random.choice(mgr_list) if mgr_list else None,
                team=team,
                start_date=start,
                due_date=due,
                position=float(position),
                labels=[td['task_type'], td['priority']] if random.random() > 0.5 else [],
            )
            task.save()
            position += 1
            self.stdout.write(f'  + Task [{task.key}]: {task.title[:50]}')

        self.stdout.write(self.style.SUCCESS(f'  Done — tasks seeded'))

        # ── 6. Attendance ─────────────────────────────────────────────────────
        self.stdout.write('\n[6/7] Seeding attendance data (last 30 days)...')
        att_employees = [u for u in created_users.values() if u.role in ('Employee', 'Manager')]

        # Weekday weights: mostly present, some leaves/half-days
        day_status_weights = [
            ('present', 75), ('present', 0), ('half_day', 8),
            ('leave', 7), ('absent', 5), ('holiday', 5),
        ]
        choices, weights = zip(*[(s, w) for s, w in day_status_weights if w > 0])

        att_created = 0
        for emp in att_employees:
            for day_offset in range(30, 0, -1):
                att_date = today - timedelta(days=day_offset)
                if att_date.weekday() >= 5:  # skip weekends
                    continue
                if Attendance.objects.filter(employee=emp, date=att_date).exists():
                    continue

                status = random.choices(choices, weights=weights)[0]
                att = Attendance.objects.create(
                    employee=emp,
                    date=att_date,
                    status=status,
                    marked_by_admin=True,
                )
                att_created += 1

                if status == 'present':
                    clock_in = time(random.randint(8, 9), random.randint(0, 59))
                    clock_out = time(random.randint(17, 18), random.randint(0, 59))
                    AttendanceSession.objects.create(attendance=att, clock_in_time=clock_in, clock_out_time=clock_out)
                elif status == 'half_day':
                    clock_in = time(random.randint(9, 10), random.randint(0, 59))
                    clock_out = time(random.randint(13, 14), random.randint(0, 59))
                    AttendanceSession.objects.create(attendance=att, clock_in_time=clock_in, clock_out_time=clock_out)

        self.stdout.write(self.style.SUCCESS(f'  Done — {att_created} attendance records'))

        # ── Leave requests ────────────────────────────────────────────────────
        leave_types = ['sick', 'casual', 'earned']
        leave_statuses = ['approved', 'approved', 'pending', 'rejected']
        leave_created = 0
        for emp in att_employees[:8]:  # seed for first 8 employees
            if LeaveRequest.objects.filter(employee=emp).exists():
                continue
            leave_type = random.choice(leave_types)
            from_date = today - timedelta(days=random.randint(5, 25))
            to_date = from_date + timedelta(days=random.randint(1, 3))
            lst = random.choice(leave_statuses)
            reviewer = random.choice(mgr_list) if mgr_list else None
            LeaveRequest.objects.create(
                employee=emp,
                leave_type=leave_type,
                from_date=from_date,
                to_date=to_date,
                total_days=(to_date - from_date).days + 1,
                reason=f'Personal {leave_type} leave request.',
                status=lst,
                reviewed_by=reviewer if lst in ('approved', 'rejected') else None,
                reviewed_on=timezone.now() if lst in ('approved', 'rejected') else None,
            )
            leave_created += 1

        self.stdout.write(self.style.SUCCESS(f'  Done — {leave_created} leave requests'))

        # ── 7. Notifications ──────────────────────────────────────────────────
        self.stdout.write('\n[7/7] Seeding notifications...')
        from notifications.models import Notification

        notification_templates = [
            # task_assigned — sent to assignee, actor is a manager
            lambda emp, mgr, task: dict(
                recipient=emp, actor=mgr, kind='task_assigned',
                title=f'You were assigned {task.key}',
                body=task.title,
                link=f'/tasks?task={task.id}',
                is_read=random.random() > 0.4,
            ),
            # leave_submitted — sent to manager
            lambda emp, mgr, _: dict(
                recipient=mgr, actor=emp, kind='leave_submitted',
                title=f'{emp.first_name} {emp.last_name} submitted a leave request',
                body='Casual leave — 2 days. Please review.',
                link='/hrms/leaves',
                is_read=random.random() > 0.5,
            ),
            # leave_approved — sent to employee
            lambda emp, mgr, _: dict(
                recipient=emp, actor=mgr, kind='leave_approved',
                title='Your leave request was approved',
                body=f'Approved by {mgr.first_name} {mgr.last_name}.',
                link='/hrms/leaves',
                is_read=random.random() > 0.3,
            ),
            # leave_rejected — sent to employee
            lambda emp, mgr, _: dict(
                recipient=emp, actor=mgr, kind='leave_rejected',
                title='Your leave request was declined',
                body='Reason: Insufficient staffing during the requested period.',
                link='/hrms/leaves',
                is_read=random.random() > 0.6,
            ),
            # incentive_granted — sent to employee
            lambda emp, mgr, _: dict(
                recipient=emp, actor=mgr, kind='incentive_granted',
                title='Performance incentive granted',
                body=f'${random.randint(2, 10) * 500} incentive approved for this quarter.',
                link='/hrms/payroll',
                is_read=random.random() > 0.2,
            ),
            # document_received — sent to employee
            lambda emp, mgr, _: dict(
                recipient=emp, actor=mgr, kind='document_received',
                title='New document shared with you',
                body='Your updated offer letter is ready for review.',
                link='/documents',
                is_read=random.random() > 0.5,
            ),
            # document_request — sent to manager
            lambda emp, mgr, _: dict(
                recipient=mgr, actor=emp, kind='document_request',
                title=f'{emp.first_name} requested a document',
                body='Experience letter requested.',
                link='/documents',
                is_read=random.random() > 0.4,
            ),
        ]

        tasks_list = list(Task.objects.all()[:20])
        notif_created = 0

        for emp in att_employees:
            if not mgr_list:
                continue
            mgr = emp.manager or random.choice(mgr_list)
            task = random.choice(tasks_list) if tasks_list else None

            # Pick 2-5 random notification types per employee
            chosen = random.sample(notification_templates, k=min(random.randint(2, 5), len(notification_templates)))
            for template in chosen:
                try:
                    kwargs = template(emp, mgr, task)
                    Notification.objects.create(**kwargs)
                    notif_created += 1
                except Exception:
                    pass

        self.stdout.write(self.style.SUCCESS(f'  Done — {notif_created} notifications'))

        self.stdout.write(self.style.SUCCESS('\n=== Seed complete! All credentials: Demo@1234 ==='))
