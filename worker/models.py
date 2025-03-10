from django.db import models
from rest_framework.exceptions import ValidationError
from django.contrib.auth import get_user_model

User = get_user_model()

# worker profilidagi inline bo'lgan image lar uchun model
class WorkerImage(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='profileimage',
        blank=True,
        null=True
    )
    image = models.ImageField(upload_to='wor_image/', blank=True, null=True)

    def __str__(self):
        return f"{self.user.full_name}'s image"

    def save(self, *args, **kwargs):
        # Check if the user has 5 images already
        if self.user.profileimage.count() >= 5:
            raise ValidationError("Profilda 5 tadan ortiq rasm boʻlishi mumkin emas.")
        super().save(*args, **kwargs)


# workerlar profilidagi nesw uchun model
class WorkerNews(models.Model):
    description = models.TextField()
    image = models.ImageField(upload_to='workernews_images/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
