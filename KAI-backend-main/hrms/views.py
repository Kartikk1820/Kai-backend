from django.http import HttpResponse
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics, permissions, filters
from drf_spectacular.utils import extend_schema, extend_schema_view
from django.contrib.auth import get_user_model
import datetime

from core.permissions import HasPermissionKey
from core.permissions_catalog import (
    HR_MARK_ATTENDANCE, HR_RUN_PAYROLL, HR_MANAGE_COMPENSATION,
    HR_MANAGE_INCENTIVE, HR_VIEW_DIRECTORY, HR_MANAGE_LEAVE_BALANCE,
)
from core.services import write_audit
from notifications.services import notify
from .models import (
    Attendance, LeaveBalance, LeaveRequest, PayrollRecord, AdvanceSalaryRequest,
    Compensation, Incentive, PayrollRun,
)
from .serializers import (
    AttendanceSerializer, LeaveBalanceSerializer, LeaveRequestSerializer,
    PayrollRecordSerializer, AdvanceSalaryRequestSerializer, CompensationSerializer,
    EmployeeDetailSerializer, IncentiveSerializer, PayrollRunSerializer,
)
from .services import LeaveService, PayrollService, IncentiveService, can_approve_for

User = get_user_model()


def _is_privileged(user, perm_key):
    return user.role == 'Admin' or user.has_perm_key(perm_key)


# ============================ Attendance ============================

class AttendanceStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(summary="Current clock status")
    def get(self, request):
        today = timezone.localtime().date()
        att = Attendance.objects.filter(employee=request.user, date=today).first()
        active_session = att.sessions.filter(clock_out_time__isnull=True).first() if att else None
        
        is_clocked_in = active_session is not None
        clock_in_time = active_session.clock_in_time.strftime('%H:%M:%S') if active_session else None
        
        previously_worked_hours = 0.0
        if att:
            from datetime import datetime
            total_seconds = 0
            for session in att.sessions.filter(clock_out_time__isnull=False):
                base = datetime.combine(att.date, session.clock_in_time)
                out = datetime.combine(att.date, session.clock_out_time)
                if out < base:
                    from datetime import timedelta
                    out += timedelta(days=1)
                total_seconds += (out - base).total_seconds()
            previously_worked_hours = round(total_seconds / 3600, 2)
        
        return Response({
            'is_clocked_in': is_clocked_in,
            'clock_in_time': clock_in_time,
            'today_date': today.strftime('%Y-%m-%d'),
            'working_hours_so_far': att.working_hours if att else 0.0,
            'previously_worked_hours': previously_worked_hours
        })


