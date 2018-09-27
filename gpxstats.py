#!/usr/bin/python

"""Outputs various information about GPX track files.

Given one or more GPX files (http://www.topografix.com/GPX/1/1/) this script
will print out the distance, minimum/maximum elevation and ascent/descent for
each track. It understands the GPX trk, trkseg, and trkpt types.

-Leah Emerson June 14 2018
Updated from http://www.madpickles.org/rokjoo/2010/08/11/gpx-elevation-profile-plotting-with-the-google-chart-api/
for Python 3.

Added keynote_to_keyname allowing reference to PySynth notes by number rather than name.

Added music creation using PySynth based on elevation and distance changes between points (labeled START MY CODE)
"""

import sys, math, urllib.parse
from gpxlib import Gpx, Geopoint, Waypoint
import pysynth_p
import pysynth_b
import pysynth_s
import mixfiles

import wave, struct
import numpy as np
from math import sin, cos, pi, log, exp, floor, ceil
from mixfiles import mix_files
from demosongs import *
from mkfreq import getfreq

pitchhz, keynum = getfreq()
#creats references to key notes, based on number 
def keynote_to_keyname(song):
    o = []
    for a, b in song:
      for x in keynum.keys():
        if keynum[x] == a - 1:
          k = x
      o.append((k, b))
    return o
def computeStatistics(points):
  # Given a list, create a generator that yields a tuple of the current
  # element and the next one.
  def pairNext(l):
    for i in range(len(l) - 1):
      yield (l[i], l[i+1])

  ascent = 0.0
  descent = 0.0
  distance = 0.0
  minimumElevation = sys.maxsize
  maximumElevation = -minimumElevation + 1

  # Calculate differences between adjacent points
  elevationChanges = [point.elevationChange(nextPoint) for point, nextPoint in
                      pairNext(points)]
  distances = [0.0]
  distances.extend([point.distance(nextPoint) for point, nextPoint in 
                       pairNext(points)])
  #START MY CODE
  tempListHigh=[]
  tempListLow = []

  #create a  note for each elevation change and length based on distance
  for i in range(len(elevationChanges)-1):

    #takes elevation number and creates a value 44-88 for upper half of scale. creates length of note (2,4,8,16,32) based on distance
    if (elevationChanges[i] > 0 ):
      newElevation = (elevationChanges[i]*5 - ((elevationChanges[i]*5) %3))/3 
      newDistance = ((distances[i]/4) - ((distances[i]/4) %4)) 
      if(newElevation <=44):
        newElevation = newElevation +44
      else:
        newElevation = 88
      
      if (newDistance>32 or newDistance==24):
        newDistance = 32
      if(newDistance == 12 or newDistance==20):
        newDistance=16
      if (newDistance ==0):
        newDistance=2

      note = (newElevation,newDistance)
      tempListHigh.append(note)

    #takes elevation number when less than 0 and gives value 1-44 for lower half of scale
    elif (elevationChanges[i] < 0):
      elevation = abs(elevationChanges[i])
      newElevation = int((elevation - (elevation %3))/3)
      newDistance = ((distances[i]/4) - ((distances[i]/4) %4)) 
    
      if (newElevation <= 44):
        newElevation = 44 - newElevation
      else:
        newElevation = 0
      if (newDistance>32 or newDistance==24):
        newDistance = 32
      if(newDistance == 12 or newDistance==20):
        newDistance=16
      if (newDistance ==0):
        newDistance=2
      
      note = (newElevation,newDistance)
      tempListLow.append(note)

  #piano-like sound for elevation changes that are greater than 0
  piano = tuple(tempListHigh)
  piano = keynote_to_keyname(piano)
  pysynth_b.make_wav(piano, fn = "piano.wav")
  
  #percussion for elevation changes are less than 0
  low = tuple(tempListLow)
  low = keynote_to_keyname(low)
  pysynth_p.make_wav(low, fn="percussion.wav")

  #string for more full sound, based on elevation changes less than 0
  pysynth_s.make_wav(low, fn="string.wav")

  #mix files created (can only mix two at a time)
  mixfiles.mix_files("percussion.wav", "piano.wav", "percussionString.wav")
  mixfiles.mix_files("string.wav", "percussionString.wav", "FINAL.wav")
  
  #END MY CODE

  return {'distances':distances,
          'elevationChanges':elevationChanges,
          'minimumElevation':min([point.elevation for point in points]),
          'maximumElevation':max([point.elevation for point in points]),
          'ascent':sum([elevation for elevation in elevationChanges 
                        if elevation > 0]),
          'descent':-1 * sum([elevation for elevation in elevationChanges 
                              if elevation < 0])
         }

