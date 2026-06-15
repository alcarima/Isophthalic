import math
import os
import tkinter as tk
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

    o2_reac = float(mves["mx_flow_to_rx_kg_h"]) / 106 * 3 * 32

    o2_mx_comb = float(
        mves["mx_flow_to_rx_kg_h"] / 106 * ((mx_conv - 106 / 166) / mx_conv)
    ) * 10.5 * 32

    o2_hac_comb = float(mves["mx_flow_to_rx_kg_h"] / 0.71 / 1000 * 65 / 60 * 2 * 32)

    tot_o2_react = o2_reac + o2_hac_comb
    tot_o2 = tot_o2_react / (1 - 0.13)
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
    ia_react_n2_offgas_mol = float(comp["tot_air_to_react"] * 0.77 / 28)
    ia_react_o2_offgas_mol = float(
        (comp["total_o2_rx_kg_h"] - comp["o2_to_iso_kg_h"] - comp["o2_to_hac_comb_kg_h"]) / 32
    )
    ia_react_co2_offgas_mol = float(comp["o2_to_hac_comb_kg_h"] / 32)
    ia_react_inc_offgas_mol = (
        ia_react_co2_offgas_mol + ia_react_n2_offgas_mol + ia_react_o2_offgas_mol
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
        ia_react_liq_wat_mol + ia_react_liq_ia_mol + ia_react_liq_hac_mol
    )

    ia_react_liq_x_hac_mol = ia_react_liq_hac_mol / ia_react_liq_tot_mol
    ia_react_liq_x_wat_mol = ia_react_liq_wat_mol / ia_react_liq_tot_mol

    ia_react_watpress = math.exp(18.36 - (3840.96 / (ia_reac_temp + 228.3))) / 760.0
    ia_react_hacpress = math.exp(19.32 - (5495.31 / (ia_reac_temp + 314.75))) / 760.0

    ia_react_y_hac = ia_react_liq_x_hac_mol * ia_react_hacpress / comp["comp_pressure_bara"]
    ia_react_y_wat = ia_react_liq_x_wat_mol * ia_react_watpress / comp["comp_pressure_bara"]

    ia_react_y_incond = 1 - ia_react_y_hac - ia_react_y_wat
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
        * (556.6107 - 23.2115 * math.sqrt(comp["comp_pressure_bara"] * (1 - ia_react_y_incond)))
        + ia_react_y_hac * ia_react_vap_tot_mol * 60 * 81
    )

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

        if condenser_1_y_incon <= 0:
            condenser_1_y_incon = 1e-6

        condenser_1_vap_tot_mol = react["incondens_offgas_mol"] / condenser_1_y_incon
        condenser_1_vap_wat_mol = condenser_1_vap_tot_mol * condenser_1_y_wat
        condenser_1_vap_hac_mol = condenser_1_vap_tot_mol * condenser_1_y_hac

        condenser_1_vap_wat_kg_h = condenser_1_vap_wat_mol * 18
        condenser_1_vap_hac_kg_h = condenser_1_vap_hac_mol * 60

        condenser_1_cond_wat_kg_h = react["ia_react_vap_wat_kg_h"] - condenser_1_vap_wat_kg_h
        condenser_1_cond_hac_kg_h = react["ia_react_vap_hac_kg_h"] - condenser_1_vap_hac_kg_h

        if condenser_1_cond_wat_kg_h < 0:
            condenser_1_cond_wat_kg_h = 0.0
        if condenser_1_cond_hac_kg_h < 0:
            condenser_1_cond_hac_kg_h = 0.0

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

        if condenser_2_y_incon <= 0:
            condenser_2_y_incon = 1e-6

        condenser_2_vap_tot_mol = react["incondens_offgas_mol"] / condenser_2_y_incon
        condenser_2_vap_wat_mol = condenser_2_vap_tot_mol * condenser_2_y_wat
        condenser_2_vap_hac_mol = condenser_2_vap_tot_mol * condenser_2_y_hac

        condenser_2_vap_wat_kg_h = condenser_2_vap_wat_mol * 18
        condenser_2_vap_hac_kg_h = condenser_2_vap_hac_mol * 60

        condenser_2_cond_wat_kg_h = cond_1["condenser_1_vap_wat_kg_h"] - condenser_2_vap_wat_kg_h
        condenser_2_cond_hac_kg_h = cond_1["condenser_1_vap_hac_kg_h"] - condenser_2_vap_hac_kg_h

        if condenser_2_cond_wat_kg_h < 0:
            condenser_2_cond_wat_kg_h = 0.0
        if condenser_2_cond_hac_kg_h < 0:
            condenser_2_cond_hac_kg_h = 0.0

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
# SOLVER REACTOR TEMPERATURE
# =========================================================
def solve_reactor(mves, comp, start_temp=206.0, step=0.1, tolerance=1000, max_iter=80):
    reactor_temp = start_temp

    for _ in range(max_iter):
        react = ia_react(mves, comp, ia_reac_temp=reactor_temp)
        cond_1 = condenser_1(react, comp)
        cond_2 = condenser_2(react, cond_1, comp)

        ia_remaining_heat = (
            react["ia_reac_heat_no_cond"]
            - cond_1["condenser_1_condensate_heat"]
            - cond_2["condenser_2_condensate_heat"]
        )

        if abs(ia_remaining_heat) < tolerance:
            ia_react_out_wat = react["wat_in_reac_liq_mol"] * 18 - cond_2["condenser_2_vap_wat_kg_h"]
            ia_react_out_HAc = react["hac_in_reac_liq_mol"] * 60 - cond_2["condenser_2_vap_hac_kg_h"]
            return react, cond_1, cond_2, reactor_temp, ia_remaining_heat, ia_react_out_wat

        if ia_remaining_heat > 0:
            reactor_temp += step
        else:
            reactor_temp -= step

    react = ia_react(mves, comp, ia_reac_temp=reactor_temp)
    cond_1 = condenser_1(react, comp)
    cond_2 = condenser_2(react, cond_1, comp)

    ia_remaining_heat = (
        react["ia_reac_heat_no_cond"]
        - cond_1["condenser_1_condensate_heat"]
        - cond_2["condenser_2_condensate_heat"]
    )
    ia_react_out_wat = react["wat_in_reac_liq_mol"]*18 - cond_2["condenser_2_vap_wat_kg_h"]
    ia_react_out_HAc = react["hac_in_reac_liq_mol"] * 60 - cond_2["condenser_2_vap_hac_kg_h"]
    ia_react_out_IA = react["ia_in_reac_liq_mol"]*166
    print("reactor tot water : " , react["wat_in_reac_liq_mol"]*18)
    print("ia reactor water : " , ia_react_out_wat)
    return react, cond_1, cond_2, reactor_temp, ia_remaining_heat,ia_react_out_wat,ia_react_out_HAc, ia_react_out_IA


