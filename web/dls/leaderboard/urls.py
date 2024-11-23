from django.urls import path
from leaderboard import views as lb_views

urlpatterns = [
    path('rankings/', lb_views.rankings),
    path('add-players/', lb_views.add_player),
    path('login/', lb_views.login),
]