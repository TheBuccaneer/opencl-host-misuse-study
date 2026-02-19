# CLIc (clEsperanto) – OpenCL Host-Misuse Audit

## Setup & Build

- Repository: `clEsperanto/CLIc`
- Build auf Linux:
  ```bash
  git clone https://github.com/clEsperanto/CLIc.git
  cd CLIc
  mkdir build && cd build
  cmake ..
  cmake --build .
  
  OpenCL-ICD (3.0) wird korrekt gefunden, Tests werden mitgebaut.

Sanity-Check:

ctest -R test_add_image_and_scalar -V


cd build
oclgrind --check-api ./tests/tier1/test_add_image_and_scalar



Oclgrind - OpenCL runtime error detected
        Function: clGetDeviceInfo
        Error:    CL_INVALID_VALUE
        param_value_size is 4, but result requires 8 bytes
        
Zusätzlich treten am Programmende Heap-Fehler auf (free(): chunks in smallbin corrupted, corrupted double-linked list), obwohl die Tests selbst grün sind.

Lokalisierung des Misuse im Code

Relevante Stellen in clic/src/opencldevice.cpp:

// korrekt (size_t):
clGetDeviceInfo(clRessources->get_device(), CL_DEVICE_MAX_WORK_GROUP_SIZE,
                sizeof(size_t), &max_work_group_size, nullptr);

// falsch (zweimal):
clGetDeviceInfo(clRessources->get_device(), CL_DEVICE_MAX_WORK_GROUP_SIZE,
                sizeof(cl_uint), &max_work_group_size, nullptr);

                
                Laut OpenCL-Spezifikation ist der Rückgabetyp von
CL_DEVICE_MAX_WORK_GROUP_SIZE ein size_t (8 Byte auf dieser Plattform).

Im Code wird an zwei Stellen sizeof(cl_uint) (4 Byte) verwendet:

opencldevice.cpp:379

opencldevice.cpp:413

Der Rückgabewert (cl_int) von clGetDeviceInfo wird an keiner dieser Stellen ausgewertet, sodass CL_INVALID_VALUE komplett ignoriert wird.

  Befund / Interpretation

Host-Misuse 1 – Falsche Buffer-Größe:
Für CL_DEVICE_MAX_WORK_GROUP_SIZE wird ein 4-Byte-Buffer (cl_uint) statt eines 8-Byte-size_t verwendet. Das triggert unter Oclgrind reproduzierbar CL_INVALID_VALUE („param_value_size is 4, but result requires 8 bytes“).

Host-Misuse 2 – Ignorierter Fehlercode:
Der Rückgabewert von clGetDeviceInfo wird nirgends geprüft. Dadurch bleiben Fehler wie CL_INVALID_VALUE und die daraus resultierende Heap-Korruption in nativen Läufen unsichtbar und die Test-Suite erscheint „grün“.

(Optionale) Fix-Idee

Für die Studie wurde kein Patch eingespielt, aber ein plausibler Fix wäre:

Typen und Größen vereinheitlichen:

size_t max_work_group_size;
cl_int err = clGetDeviceInfo(dev, CL_DEVICE_MAX_WORK_GROUP_SIZE,
                             sizeof(size_t), &max_work_group_size, nullptr);

                             
                             
---

## 3. Brauchen wir die „Lösung“ (Patch) wirklich?

Aus Sicht deines **Pilot-Artefakts** und der **Studie**:

- **Nein, du musst den Patch nicht implementieren.**
- Wichtig sind:
  - dass du zeigen kannst:  
    *„Dieses reale Projekt hat genau diesen Host-Misuse, und Oclgrind findet ihn so und so“*;
  - und dass du ihn im Code **lokalisierst** und korrekt beschreibst.
- Eine *Fix-Idee* (wie oben) ist nice-to-have für Paper-Text / Discussion, aber keine Pflicht für deine jetzigen Artefakte.

Wenn du magst, können wir im neuen Thread als nächsten Schritt einfach noch einen **sehr knappen 2-Zeiler** für `artifacts/CLIc/README.md` bauen (so wie bei CAS-2D), der nur auf die große Audit-Datei verweist.
::contentReference[oaicite:0]{index=0}
