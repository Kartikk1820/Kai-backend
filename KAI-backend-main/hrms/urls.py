from django.urls import path
from .views import (
    AttendanceStatusView, ClockInView, ClockOutView, AttendanceRecordsView, MarkAttendanceView,
    LeaveBalanceView, LeaveRequestListView, LeaveRequestCreateView, LeaveRequestStatusUpdateView,
    CompensationListView, CompensationDetailView,
    PayrollRecordListView, PayrollSlipDownloadView, PayrollRunView,
    BidBonusRunView, BonusConfigView,
    IncentiveListCreateView, IncentiveDetailView, IncentiveSendNowView,
    AdvanceSalaryListView, AdvanceSalaryCreateView, AdvanceSalaryStatusUpdateView,
    EmployeeListView, EmployeeDetailView,
)

urlpatterns = [
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
    path('payroll/compensation/', CompensationListView.as_view()),
    path('payroll/compensation/<int:pk>/', CompensationDetailView.as_view()),
    path('payroll/slips/', PayrollRecordListView.as_view()),
    path('payroll/slips/<int:pk>/download/', PayrollSlipDownloadView.as_view()),
    path('payroll/run/', PayrollRunView.as_view()),
    path('payroll/run-bid-bonuses/', BidBonusRunView.as_view()),
    path('payroll/bonus-config/', BonusConfigView.as_view()),

    # Incentives
    path('incentives/', IncentiveListCreateView.as_view()),
    path('incentives/<int:pk>/', IncentiveDetailView.as_view()),
    path('incentives/<int:pk>/send/', IncentiveSendNowView.as_view()),

    # Advances
    path('payroll/advances/', AdvanceSalaryListView.as_view()),
    path('payroll/advances/apply/', AdvanceSalaryCreateView.as_view()),
    path('payroll/advances/<int:pk>/status/', AdvanceSalaryStatusUpdateView.as_view()),

    # Directory
    path('view_employee/', EmployeeListView.as_view()),
    path('view_employee/<int:pk>/', EmployeeDetailView.as_view()),
]