# =======================================================
# PATH IMMAGINE
# =======================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_PATH = os.path.join(BASE_DIR, "isophthalic_acid.png")
print("IMG_PATH usato:", IMG_PATH)
print("File esiste?", os.path.exists(IMG_PATH))


# =======================================================
# UI TKINTER
# =======================================================
root = tk.Tk()
root.title("Glass Plant – Isophthalic Acid (Reactor Assembly)")
root.geometry("1400x820")

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
target_h = int(orig_img.height * 1.0 * scale)
base_img = orig_img.resize((target_w, target_h), Image.LANCZOS)

img_label = tk.Label(img_frame, bg="white")
img_label.pack(expand=True)

result_text = tk.StringVar()

try:
    font_big = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 22)
    font_med = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 17)
    font_small = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 15)
except Exception:
    font_big = ImageFont.load_default()
    font_med = ImageFont.load_default()
    font_small = ImageFont.load_default()


# =======================================================
# DRAW OVERLAY
# =======================================================
def make_overlay_image(mves, comp, react, cond_1, cond_2, residual_heat, reactor_temp,
                       react_pressure_barg, ia_react_out_wat, ia_react_out_HAc, ia_react_out_IA):
    img = base_img.copy()
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle((10, 100, 260, 230), radius=18, fill=(220, 245, 255), outline="black", width=2)
    draw.text((20, 100), "Feed", fill="black", font=font_big)
    draw.text((20, 130), f"MX feed: {mves['mx_flow_to_rx_kg_h']:.0f} kg/h", fill="black", font=font_med)
    draw.text((20, 160), f"HAc feed: {mves['hac_flow_to_rx_kg_h']:.0f} kg/h", fill="black", font=font_med)
    draw.text((20, 190), f"Water:   {mves['water_flow_to_rx_kg_h']:.0f} kg/h", fill="black", font=font_med)



    draw.rounded_rectangle((20, 650, 340, 730), radius=18, fill=(255, 250, 210), outline="black", width=2)
    draw.text((30, 650), "Compressor", fill="black", font=font_big)
    draw.text((30, 680), f"N2:     {comp['tot_air_to_react']*0.77:.0f} kg/h", fill="black", font=font_med)
    draw.text((200, 680), f"O2:     {comp['tot_air_to_react']*0.23:.0f} kg/h", fill="black", font=font_med)
    draw.text((30, 710), f"P react: {react_pressure_barg:.1f} barg", fill="black", font=font_med)

    draw.rounded_rectangle((285, 160, 480, 340), radius=18, fill=(255, 250, 210), outline="black", width=2)
    draw.text((290, 170), "Vap from Reactor", fill="black", font=font_big)
    draw.text((290, 210), f"T reactor: {reactor_temp:.1f} °C", fill="black", font=font_med)
    draw.text((290, 250), f"Vap H2O: {react['ia_react_vap_wat_kg_h']:.0f} kg/h", fill="black", font=font_med)
    draw.text((290, 290), f"Vap HAc: {react['ia_react_vap_hac_kg_h']:.0f} kg/h", fill="black", font=font_med)

    draw.rounded_rectangle((530, 220, 720, 350), radius=18, fill=(220, 245, 255), outline="black", width=2)
    draw.text((535, 230), "Condenser 1", fill="black", font=font_big)
    draw.text((535, 260), f"Exit T:   {cond_1['condenser_1_exit_temp']:.1f} °C", fill="black", font=font_med)
    draw.text((535, 290), f"Cond H2O: {cond_1['condenser_1_cond_wat_kg_h']:.0f} kg/h", fill="black", font=font_med)
    draw.text((535, 320), f"Cond HAc: {cond_1['condenser_1_cond_hac_kg_h']:.0f} kg/h", fill="black", font=font_med)

    draw.rounded_rectangle((740, 220, 930, 350), radius=18, fill=(230, 255, 230), outline="black", width=2)
    draw.text((745, 230), "Condenser 2", fill="black", font=font_big)
    draw.text((745, 260), f"Exit T:   {cond_2['condenser_2_exit_temp']:.1f} °C", fill="black", font=font_med)
    draw.text((745, 290), f"Cond H2O: {cond_2['condenser_2_cond_wat_kg_h']:.0f} kg/h", fill="black", font=font_med)
    draw.text((745, 320), f"Cond HAc: {cond_2['condenser_2_cond_hac_kg_h']:.0f} kg/h", fill="black", font=font_med)

    draw.rounded_rectangle((825, 0, 990, 90), radius=18, fill=(255, 235, 235), outline="black", width=2)
    draw.text((835, 5), "To scrubber", fill="black", font=font_med)
    draw.text((830, 35), f"Vap HAc:{cond_2['condenser_2_vap_hac_kg_h']:.0f} kg/h", fill="black", font=font_med)
    draw.text((830, 65), f"Vap wat:{cond_2['condenser_2_vap_wat_kg_h']:.0f} kg/h", fill="black", font=font_med)

    draw.rounded_rectangle((675, 500, 950, 700), radius=18, fill=(255, 235, 235), outline="black", width=2)
    draw.text((680, 510), "To crystallizer", fill="black", font=font_med)
    draw.text((680, 550), f"wat to cryst:{ia_react_out_wat:.0f} kg/h", fill="black", font=font_med)
    draw.text((680, 590), f"HAc to cryst:{ia_react_out_HAc:.0f} kg/h", fill="black", font=font_med)
    draw.text((680, 630), f"Isopht Acid to cryst:{ia_react_out_IA:.0f} kg/h", fill="black", font=font_med)

    liq_dilution = ia_react_out_wat + 0.7 * ia_react_out_HAc

    if liq_dilution > 0:
        thickness_index = ia_react_out_IA / liq_dilution
    else:
        thickness_index = 1.0

    low_limit = 0.10
    high_limit = 0.35

    thickness_vis = (thickness_index - low_limit) / (high_limit - low_limit)
    thickness_vis = max(0.0, min(1.0, thickness_vis))

    r = int(255 * thickness_vis)
    g = int(255 * (1.0 - thickness_vis))
    b = 0

    draw.rectangle((445, 445, 550, 580), fill=(r, g, b), outline="blue", width=2)

    if thickness_index < 0.345:
        thick_status = "OK"
    else:
        thick_status = "not OK"

    draw.text((445, 590), f"Thick idx: {thickness_index:.3f}", fill="black", font=font_small)
    draw.text((445, 620), f"Status: {thick_status}", fill="black", font=font_small)

    print("thickness_index =", thickness_index, "thickness_vis =", thickness_vis, "RGB =", r, g, b, "Status =", thick_status)

    return img
    
