#!/usr/bin/env python3
"""
Normal-user query generator for the model-extraction-detection project.

Simulates legitimate users of a news-topic classifier API (World / Sports / Business / Sci-Tech).
Output schema is column-compatible with attacker_queries.csv (v2.0); the victim fields are left
EMPTY on purpose and must be filled from the real victim API (see replay_queries_to_api.py).

Usage:  python generate_normal_dataset.py [--out normal_queries.csv] [--attacker attacker_queries.csv]
"""
import argparse, csv, json, math, random, datetime as dt
from collections import Counter, defaultdict

SEED = 20261125
N_ROWS = 3000
WINDOW_START = dt.datetime(2026, 10, 1)   # same calendar window as the attacker data (Oct 1-12)
WINDOW_DAYS = 12

# ----------------------------------------------------------------------------- vocab
COUNTRIES = ["Brazil","Kenya","Japan","Germany","India","Nigeria","Canada","Egypt","Chile","Indonesia","Poland",
 "Turkey","Argentina","Vietnam","Norway","Pakistan","Mexico","Spain","Ghana","Thailand","Peru","Australia",
 "South Africa","Italy","Morocco","Bangladesh","Colombia","Sweden","Philippines","Ethiopia","Portugal","Greece",
 "Malaysia","Algeria","Hungary","Nepal","Ecuador","Tunisia","Romania","Jordan","Cambodia","Uruguay","Finland","Kazakhstan"]
CITIES = ["Lagos","Nairobi","Jakarta","Lima","Warsaw","Hanoi","Karachi","Toronto","Cairo","Santiago","Manila","Osaka",
 "Lyon","Accra","Dhaka","Bogota","Perth","Krakow","Porto","Casablanca","Addis Ababa","Chennai","Quito","Tunis","Bucharest",
 "Amman","Phnom Penh","Montevideo","Helsinki","Almaty","Medellin","Cebu","Rosario","Izmir","Gdansk","Kumasi","Mombasa","Surabaya","Pune","Valencia"]
DATELINES = ["LONDON","NAIROBI","TORONTO","SYDNEY","NEW DELHI","BERLIN","LAGOS","MADRID","SINGAPORE","SAO PAULO","CAIRO","TOKYO","MEXICO CITY","JAKARTA","NEW YORK","PARIS"]
WHEN = ["next week","on Monday","later this month","by the end of the year","within days","early next month","this weekend","in the spring","before the end of the quarter","next Thursday"]
DAYS = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
MONTHS = ["January","February","March","April","May","June","July","August","September","October","November","December"]
PEOPLE_COUNTS = ["120,000","250,000","400,000","60,000","85,000","1.2 million","300,000","45,000","700,000","90,000"]
FIRST = ["Marco","Tomas","Liam","Aiden","Rohan","Kenji","Samir","Luca","Oscar","Daniel","Mateo","Andre","Priya","Elena","Sofia",
 "Hana","Amara","Nadia","Ivana","Clara","Jonas","Felix","Tariq","Diego","Anya","Mei","Zainab","Pedro","Idris","Greta"]
LAST = ["Delgado","Okafor","Brandt","Nakamura","Petrov","Hughes","Moreau","Santos","Khan","Lindqvist","Adeyemi","Rossi",
 "Walker","Novak","Fischer","Tanaka","Costa","Haddad","Murphy","Silva","Kowalski","Mensah","Ibrahim","Varga","Larsen","Ortega","Chen","Bianchi"]
CLUB_PLACE = ["Riverton","Ashford","Northgate","Harborough","Stonebridge","Eastvale","Kingsmoor","Redcliffe","Lakeside","Fairhaven",
 "Westbury","Oakhurst","Brightwater","Silverton","Marlow","Thornbury","Greystone","Coldwater","Pinehurst","Ironbridge","Southmere","Dunmore"]
CLUB_NICK = ["United","Rovers","Wanderers","Hawks","Lions","Titans","Strikers","Knights","Raiders","Falcons","Comets","Giants","Rangers","Athletic"]
EVENTS = ["women's 5,000 metres","men's 200 metres","national marathon","regional swimming championships","indoor high jump",
 "open golf tournament","clay-court tennis final","cycling road race","national boxing title bout","rowing regatta","sprint hurdles"]
CO_PRE = ["Halden","Corvane","Meridian","Brightpath","Ostrand","Calder","Fenwick","Granton","Harlow","Ironwood","Jessup","Kestrel",
 "Larkin","Montrose","Norcross","Oakmont","Pemberton","Quillon","Rosemont","Sterling"]
CO_SUF = ["Foods","Motors","Energy","Pharma","Airlines","Retail","Bank","Logistics","Media","Holdings","Industries","Telecom","Insurance","Steel","Mining","Group"]
SECTORS = ["renewable power","logistics","consumer lending","packaged foods","online retail","medical devices","shipping"]
ORG_PRE = ["Nexora","Quantis","Helio","Verdant","Altair","Cobalt","Lumina","Vertex","Orbis","Kairo","Zephyr","Tessera","Aurora","Ionix",
 "Polaris","Sable","Novae","Brightwave","Arcadia","Stratus"]
