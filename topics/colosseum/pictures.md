# Colosseum film: picture notes

All files are in `data/colosseum/` (not in version control). Pixel boxes are [x0,y0,x1,y1] in the downloaded file's own pixels. Every file is upright, no rotation needed. Previews and 100% crops I inspected are in `data/colosseum/_preview/`.

Licence check: Met images were confirmed as `isPublicDomain: true` (Open Access, CC0) through the Met collection API. The Met HTML record pages answer 429 to curl, so the wording on the page itself was not read. Archive.org books: 1651 volume carries Public Domain Mark 1.0 on the item record; Middleton (1892) is public domain by age.

## Ranking (for this film)

1. **met_stjohn_1856_colosseum_287727.jpg** (3821x3005). Jane Martha St. John, "The Colosseum", 1856, albumen print from paper negative, Met acc. 2005.100.382 (68). The hero image. The piers of the arcades and the parapet bands are pitted with dark holes, readable at 100%.
   - Crop: [40,30,3790,2960].
   - Detail A, pier face covered in holes (dozens, in rows): [1550,1450,2350,2150].
   - Detail B, parapet band: dark pits and slots lined up along the horizontal block joints, under the pier above: [1450,1850,2350,2300]. This is the best place to say a hole sits at a joint.
   - Detail C, upper-tier piers with scattered holes, sky seen through arches: [1500,500,2300,1200].
   - Detail D, row of piers receding to the right: [2250,1450,3050,2150].
2. **met_jones_1846_colosseum_second_view_306254.jpg** (3364x2795). Calvert Richard Jones, May 1846, salted paper print, Met acc. 2013.159.34. The earliest and the most "archival" look, with a whole-building feel and a visible handwritten caption ("67. Colosseum ... Rome"), a man in a top hat in front. Holes show as rows of small dark dots on the broken outer wall; less crisp than St. John.
   - Crop: [150,90,3280,2570] (drops the mount edge and the caption strip).
   - Detail: rows of dots on the piers between arches, right of centre: [2300,1000,3100,1700].
3. **met_piranesi_1776_veduta_colosseo_360270.jpg** (3757x2638). Piranesi, bird's-eye view, 1776, etching, Met acc. 59.570.426. Whole-building opening. Crop [20,20,3740,2600] keeps the title legends at the bottom corners (drop them with y1=2330 if unwanted). The holes are not drawn as holes.
4. **met_piranesi_1748_anfiteatro_flavio_365360.jpg** (3994x2010). Piranesi, ca. 1748 etching, Met acc. 37.45.3(79). Exterior of the whole oval. Crop [40,50,3955,1840]. The etching has no readable holes, only a few dark flecks. Use as an alternative whole-building shot.
5. **met_unknown_1850s_colosseum_269024.jpg** (2778x3513). Unknown, 1850s, salted paper print, Met acc. 46.1.78. Frontal four-storey view. Holes only faint dots. Crop [150,130,2640,3400]. Works as a tall opening plate in vertical format; not for magnifying.
6. **met_constant_1848_52_colosseo_288424.jpg** (1743x1299). Eugene Constant, 1848-52, Met acc. 2005.100.799 (29). Below the 3000 px target; fallback only.

## Documents about the holes and clamps (text pages)

