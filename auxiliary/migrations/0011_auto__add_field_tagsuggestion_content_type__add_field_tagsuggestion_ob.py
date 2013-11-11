# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'TagSuggestion.content_type'
        db.add_column(u'auxiliary_tagsuggestion', 'content_type',
                      self.gf('django.db.models.fields.related.ForeignKey')(default=1, to=orm['contenttypes.ContentType']),
                      keep_default=False)

        # Adding field 'TagSuggestion.object_id'
        db.add_column(u'auxiliary_tagsuggestion', 'object_id',
                      self.gf('django.db.models.fields.PositiveIntegerField')(default=1, db_index=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'TagSuggestion.content_type'
        db.delete_column(u'auxiliary_tagsuggestion', 'content_type_id')

        # Deleting field 'TagSuggestion.object_id'
        db.delete_column(u'auxiliary_tagsuggestion', 'object_id')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'auxiliary.feedback': {
            'Meta': {'object_name': 'Feedback'},
            'content': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip_address': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'}),
            'suggested_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'feedbacl'", 'null': 'True', 'to': u"orm['auth.User']"}),
            'url': ('django.db.models.fields.TextField', [], {}),
            'user_agent': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        u'auxiliary.tagsuggestion': {
            'Meta': {'object_name': 'TagSuggestion'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'unique': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'suggested_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'tagsuggestion'", 'null': 'True', 'to': u"orm['auth.User']"})
        },
        u'auxiliary.tagsynonym': {
            'Meta': {'object_name': 'TagSynonym'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'synonym_tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'synonym_synonym_tag'", 'unique': 'True', 'to': u"orm['tagging.Tag']"}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'synonym_proper_tag'", 'to': u"orm['tagging.Tag']"})
        },
        u'auxiliary.tidbit': {
            'Meta': {'object_name': 'Tidbit'},
            'button_link': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'button_text': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content': ('tinymce.models.HTMLField', [], {}),
            'icon': ('django.db.models.fields.CharField', [], {'max_length': '15'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'ordering': ('django.db.models.fields.IntegerField', [], {'default': '20', 'db_index': 'True'}),
            'photo': ('django.db.models.fields.files.ImageField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'suggested_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'tidbits'", 'null': 'True', 'to': u"orm['auth.User']"}),
            'title': ('django.db.models.fields.CharField', [], {'default': "u'Did you know ?'", 'max_length': '40'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'tagging.tag': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Tag'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'})
        }
    }

    complete_apps = ['auxiliary']