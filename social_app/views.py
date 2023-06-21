import json

from django.contrib.auth.models import User
from django.contrib.gis.geos import Point
from django.http import HttpResponse, JsonResponse

from .models import Player, Friendship, Match, FriendshipRequest
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm
from geopy.distance import distance
import datetime


# USER AUTHENTICATION: check_auth, signout, signin, signup

def check_auth(request):
    if request.user.is_authenticated:
        return HttpResponse(f'0: "{request.user.username}" is authenticated')
    else:
        return HttpResponse('1: user is not authenticated')

def signout(request):
    logout(request)
    return HttpResponse('0: successful logout')

def signin(request):
    if request.user.is_authenticated:
        return HttpResponse(f'1: "{request.user.username}" already signed in')
    if request.method != 'POST':
        return HttpResponse(f'incorrect request method.')
    username = request.POST['username']
    password = request.POST['password']

    # authenticate() only returns a user if username and password are correct
    user = authenticate(request, username=username, password=password)
    if user is None:
        return HttpResponse(f'could not authenticate.')
    login(request, user)
    return HttpResponse('0: successful signin')


def signup(request):
    if request.method != 'POST':
        return HttpResponse(f'incorrect request method.')
    # Instead of checking for the form data ourselves, we use the already
    # existing UserCreationForm.
    form = UserCreationForm(request.POST)
    if not form.is_valid():
        return HttpResponse(f'invalid form: {form}')
    # This creates a user from that form
    form.save()
    # This logs in that user
    username = form.cleaned_data.get('username')
    raw_password = form.cleaned_data.get('password1')
    # We don't have to check if the username and password are correct
    # because we just created that exact user.
    user = authenticate(username=username, password=raw_password)
    login(request, user)
    # Create the user's player
    player = Player(user=user)
    # Don't forget to save at the end of all the changes to table contents
    player.save()
    return HttpResponse('0: successful signup')


# FRIENDS LIST:
# view functions: get_names, get_friends, add_friend,
# helper functions: update_friendship_level, update_all_friendship_levels

def get_players(request):
    if not request.user.is_authenticated:
        return HttpResponse(f'User not signed in')

    non_friend_players = [player for player in Player.objects.all()
                          if not player.is_friend_with(request.user.player)]
    non_friend_players.remove(request.user.player)

    players = [
        {
            "id": player.user.id,
            "username": player.user.username,
            "latitude": player.location.y,
            "longitude": player.location.x,
            "distance": round(distance(request.user.player.location, player.location).kilometers, 2)
        }
        for player in non_friend_players
    ]

    return JsonResponse(players, safe=False)

def get_players_nearby(request,radius):
    if not request.user.is_authenticated:
        return HttpResponse(f'User not signed in!')


    current_location = request.user.player.location

    players = [
        {
            "username": player.user.username,
            "latitude": player.location.y,
            "longitude": player.location.x,
            "distance": round(distance(request.user.player.location, player.location).kilometers, 2)
        }
        for player in Player.objects.all() if distance(current_location, player.location).kilometers < float(radius)
    ]
    return JsonResponse(players, safe=False)

def get_player_by_username(request, username):
    if not request.user.is_authenticated:
        return HttpResponse(f'User not signed in')
    try:
        found_user = User.objects.get(username=username)
    except User.DoesNotExist:
        return HttpResponse("0: Failed to find player", status=200)

    if (request.user.player.is_friend_with(found_user.player)):
        return HttpResponse("0: This player is in your friend list", status=200)


    player = {
        "username": found_user.username,
        "latitude": found_user.player.location.y,
        "longitude": found_user.player.location.x,
        "distance": round(distance(request.user.player.location, found_user.player.location).kilometers,2)
    }

    return JsonResponse(player, safe=False)

def update_location(request):

    data = json.loads(request.body)
    latitude = float(data['latitude'])
    longitude = float(data['longitude'])

    player = request.user.player
    player.location = Point(longitude, latitude)
    player.save()

    return HttpResponse("1: Successfully updated location!")

