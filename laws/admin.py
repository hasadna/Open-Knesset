from models import Vote, Law, PrivateProposal, KnessetProposal, GovProposal, Bill, GovLegislationCommitteeDecision

from django.contrib import admin


class VoteAdmin(admin.ModelAdmin):
    #    filter_horizontal = ('voted_for','voted_against','voted_abstain','didnt_vote')
    list_display = (
    '__unicode__', 'short_summary', 'full_text_link', 'for_votes_count', 'against_votes_count', 'abstain_votes_count')


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


class BillAdmin(admin.ModelAdmin):
    pass


admin.site.register(Bill, BillAdmin)


class GovLegislationCommitteeDecisionAdmin(admin.ModelAdmin):
    pass


admin.site.register(GovLegislationCommitteeDecision, GovLegislationCommitteeDecisionAdmin)
