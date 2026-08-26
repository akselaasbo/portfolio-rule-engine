# Datasett til case: Portefølje-regelmotor

Dette datasettet er laget for et programmeringscase der kandidaten skal bygge en fullstack-applikasjon
med backend i Python + FastAPI. Målet er å validere en foreslått portefølje mot et sett med investeringsregler.

## Filer

### 1. instruments.csv
Oppslagsfil for gyldige instrumenter.

Kolonner:
- ticker: unik identifikator
- name: instrumentnavn
- asset_class: aktivaklasse, f.eks. Equity, Fixed Income, Real Estate, Cash
- sector: sektor/kategori brukt i eksponeringsberegninger
- geography: geografisk eksponering
- instrument_type: type instrument
- expense_ratio_pct: årlig kostnadsprosent

Brukes til:
- validering av ticker
- oppslag av aktivaklasse, sektor og geografi
- beregning av aggregert eksponering

### 2. sample_portfolios.csv
Eksempelporteføljer som skal valideres.

Kolonner:
- portfolio_id: identifikator for porteføljen
- ticker: instrument i porteføljen
- weight_pct: porteføljevekt i prosent

Brukes til:
- input til regelmotoren
- demo-data for UI og API
- testing av gyldige og ugyldige porteføljer

### 3. rules.csv
Regelsett for porteføljevalidering.

Kolonner:
- rule_code: unik kode for regelen
- severity: error eller warning
- metric_definition: beskriver hva som skal måles
- scope: hvilket nivå regelen gjelder for
- operator: sammenligningsoperator
- threshold: terskelverdi
- description_no: norsk beskrivelse av regelen

Brukes til:
- å gjøre regelmotoren mer konfigurerbar
- å returnere forklarbare valideringsresultater

### 4. expected_outcomes.csv
En enkel fasitfil med forventet hovedutfall per eksempelportefølje.

Kolonner:
- portfolio_id: identifikator
- expected_result: forventet hovedutfall
- notes_no: kort forklaring

Brukes til:
- manuell verifisering
- enklere demo under utvikling

## Viktige merknader
- Kandidaten trenger ikke å bruke alle filene.
- Det er helt greit å starte med hardkodede regler og senere lese dem fra rules.csv.
- Backend er viktigst i caset.
- Løsningen bør returnere tydelige violations, warnings og aggregert eksponering.
