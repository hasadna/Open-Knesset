# Create your views here.
from django.views.generic import ListView
from django.utils.translation import ugettext as _
from hashnav.detail import DetailView
from agendas.models import Agenda
from polyorg.models import CandidateList, Candidate

class CandidateListListView(ListView):
    model = CandidateList

    def get_queryset(self):
        return self.model.objects.all().order_by('ballot')

class CandidateListDetailView(DetailView):
    model = CandidateList

    def get_context_data (self, **kwargs):
        context = super(CandidateListDetailView, self).get_context_data(**kwargs)
        cl = context['object']
        context['head'] = cl.getHeadName()
        context['candidates'] = Candidate.objects.filter(candidates_list=cl).order_by('ordinal')
        agendas = []
        if cl.member_ids:
            for a in Agenda.objects.filter(is_public=True).order_by('-num_followers'):
                agendas.append({'id': a.id, 
                                'name': a.name,
                                'url': a.get_absolute_url(),
                                'score': a.candidate_list_score(cl)})
            context['agendas'] = agendas
            context['stats'] = cl.voting_statistics
        return context
