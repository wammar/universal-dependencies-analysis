from django.shortcuts import render
from django.http import HttpResponse
from django.http import HttpResponseBadRequest
from django.shortcuts import render_to_response, RequestContext
from django import forms
from searchengine.services.SearchEngine import load_index, find_matches
import json


def hello_world(request):
    load_index()
    return render_to_response('searchengine/index.html', {'hi': 'unknown'}, RequestContext(request))


def search(request):

    query = request.POST["query"]
    lang = request.POST["lang"]
    print query
    print lang.strip()
    try:
        output = find_matches(query, lang.strip())
    except:
        return HttpResponseBadRequest("bad query")
    # store results in the session
    first_ten_matches = output["results"]
    request.session["currentresult"] = 1
    request.session["resultssize"] = len(first_ten_matches)
    first_match = first_ten_matches[0] if len(first_ten_matches)>0 else None
    for i in range(0, len(first_ten_matches)):
        request.session[str(i+1)] = first_ten_matches[i]

    return HttpResponse(json.dumps({"currentresult": min(1, output["size"]), "size": output["size"], "samplesize": len(first_ten_matches), "time": output["time"], "firstresult": first_match}), content_type="application/json")


def getpreviousresult(request):
    current_result = request.session["currentresult"]
    current_result = 0 if current_result == 0 else max(1, current_result-1)
    request.session["currentresult"] = current_result
    print current_result
    return HttpResponse(json.dumps({"currentresult": current_result, "tree": request.session[str(current_result)]}), content_type="application/json")


def getnextresult(request):
    max_size = request.session["resultssize"]
    current_result = request.session["currentresult"]
    current_result = 0 if current_result == 0 else min(max_size, current_result+1)
    request.session["currentresult"] = current_result
    print current_result
    return HttpResponse(json.dumps({"currentresult": current_result, "tree": request.session[str(current_result)]}), content_type="application/json")