ORG_SUF = ["Labs","Systems","Software","Networks","Robotics","Space","Computing","Technologies","Semiconductors","Cloud","Devices"]
PRODS = ["mobile browser","operating system","photo editor","messaging app","note-taking app","video player","password manager","maps app","email client","smart speaker app"]
BODIES = ["Mars","Venus","the Moon","Saturn","Jupiter"]
PLANTS = ["wheat","rice","sorghum","barley","maize","soybean"]
RES = ["4K","8K","120-frame-per-second","ray-traced"]

def title(s): return " ".join(w[:1].upper()+w[1:] for w in s.split())

def fill_slots(rng, anchor=None):
    s = {}
    s["C"], s["C2"] = rng.sample(COUNTRIES, 2)
    s["city"] = rng.choice(CITIES); s["when"] = rng.choice(WHEN); s["day"] = rng.choice(DAYS)
    s["n"] = rng.randint(2, 9); s["pct"] = rng.randint(3, 28); s["pct_s"] = round(rng.uniform(0.4, 6.9), 1)
    s["rate"] = round(rng.uniform(3.2, 9.4), 1); s["mag"] = round(rng.uniform(4.8, 7.4), 1)
    s["ppl"] = rng.choice(PEOPLE_COUNTS); s["month"] = rng.choice(MONTHS); s["year"] = rng.choice([2027, 2028, 2029])
    s["v1"] = rng.randint(120, 260); s["v2"] = rng.randint(40, s["v1"] - 30)
    a = rng.randint(1, 5); b = rng.randint(0, a - 1); s["a"], s["b"] = a, b
    s["pts"] = rng.randint(22, 48); s["cents"] = rng.randint(8, 65)
    p = rng.sample(CLUB_PLACE, 2)
    s["T1"], s["T2"] = [f"{x} {rng.choice(CLUB_NICK)}" for x in p]
    s["player"] = f"{rng.choice(FIRST)} {rng.choice(LAST)}"; s["coach"] = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
    s["event"] = rng.choice(EVENTS)
    c = rng.sample(CO_PRE, 2)
    s["Co"], s["Co2"] = f"{c[0]} {rng.choice(CO_SUF)}", f"{c[1]} {rng.choice(CO_SUF)}"
    s["person"] = f"{rng.choice(FIRST)} {rng.choice(LAST)}"; s["person2"] = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
    s["sector"] = rng.choice(SECTORS)
    amt = rng.choice([("%.1f" % rng.uniform(1.1, 9.8), "billion"), (str(rng.choice([150, 240, 380, 450, 620, 850])), "million")])
    s["big"] = f"${amt[0]} {amt[1]}"
    s["Org"] = f"{rng.choice(ORG_PRE)} {rng.choice(ORG_SUF)}"
    s["prod"] = rng.choice(PRODS); s["prod_t"] = title(s["prod"])
    s["ver"] = f"{rng.randint(2, 19)}.{rng.randint(0, 9)}"; s["nm"] = rng.choice([2, 3, 4, 5, 7])
    s["body"] = rng.choice(BODIES); s["plant"] = rng.choice(PLANTS); s["plant_t"] = s["plant"].capitalize()
    s["res"] = rng.choice(RES); s["nlang"] = rng.randint(10, 60); s["pcthi"] = rng.randint(70, 92)
    if anchor: s.update(anchor)
    return s