class ClockInView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(summary="Clock in")
    def post(self, request):
        today = timezone.localtime().date()
        now_time = timezone.localtime().time()
        att, created = Attendance.objects.get_or_create(
            employee=request.user, date=today, defaults={'status': 'present'})
            
        if att.sessions.filter(clock_out_time__isnull=True).exists():
            return Response({'error': 'Already clocked in'}, status=status.HTTP_400_BAD_REQUEST)
            
        from .models import AttendanceSession
        session = AttendanceSession.objects.create(attendance=att, clock_in_time=now_time)
        att.status = 'present'
        att.save()
        
        try:
            from .tasks import notify_eight_hours_reached
            worked = att.working_hours
            remaining = 8.0 - worked
            if remaining > 0:
                notify_eight_hours_reached.apply_async((request.user.id, str(today)), countdown=int(remaining * 3600))
        except Exception as e:
            import logging
            logging.error(f"Failed to schedule 8hr notification: {e}")
            
        return Response({'message': 'Clocked in', 'clock_in_time': session.clock_in_time.strftime('%H:%M:%S')},
                        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class ClockOutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(summary="Clock out")
    def post(self, request):
        today = timezone.localtime().date()
        now_time = timezone.localtime().time()
        att = Attendance.objects.filter(employee=request.user, date=today).first()
        
        if not att:
            return Response({'error': "You haven't clocked in yet"}, status=status.HTTP_400_BAD_REQUEST)
            
        active_session = att.sessions.filter(clock_out_time__isnull=True).first()
        if not active_session:
            return Response({'error': 'Already clocked out'}, status=status.HTTP_400_BAD_REQUEST)
            
        active_session.clock_out_time = now_time
        active_session.save()
        
        return Response({'message': 'Clocked out',
                         'clock_out_time': active_session.clock_out_time.strftime('%H:%M:%S'),
                         'working_hours': att.working_hours})


@extend_schema_view(get=extend_schema(summary="Attendance records"))
class AttendanceRecordsView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AttendanceSerializer

    def get_queryset(self):
        qs = Attendance.objects.select_related('employee').order_by('-date')
        user = self.request.user
        if not _is_privileged(user, 'hr.view_attendance_all'):
            qs = qs.filter(employee=user)
        else:
            emp = self.request.query_params.get('employee_id')
            if emp:
                qs = qs.filter(employee_id=emp)
        p = self.request.query_params
        if p.get('start_date'):
            qs = qs.filter(date__gte=p['start_date'])
        if p.get('end_date'):
            qs = qs.filter(date__lte=p['end_date'])
        if p.get('monthYear'):
            y, m = p['monthYear'].split('-')
            qs = qs.filter(date__year=y, date__month=m)
        return qs


class MarkAttendanceView(APIView):
    permission_classes = [HasPermissionKey.of(HR_MARK_ATTENDANCE)]

    @extend_schema(summary="Mark / correct attendance (privileged)")
    def post(self, request):
        data = request.data
        emp_id, date = data.get('employee_id'), data.get('date')
        if not emp_id or not date:
            return Response({'error': 'employee_id and date are required'}, status=400)
        att, _ = Attendance.objects.get_or_create(employee_id=emp_id, date=date)
        att.status = data.get('status', att.status)
        
        in_time_str = data.get('clock_in_time')
        out_time_str = data.get('clock_out_time')
        
        if in_time_str or out_time_str:
            from .models import AttendanceSession
            # If admin marks time manually, we'll replace the sessions with a single explicit one.
            att.sessions.all().delete()
            session = AttendanceSession(attendance=att)
            if in_time_str:
                try:
                    session.clock_in_time = datetime.datetime.strptime(in_time_str, '%H:%M:%S').time()
                except ValueError:
                    return Response({'error': 'Invalid clock_in_time. Use HH:MM:SS'}, status=400)
            else:
                session.clock_in_time = datetime.time(9, 0, 0) # default fallback if only out provided
                
            if out_time_str:
                try:
                    session.clock_out_time = datetime.datetime.strptime(out_time_str, '%H:%M:%S').time()
                except ValueError:
                    return Response({'error': 'Invalid clock_out_time. Use HH:MM:SS'}, status=400)
            session.save()
            
        att.notes = data.get('notes', att.notes)
        att.marked_by_admin = True
        att.save()
        write_audit(actor=request.user, model_name='Attendance', object_id=att.id,
                    action='marked', new_state=att.status, request=request)
        return Response(AttendanceSerializer(att).data, status=201)


# ============================ Leave ============================

class LeaveBalanceView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(summary="Leave balance")
    def get(self, request):
        emp_id = request.query_params.get('employee_id')
        if emp_id and _is_privileged(request.user, 'hr.view_leave_all'):
            balance, _ = LeaveBalance.objects.get_or_create(employee_id=emp_id)
        else:
            balance, _ = LeaveBalance.objects.get_or_create(employee=request.user)
        return Response(LeaveBalanceSerializer(balance).data)

    @extend_schema(summary="Edit leave balance (privileged)")
    def patch(self, request):
        if not request.user.has_perm_key(HR_MANAGE_LEAVE_BALANCE) and request.user.role != 'Admin':
            return Response({'detail': 'Not allowed.'}, status=403)
        emp_id = request.data.get('employee_id')
        balance, _ = LeaveBalance.objects.get_or_create(employee_id=emp_id)
        for f in ('sick_total', 'casual_total', 'earned_total'):
            if f in request.data:
                setattr(balance, f, request.data[f])
        balance.save()
        return Response(LeaveBalanceSerializer(balance).data)


@extend_schema_view(get=extend_schema(summary="List leave requests"))
class LeaveRequestListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = LeaveRequestSerializer

    def get_queryset(self):
        qs = LeaveRequest.objects.select_related('employee')
        user = self.request.user
        if not _is_privileged(user, 'hr.view_leave_all'):
            qs = qs.filter(employee=user)
        else:
            emp = self.request.query_params.get('employee_id')
            if emp:
                qs = qs.filter(employee_id=emp)
        p = self.request.query_params
        if p.get('leave_type'):
            qs = qs.filter(leave_type=p['leave_type'])
        if p.get('status'):
            qs = qs.filter(status=p['status'])
        if p.get('monthYear'):
            y, m = p['monthYear'].split('-')
            qs = qs.filter(from_date__year=y, from_date__month=m)
        return qs


class LeaveRequestCreateView(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = LeaveRequestSerializer

    def perform_create(self, serializer):
        leave = serializer.save(employee=self.request.user, status='pending')
        # notify approver (manager) that a request was submitted
        if self.request.user.manager_id:
            notify(user=self.request.user.manager, kind='leave_submitted',
                   title='Leave request submitted',
                   body=f'{self.request.user.full_name} requested {leave.leave_type} leave.',
                   link='/hrms?tab=leave', actor=self.request.user)


class LeaveRequestStatusUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(summary="Approve / reject / cancel leave")
    def patch(self, request, pk):
        new_status = request.data.get('status')
        if new_status == 'cancelled':
            leave = LeaveService.cancel(pk, request.user, request=request)
        elif new_status == 'approved':
            leave = LeaveService.approve(pk, request.user, request=request)
        elif new_status == 'rejected':
            leave = LeaveService.reject(pk, request.user,
                                        request.data.get('rejection_reason'), request=request)
        else:
            return Response({'error': 'Invalid status'}, status=400)
        return Response(LeaveRequestSerializer(leave).data)


# ============================ Payroll & Compensation ============================

class CompensationListView(generics.ListCreateAPIView):
    permission_classes = [HasPermissionKey.of(HR_MANAGE_COMPENSATION)]
    serializer_class = CompensationSerializer
    queryset = Compensation.objects.select_related('employee').all()


class CompensationDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [HasPermissionKey.of(HR_MANAGE_COMPENSATION)]
    serializer_class = CompensationSerializer
    queryset = Compensation.objects.all()
    http_method_names = ['get', 'patch']


@extend_schema_view(get=extend_schema(summary="List payroll slips"))
class PayrollRecordListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PayrollRecordSerializer

    def get_queryset(self):
        qs = PayrollRecord.objects.select_related('employee')
        user = self.request.user
        if not _is_privileged(user, 'hr.view_payroll_all'):
            qs = qs.filter(employee=user)
        else:
            emp = self.request.query_params.get('employee_id')
            if emp:
                qs = qs.filter(employee_id=emp)
        p = self.request.query_params
        if p.get('slip_type'):
            qs = qs.filter(slip_type=p['slip_type'])
        if p.get('entity'):
            qs = qs.filter(entity=p['entity'])
        if p.get('monthYear'):
            y, m = p['monthYear'].split('-')
            qs = qs.filter(year=y, month=m)
        return qs


class PayrollSlipDownloadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(summary="Download slip PDF")
    def get(self, request, pk):
        record = generics.get_object_or_404(PayrollRecord, pk=pk)
        if not _is_privileged(request.user, 'hr.view_payroll_all') and record.employee_id != request.user.id:
            return Response(status=status.HTTP_403_FORBIDDEN)
        from .pdf import render_slip_pdf
        pdf_bytes = render_slip_pdf(record)
        resp = HttpResponse(pdf_bytes, content_type='application/pdf')
        resp['Content-Disposition'] = f'attachment; filename="{record.slip_type}_slip_{record.id}.pdf"'
        return resp


class PayrollRunView(APIView):
    permission_classes = [HasPermissionKey.of(HR_RUN_PAYROLL)]

    @extend_schema(summary="Trigger a salary payroll run")
    def post(self, request):
        month, year = request.data.get('month'), request.data.get('year')
        if not month or not year:
            return Response({'error': 'Month and year are required'}, status=400)
        # Run via Celery in production; run inline if eager/not configured.
        run = PayrollService.run_salary(int(month), int(year), user=request.user, request=request)
        return Response(PayrollRunSerializer(run).data, status=status.HTTP_202_ACCEPTED)


# ============================ Incentives ============================

class IncentiveListCreateView(generics.ListCreateAPIView):
    permission_classes = [HasPermissionKey.of(HR_MANAGE_INCENTIVE)]
    serializer_class = IncentiveSerializer

    def get_queryset(self):
        qs = Incentive.objects.select_related('employee')
        p = self.request.query_params
        if p.get('status'):
            qs = qs.filter(status=p['status'])
        if p.get('monthYear'):
            y, m = p['monthYear'].split('-')
            qs = qs.filter(year=y, month=m)
        return qs

    def perform_create(self, serializer):
        inc = serializer.save(granted_by=self.request.user, status='scheduled')
        write_audit(actor=self.request.user, model_name='Incentive', object_id=inc.id,
                    action='granted', new_state='scheduled', request=self.request)
        notify(user=inc.employee, kind='incentive_granted',
               title='Incentive scheduled',
               body=f'An incentive of {inc.amount} is scheduled.',
               link='/hrms?tab=payroll', actor=self.request.user)


class IncentiveDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [HasPermissionKey.of(HR_MANAGE_INCENTIVE)]
    serializer_class = IncentiveSerializer
    queryset = Incentive.objects.all()
    http_method_names = ['get', 'patch', 'delete']

    def destroy(self, request, *args, **kwargs):
        inc = self.get_object()
        if inc.status == 'sent':
            return Response({'detail': 'Cannot cancel a sent incentive.'}, status=400)
        inc.status = 'cancelled'
        inc.save()
        return Response(status=204)


class IncentiveSendNowView(APIView):
    permission_classes = [HasPermissionKey.of(HR_MANAGE_INCENTIVE)]

    @extend_schema(summary="Send an incentive immediately")
    def post(self, request, pk):
        inc = IncentiveService.send(pk, user=request.user, request=request)
        return Response(IncentiveSerializer(inc).data)


# ============================ Directory ============================

class EmployeeListView(generics.ListAPIView):
    permission_classes = [HasPermissionKey.of(HR_VIEW_DIRECTORY)]
    serializer_class = EmployeeDetailSerializer
    queryset = User.objects.exclude(role='Client')
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['first_name', 'last_name', 'email', 'sub_position']
    ordering = ['id']


class EmployeeDetailView(generics.RetrieveAPIView):
    permission_classes = [HasPermissionKey.of(HR_VIEW_DIRECTORY)]
    serializer_class = EmployeeDetailSerializer
    queryset = User.objects.exclude(role='Client')


# ============================ Advance salary ============================

@extend_schema_view(get=extend_schema(summary="List advance requests"))
class AdvanceSalaryListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AdvanceSalaryRequestSerializer

    def get_queryset(self):
        qs = AdvanceSalaryRequest.objects.select_related('employee')
        user = self.request.user
        if not _is_privileged(user, 'hr.view_payroll_all'):
            qs = qs.filter(employee=user)
        else:
            emp = self.request.query_params.get('employee_id')
            if emp:
                qs = qs.filter(employee_id=emp)
        if self.request.query_params.get('status'):
            qs = qs.filter(status=self.request.query_params['status'])
        return qs


class AdvanceSalaryCreateView(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AdvanceSalaryRequestSerializer

    def perform_create(self, serializer):
        serializer.save(employee=self.request.user, status='pending')


class AdvanceSalaryStatusUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(summary="Approve / reject advance")
    def patch(self, request, pk):
        adv = generics.get_object_or_404(AdvanceSalaryRequest, pk=pk)
        if not can_approve_for(request.user, adv.employee):
            return Response({'detail': 'Not allowed.'}, status=403)
        new_status = request.data.get('status')
        if new_status not in ('approved', 'rejected'):
            return Response({'error': 'Invalid status'}, status=400)
        adv.status = new_status
        adv.reviewed_by = request.user
        if new_status == 'rejected':
            adv.rejection_reason = request.data.get('rejection_reason')
        adv.save()
        write_audit(actor=request.user, model_name='AdvanceSalaryRequest', object_id=adv.id,
                    action='transition', new_state=new_status, request=request)
        return Response(AdvanceSalaryRequestSerializer(adv).data)