def getUnitSpecifics(units='metric'):
  unitSpecifics = dict({'elevationUnits':'m',
                        'distanceConverter':0.001,
                        'distanceUnits':'km',
                        'yAxisStepSize':100})

  if (units != 'metric'): # assume imperial
    MILES_IN_METER = 0.000621371192
    FEET_IN_METER = 3.2808399
    unitSpecifics = dict({'elevationUnits':'ft',
                          'distanceConverter':MILES_IN_METER,
                          'distanceUnits':'mi',
                          'yAxisStepSize':300})

  return unitSpecifics

def generateChartURL(points, waypoints, statistics, units='metric'):
  unitSpecifics = getUnitSpecifics(units)
  elevationUnits = unitSpecifics['elevationUnits']
  distanceConverter = unitSpecifics['distanceConverter']
  distanceUnits = unitSpecifics['distanceUnits']
  yAxisStepSize = unitSpecifics['yAxisStepSize']
  
  #http://code.google.com/apis/chart/docs/chart_params.html#gcharts_chs
  maximumArea = 300000 
  #aspectRatio = 11.0 / 8.5 # landscape letter paper
  aspectRatio = 1000.0 / 300.0
  height = math.sqrt(maximumArea / aspectRatio)
  width = maximumArea / height

  elevations = [str(int(round(point.elevation))) for point in points]

  # Create a list of increasing distance from the starting point, scaled
  # appropriately for display in a fixed width. See chds comment below.
  ceilTotalDistance = int(math.ceil(sum(statistics['distances']) * distanceConverter))
  distanceScale = width / ceilTotalDistance
  def runningTotal(s):
    def t(v):
      t.s += v
      return t.s
    t.s = s
    return t
  distances = [distance * distanceScale * distanceConverter 
               for distance in map(runningTotal(0.0), statistics['distances'])]

  minimumElevation = str(int(statistics['minimumElevation']))
  maximumElevation = int(statistics['maximumElevation'])

  # Put some space room at the top of the y axis
  ceilElevation = str(((maximumElevation / yAxisStepSize) + 1) * yAxisStepSize)
  maximumElevation = str(maximumElevation)

  sWidth = str(int(round(width)))
  sHeight = str(int(round(height)))

  # Chart type,  with lxy can plot points via xy coordinates
  cht = 'lxy' 

  # Chart size
  chs = sWidth + 'x' + sHeight

  # Custom scaling, the x axis corresponds to distance. Because the GPS track
  # datapoints are not at a fixed interval, scale to the width of the chart
  # and then use the scaled running total distance for each x coordinate. The
  # y axis corresponds to elevation and doesn't need to be custom scaled by
  # code, the chart setting is enough.
  chds = '0,' + sWidth + ',0,' + ceilElevation

  # Visible axes, the first x,y is for data, the second for labels
  chxt = 'x,y,x,y'

  # Axis ranges, the first is the distance with default step size.
  # The second is elevation with a step size
  chxr = '0,0,' + str(ceilTotalDistance) + '|1,0,' + ceilElevation + ',' + \
    str(yAxisStepSize)

  # Axis labels, the index numbers correspond to the chxt values
  chxl = '2:|' + distanceUnits + '|3:|' + elevationUnits

  # Axis tick mark styles, for elevation axis 1, create a tick mark that spans
  # the width of the chart
  chxtc = '1,' + str(int(round(width)) * -1)

  # Axis label positioning, centered for distance/elevation
  chxp = '2,50|3,50'

  # Chart data, the first values are x coordinates, the second are y.
  # Don't use more than 150 data points since the amount of data that
  # can be sent via HTTP GET is limited to ~2000 characters
  if (len(distances) != len(elevations)):
    print ("WARN: distances size %d is not equal to elevations size %d" )\
      % (len(distances), len(elevations))
  stepSize = int(math.ceil(len(distances) / 150.0))

  # Instead of doing:
  # chd = 't:' + ",".join(distances[::stepSize]) + '|' + ",".join(elevations[::stepSize])
  # iterate through the points looking for ones with 'accurate' waypoints where
  # 'accurate' means the distance from the track point is < X from the point's
  # closest waypoint. If one is not found within a stepSize, that's ok, just
  # draw the point without a waypoint annotation
  chdx = [] 
  chdy = []

  # Text and data value markers. The first one defines the fill under the line
  chm = 'B,60331133,0,0,0'
  step = 1
  outputCount = 0
  distanceTraveled = 0.0
  distanceFromLastWaypoint = sys.maxsize
  chdx.append('0')
  chdy.append(elevations[0])
  for i in range(1, len(points)):
    point = points[i]
    distanceFromLastWaypoint += (distances[i] - distanceTraveled) / distanceScale / distanceConverter
    correctStep = (step % stepSize == 0)
    hasValidWaypoint = (point.waypoint != None and 
                        point.distanceToWaypoint < 20.0 and 
                        distanceFromLastWaypoint > 500.0)
    if correctStep or hasValidWaypoint:
      chdx.append(str(int(round(distances[i]))))
      chdy.append(elevations[i])
      outputCount += 1
      step = 1
      if hasValidWaypoint:
        chm += '|A' + urllib.parse.quote(point.waypoint.getLabel()) + ',666666,0,' + \
            str(outputCount) + ',10'
        distanceFromLastWaypoint = 0.0
    else:
      step += 1
    distanceTraveled = distances[i]

  chartURL = 'http://chart.apis.google.com/chart?' + \
      'cht=' + cht + '&' + \
      'chs=' + chs + '&' + \
      'chds=' + chds + '&' + \
      'chxt=' + chxt + '&' + \
      'chxr=' + chxr + '&' + \
      'chxl=' + chxl + '&' + \
      'chxtc=' + chxtc + '&' + \
      'chxp=' + chxp + '&' + \
      'chd=t:' + ','.join(chdx) + '|' + ','.join(chdy) + '&' + \
      'chm=' + chm

  # choose every other elevation since 500 makes the URL too long
 #print (" URL length: %d" % (len(chartURL)))
  return chartURL

