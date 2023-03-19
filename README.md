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

## API v3.3.0 (current)

#### Search

Search for a property within the city of Appleton using the street address.

    GET /search?q={street address}

**Requires**: Search parameter: &q = Street address

**Returns**: JSON result consisting of a list of possible property ids.

**Example**: http://3-3.appletonapi.appspot.com/search?q=121%20Douglas%20St (street address for the Appleton Makerspace)

```
[
    [
        "315173204",
        "121",
        "N Douglas St"
    ],
    [
        "315173204",
        "121",
        "N Douglas St B"
    ],
    [
        "315173204",
        "121",
        "N Douglas St R"
    ]
]
```

#### Property

    GET /property/{property key}

**Requires**: property key

**Returns**: JSON result containing the majority of data available on my.appleton.org for that property.

**Example**: http://3-3.appletonapi.appspot.com/property/315173204 (property key for the [Appleton Makerspace](http://appletonmakerspace.org))

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

## Deployment notes (for the maintainer)
Use miniconda/conda within VSCode to create a venv for you and the tell VSCode to use it for the below.
```
Assorted pre-requisites:

# Python 2 to 3 tool
$ pip install modernize
$ python-modernize -w appletonapi.py

# Googly dev server tools
$ sudo apt-get update && sudo apt-get install google-cloud-sdk-skaffold google-cloud-sdk-bigtable-emulator google-cloud-sdk-anthos-auth google-cloud-sdk-log-streaming google-cloud-sdk-pubsub-emulator google-cloud-sdk google-cloud-sdk-terraform-tools google-cloud-sdk-cbt google-cloud-sdk-harbourbridge google-cloud-sdk-minikube google-cloud-sdk-spanner-emulator google-cloud-sdk-datastore-emulator google-cloud-sdk-app-engine-python-extras google-cloud-sdk-kpt google-cloud-sdk-kubectl-oidc google-cloud-sdk-package-go-module google-cloud-sdk-cloud-build-local google-cloud-sdk-local-extract google-cloud-sdk-app-engine-go google-cloud-sdk-app-engine-python google-cloud-sdk-app-engine-java google-cloud-sdk-app-engine-grpc google-cloud-sdk-gke-gcloud-auth-plugin google-cloud-sdk-config-connector google-cloud-sdk-nomos google-cloud-sdk-firestore-emulator kubectl google-cloud-sdk-cloud-run-proxy

# More Googly bits
$ pip install --upgrade gcloud
$ pip install --upgrade google-api-python-client
$ pip install google-cloud

# Install local deps
$ pip install -r requirements.txt

# Run Googly dev server
$ dev_appserver.py --dev_appserver_log_level debug --application appletonapi .

$ gcloud app logs tail -s default

$ gcloud app deploy --version 3-3 --no-promote
```
## Deprecated API versions.

In order to reduce client breakage due to changes in the API, it is best to define the API version number in your calls. This way you will have time to refactor your client to work with new API changes.

Clients dependent on previous versions of the API can continue to use those earlier versions for a time. However, these will be removed at some point -- best to use the latest version.

API v2.2.0 Example calls:

    GET http://2-2.appletonapi.appspot.com/search?h=121&s=Douglas
    GET http://2-2.appletonapi.appspot.com/property/315173204


API v1.0.0 Example calls:

    GET http://1.appletonapi.appspot.com/search?h=121&s=Douglas
    GET http://1.appletonapi.appspot.com/property/315173204