# ----------------------------------------------------------------------------- templates: (sentence, headline, keywords)
T = {}
T["world"] = [
 ("Foreign ministers from {C} and {C2} agreed to resume border talks {when}, officials said.","{C} And {C2} To Resume Border Talks","{C} {C2} border talks"),
 ("Election officials in {C} said turnout reached {pct}% in the first round of voting.","Turnout Hits {pct}% In {C} Election","{C} election turnout"),
 ("Rescue workers in {C} are searching for survivors after a magnitude {mag} earthquake struck near {city}.","Quake Of Magnitude {mag} Strikes Near {city}","{city} earthquake rescue"),
 ("Thousands of protesters gathered in {city} on {day} to demand changes to the pension law.","Thousands Protest Pension Law In {city}","{city} protest pension law"),
 ("The government of {C} announced new visa rules for visitors from {C2}, effective {when}.","{C} Tightens Visa Rules For {C2} Visitors","{C} visa rules {C2}"),
 ("A United Nations envoy visited {city} to discuss humanitarian access for about {ppl} displaced people.","UN Envoy Presses For Aid Access In {city}","UN envoy {city} aid"),
 ("Health officials in {C} confirmed {n}00 new cases of cholera and urged residents to boil drinking water.","{C} Reports Rise In Cholera Cases","{C} cholera outbreak"),
 ("Lawmakers in {C} voted {v1} to {v2} to approve a new climate agreement with {C2}.","{C} Parliament Backs Climate Pact With {C2}","{C} parliament climate agreement"),
 ("Trade negotiators from {C} and {C2} failed to reach a deal on agricultural tariffs after two days of talks in {city}.","Farm Tariff Talks Stall In {city}","{C} {C2} tariff talks"),
 ("Opposition leaders in {C} accused the government of delaying the release of official census figures.","Opposition In {C} Slams Census Delay","{C} census delay opposition"),
 ("Floodwaters displaced more than {ppl} residents in northern {C}, the national disaster agency said.","Floods Displace Thousands In {C}","{C} floods displaced"),
 ("The president of {C} will travel to {C2} {when} for a summit on regional security.","{C} Leader To Attend Security Summit In {C2}","{C} {C2} security summit"),
 ("Police in {city} detained {n}0 people after a demonstration outside the parliament turned violent.","{n}0 Detained After {city} Clashes","{city} clashes police detained"),
 ("{C} and {C2} signed a maritime agreement covering fishing rights and shipping lanes.","{C}, {C2} Sign Maritime Pact","{C} {C2} maritime agreement"),
 ("Aid agencies warned that drought in eastern {C} could leave {ppl} people short of food by autumn.","Drought Threatens Food Supplies In {C}","{C} drought food shortage"),
 ("Peacekeepers deployed near {city} reported that a fragile ceasefire was largely holding.","Ceasefire Holds Near {city}","{city} ceasefire peacekeepers"),
 ("Voters in {C} will go to the polls {when} to choose a new president after months of political uncertainty.","{C} Heads To Presidential Vote","{C} presidential vote"),
 ("The leaders of {C} and {C2} held phone talks on energy supplies and promised closer cooperation.","{C}, {C2} Leaders Discuss Energy Cooperation","{C} {C2} energy talks"),
 ("Border officials in {C} reopened a major crossing with {C2} after a closure of {n}0 days.","{C} Reopens Border Crossing With {C2}","{C} {C2} border crossing reopened"),
 ("A court in {city} sentenced a former transport minister to {n} years in prison over a bribery scheme.","Court In {city} Jails Former Minister","{city} court former minister bribery"),
 ("Diplomats from {C} said a prisoner exchange with {C2} had been completed without incident.","{C}, {C2} Complete Prisoner Swap","{C} {C2} prisoner exchange"),
 ("Refugee camps near {city} are running out of medical supplies, according to relief workers.","Camps Near {city} Short Of Medicines","{city} refugee camps medical supplies"),
]
T["sports"] = [
 ("{T1} beat {T2} {a}-{b} on {day} to move top of the table.","{T1} Down {T2} {a}-{b}","{T1} {T2} score"),
 ("{player} scored twice as {T1} came from behind to draw with {T2}.","{player} Double Rescues Point For {T1}","{player} {T1} draw {T2}"),
 ("{T1} have signed forward {player} on a {n}-year contract, the club announced.","{T1} Sign {player}","{T1} sign {player}"),
 ("Coach {coach} said {player} will miss {n} weeks with a hamstring injury.","{player} Out For {n} Weeks","{player} injury {n} weeks"),
 ("{T1} parted company with manager {coach} after a run of {n} straight defeats.","{T1} Sack {coach}","{T1} sack manager {coach}"),
 ("{player} won the {event} in a personal best and booked a place at next year's world championships.","{player} Wins {event}","{player} {event} win"),
 ("{T1} reached the final after a penalty shootout win over {T2}.","{T1} Edge {T2} On Penalties","{T1} {T2} penalties final"),
 ("The league fined {T1} after fans threw objects onto the field during the match against {T2}.","{T1} Fined Over Fan Behavior","{T1} fined fans {T2}"),
 ("{player} was handed a {n}-match ban for a dangerous tackle in the win over {T2}.","{player} Banned For {n} Matches","{player} ban {n} matches"),
 ("Defending champions {T1} were knocked out of the cup by lower-division {T2}.","Holders {T1} Stunned By {T2}","{T1} cup exit {T2}"),
 ("{T1} will host {T2} in the opening game of the season on {day}, organizers confirmed.","{T1} To Open Season Against {T2}","{T1} {T2} season opener"),
 ("{player} completed a hat-trick as {T1} thrashed {T2} {a}-{b}.","{player} Hat-Trick Sinks {T2}","{player} hat-trick {T1}"),
 ("Organizers said more than {ppl} tickets have been sold for the {T1} versus {T2} final.","Final Tickets Selling Fast As {T1} Meet {T2}","{T1} {T2} final tickets"),
 ("{coach} praised his side's defense after {T1} kept a fourth consecutive clean sheet against {T2}.","{T1} Keep Fourth Straight Clean Sheet","{T1} clean sheet {coach}"),
 ("{player} announced retirement after {n}0 seasons with {T1}.","{player} To Retire After {n}0 Seasons","{player} retires {T1}"),
 ("{T1} moved into the playoff places with a late {player} goal against {T2}.","Late {player} Strike Lifts {T1}","{T1} late goal {player}"),
 ("The national team squad for the qualifier against {C} includes {n} uncapped players, the coach said.","Squad Named For {C} Qualifier","{C} qualifier squad uncapped"),
 ("{T1} confirmed that {coach} has agreed a contract extension until {year}.","{coach} Extends Stay At {T1}","{coach} contract extension {T1}"),
 ("Heavy rain forced the postponement of {T1}'s home game against {T2} until {when}.","{T1}-{T2} Game Postponed","{T1} {T2} postponed rain"),
 ("{player} set a new season-best in the {event} in {city} on {day}.","{player} Shines At {city} Meet","{player} season best {city}"),
 ("{player} scored {pts} points in a narrow win for {T1} over {T2}.","{player} Drops {pts} In {T1} Win","{player} {pts} points {T1}"),
]
T["business"] = [
 ("{Co} reported quarterly profit up {pct}% on stronger demand in overseas markets.","{Co} Profit Jumps {pct}%","{Co} quarterly profit"),
 ("{Co} said it will cut {n}00 jobs as part of a plan to save {big} annually.","{Co} To Cut {n}00 Jobs","{Co} job cuts"),
 ("{Co} agreed to acquire {Co2} in a deal valued at {big}, subject to regulatory approval.","{Co} To Buy {Co2} For {big}","{Co} acquire {Co2}"),
 ("Shares of {Co} fell {pct}% after the company lowered its full-year outlook.","{Co} Shares Slide On Weak Outlook","{Co} shares fall outlook"),
 ("The central bank held interest rates steady on {day} but signaled that cuts could come later this year.","Central Bank Leaves Rates Unchanged","central bank rates steady {day}"),
 ("Oil prices rose {pct_s}% as traders weighed supply cuts from major producers.","Oil Climbs On Supply Worries","oil prices supply cuts"),
 ("Consumer prices in {C} rose {pct_s}% in the past year, slightly above economists' forecasts.","{C} Inflation Edges Up To {pct_s}%","{C} inflation {pct_s}%"),
 ("{Co} priced its initial public offering at the top of its range, valuing the company at {big}.","{Co} IPO Prices At Top Of Range","{Co} IPO"),
 ("Regulators in {C} opened a review of the proposed merger between {Co} and {Co2}.","{C} Regulators Probe {Co}-{Co2} Merger","{Co} {Co2} merger review"),
 ("Workers at a {Co} plant in {city} began a {n}-day strike over pay and shift schedules.","{Co} Workers Strike In {city}","{Co} strike {city}"),
 ("{Co} named {person} as chief executive, replacing {person2}, who retires at the end of the year.","{Co} Appoints New CEO","{Co} new CEO {person}"),
 ("The unemployment rate fell to {rate}% last month as employers added {n}0,000 jobs, government data showed.","Jobless Rate Falls To {rate}%","unemployment rate {rate}%"),
 ("{Co} will pay a quarterly dividend of {cents} cents a share, up from the previous payout.","{Co} Raises Dividend","{Co} dividend"),
 ("Retail sales in {C} grew {pct_s}% in the month, led by spending on electronics and travel.","{C} Retail Sales Rise {pct_s}%","{C} retail sales"),
 ("{Co} announced a {big} investment to build a new distribution center near {city}.","{Co} Plans {big} Distribution Hub","{Co} distribution center {city}"),
 ("Home prices in {city} climbed {pct}% over the past year, according to a new industry report.","{city} Home Prices Up {pct}%","{city} home prices"),
 ("{Co} said it will expand its network with {n} new routes next summer as demand recovers.","{Co} Expands With {n} New Routes","{Co} new routes"),
 ("The currency of {C} fell to its weakest level in {n} months against the dollar.","{C} Currency Hits {n}-Month Low","{C} currency dollar low"),
 ("{Co} recalled {n}0,000 units of its latest product line over a safety defect.","{Co} Recalls Products Over Defect","{Co} recall defect"),
 ("{Co} and {Co2} announced a joint venture to expand into {sector} in emerging markets.","{Co}, {Co2} Form Joint Venture","{Co} {Co2} joint venture"),
 ("Stocks ended mostly higher on {day} as investors cheered earnings from {Co} and other large companies.","Stocks Rise On Earnings Optimism","stocks higher earnings {Co}"),
 ("{Co} warned that higher input costs would squeeze margins in the second half.","{Co} Warns On Margins","{Co} margins warning"),
]
T["scitech"] = [
 ("{Org} released version {ver} of its {prod} with faster startup and improved battery life.","{Org} Ships {prod_t} {ver}","{Org} {prod} {ver}"),
 ("Security researchers found a flaw in the {prod} from {Org} that could let attackers take over devices.","Flaw Found In {Org} {prod_t}","{Org} {prod} vulnerability"),
 ("{Org} unveiled a {nm}-nanometer processor with {n}0 cores aimed at data centers.","{Org} Unveils {nm}nm Chip","{Org} {nm}nm processor"),
 ("A space probe launched by {Org} entered orbit around {body} after a seven-month journey.","{Org} Probe Reaches {body}","{Org} probe {body} orbit"),
 ("Astronomers using a new telescope reported a planet about {n} times the mass of Earth orbiting a nearby star.","Astronomers Spot Heavy Planet Near Neighboring Star","new planet telescope {n} earth masses"),
 ("{Org} said a ransomware attack disrupted its online services and that engineers were restoring systems.","{Org} Hit By Ransomware Attack","{Org} ransomware"),
 ("Researchers at {Org} trained a language model that matches larger systems while using {pct}% less energy.","{Org} Model Cuts Energy Use By {pct}%","{Org} language model energy"),
 ("Scientists sequenced the genome of a drought-resistant {plant}, a step toward hardier crops.","{plant_t} Genome Sequenced For Hardier Crops","{plant} genome drought"),
 ("{Org} demonstrated a solid-state battery that charges to {pcthi}% in under ten minutes.","{Org} Shows Fast-Charging Battery","{Org} solid-state battery"),
 ("Engineers at {Org} tested a quantum computer with {n}0 qubits and reported lower error rates.","{Org} Quantum Chip Reaches {n}0 Qubits","{Org} quantum {n}0 qubits"),
 ("{Org} began rolling out satellite internet service in {C}, promising speeds of up to {n}0 megabits per second.","{Org} Brings Satellite Internet To {C}","{Org} satellite internet {C}"),
 ("A data breach at {Org} exposed account details for about {ppl} users, the company said.","{Org} Confirms Data Breach","{Org} data breach"),
 ("{Org} announced that its next game console will support {res} graphics and ship {when}.","{Org} Details Next Console","{Org} console {res}"),
 ("Climate scientists said new satellite measurements show Arctic sea ice shrinking faster than models predicted in {month}.","Satellite Data Shows Faster Arctic Ice Loss","arctic sea ice satellite {month}"),
 ("{Org} open-sourced its robotics software, allowing developers to build on tools used in its warehouse robots.","{Org} Open-Sources Robotics Software","{Org} open source robotics"),
 ("Engineers at {Org} said a new recycling process recovers {pcthi}% of lithium from used batteries.","{Org} Recycling Method Recovers Lithium","{Org} lithium recycling"),
 ("The {Org} {prod} now supports on-device translation for {nlang} languages without an internet connection.","{Org} {prod_t} Adds Offline Translation","{Org} {prod} offline translation"),
 ("Researchers built a flexible sensor that can monitor air quality for {n} days on a single charge and send readings to a phone.","Flexible Air Sensor Debuts","flexible air quality sensor"),
 ("{Org} delayed the launch of its heavy-lift rocket after engineers found a fuel valve problem.","{Org} Postpones Rocket Launch","{Org} rocket launch delayed"),
 ("{Org} said its new chatbot feature will roll out to all {prod} users within {n} weeks.","{Org} Brings Chatbot To {prod_t}","{Org} chatbot {prod}"),
 ("Scientists at {Org} reported that a new gene-editing technique corrected a rare inherited disorder in mice.","Gene Editing Fixes Disorder In Mice","{Org} gene editing mice"),
 ("{Org} released a free browser extension that blocks {n}00 common tracking scripts.","{Org} Launches Anti-Tracking Extension","{Org} tracking blocker extension"),
]
D = {}
D["world"] = ["Officials said further discussions are planned in {city}.","The announcement followed weeks of pressure from regional neighbors.",
 "Residents described a tense but calm atmosphere in the capital.","Analysts said the decision could ease tensions between {C} and {C2}.",
 "International observers are expected to monitor the process closely.","The government has not released a full timetable.",
 "Humanitarian groups called for safe corridors for civilians.","Markets in {C} reacted cautiously to the news.","Local media reported that more than {n}00 people attended.",
 "A spokesperson declined to give further details.","The move comes ahead of a regional summit in {city}.","Critics said the plan does not go far enough.",
 "Schools in the area will remain closed until {when}.","Neighboring states have offered logistical support, officials added."]