def get_friends(request):
    if not request.user.is_authenticated:
        return HttpResponse(f'User not signed in')
    if not hasattr(request.user, 'player'):
        return HttpResponse(f'user is not a player')

    friends = [
        {
            "username": friend.user.username,
            "latitude": friend.location.y,
            "longitude": friend.location.x,
            "distance": round(distance(request.user.player.location, friend.location).kilometers, 2)
        }
        for friend in request.user.player.get_friends()
    ]
    return JsonResponse(friends, safe=False)

def send_friendship_request(request, username):
    if not request.user.is_authenticated:
        return HttpResponse(f'user not signed in')
    if not hasattr(request.user, 'player'):
        return HttpResponse(f'user is not a player')

    requester = User.objects.get(username=request.user.username)
    recipient = User.objects.get(username=username)

    #check if such players exists

    existing_request = FriendshipRequest.objects.filter(
        requester=requester.player, recipient=recipient.player
    ).exists()

    if existing_request:
        return HttpResponse("0: Friendship request already sent", status=200)

    # Create a new friendship request
    frRe = FriendshipRequest(requester=requester.player, recipient=recipient.player)
    frRe.save()

    return HttpResponse("1: Friendship request sent successfully", status=200)

def respond_friendship_request(request):
    # Commented for testing purposes
    # if not request.user.is_authenticated:
    #   return HttpResponse(f'user not signed in')
    # if not hasattr(request.user, 'player'):
    #    return HttpResponse(f'user is not a player')

    data = json.loads(request.body)

    from_user = data['from_user']
    response = data['response']

    requester = User.objects.get(username=from_user)
    recipient = request.user

    existing_request = FriendshipRequest.objects.filter(
        requester=requester.player, recipient=recipient.player
    ).exists()

    if not existing_request:
        return HttpResponse("0: Friendship request doesn\'t exist", status=200)

    frRe = FriendshipRequest.objects.get(requester=requester.player, recipient=recipient.player)
    if response:
        frRe.accept()
        return HttpResponse("1: Friendship request accepted successfully", status=200)
    else:
        frRe.decline()
        return HttpResponse("1: Friendship request declined successfully", status=200)

def get_friendship_requests(request):
    # Commented for testing purposes
    # if not request.user.is_authenticated:
    #   return HttpResponse(f'user not signed in')
    requestsOfPlayer = request.user.player.get_requests()
    if len(requestsOfPlayer) == 0:
        return HttpResponse("0: No requests", status=200)

    requests = [
        {
            "username": r.user.username,
            "latitude": r.location.y,
            "longitude": r.location.x,
            "distance": round(distance(request.user.player.location, r.location).kilometers, 2)
        }
        for r in requestsOfPlayer
    ]
    return JsonResponse(requests, safe=False)

def remove_friend(request):

    data = json.loads(request.body)
    friend_to_remove = data['friend_to_remove']

    friend = Player.objects.get(id=friend_to_remove)
    friendship = Friendship.objects.get(player=request.user.player, friend=friend)
    friendship.delete()

    return HttpResponse("1: Successfully removed this friend")


# TILTBALL: host_match, join_match, get_match, pass_ball, end_match
def get_matches(request):
    if not request.user.is_authenticated:
        return HttpResponse(f'user not signed in')

    matches = [
        {
            "name": match.name,
            "host": match.host,
            "latitude": match.createdAtLocation.y,
            "longitude": match.createdAtLocation.x,
            "duration": match.duration,
            "radius": match.radius,
            "distance": distance(request.user.player.location, match.createdAtLocation).kilometers,
            "number_of_joined_players": match.player_set.count(),
            "number_of_hunters": match.numberOfHunters,
            "number_of_hiders": match.numberOfHiders
        }
        for match in Match.objects.all()
    ]

    return JsonResponse(matches, safe=False)

def get_matches_nearby(request, radius):
    if not request.user.is_authenticated:
        return HttpResponse(f'user not signed in')

    matches = [
        {
            "name": match.name,
            "host": match.host,
            "latitude": match.createdAtLocation.y,
            "longitude": match.createdAtLocation.x,
            "duration": match.duration,
            "radius": match.radius,
            "distance": distance(request.user.player.location, match.createdAtLocation).kilometers,
            "number_of_joined_players": match.player_set.count(),
            "number_of_hunters": match.numberOfHunters,
            "number_of_hiders": match.numberOfHiders
        }
        for match in Match.objects.all() if distance(request.user.player.location, match.createdAtLocation).kilometers < float(radius)
    ]
    return JsonResponse(matches, safe=False)

