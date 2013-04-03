from django import forms
from django.forms.models import modelformset_factory

from models import Event
from links.models import Link

class EditEventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ('when','what','why')

# TODO: add it to the form
LinksFormset = modelformset_factory(Link,
                                    can_delete=True,
                                    fields=('url', 'title'),
                                    extra=3)

