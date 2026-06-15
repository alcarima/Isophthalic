"""
isophthalic_client_vs1.py

Glass Plant - Isophthalic Acid Reactor Assembly
OPC UA client + Tkinter visual interface.

Purpose:
- Read live OPC UA values from the Isophthalic OPC UA server.
- Run an engineering model.
- Compare model values with DCS/OPC values.
- Display operator guidance.

Required files in the same folder:
- Isophthalic.drawio.png
- opcua_tags_isophthalic.py is NOT required; tag mapping is inside this file.

Run:
    python3 isophthalic_client_vs1.py
"""

import asyncio
import math
import os
import queue
import threading
import tkinter as tk
from dataclasses import dataclass
from typing import Any, Dict, Optional

from PIL import Image, ImageDraw, ImageFont, ImageTk
from asyncua import Client


# =========================================================
# GLOBAL CONFIGURATION
# =========================================================

OPC_SERVER_URL = "opc.tcp://127.0.0.1:4842/isophthalic/server/"
OPC_SCAN_SEC = 2.0

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_PATH = os.path.join(BASE_DIR, "Isophthalic.drawio.png")

HAC_MX_RATIO_DEFAULT = 6.7
WATER_IN_FEED_DEFAULT = 0.07

OPC_TAG_NAMES = {
    "mx_feed": ["Feed", "MX_Feed_kg_h"],
    "reactor_pressure_barg": ["Reactor", "Reactor_Pressure_barg"],
    "hp_steam": ["Utilities", "HP_Steam_Pressure_barg"],
    "lp_steam": ["Utilities", "LP_Steam_Pressure_barg"],
    "reactor_temp_dcs": ["Reactor", "Reactor_Temperature_C"],
    "thickness_index_dcs": ["Product", "Thickness_Index"],
}


# =========================================================
# SMALL UTILITIES
# =========================================================

def safe_div(numerator: float, denominator: float, default: float = 0.0) -> float:
    if abs(denominator) < 1e-12:
        return default
    return numerator / denominator


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


# =========================================================
# ENGINEERING MODEL
# =========================================================

def mixing_vessel(
    water_in_feed: float = WATER_IN_FEED_DEFAULT,
    hac_mx_rat: float = HAC_MX_RATIO_DEFAULT,
    mx_flow_kg_h: float = 5300.0,
) -> Dict[str, float]:
    hac_flow_kg_h = mx_flow_kg_h * hac_mx_rat
    water_flow_kg_h = (hac_flow_kg_h + mx_flow_kg_h) * water_in_feed
    total_feed = mx_flow_kg_h + hac_flow_kg_h + water_flow_kg_h

    return {
        "total_feed": total_feed,
        "mx_flow_to_rx_kg_h": mx_flow_kg_h,
        "hac_flow_to_rx_kg_h": hac_flow_kg_h,
        "water_flow_to_rx_kg_h": water_flow_kg_h,
    }


def comp_flow(
    mves: Dict[str, float],
    mx_conv: float = 0.695,
    t_atm: float = 30.0,
    react_pressure_barg: float = 15.0,
) -> Dict[str, float]:
    react_pressure_bara = react_pressure_barg + 1.0
    mx_flow = mves["mx_flow_to_rx_kg_h"]

    o2_reac = mx_flow / 106.0 * 3.0 * 32.0

    o2_mx_comb = (
        mx_flow / 106.0 * ((mx_conv - 106.0 / 166.0) / mx_conv) * 10.5 * 32.0
    )

    o2_hac_comb = mx_flow / 0.71 / 1000.0 * 65.0 / 60.0 * 2.0 * 32.0

    tot_o2_react = o2_reac + o2_hac_comb
    tot_o2 = safe_div(tot_o2_react, 1.0 - 0.13)
    tot_air = safe_div(tot_o2, 0.23)

    air_temp_comp = (
        (react_pressure_bara / 1.0) ** ((1.4 - 1.0) / 1.4)
    ) * (t_atm + 273.15) - 273.15
    air_temp_comp = min(air_temp_comp, 111.0)

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


