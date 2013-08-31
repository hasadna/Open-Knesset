from django import forms
from django.contrib.auth.models import User, Group
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import ugettext_lazy as _
from mks.models import Party
from models import NOTIFICATION_PERIOD_CHOICES
from persons.models import GENDER_CHOICES

class RegistrationForm(UserCreationForm):
    username = forms.RegexField(label=_("Username"), max_length=30, regex=r'^(?u)[ \w.@+-]{4,}$',
        help_text = _("Required. 4-30 characters (only letters, numbers spaces and @/./+/-/_ characters)."),
        error_message = _("Required. 4-30 characters (only letters, numbers spaces and @/./+/-/_ characters)."))

    email_notification = forms.ChoiceField(choices = NOTIFICATION_PERIOD_CHOICES, initial="W",
                                           label = _('E-Mail Notifications'),
                                           help_text = _('Should we send you e-mail notification about updates to things you follow on the site?'))
    party = forms.ModelChoiceField(Party.objects.all(),
                                   required = False,
                                   label = _('(citizen) party member?'),
                                   help_text = _('Are you a member of any party?'))
    class Meta:
        model = User
        fields = ('username', 'email')

    def save(self, commit=True):
        user = super(RegistrationForm, self).save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            profile = user.get_profile()
            profile.email_notification = self.cleaned_data['email_notification']
            profile.party = self.cleaned_data['party']
            profile.save()
        return user

    def clean_email(self):
        "Can't use already existing emails for registration"

        email = self.cleaned_data['email']
        exists = User.objects.filter(email=email).count()

        if exists:
            raise forms.ValidationError(_('This email is already taken'))

        return email


class EditProfileForm(forms.Form):
    email = forms.EmailField(required=False ,label=_(u'email address'),
                             help_text = _("We don't spam, and don't show your email to anyone")
                             )
    username = forms.RegexField(label=_("Username"), max_length=30, regex=r'^(?u)[ \w.@+-]{4,}$',
        help_text = _("Required. 4-30 characters (only letters, numbers spaces and @/./+/-/_ characters)."),
        error_message = _("Required. 4-30 characters (only letters, numbers spaces and @/./+/-/_ characters)."))

    public_profile = forms.BooleanField(label=_('Public profile'),
                                        help_text = _('Allow other users to view your profile on the site'),
                                        required=False)
    gender = forms.ChoiceField(choices = GENDER_CHOICES,
                               label=_('Gender'))
    description = forms.CharField(required=False,
                                  label=_('Tell us and other users bit about yourself'),
                                  widget=forms.Textarea(attrs={'rows':3}))
    email_notification = forms.ChoiceField(choices = NOTIFICATION_PERIOD_CHOICES,
                                           label = _('E-Mail Notifications'),
                                           help_text = _('Should we send you e-mail notification about updates to things you follow on the site?'))
    party = forms.ModelChoiceField(Party.objects.all(),
                                   required = False,
                                   label = _('(citizen) party member?'),
                                   help_text = _('Are you a member of any party?'))

    def __init__(self, user=None, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)
        self.user = user
        self.userprofile = user.get_profile()
        if self.user:
            self.initial = {'username': user.username,
                        'first_name':user.first_name,
                        'last_name':user.last_name,
                        'email': user.email,
                        'public_profile': self.userprofile.public_profile,
                        'gender': self.userprofile.gender,
                        'description': self.userprofile.description,
                        'email_notification': self.userprofile.email_notification,
                        'party': self.userprofile.party,
                        }
        self.has_email = True if user.email else False
        g, created = Group.objects.get_or_create(name='Valid Email')
        self.valid_email = g in self.user.groups.all()

    def clean_username(self):
        data = self.cleaned_data['username']
        if data ==  self.user.username:
            return data
        try:
            User.objects.get(username = data)
            raise forms.ValidationError("This username is already taken.")
        except User.DoesNotExist:
            return data

    def clean(self):
        cleaned_data = self.cleaned_data
        return cleaned_data

    def save(self, commit = True):
        user = self.user
        if self.cleaned_data['email'] != None:
            if user.email != self.cleaned_data['email']: #email changed - user loses comment permissions, until he validates email again.
                g = Group.objects.get(name='Valid Email')
                user.groups.remove(g)

            user.email = self.cleaned_data['email']
        user.username = self.cleaned_data['username']
        self.userprofile.gender = self.cleaned_data['gender']
        self.userprofile.public_profile = self.cleaned_data['public_profile']
        self.userprofile.description = self.cleaned_data['description']
        self.userprofile.email_notification = self.cleaned_data['email_notification']
        self.userprofile.party = self.cleaned_data['party']

        if commit:
            user.save()
            self.userprofile.save()
        return user
