import json

from django.contrib.auth.models import User
from django.contrib.gis.geos import Point
from django.db.models import Q
from django.http import HttpResponse, JsonResponse

from .models import Player, Friendship, Match, FriendshipRequest
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm
from geopy.distance import distance, Distance
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist



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
        return HttpResponse(f'Could not authenticate.')
    login(request, user)
    return HttpResponse('1: successful signin')


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
    return HttpResponse('1: successful signup')

def is_host(request):
    if not request.user.is_authenticated:
        return HttpResponse(f'User not signed in!')

    if request.user.player.match is None:
        return HttpResponse("0: Not in a match")
    elif request.user.player.match.host is not request.user.username:
        return HttpResponse("0: Not a host")
    elif request.user.player.match.host == request.user.username:
        return HttpResponse("1: You are a host")

    return HttpResponse("0: Cannot decide if you are a host :?")

# FRIENDS LIST:
# view functions: get_names, get_friends, add_friend,
# helper functions: update_friendship_level, update_all_friendship_levels

def get_players(request):
    if not request.user.is_authenticated:
        return HttpResponse(f'User not signed in')

    non_friend_players = [player for player in Player.objects.all()
                          if not player.is_friend_with(request.user.player) and
                          not FriendshipRequest.objects.filter(Q(requester=request.user.player, recipient=player)
                                                               | Q(requester=player, recipient=request.user.player)).exists()]
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
    if not request.user.is_authenticated:
        return HttpResponse(f'User not signed in')

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
            "distance": round(distance(request.user.player.location, friend.location).kilometers, 2),
            "experience": request.user.player.get_experience_with(friend),
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
        duplicate_request_exist = FriendshipRequest.objects.filter(
            requester=recipient.player, recipient=requester.player
        ).exists()
        if duplicate_request_exist:
            duplicate_request = FriendshipRequest.objects.filter(requester=recipient.player, recipient=requester.player)
            duplicate_request.delete()
        return HttpResponse("1: Friendship request accepted successfully", status=200)
    else:
        frRe.decline()
        duplicate_request_exist = FriendshipRequest.objects.filter(
            requester=recipient.player, recipient=requester.player
        ).exists()
        if duplicate_request_exist:
            duplicate_request = FriendshipRequest.objects.filter(requester=recipient.player, recipient=requester.player)
            duplicate_request.delete()
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
            "hiding_duration": match.hiding_duration,
            "hint_interval_duration": match.hint_interval_duration,
            "distance": distance(request.user.player.location, match.createdAtLocation).kilometers,
            "number_of_joined_players": match.player_set.count(),
            "number_of_hunters": match.numberOfHunters,
            "number_of_hiders": match.numberOfHiders,
            "number_of_joined_hunters": Player.objects.filter(match=match, role='HU').count(),
            "number_of_joined_hiders": Player.objects.filter(match=match, role='HI').count()
        }
        for match in Match.objects.all()
    ]

    return JsonResponse(matches, safe=False)

