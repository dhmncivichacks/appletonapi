import datetime
import json
from datetime import date

response_string = """
[
    "generalinformation",
    {
        "2015leafcollectiondates": "To Be Determined For 2015",
        "elementaryschool": "Highlands",
        "firestationaddress": "1701 W. Brewster St",
        "firestationnumber": "5",
        "garbageday": "Monday",
        "highschool": "Appleton West",
        "middleschool": "Wilson",
        "recycleday": "Monday, 04-06-2015",
        "sanitarydistrict": "Appleton",
        "schooldistrict": "Appleton Area",
        "watersource": "Appleton"
    }
]
"""

response_json = json.loads(response_string)

next_recycling_date = date(2015,4,6)

days_until_next_recycling_date = next_recycling_date - date.today()

days_until_next_pickup = days_until_next_recycling_date.days - 7

if days_until_next_recycling_date.days < 7:
    print ("RECYCLING WEEK. PICKUP IN %i DAYS." % days_until_next_pickup)
else:
    print ("GARBAGE ONLY WEEK. PICKUP IN %i DAYS." % days_until_next_pickup)
