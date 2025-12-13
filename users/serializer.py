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

# Card add serializer
class BindCardInitSerializer(serializers.Serializer):
    card_number = serializers.CharField(max_length=16)
    expiry = serializers.CharField(max_length=5)

# Card confirm kod
class BindCardConfirmSerializer(serializers.Serializer):
    """
    SMS orqali karta tasdiqlash uchun serializer.
    """

    transaction_id = serializers.IntegerField(
        required=True,
        help_text="Oldin BindCardInitView orqali olingan transaction_id"
    )
    otp = serializers.CharField(
        required=True,
        max_length=6,
        min_length=4,
        help_text="Foydalanuvchiga SMS orqali kelgan kod"
    )

    def validate_otp(self, value):
        """
        OTP faqat raqamlardan iborat bo'lishi kerak.
        """
        if not value.isdigit():
            raise serializers.ValidationError("OTP faqat raqamlardan iborat bo'lishi kerak.")
        return value

    def validate_transaction_id(self, value):
        """
        Transaction mavjudligini tekshirish mumkin.
        Masalan, DBda shunday transaction yo'q bo'lsa xato berish.
        """
        from .models import UserCard
        if not UserCard.objects.filter(transaction_id=value).exists():
            raise serializers.ValidationError("Bunday transaction_id mavjud emas.")
        return value

# Card delete
class BindCardDeleteSerializer(serializers.Serializer):
    card_id = serializers.IntegerField()
    card_token = serializers.CharField(max_length=255)

# Payment serializer
class CreatePaymentSerializer(serializers.Serializer):
    amount = serializers.IntegerField()
    account = serializers.CharField()
    store_id = serializers.CharField()
    terminal_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    lang = serializers.CharField(required=False, default="uz")


#
class PreApplySerializer(serializers.Serializer):
    card_token = serializers.CharField(required=False, allow_blank=True)
    card_number = serializers.CharField(required=False, allow_blank=True)
    expiry = serializers.CharField(required=False, allow_blank=True)
    store_id = serializers.IntegerField()
    amount = serializers.IntegerField()
    transaction_id = serializers.IntegerField()

    def validate(self, data):
        card_token = data.get("card_token")
        card_number = data.get("card_number")
        expiry = data.get("expiry")

        # card_token bilan card_number + expiry birga bo‘lmasligi kerak
        if card_token and (card_number or expiry):
            raise serializers.ValidationError(
                "card_token yuborsang, card_number va expiry yuborib bo‘lmaydi."
            )

        # card_number bolsa expiry bolishi kerak
        if card_number and not expiry:
            raise serializers.ValidationError(
                "card_number yuborilsa, expiry ham bo‘lishi shart."
            )

        # card_token ham yo‘q, card_number ham yo‘q → xato
        if not card_token and not card_number:
            raise serializers.ValidationError(
                "card_token yoki card_number dan biri bo‘lishi shart."
            )

        return data


class ConfirmPaymentSerializer(serializers.Serializer):
    transaction_id = serializers.IntegerField()
    store_id = serializers.IntegerField()
    otp = serializers.CharField(required=False)  # card_token ishlatilsa ixtiyoriy

class CancelTransactionSerializer(serializers.Serializer):
    transaction_id = serializers.IntegerField()
    hold_amount = serializers.IntegerField(required=False)
    reason = serializers.CharField(required=False)
