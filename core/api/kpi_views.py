from django.db.models import Q
from rest_framework import viewsets, status, serializers
from rest_framework.permissions import IsAuthenticated
from core.api.permissions import IsHrOrReadOnly
from core.permissions import IsHRAdmin, IsCompanyMember
from rest_framework.decorators import action
from rest_framework.response import Response

from core.models import (
    KpiCategory, KpiTemplate, KpiFramework, PerformanceCycle,
    EmployeeKpiAssignment, KpiMeasurement, KpiFrameworkItem,
    EmployeeKpiOverride, PerformanceReview,
)
from core.serializers import (
    KpiCategorySerializer, KpiTemplateSerializer, KpiFrameworkSerializer,
    KpiFrameworkItemSerializer, EmployeeKpiOverrideSerializer,
    PerformanceCycleSerializer, EmployeeKpiAssignmentSerializer,
    KpiMeasurementSerializer, PerformanceReviewSerializer,
)
from core.kpi_service import KpiAssignmentService



class KpiCategoryViewSet(viewsets.ModelViewSet):
    queryset = KpiCategory.objects.all()
    serializer_class = KpiCategorySerializer
    lookup_field = 'uuid'
    permission_classes = [IsAuthenticated, IsHrOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        user = getattr(self.request, 'user', None)
        if user and getattr(user, 'company_id', None):
            return qs.filter(company=user.company)
        return qs.none()

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company, created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class KpiTemplateViewSet(viewsets.ModelViewSet):
    queryset = KpiTemplate.objects.all()
    serializer_class = KpiTemplateSerializer
    lookup_field = 'uuid'
    permission_classes = [IsAuthenticated, IsHrOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        user = getattr(self.request, 'user', None)
        if user and getattr(user, 'company_id', None):
            return qs.filter(company=user.company)
        return qs.none()

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company, created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class KpiFrameworkViewSet(viewsets.ModelViewSet):
    queryset = KpiFramework.objects.all()
    serializer_class = KpiFrameworkSerializer
    lookup_field = 'uuid'
    permission_classes = [IsAuthenticated, IsHrOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        user = getattr(self.request, 'user', None)
        if user and getattr(user, 'company_id', None):
            return qs.filter(company=user.company)
        return qs.none()

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company, created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @action(detail=True, methods=['post'])
    def publish(self, request, uuid=None):
        framework = self.get_object()
        try:
            framework.validate_publishing()
        except serializers.ValidationError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        framework.status = KpiFramework.Status.PUBLISHED
        framework.updated_by = request.user
        framework.save(update_fields=['status', 'updated_by', 'updated_at'])
        return Response(self.get_serializer(framework).data)


class KpiFrameworkItemViewSet(viewsets.ModelViewSet):
    queryset = KpiFrameworkItem.objects.all()
    serializer_class = KpiFrameworkItemSerializer
    lookup_field = 'id'
    permission_classes = [IsAuthenticated, IsHrOrReadOnly]

    def perform_create(self, serializer):
        # Ensure framework belongs to the requesting user's company
        framework = serializer.validated_data.get('framework')
        user = self.request.user
        if framework and framework.company_id != getattr(user, 'company_id', None):
            raise serializers.ValidationError('Cannot add items to a framework outside your company.')
        serializer.save()

    def perform_update(self, serializer):
        framework = serializer.validated_data.get('framework') or getattr(serializer.instance, 'framework', None)
        user = self.request.user
        if framework and framework.company_id != getattr(user, 'company_id', None):
            raise serializers.ValidationError('Cannot modify items for a framework outside your company.')
        serializer.save()

    def get_queryset(self):
        qs = super().get_queryset()
        user = getattr(self.request, 'user', None)
        if user and getattr(user, 'company_id', None):
            return qs.filter(framework__company=user.company)
        return qs.none()


class EmployeeKpiOverrideViewSet(viewsets.ModelViewSet):
    queryset = EmployeeKpiOverride.objects.all()
    serializer_class = EmployeeKpiOverrideSerializer
    lookup_field = 'id'
    permission_classes = [IsAuthenticated, IsHrOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        user = getattr(self.request, 'user', None)
        if user and getattr(user, 'company_id', None):
            if user.role == 'HR_ADMIN' or user.is_superuser:
                return qs.filter(company=user.company)
            return qs.filter(company=user.company, employee=user)
        return qs.none()

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company, created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def perform_destroy(self, instance):
        instance.delete()


class PerformanceCycleViewSet(viewsets.ModelViewSet):
    queryset = PerformanceCycle.objects.all()
    serializer_class = PerformanceCycleSerializer
    lookup_field = 'uuid'
    permission_classes = [IsAuthenticated, IsHrOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        user = getattr(self.request, 'user', None)
        if user and getattr(user, 'company_id', None):
            return qs.filter(company=user.company)
        return qs.none()

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company, created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @action(detail=True, methods=['get'], permission_classes=[IsHRAdmin])
    def preview_assignments(self, request, uuid=None):
        cycle = self.get_object()
        preview = KpiAssignmentService.preview_cycle_assignments(cycle)
        return Response(preview, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def score_summary(self, request, uuid=None):
        cycle = self.get_object()
        user = request.user
        employee_uuid = request.query_params.get('employee_uuid')
        from core.models import Employee
        from core.kpi_scoring_service import KpiScoringService

        if employee_uuid:
            try:
                target_emp = Employee.objects.get(uuid=employee_uuid, company=user.company)
            except Employee.DoesNotExist:
                return Response({'detail': 'Employee not found.'}, status=status.HTTP_404_NOT_FOUND)

            is_hr = user.is_superuser or getattr(user, 'role', None) == 'HR_ADMIN'
            is_manager_of_emp = (getattr(user, 'role', None) == 'MANAGER' and target_emp.manager_id == user.id)
            is_self = (target_emp.id == user.id)
            if not (is_hr or is_manager_of_emp or is_self):
                return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

            summary = KpiScoringService.evaluate_cycle_for_employee(cycle, target_emp)
            return Response(summary, status=status.HTTP_200_OK)

        if user.is_superuser or getattr(user, 'role', None) == 'HR_ADMIN':
            active_emps = Employee.objects.filter(company=user.company, is_active=True)
            summaries = [KpiScoringService.evaluate_cycle_for_employee(cycle, emp) for emp in active_emps]
            return Response({
                'cycle_uuid': str(cycle.uuid),
                'cycle_name': cycle.name,
                'total_employees': len(summaries),
                'employees': summaries,
            }, status=status.HTTP_200_OK)

        summary = KpiScoringService.evaluate_cycle_for_employee(cycle, user)
        return Response(summary, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[IsHRAdmin])
    def generate_assignments(self, request, uuid=None):
        cycle = self.get_object()
        assignments = KpiAssignmentService.generate_assignments_for_cycle(cycle)
        serializer = EmployeeKpiAssignmentSerializer(assignments, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)





class EmployeeKpiAssignmentViewSet(viewsets.ModelViewSet):
    queryset = EmployeeKpiAssignment.objects.all()
    serializer_class = EmployeeKpiAssignmentSerializer
    lookup_field = 'uuid'
    permission_classes = [IsAuthenticated, IsHrOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        user = getattr(self.request, 'user', None)
        if not user or not getattr(user, 'company_id', None):
            return qs.none()
        if user.is_superuser or getattr(user, 'role', None) == 'HR_ADMIN':
            return qs.filter(company=user.company)
        if getattr(user, 'role', None) == 'MANAGER':
            return qs.filter(company=user.company).filter(
                Q(employee=user) | Q(employee__manager=user)
            )
        return qs.filter(company=user.company, employee=user)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company, created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class KpiMeasurementViewSet(viewsets.ModelViewSet):
    queryset = KpiMeasurement.objects.all()
    serializer_class = KpiMeasurementSerializer
    lookup_field = 'uuid'
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        user = getattr(self.request, 'user', None)
        if not user or not getattr(user, 'company_id', None):
            return qs.none()
        if user.is_superuser or getattr(user, 'role', None) == 'HR_ADMIN':
            return qs.filter(company=user.company)
        if getattr(user, 'role', None) == 'MANAGER':
            return qs.filter(company=user.company).filter(
                Q(assignment__employee=user) | Q(assignment__employee__manager=user)
            )
        return qs.filter(company=user.company, assignment__employee=user)

    def perform_create(self, serializer):
        assignment = serializer.validated_data['assignment']
        user = self.request.user
        can_record = (
            user.is_superuser
            or user.role == 'HR_ADMIN'
            or assignment.employee_id == user.id
            or (user.role == 'MANAGER' and assignment.employee.manager_id == user.id)
        )
        if assignment.company_id != user.company_id or not can_record:
            raise serializers.ValidationError('You cannot record a measurement for this KPI assignment.')
        serializer.save(
            company=user.company,
            recorded_by=user,
            created_by=user,
            updated_by=user,
        )

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class PerformanceReviewViewSet(viewsets.ModelViewSet):
    queryset = PerformanceReview.objects.all()
    serializer_class = PerformanceReviewSerializer
    lookup_field = 'uuid'
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        qs = super().get_queryset()
        user = getattr(self.request, 'user', None)
        if not user or not getattr(user, 'company_id', None):
            return qs.none()
        if user.is_superuser or getattr(user, 'role', None) == 'HR_ADMIN':
            return qs.filter(company=user.company)
        if getattr(user, 'role', None) == 'MANAGER':
            return qs.filter(company=user.company).filter(
                Q(employee=user) | Q(employee__manager=user) | Q(reviewer=user)
            )
        if getattr(user, 'role', None) == 'HOD' and getattr(user, 'org_unit_id', None):
            return qs.filter(company=user.company, employee__org_unit=user.org_unit)
        return qs.filter(company=user.company, employee=user)

    def create(self, request, *args, **kwargs):
        return Response(
            {'detail': 'Performance reviews are initialized through a performance cycle.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @action(detail=True, methods=['post'])
    def self_assessment(self, request, uuid=None):
        review = self.get_object()
        user = request.user
        if review.employee_id != user.id:
            return Response({'detail': 'Only the employee can submit their self assessment.'}, status=status.HTTP_403_FORBIDDEN)
        if review.status != PerformanceReview.Status.DRAFT:
            return Response({'detail': 'Self assessment is only allowed while the review is in DRAFT.'}, status=status.HTTP_400_BAD_REQUEST)

        self_score = request.data.get('employee_self_score')
        comments = request.data.get('employee_comments', '')
        if self_score is not None:
            review.employee_self_score = self_score
        review.employee_comments = comments
        review.status = PerformanceReview.Status.SUBMITTED
        review.updated_by = user
        review.save()
        return Response(self.get_serializer(review).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def manager_review(self, request, uuid=None):
        review = self.get_object()
        user = request.user
        is_manager = (review.employee.manager_id == user.id or review.reviewer_id == user.id)
        if not is_manager:
            return Response({'detail': 'Only the assigned manager can submit a manager review.'}, status=status.HTTP_403_FORBIDDEN)
        if review.status != PerformanceReview.Status.SUBMITTED:
            return Response({'detail': 'Manager review requires an employee-submitted review.'}, status=status.HTTP_400_BAD_REQUEST)

        manager_score = request.data.get('manager_score')
        manager_comments = request.data.get('manager_comments', '')
        if manager_score is not None:
            review.manager_score = manager_score
        review.manager_comments = manager_comments
        review.reviewer = user
        review.status = PerformanceReview.Status.MANAGER_REVIEWED
        review.updated_by = user
        review.save()
        return Response(self.get_serializer(review).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[IsHRAdmin])
    def hr_review(self, request, uuid=None):
        review = self.get_object()
        if review.status != PerformanceReview.Status.MANAGER_REVIEWED:
            return Response({'detail': 'HR review requires a manager-reviewed review.'}, status=status.HTTP_400_BAD_REQUEST)

        hr_score = request.data.get('hr_score')
        hr_comments = request.data.get('hr_comments', '')
        if hr_score is not None:
            review.hr_score = hr_score
        review.hr_comments = hr_comments
        review.status = PerformanceReview.Status.HR_REVIEWED
        review.updated_by = request.user
        review.save()
        return Response(self.get_serializer(review).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[IsHRAdmin])
    def calibrate(self, request, uuid=None):
        review = self.get_object()
        if review.status != PerformanceReview.Status.HR_REVIEWED:
            return Response({'detail': 'Calibration requires an HR-reviewed review.'}, status=status.HTTP_400_BAD_REQUEST)

        calibrated_score = request.data.get('calibrated_score')
        if calibrated_score is None:
            return Response({'calibrated_score': 'This field is required.'}, status=status.HTTP_400_BAD_REQUEST)

        from django.utils import timezone
        review.calibrated_score = calibrated_score
        review.calibrated_by = request.user
        review.calibrated_at = timezone.now()
        review.final_comments = request.data.get('reason', request.data.get('final_comments', review.final_comments))
        review.status = PerformanceReview.Status.CALIBRATED
        review.updated_by = request.user
        review.save()
        return Response(self.get_serializer(review).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[IsHRAdmin])
    def finalize(self, request, uuid=None):
        review = self.get_object()
        if review.status != PerformanceReview.Status.CALIBRATED:
            return Response({'detail': 'Finalization requires a calibrated review.'}, status=status.HTTP_400_BAD_REQUEST)

        from django.utils import timezone
        final_score = request.data.get('final_score')
        if final_score is None:
            final_score = (
                review.calibrated_score
                if review.calibrated_score is not None
                else (
                    review.hr_score
                    if review.hr_score is not None
                    else (
                        review.manager_score
                        if review.manager_score is not None
                        else review.system_score
                    )
                )
            )

        review.final_score = final_score
        if 'final_comments' in request.data:
            review.final_comments = request.data.get('final_comments')
        review.finalized_by = request.user
        review.finalized_at = timezone.now()
        review.status = PerformanceReview.Status.FINALIZED
        review.updated_by = request.user
        review.save()
        return Response(self.get_serializer(review).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], permission_classes=[IsHRAdmin])
    def initialize_cycle_reviews(self, request):
        cycle_uuid = request.data.get('cycle_uuid')
        if not cycle_uuid:
            return Response({'cycle_uuid': 'This field is required.'}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        from core.models import PerformanceCycle, Employee
        from core.kpi_scoring_service import KpiScoringService

        try:
            cycle = PerformanceCycle.objects.get(uuid=cycle_uuid, company=user.company)
        except PerformanceCycle.DoesNotExist:
            return Response({'detail': 'Performance cycle not found.'}, status=status.HTTP_404_NOT_FOUND)

        employees = Employee.objects.filter(company=user.company, is_active=True)
        created_or_updated = []

        for emp in employees:
            summary = KpiScoringService.evaluate_cycle_for_employee(cycle, emp)
            system_score = summary.get('total_performance_score', 0)

            review, created = PerformanceReview.objects.get_or_create(
                company=user.company,
                cycle=cycle,
                employee=emp,
                defaults={
                    'reviewer': emp.manager,
                    'system_score': system_score,
                    'status': PerformanceReview.Status.DRAFT,
                    'created_by': user,
                    'updated_by': user,
                }
            )
            if not created and review.status != PerformanceReview.Status.FINALIZED:
                review.system_score = system_score
                if not review.reviewer and emp.manager:
                    review.reviewer = emp.manager
                review.updated_by = user
                review.save(update_fields=['system_score', 'reviewer', 'updated_by', 'updated_at'])

            created_or_updated.append(review)

        serializer = PerformanceReviewSerializer(created_or_updated, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

