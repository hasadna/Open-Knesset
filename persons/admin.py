from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from links.models import Link
from models import Person,PersonAlias,Title,Role

class RoleInline(admin.TabularInline):
    model = Role

def merge_persons(modeladmin, request, qs):
    pivot = None
    for person in qs:
        if person.mk:
            pivot = person
            break
    if not pivot:
        pivot = qs[0]

    for person in qs:
        if person != pivot:
            for role in person.roles.all():
                role.person = pivot
                role.save()
            for alias in person.aliases.all():
                alias.person = pivot
                alias.save()
            for pp in person.protocol_parts.all():
                pp.speaker = pivot
                pp.save()
            for link in Link.objects.for_model(person):
                link.content_object = pivot
                link.save()
            for field in person._meta.fields:
                if field in ['id']:
                    continue
                field_name = field.get_attname()
                val = getattr(person, field_name)
                if val and not getattr(pivot, field_name):
                    setattr(pivot, field_name, val)
            person.delete()
    pivot.save()
merge_persons.short_description = _("Merge two or more persons")

class PersonAdmin(admin.ModelAdmin):
    list_display=('name', 'mk', 'user')
    search_fields = ('name',)
    ordering = ('name',)
    inlines = [
        RoleInline,
    ]
    readonly_fields = ('calendar_sync_token',)
    actions = [merge_persons]

admin.site.register(Person, PersonAdmin)

class PersonAliasAdmin(admin.ModelAdmin):
    ordering = ('person',)
    list_display = ('person','name')
admin.site.register(PersonAlias, PersonAliasAdmin)

class TitleAdmin(admin.ModelAdmin):
    ordering = ('name',)
admin.site.register(Title, TitleAdmin)

class RoleAdmin(admin.ModelAdmin):
    ordering = ('person',)
    list_display = ('person','text')
admin.site.register(Role, RoleAdmin)

