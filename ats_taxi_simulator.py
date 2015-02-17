#!/usr/bin/python

#
# Copyright (C) 2014, Jaguar Land Rover
#
# This program is licensed under the terms and conditions of the
# Mozilla Public License, version 2.0.  The full text of the 
# Mozilla Public License is at https://www.mozilla.org/MPL/2.0/
#

#
# Device simulator reading files from cabsportingdata.
#
import sys
import getopt
import os
import time
from datetime import tzinfo, timedelta, datetime
from signal import *
from rvilib import RVI
import Queue
import threading
MY_NAME = "Big Data Demo"
    
 
class UTC(tzinfo):
    """UTC"""
    def utcoffset(self, dt):
        return timedelta(0)

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return timedelta(0)

class TaxiFileReader():
    """
    Sends data from the database to RVI
    """
    
    # destination - RVI service URL to send data to
    # data_file - File object with lat lon occupancy and unix timestamps ts to transmit
    # rvi_server - The rvi node object
    # speedup - The speedup ratio to send data with. 1.0 = send at interval specced by
    #           timestamps.
    #
    # loop_data - If set, start over with data_file once all elements have been sent
    # adjust_data - If set, use current time as time stamp offset by TS deltas in data file.
    # 
    def __init__(self, file_name, data_sender, speedup, loop_data, adjust_ts):
        self.data_sender = data_sender
        self.speedup = speedup
        self.loop_data = loop_data
        self.adjust_ts = adjust_ts
        self.utc = UTC()

        # File name expected to be: 
        # directory/.../new_[ID].txt'
        # [ID] will be extracted and be used as VIN

        # Remove any directory components, leaving just the filename.
        short_name = os.path.basename(file_name)
        
        # Extract VIN bit of file name
        self.vin = short_name[4:len(short_name)-4]

        self.data_file = open(file_name, "r")

    def start(self):
        self.serve_thread = threading.Thread(target=self.run)
        self.serve_thread.start()

    #
    # Line format:
    #   LAT        LON     O  TS
    #  37.76127 -122.39841 0 1213088776
    #
    # LAT = Latitude
    # LON = Longitude
    # O = Passenger Occupancy 0|1
    # TS = Unix timestamp
    #
    def parse_next_line(self):
        return self.data_file.next().split(" ")

    def run(self):
        print "Will send for {}".format(self.vin)
        # Parse first line to get things going
        try: 
            lat, lon, occupancy, timestamp =  self.parse_next_line()

        except StopIteration:
            return True

        timestamp = int(timestamp)

        # If we are to shift all timestamps to start with the current
        # time, we need to store that time.
        next_send_ts = 0

        if self.adjust_ts == True:
            ts_offset = int(time.time()) - timestamp
        else:
            ts_offset = 0
            
        #
        # Loop through every line in the file, with the first line
        # already being read and parsed above as we enter.
        #
        while True:
            # Sleep until it is time to send the given data
            sleep_interval = (float(next_send_ts) - time.time()) / self.speedup
            if sleep_interval > 0.0:
                print "Will sleep {} for {} seconds.".format(self.vin, sleep_interval)
                time.sleep(sleep_interval)


            # Transmit data
            utc_ts = datetime.fromtimestamp(timestamp + ts_offset, self.utc).isoformat()
            self.data_sender.queue_datapoint(self.vin, utc_ts, lat, lon, '0.0', '0')

            try:
                lat, lon, occupancy, new_timestamp = self.data_file.next().split()
            except StopIteration:
                # If we are in loop mode, reset file
                # descriptor and continue.
                if self.loop_data == True:
                    print "Looping data file"
                    self.data_file.seek(0, os.SEEK_SET)
                    # Read the first line
                    lat, lon, occupancy, timestamp =  self.data_file.next().split()
                    timestamp = int(timestamp)
                    next_send_ts = int(time.time()) + 1
                    continue

                print "Done with file."
                return True

            #
            # Calculate the UTC of the next send event based on the delta
            # between the next record timestamp and that of the current record.
            #
            new_timestamp = int(new_timestamp)
            next_send_ts = int(time.time()) + new_timestamp - timestamp
            timestamp = new_timestamp
    
