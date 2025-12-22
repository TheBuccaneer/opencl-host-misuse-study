Hier ist ein Vorschlag für den **kompletten Inhalt einer einzigen Datei** (z.B. `2025-12-22_audit_GABGFX_CLIc.md`), in die erstmal alles reinkommt, was du später auf andere Dateien / Tabellen verteilen kannst.

Du musst nur den folgenden Block in eine Datei kopieren:

---

````markdown
# OpenCL Host Misuse Studie – Raw Notes (GABGFX + CLIc, 2025-12-22)

> **Hinweis an mich selbst:**
> Diese Datei ist **Sammelbecken** für alles von heute.
> Später aufteilen in:
> - projektspezifische Notizen,
> - CSV-Einträge (`projects.csv`, `verified_misuses.csv`),
> - evtl. kurze README-Schnipsel.

---

## 0. Kontext heute

- Fokus: neue Projekte für die OpenCL-Host-Misuse-Studie testen.
- Zwei Kandidaten:
  1. `Gabrax/GABGFX` → Graphics-Demo-Engine (raylib, assimp, OpenCL-SDK).
  2. `clEsperanto/CLIc` → moderne C++ OpenCL-Backend-Library für Bildverarbeitung.
- Ziel:
  - **GABGFX**: entscheiden, ob es mit vertretbarem Aufwand build- und toolrunnable ist.
  - **CLIc**: systematisch mit `oclgrind --check-api` über die Test-Suite gehen und Host-Misuses identifizieren.

---

## 1. Projekt: Gabrax / GABGFX

### 1.1. Kurzbeschreibung

- GitHub: `Gabrax/GABGFX`
- C++/CMake-Projekt, nutzt u.a.:
  - raylib
  - assimp (+ zlib etc.)
  - OpenCL-SDK
- Offiziell soll das Projekt **über ein externes Script** (`build.sh` aus dem GABBS-Repo) gebaut werden, nicht über direktes CMake.

### 1.2. Build-Versuche (chronologisch, kurz)

