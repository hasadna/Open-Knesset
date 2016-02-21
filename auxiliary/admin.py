# -*- coding: utf-8 -*-

from django.contrib import admin
from django.contrib.flatpages.admin import FlatPage, FlatPageAdmin as DjangoFlatPageAdmin

from auxiliary.tag_suggestions import approve as tag_suggestions_approve
from .models import Tidbit, TagSuggestion


class TidibitAdmin(admin.ModelAdmin):
    model = Tidbit
    list_display = ('title', 'content', 'ordering', 'is_active')
    list_display_links = ('title', 'content')
    list_editable = ('ordering', 'is_active')


class TagSuggestionAdmin(admin.ModelAdmin):
    model = TagSuggestion
    list_display = ('name', 'suggested_by', 'object')
    actions = [tag_suggestions_approve]


admin.site.register(Tidbit, TidibitAdmin)
admin.site.register(TagSuggestion, TagSuggestionAdmin)


class FlatPageAdmin(DjangoFlatPageAdmin):
    def save_model(self, request, obj, form, change):
        super(FlatPageAdmin, self).save_model(request, obj, form, change)
        from django.core.cache import cache
        cache.delete('flatpage_block_%s' % obj.url)


admin.site.unregister(FlatPage)
admin.site.register(FlatPage, FlatPageAdmin)
