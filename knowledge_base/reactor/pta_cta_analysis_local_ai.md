# CTA / PTA World Quality Analysis — Local AI Knowledge Document

**Source file:** `Analysis CTA-PTA world.pdf`  
**Topic:** Comparative analytical data for CTA, PTA, TA and MTA products from multiple producers.  
**Prepared for:** Local AI / RAG knowledge base.  
**Document type:** Structured technical notes, chunk-ready.  

---

## 1. Purpose of this Document

This document converts the attached PDF into a structured Markdown file suitable for use with a local AI system, such as Ollama, a RAG application, or a local knowledge assistant.

The original PDF consists mainly of six comparative analytical tables:

1. PTA organic impurities
2. PTA inorganic impurities
3. PTA optical properties and particle size
4. TA and MTA inorganic impurities
5. TA and MTA organic impurities
6. TA optical properties and particle size

The data compares product quality from several producers, including Amoco, Mitsui, ICI, Cape Ind., Capco, Samsung, Temex, Interquisa, Jinshan, Mitsubishi, Eastman, and DuPont.

---

## 2. Acronyms and Definitions

| Acronym | Meaning |
|---|---|
| PTA | Purified terephthalic acid |
| CTA | Crude terephthalic acid |
| TA | Terephthalic acid, usually less purified than PTA in the context of the tables |
| MTA | Medium-quality or modified terephthalic acid, as used in the source tables |
| LC | Liquid chromatography |
| ELC | Electrochromatography |
| 4-CBA | 4-carboxybenzaldehyde |
| HM | Hydroxymethyl |
| C / CO | Carboxy |
| TC | Tricarboxy |
| DC | Dicarboxy |
| CC | Carboxydicarboxy |
| CP | Carboxyphenyl |
| Delta Y | Yellowing index / color difference indicator used in the table context |

---

## 3. High-Level Technical Summary

### 3.1 PTA Quality Pattern

PTA samples show low impurity levels compared with TA and MTA samples. In the PTA organic impurity table, 4-CBA is generally in the range of a few ppm to a few tens of ppm, depending on producer. p-Toluic acid is generally present at tens to hundreds of ppm. Other organic impurities include benzoic acid, hydroxymethyl benzoic acid, trimellitic acid, isophthalic acid, benzophenone derivatives, biphenyl derivatives, fluorenone derivatives, fluorene derivatives, and anthracene-type compounds.

### 3.2 PTA Inorganic Quality Pattern

PTA inorganic impurities are generally very low. Ash is typically in the single-digit ppm range. Metallic impurities such as aluminum, calcium, cobalt, chromium, copper, iron, potassium, magnesium, manganese, molybdenum, sodium, nickel, titanium, and zinc are reported mostly below 1 ppm or in very low ppm ranges.

### 3.3 TA / MTA Quality Pattern

TA and MTA show much higher organic impurity levels than PTA. The most important quality marker is 4-CBA, which can be in the thousands of ppm for several TA samples. p-Toluic acid, benzoic acid, trimellitic acid, isophthalic acid, and aromatic by-products are also much higher than in PTA.

### 3.4 Optical Properties

PTA has high lightness values, generally around L = 98.3 to 99.1, and low b-values, generally around 0.5 to 1.7. TA products show lower optical quality, with lower L and higher b-values. This is consistent with higher organic impurity content and lower product purity.

### 3.5 Particle Size

The tables provide particle-size distributions using mesh/micron passing data and average particle size. PTA average particle size typically appears in the approximate range of 60 to 138 microns depending on supplier and product grade. TA average particle size can vary more widely, including coarse and fine materials depending on producer and grade.

---

## 4. Chunk 001 — PTA Organic Impurities

**Source:** Page 1, Table I — PTA organic impurities.

### Description

This table compares organic impurities in PTA samples from multiple producers. The main analytical methods are liquid chromatography and electrochromatography.

### Producers / Materials Compared

