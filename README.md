AppletonAPI
===========

[AppletonAPI](http://appletonapi.appspot.com/) is the humble beginning of a RESTful API for Appleton, WI civic data.

All data presented by AppletonAPI is directly from http://my.appleton.org/ and presented in a manner usable by client programmers.

The API itself is running on [Google App Engine](https://developers.google.com/appengine/) .

## Known Clients

Apps that allow you to lookup recycling pickup schedule for the current week:

* [Is it recycling week?](https://github.com/mikeputnam/isitrecyclingweek) - Android app
* [AppletonPebble](https://github.com/zo0o0ot/AppletonPebble) - Pebble app
* [Is it recycling week in Appleton?](https://github.com/dhmncivichacks/isitrecycling) - web app
* [Civic Hack API Locator](https://github.com/mrosack/civic-hack-api-locator) - Not a client, but an API discovery/contract project to which AppletonAPI will attempt to adhere to

## API v2.0.0 (current)

#### Search

Search for a property within the city of Appleton using house number and base street name.

    GET /search?h={house number}&s={street name}

**Requires**: Search parameters: &h = house number, &s = street name.

**Returns**: JSON result consisting of a list of possible property ids.

**Example**: http://appletonapi.appspot.com/search?h=100&s=Appleton (street address for Appleton City Hall)

```
[
    [
        "312027350",
        "100",
        ""
    ],
    [
        "316035700",
        "1002",
        ""
    ],
    [
        "316012500",
        "1003",
        ""
    ],
    [
        "316012500",
        "1003",
        ""
    ],
    [
        "316012500",
        "1003",
        ""
    ],
    [
        "316035800",
        "1008",
        ""
    ],
    [
        "316012600",
        "1009",
        ""
    ],
    [
        "316012600",
        "1009",
        "1/2"
    ]
]
```

#### Property

    GET /property/{property key}

**Requires**: property key

**Returns**: JSON result containing the majority of data available on my.appleton.org for that property.

**Example**: http://appletonapi.appspot.com/property/315173204 (property key for the [Appleton Makerspace](http://appletonmakerspace.org))

```
[
    "generalinformation",
    {
        "2015leafcollectiondates": "To Be Determined For 2015",
        "elementaryschool": "Lincoln",
        "firestationaddress": "1701 W. Brewster St",
        "firestationnumber": "5",
        "garbageday": "Monday",
        "highschool": "Appleton West",
        "middleschool": "Wilson",
        "recycleday": "Monday, 04-20-2015",
        "sanitarydistrict": "Appleton",
        "schooldistrict": "Appleton Area",
        "watersource": "Appleton"
    },
    "votinginfo",
    {
        "alderman": "Christine Williams",
        "aldermandistrict": "10",
        "assemblydistrict": "57",
        "cityward": "29",
        "congressionaldistrict": "8",
        "county": "Outagamie",
        "countysupervisordistrict": "3",
        "pollinglocation": "St. Matthew Ev. Lutheran Church",
        "senatedistrict": "19",
        "whorepresentsme": "State & Government Leaders"
    },
    "parcelinformation",
    {
        "assessmentclass": "Commercial"
    },
    "propertyowner",
    {
        "address": "115 1/2 N Douglas St Appleton Wi 54914",
        "name": "Meiers, John P"
    },
    "legaldescriptioninformation",
    {
        "legaldescription": "Fifth Ward Plat 5Wd W238Ft Of E268Ft Of N192.5Ft Of S292.5Ft Of Blk 84 107-121 N Douglas St"
    },
    "landsize",
    {
        "effectivedepth": "0",
        "frontagesqftacres": "54145.00",
        "shape": ""
    },
    "zoninginformation",
    {
        "c2": "General Commercial District"
    },
    "businesses",
    {
        "businessname": "Shooting Star Photo",
        "driverseducationofthefox": "Hankey, John D & Associates",
        "valheatinc": "Julien Shade Shop, The"
    },
    "otherbuildingsonthisparcel",
    {
        "310173241": "31-0-1732-42"
    },
    "currentassessedvalue",
    {
        "building": "$259,500",
        "land": "$148,900",
        "partialfullassessment": "Full",
        "total": "$408,400"
    },
    "2014taxinformation",
    {
        "1stdollarcredit": "$62.04",
        "amountcollected": "$8,864.72",
        "balancedue": "$4,514.00",
        "interestdue": "$0.00",
        "lesslotterycredit": "$0.00",
        "propertytaxes": "$9,681.86",
        "specialassesments": "$4,347.73",
        "statecredits": "$588.83",
        "taxbillamount": "$13,378.72"
    },
    "salestransfers",
    {
        "date": "June 1990",
        "deedtype": "Quit Claim Deed",
        "document": "10456 / 26",
        "price": "$0.00",
        "vacantimproved": "Land & Building",
        "validity": "Not Open Market"
    },
    "building",
    {
        "buildingarea": "22792",
        "exteriorwalltype": "Blk",
        "framingtype": "Wd Joist Fr - Steel",
        "numberofstories": "1",
        "structuretype": "Multiuse Building",
        "wallheight": "12",
        "yearbuilt": "1952"
    },
    "otherimprovements",
    {
        "desciption": "Detached Garage - Masonry",
        "quantity": "1",
        "sqft": "1400",
        "yearbuilt": "1952"
    }
]
```

## API v1.0.0

Clients dependent on previous versions of the API can continue to use those earlier versions by specifying the version number in the call.

v1.0.0 Example calls:

    GET http://1.appletonapi.appspot.com/search?h=121&s=Douglas
    GET http://1.appletonapi.appspot.com/property/315173204
