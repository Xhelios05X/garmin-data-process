# Słownik danych — eksport Garmin Connect

> Projekt: `garmin_process` (subprojekt Health Trackera)
> Urządzenie: Garmin Venu 3
> Wersja słownika: 0.1 (2026-10-04)
> Zakres danych w eksporcie: 2025-12-19 → 2026-09-01 (257 dni)

Ten dokument opisuje, **co** jest w eksporcie, **w jakich jednostkach** i **jak to czyścić**,
zanim cokolwiek zostanie policzone. Każda reguła z sekcji 2 powinna mieć swój test jednostkowy.

---

## 1. Lokalizacja i źródła

Dane leżą w `garmin_exports/` w katalogu projektu (**ignorowane przez git**).
Interesuje nas wyłącznie katalog `DI_CONNECT/` — pozostałe katalogi eksportu ignorujemy.

| Źródło | Ścieżka (w `DI_CONNECT/`) | Wzorzec nazwy | Ziarno | Status |
|---|---|---|---|---|
| Podsumowania dzienne (UDS) | `DI-Connect-Aggregator/` | `UDSFile_*.json` | 1 rekord = 1 dzień | MVP |
| Status zdrowia (HRV itd.) | `DI-Connect-Wellness/` | `*_healthStatusData.json` | 1 rekord = 1 noc | MVP |
| Sen | `DI-Connect-Wellness/` | `*_sleepData.json` | 1 rekord = 1 noc | MVP |
| Aktywności (podsumowania) | `DI-Connect-Fitness/` | `*_summarizedActivities.json` | 1 rekord = 1 trening | Faza 2b |
| Pliki FIT | `DI-Connect-Uploaded-Files/` | `*.zip` → `*.fit` | dane sekundowe | Później |
| Metryki (VO2max) | `DI-Connect-Metrics/` | `MetricsMaxMetData*.json` | — | Do zbadania |

Format wszystkich plików JSON: **tablica obiektów** (`[ {...}, {...} ]`).

---

## 2. Reguły ogólne (normalizacja)

### R1. Wiele plików na jedno źródło
Garmin dzieli dane na pliki po zakresach dat (np. UDS: 57 + 100 + 100 dni).
→ Wczytać wszystkie pliki danego wzorca, skleić, **posortować po `calendarDate`**,
**usunąć duplikaty dni** (zostawić ostatni wpis). Kolejność plików z `find` nie jest gwarantowana.

### R2. Wartości-wartowniki (sentinel values) → NaN
| Pole | Wartość | Znaczenie | Akcja |
|---|---|---|---|
| `averageStressLevel` (dowolny typ) | `< 0` (np. `-1`, `-2`) | brak pomiaru | → NaN |
| `baselineUpperLimit`, `baselineLowerLimit` | `0.0` | baseline jeszcze nie ustalony | → NaN |
| dowolne pole liczbowe | `null` | brak danych | → NaN |
| `metrics[].value` | **brak klucza** | brak pomiaru (np. SPO2) | → NaN, bez wyjątku |

### R3. Czas i strefy czasowe
- `calendarDate` to **lokalna** data dnia — główny klucz łączenia źródeł.
- Pola `*GMT` / `*Gmt` / `*UTC` są w UTC → konwersja przez `zoneinfo.ZoneInfo("Europe/Warsaw")`.
  **Nigdy** nie dodawać sztywnego offsetu (+1 zimą, +2 latem — DST).
- Pola `*Timestamp` typu liczbowego (np. `restingHeartRateTimestamp`) to **epoch w milisekundach**.
- Format stringów czasu: `"2026-02-15T01:08:45.0"` (bez strefy w stringu — strefę określa nazwa pola).

### R4. Przypisanie nocy do dnia
Dane nocne (`sleepData`, `healthStatusData`) mają `calendarDate` = **dzień przebudzenia**.
Noc 19→20.12 ma `calendarDate = 2025-12-20`.

