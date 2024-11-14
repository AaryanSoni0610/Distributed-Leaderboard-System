from django.urls import path
from leaderboard import views as lb_views

urlpatterns = [
    path('rankings/', lb_views.rankings),
    path('leaderboard/', lb_views.leaderboard),
    path('login/', lb_views.login),
]