# =======================================================
# UPDATE MODEL
# =======================================================
def update_model(val=None):
    mx_value = mx_slider.get()
    react_pressure_barg = pressure_slider.get()

    mves = mixing_vessel(mx_flow_kg_h=mx_value, hac_mx_rat=hac_mx_rat, water_in_feed=0.07)
    comp = comp_flow(mves, react_pressure_barg=react_pressure_barg)

    react, cond_1, cond_2, reactor_temp, ia_remaining_heat, ia_react_out_wat, ia_react_out_HAc,ia_react_out_IA  = solve_reactor(
        mves, comp, start_temp=206.0, step=0.1, tolerance=1000, max_iter=80
    )

    result_text.set(
        f"MX feed: {mx_value:.0f} kg/h\n\n"
        f"Total feed: {mves['total_feed']:.1f} kg/h\n"
        f"HAc feed: {mves['hac_flow_to_rx_kg_h']:.1f} kg/h\n"
        f"Water feed: {mves['water_flow_to_rx_kg_h']:.1f} kg/h\n\n"
        f"Reactor pressure: {react_pressure_barg:.1f} barg\n"
        f"Air to reactor: {comp['tot_air_to_react']:.1f} kg/h\n"
        f"Air temp after comp: {comp['air_temp_comp']:.1f} °C\n"
        f"Reactor temp: {reactor_temp:.2f} °C\n"
        f"Residual heat: {ia_remaining_heat:,.1f} kcal/h\n\n"
        f"Cond-1 HAc cond: {cond_1['condenser_1_cond_hac_kg_h']:.1f} kg/h\n"
        f"Cond-2 HAc cond: {cond_2['condenser_2_cond_hac_kg_h']:.1f} kg/h"
    )

    overlay = make_overlay_image (
    mves,
    comp,
    react,
    cond_1,
    cond_2,
    ia_remaining_heat,
    reactor_temp,
    react_pressure_barg,
    ia_react_out_wat,
    ia_react_out_HAc,
    ia_react_out_IA
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
    font=("Arial", 16, "bold")
)
title_lbl.pack(padx=12, pady=(18, 20), anchor="w")

mx_title = tk.Label(
    controls,
    text="Meta-xylene flow (kg/h)",
    bg="#222",
    fg="white",
    font=("Arial", 12, "bold")
)
mx_title.pack(padx=12, pady=(10, 6), anchor="w")

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
    highlightthickness=0
)
mx_slider.pack(padx=12, pady=6)
mx_slider.set(5300)
pressure_title = tk.Label(
    controls,
    text="Reactor pressure (barg)",
    bg="#222",
    fg="white",
    font=("Arial", 12, "bold")
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
    highlightthickness=0
)
pressure_slider.pack(padx=12, pady=6)
pressure_slider.set(15.0)
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

update_model()
root.mainloop()