import csv
import sys
import requests
from bs4 import BeautifulSoup
import deathbycaptcha
from config import DBC_PASSWORD, DBC_USERNAME
import config
from datetime import date
import datetime
from send_mail import send_email
import logging
import io

headers = {
    "User-Agent":"Mozilla/5.0 (X11; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0"
}


""" Client for http://webapps.hcso.tampa.fl.us/ArrestInquiry """
class HillsClient(object):
    def __init__(self, start_date, days = 1):
        """
        :start_date :: datetime.date, The first date for which arrest records are desired.
        :days :: int, The number of days after start_date for wich arrest
              records are desired. Use '1' if records for start_date only are desired.
        """
        self.session = requests.session()
        self.session.headers.update(headers)

        self.main_url = "http://webapps.hcso.tampa.fl.us/ArrestInquiry/"
        self.base_url = "http://webapps.hcso.tampa.fl.us"

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
        url = "http://webapps.hcso.tampa.fl.us/ArrestInquiry/captcha.ashx?id=%s" % captcha_id
        r = self.session.get(url)
        with open('captcha.jpg','wb') as f:
            f.write(r.content)

    def _parse_detail_page(self,url):
        logging.info("Parsing details from: " + str(url))
        r = requests.get(url)
        soup = BeautifulSoup(r.content, "html.parser")
        address_table = soup('a',{"name":'Address'})[0].findNext('table')
        address_str = ','.join([x.text.strip() for x in address_table('td')])

        street, city, state, zip_code = address_str.split(',')

        return {'street':street.title(), 'city': city.title(), 'state':state,'zip_code':zip_code}

    def _parse_results(self, soup):
        out_records = []
        records = []
        record = []

        prev_row_status = 'RowOn'
        table = soup.table
        rows = table.tbody('tr')

        logging.info("Preparing to parse table rows.")

        n = 0
        for r in rows:
            row_status = [x for x in r.attrs['class'] if x][0]
            if row_status != prev_row_status: ## New entry
                records.append(record)
                record = [r]
            else:
                record.append(r)

            prev_row_status = row_status

        logging.info("Preparing to process records.")
        for i, record in enumerate(records):
            logging.info("Processing record: " + str(i))
            d = {}
            charges = []
            name_parts = record[0].a.text.split(',')

            fname = name_parts[-1].title().split(' ')[0]
            lname = name_parts[0].title()

            d['fname'] = fname
            d['lname'] =  lname

            detail_link = self.base_url + record[0].a['href']

            d.update(self._parse_detail_page(detail_link))

            for i, row in enumerate(record):
                logging.info("Processing row: " + str(i))
                try:
                    charge = row('td')[2].text.strip()
                    if charge and not charge.startswith('POB:') and not charge.startswith('SOID:'):
                        logging.info("Appending a charge: " + str(charge))
                        charges.append(charge)
                    else:
                        logging.info("Skipping charge in row: " + str(i))
                except:
                    pass

            charges = [ x for x in charges if x.strip()]
            
            try:
                d['charge1'] = charges[0]
            except:
                d['charge1'] = ''
            try:
                d['charge2'] = charges[1]
            except:
                d['charge2'] = ''
            try:
                d['charge3'] = charges[2]
            except:
                d['charge3'] = ''

            
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
            "captcha-guid": self.captcha_guid,
            "captcha": captcha_text,
            "SearchCurrentInmatesOnly": "false",
            "SearchIncludeDetails": "false",
            "SearchSortType": "BOOKNO",
            "SearchResults.PageSize": "200",
            "SearchIncludeDetails": "true",
            "SearchResults.CurrentPage": self.current_page
        }

        logging.info("Searching for arrests for " + str(date))

        r = self.session.post(self.main_url, payload,headers=headers)

        return r.content

        soup = BeautifulSoup(r.content, "html.parser")
        try:
            total_results = int(soup('span',class_='paginationLeft')[0].text.strip().split(' of ')[-1])
            self.total_results = total_results
        except:
            pass

        return r

    def run(self):
        """
        Main entry point to functionality.
        Returns an array of arrest records.
        """
        self._load_cookies()
        self._get_captcha(self.captcha_guid)
        dbc_client = deathbycaptcha.HttpClient(DBC_USERNAME,DBC_PASSWORD)

        captcha_res = dbc_client.decode('captcha.jpg')
        captcha_text = captcha_res['text']
        logging.info("CAPTCHA text: " + captcha_text)

        all_recs = []
        for date in self.dates:
            search_res = self.search_arrests(captcha_text,date=date)
            soup = BeautifulSoup(search_res, "html.parser")
            recs = self._parse_results(soup)
            all_recs += recs

        return all_recs

def write_csv(file_like, content):
    """
    :file_like A file-like object to write CSV data to.
    :content An array of objects to be converted and written to CSV.
    """
    # First, write data to a StringIO (we're ignoring the file-like passed in for now).
    f = io.StringIO()
    headers = ['fname','lname','street','city','state','zip_code','charge1','charge2','charge3']
    csvw = csv.DictWriter(f,fieldnames=headers)
    csvw.writeheader()
    csvw.writerows(content)

    # Get string value.
    contentStrTmp = f.getvalue()

    # Convert to lines.
    lines = contentStrTmp.splitlines()

    # Replace the header.
    newHeader = ','.join(['First Name','Last Name', 'Street','City','State','Zip','Charge1','Charge2','Charge3'])
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
    hc = HillsClient(yesterday, days = 2)

    # File names
    fname = str(hc.get_date()).replace('/','-')
    fname_csv = fname + '.csv'
    fname_log = fname + '.log'

    # Logging
    level = logging.DEBUG
    root = logging.getLogger()
    root.setLevel(level)
    #formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # fh = logging.FileHandler(fname_log)
    # fh.setLevel(level)
    # fh.setFormatter(formatter)
    # ch = logging.StreamHandler(sys.stdout)
    # ch.setLevel(level)
    # ch.setFormatter(formatter)
    # root.addHandler(ch)
    #root.addHandler(fh)

    all_recs = hc.run()

    with open(fname_csv, "w") as f:
        write_csv(f, all_recs)

    send_email(config.EMAIL_TO, subject="Hillsborough County Arrests",attachment=fname_csv)

if __name__ == '__main__':
    try:
        main()
    except:
        main()

