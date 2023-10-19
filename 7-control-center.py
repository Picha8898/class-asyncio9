import time
import random
import json
import asyncio
import aiomqtt
import os
import sys
from enum import Enum

student_id = "6310301036"

async def publish_message(SERIAL, client, app, action, name, value):
    print(f"{time.ctime()} - [{SERIAL}] {name} : {value}")
    payload = {
                "action"    : "get",
                "project"   : student_id,
                "model"     : "model-01",
                "serial"    : SERIAL,
                "name"      : name,
                "value"     : value
            }
    print(f"{time.ctime()} - PUBLISH - [{SERIAL}] - {payload['name']} > {payload['value']}")
    await client.publish(f"v1cdti/{app}/{action}/{student_id}/model-01/{SERIAL}"
                        , payload=json.dumps(payload))
    
async def loop_machine(client):
    while True:
        await asyncio.sleep(10)
        payload = {
                "action"    : "get",
                "project"   : student_id,
                "model"     : "model-01",
            }
        print(f"{time.ctime()} - PUBLISH - v1cdti/hw/get/{student_id}/model-01/")
        await client.publish(f"v1cdti/hw/get/{student_id}/model-01/", payload=json.dumps(payload))

async def listen(client):
    async with client.messages() as messages:
        await client.subscribe(f"v1cdti/app/get/{student_id}/model-01/+")
        print(f"{time.ctime()} - SUB topic: v1cdti/app/get/{student_id}/model-01/+")
        async for message in messages:
            m_decode = json.loads(message.payload)
            if message.topic.matches(f"v1cdti/app/get/{student_id}/model-01/+"):
                print(f"{time.ctime()} - MQTT - [{m_decode['project']}] {m_decode['serial']} : {m_decode['name']} => {m_decode['value']}")
                if m_decode['name'] == "STATUS" and m_decode['value'] == "OFF":
                    await asyncio.sleep(2)
                    await publish_message(m_decode['serial'], client, "hw", "set", "STATUS", "READY")
                elif m_decode['name'] == "STATUS" and m_decode['value'] == "FILLWATER":
                    await asyncio.sleep(2)
                    await publish_message(m_decode['serial'], client, "hw", "set", "Operation", "WATERFULLLEVEL")
                elif m_decode['name'] == "STATUS" and m_decode['value'] == "HEATWATER":
                    await asyncio.sleep(2)
                    await publish_message(m_decode['serial'], client, "hw", "set", "Operation", "TEMPERATUREREACHED")
                elif m_decode['name'] == "STATUS" and m_decode['value'] == "SPIN":
                    await asyncio.sleep(2)

async def main():
    async with aiomqtt.Client("broker.emqx.io") as client:
        await asyncio.gather(listen(client), loop_machine(client))
        
# Change to the "Selector" event loop if platform is Windows
if sys.platform.lower() == "win32" or os.name.lower() == "nt":
    from asyncio import set_event_loop_policy, WindowsSelectorEventLoopPolicy
    set_event_loop_policy(WindowsSelectorEventLoopPolicy())

asyncio.run(main())