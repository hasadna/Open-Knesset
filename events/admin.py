from django import forms
from django.contrib import admin
from django.forms.models import modelformset_factory
from django.forms.models import inlineformset_factory
from django.contrib.contenttypes import generic

from models import Event
from links.models import Link

class EventLinksInline(generic.GenericTabularInline):
    model = Link
    ct_fk_field = 'object_pk'
    extra = 1

class EventAdmin(admin.ModelAdmin):
    ordering = ('when',)
    list_display = ('when','what', 'where')
    inlines = (EventLinksInline,)
admin.site.register(Event, EventAdmin)
