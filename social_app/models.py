from django.db import models
from django.contrib.auth.models import User
from django.contrib.gis.db import models


class Player(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
    )

    def __str__(self):
        return self.user.username


class Match(models.Model):
   
    host = models.OneToOneField(
        Player,
        on_delete=models.CASCADE,
    )
    
    # password needed to access the hosted match
    password = models.CharField(max_length=10)
    
    players = models.ForeignKey(
        Player,
        on_delete=models.CASCADE,
    )
    
    numberOfHunters = models.IntegerField()
    hunters = models.ForeignKey(
        Player,
        on_delete=models.CASCADE,
    )
    numberOfHiders = models.IntegerField()
    hiders = models.ForeignKey(
        Player,
        on_delete=models.CASCADE,
    )
    
    # time(hour = 0, minute = 0, second = 0)
    matchTime = models.TimeField(auto_now=False, auto_now_add=False)
    radius = models.FloatField()
    
    # latitude and longitude of the place at which the match was first created
    createdAtlocation = models.PointField()
    
    has_started = models.BooleanField(default=False)
    is_over = models.BooleanField(default=False)
   
    def __str__(self):
        return self.host.username


class Friendship(models.Model):
    # Followers are players who have befriended you, while friends are players
    # who you have befriended.
    player = models.ForeignKey(
        Player,
        on_delete=models.CASCADE,
        related_name='friends',
    )
    friend = models.ForeignKey(
        Player,
        on_delete=models.CASCADE,
        related_name='followers',
    )

    class Meta:
        unique_together = ('player', 'friend')

    def __str__(self):
        return f'{self.player.user.username} -> {self.friend.user.username}'