### R5. Ważność danych — per metryka, nie per dzień
Dzień, w którym zegarek był noszony tylko w nocy, jest bezwartościowy dla kroków,
ale poprawny dla RHR i HRV. Każda metryka ma własną regułę ważności (sekcja 4).
Nieważnych wartości **nie usuwamy** — oznaczamy flagą i pomijamy w agregatach.

### R6. Minimalizacja danych
Parser **odrzuca od razu** wszystkie identyfikatory:
`userProfilePK`, `userProfilePk`, `uuid`, `deviceId` oraz e-mail z nazw plików.
Nie są potrzebne do żadnych obliczeń.

### R7. Zaokrąglenia
Wartości float z szumem (np. `avgSleepStress: 29.149999618530273`) zaokrąglamy do 1 miejsca po przecinku.

---

## 3. Słownik pól

### 3.1 UDS — podsumowania dzienne (`UDSFile_*.json`)

**Pola płaskie**

| Pole | Typ | Jednostka | Opis | Użycie |
|---|---|---|---|---|
| `calendarDate` | str (YYYY-MM-DD) | — | lokalny dzień | klucz |
| `restingHeartRate` | int / null | bpm | tętno spoczynkowe dnia | MVP: RHR |
| `totalSteps` | int / null | kroki | suma kroków | MVP: aktywność |
| `dailyStepGoal` | int | kroki | cel dzienny | % realizacji |
| `totalDistanceMeters` | int | m | dystans dzienny | opcjonalnie |
| `activeSeconds` | int | s | czas aktywny | pomocniczo |
| `highlyActiveSeconds` | int | s | czas bardzo aktywny | pomocniczo |
| `moderateIntensityMinutes` | int | min | minuty umiarkowanej intensywności | MVP: aktywność |
| `vigorousIntensityMinutes` | int | min | minuty wysokiej intensywności | MVP: aktywność |
| `userIntensityMinutesGoal` | int | min / tydzień | cel tygodniowy (domyślnie 150) | MVP: aktywność |
| `minHeartRate`, `maxHeartRate` | int | bpm | min/max tętna dnia | opcjonalnie |
| `totalKilocalories` | float | kcal | wydatek całkowity | opcjonalnie |
| `activeKilocalories` | float | kcal | wydatek aktywny | opcjonalnie |
| `floorsAscendedInMeters` | float | **m** (nie piętra!) | przewyższenie w górę | opcjonalnie |
| `includesWellnessData` | bool | — | czy są dane z zegarka | flaga jakości |
| `wellnessStartTimeLocal` | str | czas lokalny | początek doby | pomocniczo |
| `wellnessStartTimeGmt` | str | UTC | początek doby | pomocniczo |
| `restingHeartRateTimestamp` | int | **epoch ms** | moment wyznaczenia RHR | pomijamy |
| `userProfilePK`, `uuid` | — | — | identyfikatory | **odrzucamy (R6)** |

**Obiekt `allDayStress`** → spłaszczyć po `aggregatorList[].type`

| Ścieżka | Jednostka | Kolumna docelowa | Uwagi |
|---|---|---|---|
| `aggregatorList[type=TOTAL].averageStressLevel` | 0–100 | `stress_avg_total` | <0 → NaN |
| `aggregatorList[type=AWAKE].averageStressLevel` | 0–100 | `stress_avg_awake` | <0 → NaN; **MVP** |
| `aggregatorList[type=ASLEEP].averageStressLevel` | 0–100 | `stress_avg_asleep` | <0 → NaN (często `-2`) |
| `aggregatorList[*].maxStressLevel` | 0–100 | `stress_max_*` | opcjonalnie |

**Obiekt `bodyBattery`** → spłaszczyć po `bodyBatteryStatList[].bodyBatteryStatType`

