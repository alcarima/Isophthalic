import asyncio
from asyncua import Client


OPC_SERVER_URL = "opc.tcp://127.0.0.1:4840/freeopcua/server/"


async def main():
    async with Client(url=OPC_SERVER_URL) as client:
        print("Connected to OPC UA server")

        objects = client.nodes.objects

        # Find GlassPlant object
        glassplant = await objects.get_child(["2:GlassPlant"])
        print("GlassPlant node:", glassplant)

        # Get variables inside GlassPlant
        reactor_temp = await glassplant.get_child(["2:Reactor_Temperature_C"])
        feed_flow = await glassplant.get_child(["2:Feed_Flow_kg_h"])
        reactor_pressure = await glassplant.get_child(["2:Reactor_Pressure_barg"])

        while True:
            temp_value = await reactor_temp.read_value()
            flow_value = await feed_flow.read_value()
            pressure_value = await reactor_pressure.read_value()

            print(
                f"Reactor T = {temp_value:.2f} °C | "
                f"Feed Flow = {flow_value:.2f} kg/h | "
                f"Pressure = {pressure_value:.2f} barg"
            )

            await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(main())
    