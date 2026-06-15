import asyncio
import random
import math
from asyncua import Server


# =========================================================
# FORMALIN OPC UA SERVER
# Simulated DCS / plant tags for Glass Plant development
# =========================================================

ENDPOINT = "opc.tcp://127.0.0.1:4841/formalin/server/"
NAMESPACE_URI = "http://glassplant.local/formalin"


def clamp(value, minimum, maximum):
    return max(minimum, min(value, maximum))


async def main():
    server = Server()
    await server.init()

    server.set_endpoint(ENDPOINT)

    idx = await server.register_namespace(NAMESPACE_URI)

    # =====================================================
    # MAIN PLANT OBJECT
    # =====================================================
    plant = await server.nodes.objects.add_object(idx, "FormalinPlant")

    # =====================================================
    # PLANT SECTIONS
    # =====================================================
    feed = await plant.add_object(idx, "Feed")
    vaporizer = await plant.add_object(idx, "Vaporizer")
    reactor = await plant.add_object(idx, "Reactor")
    absorber = await plant.add_object(idx, "Absorber")
    offgas = await plant.add_object(idx, "Offgas")
    utilities = await plant.add_object(idx, "Utilities")

    # =====================================================
    # FEED TAGS
    # =====================================================
    air_flow = await feed.add_variable(idx, "Air_Flow_kg_h", 2728.0)
    methanol_feed = await feed.add_variable(idx, "Methanol_Feed_kg_h", 1818.0)
    water_feed = await feed.add_variable(idx, "Water_Feed_kg_h", 866.0)
    methanol_water_ratio = await feed.add_variable(idx, "Methanol_Water_Ratio", 2.10)

    # =====================================================
    # VAPORIZER TAGS
    # =====================================================
    vaporizer_temp = await vaporizer.add_variable(idx, "Vaporizer_Temperature_C", 70.7)
    vaporizer_pressure = await vaporizer.add_variable(idx, "Vaporizer_Pressure_barg", 0.20)
    vaporizer_level = await vaporizer.add_variable(idx, "Vaporizer_Level_pct", 50.0)

    # =====================================================
    # REACTOR TAGS
    # =====================================================
    reactor_inlet_temp = await reactor.add_variable(idx, "Reactor_Inlet_Temperature_C", 70.7)
    reactor_temp = await reactor.add_variable(idx, "Reactor_Temperature_C", 620.0)
    reactor_pressure = await reactor.add_variable(idx, "Reactor_Pressure_barg", 0.25)
    steam_production = await reactor.add_variable(idx, "Steam_Production_kg_h", 1500.0)

    # =====================================================
    # ABSORBER TAGS
    # =====================================================
    absorber_top_temp = await absorber.add_variable(idx, "Absorber_Top_Temperature_C", 40.0)
    absorber_stage5_temp = await absorber.add_variable(idx, "Absorber_Stage5_Temperature_C", 60.0)
    absorber_bottom_temp = await absorber.add_variable(idx, "Absorber_Bottom_Temperature_C", 72.0)

    formalin_flow = await absorber.add_variable(idx, "Formalin_Flow_kg_h", 10000.0)
    hcho_wt_pct = await absorber.add_variable(idx, "HCHO_wt_pct", 37.0)
    methanol_wt_pct = await absorber.add_variable(idx, "Methanol_in_Formalin_wt_pct", 1.0)

    # =====================================================
    # OFFGAS TAGS
    # =====================================================
    offgas_flow = await offgas.add_variable(idx, "Offgas_Flow_kg_h", 2200.0)
    offgas_meoh = await offgas.add_variable(idx, "Offgas_Methanol_kg_h", 0.08)
    offgas_water = await offgas.add_variable(idx, "Offgas_Water_kg_h", 8.0)
    offgas_o2 = await offgas.add_variable(idx, "Offgas_O2_vol_pct", 8.0)

    # =====================================================
    # UTILITIES TAGS
    # =====================================================
    cooling_water_flow = await utilities.add_variable(idx, "Cooling_Water_Flow_m3_h", 180.0)
    cooling_water_outlet_temp = await utilities.add_variable(idx, "Cooling_Water_Outlet_Temperature_C", 35.0)

    # =====================================================
    # MAKE TAGS WRITABLE
    # Useful if later you want to modify them from an OPC browser
    # =====================================================
    all_tags = [
        air_flow,
        methanol_feed,
        water_feed,
        methanol_water_ratio,
        vaporizer_temp,
        vaporizer_pressure,
        vaporizer_level,
        reactor_inlet_temp,
        reactor_temp,
        reactor_pressure,
        steam_production,
        absorber_top_temp,
        absorber_stage5_temp,
        absorber_bottom_temp,
        formalin_flow,
        hcho_wt_pct,
        methanol_wt_pct,
        offgas_flow,
        offgas_meoh,
        offgas_water,
        offgas_o2,
        cooling_water_flow,
        cooling_water_outlet_temp,
    ]

    for tag in all_tags:
        await tag.set_writable()

    print("FORMALIN OPC UA SERVER running")
    print(f"Address: {ENDPOINT}")
    print("Press Ctrl+C to stop")

    # =====================================================
    # SIMULATION LOOP
    # =====================================================
    async with server:
        t = 0.0

        while True:
            cycle = math.sin(t / 30.0)

            # Feed section
            air_value = clamp(2728.0 + 120.0 * cycle + random.uniform(-20, 20), 2200, 3300)
            meoh_value = air_value / 1.5
            water_value = meoh_value / 2.1

            # Vaporizer
            vap_temp_value = clamp(70.7 + 2.0 * cycle + random.uniform(-0.3, 0.3), 65.0, 80.0)
            vap_pressure_value = clamp(0.20 + random.uniform(-0.02, 0.02), 0.10, 0.40)
            vap_level_value = clamp(50.0 + 5.0 * cycle + random.uniform(-1, 1), 35.0, 70.0)

            # Reactor simplified behaviour
            reactor_temp_value = clamp(
                620.0 + 4.0 * (vap_temp_value - 70.7) + random.uniform(-5, 5),
                560.0,
                680.0,
            )

            steam_value = clamp(
                1500.0 + 3.0 * (reactor_temp_value - 620.0) + random.uniform(-30, 30),
                1000.0,
                2100.0,
            )

            # Absorber
            stage5_value = clamp(60.0 + 0.5 * cycle + random.uniform(-0.5, 0.5), 50.0, 70.0)
            hcho_value = clamp(37.0 + random.uniform(-0.2, 0.2), 35.0, 39.0)
            meoh_formalin_value = clamp(
                1.0 + 0.05 * (70.7 - vap_temp_value) + random.uniform(-0.05, 0.05),
                0.3,
                2.0,
            )

            # Offgas
            offgas_meoh_value = clamp(
                0.08 + 0.03 * max(0.0, stage5_value - 60.0) + random.uniform(-0.01, 0.01),
                0.01,
                0.50,
            )

            offgas_water_value = clamp(
                8.0 + 0.4 * max(0.0, stage5_value - 60.0) + random.uniform(-0.5, 0.5),
                3.0,
                20.0,
            )

            offgas_o2_value = clamp(8.0 + random.uniform(-0.3, 0.3), 6.0, 10.5)

            # Write values to OPC tags
            await air_flow.write_value(air_value)
            await methanol_feed.write_value(meoh_value)
            await water_feed.write_value(water_value)
            await methanol_water_ratio.write_value(2.1)

            await vaporizer_temp.write_value(vap_temp_value)
            await vaporizer_pressure.write_value(vap_pressure_value)
            await vaporizer_level.write_value(vap_level_value)

            await reactor_inlet_temp.write_value(vap_temp_value)
            await reactor_temp.write_value(reactor_temp_value)
            await reactor_pressure.write_value(clamp(0.25 + random.uniform(-0.02, 0.02), 0.10, 0.50))
            await steam_production.write_value(steam_value)

            await absorber_top_temp.write_value(clamp(40.0 + random.uniform(-0.8, 0.8), 34.0, 48.0))
            await absorber_stage5_temp.write_value(stage5_value)
            await absorber_bottom_temp.write_value(clamp(72.0 + random.uniform(-1.0, 1.0), 65.0, 82.0))

            await formalin_flow.write_value(clamp(10000.0 + random.uniform(-100, 100), 9000, 11000))
            await hcho_wt_pct.write_value(hcho_value)
            await methanol_wt_pct.write_value(meoh_formalin_value)

            await offgas_flow.write_value(clamp(2200.0 + random.uniform(-80, 80), 1900, 2600))
            await offgas_meoh.write_value(offgas_meoh_value)
            await offgas_water.write_value(offgas_water_value)
            await offgas_o2.write_value(offgas_o2_value)

            await cooling_water_flow.write_value(clamp(180.0 + random.uniform(-5, 5), 150, 220))
            await cooling_water_outlet_temp.write_value(clamp(35.0 + random.uniform(-1, 1), 30, 42))

            t += 2.0
            await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(main())
    