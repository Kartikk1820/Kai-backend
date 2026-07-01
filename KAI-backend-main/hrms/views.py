import datetime

from django.http import HttpResponse
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics, permissions, filters
from drf_spectacular.utils import extend_schema, extend_schema_view
from django.contrib.auth import get_user_model

from core.permissions import HasPermissionKey, HasAnyPermissionKey
from core.permissions_catalog import (
    HR_MARK_ATTENDANCE, HR_MARK_ATTENDANCE_TEAM,
    HR_VIEW_ATTENDANCE_ALL, HR_VIEW_ATTENDANCE_TEAM,
    HR_RUN_PAYROLL, HR_MANAGE_COMPENSATION,
    HR_MANAGE_INCENTIVE, HR_VIEW_DIRECTORY, HR_MANAGE_LEAVE_BALANCE,
    HR_VIEW_PRESENCE_ALL, HR_VIEW_DIRECTORY_TEAM,
    USER_MANAGE_ROLES, HR_MANAGE_ENTITY, HR_MANAGE_CALENDAR,
)
from core.services import write_audit
from notifications.services import notify
from users.models import Entity, Department, EmployeeBankAccount
from .models import (
    Attendance, LeaveBalance, LeaveRequest, PayrollRecord, AdvanceSalaryRequest,
    CompensationVersion, Incentive, PayrollRun,
    WeeklyOffRule, WorkingCalendarEntry, ProfessionalTaxSlab,
)
from .serializers import (
    AttendanceSerializer, LeaveBalanceSerializer, LeaveRequestSerializer,
    PayrollRecordSerializer, AdvanceSalaryRequestSerializer, CompensationVersionSerializer,
    EmployeeDetailSerializer, EmployeeUpdateSerializer, IncentiveSerializer, PayrollRunSerializer,
    EntitySerializer, DepartmentSerializer, WeeklyOffRuleSerializer, WorkingCalendarEntrySerializer,
    ProfessionalTaxSlabSerializer, EmployeeBankAccountSerializer,
)
from .services import LeaveService, PayrollService, IncentiveService, can_approve_for

User = get_user_model()


def _is_privileged(user, perm_key):
    return user.user_type == 'Admin' or user.has_perm_key(perm_key)


# ============================ Entity & calendar admin ============================

class EntityListCreateView(generics.ListCreateAPIView):
    serializer_class = EntitySerializer
    queryset = Entity.objects.all()

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated()]
        return [HasPermissionKey.of(HR_MANAGE_ENTITY)()]


class DepartmentListCreateView(generics.ListCreateAPIView):
    serializer_class = DepartmentSerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated()]
        return [HasPermissionKey.of(HR_MANAGE_ENTITY)()]

    def get_queryset(self):
        qs = Department.objects.all()
        entity_id = self.request.query_params.get('entity_id')
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        return qs


class DepartmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [HasPermissionKey.of(HR_MANAGE_ENTITY)]
    serializer_class = DepartmentSerializer
    queryset = Department.objects.all()
    http_method_names = ['get', 'patch', 'delete']


class EntityDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [HasPermissionKey.of(HR_MANAGE_ENTITY)]
    serializer_class = EntitySerializer
    queryset = Entity.objects.all()
    http_method_names = ['get', 'patch']


class WeeklyOffRuleListCreateView(generics.ListCreateAPIView):
    permission_classes = [HasPermissionKey.of(HR_MANAGE_ENTITY)]
    serializer_class = WeeklyOffRuleSerializer

    def get_queryset(self):
        qs = WeeklyOffRule.objects.select_related('entity')
        if self.request.query_params.get('entity_id'):
            qs = qs.filter(entity_id=self.request.query_params['entity_id'])
        return qs


class WeeklyOffRuleDetailView(generics.DestroyAPIView):
    permission_classes = [HasPermissionKey.of(HR_MANAGE_ENTITY)]
    serializer_class = WeeklyOffRuleSerializer
    queryset = WeeklyOffRule.objects.all()


