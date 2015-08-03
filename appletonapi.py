"""
Copyright (c) 2015 Mike Putnam <mike@theputnams.net>

Permission to use, copy, modify, and distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
"""

from datetime import datetime, timedelta
from google.appengine.api import memcache
from google.appengine.api import namespace_manager
from google.appengine.api import urlfetch
import inflect
import json
import logging
import lxml.etree
import lxml.html
import os
import re
import streetaddress
import urllib
import urllib2
import webapp2

DATE_FORMAT = "%Y-%m-%d"

_digits = re.compile('\d')
def contains_digits(d):
    return bool(_digits.search(d))


def extracttagvalues(line):
    m = re.search('(?<=value\=\").*?([^\'" >]+)', line)
    if m:
        return re.split('value="', m.group(0))[0]


def sanitizeinputwords(rawinput):
    m = re.search('^\w+$', rawinput)
    if m:
        return m.group(0)

class BaseHandler(webapp2.RequestHandler):
    def write_response(self, response):
        if response.has_key('error'):
            self.response.out.write(response['error'])
        else:
            self.response.headers["Content-Type"] = "application/json"
            self.response.headers["Access-Control-Allow-Origin"] = "*"
            self.response.out.write(json.dumps(response['result'], sort_keys=True, indent=4, separators=(',', ': ')))


class PropertyHandler(BaseHandler):
    def get(self, propkey):
        return self.write_response(self.execute(propkey))
    
    def execute(self, propkey):
        propkey = sanitizeinputwords(propkey)
        major_ver, minor_ver = os.environ.get('CURRENT_VERSION_ID').rsplit('.', 1)
        namespace_manager.set_namespace(major_ver)
        logging.debug("namespace: " + major_ver)
        p = memcache.get(propkey)
        if p is not None:
            logging.debug("from memcache: " + propkey)
            return { 'result' : p }
        else:
            detailurl = "http://my.appleton.org/Propdetail.aspx?PropKey=" + str(propkey)
            datagroups = []
            try:
                docroot = lxml.html.fromstring(urllib2.urlopen(detailurl).read())
                tables = docroot.xpath("//table[@class='t1']")
                for table in tables:
                    ths = table.xpath("./tr/th")  # assuming single <th> per table
                    for th in ths:
                        if th is not None:
                            lxml.etree.strip_tags(th, 'a', 'b', 'br', 'span', 'strong')
                            if th.text:
                                thkey = re.sub('\W', '', th.text).lower()  # nospaces all lower
                                datagroups.append(thkey)
                                if th.text.strip() == "Businesses":
                                    logging.debug("found Business <th>")
                                    tdkey = "businesses"
                                    businesslist = []
                                    tds = table.xpath("./tr/td")
                                    if tds is not None:
                                        for td in tds:
                                            lxml.etree.strip_tags(td, 'a', 'b', 'br', 'span', 'strong')
                                            businesslist.append(td.text.strip())
                                    logging.debug("businesslist: " + str(businesslist))
                                datadict = {}
                                tdcounter = 0
                                tds = table.xpath("./tr/td")
                                if tds is not None:
                                    for td in tds:
                                        lxml.etree.strip_tags(td, 'a', 'b', 'br', 'span', 'strong')
                                        if tdcounter == 0:
                                            tdkey = re.sub('\W', '', td.text).lower() if td.text else ''
                                            tdcounter += 1
                                        else:
                                            tdvalue = td.text.strip().title() if td.text else ''
                                            tdvalue = " ".join(tdvalue.split())  # remove extra whitespace
                                            tdcounter = 0
                                            # when the source tr + td are commented out lxml still sees them. PREVENT!
                                            if tdkey == '' and tdvalue == '':
                                                break
                                            else:
                                                datadict[tdkey] = tdvalue
                                    datagroups.append(datadict)
                logging.debug("setting memcache for key: " + propkey)
                memcache.add(str(propkey), datagroups)
                return { 'result' : datagroups }
            except urllib2.HTTPError, response:
                return { 'error' : 'error - Scrape: ' + str(response) }


