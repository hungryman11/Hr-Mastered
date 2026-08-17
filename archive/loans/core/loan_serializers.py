from rest_framework import serializers

from core.models import Employee, LoanCase, LoanCaseChecklistItem, LoanChecklistTemplateItem, LoanProduct


class LoanProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanProduct
        fields = ('uuid', 'name', 'is_active', 'created_at', 'updated_at')
        read_only_fields = ('uuid', 'created_at', 'updated_at')


class LoanChecklistTemplateItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanChecklistTemplateItem
        fields = ('uuid', 'loan_product', 'name', 'required', 'sort_order', 'created_at', 'updated_at')
        read_only_fields = ('uuid', 'loan_product', 'created_at', 'updated_at')


class LoanCaseChecklistItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanCaseChecklistItem
        fields = ('uuid', 'loan_case', 'name', 'required', 'status', 'evidence_reference', 'note', 'checked_by', 'checked_at', 'created_at', 'updated_at')
        read_only_fields = ('uuid', 'loan_case', 'name', 'required', 'created_at', 'updated_at', 'checked_by', 'checked_at')


class LoanCaseSerializer(serializers.ModelSerializer):
    checklist_items = LoanCaseChecklistItemSerializer(many=True, read_only=True)
    applicant_name = serializers.CharField(source='applicant.get_full_name', read_only=True)
    product_name = serializers.CharField(source='loan_product.name', read_only=True)
    applicant = serializers.SlugRelatedField(slug_field='uuid', queryset=Employee.objects.all())
    loan_product = serializers.SlugRelatedField(slug_field='uuid', queryset=LoanProduct.objects.all())

    class Meta:
        model = LoanCase
        fields = (
            'uuid', 'applicant', 'applicant_name', 'loan_product', 'product_name', 'requested_amount', 'purpose', 'repayment_months',
            'collateral_type', 'collateral_value', 'collateral_details', 'assigned_checker',
            'status', 'recommendation', 'decision_reason', 'checklist_items', 'created_at', 'updated_at',
        )
        read_only_fields = ('uuid', 'created_at', 'updated_at', 'checklist_items', 'applicant_name', 'product_name')

    def validate(self, attrs):
        amount = attrs.get('requested_amount', getattr(self.instance, 'requested_amount', None))
        collateral_value = attrs.get('collateral_value', getattr(self.instance, 'collateral_value', None))
        months = attrs.get('repayment_months', getattr(self.instance, 'repayment_months', None))
        if amount is not None and amount <= 0:
            raise serializers.ValidationError({'requested_amount': 'Requested amount must be positive.'})
        if collateral_value is not None and collateral_value <= 0:
            raise serializers.ValidationError({'collateral_value': 'Collateral value must be positive.'})
        if months is not None and months <= 0:
            raise serializers.ValidationError({'repayment_months': 'Repayment months must be positive.'})
        return attrs