def ia_react(
    mves: Dict[str, float],
    comp: Dict[str, float],
    ia_reac_temp: float = 206.0,
) -> Dict[str, float]:
    pressure_bara = comp["comp_pressure_bara"]

    n2_offgas_mol = comp["tot_air_to_react"] * 0.77 / 28.0

    o2_offgas_mol = (
        comp["total_o2_rx_kg_h"]
        - comp["o2_to_iso_kg_h"]
        - comp["o2_to_hac_comb_kg_h"]
    ) / 32.0

    co2_offgas_mol = comp["o2_to_hac_comb_kg_h"] / 32.0

    incondens_offgas_mol = n2_offgas_mol + o2_offgas_mol + co2_offgas_mol

    wat_liq_mol = (
        mves["water_flow_to_rx_kg_h"] / 18.0
        + mves["mx_flow_to_rx_kg_h"] / 106.0 * 2.0
        + mves["mx_flow_to_rx_kg_h"] / 0.71 * 65.0 / 1000.0 * 2.0 / 18.0
    )

    hac_liq_mol = (
        mves["hac_flow_to_rx_kg_h"] / 60.0
        - mves["mx_flow_to_rx_kg_h"] / 0.71 * 65.0 / 1000.0 * 2.0 / 60.0
    )

    ia_liq_mol = mves["mx_flow_to_rx_kg_h"] / 106.0
    total_liq_mol = wat_liq_mol + hac_liq_mol + ia_liq_mol

    x_hac = safe_div(hac_liq_mol, total_liq_mol)
    x_wat = safe_div(wat_liq_mol, total_liq_mol)

    water_press_atm = math.exp(18.36 - (3840.96 / (ia_reac_temp + 228.3))) / 760.0
    hac_press_atm = math.exp(19.32 - (5495.31 / (ia_reac_temp + 314.75))) / 760.0

    y_hac = x_hac * hac_press_atm / pressure_bara
    y_wat = x_wat * water_press_atm / pressure_bara
    y_incond = max(1.0 - y_hac - y_wat, 1e-6)

    vap_total_mol = incondens_offgas_mol / y_incond
    vap_wat_kg_h = vap_total_mol * y_wat * 18.0
    vap_hac_kg_h = vap_total_mol * y_hac * 60.0

    heat_react = (
        mves["mx_flow_to_rx_kg_h"] * 2672.89
        + mves["mx_flow_to_rx_kg_h"] / 106.0 * 166.0 * 35.0 * 10.0 * 1.15
    )

    heat_evap = (
        y_wat
        * vap_total_mol
        * 18.0
        * (556.6107 - 23.2115 * math.sqrt(pressure_bara * (1.0 - y_incond)))
        + y_hac * vap_total_mol * 60.0 * 81.0
    )

    liq_feed_heat = (
        mves["mx_flow_to_rx_kg_h"] * 0.41
        + mves["water_flow_to_rx_kg_h"]
        + mves["hac_flow_to_rx_kg_h"] * 0.5
    ) * (ia_reac_temp - 30.0)

    air_feed_heat = comp["tot_air_to_react"] * 0.23 * (ia_reac_temp - comp["air_temp_comp"])

    heat_no_cond = heat_react - air_feed_heat - liq_feed_heat - heat_evap

    return {
        "n2_in_offgas_mol": n2_offgas_mol,
        "o2_in_offgas_mol": o2_offgas_mol,
        "co2_in_offgas_mol": co2_offgas_mol,
        "incondens_offgas_mol": incondens_offgas_mol,
        "wat_in_reac_liq_mol": wat_liq_mol,
        "hac_in_reac_liq_mol": hac_liq_mol,
        "ia_in_reac_liq_mol": ia_liq_mol,
        "ia_in_react_liq_tot_mol": total_liq_mol,
        "ia_in_react_liq_x_hac": x_hac,
        "ia_in_react_liq_x_wat": x_wat,
        "ia_in_react_y_hac": y_hac,
        "ia_in_react_y_wat": y_wat,
        "ia_in_react_vap_tot_mol": vap_total_mol,
        "ia_react_vap_wat_kg_h": vap_wat_kg_h,
        "ia_react_vap_hac_kg_h": vap_hac_kg_h,
        "ia_in_react_reaction_heat": heat_react,
        "ia_in_react_evap_heat": heat_evap,
        "ia_in_liq_heat": liq_feed_heat,
        "ia_in_react_air_feed": air_feed_heat,
        "ia_reac_temp": ia_reac_temp,
        "ia_reac_heat_no_cond": heat_no_cond,
    }


