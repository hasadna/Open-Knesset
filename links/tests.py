import unittest
import re
import os
from django.conf import settings
from django.test.client import Client
from django.core.urlresolvers import reverse
from django.core.files import File
from django.contrib.sites.models import Site
from django.template import Template, Context
from links.models import Link, LinkType

class TestViews(unittest.TestCase):

    def setUp(self):
        self.type_a = LinkType.objects.create(title='a')
        self.obj = Site.objects.create(domain="example.com", name="example")
        self.l1 = Link.objects.create(url='http://www.example.com/l1', title='l1',
                                 content_object=self.obj, link_type=self.type_a)
        # make sure
        try:
            os.remove(os.path.join(settings.MEDIA_ROOT, 'icons' , 'testimage.png'))
        except OSError:
            pass

    def testTextType(self):
        # test a link with no image type
        self.type_a.image = None
        self.type_a.save()
        c = Context ({'obj': self.obj})
        t = Template('{% load links_tags %}{% object_links obj %}')
        r = re.sub('\s', '', t.render(c))
        self.assertEquals(r,
    '<li>&nbsp;(a)<ahref="http://www.example.com/l1"target="_blank">l1</a></li>')

    def testImageType(self):
        # test a link with  a type image
        f = open(os.path.join("testdata", "testimage.png"),"r")
        self.type_a.image=File(f)
        self.type_a.save()
        c = Context ({'obj': self.obj})
        t = Template('{% load links_tags %}{% object_links obj %}')
        r = re.sub('\s', '', t.render(c))
        self.assertEquals(r,
    '<li>&nbsp;<imgsrc="/media/icons/testimage.png"alt="a"><ahref="http://www.example.com/l1"target="_blank">l1</a></li>')

    def tearDown(self):
        self.l1.delete()
        self.type_a.delete()
        self.obj.delete()
