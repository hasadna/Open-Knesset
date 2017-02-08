# encoding: utf-8
from south.v2 import DataMigration

class Migration(DataMigration):

    def get_or_create(self, model, **kwargs):
        if model.objects.filter(**kwargs).exists():
            return model.objects.get(**kwargs), False
        else:
            return model.objects.create(**kwargs), True

    def forwards(self, orm):
        Group = orm['auth.Group']
        Permission = orm['auth.Permission']
        User = orm['auth.User']
        g, created = self.get_or_create(Group, name='Valid Email')
        if created:
            g.save()

        qs = Permission.objects.filter(name='Can add comment')
        if qs.exists():
            g.permissions.add(qs.first())
        qs = Permission.objects.filter(name='Can add annotation')
        if qs.exists():
            g.permissions.add(qs.first())

        for u in User.objects.all():
            for p in u.user_permissions.all():
                u.groups.add(g)
                u.user_permissions.remove(p)
                print "user %s: permission->group" % u.username

    def backwards(self, orm):
        Group = orm['auth.Group']
        Permission = orm['auth.Permission']
        User = orm['auth.User']

        p = Permission.objects.get(name='Can add comment')
        g = Group.objects.get(name='Valid Email')
        
        for u in User.objects.all():
            if g in u.groups.all():
                print "user %s: group->permission" % u.username
                u.user_permissions.add(p)
                u.groups.remove(g)
        
        g.delete()


    models = {
        'accounts.emailvalidation': {
            'Meta': {'object_name': 'EmailValidation'},
            'activation_key': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'date_requested': ('django.db.models.fields.DateField', [], {}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
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
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['accounts']
