# portfolio-rule-engine
Fullstack portfolio validation tool — FastAPI + Azure

## Datalag
Instrumentene leses fra data/instruments.csv ved oppstart av applikasjonen. Lesingen er lagt til app/data/loader.py, som bruker csv.DictReader fra standardbiblioteket. Pandas ville vært et unødvendig tungt valg for 17 rader — det gir en stor avhengighet og tregere oppstart uten å tilføre noe, siden dataene uansett skal konverteres til objekter.

Hver rad blir til en Instrument, en Pydantic-modell definert i app/models/instrument.py. Samme modell brukes både som API-respons og i domenelogikken. Det er et bevisst valg: å ha to nesten identiske modeller med en oversetter mellom ville gitt kode uten nytteverdi i et prosjekt av denne størrelsen. Avhengigheten går til Pydantic, ikke til FastAPI, så domenelaget forblir fritt for webrammeverket.

InstrumentRepository i app/data/repository.py holder instrumentene i en dictionary med ticker som nøkkel og gir oppslag til resten av applikasjonen. Konstruktøren tar imot en ferdig liste, mens from_csv() er en egen klassemetode. Det skillet gjør at repositoryet kan opprettes med testdata uten at filer er involvert.

Repositoryet instansieres én gang ved oppstart via FastAPIs lifespan og gjøres tilgjengelig for endepunktene gjennom dependency injection. Feiler CSV-lesingen, starter ikke applikasjonen — en app som kjører uten data ville feilet senere og mer uforståelig.

Filstien hentes fra miljøvariabelen DATA_DIR via app/config.py og bygges med pathlib relativt til prosjektrota, slik at den ikke avhenger av hvilken mappe applikasjonen startes fra.