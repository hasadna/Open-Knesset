# -*- coding: utf-8 -*-

from django.contrib import admin
from tagging.models import TaggedItem

from .models import Tidbit, TagSuggestion, TagSynonym, TagKeyphrase, Tag
from auxiliary.tag_suggestions import approve as tag_suggestions_approve
from tagging.admin import TagAdmin as OriginalTagAdmin
from tagging.forms import TagAdminForm as OriginalTagAdminForm
from django.contrib.admin import SimpleListFilter
from django.utils.translation import ugettext_lazy as _
from django.utils.html import escape, escapejs
from django.contrib.flatpages.admin import FlatPage, FlatPageAdmin as DjangoFlatPageAdmin


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


class TagSynonymAdmin(admin.ModelAdmin):
    model = TagSynonym
    list_display = ('tag', 'synonym_tag')
    raw_id_fields = ('tag', 'synonym_tag')
    ordering = ('tag', 'synonym_tag')


admin.site.register(TagSynonym, TagSynonymAdmin)


class TagKeyphraseAdmin(admin.ModelAdmin):
    model = TagKeyphrase


admin.site.register(TagKeyphrase, TagKeyphraseAdmin)


class TagSynonymInline(admin.TabularInline):
    model = TagSynonym
    fk_name = 'tag'


class TagTagSynonymListFilter(SimpleListFilter):
    title = _('Tag Synonym')
    parameter_name = 'synonyms'

    def lookups(self, request, model_admin):
        return (
            ('parents', _('parent tags'),),
            ('synonyms', _('synonym tags'),),
            ('parentswithsynonyms', _('parent tags with synonyms')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'parents':
            return queryset.filter(synonym_synonym_tag=None)
        elif self.value() == 'synonyms':
            return queryset.exclude(synonym_synonym_tag=None)
        elif self.value() == 'parentswithsynonyms':
            return queryset.filter(synonym_synonym_tag=None).exclude(synonym_proper_tag=None)
        else:
            return queryset


class TaggedItemAdmin(admin.ModelAdmin):
    model = TaggedItem
    list_display = ('tag', 'object')
    list_filter = ('content_type',)


admin.site.unregister(TaggedItem)
admin.site.register(TaggedItem, TaggedItemAdmin)


class TagAdmin(admin.ModelAdmin):
    model = Tag
    inlines = (TagSynonymInline,)
    list_filter = (TagTagSynonymListFilter,)
    list_display = ('name', 'synonyms',)

    def synonyms(self, tag):
        synonyms = []
        if tag.synonym_synonym_tag.count() == 0:
            #  parent tag
            synonyms = [escape(synonym) for synonym in
                        tag.synonym_proper_tag.values_list('synonym_tag__name', flat=True)]
        synonyms.append(
            u'<span class="tag_synonym_msg"></span><a href="javascript:tag_admin.tag_synonym_click(%s, \'%s\');" class="tag_synonym_action">( הוספת תג נרדף )</a><a href="javascript:tag_admin.tag_synonym_secondary_click(%s);" class="tag_synonym_secondary_action"></a>' % (
                tag.pk, escapejs(tag), tag.pk,))
        return ', '.join(synonyms)

    synonyms.allow_tags = True

    class Media:
        js = ('js/admin/tag_admin.js',)


admin.site.unregister(Tag)
admin.site.register(Tag, TagAdmin)


class FlatPageAdmin(DjangoFlatPageAdmin):
    def save_model(self, request, obj, form, change):
        super(FlatPageAdmin, self).save_model(request, obj, form, change)
        from django.core.cache import cache
        cache.delete('flatpage_block_%s' % obj.url)


admin.site.unregister(FlatPage)
admin.site.register(FlatPage, FlatPageAdmin)
