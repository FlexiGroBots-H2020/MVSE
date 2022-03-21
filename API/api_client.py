import time
import socket
import paho.mqtt.client as mqttClient
import concurrent.futures
import json

CONF_FILE_NAME = "api_conf.json"

with open(CONF_FILE_NAME) as f:
    param = json.loads(f.read())

TARGET_INSTANCE = param["TARGET_INSTANCE"]
UDP_IP = param["UDP_IP"]
UDP_PORT_PX4_TO_API = param["UDP_PORT_PX4_TO_API"]
UDP_PORT_API_TO_PX4 = param["UDP_PORT_API_TO_PX4"]
MQTT_BROKER_ADD = param["MQTT_BROKER_ADD"]
MQTT_PORT = param["MQTT_PORT"]
BASE_MQTT_CLIENT_NAME = param["BASE_MQTT_CLIENT_NAME"]  #"api_1*_side"
BASE_TOPIC_API_TO_PX4 = param["BASE_TOPIC_API_TO_PX4"]  #"/3009/1*/api_to_px4"
BASE_TOPIC_PX4_TO_API = param["BASE_TOPIC_PX4_TO_API"]  #"/3009/*/px4_to_api"

TOPIC_API_TO_PX4 = BASE_TOPIC_API_TO_PX4.replace("*", str(TARGET_INSTANCE))
TOPIC_PX4_TO_API = BASE_TOPIC_PX4_TO_API.replace("*", str(TARGET_INSTANCE))
CLIENT_NAME = BASE_MQTT_CLIENT_NAME.replace("*", str(TARGET_INSTANCE))

print("Starting MQTT-API interface... Target PX4 instance: "+str(TARGET_INSTANCE))
print("UDP ports for PX4-API: "+str(UDP_PORT_API_TO_PX4)+", "+str(UDP_PORT_PX4_TO_API))
print("Subscribed to topics: "+TOPIC_PX4_TO_API)
print("Publishing to topics: "+TOPIC_API_TO_PX4)
print("MQTT broker on address: "+MQTT_BROKER_ADD+", port "+str(MQTT_PORT))

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP,UDP_PORT_PX4_TO_API))

Connected = False

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to broker as: "+CLIENT_NAME)
        global Connected                #Use global variable
        Connected = True                #Signal connection 
    else:
        print("Connection failed")
  
def on_message(client, userdata, message):
    sock.sendto(message.payload,(UDP_IP, UDP_PORT_API_TO_PX4))

def rec_pub(sock, topic, client):
    while True:
        data, addr = sock.recvfrom(1024)
        client.publish(topic, data)
        print("received from API")

Connected = False
client = mqttClient.Client(CLIENT_NAME)
client.on_connect = on_connect
client.on_message = on_message

client.connect(MQTT_BROKER_ADD, MQTT_PORT)
client.loop_start()

while Connected != True:
    time.sleep(0.1)
    
client.subscribe(TOPIC_PX4_TO_API)

with concurrent.futures.ThreadPoolExecutor() as executor:
    r1 = executor.submit(rec_pub, sock,TOPIC_API_TO_PX4,client)