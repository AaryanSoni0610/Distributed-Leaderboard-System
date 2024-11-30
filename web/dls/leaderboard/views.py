from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
import requests, random, json
from django.contrib.sessions.models import Session

@login_required(login_url='/login/')
def add_player(request):
    if request.method == 'POST':
        players = request.POST.get('players')
        players = {'scores':json.loads(players)}
        for player in players['scores']:
            player['score'] = int(player['score'])
            player['player_name'] = player['name']
            del player['name']
        headers = {'Content-Type': 'application/json'}
        try:
            requests.post('http://localhost:8080/post_score/', json=players, headers=headers)
        except:
            print('Failed to add player(s)')
        return redirect('rankings')
    return render(request, 'leaderboard/addPlayer.html')

def rankings(request):
    regions = ['Global']
    try:
        available_regions = requests.get('http://localhost:8080/all-available-nodes')
        available_regions = available_regions.json()
    except:
        available_regions = []
    
    regions += available_regions
    try:
        selected_region = request.POST.get('region', 'Global')
    except:
        selected_region = 'Global'
    
    try:
        if selected_region == 'Global':
            data = requests.get('http://localhost:8080/get_scores/')
            data = data.json()
        else:
            data = requests.get(f'http://localhost:8080/get_scores/?region={selected_region}')
            data = data.json()
    except:
        data = {'scores':[]}
    
    scores = sorted(data['scores'], key=lambda x: x['score'], reverse=True)
    
    return render(request, 'leaderboard/Ranking.html', {'data':scores, 'regions':regions, 'selected_region': selected_region})

def login(request):
    if request.method == 'POST':
        uname = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=uname, password=password)
        if user is not None:
            auth_login(request, user)
            return redirect('/add-players/')
        else:
            return render(request, 'leaderboard/login.html', {'error': 'Invalid email or password'})
    return render(request, 'leaderboard/login.html')

def clear_sessions():
    Session.objects.all().delete()

clear_sessions()