class SearchHandler(BaseHandler):
    def get(self):
        return self.write_response(self.execute(self.request.get('q'), str(self.request.headers['User-Agent'])))

    def execute(self, search_input, user_agent):
        # Google maps geolocation appends 'USA' but the address parser can't cope
        search_input = search_input.replace('USA','')
        addr = streetaddress.parse(search_input)
        if addr is None:
            # Since we are so tightly coupled with Appleton data, let's just pacify the address parser
            addr = streetaddress.parse(search_input + ' Appleton, WI')
        housenumber = addr['number']
        # Handle upstream requirement of "Fifth" not "5th"
        p = inflect.engine()
        if contains_digits(addr['street']):
            street = p.number_to_words(addr['street'])
        else:
            street = addr['street']

        if not housenumber and not street:
            return { 'error' : 'Give me *SOMETHING* to search for.'}

        try:
            response = urllib2.urlopen('http://my.appleton.org/')
            for line in response:
                if "__VIEWSTATE\"" in line:
                    vs = extracttagvalues(line)
                if "__EVENTVALIDATION\"" in line:
                    ev = extracttagvalues(line)
                    formvalues = {
                        '__EVENTTARGET': '',
                        '__EVENTARGUMENT': '',
                        '__VIEWSTATE': vs,
                        '__EVENTVALIDATION': ev,
                        'ctl00$myappletonContent$txtStreetNumber': housenumber,
                        'ctl00$myappletonContent$txtStreetName': street,
                        'ctl00$myappletonContent$btnSubmit': 'Submit'}
                    headers = {
                        'User-Agent': user_agent,
                        'Referer': 'http://my.appleton.org/default.aspx',
                        'Accept': 'text/html,application/xhtml+xml,application/xml'
                    }
                    data = urllib.urlencode(formvalues)
                    req = urllib2.Request("http://my.appleton.org/default.aspx", data, headers)
                    response = urllib2.urlopen(req)
                    allresults = []
                    # Example of the HTML returned...
                    # <a id="ctl00_myappletonContent_searchResults_ctl03_PropKey"
                    # href="Propdetail.aspx?PropKey=312039300&amp;Num=100">312039300  </a>
                    #                  </td><td>100</td><td>E WASHINGTON           ST  </td>
                    for pline in response:
                        if "Propdetail.aspx?PropKey=" in pline:
                            searchresult = []
                            m = re.search('(?<=PropKey\=).*(?=&)', pline)
                            if m:
                                searchresult.append(re.split('PropKey=', m.group(0))[0])
                            m = re.findall('(?s)<td>(.*?)</td>', response.next())
                            if m:
                                # this removes whitespace and Title Cases the address
                                # given: <td>1200</td><td>W WISCONSIN    AVE </td>
                                # returns: ['1200', 'W Wisconsin Ave']
                                address = [' '.join(t.split()).strip().title() for t in m]
                                searchresult.append(address[0]) #Number
                                # Thank you Dan Gabrielson <dan.gabrielson@gmail.com> and Matt Everson https://github.com/matteverson
                                # for your help at 2015 Appleton Civic Hackathon! This closes https://github.com/mikeputnam/appletonapi/issues/5
                                label = ' '
                                for chunk in address[1:]:
                                    label += chunk + ' '
                                searchresult.append(label.strip())
                            allresults.append(searchresult)

            return { 'result' : allresults }
        except urllib2.URLError, e:
            logging.error('SEARCH FAIL! my.appleton.org up? scrape assumptions still valid?')
            return { 'error' : "Cannot search :( <br/>" + str(e) }


