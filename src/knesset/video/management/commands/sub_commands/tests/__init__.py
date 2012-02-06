#encoding: utf-8

from knesset.video.management.commands.sub_commands.tests.UpdateMembersAboutVideo import testUpdateMembersAboutVideo
from knesset.video.management.commands.sub_commands.tests.UpdateMembersRelatedVideos import testUpdateMembersRelatedVideos
from knesset.video.management.commands.sub_commands.tests.UpdateCommitteesVideos import testUpdateCommitteesVideos
from knesset.video.management.commands.sub_commands.tests.AddVideo import testAddVideo
from knesset.video.management.commands.sub_commands.tests.DownloadCommitteesVideos import testDownloadCommitteesVideos
from knesset.video.management.commands.sub_commands.tests.UploadCommitteesVideos import testUploadCommitteesVideos
from django.test import TestCase
from knesset.video.management.commands.sub_commands import (
    SubCommand, SubCommandErrorException, Timer,
    Logger, TimeoutException
)
import time
from StringIO import StringIO

class testLogger(TestCase):
    
    def _runLogs(self,logger):
        logger.log('debug','debug')
        logger.log('info','info')
        logger.log('warn','warn')
        logger.log('error','error')
    
    def test(self):
        strio=StringIO()
        logger=Logger(out=strio)
        self._runLogs(logger)
        self.assertEquals(strio.getvalue(),'info\r\nwarn\r\nerror\r\n')
        strio=StringIO()
        logger=Logger(verbosity=0,out=strio)
        self._runLogs(logger)
        self.assertEqual(strio.getvalue(),'warn\r\nerror\r\n')
        strio=StringIO()
        logger=Logger(verbosity=2,out=strio)
        self._runLogs(logger)
        self.assertEqual(strio.getvalue(),'debug\r\ninfo\r\nwarn\r\nerror\r\n')
     
class testTimer(TestCase):
    
    def testElapsed(self):
        start=time.time()
        timer=Timer()
        self.assertEqual(round(timer.elapsed,2),round(time.time()-start,2))
        time.sleep(1)
        self.assertEqual(round(timer.elapsed,2),round(time.time()-start,2))
        
    def testRemaining(self):
        start=time.time()
        limit=5
        timer=Timer(limit=limit)
        self.assertEqual(round(timer.remaining,2),round(limit-time.time()+start,2))
        time.sleep(1)
        self.assertEqual(round(timer.remaining,2),round(limit-time.time()+start,2))
        
    def testCheck(self):
        timer=Timer(limit=2)
        timer.check()
        time.sleep(1)
        timer.check()
        time.sleep(1)
        ok=False
        try:
            timer.check()
        except TimeoutException:
            ok=True
        self.assertTrue(ok)

class testSubCommand(TestCase):

    def test(self):
        class MySubCommand(SubCommand):
            def __init__(self,command,test):
                SubCommand.__init__(self,command)
                test.assertEquals(self._get_data_root(),'the data root')
                test.assertEquals(self._get_opt('opt name'),'opt value')
                ok=False
                try:
                    self._check_timer()
                except MyTimerException:
                    ok=True
                test.assertTrue(ok)
                test.assertEqual(self._timer_remaining(),92837745)
                self._debug('debug')
                self._info('info')
                self._warn('warn')
                ok=False
                try:
                    self._error('error')
                except SubCommandErrorException:
                    ok=True
                test.assertTrue(ok)
                self._error('error no ecception',no_exception=True)
                test.assertEqual(self.command.logger._log,[
                    ('debug', 'debug'),
                    ('info', 'info'), 
                    ('warn', 'warn'), 
                    ('error', 'error'), 
                    ('error', 'error no ecception')
                ])
        class MyTimerException:
            pass
        class MyTimer:
            remaining=92837745
            def check(self):
                raise MyTimerException
        class MyLogger:
            _log=[]
            def log(self,msgtype,msg):
                self._log.append((msgtype,msg))
        class MyCommand:
            DATA_ROOT='the data root'
            _opts={'opt name':'opt value'}
            timer=MyTimer()
            logger=MyLogger()
            pass
        command=MyCommand()
        MySubCommand(command,self)
