from django import forms
from django.forms.models import modelformset_factory

from models import Topic
from links.models import Link


class EditTopicForm(forms.ModelForm):
    class Meta:
        model = Topic
        fields = ('title', 'description', 'committees')


LinksFormset = modelformset_factory(Link,
                                    can_delete=True,
                                    fields=('url', 'title'),
                                    extra=3)
