import logging
from optparse import make_option

from django.core.management.base import NoArgsCommand
from django.db.models import Max

from simple.management.commands import parse_laws
from laws.models import GovProposal

logger = logging.getLogger("open-knesset.parse_laws")


def scrape_gov_proposals(use_last_booklet, specific_booklet_to_use=None):
    booklet = 0

    if specific_booklet_to_use:
        booklet = specific_booklet_to_use

    elif use_last_booklet:
        booklet = GovProposal.objects.aggregate(Max('booklet_number')).values()[0]
    parser = parse_laws.ParseGovLaws(booklet)
    parser.parse_gov_laws()


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--forceupdate', action='store_true', dest='forceupdate',
                    help="forced update for gov bills, will download all pdfs and update Bills"),
        make_option('--pdf', action='store', dest='pdf', default=None,
                    help="Download and parse a specific bill"),
        make_option('--booklet', action='store', dest='booklet', default=None, type='int',
                    help="specific booklet to fetch, on min booklet depends on context")
    )

    help = "Give information on government bills (pdfs)"

    def handle_noargs(self, **options):
        forceupdate = options.get('forceupdate', False)
        pdf = options.get('pdf')
        booklet = options.get('booklet', None)
        if pdf:
            parse_laws.ParseGovLaws(min_booklet=0).update_single_bill(pdf, booklet=booklet)
            proposal_url_oknesset = GovProposal.objects.filter(source_url=pdf)[0].get_absolute_url()
            logger.info("updated: %s" % proposal_url_oknesset)
        else:
            scrape_gov_proposals(use_last_booklet=not forceupdate, specific_booklet_to_use=booklet)
