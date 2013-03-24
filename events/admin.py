from django.contrib import admin
from events.models import Event


class EventAdmin(admin.ModelAdmin):

    list_display = ('when', 'what',)
    date_hierarchy = 'when'

admin.site.register(Event, EventAdmin, )
