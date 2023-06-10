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
    path('get_scores/', views.get_scores),
    path('edit_score/', views.edit_score),
    path('get_friends/', views.get_friends),
    path('get_players/', views.get_players),
    path('get_players_nearby/', views.get_players_nearby),
    path('send_friendship_request/', views.send_friendship_request),
    path('respond_friendship_request/', views.respond_friendship_request),
    path('get_friendship_requests/', views.get_friendship_requests),
    path('update_location/', views.update_location),
    path('get_match/', views.get_match),
    path('host_match/', views.host_match),
    path('join_match/', views.join_match),
    path('pass_ball/', views.pass_ball),
    path('end_match/', views.end_match),
]
