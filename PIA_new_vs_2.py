import math
from dataclasses import dataclass
import os
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk, ImageDraw, ImageFont

# =========================================================
# AIR FLOW TO PIA REACTOR + AIR TEMPERATURE AFTER COMPRESSOR
# =========================================================
air_flow = 29372  # kg/h
o2_air_flow = air_flow * 0.2286
n2_air_flow = air_flow * 0.7654
co2_air_flow = air_flow * 0.001
water_air_flow = air_flow * 0.005

print("Air component sum =", o2_air_flow + n2_air_flow + co2_air_flow + water_air_flow)

air_pressure_barg = 13
air_pressure_bara = air_pressure_barg + 1.0
t_atm = 30  # °C

air_temp_comp = ((air_pressure_bara / 1.0) ** ((1.4 - 1) / 1.4)) * (t_atm + 273.15) - 273.15
print("air temperature after compressor is :", air_temp_comp)

if air_temp_comp > 111:
    air_temp_comp = 111

print("air temperature after compressor limited is :", air_temp_comp)

# =========================================================
# MAIN RAW MATERIALS
# =========================================================
hac_mx_rat = 6.7
mx_feed = 5300  # kg/h
hac_feed = mx_feed * hac_mx_rat
water_feed = (hac_feed + mx_feed) * 0.07
catalyst_feed = 0.3
total_feed_to_rx = mx_feed + hac_feed + water_feed + catalyst_feed

print("mx feed is:", mx_feed)
print("hac feed is:", hac_feed)
print("water feed is:", water_feed)
print("Total feed is:", total_feed_to_rx)

# =========================================================
# BY-PRODUCTS
# =========================================================
hac_burn = 65  # kg/h
mx_conv = 1.0
mx_sel = 0.695

mx_comb = (0.695 - 106 / 166) * mx_feed / 106 * 44 * 8
hac_comb = 65 / 60 * mx_feed / 1000 * 44 * 2
tot_co2 = mx_comb + hac_comb

print("meta-xylene CO2 =", mx_comb, "acetic acid CO2 =", hac_comb)
print("total CO2 =", tot_co2)


# =========================================================
# MIXING VESSEL
# =========================================================
def mixing_vessel(water_in_feed=0.07, hac_mx_rat=6.7, mx_flow_kg_h=5300):
    total_feed = mx_flow_kg_h * (hac_mx_rat + 1.0 + water_in_feed * (hac_mx_rat + 1.0))
    hac_flow_kg_h = mx_flow_kg_h * hac_mx_rat
    water_flow_kg_h = (hac_flow_kg_h + mx_flow_kg_h) * water_in_feed

    return {
        "total_feed": total_feed,
        "mx_flow_to_rx_kg_h": mx_flow_kg_h,
        "hac_flow_to_rx_kg_h": hac_flow_kg_h,
        "water_flow_to_rx_kg_h": water_flow_kg_h,
    }


# =========================================================
# COMPRESSOR
# =========================================================
def comp_flow(mves, mx_conv=0.695, t_atm=30, react_pressure_barg=15):
    react_pressure_bara = react_pressure_barg + 1.0

    # Main reaction O2
    o2_reac = float(mves["mx_flow_to_rx_kg_h"]) / 106 * 3 * 32

    # Combustion of meta-xylene
    o2_mx_comb = float(
        mves["mx_flow_to_rx_kg_h"] / 106 * ((mx_conv - 106 / 166) / mx_conv)
    ) * 10.5 * 32

    # Acetic acid burn
    o2_hac_comb = float(mves["mx_flow_to_rx_kg_h"] / 0.71 / 1000 * 65 / 60 * 2 * 32)

    tot_o2_react = o2_reac + o2_hac_comb
    tot_o2 = tot_o2_react / (1 - 0.13)  # assuming 13% excess / residual basis
    tot_air = tot_o2 / 0.23

    air_temp_comp = ((react_pressure_bara / 1.0) ** ((1.4 - 1) / 1.4)) * (t_atm + 273.15) - 273.15
    if air_temp_comp > 111:
        air_temp_comp = 111

    return {
        "o2_to_iso_kg_h": o2_reac,
        "o2_to_mx_comb_kg_h": o2_mx_comb,
        "o2_to_hac_comb_kg_h": o2_hac_comb,
        "total_o2_rx_kg_h": tot_o2,
        "tot_air_to_react": tot_air,
        "air_temp_comp": air_temp_comp,
        "comp_pressure_barg": react_pressure_barg,
        "comp_pressure_bara": react_pressure_bara,
    }


