from django import forms
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from datetime import date
from tagging.models import Tag
from models import (Vote, Bill, KnessetProposal, BillBudgetEstimation,
                    CONVERT_TO_DISCUSSION_HEADERS)
from vote_choices import (ORDER_CHOICES, TAGGED_CHOICES, TYPE_CHOICES,
                          SIMPLE_TYPE_CHOICES, BILL_TAGGED_CHOICES,
                          BILL_STAGE_CHOICES, BILL_AGRR_STAGES)

STAGE_CHOICES = (
    ('all', _('All')),
)

LINK_ERRORS = {
    'DUP_FIRST': _('Bill already has a First Vote linked to it'),
    'DUP_APPROVE': _('Bill already has an Approval Vote linked to it'),
    'ALREADY_LINKED': _('Vote is already linked as Approval Vote of another bill'),
}


class AttachBillFromVoteForm(forms.Form):
    """Form for attaching a vote to a bill from the vote page."""

    vote_model = forms.ModelChoiceField(queryset=Vote.objects.all(),
                                        widget=forms.HiddenInput,
                                        required=True)

    vote_type = forms.ChoiceField(label=_('Vote Type'),
                                  choices=SIMPLE_TYPE_CHOICES,
                                  required=True)

    bill_model = forms.ModelChoiceField(label=_('Bill'),
                                        queryset=Bill.objects.all(),
                                        widget=forms.TextInput,
                                        required=True)

    def __init__(self, vote, *args, **kwargs):
        super(AttachBillFromVoteForm, self).__init__(*args, **kwargs)

        self.fields['vote_model'].initial = vote
        self.fields['vote_type'].initial = self.get_default_vote_type(vote)


    def clean(self):
        cleaned_data = super(AttachBillFromVoteForm, self).clean()
        vote_type = cleaned_data.get('vote_type')
        bill = cleaned_data.get('bill_model')

        if vote_type == 'first vote' and bill.first_vote is not None:
            raise forms.ValidationError(
                LINK_ERRORS['DUP_FIRST'],
                code="cannot-link")

        elif vote_type == 'approve vote':
            if bill.approval_vote is not None:
                raise forms.ValidationError(
                    LINK_ERRORS['DUP_APPROVE'],
                    code="cannot-link")

            vote = cleaned_data.get('vote_model')
            vote_already_linked = Bill.objects\
                .filter(approval_vote=vote).count() > 0

            if vote_already_linked:
                raise forms.ValidationError(
                    LINK_ERRORS['ALREADY_LINKED'],
                    code="cannot-link")

        return cleaned_data


    def get_default_vote_type(self, vote):
        for h in CONVERT_TO_DISCUSSION_HEADERS:
            if vote.title.find(h) >= 0:
                return 'pre vote'

        if vote.vote_type == 'law-approve':
            return 'approve vote'

        return None


class BudgetEstimateForm(forms.Form):
    """Form for submitting the budget estimation of a given bill, for a few
    types of budget."""

    be_one_time_gov = forms.IntegerField(label=_('One-time costs to government'), required=False)
    be_yearly_gov = forms.IntegerField(label=_('Yearly costs to government'), required=False)
    be_one_time_ext = forms.IntegerField(label=_('One-time costs to external bodies'), required=False)
    be_yearly_ext = forms.IntegerField(label=_('Yearly costs to external bodies'), required=False)
    be_summary = forms.CharField(label=_('Summary of the estimation'),widget=forms.Textarea,required=False)

    def __init__(self, bill, user, *args, **kwargs):
        super(BudgetEstimateForm, self).__init__(*args, **kwargs)

        if bill is not None and user is not None:
            try:
                be = BillBudgetEstimation.objects.get(bill=bill,estimator__username=str(user))
                self.fields['be_one_time_gov'].initial = be.one_time_gov
                self.fields['be_yearly_gov'].initial = be.yearly_gov
                self.fields['be_one_time_ext'].initial = be.one_time_ext
                self.fields['be_yearly_ext'].initial = be.yearly_ext
                self.fields['be_summary'].initial = be.summary
            except BillBudgetEstimation.DoesNotExist:
                pass
        #self.fields['tagged'].choices = new_choices


