from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Recipe


@receiver(post_save, sender=Recipe)
def set_short_link_code(sender, instance, created, **kwargs):
    """
    Сигнал для установки короткой ссылки при создании рецепта.
    """
    if created and not instance.short_link_code:
        instance.short_link_code = instance.generate_short_link_code()
        instance.save(update_fields=['short_link_code'])