def condenser_1(
    react: Dict[str, float],
    comp: Dict[str, float],
    hp_steam: float = 6.5,
) -> Dict[str, float]:
    exit_temp = math.sqrt(math.sqrt(hp_steam + 1.0)) * 100.0 + 10.0

    wat_press = math.exp(18.36 - (3840.96 / (exit_temp + 228.3))) / 760.0
    hac_press = math.exp(19.32 - (5495.31 / (exit_temp + 314.75))) / 760.0

    x_wat = 0.5
    vap_wat_mol = vap_hac_mol = vap_wat_kg_h = vap_hac_kg_h = 0.0
    cond_wat_kg_h = cond_hac_kg_h = condensate_heat = 0.0

    for _ in range(30):
        x_hac = 1.0 - x_wat
        y_hac = hac_press * x_hac / comp["comp_pressure_bara"]
        y_wat = wat_press * x_wat / comp["comp_pressure_bara"]
        y_incon = max(1.0 - y_hac - y_wat, 1e-6)

        vap_tot_mol = react["incondens_offgas_mol"] / y_incon
        vap_wat_mol = vap_tot_mol * y_wat
        vap_hac_mol = vap_tot_mol * y_hac

        vap_wat_kg_h = vap_wat_mol * 18.0
        vap_hac_kg_h = vap_hac_mol * 60.0

        cond_wat_kg_h = max(react["ia_react_vap_wat_kg_h"] - vap_wat_kg_h, 0.0)
        cond_hac_kg_h = max(react["ia_react_vap_hac_kg_h"] - vap_hac_kg_h, 0.0)

        denom = cond_wat_kg_h / 18.0 + cond_hac_kg_h / 60.0
        if denom > 0.0:
            x_wat = (cond_wat_kg_h / 18.0) / denom

        condensate_heat = (cond_wat_kg_h * 1.0 + cond_hac_kg_h * 0.5) * (
            react["ia_reac_temp"] - exit_temp
        )

    return {
        "condenser_1_exit_temp": exit_temp,
        "wat_pv_cond_1_exit": wat_press,
        "hac_pv_cond_1_exit": hac_press,
        "condenser_1_vap_wat_mol": vap_wat_mol,
        "condenser_1_vap_wat_kg_h": vap_wat_kg_h,
        "condenser_1_vap_hac_mol": vap_hac_mol,
        "condenser_1_vap_hac_kg_h": vap_hac_kg_h,
        "condenser_1_cond_wat_kg_h": cond_wat_kg_h,
        "condenser_1_cond_hac_kg_h": cond_hac_kg_h,
        "condenser_1_condensate_heat": condensate_heat,
    }


def condenser_2(
    react: Dict[str, float],
    cond_1: Dict[str, float],
    comp: Dict[str, float],
    lp_steam: float = 2.5,
) -> Dict[str, float]:
    exit_temp = math.sqrt(math.sqrt(lp_steam + 1.0)) * 100.0 + 10.0

    wat_press = math.exp(18.36 - (3840.96 / (exit_temp + 228.3))) / 760.0
    hac_press = math.exp(19.32 - (5495.31 / (exit_temp + 314.75))) / 760.0

    x_wat = 0.5
    y_hac = y_wat = vap_tot_mol = 0.0
    vap_wat_mol = vap_hac_mol = vap_wat_kg_h = vap_hac_kg_h = 0.0
    cond_wat_kg_h = cond_hac_kg_h = condensate_heat = 0.0

    for _ in range(30):
        x_hac = 1.0 - x_wat
        y_hac = hac_press * x_hac / comp["comp_pressure_bara"]
        y_wat = wat_press * x_wat / comp["comp_pressure_bara"]
        y_incon = max(1.0 - y_hac - y_wat, 1e-6)

        vap_tot_mol = react["incondens_offgas_mol"] / y_incon
        vap_wat_mol = vap_tot_mol * y_wat
        vap_hac_mol = vap_tot_mol * y_hac

        vap_wat_kg_h = vap_wat_mol * 18.0
        vap_hac_kg_h = vap_hac_mol * 60.0

        cond_wat_kg_h = max(cond_1["condenser_1_vap_wat_kg_h"] - vap_wat_kg_h, 0.0)
        cond_hac_kg_h = max(cond_1["condenser_1_vap_hac_kg_h"] - vap_hac_kg_h, 0.0)

        denom = cond_wat_kg_h / 18.0 + cond_hac_kg_h / 60.0
        if denom > 0.0:
            x_wat = (cond_wat_kg_h / 18.0) / denom

        condensate_heat = (cond_wat_kg_h * 1.0 + cond_hac_kg_h * 0.5) * (
            react["ia_reac_temp"] - exit_temp
        )

    return {
        "condenser_2_exit_temp": exit_temp,
        "wat_pv_cond_2_exit": wat_press,
        "hac_pv_cond_2_exit": hac_press,
        "condenser_2_y_hac": y_hac,
        "condenser_2_y_wat": y_wat,
        "condenser_2_vap_tot_mol": vap_tot_mol,
        "condenser_2_vap_wat_mol": vap_wat_mol,
        "condenser_2_vap_wat_kg_h": vap_wat_kg_h,
        "condenser_2_vap_hac_mol": vap_hac_mol,
        "condenser_2_vap_hac_kg_h": vap_hac_kg_h,
        "condenser_2_cond_wat_kg_h": cond_wat_kg_h,
        "condenser_2_cond_hac_kg_h": cond_hac_kg_h,
        "condenser_2_condensate_heat": condensate_heat,
    }