# =========================================================
# ISOPHTHALIC ACID REACTOR
# =========================================================
def ia_react(mves, comp, ia_reac_temp=206):
    # ---------------- OFF GAS ----------------
    ia_react_n2_offgas_mol = float(comp["tot_air_to_react"] * 0.77 / 28)
    ia_react_o2_offgas_mol = float(
        (comp["total_o2_rx_kg_h"] - comp["o2_to_iso_kg_h"] - comp["o2_to_hac_comb_kg_h"]) / 32
    )
    ia_react_co2_offgas_mol = float(comp["o2_to_hac_comb_kg_h"] / 32)
    ia_react_inc_offgas_mol = (
        ia_react_co2_offgas_mol + ia_react_n2_offgas_mol + ia_react_o2_offgas_mol
    )

    # ---------------- LIQUID IN REACTOR ----------------
    ia_react_liq_wat_mol = float(
        mves["water_flow_to_rx_kg_h"] / 18
        + mves["mx_flow_to_rx_kg_h"] / 106 * 2
        + mves["mx_flow_to_rx_kg_h"] / 0.71 * 65 / 1000 * 2 / 18
    )

    ia_react_liq_hac_mol = float(
        mves["hac_flow_to_rx_kg_h"] / 60
        - mves["mx_flow_to_rx_kg_h"] / 0.71 * 65 / 1000 * 2 / 60
    )

    ia_react_liq_ia_mol = float(mves["mx_flow_to_rx_kg_h"] / 106)
    ia_react_liq_tot_mol = (
        ia_react_liq_wat_mol + ia_react_liq_ia_mol + ia_react_liq_hac_mol
    )

    # ---------------- LIQUID MOLE FRACTION ----------------
    ia_react_liq_x_hac_mol = ia_react_liq_hac_mol / ia_react_liq_tot_mol
    ia_react_liq_x_wat_mol = ia_react_liq_wat_mol / ia_react_liq_tot_mol

    # ---------------- VAPOUR PRESSURES ----------------
    ia_react_watpress = math.exp(18.36 - (3840.96 / (ia_reac_temp + 228.3))) / 760.0
    ia_react_hacpress = math.exp(19.32 - (5495.31 / (ia_reac_temp + 314.75))) / 760.0

    ia_react_y_hac = ia_react_liq_x_hac_mol * ia_react_hacpress / comp["comp_pressure_bara"]
    ia_react_y_wat = ia_react_liq_x_wat_mol * ia_react_watpress / comp["comp_pressure_bara"]

    ia_react_y_incond = 1 - ia_react_y_hac - ia_react_y_wat
    ia_react_vap_tot_mol = ia_react_inc_offgas_mol / ia_react_y_incond

    # ---------------- EVAPORATED FLOWS ----------------
    ia_react_vap_wat_kg_h = ia_react_vap_tot_mol * ia_react_y_wat * 18
    ia_react_vap_hac_kg_h = ia_react_vap_tot_mol * ia_react_y_hac * 60

    # ---------------- HEAT OF REACTION ----------------
    ia_react_heat_react = (
        mves["mx_flow_to_rx_kg_h"] * 2672.89
        + mves["mx_flow_to_rx_kg_h"] / 106 * 166 * 35 * 10 * 1.15
    )

    # ---------------- EVAPORATION HEAT ----------------
    ia_react_heat_evap = (
        ia_react_y_wat
        * ia_react_vap_tot_mol
        * 18
        * (556.6107 - 23.2115 * math.sqrt(comp["comp_pressure_bara"] * (1 - ia_react_y_incond)))
        + ia_react_y_hac * ia_react_vap_tot_mol * 60 * 81
    )

    # ---------------- FEED HEAT ----------------
    ia_in_react_liq_feed_heat = (
        mves["mx_flow_to_rx_kg_h"] * 0.41
        + mves["water_flow_to_rx_kg_h"]
        + mves["hac_flow_to_rx_kg_h"] * 0.5
    ) * (ia_reac_temp - 30)

    ia_in_react_air_feed = comp["tot_air_to_react"] * 0.23 * (ia_reac_temp - comp["air_temp_comp"])

    ia_reac_heat_no_cond = (
        ia_react_heat_react
        - ia_in_react_air_feed
        - ia_in_react_liq_feed_heat
        - ia_react_heat_evap
    )

    return {
        "n2_in_offgas_mol": ia_react_n2_offgas_mol,
        "o2_in_offgas_mol": ia_react_o2_offgas_mol,
        "co2_in_offgas_mol": ia_react_co2_offgas_mol,
        "incondens_offgas_mol": ia_react_inc_offgas_mol,
        "wat_in_reac_liq_mol": ia_react_liq_wat_mol,
        "hac_in_reac_liq_mol": ia_react_liq_hac_mol,
        "ia_in_reac_liq_mol": ia_react_liq_ia_mol,
        "ia_in_react_liq_tot_mol": ia_react_liq_tot_mol,
        "ia_in_react_liq_x_hac": ia_react_liq_x_hac_mol,
        "ia_in_react_liq_x_wat": ia_react_liq_x_wat_mol,
        "ia_in_react_y_hac": ia_react_y_hac,
        "ia_in_react_y_wat": ia_react_y_wat,
        "ia_in_react_vap_tot_mol": ia_react_vap_tot_mol,
        "ia_react_vap_wat_kg_h": ia_react_vap_wat_kg_h,
        "ia_react_vap_hac_kg_h": ia_react_vap_hac_kg_h,
        "ia_in_react_reaction_heat": ia_react_heat_react,
        "ia_in_react_evap_heat": ia_react_heat_evap,
        "ia_in_liq_heat": ia_in_react_liq_feed_heat,
        "ia_in_react_air_feed": ia_in_react_air_feed,
        "ia_reac_temp": ia_reac_temp,
        "ia_reac_heat_no_cond": ia_reac_heat_no_cond,
    }


