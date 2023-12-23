# serializers.py

from rest_framework import serializers
from .models import Company, Transaction


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = '__all__'


class TransactionSerializer(serializers.ModelSerializer):
    # Add the split_ratio field to the serializer
    split_ratio = serializers.FloatField(required=False)

    class Meta:
        model = Transaction
        fields = '__all__'

    def create(self, validated_data):
        # Pop the split_ratio field from validated_data before calling create
        split_ratio = validated_data.pop('split_ratio', None)

        # Create the Transaction instance without the split_ratio field
        instance = super(TransactionSerializer, self).create(validated_data)

        # Set the split_ratio field on the instance if it exists
        if split_ratio is not None:
            instance.split_ratio = split_ratio
            instance.save()

        return instance

    def validate(self, data):
        trade_type = data.get('trade_type')
        split_ratio = data.get('split_ratio')

        if trade_type == 'SPLIT' and split_ratio is None:
            raise serializers.ValidationError("Split transactions require a split_ratio.")
        elif trade_type != 'SPLIT' and split_ratio is not None:
            raise serializers.ValidationError("Split_ratio is only applicable for 'SPLIT' transactions.")

        return data