def calculate_residual_heat(
    react: Dict[str, float],
    cond_1: Dict[str, float],
    cond_2: Dict[str, float],
) -> float:
    return (
        react["ia_reac_heat_no_cond"]
        - cond_1["condenser_1_condensate_heat"]
        - cond_2["condenser_2_condensate_heat"]
    )


def solve_reactor(
    mves: Dict[str, float],
    comp: Dict[str, float],
    hp_steam: float = 6.5,
    lp_steam: float = 2.5,
    start_temp: float = 206.0,
    tolerance: float = 1000.0,
    max_iter: int = 80,
) -> Dict[str, Any]:
    """
    Solve reactor temperature with a simple bracket/bisection method.
    This is more stable than changing temperature step-by-step in only one direction.
    """

    def evaluate(temp: float) -> Dict[str, Any]:
        react = ia_react(mves, comp, ia_reac_temp=temp)
        cond_1 = condenser_1(react, comp, hp_steam=hp_steam)
        cond_2 = condenser_2(react, cond_1, comp, lp_steam=lp_steam)
        residual_heat = calculate_residual_heat(react, cond_1, cond_2)
        return {
            "react": react,
            "cond_1": cond_1,
            "cond_2": cond_2,
            "residual_heat": residual_heat,
        }

    low_temp = 160.0
    high_temp = 240.0

    low_eval = evaluate(low_temp)
    high_eval = evaluate(high_temp)

    # If the residual is not bracketed, fall back to the start temperature.
    if low_eval["residual_heat"] * high_eval["residual_heat"] > 0:
        final = evaluate(start_temp)
        reactor_temp = start_temp
    else:
        reactor_temp = start_temp
        final = evaluate(reactor_temp)

        for _ in range(max_iter):
            reactor_temp = (low_temp + high_temp) / 2.0
            final = evaluate(reactor_temp)

            if abs(final["residual_heat"]) < tolerance:
                break

            if low_eval["residual_heat"] * final["residual_heat"] <= 0:
                high_temp = reactor_temp
                high_eval = final
            else:
                low_temp = reactor_temp
                low_eval = final

    react = final["react"]
    cond_2 = final["cond_2"]

    ia_react_out_wat = react["wat_in_reac_liq_mol"] * 18.0 - cond_2["condenser_2_vap_wat_kg_h"]
    ia_react_out_hac = react["hac_in_reac_liq_mol"] * 60.0 - cond_2["condenser_2_vap_hac_kg_h"]
    ia_react_out_ia = react["ia_in_reac_liq_mol"] * 166.0

    liq_dilution = ia_react_out_wat + 0.7 * ia_react_out_hac
    thickness_index = safe_div(ia_react_out_ia, liq_dilution, default=1.0)

    return {
        "react": react,
        "cond_1": final["cond_1"],
        "cond_2": final["cond_2"],
        "reactor_temp": reactor_temp,
        "residual_heat": final["residual_heat"],
        "ia_react_out_wat": ia_react_out_wat,
        "ia_react_out_hac": ia_react_out_hac,
        "ia_react_out_ia": ia_react_out_ia,
        "thickness_index": thickness_index,
    }


def run_model(
    mx_feed: float,
    reactor_pressure_barg: float,
    hp_steam: float,
    lp_steam: float,
) -> Dict[str, Any]:
    mves = mixing_vessel(mx_flow_kg_h=mx_feed)
    comp = comp_flow(mves, react_pressure_barg=reactor_pressure_barg)
    solved = solve_reactor(mves, comp, hp_steam=hp_steam, lp_steam=lp_steam)

    return {
        "mves": mves,
        "comp": comp,
        **solved,
    }