1. **Repo-Stand**

   ```bash
   git clone https://github.com/Gabrax/GABGFX.git
   cd GABGFX
   ls
   # CMakeLists.txt, src/, vendor/, res/, README.md, LICENSE, ...
````

2. **Build-Script holen**

   ```bash
   curl -O https://raw.githubusercontent.com/Gabrax/GABBS/refs/heads/main/build.sh
   chmod +x build.sh
   ```

3. **Erster Versuch mit `sh build.sh` (falsch)**

   * Aufruf:

     ```bash
     sh build.sh -Cgcc -Ddebug
     ```

   * Fehler:

     * `build.sh: [[: not found`
     * `Linux: not found`
     * `Unsupported OS: Linux`

   * Ursache: Script ist ein **Bash-Script** (`[[ ... ]]`), `sh` ist auf dem System `dash`.

   * → Korrektur: Script nur mit `./build.sh` oder `bash build.sh` ausführen.

4. **Versuch mit `./build.sh -Cgcc -Ddebug`**

   * Läuft deutlich weiter:

     * CMake-Konfiguration,
     * raylib & assimp-Subbuilds etc.

   * Build-Abbruch früh in vendored assimp/zlib:

     ```text
     [  1%] Building C object _deps/assimp-build/contrib/zlib/CMakeFiles/zlibstatic.dir/adler32.c.o
     gcc: error: unrecognized command-line option ‘-ferror-limit=0’
     gmake[2]: *** ... Error 1
     [*] Build failed
     ```

   * Interpretation:

     * `-ferror-limit=0` ist ein **Clang-Flag**, kein GCC-Flag.
     * Das GABGFX-/GABBS-Setup benutzt Clang-Flags auch im zlib/assimp-Teil.
     * Mit GCC bricht der Build daher ab.

5. **Versuche, Clang zu erzwingen**

   * Idee: `./build.sh -Cclang -Ddebug` mit `CC=clang CXX=clang++`.
   * Praktisches Problem:

     * Das Script meldet: `[*] Project already configured for RelWithDebInfo`
     * CMake-Konfiguration ist noch von GCC-Lauf → der zlib/assimp-Build wird weiterhin mit GCC + `-ferror-limit=0` gefahren.
   * Zwischenzeitlicher Versuch, CMake von Hand mit `CC=clang` aufzurufen, führte zu `add_executable("")`-Fehler → Script-internes Target-Setup wird dabei ausgehebelt.

6. **Weitere Versuche**

   * `rm -rf build`, danach erneut:

     ```bash
     CC=clang CXX=clang++ ./build.sh -Cclang -Ddebug
     ```

   * Ergebnis: Build bricht in vendored assimp ab mit Clang-spezifischen Warnings/Errors (z.B. `-Wnontrivial-memcall` auf `aiFace`/`aiMeshMorphKey`), teils kombiniert mit `-Werror`.

   * Für die Studie entscheidend:

     * Build scheitert **konsequent** an vendored Dependencies (assimp/zlib), nicht an eigenem GABGFX-Code oder OpenCL-Hostcode.
     * Ein Fix würde **Dependency-Patching** verlangen (assimp-Quellcode oder CMake-Flags) → deutlich über „Minimal-Patch“ hinaus.

### 1.3. Bewertung für die Studie

* **Build-Status:** *failed*

* **Grund:** Third-Party-Dependency-Probleme (assimp/zlib) mit Compiler-/Warning-Kombination (Clang/GCC + `-ferror-limit=0` / `-Wnontrivial-memcall`).

* **OpenCL-Relevanz:**

  * OpenCL-Hostcode wird überhaupt nicht erreicht, weil der Build schon in Dependencies scheitert.

* **Konsequenz für Dataset / CSV später:**

  Vorschlag für `projects.csv` (Skizze, nicht final):

  ```text
  project,build_status,tool_status,exclusion_reason,notes
  Gabrax/GABGFX,failed,skipped,third_party_dep_build_failure,Build via official build.sh fails in vendored assimp/zlib (Clang/GCC flags mismatch, -ferror-limit=0, -Wnontrivial-memcall); patching dependencies out-of-scope.
  ```

* Kein sinnvoller Aufwand, dieses Projekt jetzt noch weiter zu „retten“ → für die Pilot-Studie als **nicht nutzbar** markiert.

---

## 2. Projekt: clEsperanto / CLIc

### 2.1. Kurzbeschreibung

* GitHub: `clEsperanto/CLIc`
* Moderne C++-Library, die **OpenCL-Backend** für das clEsperanto-/CLIJ-Ökosystem bereitstellt.
* Fokus: GPU-beschleunigte Bildverarbeitung (3D-Arrays, Filter, Morphologie, Labeling, FFT, usw.).
* Struktur:

  * `clic/` – eigentliche Library (OpenCL-Backend, Array-/Image-Abstraktionen etc.)
  * `tests/` – umfangreiche Test-Suite (~188 GoogleTest-Binaries, in Tiers strukturiert).
  * `benchmark/`, `docs/`, Third-Party (Eigen, VkFFT, …).
* Ideal als Studienobjekt:

  * seriöses Projekt,
  * klarer OpenCL-Host-Backend,
  * umfangreiche Tests → perfekte Harnesses.

### 2.2. Build-Konfiguration

1. **CMake-Konfiguration**

   ```bash
   cd ~/.../CLIc
   mkdir -p build
   cd build
   cmake ..
   ```

   Wichtige Punkte aus der Ausgabe (gekürzt):

   * Compiler: `GNU 15.2.0` (C/C++).

   * `CMAKE_BUILD_TYPE: Release`

   * `Build tests: ON`

   * OpenCL:

     ```text
     Looking for CL_VERSION_3_0 - found
     Found OpenCL: /usr/lib/x86_64-linux-gnu/libOpenCL.so (version "3.0")
     OpenCL includes: /usr/include
     ```

   * Eigen, VkFFT etc. werden via FetchContent eingebunden.

   * Doxygen optional, nicht gefunden → nur Doku-Target betroffen.

2. **Build**

   ```bash
   cd build
   cmake --build .
   ```

   * Build läuft durch, keine harten Compilerfehler.
   * Ergebnis: Library + Test-Binaries in `build/tests/...`.

### 2.3. Tests als Harness (ctest-Überblick)

1. **Testübersicht**

   ```bash
   cd build
   ctest -N
   ```

   * Ergebnis: **188** registrierte Tests, z.B.:

     * `test_array`, `test_backends`, `test_device`, …
     * `test_add_image_and_scalar`, `test_fft`, `test_connected_component_labeling`, …
     * Tests sind in Tiers organisiert (tier1, tier7, tier8, …), plus `core`.

2. **Beispiel: Einzeltest nativ**

   ```bash
   ctest -R test_add_image_and_scalar -V
   ```

   * Startet `build/tests/tier1/test_add_image_and_scalar`.

   * GTest-Ausgabe:

     ```text
     [ RUN      ] InstantiationName/TestAddImageAndScalar.execute/0
     [       OK ] ... (ca. 325 ms)
     [  PASSED  ] 1 test.
     ```

   * Nativ (ohne Oclgrind) läuft der Test sauber durch → Test-Harness ist funktional.

### 2.4. Systematischer Lauf unter Oclgrind

#### 2.4.1. Script für komplette Suite

* In `build` wurde (sinngemäß) ein Script ausgeführt, das **alle Test-Binaries** mit `oclgrind --check-api` startet und in eine Logdatei schreibt. Typisches Muster:

  ```bash
  cd ~/.../CLIc/build

  mkdir -p oclgrind_logs

  find tests -type f -perm -u+x | sort | while read -r bin; do
    echo "===== RUNNING $bin =====" >> oclgrind_logs/all_tests.log
    oclgrind --check-api "./$bin" >> oclgrind_logs/all_tests.log 2>&1
    echo "" >> oclgrind_logs/all_tests.log
  done
  ```

* Ergebnis: `oclgrind_logs/all_tests.log` mit 188 Blöcken (`===== RUNNING tests/... =====`).

#### 2.4.2. Grobe Statistik aus dem Log

Auswertung (per Skript/Parsing):

* **Anzahl Tests:** 188
* **Tests mit Oclgrind-Runtime-Error:** 180
* **Tests mit Heap-Korruptionsmeldung:**

  * `free(): chunks in smallbin corrupted`: 144
  * `corrupted double-linked list`: 15
  * Insgesamt mind. eine der beiden Meldungen: 159
* **Tests mit GTest-FAIL (unter Oclgrind):** 8
* **Völlig saubere Tests (kein Oclgrind-Error, keine Heap-Fehler, GTest grün):** 8

Die 8 sauberen Tests:

* `tests/core/test_array`
* `tests/core/test_backends`
* `tests/core/test_create_dst`
* `tests/core/test_image`
* `tests/core/test_transform`
* `tests/tier1/test_copy`
* `tests/tier1/test_padding`
* `tests/tier7/test_deskew`

Die 8 Tests mit GTest-FAIL:

* `tests/core/test_device`
* `tests/tier1/test_detect_label_edge`
* `tests/tier1/test_equal`
* `tests/tier1/test_greater`
* `tests/tier1/test_greater_or_equal`
* `tests/tier1/test_not_equal`
* `tests/tier1/test_smaller`
* `tests/tier1/test_smaller_or_equal`

---

### 2.5. Gefundener Host-API-Misuse (clGetDeviceInfo)

#### 2.5.1. Oclgrind-Fehlermuster

In **180 von 188** Tests taucht derselbe Oclgrind-Fehler auf:

```text
Oclgrind - OpenCL runtime error detected
        Function: clGetDeviceInfo
        Error:    CL_INVALID_VALUE
        param_value_size is 4, but result requires 8 bytes
```

Charakteristik:

* Das tritt in vielen Tests mehrfach pro Run auf (je nach Anzahl der `clGetDeviceInfo`-Aufrufe).
* Alle diese Tests laufen aus Sicht von GoogleTest **grün** durch:

  * `[  PASSED  ]` trotz wiederholter Oclgrind-Fehler.
* D.h. der Rückgabecode von `clGetDeviceInfo` wird entweder:

  * gar nicht geprüft, oder
  * nicht hinreichend beachtet (Fehlerpfad führt nicht zu Test-Fehlschlag).

#### 2.5.2. Technische Interpretation

OpenCL-Signatur (vereinfacht):

```c
cl_int clGetDeviceInfo(
    cl_device_id    device,
    cl_device_info  param_name,
    size_t          param_value_size,
    void*           param_value,
    size_t*         param_value_size_ret);
```

Der Oclgrind-Fehler sagt:

* `param_value_size` wurde mit **4 Bytes** übergeben,
* der tatsächlich benötigte Wert ist aber **8 Bytes** (z.B. für `size_t` oder `cl_ulong`).

Mögliche fehlerhafte Aufrufmuster (schematisch):

* Falscher Typ bei `param_value`:

  ```cpp
  cl_device_id dev;
  cl_uint val;  // 32 Bit
  clGetDeviceInfo(dev, SOME_PARAM, sizeof(val), &val, nullptr);
  // Erwartet wäre z.B. cl_ulong oder size_t (64 Bit)
  ```

* Oder korrekter 64-Bit-Typ, aber falsches `sizeof`:

  ```cpp
  cl_ulong info;
  clGetDeviceInfo(dev, SOME_PARAM, sizeof(cl_uint), &info, nullptr);  // 4 statt 8
  ```

Laut OpenCL-Spezifikation ist das klar **invalid** → `CL_INVALID_VALUE`.
Oclgrind reagiert korrekt, native Treiber sind hier oft toleranter (undefinierte, aber „scheinbar funktionierende“ Ergebnisse).

#### 2.5.3. Misuse-Klassen

Aus Studienperspektive sind hier eigentlich **zwei Misuse-Aspekte** drin:

1. **Falsche Puffergröße / Typ-Mismatch bei `clGetDeviceInfo`**

   * Kategorie: falsche API-Parameter (Buffer-Size, Typ, Alignment).
   * Effekt:

     * Spezifikationsverstoß,
     * potentiell Out-of-Bounds-Write oder verschobene Werte,
     * Treiber-/Geräte-spezifisches Verhalten.

2. **Ignorierter Fehlercode `CL_INVALID_VALUE`**

   * Kategorie: Error-Handling-Misuse.
   * Effekt:

     * Tests bleiben grün, obwohl API-Call fehlschlägt.
     * Fehler bleibt unsichtbar für jede Logik, die sich nur auf Test-Status verlässt.

Für die Misuse-Tabelle kann man das später entweder als
**eine „Composite-Misuse“** (falscher Parameter + ignorierter Fehler) führen,
oder als **zwei Einträge**, die auf dieselbe Stelle zeigen.

#### 2.5.4. Statistische Einordnung (projektintern)

* 180/188 Tests → **praktisch die gesamte Suite** benutzt indirekt die fehlerhafte Device-Info-Routine.
* 8 Tests ohne Oclgrind-Fehler → nutzen entweder diese Funktion nicht oder treffen den Pfad nicht (z.B. rein CPU-seitige Logik, Array-Operationen ohne Device-Abhängigkeit).

→ CLIc liefert damit ein Beispiel für einen **einzigen, aber global wirksamen** Host-Misuse, der durch viele unterschiedliche High-Level-Operationen hindurch manifest wird.

---

### 2.6. Heap-Korruption & Runtimesymptome

In vielen Testläufen (159/188) tauchen zusätzlich glibc-Fehler auf, z.B.:

* `free(): chunks in smallbin corrupted`
* `corrupted double-linked list`

Eigenschaften:

* Die Meldung kommt **am Ende** des Testprogramms (nach GTest-Ausgabe).
* Sie tritt sowohl in Tests mit Oclgrind-Fehlern als auch in GTest-FAILS auf.
* Einige Tests zeigen nur `clGetDeviceInfo`-Fehler ohne Heap-Korruption, einige nur Heap-Korruption.

Mögliche Ursachen (Hypothesen, noch nicht verifiziert):

* Pufferüberläufe oder Write-after-Free im Zusammenhang mit:

  * zu kleinen Buffern für Device-Info,
  * globalen Strukturen, die im Tear-Down nochmal freigegeben werden.
* Zusätzlich könnte das Zusammenspiel aus:

  * CLIc-internem Ressourcenmanagement (Context/Device/Queue),
  * Oclgrind als ICD/Simulator,
  * C++-Destruktoren/Singletons
    zu „doppelten“ Freigaben oder kaputten Allokationen führen.

Für die Host-Misuse-Studie:

* **Primäre Erkenntnis** bleibt der `clGetDeviceInfo`-Misuse.
* Die Heap-Korruption ist ein **starkes Indiz**, dass dieser Misuse nicht nur „theoretisch“, sondern auch praktisch gefährlich sein kann (Geräte-/Implementationsabhängig).
* Ohne Stacktraces wird das aber eher als **qualitative Beobachtung** in die Beschreibung einfließen, nicht als eigener sauber eingekreister Misuse-Eintrag.

---

### 2.7. GTest-Fehlerbilder unter Oclgrind

#### 2.7.1. `tests/core/test_device`

* Erwartung im Test:

  ```text
  devices_all.size() == devices_gpu.size() + devices_cpu.size()
  ```

* Unter Oclgrind:

  * `devices_all.size() == 1`
  * `devices_gpu.size() + devices_cpu.size() == 0`

* D.h. Oclgrind-Device wird offenbar nicht als GPU/CPU klassifiziert, wie der Test es erwartet.

Interpretation:

* Kein klassischer Misuse, sondern:

  * Test macht Annahmen über Plattform-/Device-Typen (z.B. „wenn es ein Gerät gibt, ist es GPU oder CPU“),
  * Oclgrind gerät in eine Ecke, die der Test nicht vorgesehen hat.
* → Relevanter Hinweis für Dokumentation:
  „CLIc-Tests sind nicht komplett Oclgrind-agnostisch; Device-Klassifikation kann anders aussehen.“

#### 2.7.2. Vergleichs-/Labeling-Tests (7 Stück)

* Tests: `test_detect_label_edge`, `test_equal`, `test_greater`, `test_greater_or_equal`, `test_not_equal`, `test_smaller`, `test_smaller_or_equal`.
* Gemeinsam:

  * GTest-Fehler: Output-Arrays entsprechen nicht den erwarteten Werten.
  * Typische Meldungen: `expected 1, got 0` bzw. umgekehrt, etc.
* Mögliche Ursachen:

  * Präzisions-/Backend-Divergenzen,
  * andere Default-Konstanten oder Grenzwerte,
  * oder Nebeneffekte des `clGetDeviceInfo`-/Heap-Problems.

Für die Host-Misuse-Studie:

* Diese Fehler sind eher **semantische/algorithmische Abweichungen** (Vergleichsoperatoren, Thresholding/Masking).
* Nur dann relevant, wenn sich herausstellt, dass sie direkt auf Host-API-Misuse (z.B. falsche Kernel-Parameter, falsche Workgroup-Größen) zurückzuführen sind.
* Stand jetzt: als „Nebenbefund“ notieren, nicht als gesicherter Misuse.

---

### 2.8. Vorschlag für Misuse-Eintrag (CLIc)

**WIP-Eintrag für `verified_misuses.csv` (muss später mit Dateinamen/Zeilennummer ergänzt werden):**

```text
id,project,host_file,line,api_calls,short_description,spec_ref,category,how_found,detectable_CT_SA,detectable_RT,detectable_DEV,tools_detecting,patch_summary,notes
M-CLIC-001,clEsperanto/CLIc,<TODO-file>,<TODO-line>,clGetDeviceInfo,"param_value_size=4 for 8-byte device info; CL_INVALID_VALUE ignored","OpenCL 1.2/2.0/3.0 clGetDeviceInfo: param_value_size must be >= size of return type","wrong_param_size + ignored_error_code","oclgrind --check-api on tests/tier1/test_add_image_and_scalar",no,yes,yes,"Oclgrind","Use correct sizeof(type) for queried param; handle non-success return codes; adjust device info wrapper accordingly.","Error appears in 180/188 tests; causes repeated CL_INVALID_VALUE reports and contributes to heap corruption on teardown under Oclgrind."
```

Später zu ergänzen:

* `host_file` / `line`: Quelle aus `grep -R "clGetDeviceInfo" clic/`.
* `spec_ref`: konkrete Abschnittsnummer aus der OpenCL-Spezifikation.
* `patch_summary`: konkretisieren, sobald ein Fix entworfen wurde.

---

## 3. TODO-Liste (für später)

1. **CLIc: Source-Lokalisierung**

   * `grep -R "clGetDeviceInfo" -n clic/`
   * betroffene Funktion(en) identifizieren (z.B. Device-Info-Wrapper).
   * prüfen, welche `param_name`s abgefragt werden und welche Typen benutzt werden.
   * Misuse-Eintrag mit Datei/Zeile vervollständigen.

2. **CLIc: Entscheidungsfrage Heap-Korruption**

   * Falls Zeit: einen der Tests unter `valgrind` auf einem nativen ICD laufen (ohne Oclgrind), um zu schauen, ob Heap-Probleme auch dort auftreten.
   * Falls ja: zusätzlicher Misuse-Eintrag (Resource-Management).
   * Falls nein: als „Oclgrind-Interaktionsartefakt“ dokumentieren.

3. **GABGFX: Abschluss**

   * In `projects.csv` eintragen:

     * `build_status = failed`
     * `tool_status = skipped`
     * `exclusion_reason = third_party_dep_build_failure`
   * Kurze Notiz, dass Fehler in vendored assimp/zlib liegen, nicht in OpenCL-Hostcode.

4. **Generell: Stop-Regeln pro Projekt definieren**

   * Maximal X eindeutige Misuse-Klassen pro Projekt sammeln (z.B. 3–5).
   * Sobald klar ist, dass weitere Tests nur dieselben Misuse-Klassen triggern → zum nächsten Repo wechseln.

---

```

---

Das ist jetzt bewusst ein **voller Roh-Container**: alles drin, was du später auf `projects.csv`, `verified_misuses.csv`, projektspezifische Notizen usw. verteilen kannst – ohne dass du heute noch irgendwas einzeln eintragen musst.
::contentReference[oaicite:0]{index=0}
```
