from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse

def leaderboard(request):
    return render(request, 'leaderboard/gameRanking.html')

def rankings(request):
    return render(request, 'leaderboard/Ranking.html')

def login(request):
    return render(request, 'leaderboard/login.html')