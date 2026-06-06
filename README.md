# Ochrona sygnalistów - Quiz

Aplikacja Streamlit do nauki pytań z zakresu ochrony sygnalistów.

## Funkcje

- pełny quiz, szybki quiz losowy i quiz celowany,
- powtórki pytań z błędnymi odpowiedziami,
- przegląd bazy pytań z wyszukiwarką i filtrami,
- podsumowanie sesji z listą pytań do poprawki.

## Jak uruchomić lokalnie

1. Zainstaluj zależności:

   ```bash
   pip install -r requirements.txt
   ```

2. Uruchom aplikację:

   ```bash
   streamlit run streamlit_app.py
   ```

## Baza pytań

Plik `baza_pytan.json` zawiera 90 pytań jednokrotnego wyboru ułożonych na podstawie notatki `Ochrona sygnalistów + zagadnienia.pdf`, ze szczególnym naciskiem na pierwsze 11 stron.
