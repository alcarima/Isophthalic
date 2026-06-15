import asyncio
from asyncua import Client


OPC_SERVER_URL = "opc.tcp://localhost:53530/OPCUA/SimulationServer"


async def main():
    async with Client(url=OPC_SERVER_URL) as client:
        print("Connected to OPC UA server")

        # Example only: you must replace this with the real NodeId from your server
        node = client.get_node("ns=3;s=Air.Flow")

        value = await node.read_value()
        print("Air flow:", value)


if __name__ == "__main__":
    asyncio.run(main())