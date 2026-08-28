## Referanser
- docs/oppgavetekst.md — oppgaveteksten fra arbeidsgiver
- data/rules.csv — regelsettet, kilden til all validering

# Prosjektkontekst
Jobbcase: portefølje-regelmotor. Python + FastAPI, deploy til Azure App Service.
Jeg skal kunne forklare all koden muntlig i intervju.

## Arbeidsmåte
- Forklar designvalg før du skriver kode, ikke etter
- Én modul om gangen, ikke hele prosjektet på én gang
- Ikke legg til nye avhengigheter uten å spørre først
- Kommenter kun der det er ikke-åpenbart hvorfor
- Svar på norsk

## Arkitekturregler
- app/domain/ skal aldri importere fastapi eller lese filer
- Terskler kommer fra data/rules.csv, aldri hardkodet
- Konfigurasjon via miljøvariabler (app/config.py)