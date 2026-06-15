import os
import math
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk, ImageDraw, ImageFont
import asyncio
import threading
import queue
from asyncua import Client
# =======================================================
#  IMAGE PATH (relative)
# =======================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_PATH = os.path.join(BASE_DIR, "formalin_pdf.png")
print("IMG_PATH:", IMG_PATH)

# =======================================================
#  OPC UA CONFIGURATION
# =======================================================
OPC_SERVER_URL = "opc.tcp://127.0.0.1:4841/formalin/server/"

opc_queue = queue.Queue()

opc_connected = False
opc_last_values = {}
# =======================================================
#  VAPORIZER MODEL
# =======================================================
def run_vaporizer_model(airflow_kg_h=2115 * 1.29,
                        mewara=2.1,
                        temp_C=70.7,
                        vapvol_L=25000,
                        n_iter=50):

    temp = float(temp_C)
    vapvol = float(vapvol_L)

    pvmeoh = 10 ** (8.0897 - (1582.27 / (temp + 239.7))) / 760.0
    pvwat  = math.exp(16.2886 - (3816.44 / (temp + 273.0 - 46.13))) / 100.0

    airflow = float(airflow_kg_h)

    meohflow = airflow / 1.5
    watflow  = meohflow / float(mewara)

    vapliqwat  = vapvol * 0.5
    vapliqmeoh = vapvol * 0.5

    xwat  = vapliqwat/18.0 / (vapliqwat/18.0 + vapliqmeoh/32.0)
    xmeoh = 1.0 - xwat

    proc_wat = 0.0
    proc_meoh = 0.0

    for _ in range(int(n_iter)):
        ywat  = pvwat  * xwat
        ymeoh = pvmeoh * xmeoh

        incond = airflow*0.23/32.0 + airflow*0.77/28.0
        process_gas_mol = incond / (1.0 - ywat - ymeoh)

        proc_wat  = process_gas_mol * ywat  * 18.0
        proc_meoh = process_gas_mol * ymeoh * 32.04

        vapliqwat  = vapliqwat  - proc_wat  + watflow
        vapliqmeoh = vapliqmeoh - proc_meoh + meohflow

        xwat  = vapliqwat/18.0 / (vapliqwat/18.0 + vapliqmeoh/32.0)
        xmeoh = 1.0 - xwat

        # keep inventory near vapvol
        total = vapliqwat + vapliqmeoh
        if total > vapvol:
            corr = total / vapvol
            meohflow = proc_meoh / corr
            watflow  = meohflow / float(mewara)

    liqconcmeoh = vapliqmeoh / (vapliqwat + vapliqmeoh)
    liqconcwat  = 1.0 - liqconcmeoh

    return {
        "air_in_kg_h": airflow,
        "meoh_in_kg_h": meohflow,
        "water_in_kg_h": watflow,
        "meoh_proc_gas": proc_meoh,
        "wat_proc_gas":  proc_wat,
        "liqconcmeoh": liqconcmeoh,
        "liqconcwat": liqconcwat,
        "temperature_C": temp,
        "pv_meoh_atm": pvmeoh,
        "pv_water_atm": pvwat,
    }