- Amoco US
- Amoco Geel
- Mitsui
- ICI
- Cape Ind.
- Capco
- Samsung
- Temex
- Interquisa
- Jinshan

### Important Organic Impurities

| Impurity | Typical PTA observation from the table |
|---|---|
| 4-CBA | Generally low, commonly around 2–23 ppm depending on producer |
| p-Toluic acid | Frequently around 100–150 ppm, but some values are lower or higher |
| Benzoic acid | Often below a few ppm, but some producers show values around 14–42 ppm |
| HM benzoic acid | Generally low-to-moderate ppm values |
| Trimellitic acid | Usually low ppm to tens of ppm |
| Isophthalic acid | Often below 2 ppm, but some samples show higher values |
| TC benzophenone | Generally trace-to-low ppm |
| 3,7-DC benzocoumarine | Generally trace-to-low ppm |
| TC biphenyl | Low-to-tens of ppm |
| 2,6-CC fluorenone | Trace-to-low ppm |
| CC biphenyl | Can be significant, often tens to over 100 ppm |
| 2,6-CC fluorene | Low-to-tens of ppm |
| bis CP methane / ethane | Usually low ppm |
| CC anthracene | Trace-to-low ppm |

### Local AI Notes

- 4-CBA is a key aldehydic impurity in terephthalic acid quality control.
- p-Toluic acid is a partially oxidized methyl aromatic impurity.
- Higher levels of colored aromatic species can affect optical properties and downstream polymer color.
- The table is useful for benchmarking PTA quality among producers.

### Suggested Questions for Local AI

- Which impurities distinguish high-quality PTA from lower-quality TA?
- Which producer shows the lowest 4-CBA in the PTA table?
- Why are p-toluic acid and 4-CBA important in terephthalic acid quality?
- Which aromatic impurities may influence color or fluorescence?

---

## 5. Chunk 002 — PTA Inorganic Impurities

**Source:** Page 2, Table II — PTA inorganic impurities.

### Description

This table compares inorganic impurities in PTA samples. It reports ash, individual metal concentrations, water, and Delta Y.

### Main Parameters

| Parameter | PTA trend from the table |
|---|---|
| Ash | Generally low, mostly 1–9 ppm |
| Aluminum | Usually below 0.1 ppm or near trace level |
| Calcium | Usually around trace to 0.3 ppm, with some higher individual values |
| Cobalt | Usually below 0.1–0.3 ppm |
| Chromium | Usually trace level |
| Copper | Usually trace level |
| Iron | Generally below 0.5 ppm |
| Potassium | Usually trace level |
| Magnesium | Usually trace level, with some higher exceptions |
| Manganese | Usually trace-to-low ppm |
| Molybdenum | Usually trace-to-low ppm |
| Sodium | Low ppm or sub-ppm range |
| Nickel | Usually trace, although some table entries appear higher or uncertain |
| Titanium | Trace level |
| Zinc | Trace level |
| Water | Varies significantly, from tens to thousands of ppm depending on sample |
| Delta Y | Generally low, around 1.1–6 depending on producer |

### Local AI Notes

- Low metal content is important because metals can affect polymerization, catalyst behavior, color, and downstream product stability.
- Ash is a general indicator of inorganic residue.
- Water content varies more widely than most metal impurities.
- Delta Y is related to product color/yellowness.

### Suggested Questions for Local AI

- Which inorganic impurities are most relevant for PTA polymer-grade quality?
- How does ash content compare among PTA producers?
- Why can cobalt, manganese, and bromine residues matter in terephthalic acid production?
- What is the significance of water content in PTA handling and storage?

---

## 6. Chunk 003 — PTA Optical Properties and Particle Size

**Source:** Page 3, Table III — PTA optical properties and particle size.

### Description

This table compares optical properties and particle-size distribution for PTA samples.

### Optical Properties

