### Code for Isophtalic acid plant based on Lonza Singapore Technology rifatto nuovo

import math
from dataclasses import dataclass
import os
import math
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk, ImageDraw, ImageFont

### Flow air for  PIA reactor + air temperature after compressor ###
air_flow = 29372 # kg/h
o2_air_flow = air_flow * 0.2286
n2_air_flow = air_flow * 0.7654
co2_air_flow = air_flow * 0.001
water_air_flow = air_flow * 0.005
print(o2_air_flow + n2_air_flow + co2_air_flow + water_air_flow)
air_pressure = 13 # barg
t_atm = 30
air_temp_comp = (((air_pressure/1)**((1.4-1)/1.4))*(t_atm+273))-273
print ("air temperature after compressor is :" , air_temp_comp)
if air_temp_comp > 111:
    air_temp_comp = 111
print ("air temperature after compressor is :" , air_temp_comp)