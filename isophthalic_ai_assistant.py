"""
isophthalic_ai_assistant.py

Glass Plant - Isophthalic AI Assistant

Purpose:
- Read Isophthalic OPC UA values.
- Run a rule-based assistant for immediate operator guidance.
- Optionally send the context to a local Ollama/Llama model for a natural-language explanation.

Important:
- This assistant is advisory only.
- It does NOT control the plant.
- It should not bypass DCS, SIS, alarms, interlocks, procedures, or operator judgement.

Run:
    python3 isophthalic_ai_assistant.py

Optional local Llama/Ollama mode:
    1) Install Ollama
    2) Run:
        ollama pull llama3.1:8b
        ollama serve
    3) Install requests:
        python3 -m pip install requests
    4) Set USE_OLLAMA = True below
"""

import asyncio
import json
import time
from typing import Any, Dict

from asyncua import Client


# =========================================================
# CONFIGURATION
# =========================================================

OPC_SERVER_URL = "opc.tcp://127.0.0.1:4842/isophthalic/server/"
SCAN_SEC = 5.0

USE_OLLAMA = False
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.1:8b"

OPC_TAG_NAMES = {
    "MX_Feed_kg_h": ["Feed", "MX_Feed_kg_h"],
    "Reactor_Pressure_barg": ["Reactor", "Reactor_Pressure_barg"],
    "HP_Steam_Pressure_barg": ["Utilities", "HP_Steam_Pressure_barg"],
    "LP_Steam_Pressure_barg": ["Utilities", "LP_Steam_Pressure_barg"],
    "Reactor_Temperature_C": ["Reactor", "Reactor_Temperature_C"],
    "Thickness_Index": ["Product", "Thickness_Index"],
}


# =========================================================
# OPC UA FUNCTIONS
# =========================================================

async def find_child_by_browse_name(parent, browse_name: str):
    children = await parent.get_children()

    for child in children:
        node_browse_name = await child.read_browse_name()
        if node_browse_name.Name == browse_name:
            return child

    raise RuntimeError(f"Child not found: {browse_name}")


async def resolve_tag_nodes(client: Client) -> Dict[str, Any]:
    objects = client.nodes.objects
    plant = await find_child_by_browse_name(objects, "IsophthalicPlant")

    tag_nodes = {}

    for tag_name, path in OPC_TAG_NAMES.items():
        node = plant
        for part in path:
            node = await find_child_by_browse_name(node, part)
        tag_nodes[tag_name] = node

    return tag_nodes


async def read_opc_values(tag_nodes: Dict[str, Any]) -> Dict[str, float]:
    values = {}

    for tag_name, node in tag_nodes.items():
        values[tag_name] = float(await node.read_value())

    return values


# =========================================================
# RULE-BASED ASSISTANT
# =========================================================

def classify_thickness_index(thickness_index: float) -> str:
    if thickness_index < 0.330:
        return "OK"
    if thickness_index < 0.345:
        return "WARNING"
    return "NOT_OK"


