# TAREAS — Compañero de Derecho
**JusticIA — Simulacro Hack the Law Cambridge 2026**
**Semillero LegalTech ICESI**

---

## Tu rol en el proyecto

El sistema tiene un Knowledge Graph (base de datos de leyes, artículos y plantillas de argumentos) que el agente `LegalClassifier` y el `ComplaintDraftGenerator` usan para:

1. Clasificar el caso de Rosa (Escenario A, B o C)
2. Citar los artículos correctos en la reclamación formal
3. Redactar los argumentos legales del borrador que el abogado revisa

**Tu tarea:** Llenar el archivo `backend/kg/legal_graph.json` con el contenido jurídico correcto. El sistema SOLO puede citar lo que esté en ese archivo. Si falta un artículo o está mal, la reclamación queda vacía o errónea.

---

## Tarea 1 — Revisar y aprobar el árbol de decisiones (YA HECHO)

Ya revisaste `docs/arboldecisionesdereclamacion.txt` y `docs/EscenarioABC.txt`.

**Estado:** ✅ Completado

---

## Tarea 2 — Llenar el Knowledge Graph (CRÍTICA)

Crea (o edita) el archivo `backend/kg/legal_graph.json` usando el template de abajo.

El template tiene estructura fija — **no cambies las claves** (`id`, `text`, `article_number`, etc.). Solo rellena los campos marcados con `"COMPLETAR"`.

### ¿Cómo llenarlo?

- Fuentes prioritarias para los textos:
  1. Los PDFs en `docs/` (ya subidos): `Ley-1480-2011_Estatuto-del-Consumidor.pdf`
  2. La Relatoría SIC: para sentencias y criterios jurisdiccionales
  3. El Buscador de Actos Administrativos SIC: para resoluciones sectoriales
  4. Los dos libros académicos subidos en `docs/` (Ramírez-Sierra, Tamayo-Jaramillo)

- Para cada artículo, escribe el texto literal de la norma (no parafrasees).
- Para las `case_patterns`, describe en lenguaje natural el tipo de caso que activa ese artículo.
- Para los `claim_templates`, escribe el texto que irá en la sección "Pretensiones" de la reclamación formal.

---

## Template — `backend/kg/legal_graph.json`

