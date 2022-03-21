import os
import paho.mqtt.client as mqttClient
import time
from socket import *
import sys
import concurrent.futures
import json
os.environ["MAVLINK20"] = "1"
os.environ["MAVLINK_DIALECT"] = "standard"
from pymavlink import mavutil

CONF_FILE_NAME = "qgc_side_conf.json"
with open(CONF_FILE_NAME) as f:
    param = json.loads(f.read())
UDP_IP = param["UDP_IP"]
DEV_N = param["DEV_N"]
QGC_INST = param["QGC_INST"]
API_KEY = param["API_KEY"]
BASE_UDP_PORT_TO_PX4 = param["BASE_UDP_PORT_TO_PX4"]
UDP_PORT_TO_QGC = param["UDP_PORT_TO_QGC"]
MQTT_BROKER_ADD = param["MQTT_BROKER_ADD"]
MQTT_PORT = param["MQTT_PORT"]
BASE_TOPIC_QGC_TO_PX4 = param["BASE_TOPIC_QGC_TO_PX4"].replace('api-key', API_KEY)
BASE_TOPIC_PX4_TO_QGC = param["BASE_TOPIC_PX4_TO_QGC"].replace('api-key', API_KEY)
BASE_MQTT_CLIENT_NAME = param["BASE_MQTT_CLIENT_NAME"].replace('api-key', API_KEY)
EDEV_N = param["EDEV_N"]
TOPIC_EDEV_TO_QGC = param["TOPIC_EDEV_TO_QGC"].replace('api-key', API_KEY)
EDEV_ENABLE = param["EDEV_ENABLE"]
MQTT_CLIENT_NAME = BASE_MQTT_CLIENT_NAME.replace("*",str(QGC_INST))

verbose = False
## List of UDP ports and sockets on which QGC expect the MAVLink communication for different PX4 instances
UDP_PORT_TO_PX4_l = [BASE_UDP_PORT_TO_PX4+i for i in range(DEV_N)]
socket_l = [socket(AF_INET, SOCK_DGRAM) for _ in range(DEV_N)]
for i in range(DEV_N):
    socket_l[i].bind((UDP_IP, UDP_PORT_TO_PX4_l[i]))

## Lists of MQTT topics
topics_o = [BASE_TOPIC_QGC_TO_PX4.replace("*",str(i+1)) for i in range(DEV_N)]
topics_i = [BASE_TOPIC_PX4_TO_QGC.replace("*",str(i+1)) for i in range(DEV_N)]
## List of mavutil objects for simulating MAVLink communication from external devices to QGC
edev_l = [mavutil.mavlink_connection("udpout:localhost:14550", source_system=(100+i), source_component=1) for i in range(EDEV_N)]

# print("Starting MQTT link for instance #"+str(QGC_INST))
# print("Number of PX4-Autopilots: ", DEV_N)
# if EDEV_ENABLE:
#     print("External devices interface enabled")
#     print("Number of external devices: ", EDEV_N)
# print("UDP ports for PX4-QGC: ", UDP_PORT_TO_PX4_l)
# print("UDP port to QGC: ", UDP_PORT_TO_QGC)

if len(sys.argv) == 2:          #check is verbose is on
    if sys.argv[1]== "-v":
        verbose=True

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to broker")
        global Connected                #Use global variable
        Connected = True                #Signal connection 
    else:
        print("Connection failed")

def edev_send(edev_l, topic, payload):
    n = int(topic.split("/")[2]) -100
    if n >= 0 and n < EDEV_N:
        l = str(payload).split("|")
        lat = int(float(l[1])*1E7)
        lon = int(float(l[3])*1E7)
        edev_l[n].mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_FREE_BALLOON, mavutil.mavlink.MAV_AUTOPILOT_INVALID, 0, 0, 0)
        edev_l[n].mav.global_position_int_send(0,lat,lon,10,10,0,0,0,0)

def on_message(client, userdata, message):
    global socket_l
    if (message.topic == topics_i[0]):
        socket_l[0].sendto(message.payload, (UDP_IP ,UDP_PORT_TO_QGC))
    elif (message.topic == topics_i[1]):
        socket_l[1].sendto(message.payload, (UDP_IP ,UDP_PORT_TO_QGC))
    elif EDEV_ENABLE == 1:
        edev_send(edev_l, message.topic, message.payload)
    
def rec_pub(client, instance_n):
    global socket_l
    counter = 0
    while True:
        #print("waiting for "+topics_o[instance_n])
        #print(counter)
        counter +=1
        data, addr = socket_l[instance_n].recvfrom(1024)
        if verbose:
            print ("Received " +topics_o[instance_n])
        client.publish(topics_o[instance_n],data, qos = 0)

Connected = False   #global variable for the state of the connection 
client = mqttClient.Client(MQTT_CLIENT_NAME)             #create new instance
client.on_connect= on_connect                      #attach function to callback
client.on_message= on_message     

client.connect(MQTT_BROKER_ADD, port=MQTT_PORT)          #connect to broker
  
client.loop_start()        #start the loop
  
while Connected != True:    #Wait for connection
    time.sleep(0.001)

for t in range(DEV_N):
    client.subscribe(topics_i[t])
    client.subscribe(TOPIC_EDEV_TO_QGC)

with concurrent.futures.ThreadPoolExecutor() as executor:
    results = [executor.submit(rec_pub, client, IN) for IN in range(DEV_N)]
    
