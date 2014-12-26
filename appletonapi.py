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
from google.appengine.api import namespace_manager
import json
import logging
import lxml.etree
import lxml.html
import os
import re
import urllib
import urllib2
import webapp2

def extracttagvalues(line):
    m = re.search('(?<=value\=\").*?([^\'" >]+)', line)
    if m: 
        return re.split('value="',m.group(0))[0]

def sanitizeinputwords(rawinput):
    m = re.search('^\w+$', rawinput)
    if m:
        return m.group(0)

class PropertyHandler(webapp2.RequestHandler):
    def get(self,propkey):
        #memcache namespace changes UNTESTED FIXME
        propkey = sanitizeinputwords(propkey)
        major_ver, minor_ver = os.environ.get('CURRENT_VERSION_ID').rsplit('.', 1)
        namespace_manager.set_namespace(major_ver)
        logging.debug("namespace: " + major_ver)
        p = memcache.get(propkey)   
        if p is not None:             
            logging.debug("from memcache: " + propkey)
            self.response.headers["Content-Type"] = "application/json"
            self.response.out.write(json.dumps(p, sort_keys=True,indent=4, separators=(',', ': ')))
        else:                         
            detailurl = "http://my.appleton.org/Propdetail.aspx?PropKey=" + str(propkey)
            datagroups = []
            try:
                docroot = lxml.html.fromstring(urllib2.urlopen(detailurl).read())
                tables = docroot.xpath("//table[@class='t1']")
                for table in tables:
                    ths = table.xpath("./tr/th") #assuming single <th> per table
                    for th in ths:
                        if th is not None:
                            lxml.etree.strip_tags(th, 'a', 'b', 'br', 'span', 'strong')
                            if th.text:
                                thkey = re.sub('\W', '', th.text).lower() #nospaces all lower
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
                                            tdvalue = " ".join(tdvalue.split()) #remove extra whitespace
                                            tdcounter = 0
                                            #when the source tr + td are commented out lxml still sees them. PREVENT!
                                            if tdkey == '' and tdvalue == '':
                                                break
                                            else:
                                                datadict[tdkey] = tdvalue
                                    datagroups.append(datadict)
                logging.debug("setting memcache for key: " + propkey)
                memcache.add(str(propkey),datagroups) 
                self.response.headers["Content-Type"] = "application/json"
                self.response.out.write(json.dumps(datagroups, sort_keys=True,indent=4, separators=(',', ': ')))
            except urllib2.HTTPError, response:
                self.response.out.write( 'error - Scrape: ' + str(response))

class SearchHandler(webapp2.RequestHandler):
   def get(self):
        housenumber = sanitizeinputwords(str(self.request.get('h')))
        street = sanitizeinputwords(str(self.request.get('s')))
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
            self.response.out.write(json.dumps(allresults, sort_keys=True,indent=4, separators=(',', ': ')))
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
<script>
  (function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
  (i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
  m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
  })(window,document,'script','//www.google-analytics.com/analytics.js','ga');

  ga('create', 'UA-168979-12', 'appletonapi.appspot.com');
  ga('send', 'pageview');

</script>
<style>
#forkongithub a{background:#000;color:#fff;text-decoration:none;font-family:arial, sans-serif;text-align:center;font-weight:bold;padding:5px 40px;font-size:1rem;line-height:2rem;position:relative;transition:0.5s;}
#forkongithub a:hover{background:#060;color:#fff;}
#forkongithub a::before,#forkongithub a::after{content:"";width:100%;display:block;position:absolute;top:1px;left:0;height:1px;background:#fff;}
#forkongithub a::after{bottom:1px;top:auto;}@media screen and (min-width:800px){#forkongithub{position:absolute;display:block;top:0;right:0;width:200px;overflow:hidden;height:200px;}
#forkongithub a{width:200px;position:absolute;top:60px;right:-60px;transform:rotate(45deg);-webkit-transform:rotate(45deg);box-shadow:4px 4px 10px rgba(0,0,0,0.8);}}
</style>
<span id="forkongithub"><a href="https://github.com/mikeputnam/appletonapi">Fork me on GitHub</a></span>
<p>AppletonAPI is the humble beginning of a RESTful API for Appleton, WI civic data.</p>
<p>All data presented by AppletonAPI is directly from <a href="http://my.appleton.org/">http://my.appleton.org/</a> and presented in a manner usable by client programmers.</p>
<p><a href="https://github.com/mikeputnam/appletonapi">Source code available on Github.</a></p>

<hr>

<p>Current API v2.0.0:</p>
<p>Search for a property within the city of Appleton using house number and base street name.</p>

<pre>
    GET http://appletonapi.appspot.com/search?h=121&amp;s=Douglas</li>
</pre>

<p>Returns a JSON result consisting of a list of possible properties given the search parameters: &amp;h = house number, &amp;s = street name.</p>

<p>When is garbage day? Recycling day?</p>

<pre>
    GET http://appletonapi.appspot.com/property/312030300
</pre>

<p>Given a property, returns a JSON result containing the majority of data available on my.appleton.org</p>

<hr>

<p>Demo:</p>
<form action="/search" method="get">
House number: <input type="text" name="h"/><br>
Street: <input type="text" name="s"/><br>
<input type="submit" value="Submit">
</form>

<hr>

<p>Clients dependent on previous versions of the API can continue to use those earlier versions by specifying the version number in the call.</p>

<p>v1.0.0 Example calls:</p>

<pre>
    GET http://1.appletonapi.appspot.com/search?h=121&amp;s=Douglas
    GET http://1.appletonapi.appspot.com/property/312030300
</pre>

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

