# encoding: utf-8

import time, sys

class TimeoutException:
    pass
    
class SubCommandErrorException:
    
    def __init__(self,msg):
        self._msg=msg
        
    def __str__(self):
        return str(self._msg)

class Logger:
    def __init__(self,verbosity=1,out=sys.stdout):
        self._verbosity=int(verbosity)
        self._out=out
    
    def log(self,msgtype,msg):
        if (
            self._verbosity>=2 or msgtype in ['warn','error']
            or (self._verbosity==1 and msgtype != 'debug') 
        ):
            self._out.write(msg)
            self._out.write("\r\n")

class Timer:
    
    def __init__(self,limit=None):
        self._start=time.time()
        self._limit=limit
        
    def check(self):
        if self.remaining<=0:
            raise TimeoutException()

    @property
    def elapsed(self):
        return time.time()-self._start

    @property
    def remaining(self):
        if self._limit is not None:
            ans=self._limit-self.elapsed
            return 0 if ans<0 else ans
        else:
            return 60*24*365

class SubCommand:
    
    def __init__(self,command):
        self.command=command
    
    def _get_data_root(self):
        return self.command.DATA_ROOT
    
    def _get_opt(self,opt):
        return self.command._opts[opt]
        
    def _check_timer(self):
        if self.command.timer is not None:
            self.command.timer.check()

    def _timer_remaining(self):
        return self.command.timer.remaining
    
    def _debug(self,msg):
        self._log('debug',msg)
    
    def _info(self,msg):
        self._log('info',msg)
        
    def _warn(self,msg):
        self._log('warn',msg)
        
    def _error(self,msg,no_exception=False):
        self._log('error',msg)
        if not no_exception:
            raise SubCommandErrorException(msg)
    
    def _log(self,msgtype,msg):
        self.command.logger.log(msgtype,msg)

