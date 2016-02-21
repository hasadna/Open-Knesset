import urllib2

from django.core.management.base import NoArgsCommand
from django.core.files.base import ContentFile
from django.contrib.auth.models import User, Group

from actstream import follow

from mks.models import Member
from avatar.models import Avatar


class Command(NoArgsCommand):
    help = "Copy information from Member model to User, UserPrifle and Avatar"

    def handle_noargs(self, **options):
        # TODO: VALID_EMAIL_GROUP should be project-wide 
        valid_email = Group.objects.get(name='Valid Email')
        for member in Member.objects.all():
            user = member.user
            if not user: user = User()
            user.email = member.email
            user.username = member.email.split('@')[0]
            self.stdout.write(u"filling user data for member #%d (%s)\n" % ( member.id, user.username ))

            names = member.name.split(' ')
            user.first_name = ' '.join(names[:-1])
            if user.first_name:
                user.last_name = names[-1]
            else:
                # just one name, better make it the first
                user.first_name = names[0]
                user.last_name = ''

            user.save()
            user.groups.add(valid_email)
            avatars =  Avatar.objects.filter(user=user)
            avatar = avatars[0] if avatars else user.avatar_set.create()

            image_url = urllib2.urlopen(member.img_url)
            content = ContentFile(image_url.read())
            avatar.avatar.save(user.username, content)
            try:
                profile = user.profiles.get()
            except:
                profile = user.profiles.create()

            profile.email_notification='D'
            if not profile.description:
                profile.description = member.get_role

            profile.gender = member.gender
            profile.save()
            follow (user, member)

            if not member.user:
                member.user = user
                member.save()
