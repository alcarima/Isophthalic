import asyncio
from asyncua import Client

OPC_SERVER_URL = "opc.tcp://127.0.0.1:4842/isophthalic/server/"
OPC_TAG_NAMES = {
    "mx_feed": ["IsophthalicPlant", "Feed", "MX_Feed_kg_h"],
    "reactor_pressure_barg": ["IsophthalicPlant", "Reactor", "Reactor_Pressure_barg"],
    "hp_steam": ["IsophthalicPlant", "Utilities", "HP_Steam_Pressure_barg"],
    "lp_steam": ["IsophthalicPlant", "Utilities", "LP_Steam_Pressure_barg"],
    "reactor_temp_dcs": ["IsophthalicPlant", "Reactor", "Reactor_Temperature_C"],
    "thickness_index_dcs": ["IsophthalicPlant", "Product", "Thickness_Index"],
    "air_to_reactor_dcs": ["IsophthalicPlant", "Compressor", "Air_to_Reactor_kg_h"],
    "to_scrubber_hac_dcs": ["IsophthalicPlant", "Scrubber", "To_Scrubber_HAc_kg_h"],
    "to_scrubber_water_dcs": ["IsophthalicPlant", "Scrubber", "To_Scrubber_Water_kg_h"],
}

async def find_child_by_browse_name(parent, browse_name):
    children = await parent.get_children()
    for child in children:
        bn = await child.read_browse_name()
        if bn.Name == browse_name:
            return child
    raise RuntimeError(f"Cannot find OPC child: {browse_name}")

async def get_node_by_path(client, path):
    node = client.nodes.objects
    for item in path:
        node = await find_child_by_browse_name(node, item)
    return node

async def main():
    print("Connecting to:", OPC_SERVER_URL)
    async with Client(OPC_SERVER_URL) as client:
        print("Connected. Reading tags every 2 seconds. Press Ctrl+C to stop.\n")
        nodes = {key: await get_node_by_path(client, path) for key, path in OPC_TAG_NAMES.items()}
        while True:
            values = {key: await node.read_value() for key, node in nodes.items()}
            print("-" * 60)
            for key, value in values.items():
                if isinstance(value, float):
                    print(f"{key:25s}: {value:,.3f}")
                else:
                    print(f"{key:25s}: {value}")
            await asyncio.sleep(2.0)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped by user.")
