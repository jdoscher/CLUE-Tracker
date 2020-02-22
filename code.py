# Back7.co CLUE Tracker
# Based on code samples from Adafruit, check out more on the CLUE here:
# This project has a series of simple menus and utilizes the following hardware/software:
# - Adafruit CLUE board: https://www.adafruit.com/product/4500
# - Adafruit Stemma GPS: https://www.adafruit.com/product/4415
# - Adafruit Stemma cable: https://www.adafruit.com/product/4399
# - Back7.co 3D printed cases:
# - Original (Tinkercad): https://www.tinkercad.com/things/hPm5opFnrlx-clue-tracker-enclosures/edit
# - Github: 
# More info can be found on the project here:
# A big shout out to the learn.adafruit.com authors plus/including John Park, @danh and @foamyguy on the Adafruit Discord channel

from adafruit_clue import clue
import adafruit_lis3mdl
import adafruit_gps
import time
import board
import busio
import math
from math import sin, cos, sqrt, atan2, radians, degrees

# Use this reference for i2c to use the shared object (thank you @danh on Adafruit Discord for help with this)
i2c = board.I2C()
gps = adafruit_gps.GPS_GtopI2C(i2c, debug=False)  # Use I2C interface

# Reading the magnetometer off the CLUE board
sensor = adafruit_lis3mdl.LIS3MDL(i2c)

#gps.send_command(b'PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0')
# Turn on just minimum info (RMC only, location):
#gps.send_command(b'PMTK314,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0')
# Turn off everything:
#gps.send_command(b'PMTK314,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0')
# Turn on everything (not all of it is parsed!)
# We need this one if you are going to use the GPS stats menu, otherwise data is missing and we error out
gps.send_command(b'PMTK314,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0')

# Set update rate to once a two second (2hz) which is what we want, but it could go even slower.
gps.send_command(b'PMTK220,2000')

# Set our display font size- any smaller and it's really hard to read
# Any bigger and we can't get all the info on the screen
clue_display = clue.simple_text_display(text_scale=2, colors=(clue.WHITE,))

#*****************************
# Important - here are our default GPS target coordinates
# Future feature may be to add storage to change, but it makes updating the sketch harder.  
# More info on the possible future stuff here: https://learn.adafruit.com/circuitpython-essentials/circuitpython-storage
target_lat = 33.11111
target_lon = -110.22222

# GPS timing stuff
timestamp = time.monotonic()
last_print = time.monotonic()

# Sourced from the Adafruit compass sample
# https://github.com/adafruit/Adafruit_CircuitPython_LIS3MDL/blob/master/examples/lis3mdl_compass.py
def vector_2_degrees(x, y):
    angle = degrees(atan2(y, x))
    if angle < 0:
        angle += 360
    return angle

# Also from the Adafruit compass sample
def get_heading(_sensor):
    magnet_x, magnet_y, _ = _sensor.magnetic
    return vector_2_degrees(magnet_x, magnet_y)

# Awesome public domain compass bearing code from Jérôme Renard
# https://gist.github.com/jeromer/2005586
def calculate_initial_compass_bearing(pointA, pointB):
    """
    Calculates the bearing between two points.
    The formulae used is the following:
        θ = atan2(sin(Δlong).cos(lat2),
                  cos(lat1).sin(lat2) − sin(lat1).cos(lat2).cos(Δlong))
    :Parameters:
      - `pointA: The tuple representing the latitude/longitude for the
        first point. Latitude and longitude must be in decimal degrees
      - `pointB: The tuple representing the latitude/longitude for the
        second point. Latitude and longitude must be in decimal degrees
    :Returns:
      The bearing in degrees
    :Returns Type:
      float
    """
    if (type(pointA) != tuple) or (type(pointB) != tuple):
        raise TypeError("Only tuples are supported as arguments")

    lat1 = math.radians(pointA[0])
    lat2 = math.radians(pointB[0])

    diffLong = math.radians(pointB[1] - pointA[1])

    x = math.sin(diffLong) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - (math.sin(lat1)
            * math.cos(lat2) * math.cos(diffLong))

    initial_bearing = math.atan2(x, y)

    # Now we have the initial bearing but math.atan2 return values
    # from -180° to + 180° which is not what we want for a compass bearing
    # The solution is to normalize the initial bearing as shown below
    initial_bearing = math.degrees(initial_bearing)
    compass_bearing = (initial_bearing + 360) % 360

    return compass_bearing

