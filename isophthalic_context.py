ISOPHTHALIC_CONTEXT = """
Isophthalic Acid / PIA Glass Plant model context.

The model represents an isophthalic acid oxidation section.

Typical feed values:
- Acetic acid: 36213.14 kg/h
- Water: 2725.72 kg/h
- m-xylene: 5391.64 kg/h
- Oxygen: 6217.82 kg/h
- Nitrogen: 20816.18 kg/h
- CO2: 27.03 kg/h
- Feed temperature: about 60 C

Main process concept:
- m-xylene is oxidized to isophthalic acid.
- Acetic acid is used as solvent.
- Oxygen is the oxidant.
- Nitrogen mainly comes with the air / oxygen-containing gas.
- Reactor temperature, oxygen feed, solvent ratio, water content, and conversion are important indicators.

Important operating interpretation:
- High reactor temperature may indicate higher reaction rate, poor heat removal, abnormal oxidation intensity, or control deviation.
- Low conversion may indicate insufficient oxygen, poor mixing, low residence time, catalyst or promoter issue, or unsuitable reactor conditions.
- Water content affects solvent composition and can influence reaction environment.
- Acetic acid to m-xylene ratio is important for dilution, heat removal, and reaction performance.
- Oxygen feed must be interpreted carefully because oxygen deficiency can limit oxidation, while excess oxygen has safety implications.

AI rules:
- Do not invent plant data.
- Use the OPC UA values provided in the prompt.
- Separate measured OPC values from calculated interpretations.
- Explain in process engineering language.
- Mention missing data when relevant.
- This assistant is for explanation and support only, not automatic control.
"""