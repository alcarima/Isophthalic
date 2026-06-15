import asyncio
import random
import math
from asyncua import Server


# =========================================================
# ISOPHTHALIC ACID OPC UA SERVER
# Simulated DCS / plant tags for Glass Plant development
# Pattern based on formalin_opc_server_vs1.py
# =========================================================

ENDPOINT = "opc.tcp://127.0.0.1:4842/isophthalic/server/"
NAMESPACE_URI = "http://glassplant.local/isophthalic"


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
    plant = await server.nodes.objects.add_object(idx, "IsophthalicPlant")

    # =====================================================
    # PLANT SECTIONS
    # =====================================================
    feed = await plant.add_object(idx, "Feed")
    compressor = await plant.add_object(idx, "Compressor")
    reactor = await plant.add_object(idx, "Reactor")
    condenser_1 = await plant.add_object(idx, "Condenser1")
    condenser_2 = await plant.add_object(idx, "Condenser2")
    product = await plant.add_object(idx, "Product")
    scrubber = await plant.add_object(idx, "Scrubber")
    utilities = await plant.add_object(idx, "Utilities")

    # =====================================================
    # FEED TAGS - DCS VALUES
    # =====================================================
    mx_feed = await feed.add_variable(idx, "MX_Feed_kg_h", 5300.0)
    hac_mx_ratio = await feed.add_variable(idx, "HAc_MX_Ratio", 6.70)
    water_in_feed = await feed.add_variable(idx, "Water_in_Feed_frac", 0.07)
    hac_feed = await feed.add_variable(idx, "HAc_Feed_kg_h", 35510.0)
    water_feed = await feed.add_variable(idx, "Water_Feed_kg_h", 2856.7)
    total_feed = await feed.add_variable(idx, "Total_Feed_kg_h", 43666.7)

    # =====================================================
    # COMPRESSOR TAGS - DCS VALUES
    # =====================================================
    air_to_reactor = await compressor.add_variable(idx, "Air_to_Reactor_kg_h", 0.0)
    air_temp_comp = await compressor.add_variable(idx, "Air_Temperature_After_Compressor_C", 111.0)
    comp_pressure_barg = await compressor.add_variable(idx, "Compressor_Discharge_Pressure_barg", 15.0)
    comp_pressure_bara = await compressor.add_variable(idx, "Compressor_Discharge_Pressure_bara", 16.0)

    # =====================================================
    # REACTOR TAGS - DCS VALUES
    # =====================================================
    reactor_pressure = await reactor.add_variable(idx, "Reactor_Pressure_barg", 15.0)
    reactor_temp = await reactor.add_variable(idx, "Reactor_Temperature_C", 206.0)
    reactor_level = await reactor.add_variable(idx, "Reactor_Level_pct", 55.0)
    offgas_o2 = await reactor.add_variable(idx, "Reactor_Offgas_O2_vol_pct", 3.0)
    offgas_co2 = await reactor.add_variable(idx, "Reactor_Offgas_CO2_vol_pct", 6.0)

    # =====================================================
    # CONDENSERS TAGS - DCS VALUES
    # =====================================================
    cond1_exit_temp = await condenser_1.add_variable(idx, "Condenser1_Exit_Temperature_C", 0.0)
    cond1_pressure = await condenser_1.add_variable(idx, "Condenser1_Pressure_barg", 15.0)
    cond1_cond_hac = await condenser_1.add_variable(idx, "Condenser1_Condensed_HAc_kg_h", 0.0)
    cond1_cond_water = await condenser_1.add_variable(idx, "Condenser1_Condensed_Water_kg_h", 0.0)

    cond2_exit_temp = await condenser_2.add_variable(idx, "Condenser2_Exit_Temperature_C", 0.0)
    cond2_pressure = await condenser_2.add_variable(idx, "Condenser2_Pressure_barg", 15.0)
    cond2_cond_hac = await condenser_2.add_variable(idx, "Condenser2_Condensed_HAc_kg_h", 0.0)
    cond2_cond_water = await condenser_2.add_variable(idx, "Condenser2_Condensed_Water_kg_h", 0.0)

    # =====================================================
    # PRODUCT / SCRUBBER TAGS - DCS VALUES
    # =====================================================
    product_water = await product.add_variable(idx, "Crystallizer_Feed_Water_kg_h", 0.0)
    product_hac = await product.add_variable(idx, "Crystallizer_Feed_HAc_kg_h", 0.0)
    product_ia = await product.add_variable(idx, "Crystallizer_Feed_IA_kg_h", 0.0)
    thickness_index = await product.add_variable(idx, "Thickness_Index", 0.330)

    scrubber_hac = await scrubber.add_variable(idx, "To_Scrubber_HAc_kg_h", 0.0)
    scrubber_water = await scrubber.add_variable(idx, "To_Scrubber_Water_kg_h", 0.0)

    # =====================================================
    # UTILITIES TAGS - DCS VALUES
    # =====================================================
    hp_steam = await utilities.add_variable(idx, "HP_Steam_Pressure_barg", 6.5)
    lp_steam = await utilities.add_variable(idx, "LP_Steam_Pressure_barg", 2.5)
    cooling_water_flow = await utilities.add_variable(idx, "Cooling_Water_Flow_m3_h", 250.0)

    all_tags = [
        mx_feed, hac_mx_ratio, water_in_feed, hac_feed, water_feed, total_feed,
        air_to_reactor, air_temp_comp, comp_pressure_barg, comp_pressure_bara,
        reactor_pressure, reactor_temp, reactor_level, offgas_o2, offgas_co2,
        cond1_exit_temp, cond1_pressure, cond1_cond_hac, cond1_cond_water,
        cond2_exit_temp, cond2_pressure, cond2_cond_hac, cond2_cond_water,
        product_water, product_hac, product_ia, thickness_index,
        scrubber_hac, scrubber_water,
        hp_steam, lp_steam, cooling_water_flow,
    ]

    for tag in all_tags:
        await tag.set_writable()

    print("ISOPHTHALIC OPC UA SERVER running")
    print(f"Address: {ENDPOINT}")
    print("Root object: IsophthalicPlant")
    print("Sections: Feed, Compressor, Reactor, Condenser1, Condenser2, Product, Scrubber, Utilities")
    print("Press Ctrl+C to stop")

    # =====================================================
    # SIMULATION LOOP
    # =====================================================
    async with server:
        t = 0.0

        while True:
            cycle = math.sin(t / 30.0)
            slow_cycle = math.sin(t / 90.0)

            # Feed section: keep variations realistic and slow
            mx_value = clamp(
                5300.0 + 250.0 * cycle + random.uniform(-35.0, 35.0),
                4500.0,
                6200.0,
            )
            hac_mx_ratio_value = clamp(
                6.70 + 0.05 * slow_cycle + random.uniform(-0.01, 0.01),
                6.50,
                6.90,
            )
            water_frac_value = clamp(
                0.070 + 0.003 * slow_cycle + random.uniform(-0.001, 0.001),
                0.055,
                0.085,
            )
            hac_value = mx_value * hac_mx_ratio_value
            water_value = (hac_value + mx_value) * water_frac_value
            total_feed_value = mx_value + hac_value + water_value

            # Utilities / pressure
            hp_steam_value = clamp(
                6.5 + 0.15 * cycle + random.uniform(-0.03, 0.03),
                5.8,
                7.2,
            )
            lp_steam_value = clamp(
                2.5 + 0.10 * slow_cycle + random.uniform(-0.02, 0.02),
                2.0,
                3.1,
            )
            reactor_pressure_value = clamp(
                15.0 + 0.25 * slow_cycle + random.uniform(-0.05, 0.05),
                13.5,
                16.5,
            )
            reactor_pressure_bara_value = reactor_pressure_value + 1.0

            # Approximate calculated / measured values for demo
            air_value = clamp(
                11500.0 + 1.15 * (mx_value - 5300.0) + random.uniform(-120, 120),
                9500.0,
                14000.0,
            )
            air_temp_value = clamp(
                111.0 + random.uniform(-0.4, 0.4),
                108.0,
                112.0,
            )

            cond1_temp_value = math.sqrt(math.sqrt(hp_steam_value + 1.0)) * 100.0 + 10.0
            cond2_temp_value = math.sqrt(math.sqrt(lp_steam_value + 1.0)) * 100.0 + 10.0

            # Reactor temperature is intentionally close to the model expected value
            reactor_temp_value = clamp(
                206.0 + 0.015 * (mx_value - 5300.0) / 50.0 - 0.20 * (hp_steam_value - 6.5) + random.uniform(-0.20, 0.20),
                202.0,
                211.0,
            )

            # Demonstration values correlated with feed and condenser temperatures
            cond1_hac_value = clamp(1300.0 + 0.18 * (mx_value - 5300.0) + random.uniform(-40, 40), 700, 1900)
            cond1_water_value = clamp(1600.0 + 0.12 * (mx_value - 5300.0) + random.uniform(-50, 50), 900, 2300)
            cond2_hac_value = clamp(450.0 + 0.07 * (mx_value - 5300.0) + random.uniform(-25, 25), 150, 850)
            cond2_water_value = clamp(700.0 + 0.08 * (mx_value - 5300.0) + random.uniform(-30, 30), 350, 1100)

            scrubber_hac_value = clamp(90.0 + 0.03 * (mx_value - 5300.0) + random.uniform(-8, 8), 20, 180)
            scrubber_water_value = clamp(160.0 + 0.04 * (mx_value - 5300.0) + random.uniform(-15, 15), 60, 300)

            product_ia_value = mx_value / 106.0 * 166.0
            product_hac_value = clamp(hac_value - cond1_hac_value - cond2_hac_value - scrubber_hac_value, 10000, 45000)
            product_water_value = clamp(water_value + mx_value / 106.0 * 2.0 * 18.0 - cond1_water_value - cond2_water_value - scrubber_water_value, 1000, 10000)

            dilution = product_water_value + 0.7 * product_hac_value
            thickness_value = product_ia_value / max(dilution, 1e-9)

            offgas_o2_value = clamp(3.2 - 0.2 * cycle + random.uniform(-0.10, 0.10), 2.0, 5.5)
            offgas_co2_value = clamp(6.0 + 0.2 * cycle + random.uniform(-0.10, 0.10), 4.5, 8.0)
            level_value = clamp(55.0 + 4.0 * slow_cycle + random.uniform(-1.0, 1.0), 40.0, 70.0)
            cw_flow_value = clamp(250.0 + 10.0 * cycle + random.uniform(-3.0, 3.0), 200.0, 300.0)

            # Feed
            await mx_feed.write_value(mx_value)
            await hac_mx_ratio.write_value(hac_mx_ratio_value)
            await water_in_feed.write_value(water_frac_value)
            await hac_feed.write_value(hac_value)
            await water_feed.write_value(water_value)
            await total_feed.write_value(total_feed_value)

            # Compressor
            await air_to_reactor.write_value(air_value)
            await air_temp_comp.write_value(air_temp_value)
            await comp_pressure_barg.write_value(reactor_pressure_value)
            await comp_pressure_bara.write_value(reactor_pressure_bara_value)

            # Reactor
            await reactor_pressure.write_value(reactor_pressure_value)
            await reactor_temp.write_value(reactor_temp_value)
            await reactor_level.write_value(level_value)
            await offgas_o2.write_value(offgas_o2_value)
            await offgas_co2.write_value(offgas_co2_value)

            # Condensers
            await cond1_exit_temp.write_value(cond1_temp_value)
            await cond1_pressure.write_value(reactor_pressure_value)
            await cond1_cond_hac.write_value(cond1_hac_value)
            await cond1_cond_water.write_value(cond1_water_value)

            await cond2_exit_temp.write_value(cond2_temp_value)
            await cond2_pressure.write_value(reactor_pressure_value)
            await cond2_cond_hac.write_value(cond2_hac_value)
            await cond2_cond_water.write_value(cond2_water_value)

            # Product / scrubber
            await product_water.write_value(product_water_value)
            await product_hac.write_value(product_hac_value)
            await product_ia.write_value(product_ia_value)
            await thickness_index.write_value(thickness_value)
            await scrubber_hac.write_value(scrubber_hac_value)
            await scrubber_water.write_value(scrubber_water_value)

            # Utilities
            await hp_steam.write_value(hp_steam_value)
            await lp_steam.write_value(lp_steam_value)
            await cooling_water_flow.write_value(cw_flow_value)

            print(
                f"MX={mx_value:7.1f} kg/h | "
                f"P_rx={reactor_pressure_value:4.1f} barg | "
                f"HP={hp_steam_value:3.1f} barg | "
                f"LP={lp_steam_value:3.1f} barg | "
                f"T_rx_DCS={reactor_temp_value:5.2f} C | "
                f"ThickIdx_DCS={thickness_value:5.3f}"
            )

            t += 2.0
            await asyncio.sleep(2.0)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nISOPHTHALIC OPC UA SERVER stopped by user.")
