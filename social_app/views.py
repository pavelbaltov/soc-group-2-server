import json

from django.contrib.auth.models import User
from django.contrib.gis.geos import Point
from django.http import HttpResponse, JsonResponse

from .models import Player, Friendship, Match, FriendshipRequest
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm
from geopy.distance import distance


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
    #Commented for testing purposes
    # if not request.user.is_authenticated:
    #     return HttpResponse(f'User not signed in')
    players = [
        {
            "id": player.user.id,
            "username": player.user.username,
            "role": player.role,
            "latitude": player.location.y,
            "longitude": player.location.x
        }
        for player in Player.objects.all()
    ]

    return JsonResponse(players, safe=False)

def get_players_nearby(request):
    # Commented for testing purposes
    # if not request.user.is_authenticated:
    #       return HttpResponse(f'User not signed in')

    data = json.loads(request.body)
    latitude = float(data['latitude'])
    longitude = float(data['longitude'])
    radius = float(data['radius'])

    if latitude is None or longitude is None or radius is None:
        return JsonResponse({'error': 'Missing required fields'}, status=400)

    current_location = Point(longitude, latitude)

    players = [
        {
            "id": player.user.id,
            "username": player.user.username,
            "role": player.role,
            "latitude": player.location.y,
            "longitude": player.location.x
        }
        for player in Player.objects.all() if distance(current_location, player.location).kilometers < radius
    ]

    return JsonResponse(players, safe=False)

def get_friends(request):
    # Commented for testing purposes
    #if not request.user.is_authenticated:
    #   return HttpResponse(f'user not signed in')
    #if not hasattr(request.user, 'player'):
    #    return HttpResponse(f'user is not a player')

    friends = [
        {
            "id": friend.user.id,
            "username": friend.user.username,
            "role": friend.role,
            "latitude": friend.location.y,
            "longitude": friend.location.x
        }
        for friend in request.user.player.get_friends()
    ]

    return JsonResponse(friends, safe=False)

def send_friendship_request(request):
    # Commented for testing purposes
    # if not request.user.is_authenticated:
    #   return HttpResponse(f'user not signed in')
    # if not hasattr(request.user, 'player'):
    #    return HttpResponse(f'user is not a player')

    data = json.loads(request.body)
    to_user_id = data['to_user']

    requester = request.user
    recipient = User.objects.get(username=to_user_id)

    #check if such players exists

    existing_request = FriendshipRequest.objects.filter(
        player=requester.player, friend=recipient.player
    ).exists()

    if existing_request:
        return JsonResponse({'0': 'Friendship request already sent'}, status=400)

    # Create a new friendship request
    frRe = FriendshipRequest(player=requester.player, friend=recipient.player,is_accepted = False)
    frRe.save()

    return JsonResponse({'1': 'Friendship request sent successfully'})

def respond_friendship_request(request):
    # Commented for testing purposes
    # if not request.user.is_authenticated:
    #   return HttpResponse(f'user not signed in')
    # if not hasattr(request.user, 'player'):
    #    return HttpResponse(f'user is not a player')

    data = json.loads(request.body)
    from_user = data['from_user']
    to_user_id = data['to_user']
    response = bool(data['response'])

    requester = User.objects.get(username=from_user)
    recipient = User.objects.get(username=to_user_id)

    existing_request = FriendshipRequest.objects.filter(
        player=requester.player, friend=recipient.player
    ).exists()

    if not existing_request:
        return JsonResponse({'0': 'Friendship request doesn\'t exist'}, status=400)

    frRe = FriendshipRequest.objects.get(player=requester.player, friend=recipient.player)
    if response:
        frRe.accept()
    else:
        frRe.decline()


def update_friendship_level(friendship):
    # This function basically counts mutual friends. Don't worry about the
    # specifics, just write your own code for whatever network calculations
    # you want to include in your game. If you are lost, the Django
    # documentation is very helpful.
    level = 0
    for f in friendship.player.friends.all():
        level += f.friend.followers.filter(player=friendship.friend).count()
    friendship.level = level
    friendship.save()


def update_all_friendship_levels():
    for friendship in Friendship.objects.all():
        update_friendship_level(friendship)


