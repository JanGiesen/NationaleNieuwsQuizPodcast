# Nationale Nieuwsquiz -> podcastfeed

Dit repo houdt automatisch een RSS/podcastfeed bij van "De Nationale
Nieuwsquiz" (het dagelijkse onderdeel van Spraakmakers op NPO Radio 1).
Een GitHub Action controleert een paar keer per dag de fragmentenpagina
van NPO Radio 1, en zet nieuwe afleveringen in `docs/feed.xml`. Die map
wordt via GitHub Pages als gewone website gepubliceerd, dus de feed
krijgt een vaste, publieke URL die je in elke podcast-app kunt
toevoegen.

**Let op:** NPO biedt dit zelf niet als podcast aan. Dit script haalt de
audio-url met een best-effort methode uit de paginabron. Als NPO ooit de
site-structuur wijzigt, kan het stukgaan (zie "Problemen oplossen"
hieronder). Gebruik de feed alleen voor persoonlijk gebruik.

## Installatie (eenmalig)

1. **Maak een nieuwe (public) GitHub-repository** en zet alle bestanden
   uit deze map erin (`build_feed.py`, `requirements.txt`,
   `.github/workflows/build-feed.yml`, `docs/feed.xml`).

2. **Zet GitHub Pages aan:**
   Ga naar *Settings -> Pages*. Bij "Build and deployment" kies je
   Source: **Deploy from a branch**, Branch: **main**, map: **/docs**.
   Klik Save. Na een minuutje toont GitHub de publieke URL, iets als:
   `https://<jouw-gebruikersnaam>.github.io/<repo-naam>/`

3. **Zet de FEED_BASE_URL variabele:**
   Ga naar *Settings -> Secrets and variables -> Actions -> tab
   "Variables"*. Klik "New repository variable":
   - Name: `FEED_BASE_URL`
   - Value: de Pages-URL uit stap 2, **zonder** slash op het einde
     (bv. `https://janhuissen.github.io/npo-nieuwsquiz-podcast`)

4. **Draai de workflow voor het eerst:**
   Ga naar het tabblad *Actions*, kies "Build Nieuwsquiz podcast feed"
   in de lijst links, klik "Run workflow" -> "Run workflow". Wacht tot
   het groene vinkje verschijnt (duurt meestal 1-2 minuten).

5. **Controleer de feed:**
   Open `https://<jouw-pages-url>/feed.xml` in je browser. Je zou nu XML
   moeten zien met een of meer `<item>`-afleveringen erin.

6. **Abonneer in je podcast-app** met die feed.xml-URL, bijvoorbeeld:
   - Apple Podcasts: Bibliotheek -> ... -> "Programma via URL toevoegen"
   - Overcast: + -> "Add URL"
   - Pocket Casts: Zoeken -> plak de URL

Daarna hoef je niets meer te doen: de Action draait automatisch elke
dag rond 14:00 en 17:00 (Nederlandse tijd, afhankelijk van zomer-/
wintertijd) en zet nieuwe afleveringen vanzelf in de feed.

## Problemen oplossen

- **"no audio URL found" in de Action-log:** NPO heeft de pagina-opbouw
  aangepast en het script kan de audio-link niet meer vinden. Stuur me
  de logregel en de betreffende fragment-URL, dan pas ik
  `find_audio_url()` in `build_feed.py` aan.
- **Feed blijft leeg na de eerste run:** controleer of `FEED_BASE_URL`
  goed staat en of Pages daadwerkelijk vanaf de `docs`-map serveert
  (stap 2).
- **Meer geschiedenis in één keer ophalen:** verhoog eenmalig de
  `MAX_PAGES`-omgevingsvariabele in de workflow (standaard 5 paginas
  van de fragmentenlijst).

## Bestanden

- `build_feed.py` -- het scrape- en feedgeneratiescript.
- `.github/workflows/build-feed.yml` -- de geplande GitHub Action.
- `docs/feed.xml` -- de gepubliceerde podcastfeed (wordt overschreven).
- `docs/state.json` -- interne boekhouding van welke afleveringen al in
  de feed staan (wordt automatisch bijgewerkt, niet zelf aanpassen).
