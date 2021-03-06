#!/usr/bin/python

import sys
import json
import requests
import grequests
import time


##################
## Class Engine ##
##################

class URIFactory:
    # extract "concept" dbpedia URI from a well formed Alchemy JSON
    def extractingConceptsJSON(self, jsonIN):
        concepts = []
        for concept in jsonIN["concepts"]:
            if 'dbpedia' in concept:
                concepts.append(concept["dbpedia"])
        return concepts

    # extract "Entity/Disambiguated" dbpedia URI from a well formed Alchemy JSON
    def extractingDisambiguatedJSON(self, jsonIN):
        disambiguated = []
        for entity in jsonIN["entities"]:
            if 'disambiguated' in entity:
                if 'dbpedia' in entity["disambiguated"]:
                    disambiguated.append(entity["disambiguated"]["dbpedia"])
        return disambiguated

    # Alchemy Response Callback
    def alchemyResponseCallback(self, r, *args, **kwargs):
        try:
            resultatAlchemy = r.json()
            url = resultatAlchemy["url"]
        except Exception as e:
            print("Exception raised : Incorrect JSON responses. Content:" + r.text + " Exception : " + type(e))
            return
        try:
            # extracting Concepts
            concepts = self.extractingConceptsJSON(resultatAlchemy)
            disambiguated = self.extractingDisambiguatedJSON(resultatAlchemy)
            mergedList = concepts + disambiguated
        except Exception as e:
            print("Exception raised : Unable to extract concepts and disambiguatedEntities " + type(e))
            return
        try:
            # formatting JSON
            self.jsonOutput["Websites"].append(
                {"URL": url, "URIs": mergedList})
        except Exception as e:
            print("Exception raised : Unable to append to the JSON. ")

    # Constructor : just initialize the empty json Output
    def __init__(self):
        self.jsonOutput = json.loads('{"Websites":[]}')

    # Core of the class
    def run(self, request, numberOfRequests=10):
        # Defining variables
        with open('keys.json') as data_file:
            data = json.load(data_file)
            customSearchApiKey = data['customSearch']['apiKey']
            customSearchCx = data['customSearch']['cx']
            AlchemyApiKey = data['alchemy']['apiKey'][3]

        # STEP 1: Send Google Request
        # print "-- Getting list of URL (CustomSearch) --"
        r = requests.get(
            "https://www.googleapis.com/customsearch/v1?q=" + request + "&key=" + customSearchApiKey + "&cx=" + customSearchCx)
        resultat = r.json()

        # -- extracting list of urls from JSON
        urls = []
        for element in resultat['items']:
            urls.append(element['link'])

        # STEP 2: Send to AlchimyAPI, To extract things (Formated JSON) Every lines marked with "format line" comment, do JSON formating.
        # print "-- Getting informations from URLS (Alchemy) --"

        urlToRequest = []
        for url in urls:
            # Constructing the requets array
            urlToRequest.append(
                "https://gateway-a.watsonplatform.net/calls/url/URLGetCombinedData?apikey=" + AlchemyApiKey + "&url=" + url + "&outputMode=json")

        rs = (grequests.get(u, hooks=dict(response=self.alchemyResponseCallback)) for u in urlToRequest)
        grequests.map(rs)

        # STEP 3: Make JSON more richer with image, title and description
        for element in self.jsonOutput["Websites"]:
            data = self.findDatasOfAnUrl(element["URL"], resultat)
            if data is not None:
                if "title" in data.keys():
                    element["title"] = data["title"]
                if "snippet" in data.keys():
                    element["summary"] = data["snippet"]
                if "pagemap" in data.keys():
                    if "cse_image" in data["pagemap"].keys():
                        element["image"] = data["pagemap"]["cse_image"][0]["src"]
                if "displayLink" in data.keys():
                    element["linkToDisplay"] = data["displayLink"]

        return self.jsonOutput

    def findDatasOfAnUrl(self, url, gSon):
        gSon = gSon["items"]

        for element in gSon:
            if element["link"] == url:
                return element


##############
##   MAIN   ##
##############

def main():
    if len(sys.argv) < 2:
        print("Synthaxe error : please specify a request")
        sys.exit(1)

    request = sys.argv[1]
    engine = URIFactory()
    engine.run(request)


if __name__ == "__main__":
    main()
