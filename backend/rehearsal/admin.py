from django.contrib import admin

from .models import Persona, RehearsalFeedback, RehearsalMessage, RehearsalSession

admin.site.register(Persona)
admin.site.register(RehearsalSession)
admin.site.register(RehearsalMessage)
admin.site.register(RehearsalFeedback)
