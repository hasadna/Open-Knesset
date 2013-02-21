# encoding: utf-8

from django.core.management.base import NoArgsCommand
from optparse import make_option
from plenum.management.commands.parse_plenum_protocols_subcommands.download import Download
from plenum.management.commands.parse_plenum_protocols_subcommands.parse import Parse

class Command(NoArgsCommand):

    option_list = NoArgsCommand.option_list + (
        make_option('--download',action='store_true',dest='download',
            help="download the latest protocols from the knesset, convert them to xml and store in db"),
        make_option('--parse',action='store_true',dest='parse',
            help="parse the xmls from the download stage and store in db"),
        make_option('--redownload',action='store_true',dest='redownload',
            help="like the download stage but download all the files again"),
        make_option('--reparse',action='store_true',dest='reparse',
            help="like the parse stage but parses all the existing data again"),
    )

    def handle_noargs(self, **options):
        didSomething=False
        if options.get('download',False) or options.get('redownload',False):
            Download(options.get('verbosity',1),options.get('redownload',False))
            didSomething=True
        if options.get('parse',False) or options.get('reparse',False):
            Parse(options.get('verbosity',1),options.get('reparse',False))
            didSomething=True
        if not didSomething==True:
            print 'invalid options, try --help for help'
