from django.conf import settings
from django.shortcuts import render, get_object_or_404
from knesset.mmm.models import Document
from knesset.mks.models import Member
from knesset.committees.models import Committee

def member_docs(request, mid):
    mks = get_object_or_404(Member, id=mid)
    mmm_docs = mks.mmm_documents.all()
    
    return render(request, 'mmm/member_mmm_docs.html', { "member": mks,
                                                    "mmm_docs": mmm_docs})
    

def committee_docs(request, cid):
    c = get_object_or_404(Committee, id=cid)
    mmm_docs = c.mmm_documents.all()
    
    return render(request, 'mmm/committee_mmm_docs.html', { "committee":c,
                                                    "mmm_docs": mmm_docs})