### Code for Isophtalic acid plant based on Lonza Singapore Technology da foglio excel originale

import math
from dataclasses import dataclass
import os
import math
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk, ImageDraw, ImageFont


@dataclass
class Inputs:
    # questi campi corrispondono alle celle Excel usate nel VBA
    ptot: float        # I29  - pressione totale [atm] (come nel VBA, coerente con Antoine/760)
    Tin: float         # I30  - temperatura iniziale reattore [°C]
    step_T: float      # K15  - "passo" di temperatura usato per correzione [°C]
    ninc: float        # K28  - moli di incondensabili (gas) nel sistema [mol/h]
    m_wat_liq: float   # E21  - kg/h di acqua liquida in reattore
    m_mx_liq: float    # E22  - kg/h di m-xilene in reattore
    m_hac_liq: float   # E20  - kg/h di acido acetico in reattore
    reac_yield: float  # B11  - resa o fattore per consumo HAC (come in VBA, usato nel liquido)
    T_feed_ref: float  # E30  - temperatura base feed [°C]
    Cp_feed: float     # E28  - capacità termica equivalente feed [kcal/h/°C]
    T_air_ref: float   # G30  - temperatura base aria [°C]
    m_air_kgph: float  # G28  - portata aria [kg/h]
    T_e3101_out: float # M30  - temperatura uscita E3101 [°C]
    T_e3102_out: float # Q30  - temperatura uscita E3102 [°C]


