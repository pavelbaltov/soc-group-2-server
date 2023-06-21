from django.urls import path

from . import views

# More complex URL-patterns can be found in the Django documentation,
# but since these URLs will be accessed by the client automatically rather
# than a user, they can be kept very straightforward.
urlpatterns = [
    path('signup/', views.signup),
    path('login/', views.signin),
    path('logout/', views.signout),
    path('check_auth/', views.check_auth),

    path('get_players/', views.get_players),
    path('get_players_nearby/<str:radius>/', views.get_players_nearby),
    path('get_player_by_username/<str:username>/', views.get_player_by_username),

    path('get_friends/', views.get_friends),
    path('send_friendship_request/<str:username>/', views.send_friendship_request),
    path('respond_friendship_request/', views.respond_friendship_request),
    path('get_friendship_requests/', views.get_friendship_requests),
    path('remove_friend/', views.remove_friend),

    path('update_location/', views.update_location),

    path('get_matches/', views.get_matches),
    path('get_matches_nearby/<str:radius>/', views.get_matches_nearby),
    path('get_matches_of_friends/', views.get_matches_of_friends),
    path('host_match/', views.host_match),
    path('join_match/', views.join_match),
    path('end_match/', views.exit_match),
    path('get_players_in_current_match/', views.get_players_in_current_match),

    path('end_match/', views.end_match),
]