D["sports"] = ["{coach} said the team would stay focused on the next fixture.","The result leaves {T1} two points clear with {n} games left.",
 "Fans stayed behind to applaud the players after the final whistle.","{player} left the field in the second half but returned to finish the game.",
 "The club said a full medical update will follow on {day}.","It was the team's {n}th win in their last ten outings.",
 "Officials reviewed the decision for several minutes before confirming it.","The stadium was close to full capacity despite the cold weather.",
 "{T2} had led at halftime but faded badly after the break.","The next round of fixtures begins {when}.",
 "Organizers said the event will be broadcast in more than {n}0 countries.","Sponsors have welcomed the news.","It is the youngest squad in the competition this year."]
D["business"] = ["Analysts had expected a smaller gain.","The company said it would update investors at its annual meeting.",
 "Investors reacted by pushing the stock {pct_s}% lower in early trading.","Executives cited supply chain pressures and higher energy costs.",
 "The deal is expected to close in the first half of next year.","The figures were released by the statistics office on {day}.",
 "Economists said the data pointed to a gradual slowdown.","The company employs about {n}00 people in {C}.",
 "Union representatives said they were seeking talks with management.","Bond yields moved little after the announcement.",
 "A spokesperson said the restructuring would be completed by the end of the year.","The currency market was calm after the decision.",
 "Some shareholders have called for a vote on executive pay.","The firm expects margins to recover next year."]