# =========================================================
# CONDENSER 1
# =========================================================
def condenser_1(react, comp, hp_steam=6.5):
    condenser_1_exit_temp = math.sqrt(math.sqrt(hp_steam + 1)) * 100 + 10

    condenser_1_watpress = math.exp(18.36 - (3840.96 / (condenser_1_exit_temp + 228.3))) / 760.0
    condenser_1_hacpress = math.exp(19.32 - (5495.31 / (condenser_1_exit_temp + 314.75))) / 760.0

    condenser_1_x_wat = 0.5

    for _ in range(20):
        condenser_1_x_hac = 1 - condenser_1_x_wat

        condenser_1_y_hac = condenser_1_hacpress * condenser_1_x_hac / comp["comp_pressure_bara"]
        condenser_1_y_wat = condenser_1_watpress * condenser_1_x_wat / comp["comp_pressure_bara"]
        condenser_1_y_incon = 1 - condenser_1_y_hac - condenser_1_y_wat

        condenser_1_vap_tot_mol = react["incondens_offgas_mol"] / condenser_1_y_incon
        condenser_1_vap_wat_mol = condenser_1_vap_tot_mol * condenser_1_y_wat
        condenser_1_vap_hac_mol = condenser_1_vap_tot_mol * condenser_1_y_hac

        condenser_1_vap_wat_kg_h = condenser_1_vap_wat_mol * 18
        condenser_1_vap_hac_kg_h = condenser_1_vap_hac_mol * 60

        condenser_1_cond_wat_kg_h = react["ia_react_vap_wat_kg_h"] - condenser_1_vap_wat_kg_h
        condenser_1_cond_hac_kg_h = react["ia_react_vap_hac_kg_h"] - condenser_1_vap_hac_kg_h

        denom = condenser_1_cond_wat_kg_h / 18 + condenser_1_cond_hac_kg_h / 60
        if denom > 0:
            condenser_1_x_wat = (condenser_1_cond_wat_kg_h / 18) / denom

        condenser_1_condensate_heat = (
            condenser_1_cond_wat_kg_h * 1 + condenser_1_cond_hac_kg_h * 0.5
        ) * (react["ia_reac_temp"] - condenser_1_exit_temp)

    return {
        "condenser_1_exit_temp": condenser_1_exit_temp,
        "wat_pv_cond_1_exit": condenser_1_watpress,
        "hac_pv_cond_1_exit": condenser_1_hacpress,
        "condenser_1_vap_wat_mol": condenser_1_vap_wat_mol,
        "condenser_1_vap_wat_kg_h": condenser_1_vap_wat_kg_h,
        "condenser_1_vap_hac_mol": condenser_1_vap_hac_mol,
        "condenser_1_vap_hac_kg_h": condenser_1_vap_hac_kg_h,
        "condenser_1_cond_wat_kg_h": condenser_1_cond_wat_kg_h,
        "condenser_1_cond_hac_kg_h": condenser_1_cond_hac_kg_h,
        "condenser_1_condensate_heat": condenser_1_condensate_heat,
    }


