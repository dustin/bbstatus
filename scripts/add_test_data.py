#!/usr/bin/env python

import sys
import urllib

url = sys.argv[1]

BASE_PARAMS = {
    'builder': 'test_script',
    'category': 'test',
    'buildNumber': '1'
}

def xmit(event, data):
    d = dict(**BASE_PARAMS)
    d.update(data, event=event)
    urllib.urlopen(url, urllib.urlencode(d)).read()

def buildStarted():
    xmit('buildStarted', {'reason': 'testing',
                          'revision': '3.14'})

def stepStarted():
    xmit('stepStarted', {'step': 'test_step'})

def stepFinished():
    xmit('stepFinished', {'step': 'test_step',
                          'resultStatus': 'success',
                          'resultString': 'ok'})

def buildFinished():
    xmit('buildFinished', {'result': 'success',
                           'revision': '3.14',
                           'had_patch': 'False'})

if __name__ == '__main__':
    buildStarted()
    stepStarted()
    stepFinished()
    buildFinished()