D["scitech"] = ["The update is available now and will reach other regions over the coming weeks.","The team plans to publish its full results in a peer-reviewed journal.",
 "Independent experts said the findings need to be replicated.","Users are advised to install the latest patch as soon as possible.",
 "The company said it has found no evidence that the flaw was exploited.","The prototype still needs testing outside the laboratory.",
 "The mission is expected to send back its first images next month.","Developers can try an early preview through a beta program.",
 "The technology could cut costs for small manufacturers.","The project was funded by a consortium of universities.",
 "Engineers said the next version should be {pct}% faster.","The announcement drew interest from developers and investors.",
 "The data will be shared with researchers worldwide.","The company will detail pricing {when}."]
Q = {
 "world": ["what's happening in {C} right now?","any update on the {C} and {C2} talks?","what's the latest from {city}?","why are people protesting in {city}?",
           "what did the {C} government just announce?","will {C} and {C2} reach a deal?","is the {C} election still on for {when}?"],
 "sports": ["did {T1} win last night?","what was the score between {T1} and {T2}?","is {player} injured?","who is {T1} playing next?","why did {T1} sack their manager?",
            "how did {T1} do this weekend?","is {player} still with {T1}?"],
 "business": ["why are {Co} shares down today?","is {Co} really buying {Co2}?","what happened to {Co}?","are interest rates going up in {C}?","is {Co} laying people off?",
              "how is the economy in {C} doing?","did {Co} beat earnings?"],
 "scitech": ["is the new {Org} update safe to install?","what did {Org} just announce?","has {Org} been hacked?","what's new with the {Org} {prod}?",
             "did {Org} launch the rocket yet?","what is {Org} working on?","is the {Org} {prod} worth updating?"]}