# =========================================================
# CONDENSER 2
# =========================================================
def condenser_2(react, cond_1, comp, lp_steam=2.5):
    condenser_2_exit_temp = math.sqrt(math.sqrt(lp_steam + 1)) * 100 + 10

    condenser_2_watpress = math.exp(18.36 - (3840.96 / (condenser_2_exit_temp + 228.3))) / 760.0
    condenser_2_hacpress = math.exp(19.32 - (5495.31 / (condenser_2_exit_temp + 314.75))) / 760.0

    condenser_2_x_wat = 0.5

    for _ in range(20):
        condenser_2_x_hac = 1 - condenser_2_x_wat

        condenser_2_y_hac = condenser_2_hacpress * condenser_2_x_hac / comp["comp_pressure_bara"]
        condenser_2_y_wat = condenser_2_watpress * condenser_2_x_wat / comp["comp_pressure_bara"]
        condenser_2_y_incon = 1 - condenser_2_y_hac - condenser_2_y_wat

        condenser_2_vap_tot_mol = react["incondens_offgas_mol"] / condenser_2_y_incon
        condenser_2_vap_wat_mol = condenser_2_vap_tot_mol * condenser_2_y_wat
        condenser_2_vap_hac_mol = condenser_2_vap_tot_mol * condenser_2_y_hac

        condenser_2_vap_wat_kg_h = condenser_2_vap_wat_mol * 18
        condenser_2_vap_hac_kg_h = condenser_2_vap_hac_mol * 60

        condenser_2_cond_wat_kg_h = cond_1["condenser_1_vap_wat_kg_h"] - condenser_2_vap_wat_kg_h
        condenser_2_cond_hac_kg_h = cond_1["condenser_1_vap_hac_kg_h"] - condenser_2_vap_hac_kg_h

        denom = condenser_2_cond_wat_kg_h / 18 + condenser_2_cond_hac_kg_h / 60
        if denom > 0:
            condenser_2_x_wat = (condenser_2_cond_wat_kg_h / 18) / denom

        condenser_2_condensate_heat = (
            condenser_2_cond_wat_kg_h * 1 + condenser_2_cond_hac_kg_h * 0.5
        ) * (react["ia_reac_temp"] - condenser_2_exit_temp)

    return {
        "condenser_2_exit_temp": condenser_2_exit_temp,
        "wat_pv_cond_2_exit": condenser_2_watpress,
        "hac_pv_cond_2_exit": condenser_2_hacpress,
        "condenser_2_y_hac": condenser_2_y_hac,
        "condenser_2_y_wat": condenser_2_y_wat,
        "condenser_2_vap_tot_mol": condenser_2_vap_tot_mol,
        "condenser_2_vap_wat_mol": condenser_2_vap_wat_mol,
        "condenser_2_vap_wat_kg_h": condenser_2_vap_wat_kg_h,
        "condenser_2_vap_hac_mol": condenser_2_vap_hac_mol,
        "condenser_2_vap_hac_kg_h": condenser_2_vap_hac_kg_h,
        "condenser_2_cond_wat_kg_h": condenser_2_cond_wat_kg_h,
        "condenser_2_cond_hac_kg_h": condenser_2_cond_hac_kg_h,
        "condenser_2_condensate_heat": condenser_2_condensate_heat,
    }


