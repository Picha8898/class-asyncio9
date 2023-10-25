import time
import random
import json
import asyncio
import aiomqtt
import os
import sys
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
        self.Operation = 'CLOSE'
        self.SERIAL = serial

async def waiter(w, event):
    print(f"{time.ctime()} - [{w.SERIAL}-{w.MACHINE_STATUS}] Waiting to start... ")
    await event.wait()
    #print('... got it!')

async def timefillwater(w, time_fill = 100):
    print(f"{time.ctime()} - [{w.SERIAL}-{w.MACHINE_STATUS}] - Another 10 seconds Timeout")
    await asyncio.sleep(time_fill)

async def requi_temp(w, time_fill = 100):
    print(f"{time.ctime()} - [{w.SERIAL}-{w.MACHINE_STATUS}] - Another 10 seconds to Timeout")
    await asyncio.sleep(time_fill)

async def balance(w, time_fill = 100):
    print(f"{time.ctime()} - [{w.SERIAL}-{w.MACHINE_STATUS}] - Another 10 seconds to continue")
    await asyncio.sleep(time_fill)

async def motor(w, time_fill = 100):
    print(f"{time.ctime()} - [{w.SERIAL}-{w.MACHINE_STATUS}] - Another 10 seconds to continue")
    await asyncio.sleep(time_fill)

async def publish_message(w, client, app, action, name, value):
    print(f"{time.ctime()} - [{w.SERIAL}] {name} : {value}")
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
        #wait_next = round(10*random.random(),2)
        #await asyncio.sleep(wait_next)
        # Create an Event object.
        w.event = asyncio.Event()

        # Spawn a Task to wait until 'event' is set.
        waiter_task = asyncio.create_task(waiter(w, w.event))

        # Wait until the waiter task is finished.
        await waiter_task
        if w.MACHINE_STATUS == 'OFF':
            #print(f"{time.ctime()} - [{w.SERIAL}-{w.MACHINE_STATUS}] Waiting to start... ")
            continue
        # When washing is in FAULT state, wait until get FAULTCLEARED
        if w.MACHINE_STATUS == 'FALUT':
            #print(f"{time.ctime()} - [{w.SERIAL}-{w.MACHINE_STATUS}] Waiting to ready...")
            continue
        # ready state set 
        if w.MACHINE_STATUS == 'READY':
            w.Operation = 'CLOSE'
            print(f"{time.ctime()} - [{w.SERIAL}-{w.MACHINE_STATUS}]")
            await publish_message(w, client, "app", "get", "STATUS", "READY")
            # door close
            if w.Operation == 'CLOSE':
                #await publish_message(w, client, "app", "get", "Operation", "DOORCLOSE")
                print(f"{time.ctime()} - [{w.SERIAL}-{w.MACHINE_STATUS}] - User initiates Door closed")
                # fill water untill full level detected within 10 seconds if not full then timeout 
                w.MACHINE_STATUS = "FILLWATER"

                try:
                    async with asyncio.timeout(10):
                        await publish_message(w, client, "app", "get", "STATUS", "FILLWATER")
                        w.Task = asyncio.create_task(timefillwater(w))
                        await w.Task

                except TimeoutError:
                    print(f"{time.ctime()} - [{w.SERIAL}-{w.MACHINE_STATUS}] - TIMEOUT")
                    w.MACHINE_STATUS = 'FALUT'
                    continue

                except asyncio.CancelledError:
                    print(f"{time.ctime()} - [{w.SERIAL}-{w.MACHINE_STATUS}] - Full level detected")
                    w.MACHINE_STATUS = 'HEATWATER'
                    await asyncio.sleep(1)

                if w.MACHINE_STATUS == 'HEATWATER':
                    #await publish_message(w, client, "app", "get", "Operation", "WATERFULLLEVEL")
                    #print(f"{time.ctime()} - [{w.SERIAL}-{w.MACHINE_STATUS}]")
                    # fill water untill full level detected within 10 seconds if not full then timeout 
                    try:
                        async with asyncio.timeout(10):
                            await publish_message(w, client, "app", "set", "STATUS", "HEATWATER")
                            w.Task = asyncio.create_task(requi_temp(w))
                            await w.Task

                    except TimeoutError:
                        print(f"{time.ctime()} - [{w.SERIAL}-{w.MACHINE_STATUS}] - TIMEOUT")
                        w.MACHINE_STATUS = 'FALUT'

                    except asyncio.CancelledError:
                        print(f"{time.ctime()} - [{w.SERIAL}-{w.MACHINE_STATUS}] - Required Temperature reached")
                        w.MACHINE_STATUS = 'WASH'
                        await asyncio.sleep(1)

                if w.MACHINE_STATUS == 'WASH':
                    #await publish_message(w, client, "app", "get", "Operation", "TEMPERATUREREACHED")
                    #print(f"{time.ctime()} - [{w.SERIAL}-{w.MACHINE_STATUS}]")
                    # wash 10 seconds, if out of balance detected then fault
                    try:
                        async with asyncio.timeout(10):
                            await publish_message(w, client, "app", "get", "STATUS", "WASH")
                            w.Task = asyncio.create_task(balance(w))
                            await w.Task

                    except TimeoutError:
                        print(f"{time.ctime()} - [{w.SERIAL}-{w.MACHINE_STATUS}] - Function Completed")
                        w.MACHINE_STATUS = 'RINSE'
                        await asyncio.sleep(1)

                    except asyncio.CancelledError:
                        print(f"{time.ctime()} - [{w.SERIAL}-{w.MACHINE_STATUS}] - Out of balance")
                        w.MACHINE_STATUS = 'FALUT'

                if w.MACHINE_STATUS == 'RINSE':
                    #await publish_message(w, client, "app", "get", "Operation", "OUTOFBALANCE")
                    #print(f"{time.ctime()} - [{w.SERIAL}-{w.MACHINE_STATUS}]")
                    # rinse 10 seconds, if motor failure detect then fault
                    try:
                        async with asyncio.timeout(10):
                            await publish_message(w, client, "app", "get", "STATUS", "RINSE")
                            w.Task = asyncio.create_task(motor(w))
                            await w.Task

                    except TimeoutError:
                        print(f"{time.ctime()} - [{w.SERIAL}-{w.MACHINE_STATUS}] - Function Completed")
                        w.MACHINE_STATUS = 'SPIN'
                        await asyncio.sleep(1)

                    except asyncio.CancelledError:
                        print(f"{time.ctime()} - [{w.SERIAL}-{w.MACHINE_STATUS}] - Motor failure")
                        w.MACHINE_STATUS = 'FALUT'
                        
            # spin 10 seconds, if motor failure detect then fault
            if w.MACHINE_STATUS == 'SPIN':
                    #await publish_message(w, client, "app", "get", "Operation", "OUTOFBALANCE")
                    #print(f"{time.ctime()} - [{w.SERIAL}-{w.MACHINE_STATUS}]")
                    # rinse 10 seconds, if motor failure detect then fault
                    try:
                        async with asyncio.timeout(10):
                            await publish_message(w, client, "app", "get", "STATUS", "SPIN")
                            w.Task = asyncio.create_task(motor(w))
                            await w.Task

                    except TimeoutError:
                        print(f"{time.ctime()} - [{w.SERIAL}-{w.MACHINE_STATUS}] - Function Completed")
                        w.MACHINE_STATUS = 'OFF'
                        await asyncio.sleep(1)

                    except asyncio.CancelledError:
                        print(f"{time.ctime()} - [{w.SERIAL}-{w.MACHINE_STATUS}] - Motor failure")
                        w.MACHINE_STATUS = 'FALUT'

