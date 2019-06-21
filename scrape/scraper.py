import io
import csv
import sys
import datetime
import logging
from datetime import date

import requests
import deathbycaptcha
from bs4 import BeautifulSoup

import config
from send_mail import send_email
from config import DBC_PASSWORD, DBC_USERNAME


headers = {
    "User-Agent":"Mozilla/5.0 (X11; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0"
}


""" Client for http://webapps.hcso.tampa.fl.us/ArrestInquiry """
class HillsClient(object):
    def __init__(self, start_date, days=1):
        """
        :start_date :: datetime.date, The first date for which arrest records
          are desired.
        :days :: int, The total number of days for which arrest records are
          desired. Use '1' if records for start_date only are desired.
        """
        self.session = requests.session()
        self.session.headers.update(headers)

        self.main_url = "https://webapps.hcso.tampa.fl.us/ArrestInquiry/"
        self.base_url = "https://webapps.hcso.tampa.fl.us"

        self.captcha_guid = None

        self.current_page = 1
        self.total_results = 0

        # Validate `days`
        if days < 1:
            raise ValueError("'days' must not be less than 1.")

        # Create a set of dates.
        self.dates = [start_date + datetime.timedelta(days=x) for x in range(0, days)]
    
    def get_date(self,days=0):
        today = date.today()

        dt_target = today  - datetime.timedelta(days=days)

        today_str = dt_target.strftime('%m/%d/%Y')

        return today_str

    def _load_cookies(self):
        ## Load ASP session id/ initial cookies
        r = self.session.get(self.main_url)
        soup = BeautifulSoup(r.content, "html.parser")

        try:
            cid = soup('input',id='captcha-guid')[0].attrs['value']
            self.captcha_guid = cid
        except:
            raise Exception("Couldn't set CAPTCHA id")

    def _get_captcha(self, captcha_id):
        url = "https://webapps.hcso.tampa.fl.us/ArrestInquiry/captcha.ashx?id=%s" % captcha_id
        r = self.session.get(url)
        with open('captcha.jpg','wb') as f:
            f.write(r.content)

    def _parse_detail_page(self,url):
        logging.info("Parsing details from: " + str(url))
        r = requests.get(url)
        soup = BeautifulSoup(r.content, "html.parser")
        base_div = soup('div', {'class', 'default-hcso-bg bordered pt-4 pb-4 pr-4 pl-4'})[1]

        return {
            'state': base_div('div', {'class', 'col-sm-6'})[1].text.replace('State: ', ''),
            'zip_code': base_div('div', {'class', 'col-sm-12'})[1].text.strip().replace('Zip:', '')
        }

        return { 'state':state,'zip_code':zip_code }

    def _parse_results(self, soup):
        out_records = []
        records = []
        record = []

        table = soup.table
        rows = table.tbody('tr')

        logging.debug("Preparing to parse table rows.")

        n = 0
        for r in rows:
            if 'table-separator' in r.attrs.get('class', ''):
                records.append(record)
                record = []
            else:
                record.append(r)

        logging.debug("Preparing to process records.")

        for i, record in enumerate(records):
            logging.debug("Processing record: " + str(i))
            d = {}
            name_parts = record[0].a.text.split(',')

            fname = name_parts[-1].title().split(' ')[0]
            lname = name_parts[0].title()

            d['fname'] = fname
            d['lname'] = lname

            tds = record[0].find_all('td')
            d['booking_num'] = tds[1].text
            d['agency'] = tds[2].text
            d['abn'] = tds[3].text
            d['personal'] = tds[4].text

            tds = record[1].find_all('td')
            d['street'] = tds[0].text.replace('ADDRESS: ', '')
            d['city'] = tds[1].text.replace('CITY: ', '')
            d['state'] = tds[2].text.replace('POB: ', '')

            tds = record[2].find_all('td')
            d['soid'] = tds[2].text.replace('SOID: ', '')

            charges = [ii.find_all('td')[1].text for ii in record[3].table.tbody('tr')]
            d['charges'] = '\n'.join(charges)

            detail_link = self.base_url + record[0].a['href']
            d.update(self._parse_detail_page(detail_link))

            out_records.append(d)
        
        return out_records

    def search_arrests(self, captcha_text, date):
        """
        :captcha_text :: string, text found in CAPTCHA image.
        :date :: datetime.date, the date for which to retrieve arrests.
        """

        # Format the date for the payload.
        formatted_date = date.strftime('%m/%d/%Y')

        payload = {
            "SearchBookingNumber": '',
            "SearchName": '',
            "SearchBookingDate": formatted_date,
            "SearchReleaseDate": '',
            "SearchRace": '',
            "SearchSex": '',
            "SearchDOB": '',
            "SearchCurrentInmatesOnly": "false",
            "SearchIncludeDetails": "false",
            "SearchSortType": "BOOKNO",
            "captcha-guid": self.captcha_guid,
            "captcha": captcha_text,
            "SearchIncludeDetails": "true",
            "SearchResults.CurrentPage": self.current_page,
            "SearchResults.PageSize": "200"
        }

        logging.info("Searching for arrests for " + str(date))

        r = self.session.post(self.main_url, payload, headers=headers)

        return r.content

    def run(self):
        """
        Main entry point to functionality.
        Returns an array of arrest records.
        """
        self._load_cookies()
        self._get_captcha(self.captcha_guid)
        dbc_client = deathbycaptcha.HttpClient(DBC_USERNAME, DBC_PASSWORD)

        captcha_res = dbc_client.decode('captcha.jpg')
        captcha_text = captcha_res['text']
        logging.info("CAPTCHA text: " + captcha_text)

        all_recs = []
        for date in self.dates:
            # Parsing intermittently fails with a AttributeErrorException
            # because 'soup' does not have an HTML table as expected. This while
            # loop keeps trying until there is not exception.
            while True:
                try:
                    search_res = self.search_arrests(captcha_text, date=date)
                    soup = BeautifulSoup(search_res, "html.parser")
                    recs = self._parse_results(soup)
                    all_recs += recs
                except:
                    continue
                break

        return all_recs


