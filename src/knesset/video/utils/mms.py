import sys
from libmimms import libmms,core as mimms

class _options():
    def __init__(self,url,filename,time_limit,resume=False):
        self.time=time_limit
        self.bandwidth=1e6
        self.url=url
        self.filename=filename
        self.quiet=True
        self.resume=True
        self.clobber=False

def get_size(url):
    stream=libmms.Stream(url, 1e6)
    return stream.length()
    
def download(url,filename,time_limit):
    isDone=False
    try:
        mimms.download(_options(url,filename,time_limit))
        isDone=True
    except mimms.Timeout: pass
    except KeyboardInterrupt: pass 
    return isDone
    
def resume_download(url,filename,time_limit):
    isDone=False
    try:
        mimms.download(_options(url,filename,time_limit))
        isDone=True
    except mimms.Timeout: pass
    except KeyboardInterrupt: pass
    return isDone