| Property | PTA trend from the table |
|---|---|
| L | High lightness, typically around 98.3–99.1 |
| a | Slightly negative values, typically around -0.2 to -0.7 |
| b | Low positive values, typically around 0.5–1.7 |
| Fluorescence index | Generally low, often below about 1.5 |
| 4-Ctr | Very low, generally below about 1.2 ppm |
| 340 nm absorbance | Low values, generally around 0.01–0.16% |
| 400 nm absorbance | Very low values, generally around 0.001–0.019% |
| Stability test at 340 nm | Varies among suppliers |

### Particle Size

The table reports passing fractions for several mesh/micron values:

- 70 mesh / 210 micron
- 100 mesh / 149 micron
- 140 mesh / 105 micron
- 200 mesh / 74 micron
- 270 mesh / 53 micron
- 325 mesh / 44 micron
- 400 mesh / 38 micron

Average particle size varies by producer and grade, approximately from 60 to 138 microns in the data shown.

### Local AI Notes

- Higher L and lower b values indicate a whiter product.
- Particle size affects filtration, drying, conveying, silo handling, dustiness, and downstream slurry behavior.
- Optical properties are strongly linked to organic impurity profile and oxidation/purification performance.

### Suggested Questions for Local AI

- What optical properties indicate high-quality PTA?
- How does particle size influence PTA handling?
- Which PTA producer has the finest or coarsest average particle size?
- What is the relationship between organic impurities and b-value?

---

## 7. Chunk 004 — TA and MTA Inorganic Impurities

**Source:** Page 4, Table IV — TA and MTA inorganic impurities.

### Description

This table compares inorganic impurities in TA and MTA materials. Compared with PTA, TA and MTA generally show higher ash and higher residual inorganic components.

### Producers / Materials Compared

- Amoco US TA
- Amoco Geel TA
- Mitsui TA
- Capco TA
- Samsung TA
- Interquisa TA
- Mitsubishi QTA
- Mitsubishi S-QTA
- Eastman MTA

### Main Observations

| Parameter | TA / MTA trend from the table |
|---|---|
| Ash | Can be much higher than PTA, e.g. tens to around 100 ppm in several samples |
| Calcium | Several ppm to tens of ppm depending on material |
| Magnesium | Can be high in some TA samples |
| Molybdenum | Can be present at ppm levels in some samples |
| Bromine | Significant in several TA samples, with values reported around 9–52 ppm |
| Water | Often around 50–260 ppm depending on material |
| Delta Y | Variable, and generally higher than PTA in some samples |

### Local AI Notes

- Bromine is relevant because terephthalic acid oxidation commonly uses bromide-promoted cobalt/manganese catalyst systems.
- Higher ash and inorganic residues are characteristic of less purified material.
- Inorganic residues can affect downstream polymerization and product color.

### Suggested Questions for Local AI

- Why is bromine present in crude terephthalic acid?
- How do inorganic impurities differ between PTA and TA?
- Which metals are most important for downstream polyester quality?
- Why is ash higher in TA than PTA?

---

## 8. Chunk 005 — TA and MTA Organic Impurities

**Source:** Page 5, Table V — TA and MTA organic impurities.

### Description

This table compares organic impurities in TA and MTA products. These values are generally much higher than in PTA.

### Key Organic Impurity Trends

| Impurity | TA / MTA observation from the table |
|---|---|
| 4-CBA | Often very high, commonly hundreds to thousands of ppm |
| p-Toluic acid | Can range from tens to thousands of ppm depending on producer |
| Benzoic acid | Usually tens to hundreds of ppm |
| HM benzoic acid | Tens to hundreds of ppm in some samples |
| Trimellitic acid | Can be hundreds of ppm in several TA products |
| Isophthalic acid | Can be hundreds to thousands of ppm depending on sample |
| TC benzophenone | Tens of ppm in several samples |
| 3,7-DC benzocoumarine | Low-to-tens of ppm |
| TC biphenyl | Tens to over 100 ppm |
| 2,6-DC fluorenone | Tens to hundreds of ppm |
| DC biphenyl | Tens to hundreds of ppm, with some high values |
| DC benzophenone | Can be significant in some samples |
| DC anthraquinone | Can be significant in some samples |
| 3,6-DC fluorenone | Low-to-tens of ppm |
| DC stilbene | Low-to-tens of ppm |
| Acetic acid | Can be high, ranging from hundreds to thousands of ppm |

