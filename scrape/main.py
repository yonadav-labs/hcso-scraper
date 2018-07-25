import csv
import sys
import requests
from bs4 import BeautifulSoup
import deathbycaptcha
from config import DBC_PASSWORD, DBC_USERNAME
import config
from datetime import date
import datetime
from send_mail import  send_email


headers = {
    "User-Agent":"Mozilla/5.0 (X11; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0"
}


""" Client for http://webapps.hcso.tampa.fl.us/ArrestInquiry """
class HillsClient(object):
    def __init__(self):
        self.session = requests.session()
        self.session.headers.update(headers)

        self.main_url = "http://webapps.hcso.tampa.fl.us/ArrestInquiry/"
        self.base_url = "http://webapps.hcso.tampa.fl.us"

        self.captcha_guid = None

        self.current_page = 1
        self.total_results = 0

    
    def get_date(self,days=0):
        today = date.today()

        dt_target = today  - datetime.timedelta(days=days)

        today_str = dt_target.strftime('%m/%d/%Y')

        return today_str



    def _load_cookies(self):
        ## Load ASP session id/ initial cookies
        r = self.session.get(self.main_url)
        soup = BeautifulSoup(r.content)

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
        r = requests.get(url)
        soup = BeautifulSoup(r.content)
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

        n = 0
        for r in rows:
            row_status = [x for x in r.attrs['class'] if x][0]
            if row_status != prev_row_status: ## New entry
                records.append(record)
                record = [r]
            else:
                record.append(r)

            prev_row_status = row_status

        for record in records:
            d = {}
            charges = []
            name_parts = record[0].a.text.split(',')

            fname = name_parts[-1].title().split(' ')[0]
            lname = name_parts[0].title()

            d['fname'] = fname
            d['lname'] =  lname

            detail_link = self.base_url + record[0].a['href']

            d.update(self._parse_detail_page(detail_link))

            for row in record:
                try:
                    charge = row('td')[2].text.strip()
                    if not charge.startswith('POB:') and not charge.startswith('SOID:'):
                        charges.append(charge)
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
        payload = {
            "SearchBookingNumber": '',
            "SearchName": '',
            "SearchBookingDate": date,
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

        r = self.session.post(self.main_url, payload,headers=headers)

        return r.content

        soup = BeautifulSoup(r.content)
        try:
            total_results = int(soup('span',class_='paginationLeft')[0].text.strip().split(' of ')[-1])
            self.total_results = total_results
        except:
            pass

        return r

def write_csv(fname, content):
    headers = ['fname','lname','street','city','state','zip_code','charge1','charge2','charge3']
    with open(fname,'w') as f:
        csvw = csv.DictWriter(f,fieldnames=headers)
        csvw.writeheader()
        csvw.writerows(content)

    ## rewrite header
    with open(fname,'r') as in_file:
        lines = in_file.readlines()
        lines[0] = ','.join(['First Name','Last Name', 'Street','City','State','Zip','Charge1','Charge2','Charge3']) + "\n"
        
        with open(fname,'w') as out_file:
            for line in lines:
                out_file.write(line)



def main():

    hc = HillsClient()
    hc._load_cookies()
    vc = hc._get_captcha(hc.captcha_guid)
    dbc_client = deathbycaptcha.HttpClient(DBC_USERNAME,DBC_PASSWORD)

    captcha_res = dbc_client.decode('captcha.jpg')
    captcha_text = captcha_res['text']

    today, yesterday = hc.get_date(), hc.get_date(days=1)

    all_recs = []
    for date in [today, yesterday]:
        search_res = hc.search_arrests(captcha_text,date=date)

        soup = BeautifulSoup(search_res)
        recs = hc._parse_results(soup)
        all_recs += recs


    fname_out = str(hc.get_date()).replace('/','-') + '.csv'

    write_csv(fname_out, all_recs)

    send_email(config.EMAIL_TO, subject="Hillsborough County Arrests",attachment=fname_out)

if __name__ == '__main__':
    try:
        main()
    except:
        main()

