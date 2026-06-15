import asyncio
import random
from asyncua import Server


OPC_SERVER_URL = "opc.tcp://127.0.0.1:4842/isophthalic/server/"


async def main():
    server = Server()
    await server.init()

    server.set_endpoint(OPC_SERVER_URL)

    uri = "http://glassplant.local/isophthalic"
    idx = await server.register_namespace(uri)

    plant = await server.nodes.objects.add_object(idx, "IsophthalicPlant")

    # Main feed values
    mx_feed = await plant.add_variable(idx, "MX_Feed_kg_h", 5391.64)
    acetic_acid_feed = await plant.add_variable(idx, "Acetic_Acid_kg_h", 36213.14)
    water_feed = await plant.add_variable(idx, "Water_kg_h", 2725.72)
    oxygen_feed = await plant.add_variable(idx, "Oxygen_kg_h", 6217.82)
    nitrogen_feed = await plant.add_variable(idx, "Nitrogen_kg_h", 20816.18)

    # Reactor / process values
    reactor_temp = await plant.add_variable(idx, "Reactor_Temperature_C", 190.0)
    reactor_pressure = await plant.add_variable(idx, "Reactor_Pressure_barg", 15.0)
    conversion_mx = await plant.add_variable(idx, "MX_Conversion_frac", 0.965)
    pia_production = await plant.add_variable(idx, "PIA_Production_kg_h", 0.0)
    oxidation_status = await plant.add_variable(idx, "Oxidation_Status", "NORMAL")

    variables = [
        mx_feed,
        acetic_acid_feed,
        water_feed,
        oxygen_feed,
        nitrogen_feed,
        reactor_temp,
        reactor_pressure,
        conversion_mx,
        pia_production,
    ]

    for var in variables:
        await var.set_writable()

    print("Isophthalic OPC UA SERVER running")
    print(f"Address: {OPC_SERVER_URL}")
    print("Press Ctrl+C to stop")

    async with server:
        while True:
            # Simulated live values
            mx_value = 5391.64 + random.uniform(-50, 50)
            acetic_value = 36213.14 + random.uniform(-200, 200)
            water_value = 2725.72 + random.uniform(-50, 50)
            oxygen_value = 6217.82 + random.uniform(-100, 100)
            nitrogen_value = 20816.18 + random.uniform(-200, 200)

            temp_value = 190.0 + random.uniform(-2.0, 2.0)
            pressure_value = 15.0 + random.uniform(-0.3, 0.3)
            conversion_value = 0.965 + random.uniform(-0.005, 0.005)

            # Simplified PIA production estimate
            pia_value = mx_value * conversion_value * 1.35

            if temp_value > 195:
                status = "HIGH TEMPERATURE"
            elif conversion_value < 0.955:
                status = "LOW CONVERSION"
            else:
                status = "NORMAL"

            await mx_feed.write_value(round(mx_value, 2))
            await acetic_acid_feed.write_value(round(acetic_value, 2))
            await water_feed.write_value(round(water_value, 2))
            await oxygen_feed.write_value(round(oxygen_value, 2))
            await nitrogen_feed.write_value(round(nitrogen_value, 2))
            await reactor_temp.write_value(round(temp_value, 2))
            await reactor_pressure.write_value(round(pressure_value, 2))
            await conversion_mx.write_value(round(conversion_value, 4))
            await pia_production.write_value(round(pia_value, 2))
            await oxidation_status.write_value(status)

            await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(main())