# FACTS: How much of Stonehenge is still standing?

Every spoken and on-screen claim, its source, and the wording or the measurement
behind it. Quotations are kept to the words that carry the fact.

Status: revised after two independent refutation passes (12 November 2026);
see "Refutation record" at the end. Not final until the film is approved.

## Sources

- **Darvill 2022**: Darvill, T. 2022. Keeping time at Stonehenge. *Antiquity* 96(386): 319-335. https://doi.org/10.15184/aqy.2022.5 (CC BY 4.0)
- **Nash 2021**: Nash, D.J. et al. 2021. Petrological and geochemical characterisation of the sarsen stones at Stonehenge. *PLoS ONE* 16(8): e0254760, Fig 1B. https://doi.org/10.1371/journal.pone.0254760 (CC BY 4.0)
- **Field 2015**: Field, D. et al. 2015. Analytical Surveys of Stonehenge and its Environs, 2009-2013: Part 2 - the Stones. *Proceedings of the Prehistoric Society* 81: 125-148. https://doi.org/10.1017/ppr.2015.2 (section "Restoration: Hawley and the stones"; the page number 133 is from a secondary citation and was not confirmed against the print)
- **EH Description**: English Heritage, Description of Stonehenge. https://www.english-heritage.org.uk/visit/places/stonehenge/history-and-stories/history/description/
- **EH Stones**: English Heritage, Stones of Stonehenge. https://www.english-heritage.org.uk/visit/places/stonehenge/things-to-do/stone-circle/stones-of-stonehenge/
- **EH Conservation**: English Heritage, From restoration to conservation. https://www.english-heritage.org.uk/visit/places/stonehenge/history-and-stories/history/conservation/
- **EH Research**: English Heritage, Research on Stonehenge, footnotes 7 and 9. https://www.english-heritage.org.uk/visit/places/stonehenge/history/research/
- **EA LIDAR**: Environment Agency, National LIDAR Programme point cloud, tile SU1040, file `SU1040_P_11780_20210404_20210404.laz` (flown 4 April 2021), and LIDAR Composite DTM 2022 at 1 m (`SU14sw_DTM_1m.tif`). https://environment.data.gov.uk/survey (Open Government Licence v3.0)
- **Our measurement**: `topics/stonehenge/digitise_plan.py`, `build_stones.py`, `model.py` (output `topics/stonehenge/stones.json`). The Nash 2021 plan is digitised, fitted to the EA point cloud, and every outline measured against it.

## Spoken (and shown as captions)

| # | Claim | Source | Wording or method |
|---|---|---|---|
| 1 | "The great stones were raised about 4,500 years ago." | EH Description; Darvill 2022 p. 320 | EH: the central stones were brought to the site "about 2500 BC". Darvill: the sarsen structures "were set up during the period 2620-2480 BC". That is 4,500 to 4,650 years before 2026. |
| 2 | "The outer circle most likely had thirty uprights." | Darvill 2022 pp. 320-322; EH Stones; EH Description | Darvill describes a "ring of 30 upright sarsen stones" and argues from parch-marks and excavated sockets that it was completed. English Heritage hedges: the setting, "if completed, was a circle of 30 upright sarsens"; "probably once 30". Darvill notes Ashbee (1998) argued it was never finished. Hence "most likely". |
| 3 | "But of those thirty, only seventeen still stand." | Darvill 2022 p. 320; Field 2015; Nash 2021 Fig 1B; our measurement | Darvill: "Seventeen of the uprights are still standing". Field: "the 17 sarsens presently standing in the outer circuit". Nash's plan draws 17 circle sarsens as upright (stones 1-7, 10, 11, 16, 21-23, 27-30). Measurement: each of those 17 outlines rises 2.60 to 4.98 m above ground in the 2021 scan; the tallest fallen circle stone reads 0.83 m. Two of the seventeen (22 and 23) fell in 1900 and 1963 and were re-erected; see row 5. |
| 4 | "Here we show where the others stood, and the missing lintels." | Darvill 2022 Fig 8 and pp. 320-321; EH Stones | The 13 uprights not standing are projected at the remaining places of 30 even positions on the circle fitted through the 17 standing stones (radius 15.33 m). Even spacing is a modelling choice: Darvill calls the spacing "fairly regular", with a wider gap at the entrance; his Fig 8 marks each missing stone as socket known or socket inferred. 24 lintels are projected: all 30 places minus the six in place (Darvill p. 320: "Six lintels remain in place"). |
| 5 | "Last century, engineers re-set or secured thirteen of the seventeen." | Field 2015; EH Research fn 7 and 9; EH Conservation | Field: "Thirteen of the 17 sarsens presently standing in the outer circuit ... have been subject to some form of intervention". EH Research names them: stabilisation works on stones 1, 2, 6, 7, 29 and 30; stone 21 straightened; stones 22 and 23 re-erected; stones 4, 5, 27 and 28 straightened. EH Conservation dates the work to 1919 and to 1958-1964. "Re-set" here means straightened or re-erected; "secured" means set in concrete (Field reports stone 2 was only set in concrete). Field also counts six of the ten trilithon uprights as treated; this line is about the outer circle only. |
| 6 | "Inside, three of the five trilithons still stand complete." | EH Description; Nash 2021 Fig 1B; our measurement | EH: a "horseshoe of five trilithons"; "three complete trilithons still stand". Nash's plan shows lintels 152, 154 and 158 in place. Measured tops: 6.0, 6.3 and 6.5 m. |
| 7 | "Here is what survives today." "And here is what we infer." | the film's own code | White: every stone outlined on Nash 2021 Fig 1B, standing or fallen, at its measured height. Light: positions and sizes inferred as in rows 4 and 6 and in "Modelling choices" below. |

