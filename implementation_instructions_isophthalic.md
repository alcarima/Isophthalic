# Implementation Instructions - Isophthalic Glass Plant Client and AI Assistant

## 1. Files to use

Put these files in the same folder, for example:

```text
isophthalic_plant/
├── isophthalic_opc_server_vs1.py
├── isophthalic_client_vs1.py
├── isophthalic_ai_assistant.py
└── Isophthalic.drawio.png
```

The server file name can be the one you already have. The important point is that the OPC UA server must expose:

```text
Objects
└── IsophthalicPlant
    ├── Feed
    │   └── MX_Feed_kg_h
    ├── Reactor
    │   ├── Reactor_Pressure_barg
    │   └── Reactor_Temperature_C
    ├── Utilities
    │   ├── HP_Steam_Pressure_barg
    │   └── LP_Steam_Pressure_barg
    └── Product
        └── Thickness_Index
```

The OPC UA URL used by both programs is:

```text
opc.tcp://127.0.0.1:4842/isophthalic/server/
```

## 2. Create or activate the Python virtual environment

Open Terminal in the project folder.

```bash
cd ~/Desktop/isophthalic_plant
python3 -m venv .venv
source .venv/bin/activate
```

If your folder is called `Isophthalic` instead:

```bash
cd ~/Desktop/Isophthalic
python3 -m venv .venv
source .venv/bin/activate
```

## 3. Install the required packages

```bash
python3 -m pip install --upgrade pip
python3 -m pip install asyncua pillow requests
```

`requests` is only needed if you want to use Ollama/Llama in the AI Assistant.

## 4. Start the OPC UA server first

In Terminal 1:

```bash
cd ~/Desktop/isophthalic_plant
source .venv/bin/activate
python3 isophthalic_opc_server_vs1.py
```

You should see something similar to:

```text
OPC UA server started at opc.tcp://127.0.0.1:4842/isophthalic/server/
```

Keep this Terminal open.

## 5. Start the graphical Isophthalic client

Open Terminal 2:

```bash
cd ~/Desktop/isophthalic_plant
source .venv/bin/activate
python3 isophthalic_client_vs1.py
```

Expected result:

- Tkinter window opens.
- The drawing `Isophthalic.drawio.png` is displayed.
- Sliders are updated from OPC UA.
- Operator indications appear on the left.
- Model and DCS/OPC values are compared.

## 6. Start the AI Assistant

Open Terminal 3:

```bash
cd ~/Desktop/isophthalic_plant
source .venv/bin/activate
python3 isophthalic_ai_assistant.py
```

Expected result:

```text
Trying OPC UA connection: opc.tcp://127.0.0.1:4842/isophthalic/server/
OPC UA connected

Glass Plant AI Assistant - Isophthalic Unit
=======================================================
Current OPC UA values:
...
Status: OK / WARNING / NOT OK
...
```

## 7. Optional: use local Llama with Ollama

Install Ollama if not already installed.

Then run:

```bash
ollama pull llama3.1:8b
ollama serve
```

In `isophthalic_ai_assistant.py`, change:

```python
USE_OLLAMA = False
```

to:

```python
USE_OLLAMA = True
```

Then run again:

```bash
python3 isophthalic_ai_assistant.py
```

The assistant will first produce rule-based guidance, then it will ask the local Llama model to explain the operating situation in operator language.

## 8. Important safety concept

The AI Assistant is not an APC.

It does not write to OPC UA.
It does not move valves.
It does not change DCS setpoints.
It does not override alarms or interlocks.

It only:

1. Reads live data.
2. Runs rules.
3. Produces operator guidance.
4. Makes process deviations visible.

This is exactly the Glass Plant philosophy: the plant becomes visible before becoming automatic.

## 9. Recommended next development step

After this version works, split the project into modules:

```text
isophthalic_plant/
├── model_isophthalic.py
├── opc_client_isophthalic.py
├── ui_isophthalic.py
├── assistant_rules_isophthalic.py
├── isophthalic_client_vs1.py
└── isophthalic_ai_assistant.py
```

This will make the project more professional and easier to maintain.

## 10. Troubleshooting

### Problem: `zsh: command not found: python`

Use:

```bash
python3 file_name.py
```

not:

```bash
python file_name.py
```

### Problem: `ModuleNotFoundError: No module named 'asyncua'`

Run:

```bash
source .venv/bin/activate
python3 -m pip install asyncua
```

### Problem: `ModuleNotFoundError: No module named 'PIL'`

Run:

```bash
source .venv/bin/activate
python3 -m pip install pillow
```

### Problem: image not shown

Check that the file name is exactly:

```text
Isophthalic.drawio.png
```

and that it is in the same folder as:

```text
isophthalic_client_vs1.py
```

### Problem: OPC UA connection error

Check:

1. The server is running.
2. The server port is `4842`.
3. The endpoint is exactly:

```text
opc.tcp://127.0.0.1:4842/isophthalic/server/
```

4. The server exposes the object name:

```text
IsophthalicPlant
```
