# portfolio-rule-engine
Fullstack portfolio validation tool — FastAPI + Azure

## Datalag
Instrumentene leses fra data/instruments.csv ved oppstart av applikasjonen. Lesingen er lagt til app/data/loader.py, som bruker csv.DictReader fra standardbiblioteket. Pandas ville vært et unødvendig tungt valg for 17 rader — det gir en stor avhengighet og tregere oppstart uten å tilføre noe, siden dataene uansett skal konverteres til objekter.

Hver rad blir til en Instrument, en Pydantic-modell definert i app/models/instrument.py. Samme modell brukes både som API-respons og i domenelogikken. Det er et bevisst valg: å ha to nesten identiske modeller med en oversetter mellom ville gitt kode uten nytteverdi i et prosjekt av denne størrelsen. Avhengigheten går til Pydantic, ikke til FastAPI, så domenelaget forblir fritt for webrammeverket.

InstrumentRepository i app/data/repository.py holder instrumentene i en dictionary med ticker som nøkkel og gir oppslag til resten av applikasjonen. Konstruktøren tar imot en ferdig liste, mens from_csv() er en egen klassemetode. Det skillet gjør at repositoryet kan opprettes med testdata uten at filer er involvert.

Repositoryet instansieres én gang ved oppstart via FastAPIs lifespan og gjøres tilgjengelig for endepunktene gjennom dependency injection. Feiler CSV-lesingen, starter ikke applikasjonen — en app som kjører uten data ville feilet senere og mer uforståelig.

Filstien hentes fra miljøvariabelen DATA_DIR via app/config.py og bygges med pathlib relativt til prosjektrota, slik at den ikke avhenger av hvilken mappe applikasjonen startes fra.

## Regelmotor
Regelsettet leses fra data/rules.csv ved oppstart. Ingen terskler, operatorer, alvorlighetsgrader eller regeltekster finnes i koden. De kommer utelukkende fra filen. Rule-modellen i app/models/rule.py er et flatt speilbilde av en CSV-rad og tolker ingenting selv. All tolkning skjer i regelmotoren.

Hvordan rules.csv tolkes

`scope`-kolonnen avgjør hvordan en regel måles. Den har fire mønstre:

* `portfolio` gir ett tall for hele porteføljen, som totalvekt og antall posisjoner
* `holding` gir en aggregert måling per posisjon, som maks enkeltposisjon
* `asset_class:<verdi>` måler eksponering mot én bestemt aktivaklasse, som aksjer eller renter
* `sector` og `geography` måler største eksponering på tvers av alle grupper i dimensjonen

Motoren mapper på mønster, ikke på rule_code. Fem evaluatorer dekker alle åtte regler. Konsekvensen er at nye regler som passer inn i et eksisterende mønster kan legges til i CSV-filen uten kodeendring, for eksempel asset_class:Alternatives med en ny terskel. Bare en helt ny målemetode ville krevd ny kode.

Evaluering

Hver evaluator returnerer ett tall og hvilken gruppe tallet gjelder for. Sammenligningen mot terskelen gjøres av én generisk funksjon som tolker operator-kolonnen. <= og >= er inklusive, og alle sammenligninger bruker en toleranse på 0,01 prosentpoeng. Uten toleransen ville flyttallsavrunding fått gyldige porteføljer til å feile på kravet om nøyaktig 100 % totalvekt.

severity-kolonnen avgjør om et regelbrudd havner under violations eller warnings. En portefølje er gyldig hvis den ikke har noen violations. Warnings gjør den ikke ugyldig.

Eksponeringene beregnes én gang per validering og gjenbrukes av alle reglene. Samme objekt returneres i API-responsen, slik at brukeren ser tallene reglene faktisk ble målt mot.

Forklarbare resultater

Hvert regelbrudd returnerer rule_code, severity, beskrivelsen fra description_no, målt verdi, operator, terskel, hvilken gruppe det gjelder, og hvor mye grensen er overskredet. Beskrivelsen kommer direkte fra CSV-filen, slik at responsen bygges på regeldefinisjonene og ikke på tekster i koden.

Antakelser og forenklinger

metric_definition er et fritekstfelt. Innenfor portfolio- og holding-scopene brukes en enkel søkeordsjekk for å skille reglene fra hverandre, for eksempel om feltet nevner antall eller ukjent klassifisering. Dette er skjørt hvis teksten omformuleres. Alternativene var å hardkode rule_code i koden eller kreve en ekstra kolonne i datasettet. Løsningen er valgt fordi den holder koden lesbar og filen uendret, og begrensningen er kjent.

En posisjon regnes som ukjent klassifisert hvis aktivaklasse, sektor eller geografi er Unknown. Unknown behandles som en egen gruppe i eksponeringene og skjules ikke, slik at brukeren ser hvor stor andel av porteføljen som er uklassifisert.

Feil i rules.csv, som ukjent operator eller et scope-mønster motoren ikke kjenner, gjør at applikasjonen ikke starter. rule_code oppgis i feilmeldingen. En kjørende applikasjon som stille ignorerer en regel ville vært verre enn en som nekter å starte.

## API og feilhåndtering
POST /validate tar imot en portefølje og returnerer valideringsresultatet. Feilhåndteringen skiller mellom to ting som er lette å blande sammen.

Ugyldig input gir en feilkode. Formatfeil som manglende felt, feil datatype eller vekt utenfor 0 til 100 fanges av Pydantic-modellene og gir 422 uten at det er skrevet kode for det. Semantiske feil som krever oppslag i datasettet gir 400: ukjent ticker, tom portefølje, eller samme ticker oppgitt flere ganger. Ved ukjente tickere listes alle opp samtidig, slik at brukeren kan rette alt i én omgang.

En portefølje som bryter reglene er ikke en feil. Den gir 200 OK med portfolio_valid: false og en liste over bruddene. Forespørselen ble behandlet korrekt. Svaret er bare at porteføljen ikke består, og det er hele formålet med endepunktet.

Domenelaget kjenner ikke til HTTP. Når det møter noe det ikke kan behandle, kaster det en vanlig ValueError, og API-laget oversetter den til riktig statuskode.