from models import Vote, Law, PrivateProposal, KnessetProposal, GovProposal, Bill, GovLegislationCommitteeDecision
from laws.management.commands.scrape_votes import Command as ScrapeVotesCommand
from django.utils.translation import ugettext_lazy as _
from django.contrib import admin


class VoteAdmin(admin.ModelAdmin):
    #    filter_horizontal = ('voted_for','voted_against','voted_abstain','didnt_vote')
    list_display = (
        '__unicode__', 'short_summary', 'full_text_link', 'votes_count', 'for_votes_count', 'against_votes_count',
        'abstain_votes_count')

    search_fields = ('title', 'summary', 'full_text', 'id', 'src_id')

    def update_vote(self, request, queryset):
        vote_count = queryset.count()
        for vote in queryset:
            vote.update_vote_properties()

        self.message_user(request, "successfully updated {0} votes".format(vote_count))

    update_vote.short_description = 'update vote properties and calculations'

    def recreate_vote(self, request, queryset):
        recreated_votes = ScrapeVotesCommand().recreate_objects(queryset.values_list('pk', flat=True))
        self.message_user(request, "successfully recreated {0} votes".format(len(recreated_votes), ', '.join([str(v.pk) for v in recreated_votes])))

    recreate_vote.short_description = "recreate vote by deleting and then getting fresh data from knesset api"

    actions = ['update_vote', 'recreate_vote']


admin.site.register(Vote, VoteAdmin)


class LawAdmin(admin.ModelAdmin):
    pass


admin.site.register(Law, LawAdmin)


class PrivateProposalAdmin(admin.ModelAdmin):
    pass


admin.site.register(PrivateProposal, PrivateProposalAdmin)


class KnessetProposalAdmin(admin.ModelAdmin):
    pass


admin.site.register(KnessetProposal, KnessetProposalAdmin)


class GovProposalAdmin(admin.ModelAdmin):
    pass


admin.site.register(GovProposal, GovProposalAdmin)


class MissingLawListFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _('Missing Laws')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'is_missing_law'

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        return (
            ('missing_law', _('Has Missing Law')),
            # ('90s', _('in the nineties')),
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        # Compare the requested value (either '80s' or '90s')
        # to decide how to filter the queryset.
        if self.value() == 'missing_law':
            return queryset.filter(law=None)
        else:
            return queryset


class BillAdmin(admin.ModelAdmin):
    list_display = ('law', 'title', 'stage')
    search_fields = ('title',)
    list_filter = ('stage', MissingLawListFilter)


admin.site.register(Bill, BillAdmin)


class GovLegislationCommitteeDecisionAdmin(admin.ModelAdmin):
    pass


admin.site.register(GovLegislationCommitteeDecision, GovLegislationCommitteeDecisionAdmin)
