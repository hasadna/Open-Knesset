from django import forms
from django.forms import ModelForm
from django.forms.formsets import formset_factory
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from models import Agenda, AgendaVote, AgendaBill, AgendaMeeting, AGENDAVOTE_SCORE_CHOICES, IMPORTANCE_CHOICES

class H4(forms.Widget):
    """ used to display header fields """
    input_type = None # Subclasses must define this.

    def render(self, name, value, attrs=None):
        return mark_safe(u'<h4>{}</h4>'.format(value))

def _get_field_form_param(label, **kwargs):
    error_messages = {'required': _('Please enter an agenda name')}
    for length, should in [('min_length','longer'), ('max_length', 'shorter')]:
        num = kwargs.get(length)
        if num:
            error_messages[length] = _('{} must be {} than {} characters'.format(label, should, num))
    kwargs['label'] = _(label)
    return kwargs

_name_field_form_params = _get_field_form_param(u'Agenda name', max_length=300)
_description_field_form_params = _get_field_form_param(u'Agenda description', min_length=15, widget=forms.Textarea)
_public_owner_name_field_form_param = _get_field_form_param(u'Public owner name', max_length=100)

class EditAgendaForm(forms.Form):
    name = forms.CharField(**_name_field_form_params)
    public_owner_name = forms.CharField(**_public_owner_name_field_form_param)
    description = forms.CharField(**_description_field_form_params)

    def __init__(self, agenda=None, *args, **kwargs):
        super(EditAgendaForm, self).__init__(*args, **kwargs)
        self.agenda = agenda
        if agenda is not None:
            self.initial = {'name': agenda.name,
                            'public_owner_name': agenda.public_owner_name,
                            'description': agenda.description,
                            }

class AddAgendaForm(ModelForm):
    # to have the same names and help texts as the edit form, we need to override the form fields definitions:
    name = forms.CharField(**_name_field_form_params)
    public_owner_name = forms.CharField(**_public_owner_name_field_form_param)
    description = forms.CharField(**_description_field_form_params)

    class Meta:
        model = Agenda
        fields = ('name', 'public_owner_name', 'description')
        
class AbstractLinkingForm(forms.Form):
    # a form to help agendas' editors tie things to agendas
    agenda_name = forms.CharField(widget=H4, required=False, label='')
    obj_id = forms.IntegerField(widget=forms.HiddenInput)
    agenda_id = forms.IntegerField(widget=forms.HiddenInput)
    reasoning = forms.CharField(required=False, max_length=1000,
                           label=_(u'Reasoning'),
                           widget = forms.Textarea(attrs={'cols':30, 'rows':5}),
                           )
    object_type = forms.CharField(widget=forms.HiddenInput)

    #todo: memoize
    @classmethod
    def get_formset(cls):
        return formset_factory(cls, extra=0, can_delete=True)
    
class MeetingLinkingForm(AbstractLinkingForm):
    # a form to help agendas' editors tie meetings to agendas
    weight = forms.TypedChoiceField(label=_('Importance'),
                                    choices=IMPORTANCE_CHOICES,
                                    required=False,
                                    widget=forms.Select)

    def clean_weight(self):
        data = self.cleaned_data['weight']
        if not data:
            return 99
        return data

    def clean(self):
        cleaned_data = self.cleaned_data
        if cleaned_data.get('weight') == 99:
            cleaned_data["DELETE"] = 'on'
        return cleaned_data
    
    @staticmethod
    def linked_to():
        return AgendaMeeting

    @classmethod
    def detailname(cls):
        return 'committee-meeting'

class AbstractImportantLinkingForm(AbstractLinkingForm):
    weight = forms.TypedChoiceField(label=_('Position'), choices=AGENDAVOTE_SCORE_CHOICES,
             required=False, widget=forms.Select)
    importance = forms.TypedChoiceField(label=_('Importance'),
                                        choices=IMPORTANCE_CHOICES,
                                        required=False,
                                        widget=forms.Select)

    def clean_weight(self):
        data = self.cleaned_data['weight']
        if not data:
            return 99
        return data

    def clean(self):
        cleaned_data = self.cleaned_data
        if cleaned_data.get('weight') == 99:
            cleaned_data["DELETE"] = 'on'
        return cleaned_data

    @classmethod
    def detailname(cls):
        return '{}-detail'.format(cls.linked_to().keyname())

class VoteLinkingForm(AbstractImportantLinkingForm):
    @staticmethod
    def linked_to():
        return AgendaVote

class BillLinkingForm(AbstractImportantLinkingForm):
    @staticmethod
    def linked_to():
        return AgendaBill
    
# VoteLinkingFormSet =    formset_factory(VoteLinkingForm,    extra=0, can_delete=True)
# BillLinkingFormSet =    formset_factory(BillLinkingForm,    extra=0, can_delete=True)
# MeetingLinkingFormSet = formset_factory(MeetingLinkingForm, extra=0, can_delete=True)
