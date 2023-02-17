"""
Copyright (c) 2019 Mike Putnam <mike@theputnams.net>

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

from __future__ import absolute_import
from datetime import datetime, timedelta

import logging
import re

import inflect
import lxml.etree
import lxml.html
import requests
import streetaddress

from flask import Flask, jsonify

app = Flask(__name__)

DATE_FORMAT = "%Y-%m-%d"

_digits = re.compile(r'\d')
def contains_digits(maybe_digits):
    '''Decide if we have numbers.'''
    return bool(_digits.search(maybe_digits))


def extracttagvalues(line):
    '''Parse html stuff.'''
    maybe_match = re.search(r'(?<=value\=\").*?([^\'" >]+)', line)
    if maybe_match:
        return re.split('value="', maybe_match.group(0))[0]
    return None


def sanitizeinputwords(rawinput):
    '''Hacky regex to strip ugly input.'''
    maybe_match = re.search(r'^\w+$', rawinput)
    if maybe_match:
        return maybe_match.group(0)
    return None


@app.route('/property/<int:propkey>')
class PropertyHandler():
    '''Calls coming in with a propkey.'''
    def get(self, propkey):
        '''Get'''
        return self.write_response(self.execute(propkey))

    def execute(self, propkey):
        '''Execute'''
        propkey = sanitizeinputwords(propkey)
        detailurl = "http://my.appleton.org/Propdetail.aspx?PropKey=" + str(propkey)
        datagroups = []
        try:
            docroot = lxml.html.fromstring(requests.get(detailurl, timeout=15).content)
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
            return jsonify({ 'result' : datagroups })
        except requests.HTTPError as response:
            return jsonify({ 'error' : 'error - Scrape: ' + str(response) })


@app.route('/search')
class SearchHandler():
    '''
    The ugliest hack here (and only real value-add of the whole thing).
    Parse .aspx forms and get back "useful" data.
    '''
    def get(self):
        '''Get'''
        return self.write_response(self.execute(self.request.get('q'), str(self.request.headers['User-Agent'])))

    def execute(self, search_input, user_agent):
        '''Execute'''
        # Google maps geolocation appends 'USA' but the address parser can't cope
        search_input = search_input.replace('USA','')
        addr = streetaddress.parse(search_input)
        if addr is None:
            # Since we are so tightly coupled with Appleton data,
            # let's just pacify the address parser.
            addr = streetaddress.parse(search_input + ' Appleton, WI')
        housenumber = addr['number']
        # Handle upstream requirement of "Fifth" not "5th"
        inflect_instance = inflect.engine()
        if contains_digits(addr['street']):
            street = inflect_instance.number_to_words(addr['street'])
        else:
            street = addr['street']

        if not housenumber and not street:
            return { 'error' : 'Give me *SOMETHING* to search for.'}

        try:
            response = requests.get('http://my.appleton.org/', timeout=15).content
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
                    #FIXME This is going to hurt.  was "urllib2" >>> now make it "requests".
                    data = six.moves.urllib.parse.urlencode(formvalues)
                    req = six.moves.urllib.request.Request("http://my.appleton.org/default.aspx", data, headers)
                    response = six.moves.urllib.request.urlopen(req)
                    allresults = []
                    # Example of the HTML returned...
                    # <a id="ctl00_myappletonContent_searchResults_ctl03_PropKey"
                    # href="Propdetail.aspx?PropKey=312039300&amp;Num=100">312039300  </a>
                    #                  </td><td>100</td><td>E WASHINGTON           ST  </td>
                    for pline in response:
                        if "Propdetail.aspx?PropKey=" in pline:
                            searchresult = []
                            maybe_propkey_match = re.search(r'(?<=PropKey\=).*(?=&)', pline)
                            if maybe_propkey_match:
                                searchresult.append(
                                    re.split('PropKey=', maybe_propkey_match.group(0))[0]
                                    )
                            maybe_td_match = re.findall(r'(?s)<td>(.*?)</td>', next(response))
                            if maybe_td_match:
                                # this removes whitespace and Title Cases the address
                                # given: <td>1200</td><td>W WISCONSIN    AVE </td>
                                # returns: ['1200', 'W Wisconsin Ave']
                                address = [
                                    ' '.join(t.split()).strip().title() for t in maybe_td_match
                                    ]
                                searchresult.append(address[0]) #Number
                                # Thank you Dan Gabrielson <dan.gabrielson@gmail.com> and
                                # Matt Everson https://github.com/matteverson
                                # for your help at 2015 Appleton Civic Hackathon!
                                # This closes https://github.com/mikeputnam/appletonapi/issues/5
                                label = ' '
                                for chunk in address[1:]:
                                    label += chunk + ' '
                                searchresult.append(label.strip())
                            allresults.append(searchresult)

            return { 'result' : allresults }
        except RuntimeError as err:
            logging.error('SEARCH FAIL! my.appleton.org up? scrape assumptions still valid?')
            return { 'error' : "Cannot search :( <br/>" + str(err) }


@app.route('/garbagecollection')
class GarbageCollectionHandler():
    '''Look up all the useful details.'''
    def get(self):
        return self.write_response(self.execute(self.request.get('addr'), str(self.request.headers['User-Agent'])))

    def execute(self, address, user_agent):
        search_handler = SearchHandler()
        search_response = search_handler.execute(address, user_agent)

        if 'error' in search_response:
            return search_response

        collection_days = []

        if len(search_response['result']) > 0:
            prop_handler = PropertyHandler()
            prop_response = prop_handler.execute(search_response['result'][0][0])
            if 'error' in prop_response:
                return prop_response

            garbage_day = prop_response['result'][1]['garbageday']
            recycling_day = prop_response['result'][1]['residentialrecycleday']
            split_recycling_day = recycling_day.split(',')
            recycling_date = split_recycling_day[1].strip()
            found_recycling = False
            cur_date = datetime.now()
            lookahead_days = 0

            while not found_recycling and lookahead_days < 21:
                today_string = cur_date.strftime('%Y-%m-%d')

                if self.day_of_week_string_to_int(garbage_day) == cur_date.weekday():
                    collection_days.append(
                        { 'collectionType' : 'trash', 'collectionDate' : today_string }
                        )

                if cur_date.strftime('%m-%d-%Y') == recycling_date:
                    collection_days.append(
                        { 'collectionType' : 'recycling', 'collectionDate' : today_string }
                        )
                    found_recycling = True

                cur_date += timedelta(days=1)
                lookahead_days += 1

        return { 'result': collection_days }

    def day_of_week_string_to_int(self, string_day):
        '''Map numeric day of week from upstream to human readable day.'''
        return {
            'Monday' : 0,
            'Tuesday' : 1,
            'Wednesday' : 2,
            'Thursday' : 3,
            'Friday' : 4,
            'Saturday' : 5,
            'Sunday' : 6
        }[string_day]


@app.route('/')
class MainHandler():
    '''The index / of appletonapi.appspot.com.'''
    def get(self):
        '''Get'''
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
<p><a href="https://github.com/dhmncivichacks/appletonapi">Documentation and source code available on Github.</a></p>
</body>
</html>
        """
        self.response.out.write(indexhtml)


# app = webapp2.WSGIApplication(
#     [
#         ('/', MainHandler),
#         (r'/property/(\d+)', PropertyHandler),
#         ('/search', SearchHandler),
#         ('/garbagecollection', GarbageCollectionHandler)
#     ], debug=True)


# def main():
#     # Set the logging level in the main function
#     logging.getLogger().setLevel(logging.DEBUG)
#     webapp.util.run_wsgi_app(app)


# if __name__ == '__main__':
#     main()
