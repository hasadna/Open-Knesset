from django.contrib import admin
from events.models import Event


class EventAdmin(admin.ModelAdmin):
    pass    


admin.site.register(Event, EventAdmin)