def get_matches_nearby(request, radius):
    if not request.user.is_authenticated:
        return HttpResponse(f'user not signed in')

    radius.replace(',', '.')
    matches = [
        {
            "name": match.name,
            "host": match.host,
            "latitude": match.createdAtLocation.y,
            "longitude": match.createdAtLocation.x,
            "duration": match.duration,
            "hiding_duration": match.hiding_duration,
            "hint_interval_duration": match.hint_interval_duration,
            "distance": distance(request.user.player.location, match.createdAtLocation).kilometers,
            "number_of_joined_players": match.player_set.count(),
            "number_of_hunters": match.numberOfHunters,
            "number_of_hiders": match.numberOfHiders,
            "number_of_joined_hunters": Player.objects.filter(match=match, role='HU').count(),
            "number_of_joined_hiders": Player.objects.filter(match=match, role='HI').count()
        }
        for match in Match.objects.all() if distance(request.user.player.location, match.createdAtLocation).kilometers < float(radius)
                                            and match.has_started is False and match.is_full() is False
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
            "hiding_duration": match.hiding_duration,
            "hint_interval_duration": match.hint_interval_duration,
            "distance": distance(request.user.player.location, match.createdAtLocation).kilometers,
            "number_of_joined_players": match.player_set.count(),
            "number_of_hunters": match.numberOfHunters,
            "number_of_hiders": match.numberOfHiders,
            "number_of_joined_hunters": Player.objects.filter(match=match, role='HU').count(),
            "number_of_joined_hiders": Player.objects.filter(match=match, role='HI').count()
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
    name = data['name']
    latitude = float(data['latitude'])
    longitude = float(data['longitude'])
    duration = int(data['duration'])
    hiding_duration = int(data['hiding_duration'])
    hint_interval_duration = int(data['hint_interval_duration'])
    number_of_hunters = int(data['number_of_hunters'])
    number_of_hiders = int(data['number_of_hiders'])

    player = request.user.player

    if player.match is not None and player.match.host is player.user.username:
        match = Match.objects.get(host=request.user.username)
        match.delete()

    match = Match()
    match.host = player.user.username
    match.name = name
    match.createdAtLocation = Point(longitude, latitude)
    match.duration = duration
    match.hiding_duration = hiding_duration
    match.hint_interval_duration = hint_interval_duration
    match.numberOfHiders = number_of_hiders
    match.numberOfHunters = number_of_hunters
    match.save()
    player.match = match
    player.save()
    return HttpResponse(f'1: Created match')


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

def become_ready(request):
    if not request.user.is_authenticated:
        return HttpResponse(f'user not signed in')

    if request.user.player.match is None:
        return HttpResponse(f"0: No active match")

    request.user.player.ready = True
    request.user.player.save()
    return HttpResponse(f"1: You're ready!")

def become_unready(request):
    if not request.user.is_authenticated:
        return HttpResponse(f'user not signed in')

    if request.user.player.match is None:
        return HttpResponse(f"0: No active match")

    request.user.player.ready = False
    request.user.player.save()

    return HttpResponse(f"1: You're unready!")

def exit_match(request):
    if not request.user.is_authenticated:
        return HttpResponse(f'user not signed in')

    if request.user.player.match is None:
        return HttpResponse(f"0: No active match")
    else:
        request.user.player.role = None
        match = request.user.player.match
        request.user.player.match = None
        request.user.player.ready = False
        request.user.player.is_caught = False
        request.user.player.is_invisible = False
        request.user.player.is_loaded = False
        request.user.player.save()
        if match.player_set.count() == 0:
            match.delete()
            return HttpResponse('1: Exited and ended match')

        return HttpResponse(f'1: Exited match')

def get_players_in_current_match(request):
    if not request.user.is_authenticated:
        return HttpResponse(f'User not signed in!')
    if request.user.player.match is None:
        return HttpResponse(f"0: There is no active match!")

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


def get_match_afe(request):
    if not request.user.is_authenticated:
        return HttpResponse(f'user not signed in')
    if request.user.player.match is None:
        return HttpResponse(f"0: No active match")

    return HttpResponse(request.user.player.match.get_average_friendship_experience())

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
            "hiding_duration": match.hiding_duration,
            "hint_interval_duration": match.hint_interval_duration,
            "distance": distance(request.user.player.location, match.createdAtLocation).kilometers,
            "number_of_joined_players": match.player_set.count(),
            "number_of_hunters": match.numberOfHunters,
            "number_of_hiders": match.numberOfHiders,
            "number_of_joined_hunters": Player.objects.filter(match=match, role='HU').count(),
            "number_of_joined_hiders": Player.objects.filter(match=match, role='HI').count()
    }

    return JsonResponse(match, safe=False)

def start_match(request):
    if not request.user.is_authenticated:
        return HttpResponse(f'user not signed in')

    if request.user.player.match.player_set.count() < 2:
        return HttpResponse(f'0: Not enough players')

    request.user.player.match.has_started = True
    request.user.player.match.save()
    return HttpResponse(f'1: Started match')

def all_ready(request):
    if not request.user.is_authenticated:
        return HttpResponse(f'user not signed in')

    if request.user.player.match.player_set.count() < 2:
        return HttpResponse(f'0: Not enough players')

    if request.user.player.match.all_ready() is False:
        return HttpResponse(f'0: Not all players are ready')
    else:
        return HttpResponse(f'1: All players are ready! {request.user.player.match.player_set.count()}')

