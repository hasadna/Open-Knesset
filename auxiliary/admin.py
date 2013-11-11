from django.contrib import admin

from .models import Tidbit, TagSuggestion, Tag
from auxiliary.tag_suggestions import approve as tag_suggestions_approve

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
