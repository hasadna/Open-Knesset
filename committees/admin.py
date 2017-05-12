from django.contrib.contenttypes import generic
from django.contrib.contenttypes.generic import GenericTabularInline
from django.db.models import Q, Count
from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from video.models import Video
from models import Committee, CommitteeMeeting, Topic, ProtocolPart
from links.models import Link
from django.utils.translation import ugettext_lazy as _
from mks.utils import get_all_mk_names
import logging

logger = logging.getLogger(__name__)


class CommitteeRelatedVideosInline(generic.GenericTabularInline):
    model = Video
    ct_fk_field = 'object_pk'
    can_delete = False
    fields = ['title', 'description', 'embed_link', 'group', 'hide']
    ordering = ['group', '-published']
    readonly_fields = ['title', 'description', 'embed_link', 'group']
    extra = 0

    def queryset(self, request):
        qs = super(CommitteeRelatedVideosInline, self).queryset(request)
        qs = qs.filter(Q(hide=False) | Q(hide=None))
        return qs


class CommitteeAdmin(ImportExportModelAdmin):
    ordering = ('name',)
    filter_horizontal = ('members', 'chairpersons', 'replacements')
    inlines = (CommitteeRelatedVideosInline,)


admin.site.register(Committee, CommitteeAdmin)


class MissingProtocolListFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _('Missing Protocol')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'is_missing_protocol'

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        return (
            ('missing_protocol', _('Has Missing Protocol')),
            ('has_protocol', _('Has Protocol')),
            # ('90s', _('in the nineties')),
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        # Compare the requested value (either '80s' or '90s')
        # to decide how to filter the queryset.
        if self.value() == 'missing_protocol':
            return queryset.filter(parts=None)
        elif self.value() == 'has_protocol':
            return queryset.exclude(parts=None)
        else:
            return queryset


class CommitteeMeetingAdmin(ImportExportModelAdmin):
    ordering = ('-date',)
    list_display = ('id', '__unicode__', 'date', 'committee_type', 'protocol_parts')
    list_filter = ('committee', 'committee__type', MissingProtocolListFilter)
    search_fields = ['id', 'topics']
    actions = ['redownload_and_reparse_protocol', 'reparse_protocol', 'update_metadata_from_dataservice']

    def committee_type(self, obj):
        return obj.committee.type

    def protocol_parts(self, obj):
        return obj.parts.all().count()

    def redownload_and_reparse_protocol(self, request, qs):
        mks, mk_names = get_all_mk_names()
        for meeting in qs:
            meeting.reparse_protocol(mks=mks, mk_names=mk_names)
        self.message_user(request, "successfully redownloaded & reparsed %s meetings" % qs.count())

    def reparse_protocol(self, request, qs):
        mks, mk_names = get_all_mk_names()
        for meeting in qs:
            logger.debug('reparsing meeting %s' % meeting.pk)
            meeting.reparse_protocol(redownload=False, mks=mks, mk_names=mk_names)
        self.message_user(request, "successfully reparsed %s meetings" % qs.count())

    def update_metadata_from_dataservice(self, request, qs):
        [cm.update_from_dataservice() for cm in qs]
        self.message_user(request, "successfully updated %s meetings" % qs.count())


admin.site.register(CommitteeMeeting, CommitteeMeetingAdmin)


class ProtocolPartsAdmin(ImportExportModelAdmin):
    search_fields = ('id', 'meeting__pk', 'header', 'body')
    list_display = ('id', 'meeting', 'header')


admin.site.register(ProtocolPart, ProtocolPartsAdmin)


class LinksTable(GenericTabularInline):
    model = Link
    ct_field = 'content_type'
    ct_fk_field = 'object_pk'


class TopicAdmin(ImportExportModelAdmin):
    ordering = ('-created',)
    list_select_related = True
    exclude = ('meetings',)
    inlines = [
        LinksTable,
    ]


admin.site.register(Topic, TopicAdmin)
