# Programmeringscase: Portefølje-regelmotor

> Oppgavetekst fra arbeidsgiver. Kopiert til markdown for enkel referanse i repoet.

## Innhold

- [Bakgrunn](#bakgrunn)
- [Oppgave](#oppgave)
- [Teknologikrav](#teknologikrav)
- [Datasett](#datasett)
- [Kravspesifikasjon](#kravspesifikasjon)
- [Ikke-funksjonelle krav](#ikke-funksjonelle-krav)
- [Forventet leveranse](#forventet-leveranse)
- [Hva vi vurderer](#hva-vi-vurderer)
- [Hint](#hint)

---

## Bakgrunn

I dette caset skal du bygge en enkel applikasjon som hjelper en rådgiver med å validere en foreslått investeringsportefølje mot et sett med investeringsregler.

Målet er å lage et lite beslutningsstøtteverktøy der brukeren kan sette sammen en portefølje, sende den til backend for validering, og få et tydelig svar på:

- om porteføljen oppfyller reglene
- hvilke regler som eventuelt brytes
- hvilken gyldig portefølje som ligger nærmest den opprinnelige

**Backend er den viktigste delen av dette caset.**

---

## Oppgave

Bygg en fullstack-applikasjon som sjekker om en portefølje er gyldig og kommer med forslag til gyldig portefølje hvis registrert portefølje ikke er gyldig.

Applikasjonen skal:

- la brukeren bygge en portefølje i et enkelt grensesnitt
- la brukeren velge instrumenter fra en dropdown
- la brukeren angi vekt per instrument
- sende porteføljen til backend for validering
- validere porteføljen mot et sett med regler
- vise om porteføljen består eller ikke
- vise hvilke regler som eventuelt brytes
- beregne en gyldig portefølje som ligger nærmest den opprinnelige
- vise relevante eksponeringer og forklaringer
- deployes til Azure som en App Service
- bruke GitHub Actions til build og deploy

---

## Teknologikrav

### Backend

Backend skal bygges i:

- Python
- FastAPI

Backend må:

- eksponere et HTTP API
- lese og prosessere data fra de vedlagte CSV-filene
- implementere regelmotoren
- lese reglene fra `rules.csv`
- beregne en gyldig portefølje som ligger nærmest den opprinnelige
- returnere tydelige og forklarbare resultater
- håndtere ugyldig eller ufullstendig input på en ryddig måte

### Frontend

Frontend kan bygges med valgfri teknologi.

Frontend skal minst gjøre det mulig å:

- hente en liste over tilgjengelige instrumenter
- velge instrumenter fra dropdown
- angi vekt per instrument
- legge til og fjerne rader i porteføljen
- sende porteføljen til validering
- vise resultatet på en enkel og forståelig måte

### Deploy / DevOps

Løsningen må:

- deployes til **Azure App Service**
- bruke **GitHub Actions** for:
  - build
  - deploy

---

## Datasett

Du skal bruke det vedlagte datasettet som input til løsningen.

Filer:

- `instruments.csv`
- `rules.csv`
- `sample_portfolios.csv`
- `expected_outcomes.csv`

Det følger også med en README-fil som forklarer filene og hvordan de kan brukes.

### Hvordan dataene er ment brukt

- `instruments.csv` brukes som oppslagsregister for instrumentene i dropdownen og for å hente metadata som aktivaklasse, sektor og geografi
- `rules.csv` skal brukes som grunnlag for regelmotoren
- `sample_portfolios.csv` og `expected_outcomes.csv` kan brukes som eksempeldata eller støtte under utvikling, men er ikke påkrevd i hovedløpet

### Regler som datasettet beskriver (rules.csv)

Datasettet inneholder regler for blant annet:

- total porteføljevekt
- maksimal enkeltposisjon
- maksimal aksjeeksponering
- minimum renteeksponering
- maksimal sektoreksponering
- maksimal geografieksponering
- minimum antall posisjoner
- håndtering av ukjent klassifisering

Du kan velge hvordan du mapper regeldefinisjonene i `rules.csv` til kode, men det skal være tydelig at `rules.csv` er kilden til regelsettet.

---

## Kravspesifikasjon

### Viktig krav 1: Reglene skal leses fra rules.csv

Regelmotoren skal ikke være fullt hardkodet.

Det er et krav at løsningen:

- leser inn reglene fra `rules.csv`
- bruker disse reglene i valideringen
- bygger responsen basert på regeldefinisjonene i filen

Det er helt greit å gjøre noen forenklinger i hvordan `rules.csv` tolkes, så lenge:

- reglene faktisk leses fra filen
- løsningen er konsistent
- antakelser og begrensninger forklares i README

Du trenger ikke å lage en helt generell regelmotor som kan støtte alle tenkelige regler. Det er tilstrekkelig å lage en løsning som bruker strukturen i `rules.csv` på en ryddig og tydelig måte for reglene i dette caset.

### Viktig krav 2: Finn en gyldig portefølje som ligger nærmest den opprinnelige

Dersom porteføljen ikke oppfyller reglene, skal løsningen beregne en **gyldig portefølje som ligger nærmest den opprinnelige**.

Du står fritt til å definere hva "nærmest" betyr, så lenge du:

- velger en tydelig metode
- forklarer den
- bruker den konsistent

Eksempler på hva "nærmest" kan bety:

- minst mulig total endring i vekter
- minst mulig kvadratisk avvik fra opprinnelige vekter
- færrest mulig endrede posisjoner
- minst mulig endring i porteføljens overordnede profil

Det er ikke nødvendig å finne en globalt optimal løsning, men løsningen skal faktisk forsøke å finne en gyldig portefølje som:

- tilfredsstiller reglene
- kan sammenlignes med den opprinnelige
- forklares på en forståelig måte

### 1. Vise tilgjengelige instrumenter

Applikasjonen skal hente instrumenter fra backend og vise dem i en dropdown.

Et instrument har blant annet:

- ticker
- navn
- aktivaklasse
- sektor
- geografi

### 2. La brukeren bygge en portefølje

Brukeren skal kunne:

- velge ett eller flere instrumenter
- angi vekt i prosent per instrument
- legge til og fjerne rader

### 3. Validere porteføljen

Når brukeren sender inn porteføljen, skal backend:

- validere input
- slå opp instrumentinformasjon
- beregne aggregert eksponering
- evaluere porteføljen mot reglene fra `rules.csv`
- returnere et strukturert resultat

### 4. Finne nærmeste gyldige portefølje

Når porteføljen ikke er gyldig, skal backend i tillegg:

- beregne en ny portefølje som oppfyller reglene
- forsøke å holde den så nær den opprinnelige som mulig
- forklare hvordan den nye porteføljen avviker fra den opprinnelige

### 5. Presentere resultatet

Applikasjonen skal vise:

- om porteføljen er gyldig eller ikke
- hvilke regler som eventuelt brytes
- eventuelle warnings
- relevante eksponeringer
- en foreslått gyldig portefølje
- forklaring på hva som er endret

### API-krav

Backend skal minst tilby:

- `GET /health`
- `GET /instruments`
- `POST /validate`

#### GET /instruments

Returnerer listen over tilgjengelige instrumenter.

#### POST /validate

Tar inn en portefølje som brukeren har satt sammen i UI.

Eksempel på request:

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

Responsen bør være strukturert og forklarbar, og kan for eksempel inneholde:

- `portfolio_valid`
- `violations`
- `warnings`
- `exposures`
- `nearest_valid_portfolio`
- `change_summary`
- `summary`

Du står fritt til å velge den konkrete responsstrukturen, så lenge den er lett å forstå.

---

## Ikke-funksjonelle krav

Vi forventer:

- ryddig prosjektstruktur
- lesbar og vedlikeholdbar kode
- tydelige modeller i FastAPI
- god separasjon mellom API-lag, datatilgang og regel-/domenelogikk
- konfigurasjon via miljøvariabler
- README med forklaring av valg og avgrensninger
- enkel og robust deploy til Azure App Service

---

## Forventet leveranse

Du skal levere:

- GitHub-repo med kode
- backend i **Python + FastAPI**
- enkel frontend
- README
- GitHub Actions workflow
- deployet løsning i Azure App Service
- kort beskrivelse av hvordan regelmotoren fungerer

README bør forklare:

- hvordan løsningen kjøres lokalt
- hvordan deploy fungerer
- hvilke antakelser som er gjort
- hvordan regelmotoren er bygget
- hvordan `rules.csv` tolkes og brukes
- hvordan "nærmest" er definert
- hvordan nærmeste gyldige portefølje beregnes

---

## Hva vi vurderer

Vi vurderer særlig:

- kvaliteten på FastAPI-backenden
- evnen til å strukturere backend-logikk ryddig
- kvaliteten på regelmotoren
- hvordan reglene fra `rules.csv` er modellert og brukt
- kvaliteten på metoden for å finne nærmeste gyldige portefølje
- kvaliteten på API-design og responsmodeller
- pragmatiske tekniske valg
- deploy og CI/CD-oppsett
- evnen til å forklare hvordan løsningen fungerer

---

## Hint

En god og enkel start kan være:

- Les `instruments.csv`
- Les `rules.csv`
- Lag `GET /instruments`
- Lag et enkelt UI med dropdown og vektfelt
- Implementer `POST /validate`
- Start med noen få regler først, men hent terskler og metadata fra `rules.csv`
- Utvid deretter med sektor, geografi og warnings
- Implementer en metode for å finne en gyldig portefølje som ligger nærmest den opprinnelige
- Forklar tydelig hvilke kompromisser du har valgt

Det er helt greit å gjøre rimelige forenklinger, så lenge du forklarer dem.

**Prioriter en enkel, robust og ferdig løsning fremfor mange halvferdige features.**

### Hint til hvordan "nærmest" kan modelleres

En mulig tilnærming er å modellere dette som et optimeringsproblem.

Du kan tenke deg at:

- de opprinnelige vektene er input
- de nye vektene er beslutningsvariabler
- reglene fra `rules.csv` er constraints
- målet er å finne en gyldig portefølje som er så lik den opprinnelige som mulig

Eksempler på mål:

- minimere summen av absolutte endringer i vekter
- minimere summen av kvadrerte endringer i vekter

Eksempler på constraints:

- totalvekt må være 100 %
- ingen enkeltposisjon kan overstige maksgrense
- aksjeeksponering kan ikke overstige gitt grense
- renteeksponering må være minst gitt grense
- sektor- og geografieksponering må være innenfor grensene

Det er også helt greit å bruke en enklere heuristisk tilnærming, for eksempel:

- identifiser regelbrudd
- reduser holdings som bidrar mest til bruddet
- flytt vekten til holdings som forbedrer porteføljen
- revalider resultatet

Det viktigste er ikke hvilken metode du velger, men at metoden er tydelig, fornuftig og godt forklart.
