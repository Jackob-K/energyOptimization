
############################################################
#                    ENERGYOPTIMIZATION                   #
############################################################


Tato aplikace slouží k optimalizaci spotřeby elektřiny.
Využívá framework Reflex (kombinace frontendu a backendu v Pythonu) a je rozdělena do dvou hlavních částí: `backend/` a `frontend/`.

############################################################
#                      PRVNÍ SPUŠTĚNÍ                     #
############################################################

1) Podle sekce "INSTALACE NA RASPBERRY PI" naklonujte github repozitář na Raspberry PI a nainstalujte si potřebné knihovny
2) Spusťte aplikaci podle sekce "SPUŠTĚNÍ APLIKACE"
    2a) Aplikace při prvním spuštění automaticky vytvoří databázi (database.db), která obsahuje prázdné tabulky a je nutné je doplnit viz sekce "TABULKY DATABÁZE"
        (Nutno případně znát příkazy pro práci s sqlite3 viz sekce "SQLITE3")
        !!!NUTNÉ DO DATABÁZE VLOŽIT NASTAVENÍ!!!
3) Nahrajte data pomocí UI na stránce "Datafeed" kliknutím a vybrání souboru s historickými daty
    (ideálně zatím nahrávat data s celými hodnotami => nevím, zda mám ošetřeno nahrávání timestampů s různými časy)
    Struktura dat historického souboru viz sekce "STRUKTURA TABULKY S HISTORICKÝMI DATY"
    !!!NUTNO DODRŽET STRUKTURU HISTORICKÝCH DAT!!!
4) Na stránce UI s názvem "Settings" je nutné dopsat parametry jednotlivých FVE polí
    (lze jich přidat více, pokud by byly jinak natočená/nakloněná, souřadnice se pro jednoduchost kopírují, ale lze je přepsat)
    (zeměpisnou polohu ZAPISOVAT ve formátu DD.ddddd)
10) Aplikace má pevně nastavené časy automatického spouštění jednotlivých modulů
    10a) Spouštění modulů je definováno v main.py (doporučuji nenastavovat čas dřívější než v 13:05, jelikož v 13:00 se aktualizuje OTE)
    10b) Jednotlivé moduly se dají spustit samostatně příkazem "python backend/{názevModulu.py}" ideálně v následujícím pořadí
        i)      scrape.py               – stažení informací o cenách elektřiny na následující den
        ii)     fvePrediction.py        – predikce výroby FVE na následující den
        iii)    dataProcessor.py        – připravení dat pro predikci
        iv)     usagePrediction.py      – predikce spotřeby na následující den
        v)      optimization.py         – výpočet optimalizace pro následující den.
    10c) Výsledek je k vidění v nově vytvořeném/upraveném souboru optimizedSchedule.json a "přesné" ušetřené hodnoty jsou v databázi v tabulce optimizationLog



############################################################
#                 INSTALACE NA RASPBERRY PI                #
############################################################
* nutno mít nainstalovaný Python 3.9+ a pip

Instalujeme větev "first-build"

1. Klonování produkční větve:
    git clone -b first-build https://github.com/Jackob-K/energyOptimization.git
    cd energyOptimization
    git checkout prod

2. Vytvoření a aktivace virtuálního prostředí:
    python3 -m venv venv
    source venv/bin/activate

3. Instalace závislostí:
    pip install -r requirements.txt


############################################################
#                     SPUŠTĚNÍ APLIKACE                    #
############################################################

Backendová logika (spustit main.py):
=>    python backend/main.py

Webová aplikace (produkční server):
=>    reflex run --env prod


Uživatelské rozhraní:
http://localhost:8000                                       # Z lokálního zařízení
http://<IP_adresa_RaspberryPi>:8000                         # Z jiného zařízení ve stejné síti

Optimalizovaný plán na následující den:
http://localhost:3000/optimizedSchedule                     # Z lokálního zařízení
http://<IP_adresa_RaspberryPi>:3000/optimizedSchedule       # Z jiného zařízení ve stejné síti


############################################################
#                     TABULKY DATABÁZE                    #
############################################################

Databáze je rozdělena na několik tabulek viz níže:
•	energyData      – obsahuje hodnoty spotřeby elektřiny a teploty s časovým razítkem
                    – vytvářena nahráním souboru přes UI v sekci "Datafeed" nebo pomocí MQTT
•	energyPrices    – obsahuje ceny elektřiny z webového rozhraní OTE
                    – historická data jsou irelavantní a data na další den se stahují pomocí scrape.py
•	fvePanels       – obsahuje parametry jednotlivých fotovoltaických polí
                    – jednotlivá pole FVE jsou nastavována v UI skrze stránku "Settings"
•	processedData   – obsahuje rozšířená vstupní data pro predikční model, včetně časových posunů a dalších atributů
                    – vytvářena automaticky po nahrání historických dat
•	settings        – obsahuje uživatelská nastavení MQTT připojení a parametry objektu
                    – vytvářena automaticky
•	batteryPlan     – obsahuje plánované hodnoty relativního nabití baterie v jednotlivých hodinách
                    – vytvářena automaticky
•	optimizationLog – obsahuje záznamy o finančním přínosu baterie v jednotlivých dnech
                    – vytvářena automaticky a je dostupná na adrese backendu "/optimizedSchedule" viz sekce "SPUŠTĚNÍ APKIKACE"