class WorkingCalendarEntryListCreateView(generics.ListCreateAPIView):
    permission_classes = [HasPermissionKey.of(HR_MANAGE_CALENDAR)]
    serializer_class = WorkingCalendarEntrySerializer

    def get_queryset(self):
        qs = WorkingCalendarEntry.objects.select_related('entity')
        p = self.request.query_params
        if p.get('entity_id'):
            qs = qs.filter(entity_id=p['entity_id'])
        if p.get('year'):
            qs = qs.filter(date__year=p['year'])
        if p.get('month'):
            qs = qs.filter(date__month=p['month'])
        return qs


class WorkingCalendarEntryDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [HasPermissionKey.of(HR_MANAGE_CALENDAR)]
    serializer_class = WorkingCalendarEntrySerializer
    queryset = WorkingCalendarEntry.objects.all()
    http_method_names = ['get', 'patch', 'delete']


class ProfessionalTaxSlabListCreateView(generics.ListCreateAPIView):
    permission_classes = [HasPermissionKey.of(HR_MANAGE_ENTITY)]
    serializer_class = ProfessionalTaxSlabSerializer

    def get_queryset(self):
        qs = ProfessionalTaxSlab.objects.select_related('entity')
        if self.request.query_params.get('entity_id'):
            qs = qs.filter(entity_id=self.request.query_params['entity_id'])
        return qs


class ProfessionalTaxSlabDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [HasPermissionKey.of(HR_MANAGE_ENTITY)]
    serializer_class = ProfessionalTaxSlabSerializer
    queryset = ProfessionalTaxSlab.objects.all()
    http_method_names = ['get', 'patch', 'delete']


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
            total_seconds = 0
            for session in att.sessions.filter(clock_out_time__isnull=False):
                base = datetime.datetime.combine(att.date, session.clock_in_time)
                out = datetime.datetime.combine(att.date, session.clock_out_time)
                if out < base:
                    out += datetime.timedelta(days=1)
                total_seconds += (out - base).total_seconds()
            previously_worked_hours = round(total_seconds / 3600, 2)

        return Response({
            'is_clocked_in': is_clocked_in,
            'clock_in_time': clock_in_time,
            'today_date': today.strftime('%Y-%m-%d'),
            'working_hours_so_far': att.working_hours if att else 0.0,
            'previously_worked_hours': previously_worked_hours,
        })


