# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Video.approved'
        db.add_column('video_video', 'reviewed', self.gf('django.db.models.fields.BooleanField')(default=False), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Video.approved'
        db.delete_column('video_video', 'reviewed')


    models = {
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'video.video': {
            'Meta': {'object_name': 'Video'},
            'reviewed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '2000', 'blank': 'True'}),
            'embed_link': ('django.db.models.fields.URLField', [], {'max_length': '1000'}),
            'group': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'hide': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image_link': ('django.db.models.fields.URLField', [], {'max_length': '1000'}),
            'link': ('django.db.models.fields.URLField', [], {'max_length': '1000'}),
            'object_pk': ('django.db.models.fields.TextField', [], {}),
            'published': ('django.db.models.fields.DateTimeField', [], {}),
            'small_image_link': ('django.db.models.fields.URLField', [], {'max_length': '1000'}),
            'source_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'source_type': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'sticky': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '500'})
        }
    }

    complete_apps = ['video']