# =========================================================
# MAIN CALCULATION
# =========================================================
mves = mixing_vessel()
print("\n--- MIXING VESSEL ---")
for k, v in mves.items():
    print(f"{k}: {v:.2f}")

comp = comp_flow(mves)
print("\n--- COMPRESSOR ---")
for k, v in comp.items():
    print(f"{k}: {v:.2f}")

# Reactor temperature iteration
reactor_temp = 206.0
step = 0.1
tolerance = 1000  # kcal/h
max_iter = 80

print("\n--- REACTOR ITERATION ---")
for j in range(max_iter):
    react = ia_react(mves, comp, ia_reac_temp=reactor_temp)
    cond_1 = condenser_1(react, comp)
    cond_2 = condenser_2(react, cond_1, comp)

    ia_remaining_heat = (
        react["ia_reac_heat_no_cond"]
        - cond_1["condenser_1_condensate_heat"]
        - cond_2["condenser_2_condensate_heat"]
    )

    print(
        f"iter {j+1:02d} | T = {reactor_temp:.2f} °C | residual heat = {ia_remaining_heat:.2f} kcal/h"
    )

    if abs(ia_remaining_heat) < tolerance:
        print("\nConverged.")
        break

    if ia_remaining_heat > 0:
        reactor_temp += step
    else:
        reactor_temp -= step

print("\n--- FINAL REACTOR ---")
for k, v in react.items():
    print(f"{k}: {v:.2f}")

print("\n--- CONDENSER 1 ---")
for k, v in cond_1.items():
    print(f"{k}: {v:.2f}")

print("\n--- CONDENSER 2 ---")
for k, v in cond_2.items():
    print(f"{k}: {v:.2f}")

print("\nheat generated :", f"{react['ia_in_react_reaction_heat']:.2f}")
print("final reactor T :", f"{reactor_temp:.2f}")
print("heat residual :", f"{ia_remaining_heat:.2f}")

##########################################################################################
###                          GRAPHIC PART                                   ##############
###########################################################################################
# =======================================================
# PATH IMMAGINE
# =======================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_PATH = os.path.join(BASE_DIR, "isophthalic_acid.png")
print("IMG_PATH usato:", IMG_PATH)
print("File esiste?", os.path.exists(IMG_PATH))
# =======================================================
#  UI TKINTER
# =======================================================
root = tk.Tk()
root.title("Glass Plant – Isophthalic Acid (Reactor Assembly)")
root.geometry("1100x700")

main_frame = tk.Frame(root)
main_frame.pack(fill="both", expand=True)

controls = tk.Frame(main_frame, bg="#222", width=340)
controls.pack(side="left", fill="y", padx=10, pady=10)
controls.pack_propagate(False)

img_frame = tk.Frame(main_frame)
img_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

orig_img = Image.open(IMG_PATH)
# to chance picture size
target_w = 1150
scale = target_w / orig_img.width
target_h = int(orig_img.height * 1.* scale)
base_img = orig_img.resize((target_w, target_h), Image.LANCZOS)

photo = ImageTk.PhotoImage(base_img)

img_label = tk.Label(img_frame, image=photo)
img_label.image = photo
img_label.pack(expand=True)

root.mainloop()