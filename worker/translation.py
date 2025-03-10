from modeltranslation.translator import TranslationOptions, register
from .models import WorkerNews
from django.contrib.auth import get_user_model

User = get_user_model()


@register(User)
class WorkerProfileTranslationOptions(TranslationOptions):
    fields = ('full_name', 'description')


@register(WorkerNews)
class WorkerNewsTranslationOptions(TranslationOptions):
    fields = ('description',)
