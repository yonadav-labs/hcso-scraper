from django.http import HttpResponse
from django.shortcuts import render
import datetime
import scraper
import io

def index(request):
    return render(request, 'index.html', content_type='text/html')

def arrests(request):
    frmStr = request.GET.get('from', None)
    toStr = request.GET.get('to', None)

    # Create the start date and number of days desired from input.
    frmDate = fromIsoFormat(frmStr)
    toDate = fromIsoFormat(toStr)
    interval = toDate - frmDate
    days = interval.days + 1

    # Get arrest records.
    hc = scraper.HillsClient(frmDate, days)
    arrests = hc.run()

    # Convert arrests to CSV string.
    csv = ""
    with io.StringIO() as f:
        scraper.write_csv(f, arrests)
        csv = f.getvalue()

    # Create the response.
    response = HttpResponse(csv, content_type="application/csv")

    # Set the header for file download.
    response["Content-Disposition"] = "attachment; filename=arrests.csv"

    return response

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
