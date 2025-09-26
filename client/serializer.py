from django.contrib.gis.geos import Point

from users.models import AbstractUser, ClientProfile
from .models import ClientReyting, OrderImage
from .models import Order, ClientNews, ClientTarif, TarifHaridi

from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


class OrderImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderImage
        fields = ['id', 'image']

class ClientInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['full_name', 'phone']


class OrderSerializer(serializers.ModelSerializer):
    images = OrderImageSerializer(many=True, read_only=True)
    image = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False
    )
    client_info = ClientInfoSerializer(source='client', read_only=True)
    created_at = serializers.DateTimeField(format="%Y-%m-%d", read_only=True)

    # yangi qo‘shiladigan fieldlar (faqat create uchun)
    longitude = serializers.FloatField(write_only=True, required=False)
    latitude = serializers.FloatField(write_only=True, required=False)

    class Meta:
        model = Order
        fields = [
            'id', 'job_category', 'job_id', 'desc', 'price', 'full_desc',
            'region', 'city', 'gender', 'worker_count',
            'point', 'longitude', 'latitude',   # qo‘shildi
            'images', 'image', 'client_info', 'created_at', 'status',
        ]

    def validate(self, data):
        request = self.context['request']
        if request.user.role != "client":
            raise serializers.ValidationError("Only clients can create orders.")
        return data

    def create(self, validated_data):
        image_files = validated_data.pop('image', [])
        job_ids = validated_data.pop('job_id', [])
        lon = validated_data.pop('longitude', None)
        lat = validated_data.pop('latitude', None)

        validated_data['client'] = self.context['request'].user

        # longitude va latitude bo‘lsa, point yasaymiz
        if lon is not None and lat is not None:
            validated_data['point'] = Point(lon, lat)

        if not validated_data.get("point"):
            raise serializers.ValidationError({"point": "Order uchun joylashuv (point) majburiy."})

        order = Order.objects.create(**validated_data)

        if job_ids:
            order.job_id.set(job_ids)

        for img in image_files[:5]:
            OrderImage.objects.create(order=order, image=img)

        return order

class ClientRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password_confirmation = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'full_name', 'phone', 'password', 'password_confirmation', 'city', 'region', 'gender']

    def validate(self, attrs):
        # Parollarni tekshirish
        if attrs['password'] != attrs['password_confirmation']:
            raise serializers.ValidationError("Passwords do not match")

        # Telefon + client kombinatsiyasi bo‘yicha tekshirish
        phone = attrs.get("phone")
        if User.objects.filter(phone=phone, role="client").exists():
            raise serializers.ValidationError(
                {"detail": "Bu telefon raqam allaqachon client sifatida ro‘yxatdan o‘tgan."}
            )

        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirmation')

        client = User.objects.create_user(
            phone=validated_data['phone'],
            full_name=validated_data['full_name'],
            password=validated_data['password'],
            region=validated_data.get('region'),
            city=validated_data.get('city'),
            gender=validated_data.get('gender'),
            role="client"
        )

        # ClientProfile yaratish
        ClientProfile.objects.create(user=client)

        return client

class ClientLoginSerializer(serializers.Serializer):
    phone = serializers.CharField()
    password = serializers.CharField(write_only=True)
    tarif = serializers.SerializerMethodField()

    def validate(self, data):
        phone = data.get("phone")
        password = data.get("password")
        client = User.objects.filter(phone=phone, role="client").first()

        if client and client.check_password(password):
            # 0 so‘mlik tarif faqat mavjud bo‘lmasa, ulash
            self.ensure_default_tarif(client)
            return client
        else:
            raise serializers.ValidationError("Invalid phone or password")

    def get_tarif(self, obj):
        tarif_haridi = TarifHaridi.objects.filter(user=obj, status=True).first()
        if tarif_haridi:
            tarif = tarif_haridi.tarif_id
            return {
                "id": tarif.id,
                "name": tarif.name,
                "price": tarif.price,
                "top_limit": tarif.top_limit,
                "call_limit": tarif.call_limit,
            }
        return None

    def ensure_default_tarif(self, user):
        """
        Foydalanuvchi uchun faqat bitta tarif yozuvini yaratadi yoki mavjudini ishlatadi.
        """
        default_tarif = ClientTarif.objects.filter(price=0).first()
        if default_tarif:
            TarifHaridi.objects.get_or_create(
                user=user,
                tarif_id=default_tarif,
                defaults={"status": True}
            )


class ClientPasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    confirm_new_password = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value

    def validate(self, data):
        if data['new_password'] != data['confirm_new_password']:
            raise serializers.ValidationError("New passwords do not match.")
        return data

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class ClientDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = AbstractUser
        fields = ['id', 'phone', 'full_name', 'avatar', 'description']


class WorkerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientReyting
        fields = ['id', 'reyting', 'active_orders', 'completed_orders', 'cancelled_orders', ]


class ClientNewsSerializer(serializers.ModelSerializer):

    class Meta:
        model = ClientNews
        fields = ['id', 'description', 'image', ]


class ClientTarifSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientTarif
        fields = ['id', 'name', 'price', 'top_limit', 'call_limit', ]


class TarifHaridiSerializer(serializers.ModelSerializer):
    tarif_id = ClientTarifSerializer(read_only=True)

    class Meta:
        model = TarifHaridi
        fields = ['id', 'user', 'tarif_id', 'status', ]


class ClientPhoneUpdateSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_phone = serializers.CharField()

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value

    def validate_new_phone(self, value):
        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError("This phone number is already in use.")
        return value

    def save(self, **kwargs):
        user = self.context['request'].user
        if user.role != 'client':
            raise serializers.ValidationError("Only workers can update their phone number.")
        new_phone = self.validated_data['new_phone']
        user.phone = new_phone
        user.save()
        return user
