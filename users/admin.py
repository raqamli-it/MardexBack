from django.contrib import admin

from users.models import Payment, UserCard


# from users.models import AbstractUser
#
# admin.site.register(AbstractUser)


# USER CARD ADMIN
@admin.register(UserCard)
class UserCardAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "show_pan", "status", "transaction_id", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("user__username", "transaction_id")
    readonly_fields = ("card_id", "transaction_id", "created_at")

    # PAN ni decrypt qilib ko‘rsatish
    def show_pan(self, obj):
        try:
            return obj.get_decrypted_data().get("pan")
        except:
            return "Decrypt error"

    show_pan.short_description = "Card PAN"

    fieldsets = (
        ("User", {
            "fields": ("user",)
        }),
        ("Transaction info", {
            "fields": ("transaction_id", "status", "created_at"),
        }),
        ("Card info (decrypted ko‘rinmaydi)", {
            "fields": ("card_id", "pan", "expiry", "card_holder", "phone", "card_token"),
        }),
    )


# PAYMENT ADMIN
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "amount", "status", "transaction_id")
    list_filter = ("status", "amount")
    search_fields = ("user__username", "transaction_id")

    readonly_fields = ("transaction_id",)

    fieldsets = (
        ("User", {
            "fields": ("user",)
        }),
        ("Transaction data", {
            "fields": ("transaction_id", "amount", "status"),
        }),
        ("Sensitive fields (encrypted)", {
            "fields": ("account", "store_id", "terminal_id"),
        }),
    )
