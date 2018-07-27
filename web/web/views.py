from django.http import HttpResponse
from django.shortcuts import render

def index(request):
    return render(request, 'index.html', content_type='text/html')

def arrests(request):
    frm = request.GET.get('from', None)
    to = request.GET.get('to', None)
    return HttpResponse("You selected from: " + frm + " and to: " + to)
