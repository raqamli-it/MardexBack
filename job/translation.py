from modeltranslation.translator import TranslationOptions, register
from .models import CategoryJob, Job



@register(CategoryJob)
class CategoryJobTranslationOptions(TranslationOptions):
    fields = ('title',)


@register(Job)
class JobTranslationOptions(TranslationOptions):
    fields = ('title',)
