import paho.mqtt.client as mqttClient
import time
import socket
import sys
from numpy import array
from numpy.linalg import norm
import concurrent.futures
import json
import shutil
import os.path
verbose = False
if len(sys.argv) == 2:
    if sys.argv[1]== "-v":
        verbose = True
print("Insert instance number (1-9) and press enter... ")
INSTANCE_NUMBER = int(input())
while INSTANCE_NUMBER < 1 or INSTANCE_NUMBER > 9:
    print("Instance number out of addressable range (1-9), please insert a valid one... ")
    INSTANCE_NUMBER = int(input())

CONF_FILE_NAME = "px4_conf.json"

# Parameter import from configuration file
with open(CONF_FILE_NAME) as f:
    param = json.loads(f.read())
UDP_IP = param["UDP_IP"]
UDP_PORT_QGC_TO_PX4 = param["UDP_PORT_QGC_TO_PX4"]
UDP_PORT_PX4_TO_QGC = param["UDP_PORT_PX4_TO_QGC"]
UDP_PORT_API_TO_PX4 = param["UDP_PORT_API_TO_PX4"]
UDP_PORT_PX4_TO_API = param["UDP_PORT_PX4_TO_API"]
API_KEY = param["API_KEY"]
TOPIC_PX4_TO_API = param["BASE_TOPIC_PX4_TO_API"].replace("*",str(INSTANCE_NUMBER)).replace("api-key", API_KEY)
TOPIC_API_TO_PX4 = param["BASE_TOPIC_API_TO_PX4"].replace("*",str(INSTANCE_NUMBER)).replace("api-key", API_KEY)
TOPIC_QGC_TO_PX4 = param["BASE_TOPIC_QGC_TO_PX4"].replace("*",str(INSTANCE_NUMBER)).replace("api-key", API_KEY)
TOPIC_PX4_TO_QGC = param["BASE_TOPIC_PX4_TO_QGC"].replace("*",str(INSTANCE_NUMBER)).replace("api-key", API_KEY)
TOPIC_TO_FIWARE = param["BASE_TOPIC_TO_FIWARE"].replace("*",str(INSTANCE_NUMBER)).replace("api-key", API_KEY)
CLIENT_NAME = param["CLIENT_NAME"].replace("*",str(INSTANCE_NUMBER))
MQTT_BROKER_ADD = param["MQTT_BROKER_ADD"]
MQTT_PORT = param["MQTT_PORT"]
MQTT_BROKER_USERNAME = param["MQTT_BROKER_USERNAME"]
MQTT_BROKER_PASSWORD = param["MQTT_BROKER_PASSWORD"]
ENABLE_API = param["ENABLE_API"]
ENABLE_FIWARE = param["ENABLE_FIWARE"]

# PX4-Autopilot and jMAVSim configuration file edit

with open("px4-rc.params", "r") as px4_param_file:
    px4_param = px4_param_file.readlines()
px4_param[3] = px4_param[3].replace("INSTANCE_NUMBER", str(INSTANCE_NUMBER))

with open(os.path.dirname(__file__)+"/../ROMFS/px4fmu_common/init.d-posix/px4-rc.params", "w") as px4_new_param_file:
    px4_new_param_file.writelines(px4_param)

shutil.copy2("px4-rc.mavlink", os.path.dirname(__file__)+"/../ROMFS/px4fmu_common/init.d-posix/")

with open(os.path.dirname(__file__)+"/../Tools/jMAVSim/src/me/drton/jmavsim/Simulator.java", "r") as sim_file:
    sim = sim_file.readlines()
sim[81] = "public static LatLonAlt DEFAULT_ORIGIN_POS = new LatLonAlt(65.056680, 25.458728, 1);"
with open(os.path.dirname(__file__)+"/../Tools/jMAVSim/src/me/drton/jmavsim/Simulator.java", "w") as sim_file:
    sim_file.writelines(sim)

# Print some useful information

print("Starting MQTT link for instance #"+str(INSTANCE_NUMBER))
print("UDP ports for PX4-QGC: "+str(UDP_PORT_QGC_TO_PX4)+", "+str(UDP_PORT_PX4_TO_QGC))
if ENABLE_API:
    print("UDP ports for PX4-API: "+str(UDP_PORT_API_TO_PX4)+", "+str(UDP_PORT_PX4_TO_API))
