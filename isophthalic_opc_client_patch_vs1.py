# =======================================================
# PATCH FOR YOUR ISOPHTHALIC TKINTER CLIENT
# Purpose: replace the local DCS feed simulation with real OPC UA values
# from isophthalic_opc_server_vs1.py
# =======================================================

# 1) ADD THESE IMPORTS AT THE TOP OF YOUR CLIENT FILE
import asyncio
import threading
import queue
from asyncua import Client


# 2) ADD THIS OPC CONFIGURATION AFTER IMG_PATH / BEFORE TKINTER UI
OPC_SERVER_URL = "opc.tcp://127.0.0.1:4842/isophthalic/server/"
OPC_SCAN_SEC = 2.0

opc_queue = queue.Queue()
opc_connected = False
opc_last_values = {}

# Browse paths below must match the OPC server objects and variable names.
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
    """Find a direct child node using its BrowseName name part."""
    children = await parent.get_children()
    for child in children:
        bn = await child.read_browse_name()
        if bn.Name == browse_name:
            return child
    raise RuntimeError(f"Cannot find OPC child: {browse_name}")


async def get_node_by_path(client, path):
    """Navigate from Objects using simple BrowseName path."""
    node = client.nodes.objects
    for item in path:
        node = await find_child_by_browse_name(node, item)
    return node


async def opc_reader_loop():
    """Background asyncio loop. Reads OPC values and puts them in a thread-safe queue."""
    global opc_connected

    while True:
        try:
            print("Trying OPC UA connection:", OPC_SERVER_URL)
            async with Client(OPC_SERVER_URL) as client:
                print("OPC UA connected")
                opc_connected = True

                nodes = {}
                for key, path in OPC_TAG_NAMES.items():
                    nodes[key] = await get_node_by_path(client, path)

                while True:
                    values = {}
                    for key, node in nodes.items():
                        values[key] = await node.read_value()

                    opc_queue.put(values)
                    await asyncio.sleep(OPC_SCAN_SEC)

        except Exception as exc:
            opc_connected = False
            print("OPC UA connection error:", exc)
            await asyncio.sleep(2.0)


def start_opc_thread():
    """Start OPC reader in a daemon thread, so Tkinter mainloop remains responsive."""
    thread = threading.Thread(
        target=lambda: asyncio.run(opc_reader_loop()),
        daemon=True,
    )
    thread.start()


def poll_opc_queue():
    """Called by Tkinter every 500 ms. Applies last OPC values to sliders."""
    global opc_last_values

    got_new_values = False

    while not opc_queue.empty():
        opc_last_values = opc_queue.get()
        got_new_values = True

    if got_new_values:
        # Avoid multiple update_model calls from slider command callbacks.
        mx_slider.config(command="")
        pressure_slider.config(command="")
        hp_steam_slider.config(command="")
        lp_steam_slider.config(command="")

        mx_slider.set(float(opc_last_values["mx_feed"]))
        pressure_slider.set(float(opc_last_values["reactor_pressure_barg"]))
        hp_steam_slider.set(float(opc_last_values["hp_steam"]))
        lp_steam_slider.set(float(opc_last_values["lp_steam"]))

        mx_slider.config(command=update_model)
        pressure_slider.config(command=update_model)
        hp_steam_slider.config(command=update_model)
        lp_steam_slider.config(command=update_model)

        update_model()

    root.after(500, poll_opc_queue)


# 3) REMOVE OR COMMENT OUT YOUR OLD SIMULATED DCS FEED SECTION:
#    - dcs_simulation_running
#    - simulate_dcs_feed()
#    - start_dcs_simulation()
#    - stop_dcs_simulation()
#    - Start/Stop DCS buttons


# 4) IN update_model(), REPLACE THIS RESULT TEXT LINE:
#    f"DCS simulation: {'ON' if dcs_simulation_running else 'OFF'}\n\n"
# WITH THIS:
#    f"OPC connection: {'ON' if opc_connected else 'OFF'}\n\n"


# 5) OPTIONAL: IN update_model(), AFTER thickness_index IS CALCULATED,
#    ADD THIS BLOCK TO COMPARE MODEL VS DCS VALUES:
#
#    reactor_temp_dcs = opc_last_values.get("reactor_temp_dcs")
#    thickness_index_dcs = opc_last_values.get("thickness_index_dcs")
#
#    if reactor_temp_dcs is not None:
#        reactor_temp_delta = reactor_temp_dcs - reactor_temp
#    else:
#        reactor_temp_delta = None
#
#    if thickness_index_dcs is not None:
#        thickness_delta = thickness_index_dcs - thickness_index
#    else:
#        thickness_delta = None
#
# Then add these lines inside result_text.set(...):
#
#        f"Reactor temp MODEL: {reactor_temp:.2f} °C\n"
#        f"Reactor temp DCS:   {reactor_temp_dcs:.2f} °C\n" if reactor_temp_dcs is not None else "Reactor temp DCS: ---\n"
#        f"Delta T:            {reactor_temp_delta:+.2f} °C\n\n" if reactor_temp_delta is not None else "Delta T: ---\n\n"
#        f"Thickness MODEL: {thickness_index:.3f}\n"
#        f"Thickness DCS:   {thickness_index_dcs:.3f}\n" if thickness_index_dcs is not None else "Thickness DCS: ---\n"
#        f"Thickness delta: {thickness_delta:+.3f}\n" if thickness_delta is not None else "Thickness delta: ---\n"


# 6) AT THE END OF YOUR CLIENT, REPLACE:
#    initializing = False
#    update_model()
#    root.mainloop()
#
# WITH:
#    initializing = False
#    start_opc_thread()
#    poll_opc_queue()
#    update_model()
#    root.mainloop()
