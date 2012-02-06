# encoding: utf-8

import os
from django.conf import settings
from django.core.management.base import NoArgsCommand
from optparse import make_option
from sub_commands import SubCommand, Timer, Logger, TimeoutException, SubCommandErrorException
from knesset.video.management.commands.sub_commands.UpdateMembersAboutVideo import UpdateMembersAboutVideo
from knesset.video.management.commands.sub_commands.UpdateMembersRelatedVideos import UpdateMembersRelatedVideos
from knesset.video.management.commands.sub_commands.UpdateCommitteesVideos import UpdateCommitteesVideos
from knesset.video.management.commands.sub_commands.DownloadCommitteesVideos import DownloadCommitteesVideos
from knesset.video.management.commands.sub_commands.UploadCommitteesVideos import UploadCommitteesVideos
from knesset.video.management.commands.sub_commands.GetYoutubeToken import GetYoutubeToken

class Command(NoArgsCommand,SubCommand):

    def __init__(self):
        NoArgsCommand.__init__(self)
        SubCommand.__init__(self,self)

    DATA_ROOT = getattr(settings, 'DATA_ROOT',
                        os.path.join(settings.PROJECT_ROOT, os.path.pardir, os.path.pardir, 'data'))

    option_list = NoArgsCommand.option_list + (
        make_option('--all', action='store_true', dest='all',
            help="runs all the update_videos processes."),
        make_option('--download', action='store_true', dest='download',
            help="download video data (large files)"),
        make_option('--upload', action='store_true', dest='upload',
            help="uploads downloaded video data to cdn (youtube)."),
        make_option('--update', action='store_true', dest='update',
            help="update video metadata"),
        make_option('--with-history', action='store_true', dest='with-history',
            help="download historical data (only relevant with --download options)"),
        make_option('--time-limit', action='store', type='int', dest='time-limit',
            help='limit the process time (in minutes)'),
        make_option('--only-members', action='store_true', dest='only-members',
            help='only run sub commands related to members'),
        make_option('--only-committees', action='store_true', dest='only-committees',
            help='only run sub commands related to committees'),
        make_option('--committee-id', action='store', type='int', dest='committee-id',
            help='only update the given committee id'),
        make_option('--download-mb-quota', action='store', type='int', dest='download-mb-quota',
            help='limit the total amount of data stored (in mb)'),
        make_option('--get-youtube-token', action='store_true', dest='get-youtube-token',
            help='get a youtube authsub token'),
    )

    def _set_opts(self,options):
        self._opts={
            'all':options.get('all', False),
            'download':options.get('download', False),
            'upload':options.get('upload', False),
            'update':options.get('update', False),
            'with-history':options.get('with-history', False),
            'only-members':options.get('only-members', False),
            'only-committees':options.get('only-committees', False),
            'committee-id':options.get('committee-id', None),
            'download-mb-quota':options.get('download-mb-quota',None),
            'get-youtube-token':options.get('get-youtube-token',False),
        }
        
    def _init_opts(self):
        if self._opts['all']:
            self._opts['update']=True
            self._opts['download']=True
            self._opts['upload']=True
        if (all([
            not(self._opts['all']),
            not(self._opts['update']),
            not(self._opts['download']),
            not(self._opts['upload']),
            not(self._opts['get-youtube-token']),
        ])):
            self._warn("no arguments found. Running update phase. try -h for help.")
            self._opts['update']=True
        if (
            self._opts['get-youtube-token']
            and (
                self._opts['update']
                or self._opts['download']
                or self._opts['upload']
            )
        ):
            self._warn('only get youtube token action will be performed')
            self._opts['update']=False
            self._opts['download']=False
            self._opts['upload']=False

    def _init_subCommand(self,options):
        if options.get('time-limit', None) is None:
            self.timer=Timer()
        else:
            self.timer=Timer(options.get('time-limit', None)*60)
        self.logger=Logger(options.get('verbosity',1))

    def _run_subCommands(self):        
        if self._opts['download']:
            self._info("beginning download phase")
            DownloadCommitteesVideos(self,mb_quota=self._opts['download-mb-quota'])
            self._check_timer()
        
        if self._opts['upload']:
            print "beginning upload phase"
            UploadCommitteesVideos(self)
            self._check_timer()
            
        if self._opts['update']:
            self._info("beginning update phase")
            if not self._opts['only-committees']:
                self._check_timer()
                UpdateMembersAboutVideo(self)
                self._check_timer()
                UpdateMembersRelatedVideos(self)
            if not self._opts['only-members']:
                self._check_timer()
                UpdateCommitteesVideos(self)
                
        if self._opts['get-youtube-token']:
            self._info('getting youtube token')
            GetYoutubeToken(self)

    def handle_noargs(self, **options):
        self._init_subCommand(options)
        self._set_opts(options)
        self._init_opts()
        try:
            self._run_subCommands()
        except TimeoutException:
            self._error("reached the time limit, stopped",no_exception=True)
        except SubCommandErrorException:
            pass
