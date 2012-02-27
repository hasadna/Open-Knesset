import json
from knesset.hashnav import ListView
from django.http import HttpResponse
from knesset.video.models import Video

class VideoListView (ListView):
    def GET(self, *args, **kwargs):
        #if (not self.request.user.is_authenticated()):
        #    raise Exception('You must be logged in')
        #if (not self.request.user.is_staff())
        # self.request.user
        # self.extra_context        
        self.extra_context['user']=self.request.user
        return super(VideoListView, self).GET(*args,**kwargs)

def videoListApproveAjaxView(request):
    if (request.user.is_staff):
        if request.method=='POST':
            updatedVideoIds=[]
            hideVideoIds=request.POST['hideVideoIds']
            if (len(hideVideoIds))>0:
                hideVideoIds=hideVideoIds.split(',')
                Video.objects.filter(id__in=hideVideoIds).update(reviewed=True,hide=True)
                updatedVideoIds.extend(hideVideoIds)
            showVideoIds=request.POST['showVideoIds']
            if len(showVideoIds)>0:
                showVideoIds=showVideoIds.split(',')
                Video.objects.filter(id__in=showVideoIds).update(reviewed=True,hide=False)
                updatedVideoIds.extend(showVideoIds)
            res={
                'status':True,
                'updatedVideoIds':updatedVideoIds,
            }
        else:
            res={'status':False,'msg':'invalid request method'}
    else:
        res={'status':False,'msg':'not authenticated'}
    return HttpResponse(json.dumps(res), mimetype="application/json")