class VoteSelectForm(forms.Form):
    """Votes filtering form"""

    vtype = forms.ChoiceField(label=_('Vote types'),
                              choices=TYPE_CHOICES,
                              required=False,
                              initial='all')
    tagged = forms.ChoiceField(label=_('Tags'),
                               choices=TAGGED_CHOICES,
                               required=False,
                               initial='all')
    order = forms.ChoiceField(label=_('Order by'),
                              choices=ORDER_CHOICES,
                              required=False,
                              initial='time')
    from_date = forms.DateField(label=_('From date'),
                                required=False)
    to_date = forms.DateField(label=_('To date'),
                              required=False,
                              initial=date.today)
    exclude_user_agendas = forms.BooleanField(label=_('Exclude my agendas'),
                                              required=False,
                                              initial=False)
    exclude_ascribed = forms.BooleanField(
        label=_('Exclude votes ascribed to bills'),
        required=False,
        initial=False)

    def __init__(self, *args, **kwargs):
        super(VoteSelectForm, self).__init__(*args, **kwargs)

        tags = Tag.objects.usage_for_model(Vote)
        new_choices = list(TAGGED_CHOICES)
        new_choices.extend([(t.name, t.name) for t in tags])
        self.fields['tagged'].choices = new_choices


class BillSelectForm(forms.Form):
    """Bill filtering form"""

    stage = forms.ChoiceField(label=_('Bill Stage'), choices=BILL_STAGE_CHOICES,
            required=False, initial='all')
    bill_type = forms.ChoiceField(label=_('Bill type'), choices=(
        ('all', _('All')),
        ('knesset', _('Knesset Proposal')),
        ('government', _('Government Proposal')),
    ), required=False)
    tagged = forms.ChoiceField(label=_('Tags'), choices=BILL_TAGGED_CHOICES,
            required=False, initial='all')
    changed_after = forms.DateField(label=_('Stage Changed After:'), required=False,
            input_formats=["%d/%m/%Y", "%d/%m/%y"])
    changed_before = forms.DateField(label=_('Stage Chaged Before:'), required=False,
            input_formats=["%d/%m/%Y", "%d/%m/%y"])

    pp_id = forms.IntegerField(required=False,
                               label=_('Private proposal ID'))
    knesset_booklet = forms.IntegerField(required=False,
                                         label=_('Knesset booklet'))
    gov_booklet = forms.IntegerField(required=False,
                                     label=_('Government booklet'))

    # TODO: add more filter options:
    # order = forms.ChoiceField(label=_('Order by'), choices=ORDER_CHOICES,
    #         required=False, initial='time')
    # from_date = forms.DateField(label=_('From date'), required=False)
    # to_date = forms.DateField(label=_('To date'), required=False,
    #         initial=date.today)

    def __init__(self, *args, **kwargs):
        super(BillSelectForm, self).__init__(*args, **kwargs)

        tags = Tag.objects.usage_for_model(Bill)
        new_choices = list(BILL_TAGGED_CHOICES)
        new_choices.extend([(t.name, t.name) for t in tags])
        self.fields['tagged'].choices = new_choices

        new_stages = list(STAGE_CHOICES)
        new_stages.extend(BILL_STAGE_CHOICES)
        self.fields['stage'].choices = new_stages

    def clean(self):
        super(BillSelectForm, self).clean()

        #override stage error on aggregate stages (when accessing from mk page)
        if ((self.data.get('stage') in BILL_AGRR_STAGES) and
                ('stage' in self._errors)):
            del self._errors['stage']
            self.cleaned_data['stage'] = self.data.get('stage')

        return self.cleaned_data
