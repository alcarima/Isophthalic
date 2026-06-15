import math
import os
import tkinter as tk
from PIL import Image, ImageTk, ImageDraw, ImageFont
import asyncio
import threading
import queue
from asyncua import Client

# =========================================================
# MAIN RAW MATERIALS / GLOBAL DEFAULTS
# =========================================================
hac_mx_rat = 6.7
mx_feed = 5300  # kg/h


# =========================================================
# MIXING VESSEL
# =========================================================
def mixing_vessel(water_in_feed=0.07, hac_mx_rat=6.7, mx_flow_kg_h=5300):
    total_feed = mx_flow_kg_h * (
        hac_mx_rat + 1.0 + water_in_feed * (hac_mx_rat + 1.0)
    )

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

    o2_reac = float(mves["mx_flow_to_rx_kg_h"]) / 106 * 3 * 32

    o2_mx_comb = float(
        mves["mx_flow_to_rx_kg_h"]
        / 106
        * ((mx_conv - 106 / 166) / mx_conv)
    ) * 10.5 * 32

    o2_hac_comb = float(
        mves["mx_flow_to_rx_kg_h"]
        / 0.71
        / 1000
        * 65
        / 60
        * 2
        * 32
    )

    tot_o2_react = o2_reac + o2_hac_comb
    tot_o2 = tot_o2_react / (1 - 0.13)
    tot_air = tot_o2 / 0.23

    air_temp_comp = (
        (react_pressure_bara / 1.0) ** ((1.4 - 1) / 1.4)
    ) * (t_atm + 273.15) - 273.15

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
    ia_react_n2_offgas_mol = float(comp["tot_air_to_react"] * 0.77 / 28)

    ia_react_o2_offgas_mol = float(
        (
            comp["total_o2_rx_kg_h"]
            - comp["o2_to_iso_kg_h"]
            - comp["o2_to_hac_comb_kg_h"]
        )
        / 32
    )

    ia_react_co2_offgas_mol = float(comp["o2_to_hac_comb_kg_h"] / 32)

    ia_react_inc_offgas_mol = (
        ia_react_co2_offgas_mol
        + ia_react_n2_offgas_mol
        + ia_react_o2_offgas_mol
    )

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
        ia_react_liq_wat_mol
        + ia_react_liq_ia_mol
        + ia_react_liq_hac_mol
    )

    ia_react_liq_x_hac_mol = ia_react_liq_hac_mol / ia_react_liq_tot_mol
    ia_react_liq_x_wat_mol = ia_react_liq_wat_mol / ia_react_liq_tot_mol

    ia_react_watpress = math.exp(
        18.36 - (3840.96 / (ia_reac_temp + 228.3))
    ) / 760.0

    ia_react_hacpress = math.exp(
        19.32 - (5495.31 / (ia_reac_temp + 314.75))
    ) / 760.0

    ia_react_y_hac = (
        ia_react_liq_x_hac_mol
        * ia_react_hacpress
        / comp["comp_pressure_bara"]
    )

    ia_react_y_wat = (
        ia_react_liq_x_wat_mol
        * ia_react_watpress
        / comp["comp_pressure_bara"]
    )

    ia_react_y_incond = 1 - ia_react_y_hac - ia_react_y_wat

    if ia_react_y_incond <= 0:
        ia_react_y_incond = 1e-6

    ia_react_vap_tot_mol = ia_react_inc_offgas_mol / ia_react_y_incond

    ia_react_vap_wat_kg_h = ia_react_vap_tot_mol * ia_react_y_wat * 18
    ia_react_vap_hac_kg_h = ia_react_vap_tot_mol * ia_react_y_hac * 60

    ia_react_heat_react = (
        mves["mx_flow_to_rx_kg_h"] * 2672.89
        + mves["mx_flow_to_rx_kg_h"] / 106 * 166 * 35 * 10 * 1.15
    )

    ia_react_heat_evap = (
        ia_react_y_wat
        * ia_react_vap_tot_mol
        * 18
        * (
            556.6107
            - 23.2115
            * math.sqrt(comp["comp_pressure_bara"] * (1 - ia_react_y_incond))
        )
        + ia_react_y_hac * ia_react_vap_tot_mol * 60 * 81
    )

    ia_in_react_liq_feed_heat = (
        mves["mx_flow_to_rx_kg_h"] * 0.41
        + mves["water_flow_to_rx_kg_h"]
        + mves["hac_flow_to_rx_kg_h"] * 0.5
    ) * (ia_reac_temp - 30)

    ia_in_react_air_feed = (
        comp["tot_air_to_react"]
        * 0.23
        * (ia_reac_temp - comp["air_temp_comp"])
    )

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

    condenser_1_watpress = math.exp(
        18.36 - (3840.96 / (condenser_1_exit_temp + 228.3))
    ) / 760.0

    condenser_1_hacpress = math.exp(
        19.32 - (5495.31 / (condenser_1_exit_temp + 314.75))
    ) / 760.0

    condenser_1_x_wat = 0.5

    condenser_1_vap_wat_mol = 0.0
    condenser_1_vap_hac_mol = 0.0
    condenser_1_vap_wat_kg_h = 0.0
    condenser_1_vap_hac_kg_h = 0.0
    condenser_1_cond_wat_kg_h = 0.0
    condenser_1_cond_hac_kg_h = 0.0
    condenser_1_condensate_heat = 0.0

    for _ in range(20):
        condenser_1_x_hac = 1 - condenser_1_x_wat

        condenser_1_y_hac = (
            condenser_1_hacpress
            * condenser_1_x_hac
            / comp["comp_pressure_bara"]
        )

        condenser_1_y_wat = (
            condenser_1_watpress
            * condenser_1_x_wat
            / comp["comp_pressure_bara"]
        )

        condenser_1_y_incon = 1 - condenser_1_y_hac - condenser_1_y_wat

        if condenser_1_y_incon <= 0:
            condenser_1_y_incon = 1e-6

        condenser_1_vap_tot_mol = (
            react["incondens_offgas_mol"] / condenser_1_y_incon
        )

        condenser_1_vap_wat_mol = condenser_1_vap_tot_mol * condenser_1_y_wat
        condenser_1_vap_hac_mol = condenser_1_vap_tot_mol * condenser_1_y_hac

        condenser_1_vap_wat_kg_h = condenser_1_vap_wat_mol * 18
        condenser_1_vap_hac_kg_h = condenser_1_vap_hac_mol * 60

        condenser_1_cond_wat_kg_h = (
            react["ia_react_vap_wat_kg_h"] - condenser_1_vap_wat_kg_h
        )

        condenser_1_cond_hac_kg_h = (
            react["ia_react_vap_hac_kg_h"] - condenser_1_vap_hac_kg_h
        )

        if condenser_1_cond_wat_kg_h < 0:
            condenser_1_cond_wat_kg_h = 0.0

        if condenser_1_cond_hac_kg_h < 0:
            condenser_1_cond_hac_kg_h = 0.0

        denom = condenser_1_cond_wat_kg_h / 18 + condenser_1_cond_hac_kg_h / 60

        if denom > 0:
            condenser_1_x_wat = (condenser_1_cond_wat_kg_h / 18) / denom

        condenser_1_condensate_heat = (
            condenser_1_cond_wat_kg_h * 1
            + condenser_1_cond_hac_kg_h * 0.5
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

    condenser_2_watpress = math.exp(
        18.36 - (3840.96 / (condenser_2_exit_temp + 228.3))
    ) / 760.0

    condenser_2_hacpress = math.exp(
        19.32 - (5495.31 / (condenser_2_exit_temp + 314.75))
    ) / 760.0

    condenser_2_x_wat = 0.5

    condenser_2_y_hac = 0.0
    condenser_2_y_wat = 0.0
    condenser_2_vap_tot_mol = 0.0
    condenser_2_vap_wat_mol = 0.0
    condenser_2_vap_hac_mol = 0.0
    condenser_2_vap_wat_kg_h = 0.0
    condenser_2_vap_hac_kg_h = 0.0
    condenser_2_cond_wat_kg_h = 0.0
    condenser_2_cond_hac_kg_h = 0.0
    condenser_2_condensate_heat = 0.0

    for _ in range(20):
        condenser_2_x_hac = 1 - condenser_2_x_wat

        condenser_2_y_hac = (
            condenser_2_hacpress
            * condenser_2_x_hac
            / comp["comp_pressure_bara"]
        )

        condenser_2_y_wat = (
            condenser_2_watpress
            * condenser_2_x_wat
            / comp["comp_pressure_bara"]
        )

        condenser_2_y_incon = 1 - condenser_2_y_hac - condenser_2_y_wat

        if condenser_2_y_incon <= 0:
            condenser_2_y_incon = 1e-6

        condenser_2_vap_tot_mol = (
            react["incondens_offgas_mol"] / condenser_2_y_incon
        )

        condenser_2_vap_wat_mol = condenser_2_vap_tot_mol * condenser_2_y_wat
        condenser_2_vap_hac_mol = condenser_2_vap_tot_mol * condenser_2_y_hac

        condenser_2_vap_wat_kg_h = condenser_2_vap_wat_mol * 18
        condenser_2_vap_hac_kg_h = condenser_2_vap_hac_mol * 60

        condenser_2_cond_wat_kg_h = (
            cond_1["condenser_1_vap_wat_kg_h"] - condenser_2_vap_wat_kg_h
        )

        condenser_2_cond_hac_kg_h = (
            cond_1["condenser_1_vap_hac_kg_h"] - condenser_2_vap_hac_kg_h
        )

        if condenser_2_cond_wat_kg_h < 0:
            condenser_2_cond_wat_kg_h = 0.0

        if condenser_2_cond_hac_kg_h < 0:
            condenser_2_cond_hac_kg_h = 0.0

        denom = condenser_2_cond_wat_kg_h / 18 + condenser_2_cond_hac_kg_h / 60

        if denom > 0:
            condenser_2_x_wat = (condenser_2_cond_wat_kg_h / 18) / denom

        condenser_2_condensate_heat = (
            condenser_2_cond_wat_kg_h * 1
            + condenser_2_cond_hac_kg_h * 0.5
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
# SOLVER REACTOR TEMPERATURE
# =========================================================
def solve_reactor(
    mves,
    comp,
    hp_steam=6.5,
    lp_steam=2.5,
    start_temp=206.0,
    step=0.1,
    tolerance=1000,
    max_iter=40,
):
    reactor_temp = start_temp

    for _ in range(max_iter):
        react = ia_react(mves, comp, ia_reac_temp=reactor_temp)

        cond_1 = condenser_1(
            react,
            comp,
            hp_steam=hp_steam,
        )

        cond_2 = condenser_2(
            react,
            cond_1,
            comp,
            lp_steam=lp_steam,
        )

        ia_remaining_heat = (
            react["ia_reac_heat_no_cond"]
            - cond_1["condenser_1_condensate_heat"]
            - cond_2["condenser_2_condensate_heat"]
        )

        if abs(ia_remaining_heat) < tolerance:
            ia_react_out_wat = (
                react["wat_in_reac_liq_mol"] * 18
                - cond_2["condenser_2_vap_wat_kg_h"]
            )

            ia_react_out_HAc = (
                react["hac_in_reac_liq_mol"] * 60
                - cond_2["condenser_2_vap_hac_kg_h"]
            )

            ia_react_out_IA = react["ia_in_reac_liq_mol"] * 166

            return (
                react,
                cond_1,
                cond_2,
                reactor_temp,
                ia_remaining_heat,
                ia_react_out_wat,
                ia_react_out_HAc,
                ia_react_out_IA,
            )

        if ia_remaining_heat > 0:
            reactor_temp += step
        else:
            reactor_temp -= step

    react = ia_react(mves, comp, ia_reac_temp=reactor_temp)

    cond_1 = condenser_1(
        react,
        comp,
        hp_steam=hp_steam,
    )

    cond_2 = condenser_2(
        react,
        cond_1,
        comp,
        lp_steam=lp_steam,
    )

    ia_remaining_heat = (
        react["ia_reac_heat_no_cond"]
        - cond_1["condenser_1_condensate_heat"]
        - cond_2["condenser_2_condensate_heat"]
    )

    ia_react_out_wat = (
        react["wat_in_reac_liq_mol"] * 18
        - cond_2["condenser_2_vap_wat_kg_h"]
    )

    ia_react_out_HAc = (
        react["hac_in_reac_liq_mol"] * 60
        - cond_2["condenser_2_vap_hac_kg_h"]
    )

    ia_react_out_IA = react["ia_in_reac_liq_mol"] * 166

    return (
        react,
        cond_1,
        cond_2,
        reactor_temp,
        ia_remaining_heat,
        ia_react_out_wat,
        ia_react_out_HAc,
        ia_react_out_IA,
    )


# =======================================================
# PATH IMAGE
# =======================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_PATH = os.path.join(BASE_DIR, "isophthalic_acid.png")

print("IMG_PATH used:", IMG_PATH)
print("File exists?", os.path.exists(IMG_PATH))
OPC_SERVER_URL = "opc.tcp://127.0.0.1:4842/isophthalic/server/"
OPC_SCAN_SEC = 2.0

opc_queue = queue.Queue()
opc_connected = False
opc_last_values = {}

# =======================================================
# UI TKINTER
# =======================================================
root = tk.Tk()
root.title("Glass Plant – Isophthalic Acid Reactor Assembly")
root.geometry("1400x820")

initializing = True

main_frame = tk.Frame(root)
main_frame.pack(fill="both", expand=True)

controls = tk.Frame(main_frame, bg="#222", width=340)
controls.pack(side="left", fill="y", padx=10, pady=10)
controls.pack_propagate(False)

img_frame = tk.Frame(main_frame, bg="white")
img_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

orig_img = Image.open(IMG_PATH)

target_w = 980
scale = target_w / orig_img.width
target_h = int(orig_img.height * scale)

base_img = orig_img.resize((target_w, target_h), Image.LANCZOS)

img_label = tk.Label(img_frame, bg="white")
img_label.pack(expand=True)

result_text = tk.StringVar()

try:
    font_big = ImageFont.truetype(
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        22,
    )
    font_med = ImageFont.truetype(
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        17,
    )
    font_small = ImageFont.truetype(
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        15,
    )
except Exception:
    font_big = ImageFont.load_default()
    font_med = ImageFont.load_default()
    font_small = ImageFont.load_default()


# =======================================================
# DRAW OVERLAY
# =======================================================
def make_overlay_image(
    mves,
    comp,
    react,
    cond_1,
    cond_2,
    residual_heat,
    reactor_temp,
    react_pressure_barg,
    hp_steam,
    lp_steam,
    ia_react_out_wat,
    ia_react_out_HAc,
    ia_react_out_IA,
):
    img = base_img.copy()
    draw = ImageDraw.Draw(img)

    # Feed box
    draw.rounded_rectangle(
        (10, 100, 260, 230),
        radius=18,
        fill=(220, 245, 255),
        outline="black",
        width=2,
    )

    draw.text((20, 100), "Feed", fill="black", font=font_big)
    draw.text(
        (20, 130),
        f"MX feed: {mves['mx_flow_to_rx_kg_h']:.0f} kg/h",
        fill="black",
        font=font_med,
    )
    draw.text(
        (20, 160),
        f"HAc feed: {mves['hac_flow_to_rx_kg_h']:.0f} kg/h",
        fill="black",
        font=font_med,
    )
    draw.text(
        (20, 190),
        f"Water:   {mves['water_flow_to_rx_kg_h']:.0f} kg/h",
        fill="black",
        font=font_med,
    )

    # Compressor box
    draw.rounded_rectangle(
        (20, 650, 340, 730),
        radius=18,
        fill=(255, 250, 210),
        outline="black",
        width=2,
    )

    draw.text((30, 650), "Compressor", fill="black", font=font_big)
    draw.text(
        (30, 680),
        f"N2: {comp['tot_air_to_react'] * 0.77:.0f} kg/h",
        fill="black",
        font=font_med,
    )
    draw.text(
        (200, 680),
        f"O2: {comp['tot_air_to_react'] * 0.23:.0f} kg/h",
        fill="black",
        font=font_med,
    )
    draw.text(
        (30, 710),
        f"P react: {react_pressure_barg:.1f} barg",
        fill="black",
        font=font_med,
    )

    # Vapour from reactor
    draw.rounded_rectangle(
        (285, 160, 480, 340),
        radius=18,
        fill=(255, 250, 210),
        outline="black",
        width=2,
    )

    draw.text((290, 170), "Vap from Reactor", fill="black", font=font_big)
    draw.text(
        (290, 210),
        f"T reactor: {reactor_temp:.1f} °C",
        fill="black",
        font=font_med,
    )
    draw.text(
        (290, 250),
        f"Vap H2O: {react['ia_react_vap_wat_kg_h']:.0f} kg/h",
        fill="black",
        font=font_med,
    )
    draw.text(
        (290, 290),
        f"Vap HAc: {react['ia_react_vap_hac_kg_h']:.0f} kg/h",
        fill="black",
        font=font_med,
    )

    # Condenser 1
    draw.rounded_rectangle(
        (530, 200, 730, 360),
        radius=18,
        fill=(220, 245, 255),
        outline="black",
        width=2,
    )

    draw.text((535, 210), "Condenser 1", fill="black", font=font_big)
    draw.text(
        (535, 240),
        f"HP steam: {hp_steam:.1f} barg",
        fill="black",
        font=font_med,
    )
    draw.text(
        (535, 270),
        f"Exit T:   {cond_1['condenser_1_exit_temp']:.1f} °C",
        fill="black",
        font=font_med,
    )
    draw.text(
        (535, 300),
        f"Cond H2O: {cond_1['condenser_1_cond_wat_kg_h']:.0f} kg/h",
        fill="black",
        font=font_med,
    )
    draw.text(
        (535, 330),
        f"Cond HAc: {cond_1['condenser_1_cond_hac_kg_h']:.0f} kg/h",
        fill="black",
        font=font_med,
    )

    # Condenser 2
    draw.rounded_rectangle(
        (750, 200, 955, 360),
        radius=18,
        fill=(230, 255, 230),
        outline="black",
        width=2,
    )

    draw.text((755, 210), "Condenser 2", fill="black", font=font_big)
    draw.text(
        (755, 240),
        f"LP steam: {lp_steam:.1f} barg",
        fill="black",
        font=font_med,
    )
    draw.text(
        (755, 270),
        f"Exit T:   {cond_2['condenser_2_exit_temp']:.1f} °C",
        fill="black",
        font=font_med,
    )
    draw.text(
        (755, 300),
        f"Cond H2O: {cond_2['condenser_2_cond_wat_kg_h']:.0f} kg/h",
        fill="black",
        font=font_med,
    )
    draw.text(
        (755, 330),
        f"Cond HAc: {cond_2['condenser_2_cond_hac_kg_h']:.0f} kg/h",
        fill="black",
        font=font_med,
    )

    # To scrubber
    draw.rounded_rectangle(
        (825, 0, 990, 90),
        radius=18,
        fill=(255, 235, 235),
        outline="black",
        width=2,
    )

    draw.text((835, 5), "To scrubber", fill="black", font=font_med)
    draw.text(
        (830, 35),
        f"Vap HAc: {cond_2['condenser_2_vap_hac_kg_h']:.0f}",
        fill="black",
        font=font_med,
    )
    draw.text(
        (830, 65),
        f"Vap wat: {cond_2['condenser_2_vap_wat_kg_h']:.0f}",
        fill="black",
        font=font_med,
    )

    # To crystallizer
    draw.rounded_rectangle(
        (675, 500, 950, 700),
        radius=18,
        fill=(255, 235, 235),
        outline="black",
        width=2,
    )

    draw.text((680, 510), "To crystallizer", fill="black", font=font_med)
    draw.text(
        (680, 550),
        f"Water: {ia_react_out_wat:.0f} kg/h",
        fill="black",
        font=font_med,
    )
    draw.text(
        (680, 590),
        f"HAc: {ia_react_out_HAc:.0f} kg/h",
        fill="black",
        font=font_med,
    )
    draw.text(
        (680, 630),
        f"Isopht Acid: {ia_react_out_IA:.0f} kg/h",
        fill="black",
        font=font_med,
    )

    # Thickness index
    liq_dilution = ia_react_out_wat + 0.7 * ia_react_out_HAc

    if liq_dilution > 0:
        thickness_index = ia_react_out_IA / liq_dilution
    else:
        thickness_index = 1.0

    if thickness_index < 0.330:
        box_color = (0, 180, 0)
        border_color = "darkgreen"
        status_text = "OK"
        status_fill = "darkgreen"
    elif thickness_index < 0.345:
        box_color = (255, 165, 0)
        border_color = "orange"
        status_text = "WARNING"
        status_fill = "orange"
    else:
        box_color = (255, 0, 0)
        border_color = "red"
        status_text = "NOT OK"
        status_fill = "red"

    draw.rectangle(
        (445, 445, 550, 580),
        fill=box_color,
        outline=border_color,
        width=4,
    )

    draw.text(
        (445, 590),
        f"Thick idx: {thickness_index:.3f}",
        fill="black",
        font=font_small,
    )

    draw.text(
        (445, 620),
        f"Status: {status_text}",
        fill=status_fill,
        font=font_small,
    )

    return img
# =======================================================
# SIMULATED DCS FEED SIGNAL - FIXED 2 SECOND CLOCK
# =======================================================
#import time

#dcs_simulation_running = False
#dcs_feed_high = False
#dcs_after_id = None
#dcs_next_time = None


#def simulate_dcs_feed():
#    global dcs_feed_high, dcs_after_id, dcs_next_time

#    if not dcs_simulation_running:
#        return

#    now = time.monotonic()

#    if dcs_next_time is None:
#        dcs_next_time = now

#    # Alternate between two simulated DCS values
#    if dcs_feed_high:
#        new_feed = 5450
#    else:
#        new_feed = 5550
#
#    dcs_feed_high = not dcs_feed_high
#
#    print("DCS simulated MX feed:", new_feed)
#
    # Avoid double update from slider command
#    mx_slider.config(command="")
#    mx_slider.set(new_feed)
#    mx_slider.config(command=update_model)

    # Force one model update
#    update_model()

    # Fixed 15 second schedule
#    dcs_next_time += 2.0

#    delay_seconds = max(0.1, dcs_next_time - time.monotonic())
#    delay_ms = int(delay_seconds * 1000)

#    dcs_after_id = root.after(delay_ms, simulate_dcs_feed)


#def start_dcs_simulation():
#    global dcs_simulation_running, dcs_after_id, dcs_next_time

#    if dcs_simulation_running:
#        return

#    print("Starting DCS simulation")

#    dcs_simulation_running = True
#    dcs_next_time = time.monotonic()

#    if dcs_after_id is not None:
#        root.after_cancel(dcs_after_id)
#        dcs_after_id = None
#
#    simulate_dcs_feed()


#def stop_dcs_simulation():
#    global dcs_simulation_running, dcs_after_id, dcs_next_time
#
#    print("Stopping DCS simulation")

#    dcs_simulation_running = False
#    dcs_next_time = None

#    if dcs_after_id is not None:
#        root.after_cancel(dcs_after_id)
#        dcs_after_id = None

#    update_model()
# =======================================================
# UPDATE MODEL
# =======================================================
def update_model(val=None):
    global initializing

    if initializing:
        return

    mx_value = mx_slider.get()
    react_pressure_barg = pressure_slider.get()
    hp_steam = hp_steam_slider.get()
    lp_steam = lp_steam_slider.get()

    mves = mixing_vessel(
        mx_flow_kg_h=mx_value,
        hac_mx_rat=hac_mx_rat,
        water_in_feed=0.07,
    )

    comp = comp_flow(
        mves,
        react_pressure_barg=react_pressure_barg,
    )

    (
        react,
        cond_1,
        cond_2,
        reactor_temp,
        ia_remaining_heat,
        ia_react_out_wat,
        ia_react_out_HAc,
        ia_react_out_IA,
    ) = solve_reactor(
        mves,
        comp,
        hp_steam=hp_steam,
        lp_steam=lp_steam,
        start_temp=206.0,
        step=0.1,
        tolerance=1000,
        max_iter=80,
    )

    liq_dilution = ia_react_out_wat + 0.7 * ia_react_out_HAc

    if liq_dilution > 0:
        thickness_index = ia_react_out_IA / liq_dilution
    else:
        thickness_index = 1.0

    result_text.set(
        f"MX feed: {mx_value:.0f} kg/h\n"
        f"OPC connection: {'ON' if opc_connected else 'OFF'}\n\n"
    #    f"DCS simulation: {'ON' if dcs_simulation_running else 'OFF'}\n\n"
        f"Total feed: {mves['total_feed']:.1f} kg/h\n"
        f"HAc feed: {mves['hac_flow_to_rx_kg_h']:.1f} kg/h\n"
        f"Water feed: {mves['water_flow_to_rx_kg_h']:.1f} kg/h\n\n"
        f"Reactor pressure: {react_pressure_barg:.1f} barg\n"
        f"HP steam pressure: {hp_steam:.1f} barg\n"
        f"LP steam pressure: {lp_steam:.1f} barg\n\n"
        f"Cond-1 exit T: {cond_1['condenser_1_exit_temp']:.1f} °C\n"
        f"Cond-2 exit T: {cond_2['condenser_2_exit_temp']:.1f} °C\n\n"
        f"Air to reactor: {comp['tot_air_to_react']:.1f} kg/h\n"
        f"Air temp after comp: {comp['air_temp_comp']:.1f} °C\n"
        f"Reactor temp: {reactor_temp:.2f} °C\n"
        f"Residual heat: {ia_remaining_heat:,.1f} kcal/h\n\n"
        f"Cond-1 HAc cond: {cond_1['condenser_1_cond_hac_kg_h']:.1f} kg/h\n"
        f"Cond-2 HAc cond: {cond_2['condenser_2_cond_hac_kg_h']:.1f} kg/h\n"
        f"To scrubber HAc: {cond_2['condenser_2_vap_hac_kg_h']:.1f} kg/h\n"
        f"To scrubber H2O: {cond_2['condenser_2_vap_wat_kg_h']:.1f} kg/h\n\n"
        f"Thickness index: {thickness_index:.3f}"
    )

    if thickness_index < 0.330:
        op_msg = "Thickness index OK"
    elif thickness_index < 0.345:
        op_msg = "Thickness index WARNING.\nCheck crystallizer feed dilution."
    else:
        op_msg = "Thickness index NOT OK.\nCheck dilution / crystallizer feed."
reactor_temp_dcs = opc_last_values.get("reactor_temp_dcs")
thickness_index_dcs = opc_last_values.get("thickness_index_dcs")

if reactor_temp_dcs is not None:
      reactor_temp_delta = reactor_temp_dcs - reactor_temp
else:
        reactor_temp_delta = None

if thickness_index_dcs is not None:
        thickness_delta = thickness_index_dcs - thickness_index
else:
        thickness_delta = None
        operators_text.config(text=op_msg)

        overlay = make_overlay_image(
            mves,
            comp,
            react,
            cond_1,
            cond_2,
            ia_remaining_heat,
            reactor_temp,
            react_pressure_barg,
            hp_steam,
            lp_steam,
            ia_react_out_wat,
            ia_react_out_HAc,
            ia_react_out_IA,
        )

        photo = ImageTk.PhotoImage(overlay)
        img_label.config(image=photo)
        img_label.image = photo


# =======================================================
# CONTROLS
# =======================================================
title_lbl = tk.Label(
    controls,
    text="Glass Plant Controls",
    bg="#222",
    fg="white",
    font=("Arial", 16, "bold"),
)

title_lbl.pack(padx=12, pady=(18, 20), anchor="w")


# -------------------------------------------------------
# Meta-xylene slider
# -------------------------------------------------------
mx_title = tk.Label(
    controls,
    text="Meta-xylene flow (kg/h)",
    bg="#222",
    fg="white",
    font=("Arial", 12, "bold"),
)

mx_title.pack(padx=12, pady=(12, 6), anchor="w")

mx_slider = tk.Scale(
    controls,
    from_=3000,
    to=8000,
    resolution=50,
    orient="horizontal",
    length=280,
    command=update_model,
    bg="#222",
    fg="white",
    troughcolor="#666",
    highlightthickness=0,
)

mx_slider.pack(padx=12, pady=6)
mx_slider.set(5300)


# -------------------------------------------------------
# Reactor pressure slider
# -------------------------------------------------------
pressure_title = tk.Label(
    controls,
    text="Reactor pressure (barg)",
    bg="#222",
    fg="white",
    font=("Arial", 12, "bold"),
)

pressure_title.pack(padx=12, pady=(14, 6), anchor="w")

pressure_slider = tk.Scale(
    controls,
    from_=10.0,
    to=20.0,
    resolution=0.1,
    orient="horizontal",
    length=280,
    command=update_model,
    bg="#222",
    fg="white",
    troughcolor="#666",
    highlightthickness=0,
)

pressure_slider.pack(padx=12, pady=6)
pressure_slider.set(15.0)


# -------------------------------------------------------
# HP steam slider
# -------------------------------------------------------
hp_steam_title = tk.Label(
    controls,
    text="High pressure steam (barg)",
    bg="#222",
    fg="white",
    font=("Arial", 12, "bold"),
)

hp_steam_title.pack(padx=12, pady=(14, 6), anchor="w")

hp_steam_slider = tk.Scale(
    controls,
    from_=4.0,
    to=8.0,
    resolution=0.1,
    orient="horizontal",
    length=280,
    command=update_model,
    bg="#222",
    fg="white",
    troughcolor="#666",
    highlightthickness=0,
)

hp_steam_slider.pack(padx=12, pady=6)
hp_steam_slider.set(6.5)


# -------------------------------------------------------
# LP steam slider
# -------------------------------------------------------
lp_steam_title = tk.Label(
    controls,
    text="Low pressure steam (barg)",
    bg="#222",
    fg="white",
    font=("Arial", 12, "bold"),
)

lp_steam_title.pack(padx=12, pady=(14, 6), anchor="w")

lp_steam_slider = tk.Scale(
    controls,
    from_=1.0,
    to=4.0,
    resolution=0.1,
    orient="horizontal",
    length=280,
    command=update_model,
    bg="#222",
    fg="white",
    troughcolor="#666",
    highlightthickness=0,
)

lp_steam_slider.pack(padx=12, pady=6)
lp_steam_slider.set(2.5)

dcs_title = tk.Label(
    controls,
    text="Simulated DCS connection",
    bg="#222",
    fg="cyan",
    font=("Arial", 12, "bold")
)
dcs_title.pack(padx=12, pady=(14, 6), anchor="w")

start_dcs_btn = tk.Button(
    controls,
    text="Start DCS feed simulation",
    command=start_dcs_simulation,
    bg="#444",
    fg="white",
    font=("Arial", 11)
)
start_dcs_btn.pack(fill="x", padx=12, pady=4)

stop_dcs_btn = tk.Button(
    controls,
    text="Stop DCS feed simulation",
    command=stop_dcs_simulation,
    bg="#444",
    fg="white",
    font=("Arial", 11)
)
stop_dcs_btn.pack(fill="x", padx=12, pady=4)
# -------------------------------------------------------
# Result label
# -------------------------------------------------------
result_label = tk.Label(
    controls,
    textvariable=result_text,
    justify="left",
    anchor="nw",
    bg="#222",
    fg="white",
    font=("Arial", 12),
)

result_label.pack(fill="x", padx=12, pady=20)


# -------------------------------------------------------
# Operator indication
# -------------------------------------------------------
operators_title = tk.Label(
    controls,
    text="Indications for operators",
    bg="#222",
    fg="yellow",
    font=("Arial", 12, "bold"),
    justify="left",
    anchor="w",
)

operators_title.pack(fill="x", padx=12, pady=(10, 4))

operators_text = tk.Label(
    controls,
    text="---",
    bg="#222",
    fg="yellow",
    font=("Arial", 11),
    justify="left",
    anchor="w",
)

operators_text.pack(fill="x", padx=12, pady=(0, 10))


# =======================================================
# START MODEL
# =======================================================
initializing = False
#update_model()

root.mainloop()
start_opc_thread()
poll_opc_queue()
update_model()
root.mainloop()