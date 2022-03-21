import paho.mqtt.client as mqttClient
import time
from socket import *
import sys
import concurrent.futures
import json

CONF_FILE_NAME = "qgc_side_conf.txt"

with open(CONF_FILE_NAME) as f:
    param = json.loads(f.read())

UDP_IP = param["UDP_IP"]
DEV_N = param["DEV_N"]
QGC_INST = param["QGC_INST"]
BASE_UDP_PORT_TO_PX4 = param["BASE_UDP_PORT_TO_PX4"]
UDP_PORT_TO_QGC = param["UDP_PORT_TO_QGC"]
MQTT_BROKER_ADD = param["MQTT_BROKER_ADD"]
MQTT_PORT = param["MQTT_PORT"]
BASE_TOPIC_QGC_TO_PX4 = param["BASE_TOPIC_QGC_TO_PX4"]
BASE_TOPIC_PX4_TO_QGC = param["BASE_TOPIC_PX4_TO_QGC"]
BASE_MQTT_CLIENT_NAME = param["BASE_MQTT_CLIENT_NAME"]

TOPIC_EDEV_TO_QGC = "/3009/100/edev_to_qgc"

verbose = False

UDP_PORT_TO_PX4_l = [BASE_UDP_PORT_TO_PX4+i for i in range(DEV_N)]      #[18570,18571,...]

topics_o = [BASE_TOPIC_QGC_TO_PX4.replace("*",str(i+1)) for i in range(DEV_N)]
topics_i = [BASE_TOPIC_PX4_TO_QGC.replace("*",str(i+1)) for i in range(DEV_N)]

MQTT_CLIENT_NAME = BASE_MQTT_CLIENT_NAME.replace("*",str(QGC_INST))

socket_edev = socket(AF_INET, SOCK_DGRAM)

socket_l = [socket(AF_INET, SOCK_DGRAM) for _ in range(DEV_N)]
for i in range(DEV_N):
    socket_l[i].bind((UDP_IP, UDP_PORT_TO_PX4_l[i]))

if len(sys.argv) == 2:          #check is verbose is on
    if sys.argv[1]== "-v":
        verbose=True

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        if verbose:
            print("Connected to broker")
        global Connected                #Use global variable
        Connected = True                #Signal connection 
    else:
        if verbose:
            print("Connection failed")
  
def on_message(client, userdata, message):
    global socket_l
    if (message.topic == topics_i[0]):
        socket_l[0].sendto(message.payload, (UDP_IP ,UDP_PORT_TO_QGC))
    elif (message.topic == topics_i[1]):
        socket_l[1].sendto(message.payload, (UDP_IP ,UDP_PORT_TO_QGC))
    elif message.topic == TOPIC_EDEV_TO_QGC:
        socket_edev.sendto(message.payload,(UDP_IP,UDP_PORT_TO_QGC))
        print("recv from edev")
    
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
    