# =======================================================
#  REACTOR MODEL (your structure)
# =======================================================
def run_reactor(res,
                sele_fa=0.84,
                sele_co2=0.155,
                steam_pressure_barg=4.5,
                CO_kg_h_fixed=11.0):

    sele_co = 1.0 - sele_fa - sele_co2

    meoh_flow = float(res["meoh_proc_gas"])
    air       = float(res["air_in_kg_h"])
    wat_feed  = float(res["water_in_kg_h"])

    n2_kg = air * 0.77

    # CO2 branch
    o2_co2 = (sele_co2/1.5 * air * 0.23 / 32.0)
    meoh_co2_kg  = o2_co2 * 1.5 * 32.04
    meoh_co2_mol = meoh_co2_kg / 32.04
    h2o_co2_kg   = meoh_co2_mol * 2 * 18.0
    co2_kg       = o2_co2 * 1.5 * 44.0
    co2_eso_heat = meoh_co2_mol * (-751/4.184) * 1000.0

    # CO branch (heat only)
    o2_co = (sele_co * air * 0.23) / 32.0
    meoh_co_kg  = o2_co * 32.04
    meoh_co_mol = meoh_co_kg / 32.04
    h2o_co_kg   = meoh_co_mol * 2 * 18.0
    co_eso_heat = meoh_co_mol * (-751/4.184) * 1000.0

    # FA exo
    o2_fa = air*0.23/32.0 - o2_co2 - o2_co
    meoh_fa_eso_mol = o2_fa * 2.0
    meoh_fa_eso_kg  = meoh_fa_eso_mol * 32.04
    h2o_fa_eso_kg   = meoh_fa_eso_mol * 18.0
    fa_eso_kg       = meoh_fa_eso_mol * 30.0
    fa_eso_heat     = meoh_fa_eso_mol * (-159/4.184) * 1000.0

    # FA endo
    meoh_fa_endo_kg = meoh_flow - meoh_fa_eso_kg - meoh_co2_kg - meoh_co_kg
    if meoh_fa_endo_kg < 0:
        meoh_fa_endo_kg = 0.0
    fa_endo_mol  = meoh_fa_endo_kg / 32.04
    fa_endo_kg   = fa_endo_mol * 30.0
    h2_prod_kg   = fa_endo_mol * 2.0
    fa_endo_heat = fa_endo_mol * (131.796/4.184) * 1000.0

    meoh_reacted = meoh_co2_kg + meoh_co_kg + meoh_fa_eso_kg + meoh_fa_endo_kg
    meoh_unreacted = max(meoh_flow - meoh_reacted, 0.0)

    fa_prod_kg = fa_eso_kg + fa_endo_kg
    h2o_reac_kg = h2o_co2_kg + h2o_co_kg + h2o_fa_eso_kg
    h2o_total_kg = wat_feed + h2o_reac_kg

    overall_heat = co2_eso_heat + co_eso_heat + fa_eso_heat + fa_endo_heat

    temp_in = float(res["temperature_C"])
    denom = (fa_prod_kg*1.5 +
             h2_prod_kg*2.0 +
             co2_kg*1.0 +
             CO_kg_h_fixed*1.05 +
             h2o_total_kg*2.0 +
             n2_kg*1.0)

    reactor_t = temp_in - (overall_heat*4.184/denom)
    steam_kg_h = -overall_heat / (-2.295*(steam_pressure_barg+1.0) + 586.44)

    return {
        "fa_prod_kg_h": fa_prod_kg,
        "h2o_total_kg_h": h2o_total_kg,
        "co2_prod_kg_h": co2_kg,
        "co_prod_kg_h": CO_kg_h_fixed,
        "h2_prod_kg_h": h2_prod_kg,
        "n2_kg_h": n2_kg,
        "meoh_unreacted_kg_h": meoh_unreacted,
        "reactor_T_C": reactor_t,
        "steam_kg_h": steam_kg_h
    }

# =======================================================
#  OFFGAS at absorber head (FIXED)
# =======================================================
def estimate_meoh_offgas_from_T5(T5_C: float, re: dict):
    """
    Returns dict with MeOH and H2O leaving absorber head (kg/h),
    assuming equilibrium with stage-5 liquid (MeOH 4 wt%).
    """

    pvmeoh = 10 ** (8.0897 - (1582.27 / (T5_C + 239.7))) / 760.0
    pvwat  = math.exp(16.2886 - (3816.44 / (T5_C + 273.0 - 46.13))) / 100.0

    meoh_lmass = 0.04
    wat_lmass  = 1.0 - meoh_lmass

    xmeoh = (meoh_lmass/32.04) / ((meoh_lmass/32.04) + (wat_lmass/18.0))
    xwat  = 1.0 - xmeoh

    ymeoh = pvmeoh * xmeoh
    ywat  = pvwat  * xwat

    denom = 1.0 - ymeoh - ywat
    if denom <= 0:
        denom = 1e-6

    # inert mol/h from reactor products
    incon_mol = (re["co2_prod_kg_h"]/44.0 +
                 re["co_prod_kg_h"]/28.0 +
                 re["h2_prod_kg_h"]/2.0 +
                 re["n2_kg_h"]/28.0)

    tot_mol = incon_mol / denom

    meoh_kg_h = tot_mol * ymeoh * 32.04
    h2o_kg_h  = tot_mol * ywat  * 18.0

    return {"meoh_top_kg": meoh_kg_h, "wat_top_kg": h2o_kg_h}

# =======================================================
#  Recommendations (uses offgas)
# =======================================================
def operator_recommendations(res, MF_current, MF_target,
                             formalin_flow_kg_h, hcho_wt_pct,
                             meoh_wt_pct_formalin, T_stage5_C):

    re = run_reactor(res)
    roff = estimate_meoh_offgas_from_T5(float(T_stage5_C), re)
    meoh_offgas = float(roff["meoh_top_kg"])

    recos = []
    head_yellow = (meoh_offgas > 0.1)

    if float(meoh_wt_pct_formalin) > 1.0:
        recos.append("MeOH in formalin > 1% -> increase 2nd circulation temperature by +1 C")

    if head_yellow:
        recos.append(f"MeOH head > 0.1 kg/h (est {meoh_offgas:.2f}) -> reduce absorber top T / increase cooling")

    if float(MF_current) > float(MF_target):
        recos.append("M/F current > target -> reduce reactor temperature by 1 C")

    if not recos:
        recos.append("OK: no action required")

    return {
        "MeOH_offgas_kg_h": meoh_offgas,
        "head_yellow": head_yellow,
        "recommendations": recos
    }
