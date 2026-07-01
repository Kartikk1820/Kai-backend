"""
The fixed catalog of atomic permission keys used across KAI.
These are surfaced to the frontend via /auth/me/ and enforced by DRF permission
classes. Roles/Groups bundle these; users receive groups (+ optional overrides).
"""

# Tasks
TASK_VIEW_ALL = 'task.view_all'
TASK_CREATE = 'task.create'
TASK_ASSIGN = 'task.assign'
TASK_TRANSITION_ANY = 'task.transition_any'   # admin override on the board
TASK_APPROVE = 'task.approve'
TASK_BLOCK = 'task.block'
TASK_REOPEN = 'task.reopen'
TASK_MANAGE = 'task.manage_tasks'
TASK_MANAGE_COMMENTS = 'task.manage_comments'
TEAM_MANAGE = 'team.manage'

# HRMS - attendance
HR_VIEW_ATTENDANCE_ALL = 'hr.view_attendance_all'
HR_VIEW_ATTENDANCE_TEAM = 'hr.view_attendance_team'   # own + direct reports only
HR_MARK_ATTENDANCE = 'hr.mark_attendance'
HR_MARK_ATTENDANCE_TEAM = 'hr.mark_attendance_team'   # direct reports only

# HRMS - leave
HR_VIEW_LEAVE_ALL = 'hr.view_leave_all'
HR_APPROVE_LEAVE = 'hr.approve_leave'
HR_MANAGE_LEAVE_BALANCE = 'hr.manage_leave_balance'

# HRMS - payroll
HR_VIEW_PAYROLL_ALL = 'hr.view_payroll_all'
HR_MANAGE_COMPENSATION = 'hr.manage_compensation'
HR_RUN_PAYROLL = 'hr.run_payroll'
HR_MANAGE_INCENTIVE = 'hr.manage_incentive'

# Directory
HR_VIEW_DIRECTORY = 'hr.view_directory'
HR_VIEW_PRESENCE_ALL = 'hr.view_presence_all'    # see clock-in status for all employees
HR_VIEW_DIRECTORY_TEAM = 'hr.view_directory_team'  # see only own team members in directory

# Entity & calendar admin
HR_MANAGE_ENTITY = 'hr.manage_entity'      # Entity, WeeklyOffRule, PT slabs
HR_MANAGE_CALENDAR = 'hr.manage_calendar'  # WorkingCalendarEntry (public holidays)

# Admin / RBAC
USER_CREATE = 'user.create'
USER_MANAGE_ROLES = 'user.manage_roles'
USER_RESET_PASSWORD = 'user.reset_password'
RBAC_MANAGE = 'rbac.manage'

# Bids - BidOpportunity
BID_VIEW_OPPORTUNITY = 'bid.view_opportunity'
BID_CREATE_OPPORTUNITY = 'bid.create_opportunity'
BID_UPDATE_OPPORTUNITY = 'bid.update_opportunity'
BID_DELETE_OPPORTUNITY = 'bid.delete_opportunity'

# Bids - ClientBid
BID_VIEW_BID = 'bid.view_bid'
BID_CREATE_BID = 'bid.create_bid'
BID_UPDATE_BID = 'bid.update_bid'
BID_DELETE_BID = 'bid.delete_bid'

