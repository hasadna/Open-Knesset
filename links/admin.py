from django.contrib import admin
from models import Link, LinkType
from django.utils.translation import ugettext_lazy as _, ungettext

def make_active(modeladmin, request, queryset):
    queryset.update(active=True)
make_active.short_description = "Mark selected links as active"

def make_inactive(modeladmin, request, queryset):
    queryset.update(active=False)
make_inactive.short_description = "Mark selected links as inactive"

class LinkTypesAdmin(admin.ModelAdmin):
    pass

class LinksAdmin(admin.ModelAdmin):
    fieldsets = (
        (None,
           {'fields': ('content_type', 'object_pk')}
        ),
        (_('Content'),
           {'fields': ('url', 'title', 'link_type', 'active') }
        ),
     )

    list_display = ('title', 'link_type', 'content_type', 'object_pk')
    search_fields = ('title',)
    list_filter = ('link_type','active' )
    actions = [make_active, make_inactive ]


admin.site.register(Link, LinksAdmin)
admin.site.register(LinkType, LinkTypesAdmin)