def end_match(request):

    try:
        match = Match.objects.get(host=request.user.username)
        match.delete()
        request.user.player.role = None
        request.user.player.match = None
        request.user.player.ready = False
        request.user.player.is_caught = False
        request.user.player.is_invisible = False
        request.user.player.is_loaded = False


        request.user.player.save()
        return HttpResponse('1: Match ended successfully')
    except ObjectDoesNotExist:
        return HttpResponse('0: No match found for the host')

def match_ended(request):
    if not request.user.is_authenticated:
        return HttpResponse(f'user not signed in')

    if request.user.player.match is None:
        return HttpResponse(f"1: Match was ended!")

    return HttpResponse(f"0: Match hasn't ended!")

def match_started(request):
    if not request.user.is_authenticated:
        return HttpResponse(f'user not signed in')

    if request.user.player.match is None:
        return HttpResponse(f"0: There is no active match!")

    if request.user.player.match.has_started:
        return HttpResponse(f"1: Match has started!")

    return HttpResponse(f"0: Match hasn't started!")

def join_hunter(request):
    if not request.user.is_authenticated:
        return HttpResponse(f'user not signed in')

    if request.user.player.match is None:
        return HttpResponse(f'Player not in match')
    if request.user.player.role == 'HU':
        return HttpResponse(f'0: Player already hunter')

    maxHunters = request.user.player.match.numberOfHunters
    joinedHunters = Player.objects.filter(match=request.user.player.match, role='HU').count()

    if joinedHunters < maxHunters:

        request.user.player.role = 'HU'
        request.user.player.save()
        return HttpResponse(f'1: Player is now hunter')
    else:
        return HttpResponse(f'0: Hunter slots are full')


def join_hider(request):
    if not request.user.is_authenticated:
        return HttpResponse(f'user not signed in')

    if request.user.player.match is None:
        return HttpResponse(f'Player not in match')

    if request.user.player.role == 'HI':
        return HttpResponse(f'0: Player already hider')

    maxHiders = request.user.player.match.numberOfHiders
    joinedHiders = Player.objects.filter(match=request.user.player.match, role='HI').count()

    if joinedHiders < maxHiders:
        request.user.player.role = 'HI'
        request.user.player.save()

        return HttpResponse(f'1: Player is now hunter')
    else:
        return HttpResponse(f'0: Hunter slots are full')

def get_hiders_locations(request):
    if not request.user.is_authenticated:
        return HttpResponse(f'0: User not signed in')

    if request.user.player.match is None:
        return HttpResponse(f'0: Player not in match')

    if request.user.player.role != "HU":
        return HttpResponse(f'0: Not a hunter')

    players = [
        {
            "latitude": player.location.y,
            "longitude": player.location.x,
        }
        for player in request.user.player.match.player_set.filter(role="HI", is_invisible=False)
    ]
    return JsonResponse(players, safe=False)

def get_hunters_locations(request):
    if not request.user.is_authenticated:
        return HttpResponse(f'0: User not signed in')

    if request.user.player.match is None:
        return HttpResponse(f'0: Player not in match')

    if request.user.player.role != "HI":
        return HttpResponse(f'0: Not a hider')

    players = [
        {
            "latitude": player.location.y,
            "longitude": player.location.x,
        }
        for player in request.user.player.match.player_set.filter(role="HU")
    ]
    return JsonResponse(players, safe=False)

def check_if_caught(request):
    if not request.user.is_authenticated:
        return HttpResponse(f'0: User not signed in')

    if request.user.player.match is None:
        return HttpResponse(f'0: Player not in match')

    if request.user.player.is_caught:
        return HttpResponse(f'1: You are caught')
    elif not request.user.player.is_caught:
        return HttpResponse(f'0: You are not caught')

def catch_hider(request, caught_player_username):
    if not request.user.is_authenticated:
        return HttpResponse(f'0: User not signed in')

    if request.user.player.match is None:
        return HttpResponse(f'0: Player not in match')

    if request.user.player.role != "HU":
        return HttpResponse(f'0: You are not Hunter!')

    try:
        caught_player = Player.objects.get(user__username=caught_player_username)
        caught_player.is_caught = True
        caught_player.save()
        return HttpResponse('1: Player caught successfully')
    except Player.DoesNotExist:
        return HttpResponse('0: Player not found')