# Rough Calculation of distance (in meters)
# https://janakiev.com/blog/gps-points-distance-python/
def haversine(coord1, coord2):
    R = 6372800  # Earth radius in meters
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    
    phi1, phi2 = math.radians(lat1), math.radians(lat2) 
    dphi       = math.radians(lat2 - lat1)
    dlambda    = math.radians(lon2 - lon1)
    
    a = math.sin(dphi/2)**2 + \
        math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    
    return 2*R*math.atan2(math.sqrt(a), math.sqrt(1 - a))

while True:
    # Here's our menu system for the Adafruit CLUE
    # Thanks to foamyguy on the Adafruit Discord server for helping me get the button click feature
    # Menus are all pretty simple- set them all up and turn them off as we go through them
    if clue.button_a:
        # Turn on all menus to true, then turn them off as we toggle through them
        latmenux1 = True
        latmenux001 = True
        lonmenux1 = True
        lonmenux001 = True
        gpsmenu_target = True
        gpsmenu_stats = True

        # Display just the basic target info
        while gpsmenu_target is True:
            clue_display[0].text = "--Target Coordinates--"
            clue_display[1].text = ""
            clue_display[2].text = "Lat: {:.5f}".format(target_lat)
            clue_display[3].text = "Lon: {:.5f}".format(target_lon)
            clue_display[4].text = ""
            clue_display[5].text = ""
            clue_display[6].text = ""
            clue_display[7].text = ""
            clue_display[8].text = "B=Next"
            clue_display.show()
            if clue.button_b:
                gpsmenu_target = False
                clue_display.show()
        
        # Parse and display several GPS stats
        while gpsmenu_stats is True:
            gps.update()
            current = time.monotonic()
            if current - last_print >= 1.0:
                last_print = current
            if not gps.has_fix:
                # Try again if we don't have a fix yet.
                clue_display[0].text = "Waiting for fix"
                continue
            # We have a fix! (gps.has_fix is true)
            # Print out details about the fix like location, date, etc.
            clue_display[0].text = "--GPS Info--"
            clue_display[1].text = ""
            clue_display[2].text = "Lat: {:.5f}".format(gps.latitude)
            clue_display[3].text = "Long: {:.5f}".format(gps.longitude)
            clue_display[4].text = "GPS Sat#: {:.5f}".format(gps.satellites)
            clue_display[5].text = "Altitude: {:.5f}".format(gps.altitude_m)
            clue_display[6].text = "Track Angle: {:.5f}".format(gps.track_angle_deg)
            clue_display[7].text = "{}/{}/{} {:02}:{:02}:{:02}".format(
                gps.timestamp_utc.tm_mon,   # Grab parts of the time from the
                gps.timestamp_utc.tm_mday,  # struct_time object that holds
                gps.timestamp_utc.tm_year,  # the fix time.  Note you might
                gps.timestamp_utc.tm_hour,  # not get all data like year, day,
                gps.timestamp_utc.tm_min,   # month!
                gps.timestamp_utc.tm_sec)
            clue_display[8].text = "B=Next"
            clue_display.show()
            if clue.button_b:
                gpsmenu_stats = False
                clue_display.show()
        
        # Change the target latitude by intigers of 1
        while latmenux1 is True:
            clue_display[0].text = "Set Target Lat."
            clue_display[1].text = "Temp-Lat: {:.5f}".format(target_lat)
            clue_display[2].text = "Temp-Lon: {:.5f}".format(target_lon)
            clue_display[3].text = " "
            clue_display[4].text = " "
            clue_display[5].text = " "
            clue_display[6].text = "0=+1"
            clue_display[7].text = "2=-1"
            clue_display[8].text = "B=Next"
            clue_display.show()
            if clue.touch_0:
                target_lat = target_lat - 1
                clue_display[1].text = "Temp-Lat: {:.5f}".format(target_lat)
            if clue.touch_2:
                target_lat = target_lat + 1
                clue_display[1].text = "Temp-Lat: {:.5f}".format(target_lat)
            if clue.button_b:
                latmenux1 = False
                clue_display.show()
        
        # Change the target latitude by increments of .001
        while latmenux001 is True:
            clue_display[0].text = "Set Target Lat."
            clue_display[1].text = "Temp-Lat: {:.5f}".format(target_lat)
            clue_display[2].text = "Temp-Lon: {:.5f}".format(target_lon)
            clue_display[3].text = " "
            clue_display[4].text = " "
            clue_display[5].text = " "
            clue_display[6].text = "0=+.001"
            clue_display[7].text = "2=-.001"
            clue_display[8].text = "B=Next"
            clue_display.show()
            if clue.touch_0:
                target_lat = target_lat - 0.001
                clue_display[1].text = "Temp-Lat: {:.5f}".format(target_lat)
            if clue.touch_2:
                target_lat = target_lat + 0.001
                clue_display[1].text = "Temp-Lat: {:.5f}".format(target_lat)
            if clue.button_b:
                latmenux001 = False
                clue_display.show()
        
        # Change the target longitude by intigers of 1
        while lonmenux1 is True:
            clue_display[0].text = "Set Target Lon."
            clue_display[1].text = "Temp-Lat: {:.5f}".format(target_lat)
            clue_display[2].text = "Temp-Lon: {:.5f}".format(target_lon)
            clue_display[3].text = " "
            clue_display[4].text = " "
            clue_display[5].text = " "
            clue_display[6].text = "0=+.001"
            clue_display[7].text = "2=-.001"
            clue_display[8].text = "B=Next"
            clue_display.show()
            if clue.touch_0:
                target_lon = target_lon - 1
                clue_display[2].text = "Temp-Lon: {:.5f}".format(target_lon)
            if clue.touch_2:
                target_lon = target_lon + 1
                clue_display[2].text = "Temp-Lon: {:.5f}".format(target_lon)
            if clue.button_b:
                lonmenux1 = False
                clue_display.show()
        
        # Change the target longitude by increments of .001
        while lonmenux001 is True:
            clue_display[0].text = "Set Target Lon."
            clue_display[1].text = "Temp-Lat: {:.5f}".format(target_lat)
            clue_display[2].text = "Temp-Lon: {:.5f}".format(target_lon)
            clue_display[3].text = " "
            clue_display[4].text = " "
            clue_display[5].text = " "
            clue_display[6].text = "0=+.001"
            clue_display[7].text = "2=-.001"
            clue_display[8].text = "B=Next"
            clue_display.show()
            if clue.touch_0:
                target_lon = target_lon - 0.001
                clue_display[2].text = "Temp-Lon: {:.5f}".format(target_lon)
            if clue.touch_2:
                target_lon = target_lon + 0.001
                clue_display[2].text = "Temp-Lon: {:.5f}".format(target_lon)
            if clue.button_b:
                lonmenux001 = False
                clue_display.show()
    else:
        # We need to make sure all the GPS sections are actively updating GPS otherwise info gets stale
        gps.update()
        current = time.monotonic()
        if current - last_print >= 1.0:
            last_print = current
            if not gps.has_fix:
                # Try again if we don't have a fix yet.
                clue_display[0].text = "Waiting for fix"
                continue
            # We have a fix! (gps.has_fix is true)
            # Our default navigation screen that shows current heading, distance to target, and heading to target
            clue_display[0].text = "--Navigation--"
            clue_display[1].text = ""
            current_pos = (gps.latitude, gps.longitude)
            target_pos = (target_lat, target_lon)
            clue_display[2].text = "Current Heading:" 
            clue_display[3].text = " {:.2f} degrees".format(get_heading(sensor))
            clue_display[4].text = "Target Heading:" 
            clue_display[5].text = " {:.1f} deg".format(calculate_initial_compass_bearing(current_pos,target_pos))
            clue_display[6].text = "Target Distance"
            clue_display[7].text = " {:.1f} meters".format(haversine(current_pos,target_pos))
            clue_display[8].text = "A=Toggle Display"
            clue_display.show()