| Ścieżka | Jednostka | Kolumna docelowa | Uwagi |
|---|---|---|---|
| `chargedValue` | pkt | `bb_charged` | ile się naładowało |
| `drainedValue` | pkt | `bb_drained` | ile się rozładowało |
| `bodyBatteryStatList[HIGHEST].statsValue` | 0–100 | `bb_highest` | **MVP** — poziom po regeneracji |
| `bodyBatteryStatList[LOWEST].statsValue` | 0–100 | `bb_lowest` | — |
| `bodyBatteryStatList[STARTOFDAY].statTimestamp` | czas lokalny | `bb_start_time` | późna godzina = zegarek założony w trakcie dnia |
| `bodyBatteryStatList[].bodyBatteryStatus` | kategoria | — | widziane: `MEASURED`; inne wartości do sprawdzenia |

Pozostałe typy w liście: `MOSTRECENT`, `ENDOFDAY` — pomijamy.

**Obiekt `respiration`**

| Ścieżka | Jednostka | Kolumna docelowa |
|---|---|---|
| `avgWakingRespirationValue` | oddechy/min | `resp_avg_awake` |
| `lowestRespirationValue` / `highestRespirationValue` | oddechy/min | opcjonalnie |

---

### 3.2 Status zdrowia (`*_healthStatusData.json`)

Rekord: `calendarDate` (dzień przebudzenia, R4) + lista `metrics[]`.
→ Spłaszczyć po `metrics[].type`.

| Typ (`type`) | Pole | Jednostka | Kolumna docelowa | Uwagi |
|---|---|---|---|---|
| `HRV` | `value` | ms | `hrv_night` | **MVP** — nocne HRV |
| `HRV` | `status` | kategoria | `hrv_status_garmin` | np. `ONBOARDING`; druga opinia dla LLM |
| `HRV` | `baselineLowerLimit` / `baselineUpperLimit` | ms | `hrv_baseline_lo/hi_garmin` | **0.0 → NaN** (R2) |
| `HR` | `value` | bpm | `hr_night` | tętno nocne — **inne źródło niż RHR z UDS, nie mieszać** |
| `RESPIRATION` | `value` | oddechy/min | `resp_night` | opcjonalnie |
| `SPO2` | `value` | % | — | brak klucza `value` — pomijamy |
| `SKIN_TEMP_C` | `value` | °C | — | brak danych — pomijamy |

Pola `percentage`, `feedbackKey`, `createTimestampUTC`, `updateTimestampUTC`, `outliersCount` — pomijamy.

---

### 3.3 Sen (`*_sleepData.json`)

Rekord: jedna noc, `calendarDate` = dzień przebudzenia (R4).

| Pole | Typ | Jednostka | Kolumna docelowa | Uwagi |
|---|---|---|---|---|
| `calendarDate` | str | — | klucz | — |
| `sleepStartTimestampGMT` | str | UTC | `sleep_start_local` | → Europe/Warsaw (R3) |
| `sleepEndTimestampGMT` | str | UTC | `sleep_end_local` | → Europe/Warsaw (R3) |
| `deepSleepSeconds` | int | s | `sleep_deep_s` | — |
| `lightSleepSeconds` | int | s | `sleep_light_s` | — |
| `remSleepSeconds` | int | s | `sleep_rem_s` | — |
| `awakeSleepSeconds` | int | s | `sleep_awake_s` | czas wybudzeń w oknie snu |
| `unmeasurableSeconds` | int | s | `sleep_unmeasurable_s` | flaga jakości |
| `awakeCount` | int | szt. | `sleep_awake_count` | — |
| `restlessMomentCount` | int | szt. | — | opcjonalnie |
| `avgSleepStress` | float | 0–100 | `sleep_stress_avg` | zaokrąglić (R7) |
| `averageRespiration` | float | oddechy/min | — | opcjonalnie |
| `sleepScores.overallScore` | int | 0–100 | `sleep_score` | **MVP** |
| `sleepScores.qualityScore` / `durationScore` / `recoveryScore` | int | 0–100 | opcjonalnie | — |
| `sleepScores.feedback` | str | kategoria | `sleep_feedback` | przekazać LLM jako tekst |
| `sleepScores.insight` | str | kategoria | `sleep_insight` | przekazać LLM jako tekst |
| `sleepWindowConfirmationType` | str | kategoria | — | widziane: `ENHANCED_CONFIRMED_FINAL`; inne do sprawdzenia |
| `retro` | bool | — | — | znaczenie do sprawdzenia |
| `spo2SleepSummary` | obiekt | — | — | zawiera `deviceId`, `userProfilePk` → **odrzucamy (R6)** |

