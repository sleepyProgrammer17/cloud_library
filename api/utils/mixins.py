# mixins.py

class LowercaseFieldsMixin:
    """
    Mixin to specify which fields should be lowercased before saving.
    Set `lowercase_fields` on the model class.
    """
    lowercase_fields = []

    def save(self, *args, **kwargs):
        for field in self.lowercase_fields:
            value = getattr(self, field, None)
            if value and isinstance(value, str):
                setattr(self, field, value.lower())
        super().save(*args, **kwargs)