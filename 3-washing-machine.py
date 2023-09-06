import time
import random
import json
import asyncio
import aiomqtt
import sys 
import os
from enum import Enum

student_id = "6310301031"

class MachineStatus(Enum):
    pressure = round(random.uniform(2000,3000), 2)
    temperature = round(random.uniform(25.0,40.0), 2)

class MachineMaintStatus(Enum):
    filter = random.choice(["clear", "clogged"])
    noise = random.choice(["quiet", "noisy"])

class WashingMachine:
    def __init__(self, serial):
        self.MACHINE_STATUS = 'OFF'
        self.SERIAL = serial

async def publish_message(w, client, app, action, name, value):
    print(f"{time.ctime()} - [{w.SERIAL}] {name}:{value}")
    await asyncio.sleep(2)
    payload = {
                "action"    : "get",
                "project"   : student_id,
                "model"     : "model-01",
                "serial"    : w.SERIAL,
                "name"      : name,
                "value"     : value
            }
    print(f"{time.ctime()} - PUBLISH - [{w.SERIAL}] - {payload['name']} > {payload['value']}")
    await client.publish(f"v1cdti/{app}/{action}/{student_id}/model-01/{w.SERIAL}"
                        , payload=json.dumps(payload))

async def CoroWashingMachine(w, client):
    while True:
        wait_next = round(10*random.random(),2)
        print(f"{time.ctime()} - [{w.SERIAL}-{w.MACHINE_STATUS}] Waiting to start... {wait_next} seconds.")
        await asyncio.sleep(wait_next)
        if w.MACHINE_STATUS == 'OFF':
            continue
        if w.MACHINE_STATUS == 'READY':
            print(f"{time.ctime()} - [{w.SERIAL}-{w.MACHINE_STATUS}]")


            await publish_message(w, client, "app", "get", "STATUS", "READY")
            # door close
            await publish_message(w, client, "app", "get", "Operation", "DOORCLOSE")
            # fill water untill full level detected within 10 seconds if not full then timeout
            w.MACHINE_STATUS = 'FILLWATER' 
            await publish_message(w, client, "app", "get", "STATUS", "FILLWATER")
            # heat water until temperature reach 30 celcius within 10 seconds if not reach 30 celcius then timeout

            # wash 10 seconds, if out of balance detected then fault
            await publish_message(w, client, "app", "get", "STATUS", "WASH")

            # rinse 10 seconds, if motor failure detect then fault
            await publish_message(w, client, "app", "get", "STATUS", "RINSE")

            # spin 10 seconds, if motor failure detect then fault
            await publish_message(w, client, "app", "get", "STATUS", "SPIN")

            # ready state set 
            await publish_message(w, client, "app", "get", "STATUS", "FILLWATER")

            # When washing is in FAULT state, wait until get FAULTCLEARED
            await publish_message(w, client, "app", "get", "STATUS", "FILLWATER")

            w.MACHINE_STATUS = 'OFF'
            await publish_message(w, client, "app", "get", "STATUS", w.MACHINE_STATUS)
            continue
            

async def listen(w, client):
    async with client.messages() as messages:
        await client.subscribe(f"v1cdti/hw/set/{student_id}/model-01/{w.SERIAL}")
        async for message in messages:
            m_decode = json.loads(message.payload)
            if message.topic.matches(f"v1cdti/hw/set/{student_id}/model-01/{w.SERIAL}"):
                # set washing machine status
                print(f"{time.ctime()} - MQTT - [{m_decode['serial']}]:{m_decode['name']} => {m_decode['value']}")
                if (m_decode['name']=="STATUS" and m_decode['value']=="READY"):
                    w.MACHINE_STATUS = 'READY'

async def main():
    w = WashingMachine(serial='SN-001')
    async with aiomqtt.Client("broker.emqx.io") as client:
        await asyncio.gather(listen(w, client) , CoroWashingMachine(w, client)
                             )
        
# Change to the "Selector" event loop if platform is Windows
if sys.platform.lower() == "win32" or os.name.lower() == "nt":
    from asyncio import set_event_loop_policy, WindowsSelectorEventLoopPolicy
    set_event_loop_policy(WindowsSelectorEventLoopPolicy())

asyncio.run(main())