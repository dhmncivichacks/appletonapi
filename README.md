appletonapi
===========

AppletonAPI is the humble beginning of a RESTful API for Appleton, WI civic data.

All data presented by AppletonAPI is directly from http://my.appleton.org/ and presented in a manner usable by client programmers.

Current API v1.0.0:

    Search for a property within the city of Appleton using house number and base street name.

* GET http://1.appletonapi.appspot.com/search?h=120&s=Morrison
* Returns a JSON result consisting of a list of possible properties given the search parameters: &h = house number, &s = street name.

    When is garbage day? Recycling day?

* GET http://1.appletonapi.appspot.com/property/312030300
* Given a property, returns a JSON result: day of the week the garbage picked up, recycling picked up, and next date of pickup?