```json
{
  "metadata": {
    "version": "1.0",
    "last_updated": "2026-04-11",
    "author": "Semillero LegalTech ICESI",
    "description": "Knowledge Graph jurídico para pipeline JusticIA"
  },

  "laws": [
    {
      "id": "LEY_1480_2011",
      "name": "Ley 1480 de 2011 — Estatuto del Consumidor",
      "jurisdiction": "Colombia",
      "authority": "Congreso de la República",
      "scenarios": ["A", "B", "C"],
      "notes": "Ley principal. Para escenario C aplica solo supletoriamente."
    },
    {
      "id": "LEY_1328_2009",
      "name": "Ley 1328 de 2009 — Régimen de Protección al Consumidor Financiero",
      "jurisdiction": "Colombia",
      "authority": "Congreso de la República",
      "scenarios": ["B"],
      "notes": "Solo para entidades vigiladas por la Superfinanciera. Fuera del scope del demo."
    },
    {
      "id": "LEY_1341_2009",
      "name": "Ley 1341 de 2009 — Ley TIC",
      "jurisdiction": "Colombia",
      "authority": "Congreso de la República",
      "scenarios": ["C"],
      "notes": "Régimen principal usuario de comunicaciones, arts. 54 y ss."
    },
    {
      "id": "LEY_45_1990",
      "name": "Ley 45 de 1990",
      "jurisdiction": "Colombia",
      "authority": "Congreso de la República",
      "scenarios": ["B"],
      "notes": "Aplica en cobros indebidos de crédito no vigilado por Superfinanciera."
    }
  ],

  "articles": [

    // ──────────────────────────────────────────────
    // ESCENARIO A — Producto defectuoso (Ley 1480)
    // ──────────────────────────────────────────────

    {
      "id": "ART_7_LEY_1480",
      "law_id": "LEY_1480_2011",
      "article_number": "7",
      "title": "Garantía legal",
      "text": "COMPLETAR — pegar texto literal del artículo 7 de la Ley 1480",
      "scenarios": ["A"],
      "tags": ["garantia_legal", "producto_defectuoso", "bien_nuevo"],
      "claim_threshold": "El bien presenta defecto o falla dentro del plazo de garantía legal (1 año para bienes nuevos sin término especial)"
    },
    {
      "id": "ART_10_LEY_1480",
      "law_id": "LEY_1480_2011",
      "article_number": "10",
      "title": "Efectividad de la garantía",
      "text": "COMPLETAR — pegar texto literal del artículo 10 de la Ley 1480",
      "scenarios": ["A"],
      "tags": ["efectividad_garantia", "reparacion", "cambio", "devolucion"],
      "claim_threshold": "El proveedor o productor se negó a hacer efectiva la garantía del bien"
    },
    {
      "id": "ART_11_LEY_1480",
      "law_id": "LEY_1480_2011",
      "article_number": "11",
      "title": "Término y condiciones de la garantía",
      "text": "COMPLETAR — pegar texto literal del artículo 11 de la Ley 1480",
      "scenarios": ["A"],
      "tags": ["plazo_garantia", "garantia_legal", "un_año"],
      "claim_threshold": "El bien tiene menos de 1 año de comprado (o del término especial pactado) y el proveedor alega que venció la garantía"
    },
    {
      "id": "ART_16_LEY_1480",
      "law_id": "LEY_1480_2011",
      "article_number": "16",
      "title": "Causales de exoneración de responsabilidad",
      "text": "COMPLETAR — pegar texto literal del artículo 16 de la Ley 1480",
      "scenarios": ["A"],
      "tags": ["exoneracion", "responsabilidad_productor", "carga_prueba"],
      "claim_threshold": "Referencia de defensa: el proveedor alega causal de exoneración. El consumidor no tiene que probarlas."
    },
    {
      "id": "ART_58_LEY_1480",
      "law_id": "LEY_1480_2011",
      "article_number": "58",
      "title": "Acciones jurisdiccionales — Competencia SIC",
      "text": "COMPLETAR — pegar texto literal del artículo 58 de la Ley 1480",
      "scenarios": ["A", "B", "C"],
      "tags": ["accion_proteccion_consumidor", "competencia_sic", "jurisdiccion"],
      "claim_threshold": "Fundamento procesal para radicar ante la SIC"
    },

    // ──────────────────────────────────────────────
    // ESCENARIO B — Cobro indebido financiero (Ley 1480, arts. transversales)
    // ──────────────────────────────────────────────

    {
      "id": "ART_37_LEY_1480",
      "law_id": "LEY_1480_2011",
      "article_number": "37",
      "title": "Cláusulas abusivas — ineficaces de pleno derecho",
      "text": "COMPLETAR — pegar texto literal del artículo 37 de la Ley 1480",
      "scenarios": ["B"],
      "tags": ["clausula_abusiva", "ineficacia", "contrato"],
      "claim_threshold": "El contrato o reglamento contiene una cláusula que causó el cobro indebido y genera desequilibrio en perjuicio del consumidor"
    },
    {
      "id": "ART_43_LEY_1480",
      "law_id": "LEY_1480_2011",
      "article_number": "43",
      "title": "Cláusulas prohibidas",
      "text": "COMPLETAR — pegar texto literal del artículo 43 de la Ley 1480",
      "scenarios": ["B"],
      "tags": ["clausula_abusiva", "clausula_prohibida"],
      "claim_threshold": "La cláusula que originó el cobro está en la lista de cláusulas prohibidas del art. 43"
    },
    {
      "id": "ART_23_LEY_1480",
      "law_id": "LEY_1480_2011",
      "article_number": "23",
      "title": "Responsabilidad por información y publicidad engañosa",
      "text": "COMPLETAR — pegar texto literal del artículo 23 de la Ley 1480",
      "scenarios": ["A", "B", "C"],
      "tags": ["publicidad_enganosa", "informacion_enganosa", "responsabilidad"],
      "claim_threshold": "Lo que le ofrecieron (escrito, verbal, publicidad) no coincide con lo que le dieron o cobraron"
    },

    // ──────────────────────────────────────────────
    // ESCENARIO C — Telecomunicaciones (Ley 1341)
    // ──────────────────────────────────────────────

    {
      "id": "ART_54_LEY_1341",
      "law_id": "LEY_1341_2009",
      "article_number": "54",
      "title": "Derechos de los usuarios de servicios de comunicaciones",
      "text": "COMPLETAR — pegar texto literal del artículo 54 de la Ley 1341",
      "scenarios": ["C"],
      "tags": ["usuario_comunicaciones", "derechos_usuario", "telecomunicaciones"],
      "claim_threshold": "El operador incumplió las condiciones del servicio de telecomunicaciones contratado"
    },
    {
      "id": "ART_55_LEY_1341",
      "law_id": "LEY_1341_2009",
      "article_number": "55",
      "title": "COMPLETAR — título del artículo 55 Ley 1341",
      "text": "COMPLETAR — pegar texto literal del artículo 55 de la Ley 1341",
      "scenarios": ["C"],
      "tags": ["telecomunicaciones", "pqr", "COMPLETAR"],
      "claim_threshold": "COMPLETAR — cuándo aplica este artículo"
    }

    // INSTRUCCIÓN: Si encuentras más artículos relevantes en los PDFs
    // o en la Relatoría SIC, agrégalos aquí con el mismo formato.
    // El sistema los incorporará automáticamente al clasificador.
  ],

  "claim_templates": [

    // ──────────────────────────────────────────────
    // Templates de pretensiones por escenario
    // Estos textos van literalmente en la sección "Pretensiones"
    // de la reclamación formal ante la SIC.
    // ──────────────────────────────────────────────

    {
      "id": "CLAIM_A_GARANTIA_REPARACION",
      "scenario": "A",
      "pretension_type": "garantia",
      "remedy": "reparacion",
      "template": "COMPLETAR — texto formal: 'Que se haga efectiva la garantía legal del bien [PRODUCT_NAME] mediante su reparación, conforme al artículo 10 de la Ley 1480 de 2011.'",
      "articles_cited": ["ART_7_LEY_1480", "ART_10_LEY_1480"],
      "monetary": false
    },
    {
      "id": "CLAIM_A_GARANTIA_CAMBIO",
      "scenario": "A",
      "pretension_type": "garantia",
      "remedy": "cambio",
      "template": "COMPLETAR — texto formal: 'Que se haga efectiva la garantía legal mediante la entrega de un bien nuevo de iguales o superiores condiciones...'",
      "articles_cited": ["ART_7_LEY_1480", "ART_10_LEY_1480"],
      "monetary": false
    },
    {
      "id": "CLAIM_A_GARANTIA_DEVOLUCION",
      "scenario": "A",
      "pretension_type": "garantia",
      "remedy": "devolucion_dinero",
      "template": "COMPLETAR — texto formal: 'Que se devuelva el precio pagado de [AMOUNT] pesos, dado que el bien [PRODUCT_NAME] no cumple las condiciones de calidad e idoneidad...'",
      "articles_cited": ["ART_7_LEY_1480", "ART_10_LEY_1480"],
      "monetary": true,
      "amount_placeholder": "[AMOUNT]"
    },
    {
      "id": "CLAIM_B_DEVOLUCION_COBRO_INDEBIDO",
      "scenario": "B",
      "pretension_type": "cobro_indebido",
      "remedy": "devolucion_dinero",
      "template": "COMPLETAR — texto formal: 'Que se restituya la suma de [AMOUNT] pesos cobrada indebidamente el [DATE], correspondiente a [CHARGE_DESCRIPTION], sin fundamento contractual válido...'",
      "articles_cited": ["ART_23_LEY_1480", "ART_37_LEY_1480"],
      "monetary": true,
      "amount_placeholder": "[AMOUNT]"
    },
    {
      "id": "CLAIM_C_TELECOMUNICACIONES_DEVOLUCION",
      "scenario": "C",
      "pretension_type": "incumplimiento_servicio",
      "remedy": "devolucion_dinero",
      "template": "COMPLETAR — texto formal: 'Que se devuelva el valor proporcional al período de incumplimiento del servicio [SERVICE_TYPE] contratado con [OPERATOR_NAME]...'",
      "articles_cited": ["ART_54_LEY_1341"],
      "monetary": true,
      "amount_placeholder": "[AMOUNT]"
    },
    {
      "id": "CLAIM_C_TELECOMUNICACIONES_CUMPLIMIENTO",
      "scenario": "C",
      "pretension_type": "incumplimiento_servicio",
      "remedy": "cumplimiento",
      "template": "COMPLETAR — texto formal: 'Que el operador [OPERATOR_NAME] cumpla las condiciones del servicio [SERVICE_TYPE] en los términos contratados...'",
      "articles_cited": ["ART_54_LEY_1341"],
      "monetary": false
    }
  ],

  "rejection_templates": [

    // ──────────────────────────────────────────────
    // Templates para documentos de rechazo (Stage 5c)
    // Se usan cuando el abogado confirma NO CLAIM
    // o cuando Rosa elige Opción 3 (descartar).
    // ──────────────────────────────────────────────

    {
      "id": "REJECT_NO_CONSUMER_RELATION",
      "reason_code": "no_relacion_consumo",
      "title": "No se identifica relación de consumo bajo Ley 1480",
      "explanation_for_rosa": "COMPLETAR — explicación en lenguaje simple para Rosa de por qué su caso no tiene reclamación ante la SIC.",
      "legal_basis": "Artículo 1 y 2, Ley 1480 de 2011 — definición de relación de consumo"
    },
    {
      "id": "REJECT_SUPERFINANCIERA",
      "reason_code": "competencia_superfinanciera",
      "title": "El caso corresponde a la Superintendencia Financiera, no a la SIC",
      "explanation_for_rosa": "COMPLETAR — explicación simple: 'Su banco o entidad financiera está vigilado por la Superfinanciera. Le explicamos cómo presentar su queja allá.'",
      "legal_basis": "Ley 1328 de 2009 — régimen especial consumidor financiero",
      "redirect_url": "https://www.superfinanciera.gov.co/jsp/loader.jsf?lServicio=PublicacionesPortal&lTipo=publicaciones&lFuncion=loadContenidoPublicacion&id=60968"
    },
    {
      "id": "REJECT_OUT_OF_SCOPE",
      "reason_code": "fuera_de_alcance",
      "title": "El caso no encaja en los escenarios de reclamación ante la SIC",
      "explanation_for_rosa": "COMPLETAR — explicación simple y con alternativas (personería, litigación directa, conciliación).",
      "legal_basis": "COMPLETAR"
    }
  ],

  "pqr_requirement": {
    "scenario": "C",
    "required": true,
    "description": "Para telecomunicaciones, el usuario debe haber presentado PQR ante el operador antes de acudir a la SIC. La SIC interviene principalmente como autoridad de apelación.",
    "question_for_rosa": "¿Ya presentó una queja, petición o reclamo (PQR) directamente con su operador de telecomunicaciones?",
    "if_no_pqr": "COMPLETAR — texto que le dice a Rosa que primero debe agotar el recurso ante el operador antes de ir a la SIC.",
    "legal_basis": ["ART_54_LEY_1341"],
    "notes": "Arts. 54 y ss. Ley 1341/2009 y Resolución CRC 5050 de 2016"
  }
}
```

