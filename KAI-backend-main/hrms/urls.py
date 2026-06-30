from django.urls import path
from .views import (
    # Entity & calendar
    EntityListCreateView, EntityDetailView, DepartmentListCreateView, DepartmentDetailView,
    WeeklyOffRuleListCreateView, WeeklyOffRuleDetailView,
    WorkingCalendarEntryListCreateView, WorkingCalendarEntryDetailView,
    ProfessionalTaxSlabListCreateView, ProfessionalTaxSlabDetailView,
    # Attendance
    AttendanceStatusView, ClockInView, ClockOutView, AttendanceRecordsView, MarkAttendanceView,
    # Leave
    LeaveBalanceView, LeaveRequestListView, LeaveRequestCreateView, LeaveRequestStatusUpdateView,
    # Payroll & compensation
    CompensationVersionListCreateView, CompensationVersionDetailView,
    PayrollRecordListView, PayrollSlipDownloadView, PayrollRunView,
    # Incentives
    IncentiveListCreateView, IncentiveDetailView, IncentiveSendNowView, IncentiveSendAllView,
    # Advances
    AdvanceSalaryListView, AdvanceSalaryCreateView, AdvanceSalaryStatusUpdateView,
    # Directory
    EmployeeListView, EmployeeDetailView, EmployeePresenceView,
    # Bank accounts
    BankAccountListCreateView, BankAccountDetailView,
    # Reports
    AttendanceMonthlyReportView,
)

urlpatterns = [
    # Entity & calendar admin
    path('entities/', EntityListCreateView.as_view()),
    path('departments/', DepartmentListCreateView.as_view()),
    path('departments/<int:pk>/', DepartmentDetailView.as_view()),
    path('entities/<int:pk>/', EntityDetailView.as_view()),
    path('entities/weekly-off-rules/', WeeklyOffRuleListCreateView.as_view()),
    path('entities/weekly-off-rules/<int:pk>/', WeeklyOffRuleDetailView.as_view()),
    path('entities/calendar/', WorkingCalendarEntryListCreateView.as_view()),
    path('entities/calendar/<int:pk>/', WorkingCalendarEntryDetailView.as_view()),
    path('entities/pt-slabs/', ProfessionalTaxSlabListCreateView.as_view()),
    path('entities/pt-slabs/<int:pk>/', ProfessionalTaxSlabDetailView.as_view()),

    # Attendance
    path('attendance/status/', AttendanceStatusView.as_view()),
    path('attendance/clock-in/', ClockInView.as_view()),
    path('attendance/clock-out/', ClockOutView.as_view()),
    path('attendance/records/', AttendanceRecordsView.as_view()),
    path('attendance/mark/', MarkAttendanceView.as_view()),

    # Leave
    path('leave/balance/', LeaveBalanceView.as_view()),
    path('leave/requests/', LeaveRequestListView.as_view()),
    path('leave/requests/apply/', LeaveRequestCreateView.as_view()),
    path('leave/requests/<int:pk>/status/', LeaveRequestStatusUpdateView.as_view()),

    # Payroll & compensation
    path('payroll/compensation/', CompensationVersionListCreateView.as_view()),
    path('payroll/compensation/<int:pk>/', CompensationVersionDetailView.as_view()),
    path('payroll/slips/', PayrollRecordListView.as_view()),
    path('payroll/slips/<int:pk>/download/', PayrollSlipDownloadView.as_view()),
    path('payroll/run/', PayrollRunView.as_view()),

    # Incentives
    path('incentives/', IncentiveListCreateView.as_view()),
    path('incentives/<int:pk>/', IncentiveDetailView.as_view()),
    path('incentives/<int:pk>/send/', IncentiveSendNowView.as_view()),
    path('incentives/send-all/', IncentiveSendAllView.as_view()),

    # Advances
    path('payroll/advances/', AdvanceSalaryListView.as_view()),
    path('payroll/advances/apply/', AdvanceSalaryCreateView.as_view()),
    path('payroll/advances/<int:pk>/status/', AdvanceSalaryStatusUpdateView.as_view()),

    # Directory
    path('view_employee/', EmployeeListView.as_view()),
    path('view_employee/<int:pk>/', EmployeeDetailView.as_view()),
    path('employee-presence/', EmployeePresenceView.as_view()),

    # Bank accounts
    path('bank-accounts/', BankAccountListCreateView.as_view()),
    path('bank-accounts/<int:pk>/', BankAccountDetailView.as_view()),

    # Reports
    path('reports/attendance/monthly/', AttendanceMonthlyReportView.as_view()),
]