•   Při prvním spuštění nutno doplnit tabulky energyData, fvePanels a settings


############################################################
#           STRUKTURA TABULKY S HISTORICKÝMI DATY          #
############################################################

Zatím doporučuji nahrávat hodinová data (nejsem si teď jist, zda si všechny moduly správně přeberou eventy mimo celou hodinu)
Nutné dodržet sloupce a jejich formáty (v finále jediný striktní požadavek na uživatele)
    NÁZEV SLOUPCE             FORMÁT                        POZNÁMKA
•   timestamp             YYYY-MM-DDTHH:MM:SS         datum a čas měření
•   fveProduction             FLOAT                   reálná produkce FVE
•   consumption               FLOAT                   reálná spotřeba objektu
•   temperature               FLOAT                   reálná venkovní teplota


############################################################
#              PRÁCE S DATABÁZÍ POMOCÍ SQLITE3             #
############################################################

Vložení informací do tabulky "settings"

1) Přejděte do hlavní složky projektu (u mě MojeAplikace)
2) V terminálu se přihlaste do databáze pomocí příkazu "sqlite3 backedn/database.db"
3) Dále naplňte databázi pomocí následujících příkazů (mělo by jít vložit a spustit najednou)
    INSERT INTO parameters (id, paramName, value) VALUES (1, 'breakerCurrentPerPhase', '25');
    INSERT INTO parameters (id, paramName, value) VALUES (2, 'phases', '3');
    INSERT INTO parameters (id, paramName, value) VALUES (3, 'overrideMode', '0');
    INSERT INTO parameters (id, paramName, value) VALUES (11, mqqtServerAdress, 'test.mosquitto.org');
    INSERT INTO parameters (id, paramName, value) VALUES (12, mqttPort, '1883');
    INSERT INTO parameters (id, paramName, value) VALUES (13, mqttTopic, 'energy/data');
    INSERT INTO parameters (id, paramName, value) VALUES (14, mqttUserName, '');
    INSERT INTO parameters (id, paramName, value) VALUES (15, mqttUserPassword, '');
    INSERT INTO parameters (id, paramName, value) VALUES (16, 'batteryCapacityKWh', '10');
    INSERT INTO parameters (id, paramName, value) VALUES (17, 'batteryEfficiency', '0.9');
    INSERT INTO parameters (id, paramName, value) VALUES (18, 'batteryMaxChargeKW', '3.5');
    INSERT INTO parameters (id, paramName, value) VALUES (19, 'batteryMaxDischargeKW', '3.5');
    INSERT INTO parameters (id, paramName, value) VALUES (20, 'batterySocMin', '10');
    INSERT INTO parameters (id, paramName, value) VALUES (21, 'batterySocMax', '90');
    INSERT INTO parameters (id, paramName, value) VALUES (22, rezerva, '');
    INSERT INTO parameters (id, paramName, value) VALUES (23, rezerva, '');
    INSERT INTO parameters (id, paramName, value) VALUES (24, rezerva, '');
    INSERT INTO parameters (id, paramName, value) VALUES (25, rezerva, '');
    INSERT INTO parameters (id, paramName, value) VALUES (26, 'daysToPredict', '16');

4) Nastavení mqtt lze jako jediné zatím upravovat skrze UI na stránce "Datafeed"
To be continued...


############################################################
#                         POZNÁMKY                        #
############################################################


- requirements.txt je generován pomocí pipreqs pro co nejmenší balíček závislostí.
- Produkční verze je buildnutá pomocí `reflex build` a spuštěná přes `reflex run --env prod`.
- Raspberry Pi musí mít nainstalovaný Python 3.9+ a pip.

############################################################
#                ZÁKLADNÍ PŘÍKAZY PRO VÝVOJ               #
############################################################

Vygenerování requirements.txt (jen použité knihovny):
    pipreqs . --force

Lokální spuštění:
    reflex run

Build produkční verze (vytvoří složku rxbuild/):
    reflex build

Spuštění produkční verze:
    reflex run --env prod

Vymazání build složky:
    rm -rf rxbuild/

############################################################
#                     VĚTVE NA GITHUBU                    #
############################################################


- first-build: První stabilní verze připravená k instalaci a použití.
- prototype (dříve main): Vývojová větev – základní funkčnost, testování nápadů.



############################################################
#             POUŽITÉ KNIHOVNY A JEJICH LICENCE            #
############################################################


Tento projekt využívá následující open-source knihovny:

- APScheduler (MIT)
- FastAPI (MIT)
- httpx (BSD-3-Clause)
- joblib (BSD)
- numpy (BSD)
- paho-mqtt (EPL-2.0)
- pandas (BSD)
- pvlib (BSD-3-Clause)
- pydantic (MIT)
- requests (Apache-2.0)
- scikit-learn (BSD)
- uvicorn (BSD)
- xgboost (Apache-2.0)


############################################################
#                          LICENCE                         #
############################################################

Tento projekt je licencován pod [MIT licencí](LICENSE).

> ⚠️ **Poznámka:** Projekt je určen primárně pro studijní a osobní účely.  
> Pokud máte zájem o komerční využití, prosím kontaktujte mě: [koci.jakub@post.cz](mailto:koci.jakub@post.cz)