---

## Tarea 3 — Verificar las pretensiones (IMPORTANTE)

Después de llenar el template, responde estas preguntas en un comentario al final del archivo o en un mensaje al equipo:

1. ¿Las pretensiones del `CLAIM_A_GARANTIA_*` cubren los 4 remedios del art. 10 Ley 1480 (reparar, cambiar, devolver precio, otro)?
2. Para Escenario B: ¿alcanza con citar arts. 37 y 23, o hay otro artículo de la Ley 1480 que debería estar?
3. Para Escenario C: ¿la SIC puede conocer directamente la apelación, o Rosa siempre debe agotar la PQR ante el operador primero?
4. ¿Algún template de pretensión usa lenguaje que la SIC rechazaría en un caso real?

---

## Tarea 4 — Revisar el borrador final (DURANTE DEMO)

Cuando el sistema genere el borrador de reclamación en el demo, léelo y verifica:

- [ ] Todos los artículos citados existen en la Ley 1480 / Ley 1341
- [ ] Las pretensiones son claras, separadas, concretas y precisas (requisito del formato SIC)
- [ ] El monto económico está estimado cuando hay pretensión económica
- [ ] El lenguaje formal es correcto para presentación ante autoridad administrativa

---

## Recursos de consulta

| Recurso | URL / Ubicación |
|---|---|
| Ley 1480 de 2011 | `docs/Ley-1480-2011_Estatuto-del-Consumidor.pdf` |
| Formulario SIC | `docs/SIC_formulario-base-reclamacion.pdf` |
| Manual proceso SIC | `docs/SIC_manual-proceso-reclamacion.pdf` |
| Ramírez-Sierra | `docs/Ramirez-Sierra_Responsabilidad-productos-defectuosos-Estatuto-Consumidor.pdf` |
| Tamayo-Jaramillo | `docs/Tamayo-Jaramillo_Estatuto-Consumidor-responsabilidad-productos-defectuosos.pdf` |
| Relatoría SIC | https://www.sic.gov.co/relatoria |
| Buscador Actos SIC | https://www.sic.gov.co/buscador-de-actos-administrativos |
| Ley 1341 de 2009 | `docs/ley-de-las-tecnologas-de-la-informacin-y-las-comunicaciones-.pdf` |

---

## Preguntas frecuentes

**¿Puedo agregar más artículos al KG?**
Sí. Mientras uses el mismo formato JSON, el sistema los incorpora automáticamente.

**¿Qué pasa si dejo un campo como "COMPLETAR"?**
El agente `DraftValidator` detectará que el artículo no tiene texto y bloqueará la generación del borrador. El demo fallará para ese escenario.

**¿Los comentarios `//` en el JSON son válidos?**
No para el archivo final. Son solo guías en este template. Elimínalos cuando entregues el archivo.

**¿Cuánto tiempo toma esto?**
Estimado: 3–4 horas. Puedes hacerlo por secciones: primero Escenario A (es el más claro), luego B, luego C.

---

*Última actualización: 2026-04-11 — Semillero LegalTech ICESI*