class GarbageCollectionHandler(BaseHandler):
    def get(self):
        return self.write_response(self.execute(self.request.get('addr'), str(self.request.headers['User-Agent'])))

    def execute(self, address, user_agent):
        search_handler = SearchHandler()
        search_response = search_handler.execute(address, user_agent)
        
        if search_response.has_key('error'):
            return search_response
           
        collection_days = []
        
        if len(search_response['result']) > 0:
            prop_handler = PropertyHandler()
            prop_response = prop_handler.execute(search_response['result'][0][0])
            if prop_response.has_key('error'):
                return prop_response

            garbage_day = prop_response['result'][1]['garbageday']
            recycling_day = prop_response['result'][1]['recycleday']
            split_recycling_day = recycling_day.split(',')
            found_recycling = False
            cur_date = datetime.now()
            failsafe_count = 0

            while not found_recycling and failsafe_count < 21:
                today_string = cur_date.strftime('%Y-%m-%d')
                
                if self.day_of_week_string_to_int(garbage_day) == cur_date.weekday():
                    collection_days.append( { 'collectionType' : 'trash', 'collectionDate' : today_string } )
                
                if cur_date.strftime('%m-%d-%Y') == split_recycling_day[1].strip():
                    collection_days.append( { 'collectionType' : 'recycling', 'collectionDate' : today_string } )
                    found_recycling = True
                    
                cur_date += timedelta(days=1)
                failsafe_count += 1

        return { 'result': collection_days }

    def day_of_week_string_to_int(self, string_day):
        return {
            'Monday' : 0,
            'Tuesday' : 1,
            'Wednesday' : 2,
            'Thursday' : 3,
            'Friday' : 4,
            'Saturday' : 5,
            'Sunday' : 6
        }[string_day]


class CrimesHandler(BaseHandler):
    def get(self):
        start_date = self.request.get('start_date', default_value=(datetime.now()).strftime(DATE_FORMAT))
        end_date = self.request.get('end_date', default_value=start_date)
        start_date_math = datetime.strptime(start_date, DATE_FORMAT)
        end_date_math = datetime.strptime(end_date, DATE_FORMAT)
        if end_date_math - start_date_math > timedelta(days=7):
            logging.debug("Limiting search range to 7 days from start_date")
            end_date = (start_date_math + timedelta(days=7)).strftime(DATE_FORMAT)
        return self.write_response(self.execute(start_date, end_date))

    def execute(self, start_date, end_date):
        logging.debug("start_date:%s end_date:%s",start_date,end_date)
        allresults = []
        for x in range(2):
            # Rows and Columns are based on Google Map tiles of the Appleton area
            row = 2970 + x
            for y in range(1, 8):
                column = 2080 + y
                url = 'https://www.crimereports.com/v3/crime_reports/map/search_by_tile.json?org_ids={0}' \
                      '&include_sex_offenders={1}' \
                      '&incident_type_ids={2}' \
                      '&start_date={3}' \
                      '&end_date={4}' \
                      '&zoom={5}' \
                      '&row={6}' \
                      '&column={7}'.format(83558,
                                           'false',
                                           '8,9,10,11,12,14,97,98,99,100,101,103,148,149,151,160,163,165,166,167,169,171,172,180,168,121,162,164,179,178,150,173,161,104',
                                           start_date,
                                           end_date,
                                           13,
                                           row,
                                           column)
                result = urlfetch.fetch(url, deadline=10)
                allresults += json.loads(result.content)['crimes']
        return { 'result' : allresults }


class MainHandler(webapp2.RequestHandler):
    def get(self):
        indexhtml = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>appletonapi</title>
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<!--[if lt IE 9]>
<script src="http://html5shim.googlecode.com/svn/trunk/html5.js"></script>
<![endif]-->
</head>
<body>
<p>AppletonAPI is the humble beginning of a RESTful API for Appleton, WI civic data.</p>
<p>All data presented by AppletonAPI is directly from <a href="http://my.appleton.org/">http://my.appleton.org/</a> and presented in a manner usable by client programmers.</p>
<p><a href="https://github.com/mikeputnam/appletonapi">Documentation and source code available on Github.</a></p>
</body>
</html>
        """
        self.response.out.write(indexhtml)


app = webapp2.WSGIApplication(
    [
        ('/', MainHandler),
        (r'/property/(\d+)', PropertyHandler),
        ('/search', SearchHandler),
        ('/crimes', CrimesHandler),
        ('/garbagecollection', GarbageCollectionHandler)
    ], debug=True)


def main():
    # Set the logging level in the main function
    logging.getLogger().setLevel(logging.DEBUG)
    webapp.util.run_wsgi_app(app)


if __name__ == '__main__':
    main()
