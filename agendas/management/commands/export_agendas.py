import os
import csv
from django.core.management.base import NoArgsCommand
from django.conf import settings

from mks.models import Member
from agendas.models import Agenda, AgendaVote


class Command(NoArgsCommand):

    def handle_noargs(self, **options):
        mks = Member.objects.exclude(current_party__isnull=True).order_by(
            'current_party').values('id', 'name', 'current_party')
        for agenda in Agenda.objects.all():
            with open(os.path.join(settings.DATA_ROOT, 'agenda_%d.csv' %
                                  agenda.id), 'wt') as f:
                csv_writer = csv.writer(f)
                header = ['Vote id',
                          'Vote title',
                          'Vote time',
                          'Score',
                          'Importance']
                for mk in mks:
                    header.append('%s %d' % (mk['name'].encode('utf8'), mk['id']))
                csv_writer.writerow(header)
    
                for agenda_vote in AgendaVote.objects.filter(
                        agenda=agenda).select_related('vote'):
                    row = [agenda_vote.vote.id,
                           agenda_vote.vote.title.encode('utf8'),
                           agenda_vote.vote.time.isoformat(),
                           agenda_vote.score,
                           agenda_vote.importance]
                    mks_for = agenda_vote.vote.get_voters_id('for')
                    mks_against = agenda_vote.vote.get_voters_id('against')
                    for mk in mks:
                        if mk['id'] in mks_for:
                            row.append(1)
                        elif mk['id'] in mks_against:
                            row.append(-1)
                        else:
                            row.append(0)
                    csv_writer.writerow(row)
