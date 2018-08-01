from django.http import HttpResponse
from django.shortcuts import render
import datetime

def index(request):
    return render(request, 'index.html', content_type='text/html')

def arrests(request):
    frmStr = request.GET.get('from', None)
    toStr = request.GET.get('to', None)

    frmDate = fromIsoFormat(frmStr)
    toDate = fromIsoFormat(toStr)

    return HttpResponse("You selected from: " + str(frmDate) + " and to: " + str(toDate))
    #return HttpResponse("You selected from: " + frmStr + " and to: " + toStr)

def fromIsoFormat(dateStr):
    """
    Return a date corresponding to a date_string in the format emitted by
    date.isoformat(). Specifically, this function supports strings in the
    format(s) YYYY-MM-DD.

    """
    parts = dateStr.split('-')
    year = int(parts[0])
    month = int(parts[1])
    day = int(parts[2])

    return datetime.date(year, month, day)