def write_csv(file_like, content):
    """
    :file_like A file-like object to write CSV data to.
    :content An array of objects to be converted and written to CSV.
    """
    # First, write data to a StringIO (we're ignoring the file-like passed in for now).
    f = io.StringIO()
    headers = ['fname', 'lname', 'street', 'city', 'state', 'zip_code', 'charges',
               'booking_num', 'agency', 'soid', 'personal', 'abn']
    csvw = csv.DictWriter(f,fieldnames=headers)
    csvw.writeheader()
    csvw.writerows(content)

    # Get string value.
    contentStrTmp = f.getvalue()

    # Convert to lines.
    lines = contentStrTmp.splitlines()

    # Replace the header.
    newHeader = ','.join(['First Name', 'Last Name', 'Street', 'City', 'State',
                          'Zip', 'Charges', 'Booking #', 'Agency', 'SOID', 
                          'Personal', 'ABN'])
    lines[0] = newHeader

    # Concatenate the lines back together.
    contentStr = "\n".join(lines)

    # And add a newline at the end.
    contentStr += "\n"

    # Write contentStr to the given file-like.
    file_like.write(contentStr)


def main():
    # Create the client
    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    hc = HillsClient(yesterday, days=2)

    # File names
    fname = str(hc.get_date()).replace('/','-')
    fname_csv = fname + '.csv'
    fname_log = fname + '.log'

    # Logging
    level = logging.DEBUG
    root = logging.getLogger()
    root.setLevel(level)

    # Run the scraper.
    all_recs = hc.run()

    # Write the arrest records to file.
    with open(fname_csv, "w") as f:
        write_csv(f, all_recs)

    # Send the email with results attached.
    send_email(config.EMAIL_TO, subject="Hillsborough County Arrests", attachment=fname_csv)


if __name__ == '__main__':
    try:
        main()
    except:
        main()
