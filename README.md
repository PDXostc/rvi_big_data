# BIG DATA DEMO #

# ATS TAXI DATA SIMULATOR #
The ATS Taxi data simulator is used to provide a simulated real time
feed of up to 537 taxi cabs using data provided for free by
cabspotting.org

The simulator is provided as ats_taxi_simulator.py, which will open
one or more waypoint files from the cabspottingdata subdirectires and
transmit them in real time to the backend system.


## STANDALONE TESTING

To test the taxi data simulator a dummy service is setup to receive
data delivered by the taxi simulator. Both the simulator and dummy
service use a local RVI node to communicate.

## BUILDING THE RVI NODE

If no existing RVI node exist one can be built and started on yo
Check out the following repo:

   https://github.com/PDXostc/rvi

and follow the instructions at in ```BUILD.md```.

### Setup the RVI node

In the ```rvi``` directory, create a node using the standard backend
setup:

    ./scripts/setup_rvi_node.sh  -d -n backend -c backend.config

### Start the RVI node

In the ```rvi``` directory, launch the newly setup node in developer
mode:

    ./scripts/rvi_node.sh -n backend

Exit out of the RVI node by pressing ```ctrl-c ctrl-c```


## REGISTERING THE DUMMY SERVICE

Go to the ```rvi/python``` subdirectory.

Ensure that jsonprclib is installed as shown in
 ```rvi/python/README.md```

Go to the rvi/python directory and launch the dummy service, having it connect
to the local RVI node:

    ./rvi_service.py  http://localhost:8801 /logging/report

## [1/2] STARTING THE SIMULATOR

The simulator is started with one or more waypoint files from the unpacked
```cabspottingdata.tar.gz``` tarball.

Start the simulator from the directory where this ```README.md``` file resides:

    ./ats_taxi_simulator.py http://localhost:8801 cabspottingdata/new_eshroa.txt

The simulator will connect to the local RVI node and send content of a
single wayppoint file ```cabspottingdata/new_eshroa.txt``` to the
dummy service registered above.


## [2/2] USING DOCKER TO HOST THE SIMULATOR

All necessary files are present to create and execute a docker
container hosting the simulator.

**NOTE: Since docker containers have issues connecting to localhost,
the instructions below use the public RVI at
```rvi1.nginfotpdx.net```. <br>In these cases, the dummy service
should be executed directly on the ```rvi1``` host to avoid firewall
issues when the RVI node sends HTTP requests to it**

### Build the simulator docker container

Create a docker container for the simulator by running the following
command in the directory where this ```README.md``` file resides:

    sudo docker build  -t ats_simulator .

### Launch the simulator docker container

Launch the docker container, having it connect to the RVI node
at ```rvi1.nginfotpdx.net```:

	sudo docker run -ti --rm ats_simulator \
	   http://rvi1.nginfotpdx.net:8801 cabspottingdata/new_eshroa.txt


# RVI SERVICVES AND THEIR FORMATS #

The following chapters describe the service invocation between the taxi
simulator and backend node.

## SUBSCRIBE (NOT IMPLEMENTED) ##

Subscribe commands are sent from the backend server to a vehicle in order
to setup a regular reporting of specific data from vehicle to server.

Reporting will be done through the ```report``` command.

Multiple subscribe commands can be sent, where all indicated channels are
reported 

     {
		 "jsonrpc": "2.0",
	     "id": 1,
	     "method": "message",
		 "params": {
			 "service": "jlr.com/vin/123456/logging/subscribe",
		     "channels":, ["location", "odometer", "speed"],
			 "reporting_interval": 5000
		 }
	 } 

### Parameters ###
+ channels<br>
Specifies the channels that we want reported back to the server.

+ reporting_interval<br>
Specifies the number of milliseconds between each data sample that is
to be sent back end server.  If the reporting interval is a negative
integer, the channel's value will be reported at the given (absolute
value) interval, or when the value changes, whatever happens first.


## UNSUBSCRIBE ##

Unubscribe commands are sent from the backend server to a vehicle in
order to stop reporting of one or more data channels previously setup
through a ```subscribe``` command.

     {
		 "jsonrpc": "2.0",
	     "id": 2,
	     "method": "message",
		 "params": {
			 "service": "jlr.com/vin/123456/logging/unsubscribe",
		     "channels":, ["location", "odometer", "speed"]
		 }
	 } 

### Parameters ###
+ channels<br>
Specifies the channels to stop reporting. If a channel has been
specified several times by multiple subcribe commands, all
subscriptions to the channel are removed.

## REPORT ##

Publish commands are sent from the device to the backend server to report
a batch of values for channels previously subscribed to by a ```subscribe``` command.
Multiple values for a single channel can be provided in a single report.

Each channel is reported with its channel name, its value, and the UTC
msec timestamp when the value was sample.

     {
		 "jsonrpc": "2.0",
	     "id": 3,
	     "method": "message",
		 "params": {
			 "service": "jlr.com/backend/logging/report",
	         "vin":  "1234",
	         "timestamp":  1415143459110,
		     "data":, [
				 { "channel": "odometer", "value": 10022 },
				 { "channel": "odometer", "value": 10023 },
				 { "channel": "speed", "value": 113 },
				 { "channel": "location",
				   "value": { "lat": 39.0319, "lon": 125.7538, "alt": 222.3 } } 		 
	         ]
		 }
	 } 


### Parameters ###
+ data<br>
Contains an array of all reported data points.

+ channel<br>
Contains the name of the channel a data point is reporetd for. Matches
the channel name in a previously issued ```subscribe``` command.

+ value<br>
Specifies the value of the given channel at the given time. The actual
value can be a string, a double, or a JSON object, and is implicitly
defined by the channel name.

+ timestamp<br>
Specifies the timestamp in millisecond UTC when the value was sampled
from the vehicle.



