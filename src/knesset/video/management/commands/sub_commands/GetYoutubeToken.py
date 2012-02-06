# encoding: utf-8

import gdata.youtube.service
import urlparse
from knesset.video.management.commands.sub_commands import SubCommand

class GetYoutubeToken(SubCommand):

    def __init__(self,command,committees=None):
        SubCommand.__init__(self,command)
        ytService=gdata.youtube.service.YouTubeService()
        authSubUrl=ytService.GenerateAuthSubURL(
            next='http://www.oknesset.org/',
            scope='http://gdata.youtube.com', 
            secure=False, 
            session=True
        )
        print "open the following url: "+str(authSubUrl)
        print "authorize the application and at the end"
        print "you will be redirected to anothe url"
        print "paste the value of the token parameter from the query string"
        token=raw_input("paste the token here: ")
        ytService.SetAuthSubToken(token)
        ytService.UpgradeToSessionToken()
        print "thank you, this is your token:"
        print ytService.GetAuthSubToken()