### Local AI Notes

- TA and MTA contain much higher residual oxidation intermediates than PTA.
- 4-CBA is a major marker of incomplete oxidation and inadequate purification.
- Acetic acid residue reflects the oxidation solvent system and solid-liquid separation / drying performance.
- Aromatic polycarboxylic impurities can affect color, optical properties, and downstream polyester quality.

### Suggested Questions for Local AI

- Why is 4-CBA much higher in TA than PTA?
- Which impurities indicate incomplete oxidation of p-xylene?
- Which impurities are likely to contribute to yellow color or fluorescence?
- What is the role of acetic acid as a residual impurity?

---

## 9. Chunk 006 — TA Optical Properties and Particle Size

**Source:** Page 6, Table VI — TA optical properties and particle size.

### Description

This table compares optical properties and particle-size distribution for TA products.

### Optical Properties

| Property | TA trend from the table |
|---|---|
| L | Generally lower than PTA, with values around 92.0–98.8 depending on material |
| a | Negative values, sometimes more negative than PTA |
| b | Higher than PTA, often around 2–8 depending on sample |
| Fluorescence index | Generally low-to-moderate |
| 340 nm absorbance | Higher than PTA in several samples |
| 400 nm absorbance | Higher than PTA in several samples |
| Stability test at 340 nm | Variable |

### Particle Size

The table uses the same mesh/micron convention as the PTA table. Average particle size varies widely depending on material and producer, with values ranging from fine products around 39–50 microns to coarser products above 100 microns.

### Local AI Notes

- TA optical quality is generally poorer than PTA.
- Higher b-values indicate greater yellowness.
- Higher UV absorbance suggests higher levels of color-forming or conjugated impurities.
- Particle-size distribution is important for filtration, drying, conveying, and downstream slurry preparation.

### Suggested Questions for Local AI

- How do TA optical properties differ from PTA optical properties?
- Why does TA often have higher b-value than PTA?
- How does TA particle size affect plant operation?
- Which product appears to be finer or coarser based on average particle size?

---

## 10. Comparative Interpretation: PTA vs TA / MTA

### 10.1 Organic Impurity Comparison

PTA has much lower organic impurity levels than TA and MTA. In particular, 4-CBA is generally reduced from thousands of ppm in TA to tens of ppm or lower in PTA. This reflects the purification function of PTA technology.

### 10.2 Inorganic Impurity Comparison

PTA generally has lower ash and lower metal content than TA. TA can contain significant bromine and higher catalyst-related residues. PTA purification and washing reduce these impurities.

### 10.3 Optical Quality Comparison

PTA shows better color properties, with higher L values and lower b-values. TA shows more yellow color and higher UV absorbance, consistent with higher impurity content.

### 10.4 Particle Size Comparison

Particle-size distributions vary significantly among products and producers. PTA products generally fall into controlled particle-size ranges suitable for polymer applications. TA and MTA show wider variation.

---

## 11. Process Engineering Interpretation

### 11.1 Why 4-CBA Matters

4-CBA is one of the most important impurities in terephthalic acid. It is an oxidation intermediate derived from p-xylene. High 4-CBA indicates incomplete oxidation or insufficient purification. In polyester production, 4-CBA can affect polymer quality, color, and molecular weight development.

### 11.2 Why p-Toluic Acid Matters

p-Toluic acid is another partially oxidized intermediate. It indicates incomplete oxidation of methyl groups on the aromatic ring. High p-toluic acid can point to oxidation selectivity or residence-time limitations.

### 11.3 Why Bromine and Metals Matter

