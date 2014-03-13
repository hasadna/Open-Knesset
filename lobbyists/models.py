# encoding: utf-8

from django.db import models

class Lobbyist(models.Model):
    person = models.ForeignKey('persons.Person', blank=False, null=False, related_name='lobbyist')
    knesset_id = models.CharField(blank=True, null=True, max_length=20)
    profession = models.CharField(blank=True, null=True, max_length=100)
    corporation_name = models.CharField(blank=True, null=True, max_length=100)
    corporation_id = models.CharField(blank=True, null=True, max_length=20)
    faction_member = models.CharField(blank=True, null=True, max_length=100)
    faction_name = models.CharField(blank=True, null=True, max_length=100)
    permit_type = models.CharField(blank=True, null=True, max_length=100)
    represents = models.ManyToManyField('lobbyists.LobbyistRepresent')

class LobbyistRepresent(models.Model):
    knesset_id = models.CharField(blank=True, null=True, max_length=20)
    name = models.CharField(blank=True, null=True, max_length=100)
    domain = models.CharField(blank=True, null=True, max_length=100)
    type = models.CharField(blank=True, null=True, max_length=100)