7. **suaresius1651_p4_colosseum_holes.jpg** (2500x3575). Suaresius, *Diatriba de foraminibus lapidum in priscis aedificiis*, Rome 1651, printed page 4. Latin text about the holes in the "Amphitheatrum Titi". Text crop [350,120,1300,3000]; the passage "Inferiores pilae, & arcus extima facie crebris foraminibus deformati sunt ..." starts at about y 700 and runs to about y 1180 (full-pixel estimate from the 1250 px preview: multiply by 2.0). Details: the quoted Donati sentence [380,1400,2400,2150]; the market-stall explanation [380,2250,2400,3000]. (Text-page boxes for items 7 to 9 are estimates from a downscaled view and were not checked at 100%; only the Middleton boxes were.)
8. **suaresius1651_p2_holes_question.jpg** (1724x2500). Printed page 2: people in Rome asked why the big squared Tiburtine stones of the amphitheatre are "pitted with frequent holes"; the author rejects the earthquake story. Page text block [430,150,1500,2100]. A "Digitized by Google" mark sits at lower right, outside this crop.
9. **suaresius1651_p6_gomphi_clamps.jpg** (2500x3581). Printed page 6. Passage on stones bound by iron clamps and lead ("De Gomphis, id est, clavis ferreis ..."). Text block [480,150,2300,3000]. It names clamps in general, not the Colosseum.
10. **middleton1892_vol2_p87_colosseum_clamps.jpg** (2391x3644). Middleton, *The Remains of Ancient Rome*, vol. 2, 1892, p. 87. Body sentence [200,560,2250,1250]: "The whole of the exterior of the Colosseum is of massive travertine ... each clamped to the next with heavy iron clamps, run with lead". Footnote 3 [180,2910,2250,3290]: "The numerous holes, which disfigure the arcades, were made during the early Middle Ages in attempts to extract the then valuable iron of the clamps". Clean, high-contrast text; the best "document" for the clamp claim.
11. **met_piranesi_1756_antichita_III_tav53_ferri_360365.jpg** (3857x3406). Piranesi, 1756-57. Iron hooks, lewis irons and lifting holes in travertine, for the Tomb of Caecilia Metella.

## What each can and cannot honestly be said to show

- St. John 1856 and Jones 1846: show that by the 1840s-50s the outer wall was already full of holes and gouges. They do not show a clamp, and from the photograph alone you cannot tell who dug the holes or when. They are dated by the Met as stated (1856; May 1846).
- Piranesi etchings: show the shape of the ruin in the 1740s and 1770s; they do not show the holes legibly, so do not magnify them as evidence of holes.
- Piranesi 1756 plate (item 11): the iron things are lifting tackle and the square holes are for lifting blocks. They are not joint clamps and not at the Colosseum. Calling them clamps would be wrong. I consider it risky even as a decoration; I would skip it.
- Suaresius 1651: shows that Romans were already asking about the holes in the 1600s. Page 4 reports several explanations (Goths, market-stall poles). The sentence about stealing the iron, bronze and lead that bound the stones sits near the end of the book (OCR line ~439 of 453) in a list of six possible causes, from Goths to builders to people who stripped the metal (in the OCR, the paragraph ending "Quin ab illis, qui ferrum, aes, plumbum, quibus lapides devincti erant, diripuerunt"), so the book does not settle on the clamp answer. Do not present Suaresius as proof of the clamp theory.
- Middleton 1892: the clearest statement that the clamps were iron set in lead and that the holes are from medieval extraction; it is one scholar's 1892 statement with no evidence on the page. Research.md should carry the modern evidence and dating.

## Recommended sequence (3 to 5 plates)

1. Piranesi 1776 bird's-eye (or the 1748 front view) for the opening: the whole building.
2. Jones 1846, then the loupe moves to the dotted piers.
3. St. John 1856 as the main magnification plate, in this order: Detail A (pier face), then Detail B (holes along a joint).
4. Middleton 1892 p. 87, loupe on the clamp sentence, then footnote 3 ("iron of the clamps").
5. Optional: Suaresius 1651 p. 4, for "people argued about the holes already in 1651".

## Gaps

- No image of an actual Roman iron clamp, a clamp cutting, or an engraved joint-clamp diagram. Searched: Met (public-domain Piranesi), Internet Archive (Middleton vol. 1 and 2 text only: no clamp figure found; Choisy 1873 and Durm not found in the archive search; Suaresius has no plates), Commons text search (nothing usable). Not searched at depth: Gallica (Choisy), LoC, Getty, Rijksmuseum, Cleveland.
- No modern CC0/CC BY close-up of the holes and no second monument with robbing holes (item D).
- No photograph in this set shows a hole at a joint between two clearly separate blocks with certainty; Detail B in St. John is the closest.
- Nothing by Macpherson, Anderson, Alinari, Sommer or Naya. Not found at the institutions searched.