# LEADERBOARD: get_scores, edit_score

def get_scores(request):
    if not request.user.is_authenticated:
        return HttpResponse(f'user not signed in')
    response = '0: '
    # Iterates over all players
    for player in Player.objects.all():
        # Remember you can't do player.username because the player does not
        # have a username, only the player's user.
        response += f'{player.user.username} {player.score},'
    # Removes the trailing comma left by the above iteration
    response = response[:-1]
    return HttpResponse(response)


def edit_score(request):
    if not request.user.is_authenticated:
        return HttpResponse('user not signed in')
    if request.method != 'POST':
        return HttpResponse('incorrect request method')
    # Get the score
    score = request.POST['score']
    # Change the player's score
    request.user.player.score = int(score)
    # Save that change
    request.user.player.save()
    response = f'0: changed the score of {request.user.username} to {score}'
    return HttpResponse(response)


# TILTBALL: host_match, join_match, get_match, pass_ball, end_match

def host_match(request):
    if not request.user.is_authenticated:
        return HttpResponse(f'user not signed in')
    if not hasattr(request.user, 'player'):
        return HttpResponse(f'user is not a player')

    player = request.user.player
    if hasattr(player, 'match'):
        # The player has at some point hosted a match, so this is reset to
        # its initial state.
        player.match.host_has_ball = False
        player.match.has_started = False
        player.match.is_over = False
        player.match.position = 0
        player.match.save()
        return HttpResponse(f'0: reset match')
    else:
        # The player has never hosted a match, so the default values of the
        # newly created match are already correct.
        match = Match(host=player)
        match.save()
        return HttpResponse(f'0: created match')


def join_match(request):
    if not request.user.is_authenticated:
        return HttpResponse(f'user not signed in')
    if request.method != 'POST':
        return HttpResponse(f'incorrect request method.')

    host_name = request.POST['host']
    host = Player.objects.get(user__username=host_name)
    if hasattr(host, 'match'):
        host.match.host_has_ball = True
        host.match.has_started = True
        host.match.save()
        return HttpResponse(f'0: joined match, started match')
    else:
        return HttpResponse(f'no match with host {host_name} exists')


def get_match(request):
    if not request.user.is_authenticated:
        return HttpResponse(f'user not signed in')
    if request.method != 'POST':
        return HttpResponse(f'incorrect request method.')

    host_name = request.POST['host']
    # Keyword attributes are very powerful. Look at the Django documentation
    # for more details. This line fetches the player that has a user that
    # has a username that equals name. The __ is equivalent to a dot.
    # user.username in regular code becomes the user__username parameter of
    # the get function. Remember: players don't have usernames, only the
    # players' users have usernames.
    host = Player.objects.get(user__username=host_name)

    if not hasattr(host, 'match'):
        return HttpResponse(f'no match with host {host_name} exists')
    if not host.match.has_started:
        return HttpResponse(f'match has not started')
    if host.match.is_over:
        return HttpResponse(f'2: match is over')
    match_ball = f'{host.match.position} '
    match_ball += f'{host.match.velocity_x} '
    match_ball += f'{host.match.velocity_y}'
    if host.match.host_has_ball:
        return HttpResponse(f'0: {match_ball}')
    else:
        return HttpResponse(f'1: {match_ball}')


def pass_ball(request):
    if not request.user.is_authenticated:
        return HttpResponse(f'user not signed in')
    if request.method != 'POST':
        return HttpResponse(f'incorrect request method.')

    host_name = request.POST['host']
    host_has_ball = request.POST['host_has_ball'] == "true"
    position = request.POST['position']
    velocity_x = request.POST['velocity_x']
    velocity_y = request.POST['velocity_y']

    host = Player.objects.get(user__username=host_name)
    if not hasattr(host, 'match'):
        return HttpResponse(f'no match with host {host_name} exists')

    host.match.host_has_ball = host_has_ball
    host.match.position = position
    host.match.velocity_x = velocity_x
    host.match.velocity_y = velocity_y
    host.match.save()
    return HttpResponse(f'0: passed ball')


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