class ClockInView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(summary="Clock in")
    def post(self, request):
        today = timezone.localtime().date()
        now_time = timezone.localtime().time()
        att, created = Attendance.objects.get_or_create(
            employee=request.user, date=today,
            defaults={'status': 'present', 'source': 'clock_in'},
        )
        if not created and att.source != 'clock_in':
            # Preserve existing status (e.g. holiday/weekly_off set by calendar seed),
            # but still allow clocking in — mark source as clock_in override.
            att.status = 'present'
            att.source = 'clock_in'
            att.save()

        if att.sessions.filter(clock_out_time__isnull=True).exists():
            return Response({'error': 'Already clocked in'}, status=status.HTTP_400_BAD_REQUEST)

        from .models import AttendanceSession
        session = AttendanceSession.objects.create(attendance=att, clock_in_time=now_time)

        try:
            from .tasks import notify_eight_hours_reached
            worked = att.working_hours
            remaining = 8.0 - worked
            if remaining > 0:
                notify_eight_hours_reached.apply_async(
                    (request.user.id, str(today)), countdown=int(remaining * 3600)
                )
        except Exception as e:
            import logging
            logging.error(f"Failed to schedule 8hr notification: {e}")

        return Response(
            {'message': 'Clocked in', 'clock_in_time': session.clock_in_time.strftime('%H:%M:%S')},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


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
        return Response({
            'message': 'Clocked out',
            'clock_out_time': active_session.clock_out_time.strftime('%H:%M:%S'),
            'working_hours': att.working_hours,
        })


@extend_schema_view(get=extend_schema(summary="Attendance records"))
class AttendanceRecordsView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AttendanceSerializer

    def get_queryset(self):
        from django.db.models import Q
        qs = Attendance.objects.select_related('employee').prefetch_related('sessions').order_by('-date')
        user = self.request.user
        if _is_privileged(user, HR_VIEW_ATTENDANCE_ALL):
            emp = self.request.query_params.get('employee_id')
            if emp:
                qs = qs.filter(employee_id=emp)
        elif user.has_perm_key(HR_VIEW_ATTENDANCE_TEAM):
            # own records + direct reports
            qs = qs.filter(Q(employee=user) | Q(employee__manager=user)).distinct()
            emp = self.request.query_params.get('employee_id')
            if emp:
                qs = qs.filter(employee_id=emp)
        else:
            qs = qs.filter(employee=user)
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
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(summary="Mark / correct attendance (privileged or team-lead)")
    def post(self, request):
        data = request.data
        emp_id, date_str = data.get('employee_id'), data.get('date')
        if not emp_id or not date_str:
            return Response({'error': 'employee_id and date are required'}, status=400)

        # Full: admin/HR can mark anyone. Team: manager can only mark direct reports.
        if not _is_privileged(request.user, HR_MARK_ATTENDANCE):
            if not request.user.has_perm_key(HR_MARK_ATTENDANCE_TEAM):
                return Response({'detail': 'Not allowed.'}, status=403)
            try:
                target_employee = User.objects.get(pk=emp_id)
            except User.DoesNotExist:
                return Response({'error': 'Employee not found.'}, status=404)
            if target_employee.manager_id != request.user.id:
                return Response({'detail': 'You can only mark attendance for your direct reports.'}, status=403)

        att, _ = Attendance.objects.get_or_create(employee_id=emp_id, date=date_str)
        new_status = data.get('status', att.status)
        new_is_half_day = data.get('is_half_day', att.is_half_day)

        # present + is_half_day is invalid — route to half_day status instead.
        NON_LEAVE_STATUSES = {'present', 'wfh', 'weekly_off', 'holiday', 'unmarked', 'absent'}
        if new_is_half_day and new_status in NON_LEAVE_STATUSES:
            new_status = 'half_day'
            new_is_half_day = False

        att.status = new_status
        att.source = 'admin_override'
        att.is_half_day = new_is_half_day

        in_time_str = data.get('clock_in_time')
        out_time_str = data.get('clock_out_time')

        if in_time_str or out_time_str:
            from .models import AttendanceSession
            att.sessions.all().delete()
            session = AttendanceSession(attendance=att)
            if in_time_str:
                try:
                    session.clock_in_time = datetime.datetime.strptime(in_time_str, '%H:%M:%S').time()
                except ValueError:
                    return Response({'error': 'Invalid clock_in_time. Use HH:MM:SS'}, status=400)
            else:
                session.clock_in_time = datetime.time(9, 0, 0)
            if out_time_str:
                try:
                    session.clock_out_time = datetime.datetime.strptime(out_time_str, '%H:%M:%S').time()
                except ValueError:
                    return Response({'error': 'Invalid clock_out_time. Use HH:MM:SS'}, status=400)
            session.save()

        att.notes = data.get('notes', att.notes)
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
        if not request.user.has_perm_key(HR_MANAGE_LEAVE_BALANCE) and request.user.user_type != 'Admin':
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
        from django.db.models import Q
        qs = LeaveRequest.objects.select_related('employee')
        user = self.request.user
        if not _is_privileged(user, 'hr.view_leave_all'):
            qs = qs.filter(Q(employee=user) | Q(employee__manager=user)).distinct()
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


# ============================ Compensation (versioned) ============================

class CompensationVersionListCreateView(generics.ListCreateAPIView):
    permission_classes = [HasPermissionKey.of(HR_MANAGE_COMPENSATION)]
    serializer_class = CompensationVersionSerializer

    def get_queryset(self):
        qs = CompensationVersion.objects.select_related('employee')
        if self.request.query_params.get('employee_id'):
            qs = qs.filter(employee_id=self.request.query_params['employee_id'])
        return qs

    def perform_create(self, serializer):
        data = serializer.validated_data
        PayrollService.create_compensation_version(
            employee=data['employee'],
            effective_from=data['effective_from'],
            basic_salary=data['basic_salary'],
            hra=data.get('hra'),
            special_allowance=data.get('special_allowance'),
            conveyance_allowance=data.get('conveyance_allowance'),
            medical_allowance=data.get('medical_allowance'),
            other_allowance=data.get('other_allowance'),
            incentive=data.get('monthly_incentive', 0),
            tds=data.get('monthly_tds', 0),
            actor=self.request.user,
            request=self.request,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        emp_id = serializer.validated_data['employee'].id
        version = (
            CompensationVersion.objects
            .filter(employee_id=emp_id, effective_to__isnull=True)
            .order_by('-effective_from')
            .first()
        )
        return Response(CompensationVersionSerializer(version).data, status=status.HTTP_201_CREATED)


class CompensationVersionDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [HasPermissionKey.of(HR_MANAGE_COMPENSATION)]
    serializer_class = CompensationVersionSerializer
    queryset = CompensationVersion.objects.all()
    http_method_names = ['get', 'patch']

    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        allowed = {
            'basic_salary', 'hra', 'special_allowance', 'conveyance_allowance',
            'medical_allowance', 'other_allowance', 'monthly_incentive', 'monthly_tds',
        }
        for field in set(request.data.keys()) - allowed:
            return Response(
                {'error': f'Cannot update {field} on existing version. Create a new version instead.'},
                status=400,
            )
        return super().partial_update(request, *args, **kwargs)


# ============================ Payroll ============================

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
            return Response({'error': 'month and year are required'}, status=400)
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
        from django.db import IntegrityError
        try:
            inc = serializer.save(granted_by=self.request.user, status='scheduled')
        except IntegrityError:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'detail': 'An incentive already exists for this employee in this month/year.'})
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


