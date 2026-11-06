# Reading use labels off 1904 Sanborn map crops

Each crop is a 190 m square piece of a 1904 Sanborn fire-insurance map (Cincinnati), rendered at 4 px per metre (760 x 760 px), in grey.
A light red grid is drawn every 25 m, labelled in metres from the TOP-LEFT corner: x to the right, y DOWN (0 to 190).
A blue box marks the crop's core, 20 m to 170 m on both axes. Neighbouring crops overlap, so report a label ONLY if its centre is inside the blue box.

## What to report

Every printed label on a building or yard that names its USE or the business or institution in it, for example:
CHURCH, CHAPEL, MISSION, CONVENT, PARSONAGE, SYNAGOGUE / TEMPLE; SCHOOL, PUBLIC SCHOOL, COLLEGE, SEMINARY; HALL (Turner Hall, Music Hall, lodge or society hall), HOSPITAL, ASYLUM, ORPHANS HOME, ENGINE HOUSE / ENGINE CO. (fire), POLICE STATION, MARKET HOUSE, LIBRARY, BATH HOUSE;
STORE / STORES (spelled out), OFFICE / OFF., SALOON / SAL., HOTEL, BANK, THEATRE, RESTAURANT, BAKERY, GARAGE, LIVERY, a named business's STABLES (e.g. "Kroger Gro. & Baking Co's Stables"), TAILOR SHOP, BARBER, PRINTING;
FACTORY / FACT'Y, WORKS, MFG., any "... CO." company name, MILL, FOUNDRY, MACHINE SHOP, BLACKSMITH, CARPENTER SHOP, PAINT SHOP, PLANING MILL, BREWERY, MALT HOUSE, DISTILLERY, PACKING HOUSE, LAUNDRY, WAREHOUSE / W. HO., a business's STORAGE (e.g. "Furniture Storage"), LUMBER YARD, COAL YARD, ICE HOUSE, TANNERY, CARRIAGE or WAGON SHOP / REPOSITORY.

Do NOT report: street and alley names, house numbers, lot or block numbers, sheet notes, construction codes (single letters D, S, F, B, numbers like 2, 2 1/2, the x of a skylight), "Shed", "Private", "Coal" or "Wash house", "Privy", or a plain "Stable" or "Shed" behind a dwelling. Single letters S (store) and D (dwelling) are NOT reported.

## Use classes

- religious: churches, chapels, missions, convents, parsonages, synagogues.
- civic: schools, colleges, halls, hospitals, asylums, homes, fire engine houses, police, market houses, libraries, bath houses.
- commercial: stores, offices, saloons, hotels, banks, theatres, restaurants, bakeries, garages, livery and business stables, tailor and barber shops, printing.
- industrial: factories, works, mfg., named companies making or storing goods, mills, foundries, machine/blacksmith/carpenter/paint shops, breweries, malt houses, distilleries, packing houses, laundries, warehouses and business storage, lumber/coal yards, ice houses, tanneries, carriage and wagon shops.

## Position

Give the centre of the label text in crop metres, read off the grid (x right, y down), to about 2 m. Rotated text is common; read it anyway.

## Output

You are given a list of crop ids. For each, open `crops/<id>.png` (with the Read tool) in the directory
`data/sanborn/plots/`.
Write ALL your results to the JSON file you are told, as one list of objects:

    [{"crop": "c0300", "text": "1st German Presb. Church", "use": "religious", "x": 52, "y": 176}, ...]

Rewrite the whole file after every 5 crops (so nothing is lost), and once more at the end. A crop with nothing to report adds nothing.
Keep the printed wording (abbreviations as printed). Be thorough: read every crop at full size, including small lettering inside buildings.
When finished, reply with one line: how many crops you read and how many labels you wrote.
