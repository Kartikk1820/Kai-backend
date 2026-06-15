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
TASK_DELETE_ANY = 'task.delete_any'
TEAM_MANAGE = 'team.manage'

# HRMS - attendance
HR_VIEW_ATTENDANCE_ALL = 'hr.view_attendance_all'
HR_MARK_ATTENDANCE = 'hr.mark_attendance'

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

# Admin / RBAC
USER_CREATE = 'user.create'
USER_MANAGE_ROLES = 'user.manage_roles'
USER_RESET_PASSWORD = 'user.reset_password'
RBAC_MANAGE = 'rbac.manage'

# Grouped for UI display (Permission catalog screen) and for seeding.
CATALOG = {
    'Tasks': [
        (TASK_VIEW_ALL, 'View all tasks'),
        (TASK_CREATE, 'Create tasks'),
        (TASK_ASSIGN, 'Assign tasks to others'),
        (TASK_TRANSITION_ANY, 'Override task status (any transition)'),
        (TASK_DELETE_ANY, 'Delete any task'),
        (TEAM_MANAGE, 'Create & manage teams'),
    ],
    'Attendance': [
        (HR_VIEW_ATTENDANCE_ALL, 'View everyone\'s attendance'),
        (HR_MARK_ATTENDANCE, 'Mark / correct attendance'),
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
        (HR_VIEW_DIRECTORY, 'View employee directory'),
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
        TASK_CREATE,
    ],
    'Manager': [
        TASK_VIEW_ALL, TASK_CREATE, TASK_ASSIGN, TEAM_MANAGE,
        HR_VIEW_ATTENDANCE_ALL, HR_VIEW_LEAVE_ALL, HR_APPROVE_LEAVE,
        HR_MANAGE_LEAVE_BALANCE, HR_VIEW_DIRECTORY,
    ],
    'HR Manager': [
        HR_VIEW_ATTENDANCE_ALL, HR_MARK_ATTENDANCE, HR_VIEW_LEAVE_ALL,
        HR_APPROVE_LEAVE, HR_MANAGE_LEAVE_BALANCE, HR_VIEW_PAYROLL_ALL,
        HR_MANAGE_COMPENSATION, HR_RUN_PAYROLL, HR_MANAGE_INCENTIVE,
        HR_VIEW_DIRECTORY,
    ],
    'Admin': list(ALL_KEYS),
}