print("Subscribed to topics: "+TOPIC_API_TO_PX4+", "+TOPIC_QGC_TO_PX4)
print("Publishing to topics: "+TOPIC_PX4_TO_API+", "+TOPIC_PX4_TO_QGC)
print("MQTT broker on address: "+MQTT_BROKER_ADD+", port "+str(MQTT_PORT))

#global variable for telemetry data from MAVLink messages
tele = {}

# socket that listens PX4 UDP messages to forward them via MQTT
socket_to_qgc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
socket_to_qgc.bind((UDP_IP, UDP_PORT_PX4_TO_QGC))               

# socket for PX4-API communication
if ENABLE_API:
    socket_to_api = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    socket_to_api.bind((UDP_IP, UDP_PORT_PX4_TO_API))


# MQTT client handler
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        if verbose:
            print("Connected to broker")
        global Connected                #Use global variable
        Connected = True                #Signal connection 
    else:
        print("Connection failed")

# Send over UDP to PX4 message received from MQTT by QGC or APIs  
def on_message(client, userdata, message):

    if message.topic == TOPIC_QGC_TO_PX4:
        socket_to_qgc.sendto(message.payload,(UDP_IP, UDP_PORT_QGC_TO_PX4))
    
    if message.topic == TOPIC_API_TO_PX4 and ENABLE_API:
        socket_to_api.sendto(message.payload,(UDP_IP, UDP_PORT_API_TO_PX4))

# Receive UDP packets from sock and publish them under "topic" from "client"
def rec_pub(sock, topic, client):
    msg_code = 0
    while True:
        data, addr = sock.recvfrom(1024)
        if verbose:
            print("received: " + topic)
        client.publish(topic, data)
        # MAVlink message decoding block
        if ENABLE_FIWARE:
            if topic == TOPIC_PX4_TO_QGC:
                msg_code = int.from_bytes(data[7:10], byteorder="little")
            if msg_code == 33:
                tele["lat"] = int.from_bytes(data[14:18], byteorder= "little")/1e7
                tele["lon"] = int.from_bytes(data[18:22], byteorder= "little")/1e7
                tele["alt"] = int.from_bytes(data[22:26], byteorder= "little")/1e3
                tele["ele"] = int.from_bytes(data[26:30], byteorder= "little")/1e3
                tele["vx"] = int.from_bytes(data[30:32], byteorder= "little")/1e2
                tele["vy"] = int.from_bytes(data[32:34], byteorder= "little")/1e2
                tele["vz"] = int.from_bytes(data[34:36], byteorder= "little")/1e2
                tele["hdg"] = int.from_bytes(data[36:38], byteorder= "little")/100
                tele["v"] = norm(array([tele["vx"],tele["vy"],tele["vz"]]))

                S = "lat|"+str(tele["lat"])+"|lon|"+str(tele["lon"])+"|ele|"+str(tele["ele"])+"|h|"+str(tele["hdg"])+"|v|"+str(tele["v"])
                client.publish(TOPIC_TO_FIWARE, S)
                
                if verbose:
                    print(TOPIC_TO_FIWARE + ": " + S)


# MQTT client instance start
Connected = False   #global variable for the state of the MQTT connection
client = mqttClient.Client(CLIENT_NAME)
client.on_connect= on_connect       #attach function to callback (connection)
client.on_message= on_message       #attach function to callback (message received)
if MQTT_BROKER_USERNAME != "" and MQTT_BROKER_PASSWORD != "":
    client.username_pw_set(MQTT_BROKER_USERNAME, MQTT_BROKER_PASSWORD)
client.connect(MQTT_BROKER_ADD, port=MQTT_PORT)
client.loop_start()        #start the loop 
while Connected != True:    #Wait for connection
    time.sleep(0.1)
client.subscribe(TOPIC_QGC_TO_PX4)
if ENABLE_API:
    client.subscribe(TOPIC_API_TO_PX4)

# concurrent execution of rec_pub function instances, required since sockets are "blocking"
with concurrent.futures.ThreadPoolExecutor() as executor:
    r_qgc = executor.submit(rec_pub,socket_to_qgc, TOPIC_PX4_TO_QGC,client)
    if ENABLE_API:
        r_api = executor.submit(rec_pub,socket_to_api, TOPIC_PX4_TO_API,client)