ANCHOR_KEYS = {"world": ["C"], "sports": ["T1"], "business": ["Co"], "scitech": ["Org"]}
CATS = ["world", "sports", "business", "scitech"]

OFF = ["hello","hi there","test","testing 123","asdfgh","what can you do","how accurate are you","what's the weather like in {city} tomorrow",
 "recipe for banana bread","write me a short poem about autumn","translate good morning into french","best laptop under {n}00 dollars","how do I reset my password",
 "convert {n}0 miles to kilometers","tell me a joke","how many words is this","what is {pct} percent of 240","give me a workout plan","explain photosynthesis simply",
 "movie recommendations for tonight","how to tie a tie","is this thing working","good morning","summarize the plot of a famous novel","random fact please"]

# ----------------------------------------------------------------------------- personas
H_EVE = [(7,2),(8,3),(12,3),(13,2),(18,3),(19,4),(20,5),(21,5),(22,3),(23,1)]
H_COMMUTE = [(6,2),(7,5),(8,5),(9,2),(12,4),(13,3),(17,3),(18,4),(19,3),(21,2)]
H_AFT = [(10,2),(11,2),(14,4),(15,5),(16,4),(17,3),(20,3),(21,4),(22,4),(23,3)]
H_WORK = [(8,2),(9,6),(10,6),(11,5),(12,2),(13,3),(14,6),(15,6),(16,5),(17,3)]
H_ANY = [(h,1) for h in range(24)]
STYLES = ["headline","sentence","two_sent","dateline","question","keywords","casual","paragraph"]
PERSONAS = {
 # name: users, sessions/user, queries/session (median, sigma, lo, hi), style weights, gap median s / sigma, stickiness, probs
 "casual_reader": dict(users=40, sess=(1,3), q=(2.5,.6,1,7),  sw=[.15,.20,.05,.02,.20,.15,.20,.03], gap=(45,.9), stick=.80, p_rep=.02, p_reph=.08, p_fol=.15, p_trend=.30, p_off=.04, typo=.12, hours=H_EVE, wk=1.3),
 "news_app_user": dict(users=30, sess=(3,6), q=(6,.5,3,14),   sw=[.40,.25,.15,.10,.02,.03,.02,.03], gap=(18,.8), stick=.55, p_rep=.01, p_reph=.03, p_fol=.20, p_trend=.30, p_off=.00, typo=.03, hours=H_COMMUTE, wk=1.0),
 "student_researcher": dict(users=20, sess=(3,5), q=(8,.5,3,20), sw=[.12,.20,.20,.05,.12,.10,.06,.15], gap=(35,.9), stick=.75, p_rep=.03, p_reph=.18, p_fol=.20, p_trend=.08, p_off=.02, typo=.06, hours=H_AFT, wk=1.0),
 "journalist_editor":  dict(users=12, sess=(3,6), q=(12,.5,5,28),sw=[.10,.10,.25,.15,.00,.02,.00,.38], gap=(28,.8), stick=.35, p_rep=.02, p_reph=.10, p_fol=.15, p_trend=.15, p_off=.00, typo=.02, hours=H_WORK, wk=.1),
 "analyst_batch_user": dict(users=5, sess=(4,6), q=(18,.35,10,32),sw=[.25,.20,.25,.10,.00,.05,.00,.15], gap=(6,.5), stick=.40, p_rep=.02, p_reph=.04, p_fol=.10, p_trend=.05, p_off=.00, typo=.01, hours=H_WORK, wk=.1),
 "curious_tester":     dict(users=8,  sess=(1,3), q=(2,.5,1,5),   sw=[.20,.20,.10,.00,.15,.15,.20,.00], gap=(12,1.0), stick=.30, p_rep=.06, p_reph=.05, p_fol=.05, p_trend=.05, p_off=.40, typo=.10, hours=H_ANY, wk=1.0),
}

# ----------------------------------------------------------------------------- rendering
def fmt(t, s): return t.format(**s)
def cap(x): return x[:1].upper() + x[1:]

def new_event(rng, cat, anchor=None, avoid_t=None):
    s = fill_slots(rng, anchor)
    idxs = [i for i in range(len(T[cat])) if i != avoid_t]
    return {"cat": cat, "t": rng.choice(idxs), "s": s}

