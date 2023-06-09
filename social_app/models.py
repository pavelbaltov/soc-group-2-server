from django.db import models
from django.contrib.auth.models import User
from django.contrib.gis.db import models
import datetime

class Location(models.Model):
    latitude = models.FloatField()
    longitude = models.FloatField()

class Player(models.Model):
    ROLE_CHOICES = [
        ("HI", "Hider"),
        ("HU", "Hunter"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)

    # represents the GPS location of a player
    location = models.OneToOneField(Location, on_delete=models.CASCADE,)

    # function which has to return all Friendship objects which are associated with this user
    # i.e. returns the friendships of a player
    def get_friends(self):
        return Friendship.objects.filter(player=self.user.username)

    def __str__(self):
        return self.user.username


class Match(models.Model):
    # no need for id field as Django creates auto-incrementing ids
    # for each model

    host = models.OneToOneField(
        Player,
        on_delete=models.CASCADE,
        related_name='playerHost',
    )
    
    # password needed to access the hosted match
    password = models.CharField(max_length=10)
    
    players = models.ForeignKey(
        Player,
        on_delete=models.CASCADE,
        related_name='playersInMatch',
    )
    
    numberOfHunters = models.IntegerField()
    numberOfHiders = models.IntegerField()
    
    # time(hour = 0, minute = 0, second = 0)
    duration = models.TimeField(auto_now=False, auto_now_add=False)
    radius = models.FloatField(max_length=10)
    
    # latitude and longitude of the place at which the match was first created
    createdAtLocation = models.OneToOneField(Location, default={41.84163, 9.78773},on_delete=models.CASCADE,)
    createdAtTime = models.TimeField(auto_now=False, auto_now_add=False)
    #redundant: has_started = models.BooleanField(default=False)
    #redundant: is_over = models.BooleanField(default=False)

    def hasStarted(self):
        if datetime.now() > self.createdAtTime:
           return True
        else:
            return False

    def __str__(self):
        return self.host.username

class Clue(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    player = models.OneToOneField(Player, on_delete=models.CASCADE,)
    #should we use the already defined location in Player model ???
    location = models.OneToOneField(Location, on_delete=models.CASCADE)

class Object(models.Model):
    OBJECT_TYPE = [
        ("T", "Trap"),
        ("L", "Loot"),
    ]

    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    type = models.CharField(max_length=10, choices=OBJECT_TYPE)
    location = models.OneToOneField(Location, on_delete=models.CASCADE)


class Friendship(models.Model):
    # Followers are players who have befriended you, while friends are players
    # who you have befriended. We use ForeignKey (Many-to-One) because Friendship
    # can have only one player and friend object but player and friend object
    # can be associated with many Friendship objects
    player = models.ForeignKey(
        Player,
        on_delete=models.CASCADE,
        related_name='friendFrom',
    )
    friend = models.ForeignKey(
        Player,
        on_delete=models.CASCADE,
        related_name='friendTo',
    )
    class Meta:
        unique_together = ('player', 'friend')
    def __str__(self):
        return f'{self.player.user.username} -> {self.friend.user.username}'

class FriendshipRequest(models.Model):
    player = models.ForeignKey(
        Player,
        on_delete=models.CASCADE,
        related_name='requesterFrom',
    )
    friend = models.ForeignKey(
        Player,
        on_delete=models.CASCADE,
        related_name='requestedTo',
    )

    is_accepted = models.BooleanField()

    # accepts the friendship request and creates a new Friendship object and
    # deletes the current Friendship request
    def accept(self):
        acceptedFriendship = Friendship(player=self.player, friend=self.friend)
        acceptedFriendship.save()
        self.delete()

    # declines the friendship request and deletes the current Friendship request
    def decline(self):
        self.delete()

    # Meta - additional options for this model
    # ensures that all pairs are unique!
    class Meta:
        unique_together = ('player', 'friend')
