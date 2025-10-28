from rest_framework import serializers

class MyIDSessionCreateSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    birth_date = serializers.DateField(required=False, allow_null=True)
    is_resident = serializers.BooleanField(required=False, allow_null=True)
    pass_data = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    pinfl = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class MyIDVerifySerializer(serializers.Serializer):
    code = serializers.CharField()


class MyIDSessionStatusSerializer(serializers.Serializer):
    session_id = serializers.CharField()