def rule_based_guidance(values: Dict[str, float]) -> str:
    mx_feed = values["MX_Feed_kg_h"]
    reactor_pressure = values["Reactor_Pressure_barg"]
    hp_steam = values["HP_Steam_Pressure_barg"]
    lp_steam = values["LP_Steam_Pressure_barg"]
    reactor_temp = values["Reactor_Temperature_C"]
    thickness_index = values["Thickness_Index"]

    status = classify_thickness_index(thickness_index)

    messages = []
    messages.append("Glass Plant AI Assistant - Isophthalic Unit")
    messages.append("=" * 55)
    messages.append("")
    messages.append("Current OPC UA values:")
    messages.append(f"- MX feed: {mx_feed:.1f} kg/h")
    messages.append(f"- Reactor pressure: {reactor_pressure:.2f} barg")
    messages.append(f"- HP steam pressure: {hp_steam:.2f} barg")
    messages.append(f"- LP steam pressure: {lp_steam:.2f} barg")
    messages.append(f"- Reactor temperature: {reactor_temp:.2f} °C")
    messages.append(f"- Thickness index: {thickness_index:.3f}")
    messages.append("")

    if status == "OK":
        messages.append("Status: OK")
        messages.append("The crystallizer feed thickness index is inside the normal operating range.")
        messages.append("Recommended action: continue monitoring.")
    elif status == "WARNING":
        messages.append("Status: WARNING")
        messages.append("The thickness index is moving toward the upper limit.")
        messages.append("Recommended checks:")
        messages.append("1. Check water and acetic acid dilution to crystallizer.")
        messages.append("2. Check condenser performance.")
        messages.append("3. Check whether LP/HP steam pressure changed recently.")
        messages.append("4. Compare DCS value with lab/analyzer trend if available.")
    else:
        messages.append("Status: NOT OK")
        messages.append("The thickness index is too high.")
        messages.append("Recommended checks:")
        messages.append("1. Verify crystallizer feed dilution immediately.")
        messages.append("2. Check if acetic acid/water condensation is lower than expected.")
        messages.append("3. Check reactor temperature and pressure consistency.")
        messages.append("4. Escalate according to plant operating procedure.")

    messages.append("")

    if reactor_temp > 215.0:
        messages.append("Additional observation: reactor temperature is high.")
        messages.append("Check steam balance, oxidation severity, and cooling duty.")
    elif reactor_temp < 190.0:
        messages.append("Additional observation: reactor temperature is low.")
        messages.append("Check feed rate, oxygen supply, and reactor heat release.")

    if reactor_pressure < 12.0 or reactor_pressure > 18.0:
        messages.append("Additional observation: reactor pressure is outside the preferred demonstration range.")

    messages.append("")
    messages.append("Important: this assistant is advisory only and does not replace DCS alarms, SIS, procedures, or operator judgement.")

    return "\n".join(messages)


# =========================================================
# OPTIONAL OLLAMA / LOCAL LLAMA EXPLANATION
# =========================================================

def build_llama_prompt(values: Dict[str, float], rule_guidance: str) -> str:
    return f"""
You are an industrial process assistant for an isophthalic acid plant.

Your role:
- Explain the current operating situation clearly.
- Support the operator.
- Do not invent data.
- Do not recommend unsafe actions.
- Do not bypass plant procedures, DCS alarms, SIS, or operator judgement.
- Keep the answer practical and concise.

Current OPC UA values:
{json.dumps(values, indent=2)}

Rule-based engineering guidance:
{rule_guidance}

Write:
1. Situation summary.
2. Most likely concern.
3. Recommended checks for the operator.
4. Safety reminder.
"""


def ask_ollama(prompt: str) -> str:
    try:
        import requests
    except ImportError:
        return (
            "Ollama mode requested, but the Python package 'requests' is not installed.\n"
            "Install it with:\n"
            "    python3 -m pip install requests"
        )

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data.get("response", "No response field returned by Ollama.")
    except Exception as exc:
        return f"Ollama connection error: {exc}"


# =========================================================
# MAIN LOOP
# =========================================================

async def main_loop():
    while True:
        try:
            print("Trying OPC UA connection:", OPC_SERVER_URL)

            async with Client(url=OPC_SERVER_URL) as client:
                print("OPC UA connected")
                tag_nodes = await resolve_tag_nodes(client)

                while True:
                    values = await read_opc_values(tag_nodes)

                    rule_guidance = rule_based_guidance(values)

                    print("\n" + rule_guidance)

                    if USE_OLLAMA:
                        prompt = build_llama_prompt(values, rule_guidance)
                        llama_answer = ask_ollama(prompt)
                        print("\nLocal Llama explanation")
                        print("=" * 55)
                        print(llama_answer)

                    print("\nNext scan in", SCAN_SEC, "seconds.")
                    print("-" * 80)

                    await asyncio.sleep(SCAN_SEC)

        except Exception as exc:
            print("OPC UA connection error:", exc)
            print("Retrying in 3 seconds...")
            await asyncio.sleep(3.0)


def main():
    asyncio.run(main_loop())


if __name__ == "__main__":
    main()