# Grouped for UI display (Permission catalog screen) and for seeding.
CATALOG = {
    'Tasks': [
        (TASK_VIEW_ALL, 'View all tasks'),
        (TASK_CREATE, 'Create tasks'),
        (TASK_ASSIGN, 'Assign tasks to others'),
        (TASK_TRANSITION_ANY, 'Transition any task (Admin override)'),
        (TASK_APPROVE, 'Approve tasks (move to Done)'),
        (TASK_BLOCK, 'Block tasks'),
        (TASK_REOPEN, 'Reopen completed tasks'),
        (TASK_MANAGE, 'Manage tasks (edit/delete any)'),
        (TASK_MANAGE_COMMENTS, 'Manage comments (edit/delete any)'),
        (TEAM_MANAGE, 'Create & manage teams'),
    ],
    'Attendance': [
        (HR_VIEW_ATTENDANCE_ALL, 'View everyone\'s attendance'),
        (HR_VIEW_ATTENDANCE_TEAM, 'View own + direct reports\' attendance'),
        (HR_MARK_ATTENDANCE, 'Mark / correct any employee\'s attendance'),
        (HR_MARK_ATTENDANCE_TEAM, 'Mark / correct direct reports\' attendance'),
    ],
    'Leave': [
        (HR_VIEW_LEAVE_ALL, 'View all leave requests'),
        (HR_APPROVE_LEAVE, 'Approve / reject any leave'),
        (HR_MANAGE_LEAVE_BALANCE, 'Edit leave balances'),
    ],
    'Payroll': [
        (HR_VIEW_PAYROLL_ALL, 'View all payroll'),
        (HR_MANAGE_COMPENSATION, 'Manage compensation'),
        (HR_RUN_PAYROLL, 'Run payroll'),
        (HR_MANAGE_INCENTIVE, 'Grant & manage incentives'),
    ],
    'Directory': [
        (HR_VIEW_DIRECTORY, 'View all employees in directory'),
        (HR_VIEW_PRESENCE_ALL, 'View present/offline status of all employees'),
        (HR_VIEW_DIRECTORY_TEAM, 'View own team members in directory only'),
    ],
    'Entity & Calendar': [
        (HR_MANAGE_ENTITY, 'Manage entities, weekly-off rules, PT slabs'),
        (HR_MANAGE_CALENDAR, 'Manage public holiday calendar'),
    ],
    'Bids': [
        (BID_VIEW_OPPORTUNITY, 'View bid opportunities'),
        (BID_CREATE_OPPORTUNITY, 'Create bid opportunities'),
        (BID_UPDATE_OPPORTUNITY, 'Edit bid opportunities'),
        (BID_DELETE_OPPORTUNITY, 'Delete bid opportunities'),
        (BID_VIEW_BID, 'View client bids'),
        (BID_CREATE_BID, 'Create client bids'),
        (BID_UPDATE_BID, 'Edit client bids (status, comments, etc.)'),
        (BID_DELETE_BID, 'Delete client bids'),
    ],
    'Admin': [
        (USER_CREATE, 'Create users'),
        (USER_MANAGE_ROLES, 'Assign roles & permissions'),
        (USER_RESET_PASSWORD, 'Reset user passwords'),
        (RBAC_MANAGE, 'Manage roles & groups'),
    ],
}

ALL_KEYS = [key for group in CATALOG.values() for (key, _label) in group]

# Default role -> permission bundles used by the seeder.
ROLE_BUNDLES = {
    'Employee': [
        BID_VIEW_OPPORTUNITY, BID_VIEW_BID,
        HR_VIEW_PRESENCE_ALL, HR_VIEW_DIRECTORY_TEAM,
    ],
    'Client': [
        # Clients get no internal permissions by default.
    ],
    'Manager': [
        TASK_VIEW_ALL, TASK_CREATE, TASK_ASSIGN, TEAM_MANAGE,
        TASK_APPROVE, TASK_BLOCK, TASK_REOPEN,
        HR_VIEW_ATTENDANCE_TEAM, HR_MARK_ATTENDANCE_TEAM,
        HR_VIEW_LEAVE_ALL, HR_APPROVE_LEAVE,
        HR_MANAGE_LEAVE_BALANCE, HR_VIEW_DIRECTORY, HR_VIEW_PRESENCE_ALL,
        BID_VIEW_OPPORTUNITY, BID_CREATE_OPPORTUNITY, BID_UPDATE_OPPORTUNITY, BID_DELETE_OPPORTUNITY,
        BID_VIEW_BID, BID_CREATE_BID, BID_UPDATE_BID, BID_DELETE_BID,
    ],
    'HR Manager': [
        HR_VIEW_ATTENDANCE_ALL, HR_MARK_ATTENDANCE, HR_VIEW_LEAVE_ALL,
        HR_APPROVE_LEAVE, HR_MANAGE_LEAVE_BALANCE, HR_VIEW_PAYROLL_ALL,
        HR_MANAGE_COMPENSATION, HR_RUN_PAYROLL, HR_MANAGE_INCENTIVE,
        HR_VIEW_DIRECTORY, HR_VIEW_PRESENCE_ALL, HR_MANAGE_CALENDAR,
        BID_VIEW_OPPORTUNITY, BID_VIEW_BID,
    ],
    'Admin': list(ALL_KEYS),
}