class IncentiveSendAllView(APIView):
    permission_classes = [HasPermissionKey.of(HR_MANAGE_INCENTIVE)]

    @extend_schema(summary="Send all scheduled incentives for a month/year")
    def post(self, request):
        month = request.data.get('month')
        year = request.data.get('year')
        if not month or not year:
            return Response({'error': 'month and year are required'}, status=400)
        qs = Incentive.objects.filter(status='scheduled', month=int(month), year=int(year))
        sent, errors = 0, []
        for inc in qs:
            try:
                IncentiveService.send(inc.id, user=request.user, request=request)
                sent += 1
            except Exception as e:
                errors.append({'id': inc.id, 'error': str(e)})
        write_audit(actor=request.user, model_name='Incentive', object_id=0,
                    action='send_all', new_state='sent', request=request,
                    context={'month': month, 'year': year, 'sent': sent, 'errors': len(errors)})
        return Response({'sent': sent, 'errors': errors})


# ============================ Directory ============================

class EmployeePresenceView(APIView):
    permission_classes = [HasAnyPermissionKey.of(HR_VIEW_DIRECTORY, HR_VIEW_PRESENCE_ALL, HR_VIEW_DIRECTORY_TEAM)]

    def get(self, request):
        user = request.user
        today = timezone.localtime().date()
        from .models import AttendanceSession
        clocked_in_ids = set(
            AttendanceSession.objects
            .filter(attendance__date=today, clock_out_time__isnull=True)
            .values_list('attendance__employee_id', flat=True)
        )
        has_all = (user.user_type == 'Admin' or
                   user.has_perm_key(HR_VIEW_DIRECTORY) or
                   user.has_perm_key(HR_VIEW_PRESENCE_ALL))
        if has_all:
            uid_qs = User.objects.exclude(user_type='Client').values_list('id', flat=True)
        else:
            from tasks.models import Team
            from django.db.models import Q
            team_ids = Team.objects.filter(Q(members=user) | Q(lead=user)).values_list('id', flat=True)
            uid_qs = Team.objects.filter(id__in=team_ids).values_list('members__id', flat=True).distinct()
        result = {}
        for uid in uid_qs:
            result[str(uid)] = 'present' if uid in clocked_in_ids else 'offline'
        return Response(result)