def get_matches_of_friends(request):
    if not request.user.is_authenticated:
        return HttpResponse(f'user not signed in')

    matches = [
        {
            "name": match.name,
            "host": match.host,
            "latitude": match.createdAtLocation.y,
            "longitude": match.createdAtLocation.x,
            "duration": match.duration,
            "radius": match.radius,
            "distance": distance(request.user.player.location, match.createdAtLocation).kilometers,
            "number_of_joined_players": match.player_set.count(),
            "number_of_hunters": match.numberOfHunters,
            "number_of_hiders": match.numberOfHiders
        }
        for match in Match.objects.all() if request.user.player.is_friend_with(Player.objects.get(user__username=match.host))
    ]
    return JsonResponse(matches, safe=False)

def host_match(request):
    if not request.user.is_authenticated:
        return HttpResponse(f'user not signed in')
    if not hasattr(request.user, 'player'):
        return HttpResponse(f'user is not a player')

    data = json.loads(request.body)
    name = data["name"]
    latitude = float(data['latitude'])
    longitude = float(data['longitude'])
    duration = data['duration']
    radius = float(data['radius'])
    number_of_hunters = int(data['number_of_hunters'])
    number_of_hiders = int(data['number_of_hiders'])

    player = request.user.player
    player.match = Match()
    player.match.host = player.user.username
    player.match.name = name
    player.match.createdAtLocation = Point(longitude, latitude)
    player.match.duration = datetime.timedelta(minutes=int(duration))
    player.match.radius = radius
    player.match.numberOfHiders = number_of_hiders
    player.match.numberOfHunters = number_of_hunters
    player.match.save()
    return HttpResponse(f'1: reset match')


def join_match(request):
    if not request.user.is_authenticated:
        return HttpResponse(f'user not signed in')
    if request.method != 'POST':
        return HttpResponse(f'incorrect request method.')

    host_name = request.POST['hostname']
    hostPlayer = Player.objects.get(user__username=host_name)

    if hostPlayer.match is not None:
        if hostPlayer.match.is_full():
            return HttpResponse(f"0: Match is full")
        else:
            request.user.player.match = Match.objects.get(host=host_name)
            request.user.player.save()
            return HttpResponse(f'1: Joined match')
    else:
        return HttpResponse(f'0: No match with host {host_name} exists')

def exit_match(request):
    if not request.user.is_authenticated:
        return HttpResponse(f'user not signed in')

    if request.user.player.match is None:
        return HttpResponse(f"0: No active match")
    else:
        request.user.player.match = None
        request.user.player.save()
        return HttpResponse(f'1: Exited match')

def get_players_in_current_match(request):
    if not request.user.is_authenticated:
        return HttpResponse(f'User not signed in!')

    players = [
        {
            "username": player.user.username,
            "latitude": player.location.y,
            "longitude": player.location.x,
            "distance": round(distance(request.user.player.location, player.location).kilometers, 2)
        }
        for player in request.user.player.match.player_set.all()
    ]
    return JsonResponse(players, safe=False)

def get_match(request):
    if not request.user.is_authenticated:
        return HttpResponse(f'User not signed in!')
    if request.user.player.match is None:
        return HttpResponse(f"0: No active match")

    match = request.user.player.match

    match = {
            "name": match.name,
            "host": match.host,
            "latitude": match.createdAtLocation.y,
            "longitude": match.createdAtLocation.x,
            "duration": match.duration,
            "radius": match.radius,
            "distance": distance(request.user.player.location, match.createdAtLocation).kilometers,
            "number_of_joined_players": match.player_set.count(),
            "number_of_hunters": match.numberOfHunters,
            "number_of_hiders": match.numberOfHiders
    }

    return JsonResponse(match, safe=False)


def end_match(request):
    if not request.user.is_authenticated:
        return HttpResponse(f'user not signed in')
    if request.method != 'POST':
        return HttpResponse(f'incorrect request method.')
    host_name = request.POST['host']
    host = Player.objects.get(user__username=host_name)
    if not hasattr(host, 'match'):
        return HttpResponse(f'no match with host {host_name} exists')
    host.match.is_over = True
    host.match.save()
    return HttpResponse(f'0: ended match')