# # =======================================================
#  OPC UA CLIENT - BACKGROUND READER
# =======================================================
async def opc_reader_loop():
    """
    Reads values from the Formalin OPC UA server and sends them
    to Tkinter through a queue.
    """

    global opc_connected

    while True:
        try:
            async with Client(url=OPC_SERVER_URL) as client:
                print("Connected to Formalin OPC UA server")
                opc_connected = True

                objects = client.nodes.objects

                # Main plant object
                plant = await objects.get_child(["2:FormalinPlant"])

                # Sections
                feed = await plant.get_child(["2:Feed"])
                vaporizer = await plant.get_child(["2:Vaporizer"])
                absorber = await plant.get_child(["2:Absorber"])

                # Tags matching the current formalin_opc_server.py
                air_flow_node = await feed.get_child(["2:Air_Flow_kg_h"])
                vap_temp_node = await vaporizer.get_child(["2:Vaporizer_Temperature_C"])

                abs_stage5_node = await absorber.get_child(["2:Absorber_Stage5_Temperature_C"])
                hcho_node = await absorber.get_child(["2:HCHO_wt_pct"])
                meoh_product_node = await absorber.get_child(["2:Methanol_in_Formalin_wt_pct"])

                while True:
                    air_kg_h = await air_flow_node.read_value()
                    vap_temp_c = await vap_temp_node.read_value()
                    abs_stage5_c = await abs_stage5_node.read_value()
                    hcho_wt_pct = await hcho_node.read_value()
                    meoh_wt_pct = await meoh_product_node.read_value()

                    values = {
                        "air_kg_h": air_kg_h,
                        "vap_temp_c": vap_temp_c,
                        "abs_stage5_c": abs_stage5_c,
                        "hcho_wt_pct": hcho_wt_pct,
                        "meoh_wt_pct": meoh_wt_pct,
                    }

                    opc_queue.put(values)

                    await asyncio.sleep(2)

        except Exception as ex:
            opc_connected = False
            print("OPC UA connection error:", ex)
            await asyncio.sleep(3)

# =======================================================
#  OPC UA CLIENT THREAD STARTER
# =======================================================
def start_opc_thread():
    """
    Starts the OPC UA client reader in a background thread.
    This prevents Tkinter from freezing.
    """
    thread = threading.Thread(
        target=lambda: asyncio.run(opc_reader_loop()),
        daemon=True
    )
    thread.start()            
# =======================================================
#  TKINTER UI
# =======================================================
root = tk.Tk()
root.title("Glass Plant – Formalin")
root.geometry("1200x760")

main = tk.Frame(root)
main.pack(fill="both", expand=True)

LEFT_WIDTH = 340
controls = tk.Frame(main, bg="#222", width=LEFT_WIDTH)
controls.pack(side="left", fill="y", padx=10, pady=10)
controls.pack_propagate(False)

img_frame = tk.Frame(main)
img_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

# image
orig_img = Image.open(IMG_PATH)
target_w = 850
scale = target_w / orig_img.width
target_h = int(orig_img.height * scale)
base_img = orig_img.resize((target_w, target_h), Image.LANCZOS)

img_label = tk.Label(img_frame)
img_label.pack(expand=True)

BIGFONT = ("Arial", 14, "bold")
MIDFONT = ("Arial", 12, "bold")

# sliders
tk.Label(controls, text="Air Flow [kg/h]", bg="#222", fg="white", font=BIGFONT).pack(pady=(6, 2))
air_var = tk.DoubleVar(value=2115.0 * 1.29)
tk.Scale(controls, from_=1000, to=4000, orient="horizontal", variable=air_var, length=280).pack()

tk.Label(controls, text="Vaporizer T [C]", bg="#222", fg="white", font=BIGFONT).pack(pady=(10, 2))
temp_var = tk.DoubleVar(value=70.7)
tk.Scale(controls, from_=65, to=80, resolution=0.1, orient="horizontal", variable=temp_var, length=280).pack()