def tempcalc(params: Inputs):
    """
    Traduzione Python del VBA tempcalc().
    Restituisce un dict con:
    - temperature_final
    - diffheat
    - e3101kgwatcond, e3101kgaccond
    - e3102kgwatcond, e3102kgaccond
    - kgacev, kgwatev (evaporati dal reattore)
    """

    # unpack per leggibilità
    ptot = params.ptot
    temperature = params.Tin  # °C
    step_T = params.step_T
    ninc = params.ninc

    # queste variabili vengono usate prima di essere ricalcolate nei cicli
    # nel VBA erano implicite (inizializzate a 0)
    e3101kgwatcond = 0.0
    e3101kgaccond = 0.0
    e3102kgwatcond = 0.0
    e3102kgaccond = 0.0

    kgacev = 0.0
    kgwatev = 0.0
    diffheat = 0.0

    # ciclo esterno 1..20 come in VBA
    for i in range(1, 31):

        # 1) Pressioni di vapore Antoine (acqua e HAC) [atm]
        # eq. come in VBA, con Exp(...) / 760
        watpress = math.exp(18.36 - (3840.96 / (temperature + 228.3))) / 760.0
        print (" partial pressure of water" , watpress)
        acpress = math.exp(19.32 - (5495.31 / (temperature + 314.75))) / 760.0
        print (" > partial pressure of acetic acid : ", acpress)

        # 2) Moli in liquido nel reattore
        # acqua liquida [mol]
        liqwat = params.m_wat_liq / 18.0 + params.m_mx_liq / 106.0 * 2.0
        # HAC liquido [mol]
        liqac = params.m_hac_liq / 60.0 - (params.m_mx_liq / 0.71 * params.reac_yield / 1000.0) / 60.0
        # PIA in soluzione [mol] (nel VBA: liqpia = E22/106, qui mantenuto)
        liqpia = params.m_mx_liq / 106.0

        totliqmol = liqwat + liqac + liqpia

        xwat = liqwat / totliqmol
        xac = liqac / totliqmol

        # 3) Pressioni parziali nel reattore [atm]
        ppac = acpress * xac
        ppwat = watpress * xwat
        Pinc = ptot - ppac - ppwat

        # 4) Moli totali in fase vapore (gas + vapori) [mol/h]
        # ntot = ninc / (Pinc / ptot)
        ntot = ninc * ptot / Pinc

        yac = ppac / ptot
        ywat = ppwat / ptot
        yinc = 1.0 - yac - ywat  # non usato direttamente, ma lo calcolo per completezza

        # 5) kg/h evaporati dal reattore
        kgacev = ntot * yac * 60.0   # 
        print (" kg of acetic acid evaporated  : " , kgacev)
        kgwatev = ntot * ywat * 18.0 # H2O
        print (" kg of water evaporated ;  ", kgwatev)

        # 6) Calore di evaporazione
        # steamlatheat = 556.6107 - 23.2115 * sqrt(ptot - Pinc)
        steamlatheat = 556.6107 - 23.2115 * math.sqrt(ptot - Pinc)
        heatev = steamlatheat * kgwatev + 81.0 * kgacev  # 81 = calore latente HAC [kcal/kg] (dal VBA)

        # 7) Calore di reazione [kcal/h]
        # reactionheat = E22 * 2672.89 + E22 * 166/106 * 35 * 10 * 1.15
        # (formula originale VBA, Joback + extra termine)
        reactionheat = (
            params.m_mx_liq * 2672.89
            + params.m_mx_liq * 166.0 / 106.0 * 35.0 * 10.0 * 1.15
        )
        

        # 8) Enthalpy feed [kcal/h]
        feedheat = (temperature - params.T_feed_ref) * (params.m_hac_liq+params.m_wat_liq+params.m_mx_liq*0.6)
        print(" feedheat : ", feedheat , "kcal/h")

        # 9) Enthalpy aria inlet [kcal/h]  
        # (temperature - G30) * ((6.5 + 0.001*(T+273.01))/28) * G28
        airCp_per_kg = (6.5 + 0.001 * (temperature + 273.01)) / 28.0  # [kcal/kg/°C] approx
        airheat = (temperature - params.T_air_ref) * airCp_per_kg * params.m_air_kgph

        # 10) entalpia ricicli da E3101 ed E3102 (dipendono da iterazioni precedenti del condensato)
        e3101heat = e3101kgwatcond * (temperature - params.T_e3101_out) + \
                    e3101kgaccond * (temperature - params.T_e3101_out)
        e3102heat = e3102kgwatcond * (temperature - params.T_e3102_out) + \
                    e3102kgaccond * (temperature - params.T_e3102_out)

        # 11) Bilancio termico globale reattore
        diffheat = reactionheat - feedheat - airheat - heatev - e3101heat - e3102heat

        # 12) Aggiornamento temperatura (tipo "relaxation" molto semplice)
        if diffheat > 0:
            temperature = temperature + step_T / i
        else:
            temperature = temperature - step_T / i


        # --- BLOCCO CONDENSAZIONE E3101 ------------------------------------
        TE3101out = params.T_e3101_out

        watpresse3101 = math.exp(18.36 - (3840.96 / (TE3101out + 228.3))) / 760.0
        acpresse3101  = math.exp(19.32 - (5495.31 / (TE3101out + 314.75))) / 760.0

        # iterazione su composizione liquida condensata
        e3101xwat = 0.5
        for j in range(5):
            e3101xac = 1.0 - e3101xwat
            e3101ppac = e3101xac * acpresse3101
            e3101ppwat = e3101xwat * watpresse3101
            prince3101 = ptot - e3101ppac - e3101ppwat

            e3101yac = e3101ppac / ptot
            e3101ywat = e3101ppwat / ptot

            e3101ntot = ninc * ptot / prince3101

            e3101vapwat = e3101ntot * e3101ywat
            e3101vapac  = e3101ntot * e3101yac

            nevwat = kgwatev / 18.0
            nevac  = kgacev / 60.0

            e3101condwat = nevwat - e3101vapwat
            e3101condac  = nevac  - e3101vapac

            e3101xwat = e3101condwat / (e3101condwat + e3101condac)
            # e3101xac = 1 - e3101xwat (non serve ricalcolarlo)

        e3101kgwatcond = e3101condwat * 18.0
        e3101kgaccond  = e3101condac  * 60.0

        # --- BLOCCO CONDENSAZIONE E3102 ------------------------------------
        TE3102out = params.T_e3102_out

        watpresse3102 = math.exp(18.36 - (3840.96 / (TE3102out + 228.3))) / 760.0
        acpresse3102  = math.exp(19.32 - (5495.31 / (TE3102out + 314.75))) / 760.0

        e3102xwat = 0.5
        for k in range(5):
            e3102xac = 1.0 - e3102xwat
            e3102ppac = e3102xac * acpresse3102
            e3102ppwat = e3102xwat * watpresse3102
            prince3102 = ptot - e3102ppac - e3102ppwat

            e3102yac = e3102ppac / ptot
            e3102ywat = e3102ppwat / ptot

            e3102ntot = ninc * ptot / prince3102

            e3102vapwat = e3102ntot * e3102ywat
            e3102vapac  = e3102ntot * e3102yac

            # attenzione: qui il VBA usa "e3101vapwat" come base da cui condensa E3102
            e3102condwat = e3101vapwat - e3102vapwat
            e3102condac  = e3101vapac  - e3102vapac

            e3102xwat = e3102condwat / (e3102condwat + e3102condac)
            # e3102xac = 1 - e3102xwat

        e3102kgwatcond = e3102condwat * 18.0
        e3102kgaccond  = e3102condac  * 60.0

        # fine ciclo I, ricomincia con nuova temperatura, nuovi condensati, ecc.

    # fine ciclo 1..20
    return {
        "temperature_final_C": temperature,
        "diffheat_kcal_per_h": diffheat,
        "kg_HAc_evaporated": kgacev,
        "kg_H2O_evaporated": kgwatev,
        "E3101_kg_H2O_cond": e3101kgwatcond,
        "E3101_kg_HAc_cond": e3101kgaccond,
        "E3102_kg_H2O_cond": e3102kgwatcond,
        "E3102_kg_HAc_cond": e3102kgaccond,
    }


if __name__ == "__main__":
    # Esempio di chiamata con numeri inventati (da sostituire coi tuoi)
    params = Inputs(
        ptot=12.0,          # atm
        Tin=200.0,         # °C
        step_T=1.0,       # °C (K15)
        ninc=5000.0,       # mol/h
        m_wat_liq=2725.72, # kg/h (E21)
        m_mx_liq=5391.64,  # kg/h (E22)
        m_hac_liq=36213.14,# kg/h (E20)
        reac_yield=80.0,   # B11 (% o fattore, da verificare)
        T_feed_ref=60.0,   # °C (E30)
        Cp_feed=1.0,   # kcal/h/°C (E28, da impostare corretto)
        T_air_ref=25.0,    # °C (G30)
        m_air_kgph=10000.0,# kg/h (G28)
        T_e3101_out=40.0,  # °C (M30)
        T_e3102_out=30.0,  # °C (Q30)
    )

    res = tempcalc(params)
    print(res)