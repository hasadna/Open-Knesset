# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'CandidateListVotingStatistics'
        db.create_table('laws_candidatelistvotingstatistics', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('candidates_list', self.gf('django.db.models.fields.related.OneToOneField')(related_name='voting_statistics', unique=True, to=orm['polyorg.CandidateList'])),
        ))
        db.send_create_signal('laws', ['CandidateListVotingStatistics'])


    def backwards(self, orm):
        # Deleting model 'CandidateListVotingStatistics'
        db.delete_table('laws_candidatelistvotingstatistics')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'committees.committee': {
            'Meta': {'object_name': 'Committee'},
            'aliases': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'chairpersons': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'chaired_committees'", 'blank': 'True', 'to': "orm['mks.Member']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'members': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'committees'", 'blank': 'True', 'to': "orm['mks.Member']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'portal_knesset_broadcasts_url': ('django.db.models.fields.URLField', [], {'max_length': '1000', 'blank': 'True'}),
            'replacements': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'replacing_in_committees'", 'blank': 'True', 'to': "orm['mks.Member']"})
        },
        'committees.committeemeeting': {
            'Meta': {'ordering': "('-date',)", 'object_name': 'CommitteeMeeting'},
            'committee': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'meetings'", 'to': "orm['committees.Committee']"}),
            'date': ('django.db.models.fields.DateField', [], {}),
            'date_string': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mks_attended': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'committee_meetings'", 'symmetrical': 'False', 'to': "orm['mks.Member']"}),
            'protocol_text': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'src_url': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'null': 'True', 'blank': 'True'}),
            'topics': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'votes_mentioned': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'committee_meetings'", 'blank': 'True', 'to': "orm['laws.Vote']"})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'events.event': {
            'Meta': {'object_name': 'Event'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'what': ('django.db.models.fields.TextField', [], {}),
            'when': ('django.db.models.fields.DateTimeField', [], {}),
            'when_over': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'when_over_guessed': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'where': ('django.db.models.fields.TextField', [], {}),
            'which_pk': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'which_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'event_for_event'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'who': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['persons.Person']", 'symmetrical': 'False'})
        },
        'laws.bill': {
            'Meta': {'ordering': "('-stage_date', '-id')", 'object_name': 'Bill'},
            'approval_vote': ('django.db.models.fields.related.OneToOneField', [], {'blank': 'True', 'related_name': "'bill_approved'", 'unique': 'True', 'null': 'True', 'to': "orm['laws.Vote']"}),
            'first_committee_meetings': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'bills_first'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['committees.CommitteeMeeting']"}),
            'first_vote': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'bills_first'", 'null': 'True', 'to': "orm['laws.Vote']"}),
            'full_title': ('django.db.models.fields.CharField', [], {'max_length': '2000', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'joiners': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'bills_joined'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['mks.Member']"}),
            'law': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'bills'", 'null': 'True', 'to': "orm['laws.Law']"}),
            'popular_name': ('django.db.models.fields.CharField', [], {'max_length': '1000', 'blank': 'True'}),
            'popular_name_slug': ('django.db.models.fields.CharField', [], {'max_length': '1000', 'blank': 'True'}),
            'pre_votes': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'bills_pre_votes'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['laws.Vote']"}),
            'proposers': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'bills'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['mks.Member']"}),
            'second_committee_meetings': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'bills_second'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['committees.CommitteeMeeting']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '1000'}),
            'stage': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'stage_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '1000'})
        },
        'laws.candidatelistvotingstatistics': {
            'Meta': {'object_name': 'CandidateListVotingStatistics'},
            'candidates_list': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'voting_statistics'", 'unique': 'True', 'to': "orm['polyorg.CandidateList']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'laws.govlegislationcommitteedecision': {
            'Meta': {'object_name': 'GovLegislationCommitteeDecision'},
            'bill': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'gov_decisions'", 'null': 'True', 'to': "orm['laws.Bill']"}),
            'date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'number': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'source_url': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'null': 'True', 'blank': 'True'}),
            'stand': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'subtitle': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '1000'})
        },
        'laws.govproposal': {
            'Meta': {'object_name': 'GovProposal'},
            'bill': ('django.db.models.fields.related.OneToOneField', [], {'blank': 'True', 'related_name': "'gov_proposal'", 'unique': 'True', 'null': 'True', 'to': "orm['laws.Bill']"}),
            'booklet_number': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'committee_meetings': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'laws_govproposal_related'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['committees.CommitteeMeeting']"}),
            'content_html': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'knesset_id': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'law': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'laws_govproposal_related'", 'null': 'True', 'to': "orm['laws.Law']"}),
            'source_url': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '1000'}),
            'votes': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'laws_govproposal_related'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['laws.Vote']"})
        },
        'laws.knessetproposal': {
            'Meta': {'object_name': 'KnessetProposal'},
            'bill': ('django.db.models.fields.related.OneToOneField', [], {'blank': 'True', 'related_name': "'knesset_proposal'", 'unique': 'True', 'null': 'True', 'to': "orm['laws.Bill']"}),
            'booklet_number': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'committee': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'bills'", 'null': 'True', 'to': "orm['committees.Committee']"}),
            'committee_meetings': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'laws_knessetproposal_related'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['committees.CommitteeMeeting']"}),
            'content_html': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'knesset_id': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'law': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'laws_knessetproposal_related'", 'null': 'True', 'to': "orm['laws.Law']"}),
            'originals': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'knesset_proposals'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['laws.PrivateProposal']"}),
            'source_url': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '1000'}),
            'votes': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'laws_knessetproposal_related'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['laws.Vote']"})
        },
        'laws.law': {
            'Meta': {'object_name': 'Law'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'merged_into': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'duplicates'", 'null': 'True', 'to': "orm['laws.Law']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '1000'})
        },
        'laws.membervotingstatistics': {
            'Meta': {'object_name': 'MemberVotingStatistics'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'member': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'voting_statistics'", 'unique': 'True', 'to': "orm['mks.Member']"})
        },
        'laws.partyvotingstatistics': {
            'Meta': {'object_name': 'PartyVotingStatistics'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'party': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'voting_statistics'", 'unique': 'True', 'to': "orm['mks.Party']"})
        },
        'laws.privateproposal': {
            'Meta': {'object_name': 'PrivateProposal'},
            'bill': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'proposals'", 'null': 'True', 'to': "orm['laws.Bill']"}),
            'committee_meetings': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'laws_privateproposal_related'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['committees.CommitteeMeeting']"}),
            'content_html': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'joiners': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'proposals_joined'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['mks.Member']"}),
            'knesset_id': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'law': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'laws_privateproposal_related'", 'null': 'True', 'to': "orm['laws.Law']"}),
            'proposal_id': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'proposers': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'proposals_proposed'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['mks.Member']"}),
            'source_url': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '1000'}),
            'votes': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'laws_privateproposal_related'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['laws.Vote']"})
        },
        'laws.vote': {
            'Meta': {'ordering': "('-time', '-id')", 'object_name': 'Vote'},
            'against_coalition': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'against_opposition': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'against_own_bill': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'against_party': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'against_votes_count': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'controversy': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'for_votes_count': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'full_text': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'full_text_url': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'importance': ('django.db.models.fields.FloatField', [], {'default': '0.0'}),
            'meeting_number': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'src_id': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'src_url': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'null': 'True', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'time': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'time_string': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '1000'}),
            'vote_number': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'votes': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'votes'", 'blank': 'True', 'through': "orm['laws.VoteAction']", 'to': "orm['mks.Member']"}),
            'votes_count': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'laws.voteaction': {
            'Meta': {'object_name': 'VoteAction'},
            'against_coalition': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'against_opposition': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'against_own_bill': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'against_party': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'member': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['mks.Member']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'vote': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['laws.Vote']"})
        },
        'mks.member': {
            'Meta': {'ordering': "['name']", 'object_name': 'Member'},
            'area_of_residence': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'average_monthly_committee_presence': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'average_weekly_presence_hours': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'backlinks_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'bills_stats_approved': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'bills_stats_first': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'bills_stats_pre': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'bills_stats_proposed': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'blog': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['planet.Blog']", 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'current_party': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'members'", 'null': 'True', 'to': "orm['mks.Party']"}),
            'current_role_descriptions': ('django.db.models.fields.CharField', [], {'max_length': '1024', 'null': 'True', 'blank': 'True'}),
            'date_of_birth': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'date_of_death': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'family_status': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True', 'blank': 'True'}),
            'fax': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'gender': ('django.db.models.fields.CharField', [], {'max_length': '1', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'img_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'is_current': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'number_of_children': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'parties': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'all_members'", 'symmetrical': 'False', 'through': "orm['mks.Membership']", 'to': "orm['mks.Party']"}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'place_of_birth': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'place_of_residence': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'place_of_residence_lat': ('django.db.models.fields.CharField', [], {'max_length': '16', 'null': 'True', 'blank': 'True'}),
            'place_of_residence_lon': ('django.db.models.fields.CharField', [], {'max_length': '16', 'null': 'True', 'blank': 'True'}),
            'residence_centrality': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'residence_economy': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'start_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'website': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'year_of_aliyah': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'mks.membership': {
            'Meta': {'object_name': 'Membership'},
            'end_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'member': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['mks.Member']"}),
            'party': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['mks.Party']"}),
            'start_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'})
        },
        'mks.party': {
            'Meta': {'ordering': "('-number_of_seats',)", 'object_name': 'Party'},
            'end_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_coalition': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'number_of_members': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'number_of_seats': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'start_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'})
        },
        'persons.person': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Person'},
            'area_of_residence': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'date_of_birth': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'date_of_death': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'family_status': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True', 'blank': 'True'}),
            'fax': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'gender': ('django.db.models.fields.CharField', [], {'max_length': '1', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'img_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'mk': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'person'", 'null': 'True', 'to': "orm['mks.Member']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'number_of_children': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'place_of_birth': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'place_of_residence': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'place_of_residence_lat': ('django.db.models.fields.CharField', [], {'max_length': '16', 'null': 'True', 'blank': 'True'}),
            'place_of_residence_lon': ('django.db.models.fields.CharField', [], {'max_length': '16', 'null': 'True', 'blank': 'True'}),
            'residence_centrality': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'residence_economy': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'titles': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'persons'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['persons.Title']"}),
            'year_of_aliyah': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'persons.title': {
            'Meta': {'object_name': 'Title'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'})
        },
        'planet.blog': {
            'Meta': {'ordering': "('title', 'url')", 'object_name': 'Blog'},
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '255', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '1024', 'db_index': 'True'})
        },
        'polyorg.candidate': {
            'Meta': {'object_name': 'Candidate'},
            'candidates_list': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['polyorg.CandidateList']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ordinal': ('django.db.models.fields.IntegerField', [], {}),
            'party': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['polyorg.Party']", 'null': 'True', 'blank': 'True'}),
            'person': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['persons.Person']"}),
            'votes': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'polyorg.candidatelist': {
            'Meta': {'object_name': 'CandidateList'},
            'ballot': ('django.db.models.fields.CharField', [], {'max_length': '4'}),
            'candidates': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['persons.Person']", 'null': 'True', 'through': "orm['polyorg.Candidate']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mpg_html_report': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'number_of_seats': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'surplus_partner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['polyorg.CandidateList']", 'null': 'True', 'blank': 'True'})
        },
        'polyorg.party': {
            'Meta': {'object_name': 'Party'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'number_of_seats': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'tagging.tag': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'})
        },
        'tagging.taggeditem': {
            'Meta': {'unique_together': "(('tag', 'content_type', 'object_id'),)", 'object_name': 'TaggedItem'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'items'", 'to': "orm['tagging.Tag']"})
        }
    }

    complete_apps = ['laws']