class EmployeeListView(generics.ListAPIView):
    permission_classes = [HasAnyPermissionKey.of(HR_VIEW_DIRECTORY, HR_VIEW_DIRECTORY_TEAM)]
    serializer_class = EmployeeDetailSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['first_name', 'last_name', 'email', 'designation__name']
    ordering = ['id']

    def get_queryset(self):
        user = self.request.user
        qs = User.objects.exclude(user_type='Client').select_related('entity')
        if user.user_type == 'Admin' or user.has_perm_key(HR_VIEW_DIRECTORY):
            return qs
        from tasks.models import Team
        from django.db.models import Q
        team_ids = Team.objects.filter(Q(members=user) | Q(lead=user)).values_list('id', flat=True)
        member_ids = Team.objects.filter(id__in=team_ids).values_list('members__id', flat=True).distinct()
        return qs.filter(id__in=member_ids)


class EmployeeDetailView(generics.RetrieveUpdateAPIView):
    queryset = User.objects.exclude(user_type='Client').select_related('entity')

    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH'):
            return [HasPermissionKey.of(USER_MANAGE_ROLES)()]
        return [HasAnyPermissionKey.of(HR_VIEW_DIRECTORY, HR_VIEW_DIRECTORY_TEAM)()]

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return EmployeeUpdateSerializer
        return EmployeeDetailSerializer

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        instance = self.get_object()
        ser = EmployeeUpdateSerializer(instance, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        instance.refresh_from_db()
        return Response(EmployeeDetailSerializer(instance).data)


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
        amount = serializer.validated_data['amount']
        months = serializer.validated_data['proposed_recovery_months']
        monthly = round(amount / months, 2) if months else amount
        serializer.save(employee=self.request.user, status='pending', monthly_recovery_amount=monthly)


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


# ============================ Bank Accounts ============================

class BankAccountListCreateView(APIView):
    """
    GET  — returns bank accounts for the requesting employee (or any employee if HR_MANAGE_COMPENSATION).
    POST — creates a new bank account (deactivates previous active account for that employee).
    """
    permission_classes = [permissions.IsAuthenticated]

    def _target_employee_id(self, request):
        if _is_privileged(request.user, HR_MANAGE_COMPENSATION):
            return request.query_params.get('employee_id') or request.data.get('employee_id') or request.user.id
        return request.user.id

    def get(self, request):
        emp_id = self._target_employee_id(request)
        qs = EmployeeBankAccount.objects.filter(employee_id=emp_id).order_by('-effective_from')
        return Response(EmployeeBankAccountSerializer(qs, many=True).data)

    def post(self, request):
        emp_id = self._target_employee_id(request)
        try:
            emp_id = int(emp_id)
        except (TypeError, ValueError):
            return Response({'error': 'Invalid employee_id'}, status=status.HTTP_400_BAD_REQUEST)

        bank_name = request.data.get('bank_name', '').strip()
        account_number = request.data.get('account_number', '').strip()
        ifsc_code = request.data.get('ifsc_code', '').strip()
        if not bank_name or not account_number:
            return Response({'error': 'bank_name and account_number are required'}, status=status.HTTP_400_BAD_REQUEST)

        # Deactivate existing active accounts for this employee
        EmployeeBankAccount.objects.filter(employee_id=emp_id, is_active=True).update(is_active=False)
        account = EmployeeBankAccount.objects.create(
            employee_id=emp_id,
            bank_name=bank_name,
            account_number=account_number,
            ifsc_code=ifsc_code,
            is_active=True,
        )
        write_audit(actor=request.user, model_name='EmployeeBankAccount', object_id=account.id,
                    action='created', new_state='active', request=request)
        return Response(EmployeeBankAccountSerializer(account).data, status=status.HTTP_201_CREATED)


# ============================ Reports ============================

class AttendanceMonthlyReportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    STATUS_KEYS = [
        'present', 'wfh', 'half_day', 'sick_leave', 'casual_leave',
        'earned_leave', 'lop', 'weekly_off', 'holiday', 'absent', 'unmarked',
    ]
    STATUS_LABELS = [
        'Present', 'WFH', 'Half Day', 'Sick Leave', 'Casual Leave',
        'Earned Leave', 'LOP', 'Weekly Off', 'Holiday', 'Absent', 'Unmarked',
    ]

    def get(self, request):
        from collections import defaultdict
        import csv as csv_mod
        import io

        user = request.user
        if not _is_privileged(user, HR_VIEW_ATTENDANCE_ALL):
            return Response({'detail': 'Permission denied.'}, status=403)

        year = request.query_params.get('year')
        month = request.query_params.get('month')
        if not year or not month:
            return Response({'detail': 'year and month are required.'}, status=400)
        try:
            year, month = int(year), int(month)
        except ValueError:
            return Response({'detail': 'Invalid year/month.'}, status=400)

        qs = (
            Attendance.objects
            .filter(date__year=year, date__month=month)
            .select_related('employee', 'employee__entity', 'employee__department')
            .prefetch_related('sessions')
            .order_by('employee__first_name', 'employee__last_name', 'date')
        )

        if request.query_params.get('entity_id'):
            qs = qs.filter(employee__entity_id=request.query_params['entity_id'])
        if request.query_params.get('department_id'):
            qs = qs.filter(employee__department_id=request.query_params['department_id'])
        if request.query_params.get('employee_id'):
            qs = qs.filter(employee_id=request.query_params['employee_id'])

        def blank_row():
            return {
                'employee_id': None,
                'employee_name': '',
                'entity': '',
                'department': '',
                'total_working_hours': 0.0,
                **{k: 0 for k in self.STATUS_KEYS},
            }

        by_emp = defaultdict(blank_row)
        for att in qs:
            row = by_emp[att.employee_id]
            row['employee_id'] = att.employee_id
            row['employee_name'] = f"{att.employee.first_name} {att.employee.last_name}".strip() or att.employee.email
            row['entity'] = att.employee.entity.name if att.employee.entity_id else ''
            row['department'] = att.employee.department.name if att.employee.department_id else ''
            row[att.status] = row.get(att.status, 0) + 1
            row['total_working_hours'] = round(row['total_working_hours'] + (att.working_hours or 0), 2)

        data = sorted(by_emp.values(), key=lambda r: r['employee_name'])

        if request.query_params.get('format') == 'csv':
            from django.http import HttpResponse
            buf = io.StringIO()
            writer = csv_mod.writer(buf)
            writer.writerow(['Employee', 'Entity', 'Department'] + self.STATUS_LABELS + ['Working Hours (h)'])
            for row in data:
                writer.writerow(
                    [row['employee_name'], row['entity'], row['department']]
                    + [row[k] for k in self.STATUS_KEYS]
                    + [row['total_working_hours']]
                )
            resp = HttpResponse(buf.getvalue(), content_type='text/csv')
            resp['Content-Disposition'] = f'attachment; filename="attendance_{year}_{month:02d}.csv"'
            return resp

        return Response(data)


class BankAccountDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _get_account(self, pk, user):
        try:
            account = EmployeeBankAccount.objects.get(pk=pk)
        except EmployeeBankAccount.DoesNotExist:
            return None, 404
        if not _is_privileged(user, HR_MANAGE_COMPENSATION) and account.employee_id != user.id:
            return None, 403
        return account, 200

    def patch(self, request, pk):
        account, code = self._get_account(pk, request.user)
        if account is None:
            return Response(status=code)
        allowed_fields = {'bank_name', 'account_number', 'ifsc_code', 'is_active'}
        for field, value in request.data.items():
            if field in allowed_fields:
                setattr(account, field, value)
        account.save()
        return Response(EmployeeBankAccountSerializer(account).data)

    def delete(self, request, pk):
        account, code = self._get_account(pk, request.user)
        if account is None:
            return Response(status=code)
        account.is_active = False
        account.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
