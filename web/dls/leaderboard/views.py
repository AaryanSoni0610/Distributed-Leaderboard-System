from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
import requests, random

def add_player(request):
    return render(request, 'leaderboard/addPlayer.html')

def rankings(request):
    
    # regions = requests.get('http://localhost:8080/get-available-regions/')
    # regions = regions.json()
    # print(regions)
    
    regions = ['Global', 'Hyderabad', 'Goa', 'Pilani']
    
    # data = requests.get('http://localhost:8080/get-leaderboard/')
    # data = data.json()
    # print(data)
    
    # create 40 random entries
    data = [
        {'name': 'Player'+str(i+1), 'score': random.randint(1, 100), 'region': regions[random.randint(0, 3)]} for i in range(40)
    ]
    # assign rank after data is sorted
    data = sorted(data, key=lambda x: x['score'], reverse=True)
    for i in range(len(data)):
        data[i]['rank'] = i+1
    
    return render(request, 'leaderboard/Ranking.html', {'data':data, 'regions':regions})

def login(request):
    return render(request, 'leaderboard/login.html')