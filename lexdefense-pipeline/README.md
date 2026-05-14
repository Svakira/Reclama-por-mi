# LexDefense Pipeline

Sistema evidence-first para generar borradores auditables de contestacion de demanda en Colombia.

## Que es

Genera un primer borrador verificable, matriz hecho-prueba-respuesta, reporte de auditoria y checklist de revision humana.

## Que no es

No es un abogado autonomo. No firma, no radica, no reemplaza la revision profesional y no debe tratar citas no verificadas como definitivas.

## Instalacion

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuracion

```bash
cp .env.example .env
```

## Corpus local

Coloca leyes, codigos y jurisprudencia curada en `data/legal_corpus/`.

- Si el pipeline encuentra fuentes locales relevantes, las guarda como citas `VERIFIED` en `legal_citations.json`.
- Si no encuentra soporte local, genera la marca `[CITA JURISPRUDENCIAL REQUIERE VERIFICACION POR ABOGADO]` y bloquea exportacion final.

## Uso CLI

```bash
PYTHONPATH=src python3 -m lexdefense.cli ingest --input data/input --out runs/case001
PYTHONPATH=src python3 -m lexdefense.cli build-case --run runs/case001 --client-role aseguradora_llamada_en_garantia
PYTHONPATH=src python3 -m lexdefense.cli generate-matrix --run runs/case001
PYTHONPATH=src python3 -m lexdefense.cli draft --run runs/case001
PYTHONPATH=src python3 -m lexdefense.cli audit --run runs/case001
PYTHONPATH=src python3 -m lexdefense.cli export --run runs/case001 --format md
```

## Uso Streamlit

```bash
PYTHONPATH=src streamlit run app.py
```

## Limites

Toda salida requiere revision humana y toda cita juridica sugerida debe verificarse antes de cualquier uso final.