## On screen

| # | Text | Source | Wording or method |
|---|---|---|---|
| 8 | "17 of 30 circle uprights still stand" | rows 2 and 3 | The counter runs through the 17 standing uprights in stone-number order. The 30 carries the caveat of row 2. |
| 9 | "WHITE survives today · airborne laser scan 2021" | EA LIDAR | Heights are from the airborne laser scan flown 4 April 2021, measured above the 2022 composite ground model. |
| 10 | "LIGHT inferred · sarsens set up c. 2500 BC" | row 1 | |
| 11 | Engraved scale bar "10 m" | Nash 2021 scale bar; EA LIDAR | The plan's own 10 m scale bar sets the model scale; fitting the plan to the scan changed it by 0.3 % (scale 1.0032, rotation -0.21 degrees). |
| 12 | "Plan after Nash et al. 2021, CC BY 4.0 · Heights: Environment Agency LIDAR 2021, OGL v3.0 · Synthetic voice" | licences | See CREDITS.md. The narration is a text-to-speech voice (Kokoro). |

## Measured values

From the 2021 scan above the 2022 ground model, recomputed by the refuter from `stones.json`:
top of uprights without lintels 4.10 m (median); lintel tops 4.85 m (median); footprint of circle uprights 2.15 by 1.10 m (median, from the plan). Fit of plan to scan: of 206 scan points more than 2 m above ground, 171 lie within 0.3 m of an upright sarsen outline; the remaining 35 are mostly on lintels and tall bluestones (not checked point by point).

## Modelling choices (not measurements)

- Lintel thickness 0.75 m: the difference between the two medians above, not a direct measurement.
- Missing circle uprights stand at even 12-degree positions, with the median footprint and the median height.
- Ground flattened: heights are above local ground.
- Trilithon lintel thickness 1.05 m: lintel top of trilithon 51-52 minus the top of upright 60.
- The two fallen trilithon uprights (55, 59) are projected as mirror images of 56 and 52 across the solstice axis (Darvill 2022: the horseshoe sits symmetrically astride the axis).
- Bluestones the scan does not resolve (29 of 41 outlines read under 1 m) are drawn as low footprints. Missing bluestones are not projected: their original number is not agreed and no openly licensed plan of their sockets was available.

## Known disagreements between sources

- Fallen versus missing: Darvill 2022 counts seven fallen and six missing circle uprights (his Fig 4 shows 13, 15, 17, 18, 20 and 24 missing); Nash 2021 Fig 1B draws eight as fallen (8, 9, 12, 14, 15, 19, 25, 26) and five places empty. The difference is stone 15, a fragment. The film states only the number standing.
- Stone 2: Field 2015 reports it was judged not to need straightening and was set in concrete; EH Conservation says stones 29, 30, 1 and 2 were "straightened and set in concrete".

## Refutation record

First pass, 12 November 2026, by an independent agent instructed to refute every row, with access to the sources, the page scans and the model data. It found no wrong number. Changes made because of it:

| Was | Now | Why |
|---|---|---|
| "Thirty uprights made the outer circle." | "The outer circle most likely had thirty uprights." | English Heritage hedges twice; one author argued the circle was never finished. |
| "...and the lintels they carried." | "...and the missing lintels." | Many missing lintels sat on uprights that still stand. |
| "Thirteen were straightened, re-erected or set in concrete last century." (after the trilithon line) | "Thirteen of the seventeen were re-set or secured last century." (before the trilithon line) | The bare "thirteen" could be read as trilithon stones. |
| "White is stone that stands today." / "WHITE stands today" | "White is what survives today." / "WHITE survives today" | Fallen stones are drawn white and do not stand. |
| Darvill counts cited to p. 321 | p. 320 | Wrong page. |
| "28 of 41" bluestones unresolved | 29 of 41 | Miscount. |

Still open: the Environment Agency licence wording was confirmed from data.gov.uk metadata, not from the survey portal page itself; Field 2015's printed page number.

Second pass, 12 November 2026, by a fresh independent agent on the revised wording. It found no wrong number and re-derived the thirteen re-set or secured stones from the English Heritage research notes. Changes made because of it:

| Was | Now | Why |
|---|---|---|
| Legend "survives today · laser scan 2021" | "survives today · airborne laser scan 2021" | The 2021 data is the Environment Agency's airborne survey, not a ground scan of the stones. |
| Legend "inferred · built c. 2500 BC" | "inferred · sarsens set up c. 2500 BC" | The monument has phases from about 3000 BC; the date is for the sarsens. |

Noted and left as is: "17 of 30" on screen is unhedged, the voice says "most likely" as it appears. Two of the lintels shown in light survive on the ground. The Great Trilithon is complete because it was re-erected in 1958.

Script revised by the account owner, 12 November 2026 (rows 3 to 7 above show the new wording). "Engineers" in row 5: English Heritage (Conservation) describes the 1958-59 work as a "major engineering project", accepted by the Ministry of Works; the 1919-20 work was done for the Office of Works with excavations directed by William Hawley. "Still stand complete" in row 6 was chosen over "standing the test of time" because one of the three complete trilithons fell in 1797 and was re-erected in 1958.