**Niezmiennik (test!):**
`deep + light + rem + awake (+ unmeasurable) == sleepEnd − sleepStart` (w sekundach).
Przykład 2026-02-15: 5340 + 14400 + 900 + 6540 = 27180 s = 7h33m ✔

---

## 4. Reguły ważności (per metryka)

| Metryka | Wartość ważna, gdy… | Uzasadnienie |
|---|---|---|
| Kroki | `totalSteps` nie null **i** `≥ 500` (próg konfigurowalny) | dni z zegarkiem tylko w nocy / założonym wieczorem |
| RHR | `restingHeartRate` nie null | wymaga tylko noszenia w spoczynku |
| HRV | `hrv_night` nie NaN | — |
| Sen | rekord istnieje **i** niezmiennik z 3.3 spełniony | — |
| Stres | `stress_avg_awake` ≥ 0 | R2 |

Znane przypadki brzegowe: 3 dni z `totalSteps = null`; 2025-12-19 — zegarek założony ok. 20:38 (428 kroków).

---

## 5. Metryki pochodne (liczy Python, nie LLM)

| Metryka | Definicja | Grupa MVP |
|---|---|---|
| `rhr_7d` | średnia krocząca 7 dni z ważnych wartości RHR | 1. RHR |
| `rhr_baseline_28d` | średnia krocząca 28 dni RHR | 1. RHR |
| `rhr_delta` | `rhr_7d − rhr_baseline_28d` (bpm) | 1. RHR |
| `hrv_7d` | średnia krocząca 7 dni `hrv_night` | 2. HRV |
| `hrv_baseline_28d` | średnia krocząca 28 dni `hrv_night` (własny baseline) | 2. HRV |
| `hrv_delta_pct` | `(hrv_7d − hrv_baseline_28d) / hrv_baseline_28d × 100` | 2. HRV |
| `sleep_total_s` | `deep + light + rem` | 3. Sen |
| `sleep_efficiency` | `sleep_total_s / (sleepEnd − sleepStart)` | 3. Sen |
| `sleep_score_7d` | średnia 7 dni `sleep_score` | 3. Sen |
| `bedtime_std_7d` | odchylenie standardowe lokalnej godziny zaśnięcia z 7 dni (minuty) | 3. Sen |
| `steps_7d` | średnia 7 dni z ważnych dni | 4. Aktywność |
| `intensity_min_week` | `Σ moderate + 2 × Σ vigorous` w tygodniu kalendarzowym | 4. Aktywność |
| `intensity_goal_pct` | `intensity_min_week / userIntensityMinutesGoal × 100` | 4. Aktywność |
| `stress_awake_7d` | średnia 7 dni `stress_avg_awake` | 5. Stres/BB |
| `bb_highest_7d` | średnia 7 dni `bb_highest` | 5. Stres/BB |

Uwagi:
- Średnie kroczące liczone tylko z ważnych wartości; wymagane minimum ważnych dni w oknie (np. 4/7, 20/28) — inaczej wynik = NaN.
- Do `bedtime_std_7d` godziny po północy traktować jako ciąg dalszy wieczoru (np. 01:30 → 25:30), inaczej odchylenie wyjdzie absurdalne.

---

## 6. Otwarte pytania / TODO

- [ ] Struktura `*_summarizedActivities.json` (Faza 2b) — jednostki czasu, dystansu, prędkości.
- [ ] Zawartość `MetricsMaxMetData*.json` (VO2max).
- [ ] Możliwe wartości `bodyBatteryStatus` i `sleepWindowConfirmationType`.
- [ ] Znaczenie pola `retro` w `sleepData`.
- [ ] Od kiedy HRV ma status inny niż `ONBOARDING` (koniec okresu kalibracji)?
- [ ] Czy `healthStatusData` i `sleepData` mają rekord na każdą noc z UDS (pokrycie)?