def check_if_hider_nearby(request, max_radius_m):
    if not request.user.is_authenticated:
        return HttpResponse(f'0: User not signed in')

    if request.user.player.match is None:
        return HttpResponse(f'0: Player not in match')
    hiders = request.user.player.match.player_set.filter(role="HI", is_invisible=False)

    invisible_hiders = request.user.player.match.player_set.filter(role="HI", is_invisible=True)

    if hiders.count() == 0 and invisible_hiders.count() == 0:
        return HttpResponse(f"2: You win! No hiders!")

    maxNearestHiderDistance = 10000000
    nearestHider = None

    for hider in hiders:
        distanceToHider = distance(hider.location, request.user.player.location).meters
        if distanceToHider < maxNearestHiderDistance:
            nearestHider = hider
            maxNearestHiderDistance = distanceToHider

    if distance(nearestHider.location, request.user.player.location).meters <= float(max_radius_m):
        return HttpResponse(f"1:{nearestHider.user.username}")
    else:
        return HttpResponse(f"0: No hiders around you!")

def check_if_match_suddenly_ended(request):
    if not request.user.is_authenticated:
        return HttpResponse(f'0: User not signed in')

    if request.user.player.match is None:
        return HttpResponse(f'0: Player not in match')

    if request.user.player.role == "HI":
        if Player.objects.filter(match=request.user.player.match, role='HU').count() == 0:
            return HttpResponse("0: No hunters!?")
        # check if you game's ended for a hider

    if request.user.player.role == "HU":
        if Player.objects.filter(match=request.user.player.match, role='HI').count() == 0:
            return HttpResponse("0: No hiders!?")

    return HttpResponse("1: OK")


def get_server_time(request):
    server_time = timezone.localtime(timezone.now()).isoformat()
    return JsonResponse({'server_time': server_time})

def become_invisible(request):
    if not request.user.is_authenticated:
        return HttpResponse(f'0: User not signed in')

    if request.user.player.match is None:
        return HttpResponse(f'0: Player not in match')

    request.user.player.is_invisible = True
    request.user.player.save()
    return HttpResponse(f'1: Player is now invisible!')


def become_visible(request):
    if not request.user.is_authenticated:
        return HttpResponse(f'0: User not signed in')

    if request.user.player.match is None:
        return HttpResponse(f'0: Player not in match')

    request.user.player.is_invisible = False
    request.user.player.save()
    return HttpResponse(f'1: Player is now visible!')

def update_experience_with_friends(request, experience):
    if not request.user.is_authenticated:
        return HttpResponse(f'0: User not signed in')

    request.user.player.update_experience_with_friends(int(experience))
    request.user.player.save()
    return HttpResponse(f"1: Updated experience with friends!")

def clear_player(request):
    if not request.user.is_authenticated:
        return HttpResponse(f'0: User not signed in')

    if request.user.player.match is None:
        return HttpResponse(f'0: Player not in match')

    request.user.player.role = None
    match = request.user.player.match
    for match in Match.objects():
        if match.player_set.count() <= 1:
            match.delete()

    request.user.player.match = None
    request.user.player.ready = False
    request.user.player.is_caught = False
    request.user.player.is_invisible = False
    request.user.player.is_loaded = False
    request.user.player.save()

    return HttpResponse(f'1: Player cleared')

def is_loaded(request):
    if not request.user.is_authenticated:
        return HttpResponse(f'0: User not signed in')

    if request.user.player.match is None:
        return HttpResponse(f'0: Player not in match')

    request.user.player.is_loaded = True
    request.user.player.save()
    return HttpResponse(f'1: Player is loaded')


def all_loaded(request):
    if not request.user.is_authenticated:
        return HttpResponse(f'user not signed in')

    if request.user.player.match.player_set.count() < 2:
        return HttpResponse(f'0: Not enough players')

    if request.user.player.match.all_loaded() is False:
        return HttpResponse(f'0: Not all players are loaded')
    else:
        return HttpResponse(f'1: All players are loaded!')