# operator inputs vars
op_MF_current = tk.DoubleVar(value=0.90)
op_MF_target  = tk.DoubleVar(value=0.92)
op_formalin_flow = tk.DoubleVar(value=10000.0)
op_hcho_pct      = tk.DoubleVar(value=37.0)
op_meoh_pct      = tk.DoubleVar(value=1.0)
op_T_stage5      = tk.DoubleVar(value=60.0)

ops_state = None

# KPI labels
kpi = tk.Frame(controls, bg="#222")
kpi.pack(pady=10, anchor="w")

lbl_kpi = tk.Label(kpi, bg="#222", fg="white", font=("Arial", 11), justify="left")
lbl_kpi.pack(anchor="w")

lbl_reco = tk.Label(controls, bg="#222", fg="yellow", justify="left", wraplength=LEFT_WIDTH-10)
lbl_reco.pack(pady=10, anchor="w")

lbl_opc = tk.Label(
    controls,
    bg="#222",
    fg="lightgreen",
    font=("Arial", 10, "bold"),
    justify="left",
    wraplength=LEFT_WIDTH-10
)
lbl_opc.pack(pady=5, anchor="w")
def open_inputs_popup():
    win = tk.Toplevel(root)
    win.title("Operator Inputs")
    win.geometry("460x320")
    win.grab_set()

    frm = tk.Frame(win, padx=10, pady=10)
    frm.pack(fill="both", expand=True)

    def row(r, txt, var):
        tk.Label(frm, text=txt).grid(row=r, column=0, sticky="w", pady=4)
        tk.Entry(frm, textvariable=var, width=14).grid(row=r, column=1, sticky="w", padx=10)

    row(0, "M/F current", op_MF_current)
    row(1, "M/F target", op_MF_target)
    row(2, "Formalin flow [kg/h]", op_formalin_flow)
    row(3, "HCHO in formalin [wt%]", op_hcho_pct)
    row(4, "MeOH in formalin [wt%]", op_meoh_pct)
    row(5, "T absorber stage 5 [C]", op_T_stage5)

    def ok():
        try:
            float(op_MF_current.get()); float(op_MF_target.get())
            float(op_formalin_flow.get()); float(op_hcho_pct.get())
            float(op_meoh_pct.get()); float(op_T_stage5.get())
            win.destroy()
        except Exception as ex:
            messagebox.showerror("Input error", str(ex))

    tk.Button(frm, text="OK", command=ok).grid(row=6, column=0, pady=12)
    tk.Button(frm, text="Cancel", command=win.destroy).grid(row=6, column=1, pady=12)

tk.Button(controls, text="Operator Inputs…", command=open_inputs_popup).pack(pady=(6, 4), fill="x")

def safe_text(s: str) -> str:
    return s.replace("₂","2").replace("°"," deg ")

def draw_box(draw, font, x, y, text, bg=(0,0,0,180)):
    t = safe_text(text)
    bbox = draw.textbbox((0,0), t, font=font)
    w = bbox[2]-bbox[0]; h = bbox[3]-bbox[1]
    m=5
    draw.rectangle((x, y, x+w+2*m, y+h+2*m), fill=bg)
    draw.text((x+m, y+m), t, font=font, fill="white")

