from django.contrib.auth import get_user_model
from rest_framework import serializers

from users.models import AbstractUser, WorkerProfile
from job.models import Job, CategoryJob
from worker.models import WorkerNews, WorkerImage
from job.models import Region, City

User = get_user_model()


class WorkerRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password_confirmation = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'full_name', 'phone', 'password', 'password_confirmation', 'region', 'city', 'gender']

    def validate(self, attrs):
        # Parollarni tekshirish
        if attrs['password'] != attrs['password_confirmation']:
            raise serializers.ValidationError("Passwords do not match")

        # Telefon + worker kombinatsiyasi bo‘yicha tekshirish
        phone = attrs.get("phone")
        if User.objects.filter(phone=phone, role="worker").exists():
            raise serializers.ValidationError(
                {"detail": "Bu telefon raqam allaqachon worker sifatida ro‘yxatdan o‘tgan."}
            )

        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirmation')

        worker = User.objects.create_user(
            phone=validated_data['phone'],
            full_name=validated_data['full_name'],
            password=validated_data['password'],
            region=validated_data.get('region'),
            city=validated_data.get('city'),
            gender=validated_data.get('gender'),
            role="worker"
        )

        # WorkerProfile yaratish
        WorkerProfile.objects.create(user=worker)

        return worker


class WorkerLoginSerializer(serializers.Serializer):
    phone = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        phone = data.get("phone")
        password = data.get("password")
        worker = User.objects.filter(phone=phone, role="worker").first()

        if worker and worker.check_password(password):
            return worker
        else:
            raise serializers.ValidationError("Invalid phone or password")


class WorkerPasswordChangeSerializer(serializers.Serializer):
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


class WorkerImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkerImage
        fields = ['id', 'image']


class WorkerSerializer(serializers.ModelSerializer):
    images = WorkerImageSerializer(source='profileimage', many=True, read_only=True)
    distance_km = serializers.SerializerMethodField()

    class Meta:
        model = AbstractUser
        fields = ['id', 'full_name', 'phone', 'avatar', 'job_id', 'description', 'reyting', 'images', 'distance_km']

    def get_distance_km(self, obj):
        if hasattr(obj, 'distance') and obj.distance:
            return round(obj.distance.km, 2)
        return None

class WorkerUpdateSerializer(serializers.ModelSerializer):
    images = WorkerImageSerializer(source='profileimage', many=True, read_only=True)

    class Meta:
        model = User
        fields = ['id', 'full_name', 'description', 'phone', 'avatar', 'images']


class UserUpdateSerializer(serializers.ModelSerializer):
    job_category = serializers.PrimaryKeyRelatedField(queryset=CategoryJob.objects.all())
    job_id = serializers.PrimaryKeyRelatedField(queryset=Job.objects.all(),
                                                many=True)

    class Meta:
        model = AbstractUser  # Bu serializer AbstractUser modeliga tegishli
        fields = ['job_category', 'job_id']  # faqat job_category va job_id ni yangilaymiz

    # Yangilanishni amalga oshirish
    def update(self, instance, validated_data):
        # Yangi job_category va job_id ni olish
        job_category_data = validated_data.get('job_category')
        if job_category_data:
            instance.job_category = job_category_data  # job_category ni yangilash

        job_data = validated_data.get('job_id')
        if job_data:
            instance.job_id.set(job_data)  # job_id (ManyToMany) ni yangilash

        instance.save()
        return instance


class JobCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoryJob
        fields = ['id', 'title_uz', 'title_ru', 'title_en']


class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = ['id', 'title_uz', 'title_ru', 'title_en']


class WorkerJobSerializer(serializers.ModelSerializer):
    job_category = JobCategorySerializer()  # `job_category`ni ID va nom bilan olish
    job_id = JobSerializer(many=True)  # `job_id` ManyToManyField bo‘lgani uchun ko‘plikda

    class Meta:
        model = AbstractUser
        fields = ['id', 'full_name', 'job_category', 'job_id']


class WorkerPhoneUpdateSerializer(serializers.Serializer):
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
        if user.role != 'worker':
            raise serializers.ValidationError("Only workers can update their phone number.")
        new_phone = self.validated_data['new_phone']
        user.phone = new_phone
        user.save()
        return user


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ['id', 'title']  # Kerakli maydonlarni kiriting


class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ['id', 'title', ]  # Kerakli maydonlarni kiriting


class WorkerNewsSerializer(serializers.ModelSerializer):

    class Meta:
        model = WorkerNews
        fields = ['id', 'description', 'image',]


class WorkerImageDeleteSerializer(serializers.Serializer):
    image_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        help_text="WorkerImage modelidagi rasmlarning id-larini yuboring",
    )

    def validate_image_ids(self, image_ids):
        # Foydalanuvchiga tegishli bo'lmagan id-larni bloklash
        user = self.context['request'].user
        invalid_ids = WorkerImage.objects.filter(id__in=image_ids).exclude(user=user).values_list('id', flat=True)
        if invalid_ids:
            raise serializers.ValidationError(
                f"Quyidagi rasmlar id-lari sizga tegishli emas: {list(invalid_ids)}"
            )
        return image_ids

    def delete_images(self, user, image_ids):
        # Ruxsat bo'lgan rasmlarni o'chirish
        WorkerImage.objects.filter(id__in=image_ids, user=user).delete()
        return image_ids


class WorkerActiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = AbstractUser
        fields = ['id', 'is_worker_active', ]

class WorkerLocationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['point']

    def validate(self, attrs):
        if self.instance.role != "worker":
            raise serializers.ValidationError("Only workers can update location.")
        return attrs