Cobalt, manganese, and bromine are associated with the common liquid-phase oxidation catalyst system used in terephthalic acid production. Residual metals and bromine may indicate insufficient washing, filtration, or purification.

### 11.4 Why Color Matters

The L, a, b, absorbance, fluorescence, and Delta Y indicators provide a practical quality view. High-quality PTA should be white, stable, and low in color-forming impurities. Colored aromatic by-products and conjugated structures can increase yellowness and absorbance.

### 11.5 Why Particle Size Matters

Particle size affects:

- crystallization behavior
- filtration rate
- cake washing efficiency
- dryer operation
- dust formation
- pneumatic conveying
- silo handling
- slurry preparation for polymerization

---

## 12. Knowledge Base Metadata

```yaml
document_title: CTA / PTA World Quality Analysis
document_type: technical_quality_tables
main_topic: terephthalic_acid_quality
subtopics:
  - PTA organic impurities
  - PTA inorganic impurities
  - PTA optical properties
  - PTA particle size
  - TA organic impurities
  - TA inorganic impurities
  - TA optical properties
  - TA particle size
  - MTA quality comparison
  - terephthalic acid purification
  - 4-CBA
  - p-toluic acid
  - catalyst residues
  - product color
  - particle size distribution
recommended_use:
  - RAG retrieval
  - local AI process assistant
  - product quality comparison
  - training document for process engineers
  - PTA / CTA technology benchmarking
source_pages: 1-6
```

---

## 13. Recommended RAG Chunking Strategy

For a local AI system, split this document into the following chunks:

1. Acronyms and definitions
2. High-level summary
3. PTA organic impurities
4. PTA inorganic impurities
5. PTA optical properties and particle size
6. TA / MTA inorganic impurities
7. TA / MTA organic impurities
8. TA optical properties and particle size
9. PTA vs TA comparison
10. Process engineering interpretation

Recommended chunk size: 500–900 words.  
Recommended overlap: 80–150 words.  
Recommended metadata fields: `source_page`, `table_number`, `material_type`, `quality_category`, `main_impurities`.

---

## 14. Example Local AI Prompts

Use the following prompts to test the local AI after ingestion:

1. Compare PTA and TA in terms of 4-CBA content.
2. Which impurities are most important for PTA color quality?
3. Explain why bromine appears in TA inorganic analysis.
4. What is the relevance of p-toluic acid in terephthalic acid production?
5. Which parameters should be monitored to assess PTA whiteness?
6. How does particle size affect PTA filtration and drying?
7. Summarize the difference between PTA and TA optical properties.
8. Explain the relationship between organic impurities and b-value.
9. Which impurities are likely related to incomplete oxidation?
10. How can this quality data support a Glass Plant digital twin or operator advisory system?

---

## 15. Relevance for the Glass Plant / Local AI Operator Assistant

This document can be used as a reference layer for a local AI assistant in a terephthalic acid or related oxidation plant.

Possible use cases:

- Explain the meaning of laboratory quality parameters.
- Connect process deviations to likely impurity formation.
- Support operator training on CTA/PTA quality.
- Provide benchmark ranges for product quality comparison.
- Link oxidation, crystallization, filtration, washing, and drying conditions to product quality.
- Help management understand why small impurity changes matter for downstream polymer performance.

For a Glass Plant application, this document should be connected to live or historical data such as:

- reactor temperature
- reactor pressure
- oxygen concentration
- catalyst concentration
- bromide concentration
- acetic acid / water ratio
- crystallizer temperature profile
- filtration wash ratio
- dryer outlet moisture
- laboratory 4-CBA
- p-toluic acid
- Delta Y
- L/a/b color values
- particle size distribution

---

## 16. Caution on Data Quality

The source is an image-based scanned PDF with tables. Some OCR values may be imperfect, especially where symbols, decimals, ranges, or special characters are present. For critical engineering or commercial use, values should be checked against the original PDF image or laboratory source data.

