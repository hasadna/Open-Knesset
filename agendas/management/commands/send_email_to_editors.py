from django.utils.translation import ugettext as _
from django.utils import translation
from django.core.management.base import NoArgsCommand
from django.conf import settings

from mailer import send_html_mail 
from agendas.models import UserSuggestedVote
from django.contrib.auth.models import User

class Command(NoArgsCommand):

    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'email@example.com')
    prefix = 'https://oknesset.org'
    lang = getattr(settings, 'LANGUAGE_CODE', 'he')

    def handle_noargs(self, **options):
        translation.activate(self.lang)
        for u in User.objects.filter(agendas__isnull=False).distinct().all():
            msg = ''
            html_msg = ''
            for a in u.agendas.all():
                for usv in UserSuggestedVote.objects.filter(
                                                    agenda=a,
                                                    sent_to_editor=False):
                    usv.sent_to_editor = True
                    usv.save()
                    msg += _('User %(user)s suggested vote %(vote)s to agenda '
                             '%(agenda)s with reasoning: %(reasoning)s') % {
                                        'user': usv.user.username,
                                        'vote': usv.vote,
                                        'agenda':a,
                                        'reasoning':usv.reasoning,
                             }
                    msg += '\n'
                    html_msg += _('User <a href="%(user_href)s">%(user)s</a> suggested vote '
                                  '<a href="%(vote_href)s">%(vote)s</a> to agenda '
                                  '<a href="%(agenda_href)s">%(agenda)s</a> '
                                  'with reasoning %(reasoning)s' ) % {
                                        'user_href':self.prefix+usv.user.get_absolute_url(),
                                        'user':usv.user.username,
                                        'vote_href':self.prefix+usv.vote.get_absolute_url(),
                                        'vote':usv.vote,
                                        'agenda_href':self.prefix+a.get_absolute_url(),
                                        'agenda':a,
                                        'reasoning': usv.reasoning,
                                    }
                    html_msg += '<br>'
            if msg:
                send_html_mail(_('Open Knesset Agenda Editor Update'),
                               msg,
                               html_msg,
                               self.from_email,
                               [u.email],
                              )