def update_display():
    global ops_state

    res = run_vaporizer_model(airflow_kg_h=air_var.get(), temp_C=temp_var.get(), mewara=2.1)
    re = run_reactor(res)
    roff = estimate_meoh_offgas_from_T5(op_T_stage5.get(), re)

    meoh_liq_pct = res["liqconcmeoh"] * 100.0

    # KPI block
    kpi_text = (
        f"MeOH feed: {res['meoh_in_kg_h']:.0f} kg/h\n"
        f"H2O feed:  {res['water_in_kg_h']:.0f} kg/h\n"
        f"Air:       {res['air_in_kg_h']:.0f} kg/h\n"
        f"MeOH gas:  {res['meoh_proc_gas']:.0f} kg/h\n"
        f"H2O gas:   {res['wat_proc_gas']:.0f} kg/h\n"
        f"T vap:     {res['temperature_C']:.1f} C\n"
        f"MeOH liq:  {meoh_liq_pct:.2f} wt%\n"
        f"T rx:      {re['reactor_T_C']:.1f} C\n"
        f"Steam:     {re['steam_kg_h']:.0f} kg/h\n"
        f"MeOH head: {roff['meoh_top_kg']:.2f} kg/h\n"
        f"H2O head:  {roff['wat_top_kg']:.2f} kg/h\n"
    )
    lbl_kpi.config(text=kpi_text)

    if ops_state is None:
        lbl_reco.config(text="Press Update/Recommend to compute recommendations.")
    else:
        txt = f"MeOH head est: {ops_state['MeOH_offgas_kg_h']:.2f} kg/h\n"
        txt += "Recommendations:\n- " + "\n- ".join(ops_state["recommendations"])
        lbl_reco.config(text=txt)

    # overlay
    img = base_img.copy()
    draw = ImageDraw.Draw(img, "RGBA")
    try:
        font = ImageFont.truetype("Arial.ttf", 16)
    except:
        font = ImageFont.load_default()

    W,H = img.size

    # Positions (tune for your PFD if needed)
    draw_box(draw, font, int(W*0.05), int(H*0.40), f"H2O {res['water_in_kg_h']:.0f}")
    draw_box(draw, font, int(W*0.05), int(H*0.52), f"MeOH {res['meoh_in_kg_h']:.0f}")
    draw_box(draw, font, int(W*0.05), int(H*0.86), f"Air {res['air_in_kg_h']:.0f}")

    draw_box(draw, font, int(W*0.38), int(H*0.34), f"T {res['temperature_C']:.1f}")
    draw_box(draw, font, int(W*0.38), int(H*0.44), f"MeOH liq {meoh_liq_pct:.1f}%")

    draw_box(draw, font, int(W*0.45), int(H*0.12), f"MeOH gas {res['meoh_proc_gas']:.0f}")
    draw_box(draw, font, int(W*0.45), int(H*0.17), f"H2O gas {res['wat_proc_gas']:.0f}")

    draw_box(draw, font, int(W*0.60), int(H*0.28), f"T rx {re['reactor_T_C']:.1f}")
    draw_box(draw, font, int(W*0.66), int(H*0.06), f"Steam {re['steam_kg_h']:.0f}")

    draw_box(draw, font, int(W*0.86), int(H*0.12), f"MeOH head {roff['meoh_top_kg']:.2f}")
    draw_box(draw, font, int(W*0.86), int(H*0.17), f"H2O head {roff['wat_top_kg']:.2f}")

    if ops_state and ops_state.get("head_yellow", False):
        xh = int(W*0.92); yh = int(H*0.08); r=14
        draw.ellipse((xh-r, yh-r, xh+r, yh+r), fill=(255,215,0,200), outline=(0,0,0,220))

    tk_img = ImageTk.PhotoImage(img)
    img_label.config(image=tk_img)
    img_label.image = tk_img

def on_recommend():
    global ops_state
    res = run_vaporizer_model(airflow_kg_h=air_var.get(), temp_C=temp_var.get(), mewara=2.1)

    ops_state = operator_recommendations(
        res=res,
        MF_current=op_MF_current.get(),
        MF_target=op_MF_target.get(),
        formalin_flow_kg_h=op_formalin_flow.get(),
        hcho_wt_pct=op_hcho_pct.get(),
        meoh_wt_pct_formalin=op_meoh_pct.get(),
        T_stage5_C=op_T_stage5.get()
    )

    update_display()

#tk.Button(controls, text="Update / Recommend", command=on_recommend).pack(pady=(6, 10), fill="x")
btn_reco = tk.Button(controls, text="Aggiorna / Raccomanda", command=on_recommend)
btn_reco.pack(pady=(5, 10))
# live update when sliders move
air_var.trace_add("write", lambda *_: update_display())
temp_var.trace_add("write", lambda *_: update_display())
def poll_opc_queue():
    """
    Reads latest OPC values from the queue and updates Tkinter variables.
    This function runs inside Tkinter main thread using root.after().
    """

    global opc_last_values

    received = False

    while not opc_queue.empty():
        values = opc_queue.get_nowait()
        opc_last_values = values
        received = True

    if received:
        try:
            air_var.set(opc_last_values["air_kg_h"])
            temp_var.set(opc_last_values["vap_temp_c"])
            op_T_stage5.set(opc_last_values["abs_stage5_c"])
            op_hcho_pct.set(opc_last_values["hcho_wt_pct"])
            op_meoh_pct.set(opc_last_values["meoh_wt_pct"])

            lbl_opc.config(
                text=(
                    "OPC UA: connected\n"
                    f"Air: {opc_last_values['air_kg_h']:.0f} kg/h\n"
                    f"Vap T: {opc_last_values['vap_temp_c']:.1f} C\n"
                    f"Abs S5 T: {opc_last_values['abs_stage5_c']:.1f} C"
                ),
                fg="lightgreen"
            )

            update_display()

        except Exception as ex:
            lbl_opc.config(text=f"OPC update error: {ex}", fg="red")

    else:
        if not opc_connected:
            lbl_opc.config(text="OPC UA: not connected", fg="orange")

    root.after(1000, poll_opc_queue)

start_opc_thread()
poll_opc_queue()

update_display()
root.mainloop()