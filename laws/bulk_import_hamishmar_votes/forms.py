from django import forms
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.utils.safestring import mark_safe


class BulkImportHamishmarVotesForm(forms.Form):
    file = forms.FileField(required=True, help_text=mark_safe('<div>Hamishmar Votes CSV file, see <a href="%s">example file</a> for reference</div>'%static('data/hamishmar_votes_data.csv')))
