from modeltranslation.translator import TranslationOptions, register
from .models import Order, ClientNews


@register(Order)
class OrderTranslationOptions(TranslationOptions):
    fields = ('desc', 'full_desc',)


@register(ClientNews)
class ClientNewsTranslationOptions(TranslationOptions):
    fields = ('description',)
