from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User
from django.contrib.gis.db import models
import datetime

class Match(models.Model):
    # no need for id field as Django creates auto-incrementing ids
    # for each model
    host = models.CharField(max_length=20, default="")
    name = models.CharField(max_length=10, default="")

    # password needed to access the hosted match
    password = models.CharField(max_length=10, null=True)

    #players = models.ForeignKey(
    #    Player,
    #    on_delete=models.CASCADE,
    #    related_name='playersInMatch',
    #    null=True
    #)

    numberOfHunters = models.IntegerField(default=2)
    numberOfHiders = models.IntegerField(default=4)

    # time(hour = 0, minute = 0, second = 0)
    duration = models.TimeField(auto_now=False, auto_now_add=False, null=True)
    radius = models.FloatField(max_length=10, default=5)

    # latitude and longitude of the place at which the match was first created
    createdAtLocation = models.PointField(null=True)
    createdAtTime = models.TimeField(auto_now=False, auto_now_add=False, null=True)

    # redundant: has_started = models.BooleanField(default=False)
    # redundant: is_over = models.BooleanField(default=False)

    def hasStarted(self):
        if datetime.now() > self.createdAtTime:
            return True
        else:
            return False
    def is_full(self):
        if self.player_set.count() >= self.numberOfHunters + self.numberOfHiders:
            return True
        else:
            return False
    def __str__(self):
        return self.name

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
    role = models.CharField(max_length=10,  null=True, choices=ROLE_CHOICES)

    # represents the GPS location of a player
    location = models.PointField(null=True)
    match = models.ForeignKey(Match, blank=True, null=True, on_delete=models.SET_NULL)
    # function which has to return all Friendship objects which are associated with this user
    # i.e. returns the friendships of a player
    def get_friends(self):
        friendships = Friendship.objects.filter(Q(player=self) | Q(friend=self))
        friends = [f.get_friend_of_player(self) for f in friendships]
        return friends

    def get_requests(self):
        friendship_requests = FriendshipRequest.objects.filter(recipient=self.user.id)
        requests = [r.requester for r in friendship_requests]
        return requests

    def is_friend_with(self, player):
        is_friend = Friendship.objects.filter(Q(player=self, friend=player) | Q(player=player, friend=self)).exists()
        return is_friend

    def __str__(self):
        return self.user.username





class Clue(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE, null=True)
    player = models.OneToOneField(Player, on_delete=models.CASCADE, null=True)
    # should we use the already defined location in Player model ???
    location = models.PointField(null=True)


class Object(models.Model):
    OBJECT_TYPE = [
        ("T", "Trap"),
        ("L", "Loot"),
    ]

    match = models.ForeignKey(Match, on_delete=models.CASCADE, null=True)
    type = models.CharField(max_length=10, choices=OBJECT_TYPE)
    location = models.PointField(null=True)


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
    def get_friend_of_player(self, player_to_inspect):
        if player_to_inspect.user.id == self.player.user.id:
            return self.friend
        elif player_to_inspect.user.id == self.friend.user.id:
            return self.player
        return None

    class Meta:
        unique_together = ('player', 'friend')

    def __str__(self):
        return f'{self.player.user.username} -> {self.friend.user.username}'


class FriendshipRequest(models.Model):
    requester = models.ForeignKey(
        Player,
        on_delete=models.CASCADE,
        related_name='requesterFrom',
    )
    recipient = models.ForeignKey(
        Player,
        on_delete=models.CASCADE,
        related_name='requestedTo',
    )

    # accepts the friendship request and creates a new Friendship object and
    # deletes the current Friendship request
    def accept(self):
        acceptedFriendship = Friendship(player=self.requester, friend=self.recipient)
        acceptedFriendship.save()
        self.delete()

    # declines the friendship request and deletes the current Friendship request
    def decline(self):
        self.delete()

    # Meta - additional options for this model
    # ensures that all pairs are unique!
    class Meta:
        unique_together = ('requester', 'recipient')

    def __str__(self):
        return f'Request: {self.requester.user.username} -> {self.recipient.user.username}'

