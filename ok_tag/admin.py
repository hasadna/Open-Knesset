# -*- coding: utf-8 -*-

from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.utils.html import escape, escapejs
from django.utils.translation import ugettext_lazy as _
from tagging.models import TaggedItem, Tag

from auxiliary.models import TagSynonym, TagKeyphrase


class TagSynonymAdmin(admin.ModelAdmin):
    model = TagSynonym
    list_display = ('tag', 'synonym_tag')
    raw_id_fields = ('tag', 'synonym_tag')
    ordering = ('tag', 'synonym_tag')


class TagKeyphraseAdmin(admin.ModelAdmin):
    model = TagKeyphrase


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


admin.site.register(TagSynonym, TagSynonymAdmin)

admin.site.register(TagKeyphrase, TagKeyphraseAdmin)

admin.site.unregister(TaggedItem)
admin.site.register(TaggedItem, TaggedItemAdmin)

admin.site.unregister(Tag)
admin.site.register(Tag, TagAdmin)