# Given a list of waypoints, return a list of waypoints, all of which are
# minimumProximity away from the rest
def filterCloseWaypoints(waypoints, minimumProximity):
  if len(waypoints) < 2:
    return waypoints
  waypoint = waypoints[0]
  filteredWaypoints = []
  for nextWaypoint in waypoints[1:]:
    if waypoint[0].distance(nextWaypoint[0]) > minimumProximity:
      filteredWaypoints.append(nextWaypoint)
  output = [waypoint]
  output.extend(filterCloseWaypoints(filteredWaypoints, minimumProximity))
  return output

def outputTrackDetails(track, waypoints, units):
  print ('Track: %s' % (track.name))
  points = track.points
  statistics = computeStatistics(points)
  distance = sum(statistics['distances'])


  unitSpecifics = getUnitSpecifics(units)
  elevationUnits = unitSpecifics['elevationUnits']
  distanceConverter = unitSpecifics['distanceConverter']
  distanceUnits = unitSpecifics['distanceUnits']

  print (" total distance: %.2f%s" % (distance * distanceConverter, distanceUnits))
  print (" ascent: %.1f%s" % (statistics['ascent'], elevationUnits) )
  print (" descent: %.1f%s" % (statistics['descent'], elevationUnits)) 
  print (" minimum elevation: %.1f%s" % (statistics['minimumElevation'], elevationUnits))
  print (" maximum elevation: %.1f%s" % (statistics['maximumElevation'], elevationUnits))
  #print (generateChartURL(points, waypoints, statistics, units) )
 
def outputFileDetails(fileName, units):
  gpx = Gpx(fileName, units)
  _ = [outputTrackDetails(track, gpx.waypoints, units) 
       for track in gpx.tracks]

def main(argv=None):
  if argv == None:
    argv = sys.argv
  if len(argv) < 2:
    print ("No GPX file provided.\nUsage is: gpxstats.py [-i] <file1> <file2>...")
    return 0
  units = 'metric'
  firstFileIndex = 1
  if argv[1] == '-i':
    units = 'imperial'
    firstFileIndex = 2
  for i in range(firstFileIndex,len(argv)):
    outputFileDetails(argv[i], units)

if __name__ == '__main__':
  sys.exit(main())