def render(rng, ev, style):
    cat, ti, s = ev["cat"], ev["t"], ev["s"]
    sent, head, kw = (fmt(x, s) for x in T[cat][ti])
    det = lambda: cap(fmt(rng.choice(D[cat]), s))
    if style == "headline": return head
    if style == "sentence": return cap(sent)
    if style == "two_sent": return f"{cap(sent)} {det()}"
    if style == "dateline": return f"{rng.choice(DATELINES)} - {cap(sent)}"
    if style == "keywords": return (kw + " " + rng.choice(["", "", "news", "latest", "today", "update"])).strip().lower()
    if style == "question": return fmt(rng.choice(Q[cat]), s)
    if style == "casual":
        base = rng.choice([sent, head]).lower().rstrip(".")
        if rng.random() < .5: base = base.replace(",", "")
        return (rng.choice(["", "", "so ", "just saw: ", "is it true that ", "heard that ", "ok so ", "news: ", "read this earlier - "]) + base).strip()
    if style == "paragraph":
        other = fmt(T[cat][rng.choice([i for i in range(len(T[cat])) if i != ti])][0], s)
        parts = [cap(sent), det(), cap(other)] + ([det()] if rng.random() < .6 else [])
        return " ".join(parts)
    raise ValueError(style)

def typo(rng, text):
    w = text.split(" ")
    cand = [i for i, x in enumerate(w) if len(x) >= 5 and x.isalpha()]
    if not cand: return text
    for i in rng.sample(cand, min(len(cand), rng.choice([1, 1, 2]))):
        x = w[i]; k = rng.randint(1, len(x) - 2); op = rng.choice(["swap", "drop", "dup"])
        w[i] = (x[:k] + x[k+1] + x[k] + x[k+2:] if op == "swap" else x[:k] + x[k+1:] if op == "drop" else x[:k] + x[k] + x[k:])
    return " ".join(w)

def off_topic(rng):
    return fmt(rng.choice(OFF), fill_slots(rng)) + rng.choice(["", "", " please", "?"])

# ----------------------------------------------------------------------------- sessions
def make_trending(seed):
    r = random.Random(seed + 1); out = {}
    for d in range(WINDOW_DAYS + 2):
        out[d] = [new_event(r, c) for c in CATS for _ in range(2)]
    return out

def make_session(rng, P, trending, day):
    lo_, hi_ = P["q"][2], P["q"][3]
    n = max(lo_, min(hi_, int(round(rng.lognormvariate(math.log(P["q"][0]), P["q"][1])))))
    primary = rng.choice(CATS); queries, gaps = [], []
    prev_ev = prev_style = last_text = None
    for i in range(n):
        cat = primary if rng.random() < P["stick"] else rng.choice(CATS)
        intent, ev, style = "fresh_query", None, None
        r = rng.random()
        if i > 0 and r < P["p_rep"]:
            intent, text = "repeat", last_text
        elif i > 0 and prev_ev is not None and r < P["p_rep"] + P["p_reph"]:
            intent = "rephrase"; ev = prev_ev
            style = rng.choices([s for s in STYLES if s != prev_style], [w for s, w in zip(STYLES, P["sw"]) if s != prev_style])[0] if sum(P["sw"]) else "sentence"
        elif i > 0 and prev_ev is not None and r < P["p_rep"] + P["p_reph"] + P["p_fol"]:
            intent = "follow_up"; ev = new_event(rng, prev_ev["cat"], {k: prev_ev["s"][k] for k in ANCHOR_KEYS[prev_ev["cat"]]}, prev_ev["t"])
        elif rng.random() < P["p_trend"]:
            intent = "trending"; ev = rng.choice(trending[day])
        elif rng.random() < P["p_off"]:
            intent = "off_topic"
        else:
            ev = new_event(rng, cat)
        if intent == "off_topic":
            text, cat_out = off_topic(rng), "off_topic"
            if rng.random() < P["typo"]: text = typo(rng, text)
            prev_ev = None
        elif intent == "repeat":
            cat_out = queries[-1]["topic"]
        else:
            style = style or rng.choices(STYLES, P["sw"])[0]
            text = render(rng, ev, style)
            if rng.random() < P["typo"]: text = typo(rng, text)
            cat_out = ev["cat"]; prev_ev, prev_style = ev, style
        last_text = text
        queries.append({"text": text, "intent": intent, "topic": cat_out})
        if i > 0:
            g = rng.lognormvariate(math.log(P["gap"][0]), P["gap"][1])
            if intent == "rephrase": g *= .5
            if rng.random() < .05: g += rng.uniform(180, 720)
            gaps.append(max(1, int(round(g))))
    return {"queries": queries, "gaps": gaps}

