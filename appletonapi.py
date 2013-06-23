"""
Copyright (c) 2013 Mike Putnam <mike@theputnams.net>

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

from google.appengine.api import memcache
import json
import logging
import re
import urllib
import urllib2
import webapp2

def extracttagvalues(line):
    m = re.search('(?<=value\=\").*?([^\'" >]+)', line)
    if m:
        return re.split('value="',m.group(0))[0]

def sanitizeinput(rawinput):
    m = re.search('^\w+$', rawinput)
    if m:
        return m.group(0)

class PropertyHandler(webapp2.RequestHandler):
    def get(self,propkey):
        p = memcache.get(sanitizeinput(propkey))   
        if p is not None:             
            self.response.headers["Content-Type"] = "application/json"
            self.response.out.write(json.dumps(p))
        else:                         
            detailurl = "http://my.appleton.org/Propdetail.aspx?PropKey=" + str(propkey)
            scrapehooks =  [
            "Garbage Day",
            "Recycle Day"
            ]
            datalist = []
            try:
                response = urllib2.urlopen(detailurl)
                for line in response:
                    for h in scrapehooks:
                        if h in line:
                            m = re.search('(?<=</td><td>).*', line)
                            if m:
                                datalist.append( re.split('</td></tr>',m.group(0))[0] )
                            if h == scrapehooks[-1]:
                                self.response.headers["Content-Type"] = "application/json"
                                self.response.out.write(json.dumps(datalist))
                                memcache.add(str(propkey),datalist) 
            except urllib2.HTTPError, response:
                self.response.out.write( 'error - Scrape',response)

class SearchHandler(webapp2.RequestHandler):
   def get(self):
        housenumber = sanitizeinput(str(self.request.get('h')))
        street = sanitizeinput(str(self.request.get('s')))
        if not housenumber and not street:
            self.response.out.write('Give me *SOMETHING* to search for.')
            return
        try:
            response = urllib2.urlopen('http://my.appleton.org/')
            for line in response:
                if "__VIEWSTATE" in line:
                    vs = extracttagvalues(line)
                if "__EVENTVALIDATION" in line:
                    ev = extracttagvalues(line)
                    formvalues = {
                        '__EVENTTARGET' : '',
                        '__EVENTARGUMENT' : '',
                        '__VIEWSTATE' : vs,
                        '__EVENTVALIDATION' : ev,
                        'ctl00$myappletonContent$txtStreetNumber' : housenumber,
                        'ctl00$myappletonContent$txtStreetName' : street,
                        'ctl00$myappletonContent$btnSubmit':'Submit'}
                    headers = {
                        'User-Agent':str(self.request.headers['User-Agent']),
                        'Referer':'http://my.appleton.org/default.aspx',
                        'Accept':'text/html,application/xhtml+xml,application/xml'
                        }
                    data = urllib.urlencode(formvalues)
                    req = urllib2.Request("http://my.appleton.org/default.aspx",data, headers)
                    response = urllib2.urlopen(req)
                    allresults = []
                    #Example of the HTML returned...
                    #<a id="ctl00_myappletonContent_searchResults_ctl03_PropKey"
                    #href="Propdetail.aspx?PropKey=312039300&amp;Num=100">312039300  </a>
                    #                  </td><td>100</td><td>E WASHINGTON           ST  </td>
                    for pline in response:
                        if "Propdetail.aspx?PropKey=" in pline:
                            searchresult = []
                            m = re.search('(?<=PropKey\=).*(?=&)', pline)
                            if m:
                                searchresult.append( re.split('PropKey=',m.group(0))[0] )
                            m = re.findall('(?s)<td>(.*?)</td>', response.next())
                            if m:
                                # this removes whitespace and Title Cases the address
                                # given: <td>1200</td><td>W WISCONSIN    AVE </td>
                                # returns: ['1200', 'W Wisconsin Ave']
                                address = [' '.join(t.split()).strip().title() for t in m] 
                                searchresult.append(address[0])
                                searchresult.append(address[1])
                            allresults.append(searchresult)

            self.response.headers["Content-Type"] = "application/json"
            self.response.out.write(json.dumps(allresults))
        except urllib2.HTTPError, response:
            self.response.out.write("500 - Cannot search :(")
            logging.error('SEARCH FAIL! my.appleton.org up? scrape assumptions still valid?')

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
<hr>
<p>Current API v1.0.0:</p>
<p>Search for a property within the city of Appleton using house number and base street name.</p>
<ul>
<li>GET http://1.appletonapi.appspot.com/search?h=120&amp;s=Morrison</li>
<li>Returns a JSON result consisting of a list of possible properties given the search parameters: &amp;h = house number, &amp;s = street name.</li>
</ul>
<p>When is garbage day? Recycling day?</p>
<ul>
<li>GET http://1.appletonapi.appspot.com/property/312030300/</li>
<li>Given a property, returns a JSON result: day of the week the garbage picked up, recycling picked up, and next date of pickup?</li>
</ul>
<hr>
<p>Demo:</p>
<form action="/search" method="get">
House number: <input type="text" name="h"/><br>
Street: <input type="text" name="s"/><br>
<input type="submit" value="Submit">
</form>
</body>
</html> 
        """
        self.response.out.write(indexhtml)
app = webapp2.WSGIApplication(
    [
        ('/', MainHandler),
        (r'/property/(\d+)', PropertyHandler),
        ('/search', SearchHandler)
    ], debug=True)

def main():
    # Set the logging level in the main function
    logging.getLogger().setLevel(logging.DEBUG)
    webapp.util.run_wsgi_app(app)

if __name__ == '__main__':
    main()

