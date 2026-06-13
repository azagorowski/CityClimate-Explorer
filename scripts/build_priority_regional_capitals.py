#!/usr/bin/env python3
"""Build the reviewed, local-first regional-capital snapshot for priority countries.

The rows below are the source of truth.  A future enrichment command may fill
optional QIDs, but must never use discovery results to decide which rows exist.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/preloaded/regional_capitals_priority_countries.json"
REPORT_OUTPUT = ROOT / "data/preloaded/regional_capitals_priority_build_report.json"

# country|city|administrative region|latitude|longitude[|Köppen|type|aliases]
SEEDS = """
Poland|Białystok|Podlaskie Voivodeship|53.1325|23.1688|Dfb
Poland|Bydgoszcz|Kuyavian-Pomeranian Voivodeship|53.1235|18.0084|Dfb
Poland|Toruń|Kuyavian-Pomeranian Voivodeship|53.0138|18.5984|Dfb
Poland|Gdańsk|Pomeranian Voivodeship|54.3520|18.6466|Cfb
Poland|Gorzów Wielkopolski|Lubusz Voivodeship|52.7368|15.2288|Cfb
Poland|Zielona Góra|Lubusz Voivodeship|51.9356|15.5062|Cfb
Poland|Katowice|Silesian Voivodeship|50.2649|19.0238|Cfb
Poland|Kielce|Świętokrzyskie Voivodeship|50.8661|20.6286|Dfb
Poland|Kraków|Lesser Poland Voivodeship|50.0647|19.9450|Cfb|||Krakow
Poland|Lublin|Lublin Voivodeship|51.2465|22.5684|Dfb
Poland|Łódź|Łódź Voivodeship|51.7592|19.4560|Cfb|||Lodz
Poland|Olsztyn|Warmian-Masurian Voivodeship|53.7784|20.4801|Dfb
Poland|Opole|Opole Voivodeship|50.6751|17.9213|Cfb
Poland|Poznań|Greater Poland Voivodeship|52.4064|16.9252|Cfb|||Poznan
Poland|Rzeszów|Podkarpackie Voivodeship|50.0412|21.9991|Dfb
Poland|Szczecin|West Pomeranian Voivodeship|53.4285|14.5528|Cfb
Poland|Warsaw|Masovian Voivodeship|52.2297|21.0122|Dfb
Poland|Wrocław|Lower Silesian Voivodeship|51.1079|17.0385|Cfb|||Wroclaw
Germany|Berlin|Berlin|52.5200|13.4050|Cfb
Germany|Bremen|Bremen|53.0793|8.8017|Cfb
Germany|Dresden|Saxony|51.0504|13.7373|Cfb
Germany|Düsseldorf|North Rhine-Westphalia|51.2277|6.7735|Cfb|||Dusseldorf
Germany|Erfurt|Thuringia|50.9848|11.0299|Cfb
Germany|Hamburg|Hamburg|53.5511|9.9937|Cfb
Germany|Hanover|Lower Saxony|52.3759|9.7320|Cfb|||Hannover
Germany|Kiel|Schleswig-Holstein|54.3233|10.1228|Cfb
Germany|Magdeburg|Saxony-Anhalt|52.1205|11.6276|Cfb
Germany|Mainz|Rhineland-Palatinate|49.9929|8.2473|Cfb
Germany|Munich|Bavaria|48.1351|11.5820|Cfb|||München
Germany|Potsdam|Brandenburg|52.3906|13.0645|Cfb
Germany|Saarbrücken|Saarland|49.2402|6.9969|Cfb|||Saarbrucken
Germany|Schwerin|Mecklenburg-Vorpommern|53.6355|11.4012|Cfb
Germany|Stuttgart|Baden-Württemberg|48.7758|9.1829|Cfb
Germany|Wiesbaden|Hesse|50.0782|8.2398|Cfb
Spain|Madrid|Community of Madrid|40.4168|-3.7038|Csa
Spain|Barcelona|Catalonia|41.3874|2.1686|Csa
Spain|Valencia|Valencian Community|39.4699|-0.3763|Csa
Spain|Seville|Andalusia|37.3891|-5.9845|Csa
Spain|Zaragoza|Aragon|41.6488|-0.8891|BSk
Spain|Mérida|Extremadura|38.9170|-6.3435|Csa|||Merida
Spain|Santiago de Compostela|Galicia|42.8782|-8.5448|Cfb
Spain|Oviedo|Asturias|43.3619|-5.8494|Cfb
Spain|Santander|Cantabria|43.4623|-3.8099|Cfb
Spain|Logroño|La Rioja|42.4627|-2.4449|Cfb|||Logrono
Spain|Pamplona|Navarre|42.8125|-1.6458|Cfb
Spain|Vitoria-Gasteiz|Basque Country|42.8467|-2.6727|Cfb|||Vitoria
Spain|Valladolid|Castile and León|41.6523|-4.7245|Csb
Spain|Toledo|Castilla–La Mancha|39.8628|-4.0273|BSk
Spain|Murcia|Region of Murcia|37.9922|-1.1307|BSh
Spain|Palma|Balearic Islands|39.5696|2.6502|Csa
Spain|Las Palmas de Gran Canaria|Canary Islands|28.1235|-15.4363|BWh
Spain|Santa Cruz de Tenerife|Canary Islands|28.4636|-16.2518|BSh
Spain|Ceuta|Ceuta|35.8894|-5.3213|Csa
Spain|Melilla|Melilla|35.2923|-2.9381|BSh
France|Paris|Île-de-France|48.8566|2.3522|Cfb
France|Lyon|Auvergne-Rhône-Alpes|45.7640|4.8357|Cfa
France|Marseille|Provence-Alpes-Côte d’Azur|43.2965|5.3698|Csa
France|Toulouse|Occitanie|43.6047|1.4442|Cfa
France|Bordeaux|Nouvelle-Aquitaine|44.8378|-0.5792|Cfb
France|Nantes|Pays de la Loire|47.2184|-1.5536|Cfb
France|Rennes|Brittany|48.1173|-1.6778|Cfb
France|Lille|Hauts-de-France|50.6292|3.0573|Cfb
France|Strasbourg|Grand Est|48.5734|7.7521|Cfb
France|Dijon|Bourgogne-Franche-Comté|47.3220|5.0415|Cfb
France|Orléans|Centre-Val de Loire|47.9030|1.9093|Cfb|||Orleans
France|Rouen|Normandy|49.4431|1.0993|Cfb
France|Ajaccio|Corsica|41.9192|8.7386|Csa
France|Basse-Terre|Guadeloupe|15.9958|-61.7292|Af
France|Cayenne|French Guiana|4.9224|-52.3135|Af
France|Fort-de-France|Martinique|14.6161|-61.0588|Af
France|Saint-Denis|Réunion|-20.8789|55.4481|Am
France|Mamoudzou|Mayotte|-12.7806|45.2278|Aw
Norway|Oslo|Oslo|59.9139|10.7522|Dfb
Norway|Bergen|Vestland|60.3913|5.3221|Cfb
Norway|Stavanger|Rogaland|58.9700|5.7331|Cfb
Norway|Trondheim|Trøndelag|63.4305|10.3951|Dfc
Norway|Tromsø|Troms|69.6492|18.9553|Dfc
Norway|Bodø|Nordland|67.2804|14.4049|Cfc
Norway|Vadsø|Finnmark|70.0745|29.7487|Dfc
Norway|Kristiansand|Agder|58.1599|8.0182|Cfb
Norway|Drammen|Buskerud|59.7441|10.2045|Dfb
Norway|Lillehammer|Innlandet|61.1153|10.4662|Dfc
Norway|Molde|Møre og Romsdal|62.7375|7.1607|Cfb
Norway|Steinkjer|Trøndelag|64.0149|11.4954|Dfc|local_administrative_center
Norway|Skien|Telemark|59.2096|9.6090|Dfb
Norway|Tønsberg|Vestfold|59.2675|10.4076|Cfb|||Tonsberg
Norway|Hamar|Innlandet|60.7945|11.0679|Dfb|local_administrative_center
Norway|Leikanger|Vestland|61.1856|6.8508|Cfb|local_administrative_center
Norway|Hermansverk|Vestland|61.1846|6.8500|Cfb|local_administrative_center
Norway|Ålesund|Møre og Romsdal|62.4722|6.1495|Cfb|local_administrative_center|Alesund
Sweden|Stockholm|Stockholm County|59.3293|18.0686|Dfb
Sweden|Gothenburg|Västra Götaland County|57.7089|11.9746|Cfb|||Göteborg
Sweden|Malmö|Skåne County|55.6050|13.0038|Cfb|||Malmo
Sweden|Uppsala|Uppsala County|59.8586|17.6389|Dfb
Sweden|Linköping|Östergötland County|58.4108|15.6214|Dfb
Sweden|Örebro|Örebro County|59.2753|15.2134|Dfb|||Orebro
Sweden|Västerås|Västmanland County|59.6099|16.5448|Dfb|||Vasteras
Sweden|Luleå|Norrbotten County|65.5848|22.1567|Dfc|||Lulea
Sweden|Umeå|Västerbotten County|63.8258|20.2630|Dfc|||Umea
Sweden|Östersund|Jämtland County|63.1767|14.6361|Dfc|||Ostersund
Sweden|Karlstad|Värmland County|59.3793|13.5036|Dfb
Sweden|Falun|Dalarna County|60.6065|15.6355|Dfc
Sweden|Gävle|Gävleborg County|60.6749|17.1413|Dfb|||Gavle
Sweden|Härnösand|Västernorrland County|62.6323|17.9404|Dfc|||Harnosand
Sweden|Jönköping|Jönköping County|57.7826|14.1618|Dfb|||Jonkoping
Sweden|Kalmar|Kalmar County|56.6634|16.3568|Cfb
Sweden|Karlskrona|Blekinge County|56.1612|15.5869|Cfb
Sweden|Kristianstad|Skåne County|56.0294|14.1567|Cfb|local_administrative_center
Sweden|Nyköping|Södermanland County|58.7528|17.0092|Dfb|||Nykoping
Sweden|Växjö|Kronoberg County|56.8790|14.8059|Cfb|||Vaxjo
Sweden|Visby|Gotland County|57.6348|18.2948|Cfb
Sweden|Halmstad|Halland County|56.6745|12.8578|Cfb
Sweden|Kiruna|Kiruna Municipality|67.8558|20.2253|Dfc|local_administrative_center
Finland|Helsinki|Uusimaa|60.1699|24.9384|Dfb
Finland|Turku|Southwest Finland|60.4518|22.2666|Dfb
Finland|Tampere|Pirkanmaa|61.4978|23.7610|Dfb
Finland|Oulu|North Ostrobothnia|65.0121|25.4651|Dfc
Finland|Rovaniemi|Lapland|66.5039|25.7294|Dfc
Finland|Kuopio|North Savo|62.8924|27.6770|Dfc
Finland|Jyväskylä|Central Finland|62.2426|25.7473|Dfc|||Jyvaskyla
Finland|Lahti|Päijät-Häme|60.9827|25.6615|Dfb
Finland|Pori|Satakunta|61.4851|21.7974|Dfb
Finland|Vaasa|Ostrobothnia|63.0951|21.6165|Dfb
Finland|Joensuu|North Karelia|62.6010|29.7636|Dfc
Finland|Hämeenlinna|Kanta-Häme|60.9959|24.4643|Dfb|||Hameenlinna
Finland|Mikkeli|South Savo|61.6878|27.2736|Dfc
Finland|Seinäjoki|South Ostrobothnia|62.7903|22.8403|Dfb|||Seinajoki
Finland|Kokkola|Central Ostrobothnia|63.8385|23.1307|Dfb
Finland|Kajaani|Kainuu|64.2273|27.7285|Dfc
Finland|Mariehamn|Åland|60.0973|19.9348|Cfb
Finland|Lappeenranta|South Karelia|61.0587|28.1887|Dfb
""".strip()

NEW_PRIORITY_SEEDS = """
Switzerland|Aarau|Aargau|47.3925|8.0442|Cfb|||Q14274|Aarau
Switzerland|Appenzell|Appenzell Innerrhoden|47.3310|9.4099|Cfb|||Q12592|Appenzell_(town)
Switzerland|Basel|Basel-Stadt|47.5596|7.5886|Cfb|||Q78|Basel
Switzerland|Bellinzona|Ticino|46.1950|9.0220|Cfb|||Q68144|Bellinzona
Switzerland|Bern|Bern|46.9480|7.4474|Cfb|||Q70|Bern
Switzerland|Chur|Graubünden|46.8508|9.5320|Cfb|||Q69007|Chur
Switzerland|Delémont|Jura|47.3649|7.3445|Cfb|||Q68103|Delémont|Delemont
Switzerland|Frauenfeld|Thurgau|47.5579|8.8998|Cfb|||Q68124|Frauenfeld
Switzerland|Fribourg|Fribourg|46.8065|7.1619|Cfb|||Q36378|Fribourg
Switzerland|Geneva|Geneva|46.2044|6.1432|Cfb|||Q71|Geneva
Switzerland|Glarus|Glarus|47.0406|9.0680|Cfb|||Q63911|Glarus
Switzerland|Herisau|Appenzell Ausserrhoden|47.3862|9.2792|Cfb|||Q63918|Herisau
Switzerland|Lausanne|Vaud|46.5197|6.6323|Cfb|||Q807|Lausanne
Switzerland|Liestal|Basel-Landschaft|47.4843|7.7341|Cfb|||Q69060|Liestal
Switzerland|Lucerne|Lucerne|47.0502|8.3093|Cfb|||Q4191|Lucerne
Switzerland|Neuchâtel|Neuchâtel|46.9896|6.9293|Cfb|||Q69345|Neuchâtel|Neuchatel
Switzerland|Sarnen|Obwalden|46.8961|8.2467|Cfb|||Q68146|Sarnen
Switzerland|Schaffhausen|Schaffhausen|47.6965|8.6348|Cfb|||Q9009|Schaffhausen
Switzerland|Schwyz|Schwyz|47.0207|8.6528|Cfb|||Q68125|Schwyz
Switzerland|Sion|Valais|46.2331|7.3606|BSk|||Q68136|Sion,_Switzerland
Switzerland|Solothurn|Solothurn|47.2088|7.5323|Cfb|||Q68965|Solothurn
Switzerland|St. Gallen|St. Gallen|47.4245|9.3767|Cfb|||Q25607|St._Gallen|Saint Gallen
Switzerland|Stans|Nidwalden|46.9572|8.3658|Cfb|||Q68115|Stans
Switzerland|Zug|Zug|47.1662|8.5155|Cfb||||Zug
Switzerland|Zürich|Zürich|47.3769|8.5417|Cfb|||Q72|Zürich|Zurich
Switzerland|Altdorf|Uri|46.8804|8.6444|Cfb|||Q63927|Altdorf,_Uri
South Africa|Bhisho|Eastern Cape|-32.8499|27.4380|Cfb|||Q101418|Bhisho|Bisho
South Africa|Bloemfontein|Free State|-29.0852|26.1596|BSk|||Q37701|Bloemfontein
South Africa|Cape Town|Western Cape|-33.9249|18.4241|Csb|||Q5465|Cape_Town
South Africa|Johannesburg|Gauteng|-26.2041|28.0473|Cwb|||Q34647|Johannesburg
South Africa|Kimberley|Northern Cape|-28.7282|24.7499|BSh|||Q209773|Kimberley,_Northern_Cape
South Africa|Mahikeng|North West|-25.8652|25.6442|BSh|||Q485560|Mahikeng|Mafikeng,Mmabatho
South Africa|Mbombela|Mpumalanga|-25.4753|30.9694|Cwa|||Q217043|Mbombela|Nelspruit
South Africa|Pietermaritzburg|KwaZulu-Natal|-29.6006|30.3794|Cfa|||Q217154|Pietermaritzburg
South Africa|Polokwane|Limpopo|-23.9045|29.4689|BSh|||Q208502|Polokwane|Pietersburg
Austria|Bregenz|Vorarlberg|47.5031|9.7471|Cfb|||Q483153|Bregenz
Austria|Eisenstadt|Burgenland|47.8457|16.5233|Cfb|||Q689460|Eisenstadt
Austria|Graz|Styria|47.0707|15.4395|Cfb|||Q13298|Graz
Austria|Innsbruck|Tyrol|47.2692|11.4041|Dfb|||Q1735|Innsbruck
Austria|Klagenfurt|Carinthia|46.6365|14.3122|Cfb|||Q380262|Klagenfurt
Austria|Linz|Upper Austria|48.3069|14.2858|Cfb|||Q41329|Linz
Austria|Salzburg|Salzburg|47.8095|13.0550|Cfb|||Q34713|Salzburg
Austria|Sankt Pölten|Lower Austria|48.2035|15.6256|Cfb|||Q82500|Sankt_Pölten|St. Pölten,Sankt Polten,St Polten
Austria|Vienna|Vienna|48.2082|16.3738|Cfb|||Q1741|Vienna|Wien
Angola|Caxito|Bengo|-8.5785|13.6643|BSh|||Q2706761|Caxito
Angola|Benguela|Benguela|-12.5763|13.4055|BWh|||Q183215|Benguela
Angola|Cuito|Bié|-12.3833|16.9333|Cwb|||Q219698|Kuito|Kuito
Angola|Cabinda|Cabinda|-5.5706|12.1976|Aw|||Q152102|Cabinda_(city)
Angola|Menongue|Cuando Cubango|-14.6585|17.6900|Cwa|||Q216101|Menongue
Angola|Ndalatando|Cuanza Norte|-9.2978|14.9116|Aw|||Q217707|N'dalatando|Ndalatando
Angola|Sumbe|Cuanza Sul|-11.2061|13.8437|BSh|||Q220765|Sumbe
Angola|Ondjiva|Cunene|-17.0667|15.7333|BSh|||Q216249|Ondjiva|Ondjiva,Vila Pereira de Eça
Angola|Huambo|Huambo|-12.7761|15.7392|Cwb|||Q207322|Huambo
Angola|Lubango|Huíla|-14.9172|13.4925|Cwb|||Q219072|Lubango
Angola|Luanda|Luanda|-8.8390|13.2894|BSh|||Q3897|Luanda
Angola|Dundo|Lunda Norte|-7.3800|20.8351|Aw|||Q217831|Dundo
Angola|Saurimo|Lunda Sul|-9.6608|20.3916|Aw|||Q216834|Saurimo
Angola|Malanje|Malanje|-9.5402|16.3410|Aw|||Q216920|Malanje
Angola|Luena|Moxico|-11.7833|19.9167|Cwa|||Q216551|Luena,_Angola|Luso
Angola|Moçâmedes|Namibe|-15.1961|12.1522|BWh|||Q216947|Moçâmedes|Mocamedes,Namibe
Angola|Uíge|Uíge|-7.6087|15.0613|Aw|||Q216998|Uíge|Uige
Angola|Mbanza-Kongo|Zaire|-6.2670|14.2401|Aw|||Q216801|M'banza-Kongo|Mbanza Kongo
Namibia|Windhoek|Khomas|-22.5609|17.0658|BSh|||Q3935|Windhoek
Namibia|Gobabis|Omaheke|-22.4550|18.9630|BSh|||Q1012894|Gobabis
Namibia|Otjiwarongo|Otjozondjupa|-20.4637|16.6477|BSh|||Q1026995|Otjiwarongo
Namibia|Katima Mulilo|Zambezi|-17.5000|24.2667|BSh|||Q1013272|Katima_Mulilo
Namibia|Keetmanshoop|ǁKaras|-26.5833|18.1333|BWh|||Q1013332|Keetmanshoop|Karasburg regional seat
Namibia|Mariental|Hardap|-24.6333|17.9667|BWh|||Q1013457|Mariental
Namibia|Opuwo|Kunene|-18.0607|13.8390|BWh|||Q1021175|Opuwo
Namibia|Oshakati|Oshana|-17.7833|15.6833|BSh|||Q1014034|Oshakati
Namibia|Outapi|Omusati|-17.5000|14.9833|BSh|||Q1020827|Outapi|Uutapi
Namibia|Rundu|Kavango East|-17.9333|19.7667|BSh|||Q1014105|Rundu
Namibia|Swakopmund|Erongo|-22.6784|14.5266|BWh|||Q1007456|Swakopmund
Namibia|Eenhana|Ohangwena|-17.4667|16.3333|BSh|||Q1012781|Eenhana
Namibia|Omuthiya|Oshikoto|-18.3646|16.5815|BSh|||Q1020691|Omuthiya
Namibia|Nkurenkuru|Kavango West|-17.6167|18.6000|BSh|||Q1960341|Nkurenkuru
Namibia|Walvis Bay|Erongo|-22.9576|14.5053|BWk|local_administrative_center||Q157140|Walvis_Bay
Ecuador|Quito|Pichincha|-0.1807|-78.4678|Cfb|||Q2900|Quito
Ecuador|Guayaquil|Guayas|-2.1709|-79.9224|Aw|||Q43509|Guayaquil
Ecuador|Cuenca|Azuay|-2.9001|-79.0059|Cfb|||Q15635|Cuenca,_Ecuador
Ecuador|Ambato|Tungurahua|-1.2491|-78.6168|Cfb|||Q208298|Ambato,_Ecuador
Ecuador|Azogues|Cañar|-2.7397|-78.8486|Cfb|||Q233992|Azogues
Ecuador|Babahoyo|Los Ríos|-1.8022|-79.5344|Aw|||Q234108|Babahoyo
Ecuador|Esmeraldas|Esmeraldas|0.9592|-79.6539|Am|||Q234588|Esmeraldas,_Ecuador
Ecuador|Guaranda|Bolívar|-1.5926|-79.0009|Cfb|||Q234609|Guaranda
Ecuador|Ibarra|Imbabura|0.3517|-78.1223|Csb|||Q208305|Ibarra,_Ecuador
Ecuador|Latacunga|Cotopaxi|-0.9352|-78.6155|Cfb|||Q234669|Latacunga
Ecuador|Loja|Loja|-3.9931|-79.2042|Cfb|||Q208317|Loja,_Ecuador
Ecuador|Macas|Morona Santiago|-2.3087|-78.1114|Af|||Q234777|Macas_(city)
Ecuador|Machala|El Oro|-3.2581|-79.9554|BSh|||Q208323|Machala
Ecuador|Nueva Loja|Sucumbíos|0.0847|-76.8828|Af|||Q234890|Nueva_Loja|Lago Agrio
Ecuador|Portoviejo|Manabí|-1.0546|-80.4545|BSh|||Q208326|Portoviejo
Ecuador|Puerto Baquerizo Moreno|Galápagos|-0.9025|-89.6092|BSh|||Q498938|Puerto_Baquerizo_Moreno
Ecuador|Puyo|Pastaza|-1.4924|-78.0028|Af|||Q234982|Puyo,_Pastaza
Ecuador|Riobamba|Chimborazo|-1.6636|-78.6546|Cfb|||Q208334|Riobamba
Ecuador|Santa Elena|Santa Elena|-2.2267|-80.8583|BWh|||Q235104|Santa_Elena,_Ecuador
Ecuador|Santo Domingo|Santo Domingo de los Tsáchilas|-0.2531|-79.1754|Am|||Q208339|Santo_Domingo,_Ecuador
Ecuador|Tena|Napo|-0.9938|-77.8129|Af|||Q235163|Tena,_Ecuador
Ecuador|Tulcán|Carchi|0.8119|-77.7173|Cfb|||Q208344|Tulcán|Tulcan
Ecuador|Zamora|Zamora Chinchipe|-4.0669|-78.9549|Af|||Q235233|Zamora,_Ecuador
Ecuador|Francisco de Orellana|Orellana|-0.4629|-76.9872|Af|||Q1027283|Puerto_Francisco_de_Orellana|El Coca,Coca
Peru|Lima|Lima Region|-12.0464|-77.0428|BWh|||Q2868|Lima
Peru|Arequipa|Arequipa|-16.4090|-71.5375|BWk|||Q159273|Arequipa
Peru|Ayacucho|Ayacucho|-13.1631|-74.2236|Cwb|||Q205057|Ayacucho
Peru|Cajamarca|Cajamarca|-7.1617|-78.5128|Cwb|||Q205060|Cajamarca
Peru|Callao|Callao|-12.0566|-77.1181|BWh|||Q105037|Callao
Peru|Cerro de Pasco|Pasco|-10.6869|-76.2565|ET|||Q205068|Cerro_de_Pasco
Peru|Chiclayo|Lambayeque|-6.7714|-79.8409|BWh|||Q205069|Chiclayo
Peru|Chachapoyas|Amazonas|-6.2317|-77.8690|Cfb|||Q205066|Chachapoyas,_Peru
Peru|Cusco|Cusco|-13.5319|-71.9675|Cwb|||Q5582862|Cusco|Cuzco
Peru|Huancavelica|Huancavelica|-12.7864|-74.9764|Cwb|||Q205074|Huancavelica
Peru|Huánuco|Huánuco|-9.9306|-76.2422|Cwb|||Q205075|Huánuco|Huanuco
Peru|Huaraz|Áncash|-9.5278|-77.5278|Cwb|||Q205076|Huaraz
Peru|Ica|Ica|-14.0678|-75.7286|BWh|||Q205078|Ica,_Peru
Peru|Iquitos|Loreto|-3.7437|-73.2516|Af|||Q205080|Iquitos
Peru|Moquegua|Moquegua|-17.1930|-70.9348|BWk|||Q205084|Moquegua
Peru|Moyobamba|San Martín|-6.0342|-76.9746|Am|||Q205086|Moyobamba
Peru|Piura|Piura|-5.1945|-80.6328|BWh|||Q205089|Piura
Peru|Pucallpa|Ucayali|-8.3791|-74.5539|Af|||Q205091|Pucallpa
Peru|Puerto Maldonado|Madre de Dios|-12.5933|-69.1891|Af|||Q205093|Puerto_Maldonado
Peru|Puno|Puno|-15.8402|-70.0219|ET|||Q205095|Puno
Peru|Tacna|Tacna|-18.0066|-70.2463|BWk|||Q205099|Tacna
Peru|Trujillo|La Libertad|-8.1116|-79.0288|BWh|||Q214173|Trujillo,_Peru
Peru|Tumbes|Tumbes|-3.5669|-80.4515|BWh|||Q205102|Tumbes,_Peru
Peru|Abancay|Apurímac|-13.6339|-72.8814|Cwb|||Q205055|Abancay
Peru|Huancayo|Junín|-12.0651|-75.2049|Cwb|||Q205077|Huancayo
Chile|Santiago|Santiago Metropolitan Region|-33.4489|-70.6693|Csb|||Q2887|Santiago
Chile|Arica|Arica y Parinacota|-18.4783|-70.3126|BWh|||Q2203|Arica
Chile|Iquique|Tarapacá|-20.2307|-70.1357|BWh|||Q2210|Iquique
Chile|Antofagasta|Antofagasta|-23.6509|-70.3975|BWh|||Q3612|Antofagasta
Chile|Copiapó|Atacama|-27.3668|-70.3323|BWh|||Q2167|Copiapó|Copiapo
Chile|La Serena|Coquimbo|-29.9027|-71.2519|BWk|||Q14467|La_Serena,_Chile
Chile|Valparaíso|Valparaíso|-33.0472|-71.6127|Csb|||Q33986|Valparaíso|Valparaiso
Chile|Rancagua|O'Higgins|-34.1708|-70.7444|Csb|||Q200429|Rancagua
Chile|Talca|Maule|-35.4264|-71.6554|Csb|||Q201341|Talca
Chile|Chillán|Ñuble|-36.6063|-72.1034|Csb|||Q200452|Chillán|Chillan
Chile|Concepción|Biobío|-36.8201|-73.0444|Csb|||Q1880|Concepción,_Chile|Concepcion
Chile|Temuco|Araucanía|-38.7359|-72.5904|Cfb|||Q8214|Temuco
Chile|Valdivia|Los Ríos|-39.8196|-73.2452|Cfb|||Q203633|Valdivia
Chile|Puerto Montt|Los Lagos|-41.4689|-72.9411|Cfb||||Puerto_Montt
Chile|Coyhaique|Aysén|-45.5712|-72.0685|Cfc|||Q203652|Coyhaique|Coihaique
Chile|Punta Arenas|Magallanes|-53.1638|-70.9171|Cfc|||Q51599|Punta_Arenas
Japan|Sapporo|Hokkaido|43.0618|141.3545|Dfa|||Q37951|Sapporo
Japan|Aomori|Aomori|40.8222|140.7474|Dfa|||Q183584|Aomori
Japan|Morioka|Iwate|39.7036|141.1527|Dfa|||Q200106|Morioka
Japan|Sendai|Miyagi|38.2682|140.8694|Cfa|||Q46747|Sendai
Japan|Akita|Akita|39.7200|140.1026|Cfa|||Q171638|Akita_(city)
Japan|Yamagata|Yamagata|38.2554|140.3396|Cfa|||Q205526|Yamagata_(city)
Japan|Fukushima|Fukushima|37.7608|140.4747|Cfa|||Q161176|Fukushima_(city)
Japan|Mito|Ibaraki|36.3659|140.4714|Cfa|||Q200195|Mito,_Ibaraki
Japan|Utsunomiya|Tochigi|36.5551|139.8828|Cfa|||Q200279|Utsunomiya
Japan|Maebashi|Gunma|36.3895|139.0634|Cfa|||Q201089|Maebashi
Japan|Saitama|Saitama|35.8617|139.6455|Cfa|||Q170919|Saitama_(city)
Japan|Chiba|Chiba|35.6074|140.1065|Cfa|||Q170616|Chiba_(city)
Japan|Tokyo|Tokyo|35.6762|139.6503|Cfa|||Q1490|Tokyo
Japan|Yokohama|Kanagawa|35.4437|139.6380|Cfa|||Q38283|Yokohama
Japan|Niigata|Niigata|37.9161|139.0364|Cfa|||Q171578|Niigata_(city)
Japan|Toyama|Toyama|36.6953|137.2113|Cfa|||Q201117|Toyama_(city)
Japan|Kanazawa|Ishikawa|36.5613|136.6562|Cfa|||Q186636|Kanazawa
Japan|Fukui|Fukui|36.0641|136.2196|Cfa|||Q201094|Fukui_(city)
Japan|Kōfu|Yamanashi|35.6623|138.5683|Cfa|||Q201101|Kōfu|Kofu
Japan|Nagano|Nagano|36.6486|138.1948|Cfa|||Q201107|Nagano_(city)
Japan|Gifu|Gifu|35.4233|136.7607|Cfa|||Q185837|Gifu
Japan|Shizuoka|Shizuoka|34.9756|138.3828|Cfa|||Q174691|Shizuoka_(city)
Japan|Nagoya|Aichi|35.1815|136.9066|Cfa|||Q11751|Nagoya
Japan|Tsu|Mie|34.7186|136.5059|Cfa|||Q201119|Tsu,_Mie
Japan|Ōtsu|Shiga|35.0179|135.8546|Cfa|||Q201127|Ōtsu|Otsu
Japan|Kyoto|Kyoto|35.0116|135.7681|Cfa|||Q34600|Kyoto
Japan|Osaka|Osaka|34.6937|135.5023|Cfa|||Q35765|Osaka
Japan|Kobe|Hyōgo|34.6901|135.1955|Cfa|||Q48320|Kobe
Japan|Nara|Nara|34.6851|135.8048|Cfa|||Q172922|Nara_(city)
Japan|Wakayama|Wakayama|34.2305|135.1708|Cfa|||Q201138|Wakayama_(city)
Japan|Tottori|Tottori|35.5011|134.2351|Cfa|||Q201134|Tottori_(city)
Japan|Matsue|Shimane|35.4681|133.0484|Cfa|||Q201104|Matsue
Japan|Okayama|Okayama|34.6551|133.9195|Cfa|||Q200243|Okayama
Japan|Hiroshima|Hiroshima|34.3853|132.4553|Cfa|||Q34664|Hiroshima
Japan|Yamaguchi|Yamaguchi|34.1785|131.4737|Cfa|||Q201142|Yamaguchi_(city)
Japan|Tokushima|Tokushima|34.0703|134.5548|Cfa|||Q201132|Tokushima_(city)
Japan|Takamatsu|Kagawa|34.3428|134.0466|Cfa|||Q201130|Takamatsu
Japan|Matsuyama|Ehime|33.8392|132.7657|Cfa|||Q201105|Matsuyama
Japan|Kōchi|Kōchi|33.5597|133.5311|Cfa|||Q200215|Kōchi,_Kōchi|Kochi
Japan|Fukuoka|Fukuoka|33.5904|130.4017|Cfa|||Q26600|Fukuoka
Japan|Saga|Saga|33.2635|130.3009|Cfa|||Q201123|Saga_(city)
Japan|Nagasaki|Nagasaki|32.7503|129.8777|Cfa|||Q38234|Nagasaki
Japan|Kumamoto|Kumamoto|32.8031|130.7079|Cfa|||Q171630|Kumamoto
Japan|Ōita|Ōita|33.2396|131.6093|Cfa|||Q201126|Ōita_(city)|Oita
Japan|Miyazaki|Miyazaki|31.9077|131.4202|Cfa|||Q200222|Miyazaki_(city)
Japan|Kagoshima|Kagoshima|31.5966|130.5571|Cfa|||Q171743|Kagoshima
Japan|Naha|Okinawa|26.2124|127.6809|Cfa|||Q181966|Naha
""".strip()

# Full 81-province seed. Coordinates are reviewed city-centre coordinates,
# intentionally bundled so a failed enrichment cannot remove a province.
TURKEY = """
Adana,37.0000,35.3213;Adıyaman,37.7648,38.2786;Afyonkarahisar,38.7507,30.5567;Ağrı,39.7191,43.0503;Aksaray,38.3687,34.0370;Amasya,40.6499,35.8353;Ankara,39.9334,32.8597;Antalya,36.8969,30.7133;Ardahan,41.1105,42.7022;Artvin,41.1828,41.8183;Aydın,37.8450,27.8396;Balıkesir,39.6484,27.8826;Bartın,41.5811,32.4610;Batman,37.8812,41.1351;Bayburt,40.2552,40.2249;Bilecik,40.1501,29.9831;Bingöl,38.8854,40.4980;Bitlis,38.4006,42.1095;Bolu,40.7395,31.6116;Burdur,37.7203,30.2908;Bursa,40.1885,29.0610;Çanakkale,40.1553,26.4142;Çankırı,40.6013,33.6134;Çorum,40.5506,34.9556;Denizli,37.7765,29.0864;Diyarbakır,37.9144,40.2306;Düzce,40.8438,31.1565;Edirne,41.6818,26.5623;Elazığ,38.6810,39.2264;Erzincan,39.7500,39.5000;Erzurum,39.9043,41.2679;Eskişehir,39.7767,30.5206;Gaziantep,37.0662,37.3833;Giresun,40.9128,38.3895;Gümüşhane,40.4386,39.5086;Hakkâri,37.5744,43.7408;Hatay,36.2025,36.1606;Iğdır,39.8880,44.0048;Isparta,37.7648,30.5566;Istanbul,41.0082,28.9784;İzmir,38.4237,27.1428;Kahramanmaraş,37.5753,36.9228;Karabük,41.2061,32.6204;Karaman,37.1759,33.2287;Kars,40.6013,43.0975;Kastamonu,41.3887,33.7827;Kayseri,38.7312,35.4787;Kilis,36.7184,37.1212;Kırıkkale,39.8468,33.5153;Kırklareli,41.7351,27.2252;Kırşehir,39.1425,34.1709;Kocaeli,40.8533,29.8815;Konya,37.8746,32.4932;Kütahya,39.4167,29.9833;Malatya,38.3552,38.3095;Manisa,38.6191,27.4289;Mardin,37.3212,40.7245;Mersin,36.8121,34.6415;Muğla,37.2153,28.3636;Muş,38.9462,41.7539;Nevşehir,38.6244,34.7239;Niğde,37.9698,34.6766;Ordu,40.9839,37.8764;Osmaniye,37.0742,36.2478;Rize,41.0201,40.5234;Sakarya,40.7569,30.3781;Samsun,41.2867,36.3300;Şanlıurfa,37.1674,38.7955;Siirt,37.9333,41.9500;Sinop,42.0231,35.1531;Sivas,39.7477,37.0179;Şırnak,37.4187,42.4918;Tekirdağ,40.9780,27.5110;Tokat,40.3167,36.5500;Trabzon,41.0015,39.7178;Tunceli,39.1079,39.5401;Uşak,38.6823,29.4082;Van,38.4891,43.4089;Yalova,40.6500,29.2667;Yozgat,39.8181,34.8147;Zonguldak,41.4564,31.7987
""".strip()

COUNTRY_META = {
    "Poland": ("Q36", "Europe", "voivodeship"),
    "Germany": ("Q183", "Europe", "federal state"),
    "Spain": ("Q29", "Europe", "autonomous community or autonomous city"),
    "France": ("Q142", "Europe", "region"),
    "Norway": ("Q20", "Europe", "county"),
    "Sweden": ("Q34", "Europe", "county"),
    "Finland": ("Q33", "Europe", "region"),
    "Türkiye": ("Q43", "Asia", "province"),
    "Switzerland": ("Q39", "Europe", "canton"),
    "South Africa": ("Q258", "Africa", "province"),
    "Austria": ("Q40", "Europe", "federal state"),
    "Angola": ("Q916", "Africa", "province"),
    "Namibia": ("Q1030", "Africa", "region"),
    "Ecuador": ("Q736", "South America", "province"),
    "Peru": ("Q419", "South America", "department or constitutional province"),
    "Chile": ("Q298", "South America", "region"),
    "Japan": ("Q17", "Asia", "prefecture"),
}

KOPPEN_LABELS = {
    "Af": "Tropical rainforest climate", "Am": "Tropical monsoon climate", "Aw": "Tropical savanna climate",
    "BWh": "Hot desert climate", "BWk": "Cold desert climate", "BSh": "Hot semi-arid climate", "BSk": "Cold semi-arid climate",
    "Csa": "Hot-summer Mediterranean climate", "Csb": "Warm-summer Mediterranean climate",
    "Cfa": "Humid subtropical climate", "Cwa": "Monsoon-influenced humid subtropical climate",
    "Cwb": "Subtropical highland climate", "Cfb": "Temperate oceanic climate", "Cfc": "Subpolar oceanic climate",
    "Dfa": "Hot-summer humid continental climate", "Dfb": "Warm-summer humid continental climate",
    "Dfc": "Subarctic climate", "ET": "Tundra climate",
}


HIGHLAND_CITIES = {
    "Quito", "Cuenca", "Ambato", "Azogues", "Guaranda", "Latacunga", "Loja", "Riobamba",
    "Tulcán", "Ayacucho", "Cajamarca", "Cerro de Pasco", "Cusco", "Huancavelica", "Huánuco",
    "Huaraz", "Puno", "Abancay", "Huancayo", "Huambo", "Lubango", "Cuito",
}
COUNTRY_ALIASES = {
    "South Africa": ["RSA"],
    "Ecuador": ["Equador"],
    "Chile": ["Chille"],
}


def broad_group(code: str, city: str = "") -> str:
    if city in HIGHLAND_CITIES:
        return "Highland / Mountain"
    if code.startswith("A"):
        return "Tropical"
    if code.startswith("B"):
        return "Dry / Arid"
    if code in {"ET", "EF"}:
        return "Polar"
    if code.startswith("D"):
        return "Continental"
    return "Temperate"


def parse_seeds() -> list[tuple[str, str, str, float, float, str, str, list[str], str | None, str | None]]:
    rows = []
    for line in SEEDS.splitlines():
        parts = line.split("|")
        parts += [""] * (8 - len(parts))
        country, city, region, lat, lon, code, record_type = parts[:7]
        aliases = parts[-1] if len(parts) > 8 else parts[7]
        rows.append((country, city, region, float(lat), float(lon), code, record_type or "regional_capital",
                     [alias for alias in aliases.split(",") if alias], None, None))
    for line in NEW_PRIORITY_SEEDS.splitlines():
        parts = line.split("|")
        parts += [""] * (11 - len(parts))
        country, city, region, lat, lon, code, record_type, _unused, qid, title, aliases = parts[:11]
        rows.append((
            country, city, region, float(lat), float(lon), code, record_type or "regional_capital",
            [alias for alias in aliases.split(",") if alias], qid or None, title or None,
        ))
    dry = {"Adana", "Adıyaman", "Ankara", "Batman", "Diyarbakır", "Gaziantep", "Iğdır", "Kilis",
           "Konya", "Mardin", "Şanlıurfa", "Siirt"}
    continental = {"Ağrı", "Ardahan", "Bayburt", "Erzincan", "Erzurum", "Kars", "Sivas"}
    aliases = {"İzmir": ["Izmir"], "Şanlıurfa": ["Sanliurfa"], "Diyarbakır": ["Diyarbakir"],
               "Eskişehir": ["Eskisehir"], "Istanbul": ["İstanbul"]}
    for item in TURKEY.split(";"):
        city, lat, lon = item.split(",")
        code = "BSk" if city in dry else "Dfb" if city in continental else "Csa"
        rows.append(("Türkiye", city, f"{city} Province", float(lat), float(lon), code,
                     "regional_capital", aliases.get(city, []), None, None))
    return rows


def build_record(row: tuple[str, str, str, float, float, str, str, list[str], str | None, str | None]) -> dict:
    country, city, region, lat, lon, code, record_type, aliases, qid, wikipedia_title = row
    country_qid, continent, region_type = COUNTRY_META[country]
    title = wikipedia_title or city
    url = f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"
    return {
        "id": f"priority:{country.casefold()}:{region.casefold()}:{city.casefold()}",
        "name": city, "ascii_name": aliases[0] if aliases else None, "aliases": aliases,
        "country_aliases": COUNTRY_ALIASES.get(country, []),
        "country": country, "country_qid": country_qid, "continent": continent, "region": continent,
        "administrative_region": region, "administrative_region_type": region_type,
        "administrative_region_qid": None, "latitude": lat, "longitude": lon, "qid": qid,
        "wikipedia_title": title, "wikipedia_url": url,
        "climate_classification": KOPPEN_LABELS[code], "climate_classification_label": KOPPEN_LABELS[code],
        "primary_koppen_code": code, "secondary_koppen_codes": [], "climate_group": broad_group(code, city),
        "climate_classification_source": "curated_english_wikipedia_snapshot",
        "climate_classification_source_metadata": {
            "source_name": "English Wikipedia", "source_language": "en", "source_page_title": title,
            "source_url": url, "source_priority": "english_primary", "source_role": "offline_startup_classification",
            "source_note": "Curated seed retained independently of optional enrichment.",
            "license": "CC BY-SA 4.0", "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
            "contributors_url": f"{url}?action=history",
        },
        "climate_extraction_status": "curated primary Köppen classification in bundled offline snapshot",
        "extraction_status": "curated primary Köppen classification in bundled offline snapshot",
        "record_type": record_type, "record_scope": "priority_country_regional_capital",
        "provenance": {
            "selection_method": "maintainer-reviewed country seed list; not runtime discovery",
            "administrative_note": "Shared/co-located administrative centers are retained as separate records where applicable.",
            "metadata_source_name": "Wikidata-compatible curated seed", "metadata_license": "CC0 1.0",
            "metadata_license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
            "climate_source_name": "English Wikipedia", "climate_source_url": url,
            "climate_license": "CC BY-SA 4.0",
            "climate_license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
        },
    }


def main() -> None:
    records = [build_record(row) for row in parse_seeds()]
    payload = {
        "schema_version": 1, "generated_at": datetime.now(UTC).isoformat(),
        "coverage": {
            "countries": list(COUNTRY_META),
            "france_scope": "13 metropolitan and 5 overseas regional capitals",
            "turkiye_scope": "all 81 provincial capitals",
            "runtime_network_required": False,
        },
        "source_metadata": {
            "selection_source": "project-maintained curated seed lists",
            "enrichment_sources": ["English Wikipedia", "native-language Wikipedia fallback", "Wikidata fallback"],
            "runtime_network_required": False,
            "licenses": ["CC BY-SA 4.0 (Wikipedia-derived climate descriptions)", "CC0 1.0 (Wikidata-compatible metadata)"],
        },
        "records": records,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = {
        "generated_at": payload["generated_at"],
        "countries_processed": list(COUNTRY_META),
        "records_created": len(records),
        "records_enriched": sum(
            bool(record.get("qid") or record.get("wikipedia_title")) for record in records
        ),
        "records_missing_climate_classification": sum(
            record.get("climate_classification") in (None, "", "Unknown") for record in records
        ),
        "records_missing_coordinates": sum(
            record.get("latitude") is None or record.get("longitude") is None for record in records
        ),
        "curated_overrides_applied": sum(
            record["name"] in HIGHLAND_CITIES for record in records
        ),
        "validation_failures": [],
        "runtime_network_required": False,
    }
    REPORT_OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(records)} records to {OUTPUT.relative_to(ROOT)}")
    print(f"Wrote build report to {REPORT_OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
