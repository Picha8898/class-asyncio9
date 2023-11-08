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
        self.event = asyncio.Event()

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

async def CoroWashingMachine(w:WashingMachine, client):
    while True:
        #wait_next = round(10*random.random(),2)
        #await asyncio.sleep(wait_next)

        if w.MACHINE_STATUS == 'OFF':
            await publish_message(w, client, "app", "get", "STATUS", "OFF")
            print(f"{time.ctime()} - [{w.SERIAL}-{w.MACHINE_STATUS}] Waiting to start... ")
            await w.event.wait()
            w.event.clear()
            #print(f"{time.ctime()} - [{w.SERIAL}-{w.MACHINE_STATUS}] Waiting to start... ")
            continue
        # When washing is in FAULT state, wait until get FAULTCLEARED
        if w.MACHINE_STATUS == 'FALUT':
            await publish_message(w, client, "app", "get", "STATUS", "FALUT")
            print(f"{time.ctime()} - [{w.SERIAL}-{w.MACHINE_STATUS}] Waiting to Clear falut... ")
            await w.event.wait()
            w.event.clear()
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

                if w.MACHINE_STATUS == 'HEATWATER':
                    #await publish_message(w, client, "app", "get", "Operation", "WATERFULLLEVEL")
                    #print(f"{time.ctime()} - [{w.SERIAL}-{w.MACHINE_STATUS}]")
                    # fill water untill full level detected within 10 seconds if not full then timeout 
                    try:
                        async with asyncio.timeout(10):
                            await publish_message(w, client, "app", "get", "STATUS", "HEATWATER")
                            w.Task = asyncio.create_task(requi_temp(w))
                            await w.Task

                    except TimeoutError:
                        print(f"{time.ctime()} - [{w.SERIAL}-{w.MACHINE_STATUS}] - TIMEOUT")
                        w.MACHINE_STATUS = 'FALUT'

                    except asyncio.CancelledError:
                        print(f"{time.ctime()} - [{w.SERIAL}-{w.MACHINE_STATUS}] - Required Temperature reached")
                        w.MACHINE_STATUS = 'WASH'

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

                    except asyncio.CancelledError:
                        print(f"{time.ctime()} - [{w.SERIAL}-{w.MACHINE_STATUS}] - Motor failure")
                        w.MACHINE_STATUS = 'FALUT'

async def listen(w:WashingMachine, client):
    async with client.messages() as messages:
        await client.subscribe(f"v1cdti/hw/set/{student_id}/model-01/{w.SERIAL}")
        #print(f"{time.ctime()} - [{w.SERIAL}] SUB topic: v1cdti/hw/set/{student_id}/model-01/{w.SERIAL}")
        await client.subscribe(f"v1cdti/hw/get/{student_id}/model-01/")
        #print(f"{time.ctime()} - [{w.SERIAL}] SUB topic: v1cdti/app/get/{student_id}/model-01/")
        async for message in messages:
            m_decode = json.loads(message.payload)
            if message.topic.matches(f"v1cdti/hw/get/{student_id}/model-01/"):
                await publish_message(w, client, "app", "monitor", "STATUS", w.MACHINE_STATUS)
            if message.topic.matches(f"v1cdti/hw/set/{student_id}/model-01/{w.SERIAL}"):
                # set washing machine status
                print(f"{time.ctime()} - MQTT - [{m_decode['serial']}] : {m_decode['name']} => {m_decode['value']}")
                if m_decode['serial'] == w.SERIAL:
                    if (m_decode['name']=="STATUS" and m_decode['value']=="READY"):
                        # Sleep for 1 second and set the event.
                        w.event.set()
                        w.MACHINE_STATUS = 'READY'
                    elif (m_decode['name']=="Operation" and m_decode['value']=="WATERFULLLEVEL"):
                        if w.MACHINE_STATUS == "FILLWATER":
                            w.Operation = 'WATERFULLLEVEL'
                            if w.Task:
                                w.Task.cancel()
                        else :
                            print(f"{time.ctime()} - [{w.SERIAL}-{w.MACHINE_STATUS}] - Enter error")
                    elif (m_decode['name']=="Operation" and m_decode['value']=="TEMPERATUREREACHED"):
                        if w.MACHINE_STATUS == "HEATWATER":
                            w.Operation = 'TEMPERATUREREACHED'
                            if w.Task:
                                w.Task.cancel()
                        else :
                            print(f"{time.ctime()} - [{w.SERIAL}-{w.MACHINE_STATUS}] - Enter error")
                    elif (m_decode['name']=="Operation" and m_decode['value']=="OUTOFBALANCE"):
                        if w.MACHINE_STATUS == "WASH":
                            w.Operation = 'OUTOFBALANCE'
                            if w.Task:
                                w.Task.cancel()
                        else :
                            print(f"{time.ctime()} - [{w.SERIAL}-{w.MACHINE_STATUS}] - Enter error")
                    elif (m_decode['name']=="Operation" and m_decode['value']=="MOTORFAILURE"):
                        if w.MACHINE_STATUS == "RINSE" or w.MACHINE_STATUS == "SPIN":
                            w.Operation = 'MOTORFAILURE'
                            if w.Task:
                                w.Task.cancel()
                        else :
                            print(f"{time.ctime()} - [{w.SERIAL}-{w.MACHINE_STATUS}] - Enter error")
                    if (m_decode['name']=="Operation" and m_decode['value']=="FAULT_CLEAR"):
                        w.event.set()
                        w.MACHINE_STATUS = 'OFF'
                else:
                    print(f"{time.ctime()} - [{w.SERIAL}-{w.MACHINE_STATUS}] - Serial error")

async def main():
    n = 2
    W = [WashingMachine(serial=f'SN-00{i+1}') for i in range(n)]
    async with aiomqtt.Client("broker.emqx.io") as client:
        listenTask = []
        CoroWashingMachineTask = []
        for w in W:
            listenTask.append(listen(w, client))
            CoroWashingMachineTask.append(CoroWashingMachine(w, client))
        await asyncio.gather(*listenTask, *CoroWashingMachineTask)
        

# Change to the "Selector" event loop if platform is Windows
if sys.platform.lower() == "win32" or os.name.lower() == "nt":
    from asyncio import set_event_loop_policy, WindowsSelectorEventLoopPolicy
    set_event_loop_policy(WindowsSelectorEventLoopPolicy())

asyncio.run(main())