import asyncio
import random
from asyncua import Server


async def main():
    server = Server()
    await server.init()

    server.set_endpoint("opc.tcp://127.0.0.1:4840/freeopcua/server/")

    uri = "http://glassplant.local"
    idx = await server.register_namespace(uri)

    plant = await server.nodes.objects.add_object(idx, "GlassPlant")

    temp = await plant.add_variable(idx, "Reactor_Temperature_C", 180.0)
    flow = await plant.add_variable(idx, "Feed_Flow_kg_h", 5300.0)
    pressure = await plant.add_variable(idx, "Reactor_Pressure_barg", 8.5)

    await temp.set_writable()
    await flow.set_writable()
    await pressure.set_writable()

    print("OPC UA server running at:")
    print("opc.tcp://127.0.0.1:4840/freeopcua/server/")
    print("Press Ctrl+C to stop")

    async with server:
        while True:
            await temp.write_value(180.0 + random.uniform(-2.0, 2.0))
            await flow.write_value(5300.0 + random.uniform(-100.0, 100.0))
            await pressure.write_value(8.5 + random.uniform(-0.2, 0.2))

            await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(main())
    