def build(seed, attacker_path=None):
    rng = random.Random(seed); trending = make_trending(seed)
    plist = [p for p, P in PERSONAS.items() for _ in range(P["users"])]
    rng.shuffle(plist)
    users = []
    for i, p in enumerate(plist):
        users.append({"uid": f"client_{101+i}", "persona": p, "sessions": []})

    def pick_day(P):
        w = [(P["wk"] if (WINDOW_START + dt.timedelta(days=d)).weekday() >= 5 else 1.0) for d in range(WINDOW_DAYS)]
        return rng.choices(range(WINDOW_DAYS), w)[0]
    def add_session(u):
        P = PERSONAS[u["persona"]]; day = pick_day(P)
        h = rng.choices([h for h, _ in P["hours"]], [w for _, w in P["hours"]])[0]
        start = WINDOW_START + dt.timedelta(days=day, hours=h, minutes=rng.randint(0, 59), seconds=rng.randint(0, 59))
        ses = make_session(rng, P, trending, day); ses["start"] = start; u["sessions"].append(ses)

    for u in users:
        for _ in range(rng.randint(*PERSONAS[u["persona"]]["sess"])): add_session(u)
    total = lambda: sum(len(s["queries"]) for u in users for s in u["sessions"])
    growable = [u for u in users if u["persona"] != "curious_tester"]
    while total() < N_ROWS + 60: add_session(rng.choice(growable))
    # trim random session tails (keeps >=1 query/session) until exactly N_ROWS
    while total() > N_ROWS:
        u = rng.choice(users)
        if not u["sessions"]: continue
        s = rng.choice(u["sessions"])
        if len(s["queries"]) > 1: s["queries"].pop(); s["gaps"].pop()

    rows = []
    for u in users:
        u["sessions"].sort(key=lambda s: s["start"]); prev_end = None
        for k, s in enumerate(u["sessions"], 1):
            if prev_end and s["start"] < prev_end + dt.timedelta(minutes=45):
                s["start"] = prev_end + dt.timedelta(minutes=45 + rng.randint(0, 120))
            t = s["start"]
            for j, q in enumerate(s["queries"]):
                if j > 0: t += dt.timedelta(seconds=s["gaps"][j - 1])
                rows.append({"user_id": u["uid"], "session_id": f"session_{u['uid'][7:]}_{k:02d}", "ts": t,
                             "input_text": q["text"], "user_profile": u["persona"], "query_intent": q["intent"], "intended_topic": q["topic"]})
            prev_end = t
    rows.sort(key=lambda r: (r["ts"], r["user_id"]))
    for i, r in enumerate(rows, 1):
        r.update(query_id=f"q_{100000+i}", request_timestamp=r["ts"].strftime("%Y-%m-%dT%H:%M:%SZ"), attack_strategy="none",
                 label="normal", sequence_index=i, generation_seed=seed, victim_prediction="", victim_confidence_scores="")
    return rows

COLS = ["query_id","user_id","session_id","request_timestamp","input_text","attack_strategy","label","sequence_index","generation_seed",
        "victim_prediction","victim_confidence_scores","user_profile","query_intent","intended_topic"]

def summarize(rows, attacker_path):
    import statistics as st, re
    n = len(rows); texts = [r["input_text"] for r in rows]
    sess = defaultdict(list)
    for r in rows: sess[r["session_id"]].append(r)
    sizes = [len(v) for v in sess.values()]
    gaps = []
    for v in sess.values():
        ts = [x["ts"] for x in v]; gaps += [(b - a).total_seconds() for a, b in zip(ts, ts[1:])]
    wl = [len(t.split()) for t in texts]
    out = {
        "records": n, "users": len({r["user_id"] for r in rows}), "sessions": len(sess),
        "rows_by_profile": dict(Counter(r["user_profile"] for r in rows)),
        "users_by_profile": {p: len({r["user_id"] for r in rows if r["user_profile"] == p}) for p in PERSONAS},
        "query_intent_counts": dict(Counter(r["query_intent"] for r in rows)),
        "intended_topic_counts": dict(Counter(r["intended_topic"] for r in rows)),
        "unique_input_texts": len(set(texts)),
        "queries_per_session": {"min": min(sizes), "median": st.median(sizes), "mean": round(st.mean(sizes), 2), "max": max(sizes)},
        "inter_query_gap_seconds": {"median": st.median(gaps), "p10": sorted(gaps)[int(.1*len(gaps))], "p90": sorted(gaps)[int(.9*len(gaps))]},
        "words_per_query": {"min": min(wl), "median": st.median(wl), "mean": round(st.mean(wl), 1), "max": max(wl)},
        "first_timestamp": min(r["request_timestamp"] for r in rows), "last_timestamp": max(r["request_timestamp"] for r in rows),
    }
    if attacker_path:
        import pandas as pd
        a = pd.read_csv(attacker_path)
        split = lambda t: {x.strip().lower() for x in re.split(r"(?<=[.?!])\s+", t) if len(x.strip()) > 25}
        a_sent = set().union(*[split(t) for t in a.input_text]); n_sent = set().union(*[split(t) for t in texts])
        out["overlap_with_attacker"] = {"exact_text_matches": len(set(texts) & set(a.input_text)), "shared_sentences": len(a_sent & n_sent)}
    return out

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="normal_queries.csv"); ap.add_argument("--attacker", default=None)
    ap.add_argument("--stats", default="normal_dataset_stats.json"); ap.add_argument("--seed", type=int, default=SEED)
    a = ap.parse_args()
    rows = build(a.seed)
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    stats = summarize(rows, a.attacker)
    json.dump(stats, open(a.stats, "w"), indent=2); print(json.dumps(stats, indent=2))
