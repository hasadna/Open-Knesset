from __future__ import division

from django.core.management.base import NoArgsCommand
from django.db import transaction

from agendas.models import SummaryAgenda,AgendaVote

class Command(NoArgsCommand):

    @transaction.commit_manually
    def handle_noargs(self, **options):
        print('Deleting existing summary objects')
        SummaryAgenda.objects.all().delete()
        numAgendaVotes = AgendaVote.objects.count()
        print('Summary agenda objects deleted, recalculating for %d votes' % \
                    numAgendaVotes)
        try:
            AgendaVote.objects.compute_all()
        except Exception as e:
            transaction.rollback()
            print(e)
            print('Failed to recompute transaction, no worries I rolled back')
        else:
            transaction.commit()
            print('Completed recalculation of agenda votes')
