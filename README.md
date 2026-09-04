# Portefølje-regelmotor

Beslutningsstøtteverktøy som validerer en investeringsportefølje mot et regelsett, og foreslår den gyldige porteføljen som ligger nærmest den opprinnelige når reglene brytes.

Backend er bygget i Python med FastAPI. Frontend er ren HTML, CSS og JavaScript, servert av samme applikasjon. Løsningen deployes til Azure App Service med GitHub Actions.

**Deployet løsning:** https://portfolio-rule-engine-h6g9fzgqgyd2hafn.norwayeast-01.azurewebsites.net

## Innhold

- [Kjøre lokalt](#kjøre-lokalt)
- [Prosjektstruktur](#prosjektstruktur)
- [API](#api)
- [Datalag](#datalag)
- [Regelmotor](#regelmotor)
- [API og feilhåndtering](#api-og-feilhåndtering)
- [Nærmeste gyldige portefølje](#nærmeste-gyldige-portefølje)
- [Konfigurasjon](#konfigurasjon)
- [Tester](#tester)
- [Avvik i datasettet](#avvik-i-datasettet)
- [Deploy](#deploy)
- [Antakelser og begrensninger](#antakelser-og-begrensninger)

## Kjøre lokalt

Krever Python 3.13.

```powershell
git clone https://github.com/akselaasbo/portfolio-rule-engine.git
cd portfolio-rule-engine

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

uvicorn app.main:app --reload
```

På macOS og Linux aktiveres miljøet med `source .venv/bin/activate`.

Applikasjonen kjører da på http://127.0.0.1:8000

- `/` viser grensesnittet
- `/docs` viser den automatisk genererte API-dokumentasjonen

Kopier `.env.example` til `.env` for å overstyre standardverdiene lokalt. Applikasjonen kjører fint uten, siden alle innstillinger har fornuftige standardverdier.

Kjør testene med `pytest`.

## Prosjektstruktur

```
app/
├── api/                  HTTP-laget: ruter og statuskoder
│   ├── routes_instruments.py
│   └── routes_validate.py
├── data/                 Datatilgang: CSV-lesing og oppslag
│   ├── loader.py
│   └── repository.py
├── domain/               Domenelogikk: eksponering, regler, optimering
│   ├── engine.py
│   ├── exposures.py
│   ├── optimizer.py
│   └── rules.py
├── models/               Pydantic-modeller
│   ├── holding.py
│   ├── instrument.py
│   ├── requests.py
│   ├── responses.py
│   └── rule.py
├── static/               Frontend
│   ├── index.html
│   ├── style.css
│   └── app.js
├── config.py             Konfigurasjon fra miljøvariabler
└── main.py               Applikasjonsoppstart og ruteregistrering

data/                     Datasettet: instrumenter, regler, eksempeldata
docs/                     Oppgaveteksten
tests/                    Enhetstester, datadrevne tester og API-tester
.github/workflows/        Build og deploy
```

Lagdelingen er prosjektets viktigste strukturelle valg. Domenelaget importerer aldri FastAPI og leser aldri filer. Det tar imot ferdige objekter og returnerer ferdige objekter. Konsekvensen er at regelmotoren kan kjøres fra et vanlig Python-skript uten webserver og uten CSV-filer på disk, noe testene utnytter.

## API

| Endepunkt | Beskrivelse |
|---|---|
| `GET /health` | Liveness-sjekk. Brukes av Azure App Service |
| `GET /instruments` | Alle tilgjengelige instrumenter med metadata |
| `POST /validate` | Validerer en portefølje og foreslår en gyldig variant ved brudd |
| `GET /` | Grensesnittet |

Eksempel på forespørsel til `/validate`:

```json
{
  "holdings": [
    { "ticker": "VTI", "weight_pct": 25 },
    { "ticker": "VXUS", "weight_pct": 20 },
    { "ticker": "BND", "weight_pct": 20 },
    { "ticker": "VNQ", "weight_pct": 10 },
    { "ticker": "GLD", "weight_pct": 5 },
    { "ticker": "XLF", "weight_pct": 10 },
    { "ticker": "XLK", "weight_pct": 10 }
  ]
}
```

Responsen inneholder `portfolio_valid`, `violations`, `warnings`, `exposures`, `summary`, og ved regelbrudd også `nearest_valid_portfolio` og `change_summary`.

## Datalag

Instrumentene leses fra `data/instruments.csv` ved oppstart av applikasjonen. Lesingen er lagt til `app/data/loader.py`, som bruker `csv.DictReader` fra standardbiblioteket. Pandas ville vært et unødvendig tungt valg for 17 rader. Det gir en stor avhengighet og tregere oppstart uten å tilføre noe, siden dataene uansett skal konverteres til objekter.

Hver rad blir til en `Instrument`, en Pydantic-modell definert i `app/models/instrument.py`. Samme modell brukes både som API-respons og i domenelogikken. Det er et bevisst valg: å ha to nesten identiske modeller med en oversetter mellom ville gitt kode uten nytteverdi i et prosjekt av denne størrelsen. Avhengigheten går til Pydantic, ikke til FastAPI, så domenelaget forblir fritt for webrammeverket.

`InstrumentRepository` i `app/data/repository.py` holder instrumentene i en dictionary med ticker som nøkkel og gir oppslag til resten av applikasjonen. Konstruktøren tar imot en ferdig liste, mens `from_csv()` er en egen klassemetode. Det skillet gjør at repositoryet kan opprettes med testdata uten at filer er involvert.

Repositoryet instansieres én gang ved oppstart via FastAPIs lifespan og gjøres tilgjengelig for endepunktene gjennom dependency injection. Feiler CSV-lesingen, starter ikke applikasjonen. En app som kjører uten data ville feilet senere og mer uforståelig.

Filstien hentes fra miljøvariabelen `DATA_DIR` via `app/config.py` og bygges med `pathlib` relativt til prosjektrota, slik at den ikke avhenger av hvilken mappe applikasjonen startes fra.

## Regelmotor

Regelsettet leses fra `data/rules.csv` ved oppstart. Ingen terskler, operatorer, alvorlighetsgrader eller regeltekster finnes i koden. De kommer utelukkende fra filen. Optimeringen har to egne terskler som styrer hvordan forslaget bygges, ikke om en portefølje er gyldig. Begge ligger i konfigurasjonen og er beskrevet under Nærmeste gyldige portefølje. `Rule`-modellen i `app/models/rule.py` er et flatt speilbilde av en CSV-rad og tolker ingenting selv. All tolkning skjer i regelmotoren.

### Hvordan rules.csv tolkes

`scope`-kolonnen avgjør hvordan en regel måles. Den har fire mønstre:

* `portfolio` gir ett tall for hele porteføljen, som totalvekt og antall posisjoner
* `holding` gir en aggregert måling per posisjon, som maks enkeltposisjon
* `asset_class:<verdi>` måler eksponering mot én bestemt aktivaklasse, som aksjer eller renter
* `sector` og `geography` måler største eksponering på tvers av alle grupper i dimensjonen

Motoren mapper på mønster, ikke på `rule_code`. Fem evaluatorer dekker alle åtte regler. Konsekvensen er at nye regler som passer inn i et eksisterende mønster kan legges til i CSV-filen uten kodeendring, for eksempel `asset_class:Alternatives` med en ny terskel. Bare en helt ny målemetode ville krevd ny kode.

### Evaluering

Hver evaluator returnerer ett tall, hvilken gruppe tallet gjelder for, og hvilken enhet det er målt i. Sammenligningen mot terskelen gjøres av én generisk funksjon som tolker `operator`-kolonnen. `<=` og `>=` er inklusive, og alle sammenligninger bruker en toleranse på 0,01 prosentpoeng. Uten toleransen ville flyttallsavrunding fått gyldige porteføljer til å feile på kravet om nøyaktig 100 % totalvekt.

`severity`-kolonnen avgjør om et regelbrudd havner under `violations` eller `warnings`. En portefølje er gyldig hvis den ikke har noen violations. Warnings gjør den ikke ugyldig.

Eksponeringene beregnes én gang per validering og gjenbrukes av alle reglene. Samme objekt returneres i API-responsen, slik at brukeren ser tallene reglene faktisk ble målt mot.

### Forklarbare resultater

Hvert regelbrudd returnerer `rule_code`, `severity`, beskrivelsen fra `description_no`, målt verdi, operator, terskel, hvilken gruppe det gjelder, enhet, og hvor mye grensen er overskredet. Beskrivelsen kommer direkte fra CSV-filen, slik at responsen bygges på regeldefinisjonene og ikke på tekster i koden.

Enheten skilles mellom prosent og antall, slik at frontend kan vise `MIN_NUMBER_OF_HOLDINGS` som «4 posisjoner, minst 5» og ikke som prosent. Vurderingen gjøres i backend fordi den allerede har lest `metric_definition`. Å gjenta logikken i JavaScript ville plassert domenekunnskap i frontend og brutt med at `rules.csv` er kilden til sannhet.

## API og feilhåndtering

`POST /validate` tar imot en portefølje og returnerer valideringsresultatet. Feilhåndteringen skiller mellom to ting som er lette å blande sammen.

**Ugyldig input** gir en feilkode. Formatfeil som manglende felt, feil datatype eller vekt utenfor 0 til 100 fanges av Pydantic-modellene og gir 422 uten at det er skrevet kode for det. Semantiske feil som krever oppslag i datasettet gir 400: ukjent ticker, tom portefølje, eller samme ticker oppgitt flere ganger. Ved ukjente tickere listes alle opp samtidig, slik at brukeren kan rette alt i én omgang.

**En portefølje som bryter reglene er ikke en feil.** Den gir 200 OK med `portfolio_valid: false` og en liste over bruddene. Forespørselen ble behandlet korrekt. Svaret er bare at porteføljen ikke består, og det er hele formålet med endepunktet.

Domenelaget kjenner ikke til HTTP. Møter det noe det ikke kan behandle, kaster det en vanlig ValueError, og API-laget fanger den og oversetter til riktig statuskode. I praksis fanger ruten de fleste slike tilfeller på forhånd, blant annet for å kunne liste alle ukjente tickere samtidig i stedet for å stoppe ved den første. except-blokken beholdes som et sikkerhetsnett hvis en ny kodesti skulle omgå forhåndssjekken.

## Nærmeste gyldige portefølje

Når en portefølje bryter en eller flere regler, beregnes en gyldig portefølje som ligger så nær den opprinnelige som mulig.

### Definisjon av «nærmest»

Avstand måles som summen av kvadrerte endringer i vekter. Den gyldige porteføljen som minimerer denne summen regnes som den nærmeste.

Kvadrert avvik er valgt fremfor absoluttavvik fordi det fordeler justeringen over flere posisjoner i stedet for å endre få posisjoner mye. Skal aksjeeksponeringen ned ti prosentpoeng, er det som regel bedre å ta litt fra flere aksjeposisjoner enn å fjerne én helt. Resultatet ligner mer på porteføljen rådgiveren opprinnelig satte sammen. Kvadrert avvik gir også et glatt og konvekst problem, som gjør at optimeringen konvergerer pålitelig.

### Metode

Problemet løses med `scipy.optimize.minimize` og metoden SLSQP. Beslutningsvariablene er vekten til hvert instrument, målfunksjonen er summen av kvadrerte avvik fra de opprinnelige vektene, og reglene fra `rules.csv` utgjør bibetingelsene. De opprinnelige vektene brukes som startpunkt.

Bibetingelsene bygges fra de samme regelobjektene som validatoren bruker. Endres en terskel i `rules.csv`, påvirker det både valideringen og optimeringen samtidig. To separate kodeveier for det samme regelsettet ville kunnet komme i utakt.

### Hele instrumentuniverset er beslutningsvariabler

Optimeringen kan tildele vekt til alle instrumenter i `instruments.csv`, ikke bare de brukeren valgte. Dette er nødvendig, ikke en utvidelse for sikkerhets skyld. Eksempelportefølje P2 består av seks amerikanske instrumenter og har 100 % US-eksponering. Geografiregelen tillater maks 60 %. Uansett hvordan vekten fordeles mellom de seks, forblir eksponeringen 100 %, og det finnes ingen gyldig løsning innenfor brukerens eget utvalg.

Målfunksjonen sørger for at dette ikke fører til unødvendige tilføyelser. Instrumenter brukeren ikke eier har opprinnelig vekt 0, og enhver vekt de tildeles straffes av kvadratleddet. De forblir derfor på 0 med mindre reglene krever noe annet.

Instrumenter med `Unknown` i aktivaklasse, sektor eller geografi holdes utenfor kandidatutvalget. Uten denne begrensningen kunne optimeringen bruke dem til å avlaste geografigrensen, siden `Unknown` utgjør sin egen gruppe, og dermed foreslå en portefølje som selv utløser en advarsel om ukjent klassifisering. Eier brukeren et slikt instrument fra før, beholdes det og kan justeres, men optimeringen legger det ikke til på eget initiativ.

### Minsteterskel for posisjoner

En posisjon i forslaget må utgjøre minst 2 prosentpoeng. Terskelen er en domenevurdering, ikke en teknisk: en posisjon under dette regnes ikke som en investeringsbeslutning.

Terskelen er nødvendig fordi kvadrert avvik favoriserer å spre en endring over mange posisjoner fremfor å konsentrere den i få. Uten den ga en portefølje med fire posisjoner og 80 % totalvekt et forslag med seksten posisjoner, hvorav tolv nye på 1,3 % hver. Matematisk korrekt, men ubrukelig som investeringsråd.

Terskelen brukes to steder: posisjoner under den fjernes etter optimeringen og vekten omfordeles, og en posisjon som tvinges inn for å oppfylle kravet om minimum antall posisjoner tildeles minst denne vekten. En egen og lavere terskel på 0,5 prosentpoeng brukes fortsatt til å fjerne rene avrundingsrester fra SLSQP.

Slår terskelen inn, kjøres optimeringen på nytt uten de utelatte instrumentene. Feiler den andre runden, brukes resultatet fra den første.

### Forenkling: minimum antall posisjoner

Kravet om minst fem posisjoner er en kardinalitetsbetingelse. Antall posisjoner er ikke en kontinuerlig funksjon av vektene, og betingelsen lar seg ikke uttrykke som en konveks bibetingelse i optimeringen.

Den håndteres derfor som etterbehandling. Etter optimeringen telles antall reelle posisjoner, altså posisjoner over minsteterskelen. Er tallet under minimum, tvinges de nærmeste kandidatene inn og optimeringen kjøres på nytt. Dette gir ikke nødvendigvis den globalt optimale løsningen, men det gir en gyldig portefølje som ligger nær den opprinnelige.

### Sikkerhetsnett

Den foreslåtte porteføljen kjøres alltid gjennom regelmotoren på nytt før den returneres. Er den ikke gyldig, returneres `nearest_valid_portfolio: null` med en forklaring i stedet for et forslag som ikke holder mål. Det samme skjer hvis optimeringen ikke konvergerer eller `scipy` kaster en feil.

Denne revalideringen fanget en reell feil under utviklingen. Normaliseringen som sikret at vektene summerte til nøyaktig 100 kunne skyve en posisjon over grensen for maksimal enkeltposisjon. Feilen ble oppdaget som et ugyldig resultat og ikke som et forslag til brukeren, og normaliseringen ble erstattet med en additiv korreksjon på en posisjon som har rom for den.

### Forklaring av endringer

`change_summary` viser hver endring med opprinnelig vekt, ny vekt, differanse og kategori: justert, lagt til eller fjernet. Der det er mulig knyttes endringen til regelen som drev den.

Koblingen er heuristisk. Den bygger på hvilken gruppe instrumentet tilhører og hvilken retning vekten er endret i: et maksimumskrav kan bare avlastes ved å redusere en posisjon i den aktuelle gruppen, og et minimumskrav bare ved å øke en. Kan ingen regel knyttes til endringen med sikkerhet, brukes en generisk begrunnelse fremfor en som kan være misvisende.

## Konfigurasjon

All konfigurasjon leses fra miljøvariabler via `app/config.py`, som bruker `pydantic-settings`. Lokalt kan verdiene settes i en `.env`-fil. På Azure settes de som Application settings.

| Variabel | Standard | Beskrivelse |
|---|---|---|
| `DATA_DIR` | `data` | Mappe med CSV-filene |
| `LOG_LEVEL` | `INFO` | Loggnivå |
| `WEIGHT_TOLERANCE` | `0.01` | Toleranse i prosentpoeng ved sammenligning mot terskler |
| `MIN_POSITION_WEIGHT_PCT` | `2.0` | Minste meningsfulle posisjon i foreslått portefølje |

Skillet mot `rules.csv` er bevisst. Miljøvariabler er teknisk oppsett som varierer mellom kjøremiljøer. Terskelverdiene i regelsettet er forretningsregler som eieren av regelverket styrer, og de hører hjemme i datafilen.

## Tester

Testene er skrevet med pytest og dekker tre nivåer.

**Enhetstester av domenet** bygger et lite instrumentregister med håndlagde instrumenter, uten at filer er involvert. De dekker aggregering av eksponeringer, tolkning av `scope`, og grensetilfellene i sammenligningsfunksjonen: at `<=` er inklusiv, at toleransen fungerer på kravet om nøyaktig 100 %, og at en ukjent operator gir feil.

**Datadrevne tester** kjører alle sju porteføljene fra `sample_portfolios.csv` gjennom regelmotoren og sammenligner med `expected_outcomes.csv`.

**API-tester** bruker FastAPIs `TestClient` og verifiserer statuskodene: 200 for gyldig portefølje, 200 for ugyldig portefølje, 400 for ukjent ticker, tom liste og duplikate tickere, og 422 for vekt utenfor gyldig område.

I tillegg testes optimeringen mot alle ugyldige eksempelporteføljer, med krav om at resultatet faktisk er gyldig, at ingen posisjon havner under minsteterskelen, og at ingen instrumenter med ukjent klassifisering introduseres.

## Avvik i datasettet

`expected_outcomes.csv` er ikke fullt konsistent med `rules.csv`. Tre porteføljer er merket som gyldige, men bryter regler ved en bokstavelig lesning av regelsettet:

| Portefølje | Fasit | Faktisk resultat |
|---|---|---|
| P1_VALID_BALANCED | valid | US-eksponering 77 %, over grensen på 60 % |
| P6_NEAR_LIMITS | valid | US-eksponering 70 %, over grensen på 60 % |
| P7_DEFENSIVE | valid | US-eksponering 85 %, og 45 % i sektoren US Aggregate Bond, over grensen på 40 % |

`rules.csv` er behandlet som kilden til sannhet, i tråd med oppgavetekstens krav om at regelmotoren skal lese reglene fra filen. Avviket er ikke skjult i koden: testene dokumenterer det eksplisitt i en egen oversikt over kjente avvik, og de feiler dersom avviket blir noe annet enn det dokumenterte.

P5_UNKNOWN_INSTRUMENT har den tvetydige fasitverdien `warning_or_invalid`. Siden regelen om ukjent klassifisering har `severity: warning` i `rules.csv`, gir motoren alltid en gyldig portefølje med en advarsel. Testen aksepterer begge utfall eksplisitt fremfor å tvinge frem ett av dem.

## Deploy

Løsningen kjører på Azure App Service med Linux og Python 3.13, på gratisplanen F1.

Hver push til `main` utløser en GitHub Actions-workflow som bygger applikasjonen, installerer avhengighetene fra `requirements.txt` og deployer til App Service. Workflow-filen ligger under `.github/workflows/`.

Applikasjonen startes med gunicorn og uvicorn-workers:

```
gunicorn -w 2 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000
```

Gunicorn håndterer prosessene, mens uvicorn-workeren gir den ASGI-støtten FastAPI krever.


## Antakelser og begrensninger

**`metric_definition` tolkes med søkeord.** Innenfor `portfolio`- og `holding`-scopene skilles reglene fra hverandre ved å se etter nøkkelord i fritekstfeltet, for eksempel om det nevner antall eller ukjent klassifisering. Dette er skjørt hvis teksten omformuleres. Alternativene var å hardkode `rule_code` i koden eller kreve en ekstra kolonne i datasettet. Løsningen holder koden lesbar og datafilen uendret, og begrensningen er kjent. Sjekken er dessuten implementert flere steder, både i regelmotoren og i optimeringen, noe som forsterker skjørheten. En delt hjelpefunksjon for tolkningen ville vært en forbedring.

**Ukjent klassifisering.** En posisjon regnes som ukjent klassifisert hvis aktivaklasse, sektor eller geografi er `Unknown`. `Unknown` behandles som en egen gruppe i eksponeringene og skjules ikke, slik at brukeren ser hvor stor andel av porteføljen som er uklassifisert.

**Geografi behandles som gjensidig utelukkende grupper.** `Global` og `Global ex-US` er egne kategorier og fordeles ikke ut på underliggende markeder. Det følger klassifiseringen i `instruments.csv`.

**Manglende totalvekt håndteres ikke spesielt.** Kvadrert avvik favoriserer spredning, så en portefølje som mangler vekt får den fordelt over flere posisjoner fremfor proporsjonal oppskalering av de eksisterende. Minsteterskelen på 2 prosentpoeng demper effekten betydelig. En mer treffende løsning ville vært å skalere de eksisterende posisjonene proporsjonalt før optimeringen, men det er ikke implementert.

**Kardinalitetskravet løses heuristisk.** Kravet om minimum antall posisjoner håndteres som etterbehandling og ikke som en bibetingelse, siden det ikke er konvekst. Resultatet er gyldig, men ikke nødvendigvis globalt optimalt.

**Forklaringene i `change_summary` er heuristiske.** De utledes fra gruppemedlemskap og endringsretning, og treffer ikke alltid den faktiske årsaken til en enkelt endring. Ved usikkerhet brukes en generisk begrunnelse.

**Feil i `rules.csv` stopper oppstart.** Ukjent operator eller et scope-mønster motoren ikke kjenner gjør at applikasjonen ikke starter, med `rule_code` oppgitt i feilmeldingen. En kjørende applikasjon som stille ignorerer en regel ville vært verre enn en som nekter å starte.