def operator_guidance(
    model: Dict[str, Any],
    opc_values: Dict[str, Any],
    opc_connected: bool,
) -> str:
    thickness = model["thickness_index"]
    reactor_temp = model["reactor_temp"]

    messages = []

    if opc_connected:
        messages.append("OPC UA connection: ON")
    else:
        messages.append("OPC UA connection: OFF - using manual slider values.")

    if thickness < 0.330:
        messages.append("Thickness index OK.")
    elif thickness < 0.345:
        messages.append("Thickness index WARNING. Check crystallizer feed dilution.")
    else:
        messages.append("Thickness index NOT OK. Check water/HAc balance and crystallizer feed dilution.")

    reactor_temp_dcs = opc_values.get("reactor_temp_dcs")
    if reactor_temp_dcs is not None:
        delta_t = reactor_temp_dcs - reactor_temp
        messages.append(f"DCS reactor T: {reactor_temp_dcs:.2f} °C")
        messages.append(f"DCS - model ΔT: {delta_t:.2f} °C")

        if abs(delta_t) > 5.0:
            messages.append("Large temperature mismatch. Check thermocouple, pressure, steam data, or model assumptions.")

    thickness_dcs = opc_values.get("thickness_index_dcs")
    if thickness_dcs is not None:
        delta_idx = thickness_dcs - thickness
        messages.append(f"DCS thickness index: {thickness_dcs:.3f}")
        messages.append(f"DCS - model Δindex: {delta_idx:.3f}")

        if abs(delta_idx) > 0.015:
            messages.append("Large thickness-index mismatch. Check DCS analyzer, lab data, or model calibration.")

    return "\n".join(messages)


# =========================================================
# OPC UA CLIENT
# =========================================================

async def find_child_by_browse_name(parent, browse_name: str):
    children = await parent.get_children()

    for child in children:
        node_browse_name = await child.read_browse_name()
        if node_browse_name.Name == browse_name:
            return child

    raise RuntimeError(f"Child not found: {browse_name}")


class OpcReader:
    def __init__(self, url: str, tag_paths: Dict[str, list], scan_sec: float = 2.0):
        self.url = url
        self.tag_paths = tag_paths
        self.scan_sec = scan_sec
        self.queue: queue.Queue = queue.Queue()
        self.connected = False
        self.last_values: Dict[str, Any] = {}

    async def reader_loop(self):
        while True:
            try:
                print("Trying OPC UA connection:", self.url)

                async with Client(url=self.url) as client:
                    print("OPC UA connected")
                    self.connected = True

                    objects = client.nodes.objects
                    plant = await find_child_by_browse_name(objects, "IsophthalicPlant")

                    tag_nodes = {}

                    for tag_name, path in self.tag_paths.items():
                        node = plant
                        for part in path:
                            node = await find_child_by_browse_name(node, part)
                        tag_nodes[tag_name] = node

                    while True:
                        values = {}
                        for tag_name, node in tag_nodes.items():
                            values[tag_name] = await node.read_value()

                        self.queue.put(values)
                        await asyncio.sleep(self.scan_sec)

            except Exception as exc:
                self.connected = False
                print("OPC UA connection error:", exc)
                await asyncio.sleep(2.0)

    def start(self):
        thread = threading.Thread(
            target=lambda: asyncio.run(self.reader_loop()),
            daemon=True,
        )
        thread.start()

    def get_pending_values(self) -> Optional[Dict[str, Any]]:
        latest = None

        try:
            while True:
                latest = self.queue.get_nowait()
        except queue.Empty:
            pass

        if latest:
            self.last_values.update(latest)

        return latest


# =========================================================
# TKINTER APPLICATION
# =========================================================

class IsophthalicApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Glass Plant - Isophthalic Acid Reactor Assembly")
        self.root.geometry("1400x820")

        self.opc_reader = OpcReader(OPC_SERVER_URL, OPC_TAG_NAMES, OPC_SCAN_SEC)

        self.initializing = True
        self.result_text = tk.StringVar()

        self._load_fonts()
        self._load_image()
        self._build_ui()

        self.initializing = False

        self.opc_reader.start()
        self.poll_opc_queue()
        self.update_model()

    def _load_fonts(self):
        try:
            self.font_big = ImageFont.truetype(
                "/System/Library/Fonts/Supplemental/Arial.ttf", 22
            )
            self.font_med = ImageFont.truetype(
                "/System/Library/Fonts/Supplemental/Arial.ttf", 17
            )
            self.font_small = ImageFont.truetype(
                "/System/Library/Fonts/Supplemental/Arial.ttf", 15
            )
        except Exception:
            self.font_big = ImageFont.load_default()
            self.font_med = ImageFont.load_default()
            self.font_small = ImageFont.load_default()

    def _load_image(self):
        print("IMG_PATH used:", IMG_PATH)
        print("File exists?", os.path.exists(IMG_PATH))

        if os.path.exists(IMG_PATH):
            original = Image.open(IMG_PATH)
        else:
            print("WARNING: Isophthalic.drawio.png not found. Using blank image.")
            original = Image.new("RGB", (1200, 850), "white")

        target_w = 980
        scale = target_w / original.width
        target_h = int(original.height * scale)
        self.base_img = original.resize((target_w, target_h), Image.LANCZOS)

    def _build_ui(self):
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill="both", expand=True)

        controls = tk.Frame(main_frame, bg="#222", width=340)
        controls.pack(side="left", fill="y", padx=10, pady=10)
        controls.pack_propagate(False)

        img_frame = tk.Frame(main_frame, bg="white")
        img_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        self.img_label = tk.Label(img_frame, bg="white")
        self.img_label.pack(expand=True)

        tk.Label(
            controls,
            text="Glass Plant Controls",
            bg="#222",
            fg="white",
            font=("Arial", 16, "bold"),
        ).pack(padx=12, pady=(18, 20), anchor="w")

        self.mx_slider = self._make_slider(
            controls, "Meta-xylene flow (kg/h)", 3000, 8000, 50, 5300
        )
        self.pressure_slider = self._make_slider(
            controls, "Reactor pressure (barg)", 10.0, 20.0, 0.1, 15.0
        )
        self.hp_steam_slider = self._make_slider(
            controls, "High pressure steam (barg)", 4.0, 8.0, 0.1, 6.5
        )
        self.lp_steam_slider = self._make_slider(
            controls, "Low pressure steam (barg)", 1.0, 4.0, 0.1, 2.5
        )

        tk.Label(
            controls,
            text="OPC UA connection",
            bg="#222",
            fg="cyan",
            font=("Arial", 12, "bold"),
        ).pack(padx=12, pady=(14, 6), anchor="w")

        tk.Label(
            controls,
            text="Reading from OPC UA server\nPort: 4842",
            bg="#222",
            fg="white",
            font=("Arial", 11),
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=12, pady=0)

        tk.Label(
            controls,
            textvariable=self.result_text,
            justify="left",
            anchor="nw",
            bg="#222",
            fg="white",
            font=("Arial", 12),
        ).pack(fill="x", padx=12, pady=20)

        tk.Label(
            controls,
            text="Indications for operators",
            bg="#222",
            fg="yellow",
            font=("Arial", 11, "bold"),
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=(0,4), pady=(0,0))

        self.operators_text = tk.Label(
            controls,
            text="---",
            bg="#222",
            fg="yellow",
            font=("Arial", 11),
            justify="left",
            anchor="nw",

            height=10,

            wraplength=280,
        )
        self.operators_text.pack(fill="both", padx=12, pady=(0, 10))

    def _make_slider(self, parent, title, from_, to, resolution, initial):
        tk.Label(
            parent,
            text=title,
            bg="#222",
            fg="white",
            font=("Arial", 12, "bold"),
        ).pack(padx=12, pady=(12, 6), anchor="w")

        slider = tk.Scale(
            parent,
            from_=from_,
            to=to,
            resolution=resolution,
            orient="horizontal",
            length=280,
            command=self.update_model,
            bg="#222",
            fg="white",
            troughcolor="#666",
            highlightthickness=0,
        )
        slider.pack(padx=12, pady=6)
        slider.set(initial)
        return slider

    def set_slider_without_callback(self, slider: tk.Scale, value: float):
        slider.config(command="")
        slider.set(value)
        slider.config(command=self.update_model)

    def poll_opc_queue(self):
        values = self.opc_reader.get_pending_values()

        if values:
            if "mx_feed" in values:
                self.set_slider_without_callback(self.mx_slider, values["mx_feed"])
            if "reactor_pressure_barg" in values:
                self.set_slider_without_callback(self.pressure_slider, values["reactor_pressure_barg"])
            if "hp_steam" in values:
                self.set_slider_without_callback(self.hp_steam_slider, values["hp_steam"])
            if "lp_steam" in values:
                self.set_slider_without_callback(self.lp_steam_slider, values["lp_steam"])

            self.update_model()

        self.root.after(500, self.poll_opc_queue)

    def update_model(self, val=None):
        if self.initializing:
            return

        mx_value = float(self.mx_slider.get())
        react_pressure_barg = float(self.pressure_slider.get())
        hp_steam = float(self.hp_steam_slider.get())
        lp_steam = float(self.lp_steam_slider.get())

        model = run_model(mx_value, react_pressure_barg, hp_steam, lp_steam)

        mves = model["mves"]
        comp = model["comp"]
        react = model["react"]
        cond_1 = model["cond_1"]
        cond_2 = model["cond_2"]

        reactor_temp = model["reactor_temp"]
        residual_heat = model["residual_heat"]
        thickness_index = model["thickness_index"]

        reactor_temp_dcs = self.opc_reader.last_values.get("reactor_temp_dcs")
        thickness_index_dcs = self.opc_reader.last_values.get("thickness_index_dcs")

        dcs_reactor_text = "Not available"
        reactor_temp_delta_text = "Not available"
        if reactor_temp_dcs is not None:
            dcs_reactor_text = f"{reactor_temp_dcs:.2f} °C"
            reactor_temp_delta_text = f"{reactor_temp_dcs - reactor_temp:.2f} °C"

        dcs_thickness_text = "Not available"
        thickness_delta_text = "Not available"
        if thickness_index_dcs is not None:
            dcs_thickness_text = f"{thickness_index_dcs:.3f}"
            thickness_delta_text = f"{thickness_index_dcs - thickness_index:.3f}"

        self.result_text.set(
            f"MX feed: {mx_value:.0f} kg/h\n"
            f"OPC connection: {'ON' if self.opc_reader.connected else 'OFF'}\n\n"
            f"Total feed: {mves['total_feed']:.1f} kg/h\n"
            f"HAc feed: {mves['hac_flow_to_rx_kg_h']:.1f} kg/h\n"
            f"Water feed: {mves['water_flow_to_rx_kg_h']:.1f} kg/h\n\n"
            f"Reactor pressure: {react_pressure_barg:.1f} barg\n"
            f"HP steam pressure: {hp_steam:.1f} barg\n"
            f"LP steam pressure: {lp_steam:.1f} barg\n\n"
            f"Cond-1 exit T: {cond_1['condenser_1_exit_temp']:.1f} °C\n"
            f"Cond-2 exit T: {cond_2['condenser_2_exit_temp']:.1f} °C\n\n"
            f"Air to reactor: {comp['tot_air_to_react']:.1f} kg/h\n"
            f"Air temp after comp: {comp['air_temp_comp']:.1f} °C\n\n"
            f"Model reactor temp: {reactor_temp:.2f} °C\n"
            f"DCS reactor temp: {dcs_reactor_text}\n"
            f"DCS - model ΔT: {reactor_temp_delta_text}\n\n"
            f"Residual heat: {residual_heat:,.1f} kcal/h\n\n"
            f"Cond-1 HAc cond: {cond_1['condenser_1_cond_hac_kg_h']:.1f} kg/h\n"
            f"Cond-2 HAc cond: {cond_2['condenser_2_cond_hac_kg_h']:.1f} kg/h\n"
            f"To scrubber HAc: {cond_2['condenser_2_vap_hac_kg_h']:.1f} kg/h\n"
            f"To scrubber H2O: {cond_2['condenser_2_vap_wat_kg_h']:.1f} kg/h\n\n"
            f"Model thickness index: {thickness_index:.3f}\n"
            f"DCS thickness index: {dcs_thickness_text}\n"
            f"DCS - model Δidx: {thickness_delta_text}"
        )

        self.operators_text.config(
            text=operator_guidance(model, self.opc_reader.last_values, self.opc_reader.connected)
        )

        overlay = self.make_overlay_image(model, react_pressure_barg, hp_steam, lp_steam)
        photo = ImageTk.PhotoImage(overlay)
        self.img_label.config(image=photo)
        self.img_label.image = photo

    def make_overlay_image(
        self,
        model: Dict[str, Any],
        react_pressure_barg: float,
        hp_steam: float,
        lp_steam: float,
    ):
        img = self.base_img.copy()
        draw = ImageDraw.Draw(img)

        mves = model["mves"]
        comp = model["comp"]
        react = model["react"]
        cond_1 = model["cond_1"]
        cond_2 = model["cond_2"]

        reactor_temp = model["reactor_temp"]
        ia_react_out_wat = model["ia_react_out_wat"]
        ia_react_out_hac = model["ia_react_out_hac"]
        ia_react_out_ia = model["ia_react_out_ia"]
        thickness_index = model["thickness_index"]

        # Feed box
        draw.rounded_rectangle((10, 100, 260, 230), radius=18, fill=(220, 245, 255), outline="black", width=2)
        draw.text((20, 100), "Feed", fill="black", font=self.font_big)
        draw.text((20, 130), f"MX feed: {mves['mx_flow_to_rx_kg_h']:.0f} kg/h", fill="black", font=self.font_med)
        draw.text((20, 160), f"HAc feed: {mves['hac_flow_to_rx_kg_h']:.0f} kg/h", fill="black", font=self.font_med)
        draw.text((20, 190), f"Water:   {mves['water_flow_to_rx_kg_h']:.0f} kg/h", fill="black", font=self.font_med)

        # Compressor box
        draw.rounded_rectangle((20, 650, 340, 730), radius=18, fill=(255, 250, 210), outline="black", width=2)
        draw.text((30, 650), "Compressor", fill="black", font=self.font_big)
        draw.text((30, 680), f"N2: {comp['tot_air_to_react'] * 0.77:.0f} kg/h", fill="black", font=self.font_med)
        draw.text((200, 680), f"O2: {comp['tot_air_to_react'] * 0.23:.0f} kg/h", fill="black", font=self.font_med)
        draw.text((30, 710), f"P react: {react_pressure_barg:.1f} barg", fill="black", font=self.font_med)

        # Vapour from reactor
        draw.rounded_rectangle((285, 160, 480, 340), radius=18, fill=(255, 250, 210), outline="black", width=2)
        draw.text((290, 170), "Vap from Reactor", fill="black", font=self.font_big)
        draw.text((290, 210), f"T reactor: {reactor_temp:.1f} °C", fill="black", font=self.font_med)
        draw.text((290, 250), f"Vap H2O: {react['ia_react_vap_wat_kg_h']:.0f} kg/h", fill="black", font=self.font_med)
        draw.text((290, 290), f"Vap HAc: {react['ia_react_vap_hac_kg_h']:.0f} kg/h", fill="black", font=self.font_med)

        # Condenser 1
        draw.rounded_rectangle((530, 200, 730, 360), radius=18, fill=(220, 245, 255), outline="black", width=2)
        draw.text((535, 210), "Condenser 1", fill="black", font=self.font_big)
        draw.text((535, 240), f"HP steam: {hp_steam:.1f} barg", fill="black", font=self.font_med)
        draw.text((535, 270), f"Exit T:   {cond_1['condenser_1_exit_temp']:.1f} °C", fill="black", font=self.font_med)
        draw.text((535, 300), f"Cond H2O: {cond_1['condenser_1_cond_wat_kg_h']:.0f} kg/h", fill="black", font=self.font_med)
        draw.text((535, 330), f"Cond HAc: {cond_1['condenser_1_cond_hac_kg_h']:.0f} kg/h", fill="black", font=self.font_med)

        # Condenser 2
        draw.rounded_rectangle((750, 200, 955, 360), radius=18, fill=(230, 255, 230), outline="black", width=2)
        draw.text((755, 210), "Condenser 2", fill="black", font=self.font_big)
        draw.text((755, 240), f"LP steam: {lp_steam:.1f} barg", fill="black", font=self.font_med)
        draw.text((755, 270), f"Exit T:   {cond_2['condenser_2_exit_temp']:.1f} °C", fill="black", font=self.font_med)
        draw.text((755, 300), f"Cond H2O: {cond_2['condenser_2_cond_wat_kg_h']:.0f} kg/h", fill="black", font=self.font_med)
        draw.text((755, 330), f"Cond HAc: {cond_2['condenser_2_cond_hac_kg_h']:.0f} kg/h", fill="black", font=self.font_med)

        # To scrubber
        draw.rounded_rectangle((825, 0, 990, 90), radius=18, fill=(255, 235, 235), outline="black", width=2)
        draw.text((835, 5), "To scrubber", fill="black", font=self.font_med)
        draw.text((830, 35), f"Vap HAc: {cond_2['condenser_2_vap_hac_kg_h']:.0f}", fill="black", font=self.font_med)
        draw.text((830, 65), f"Vap wat: {cond_2['condenser_2_vap_wat_kg_h']:.0f}", fill="black", font=self.font_med)

        # To crystallizer
        draw.rounded_rectangle((675, 500, 950, 700), radius=18, fill=(255, 235, 235), outline="black", width=2)
        draw.text((680, 510), "To crystallizer", fill="black", font=self.font_med)
        draw.text((680, 550), f"Water: {ia_react_out_wat:.0f} kg/h", fill="black", font=self.font_med)
        draw.text((680, 590), f"HAc: {ia_react_out_hac:.0f} kg/h", fill="black", font=self.font_med)
        draw.text((680, 630), f"Isopht Acid: {ia_react_out_ia:.0f} kg/h", fill="black", font=self.font_med)

        # Thickness index status
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

        draw.rectangle((445, 445, 550, 580), fill=box_color, outline=border_color, width=4)
        draw.text((445, 590), f"Thick idx: {thickness_index:.3f}", fill="black", font=self.font_small)
        draw.text((445, 620), f"Status: {status_text}", fill=status_fill, font=self.font_small)

        return img


def main():
    root = tk.Tk()
    IsophthalicApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