class DataSender():
    """
    Sends data from the database to RVI
    """
    
    # destination - RVI service URL to send data to
    # data_file - File object with lat lon occupancy and unix timestamps ts to transmit
    # rvi_server - The rvi node object
    # speedup - The speedup ratio to send data with. 1.0 = send at interval specced by
    #           timestamps.
    #
    # loop_data - If set, start over with data_file once all elements have been sent
    # adjust_data - If set, use current time as time stamp offset by TS deltas in data file.
    # 
    def __init__(self, destination, rvi):
        self.destination = destination
        self.rvi = rvi
        self.transaction_id = 1
        self.utc = UTC()
        self.queue = Queue.Queue()


    def queue_datapoint(self, vin, utc_ts, lat, lon, alt, occupancy):
        self.queue.put((vin, utc_ts, lat, lon, alt, occupancy))

    def run(self):
        
        while True:
            (vin, utc_ts, lat, lon, alt, occupancy) = self.queue.get()

            # occupancy not used - yet.
            param = [{
                u'vin': vin,
                u'timestamp': utc_ts,
                u'data': [ { u'channel': 'location',
                             u'value': { u'lat': lat, 
                                         u'lon': lon,
                                         u'alt': alt
                                     } } ]
            }]

            print "Sending to {}: {}".format(self.destination, param)

            rvi.message(self.destination, param)

def cleanup(*args):
    print "Caught signal:", args[0], "Shutting down..."
    # Not much to do here.
    sys.exit(0)

def usage():
    print "Usage: %s [-l] [-s speedup] [-a] RVI-URL file ..." % sys.argv[0]
    print "  RVI-URL      URL of RVI node to use."
    print
    print "  file ...     One or more cab spotting data files to send."
    print "               Filename will be used as vin."
    print 
    print "  -l           Loop data set once exhausted."
    print "               Default is to exit once complete."
    print 
    print "  -a           Adjust timestamps, starting at current system time."
    print "               Default is to use time stamp in data set."
    print
    print "  -s [speedup] Accelerate or slow down period between send."
    print "               Default = 1.0. Higher value -> faster transmission"

    sys.exit(255)

        
if __name__ == "__main__":
    # 
    # Check that we have the correct arguments
    #

    # Grab the URL to use
    loop_data = False
    adjust_ts = False
    speedup = 1.0
    try:
        optlist, remain = getopt.getopt(sys.argv[1:], 'f:ls:a')
    except:
        print "Failed to parse arguments"
        usage()

    if len(remain) < 2:
        usage()

    rvi_url = remain[0]
    if rvi_url[0:7] != 'http://':
        print "No URL provided"
        usage()

    file_names = remain[1:]

    for o, a in optlist:
        if o == '-l':
            loop_data = True

        elif o == '-a':
            adjust_ts = True

        elif o == '-s':
            speedup = float(a)
            
        else:
            usage()
            
    # Welcome message
    print "RVI Big Data Device Simulator"
    print "RVI Node:             ", rvi_url
    print "File(s):              ", file_names
    print "Loop data:            ", loop_data
    print "Speedup:              ", speedup
    print "Adjust time stamp:    ", adjust_ts


    # Setup outbound JSON-RPC connection to the RVI Service Edge
    rvi = RVI(rvi_url)

    # Setup data sender
    data_sender = DataSender("jlr.com/backend/logging/report", rvi)
    

    for file_name in file_names:
        try:
            file_reader = TaxiFileReader(file_name, 
                                         data_sender, 
                                         speedup, 
                                         loop_data, 
                                         adjust_ts)
        except IOError:
            print "Failed to open file {}. Skipped.".format(file_name)

        file_reader.start()


    # catch signals for proper shutdown
    for sig in (SIGABRT, SIGTERM, SIGINT):
        signal(sig, cleanup)

    data_sender.run()
    print "Device simulator finished."
