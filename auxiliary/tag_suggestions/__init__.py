from tagging.models import Tag, TaggedItem
from django.contrib.contenttypes.models import ContentType
from auxiliary.models import TagSuggestion
from django.db import IntegrityError

def approve(admin, request, tag_suggestions):
    for tag_suggestion in tag_suggestions:
        object = tag_suggestion.object
        try:
            tag = Tag.objects.create(name=tag_suggestion.name)
            TaggedItem.objects.create(tag=tag, object=object)
        except IntegrityError as e:
            if str(e) != 'column name is not unique':
                raise
        tag_suggestion.delete()