async def listen(w, client):
    async with client.messages() as messages:
        await client.subscribe(f"v1cdti/app/set/{student_id}/model-01/{w.SERIAL}")
        async for message in messages:
            m_decode = json.loads(message.payload)
            if message.topic.matches(f"v1cdti/app/set/{student_id}/model-01/{w.SERIAL}"):
                # set washing machine status
                print(f"{time.ctime()} - MQTT - [{m_decode['serial']}] : {m_decode['name']} => {m_decode['value']}")
                if (m_decode['name']=="STATUS" and m_decode['value']=="READY"):
                    # Sleep for 1 second and set the event.
                    w.event.set()
                    w.MACHINE_STATUS = 'READY'
                elif (m_decode['name']=="Operation" and m_decode['value']=="WATERFULLLEVEL"):
                    w.Operation = 'WATERFULLLEVEL'
                    if w.Task:
                        w.Task.cancel()
                elif (m_decode['name']=="Operation" and m_decode['value']=="TEMPERATUREREACHED"):
                    w.Operation = 'TEMPERATUREREACHED'
                    if w.Task:
                        w.Task.cancel()
                elif (m_decode['name']=="Operation" and m_decode['value']=="OUTOFBALANCE"):
                    w.Operation = 'OUTOFBALANCE'
                    if w.Task:
                        w.Task.cancel()
                elif (m_decode['name']=="Operation" and m_decode['value']=="MOTORFAILURE"):
                    w.Operation = 'MOTORFAILURE'
                    if w.Task:
                        w.Task.cancel()
                if (m_decode['name']=="Operation" and m_decode['value']=="FAULT_CLEAR"):
                     w.event.set()
                     w.MACHINE_STATUS = 'OFF'

async def main():
    w = WashingMachine(serial='SN-001')
    async with aiomqtt.Client("broker.emqx.io") as client:
        await asyncio.gather(listen(w, client) , CoroWashingMachine(w, client))
        

# Change to the "Selector" event loop if platform is Windows
if sys.platform.lower() == "win32" or os.name.lower() == "nt":
    from asyncio import set_event_loop_policy, WindowsSelectorEventLoopPolicy
    set_event_loop_policy(WindowsSelectorEventLoopPolicy())

asyncio.run(main())import time
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