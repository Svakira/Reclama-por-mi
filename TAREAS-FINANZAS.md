# TAREAS — Compañero de Finanzas / Presentación
**JusticIA — Simulacro Hack the Law Cambridge 2026**
**Semillero LegalTech ICESI**

---

## Tu rol en el proyecto

Tienes **dos frentes**:

1. **Presentación y demo** — Construir el deck para los jueces y preparar el script del demo en vivo
2. **Documentos de prueba** — Crear los archivos falsos (facturas, contratos, extractos) que el sistema necesita para demostrar que funciona con los 3 escenarios

---

## Tarea 1 — Documentos de prueba para el demo (URGENTE)

El sistema necesita archivos reales para que el `DocumentParser` los procese durante el demo. Si no hay documentos, el demo no puede mostrar el pipeline completo.

### Crea los siguientes PDFs/imágenes:

#### Escenario A — Producto defectuoso

| Documento | Qué debe contener | Formato |
|---|---|---|
| `demo/escenario_a/factura_celular.pdf` | Factura de compra: "Samsung Galaxy A54, IMEI: 352547113456789, $1.200.000 COP, Tienda TecnoPlus Cali, 15/10/2025" | PDF simple |
| `demo/escenario_a/foto_defecto.jpg` | Foto (puede ser genérica de pantalla rota o imagen de muestra) | JPG |
| `demo/escenario_a/chat_tienda.pdf` | Captura de chat falso: Rosa le escribe a la tienda, la tienda responde "No aplica garantía" | PDF |

#### Escenario B — Cobro indebido financiero

| Documento | Qué debe contener | Formato |
|---|---|---|
| `demo/escenario_b/extracto_bancario.pdf` | Extracto de cuenta: cobro de "$45.000 COP — Seguro vida obligatorio" en fecha 01/03/2026, sin autorización previa | PDF |
| `demo/escenario_b/contrato_credito.pdf` | Contrato de crédito de consumo: sin mencionar el seguro vida en cláusulas | PDF |

#### Escenario C — Telecomunicaciones

| Documento | Qué debe contener | Formato |
|---|---|---|
| `demo/escenario_c/factura_internet.pdf` | Factura Claro/ETB: plan 50 Mbps, $89.000/mes, período ene-feb 2026 | PDF |
| `demo/escenario_c/radicado_pqr.pdf` | Radicado de PQR del operador: "Caso #2026-003421, resuelto: Solicitud no procede" | PDF |

### ¿Cómo crearlos?

- Word o Google Docs → exportar como PDF
- Los datos son ficticios pero deben ser coherentes (nombres, cédulas, fechas)
- Usa nombres ficticios para Rosa: **Rosa Inés Morales Vargas, CC 32.456.789, Cali, Valle del Cauca**
- Empresa Escenario A: **TecnoPlus S.A.S.**, NIT 900.123.456-7, Cali
- Banco Escenario B: **FinanzaFácil S.A.S.** (fintech ficticia), NIT 901.234.567-8
- Operador Escenario C: **ClaroColombia**, NIT 800.153.993-8

---

## Tarea 2 — Deck de presentación

### Estructura recomendada (15 slides, ~8 minutos)

#### Acto 1: El problema (slides 1–3)

**Slide 1 — Portada**
- Nombre: JusticIA
- Subtítulo: *"El derecho que no llega, ahora llega."*
- Logos: ICESI + Semillero LegalTech
- Hackathon: Simulacro Hack the Law Cambridge 2026

**Slide 2 — El problema**
- Estadísticas clave:
  - 400.000+ reclamaciones/año ante la SIC
  - 70% de colombianos sin acceso a asesoría jurídica
  - El formulario SIC tiene 14 campos técnicos
  - Un error en el campo "tipo de bien" = reclamación inadmisible
- Imagen sugerida: formulario SIC con los 14 campos visibles

**Slide 3 — Rosa**
- Foto de perfil: mujer de ~54 años, vendedora informal
- Historia: compró un celular en cuotas, a los 2 meses dejó de funcionar, la tienda dice que "es daño por mal uso"
- Rosa no sabe qué es una "garantía legal". Tampoco sabe que tiene 1 año para reclamar.
- Frase: *"¿Cómo puede Rosa ejercer un derecho que no entiende?"*

#### Acto 2: La solución (slides 4–8)

**Slide 4 — JusticIA en una línea**
- Un pipeline de 9 agentes de IA que convierte el relato de Rosa en una reclamación formal válida ante la SIC
- El abogado siempre aprueba antes de enviar (hard gate)
- Diagrama: Rosa → Pipeline → Abogado → SIC

**Slide 5 — El pipeline (resumen visual)**
- 9 pasos en fila horizontal:
  1. Escucha a Rosa (voz o texto)
  2. Pide documentos específicos
  3. Lee y extrae información de documentos
  4. Valida con el relato
  5. Clasifica el caso (A/B/C)
  6. Genera borrador legal
  7. Valida campos SIC
  8. Empaqueta caso
  9. Abogado aprueba → SIC

**Slide 6 — Lo que Rosa ve**
- Captura de pantalla (o mockup) de la interfaz `/app`
- Conversación simple: "¿Qué pasó con su producto?"
- Sin tecnicismos. Sin formularios. Solo una conversación.

**Slide 7 — Lo que el abogado ve**
- Captura de pantalla del dashboard `/admin`
- Queue de casos, clasificación automática, borrador listo para revisar
- Botones: APROBAR / EDITAR / SOLICITAR DOCS / NO APLICA

**Slide 8 — Los hard gates (diferenciador ético)**
- "El sistema NUNCA envía sin aprobación del abogado"
- "Rosa debe consentir explícitamente que la clínica presente en su nombre"
- "Los documentos ilegibles se bloquean hasta que el abogado los revisa"
- Este es el argumento de confianza: no es un bot que hace cosas solo

#### Acto 3: Stack y escalabilidad (slides 9–11)

**Slide 9 — Stack técnico**
- Tabla simple:
  - LLM: Groq (llama-3.3-70b-versatile) — gratis
  - Voz: Groq Whisper — gratis
  - KG Legal: Neo4j AuraDB — gratis
  - BD: Firestore Google — gratis
  - Notificaciones: Twilio WhatsApp Sandbox — gratis
  - Hosting: Replit Core — $20/mes (ya pagado)
- Total costo adicional: **$0**

**Slide 10 — Los 3 escenarios que maneja**
- A: Producto defectuoso (Ley 1480, arts. 7, 10, 11, 16, 58)
- B: Cobro indebido financiero no vigilado por Superfinanciera (Ley 1480 + Ley 45/1990)
- C: Incumplimiento telecomunicaciones con PQR previa (Ley 1341 + Ley 1480 supletoria)
- Nota: el sistema también sabe cuándo NO aplica y lo dice con un documento formal

**Slide 11 — Escalabilidad / Visión B2B**
- Clínicas jurídicas universitarias en Colombia: 47 activas
- Personerías municipales: 1.102
- Ligas de consumidores
- Potencial de licenciamiento SaaS: $X/mes por clínica
- (Número concreto opcional — puedes usar una estimación conservadora)

#### Acto 4: Demo y cierre (slides 12–15)

**Slide 12 — "Vean a Rosa en acción"**
- Slide de transición antes del demo en vivo
- Texto: "Demo — Escenario A: celular defectuoso"
- Subtext: "Rosa habla. JusticIA escucha. El abogado aprueba. La SIC recibe."

**Slide 13 — Resultados del demo**
- (Llenar después del demo en vivo — o preparar con capturas)
- Tiempo total: X minutos desde relato hasta borrador listo
- Campos SIC completados: 14/14
- Artículos citados correctamente: Sí

**Slide 14 — Impacto potencial**
- Si 10% de los casos con derecho a reclamar lo hacen gracias a JusticIA:
  - ~40.000 consumidores/año
  - Que actualmente no reclaman por barreras de información
- "JusticIA no reemplaza al abogado. Lo potencia."

**Slide 15 — Cierre**
- Equipo: fotos + nombres + roles
- *"El derecho que no llega, ahora llega."*
- Repositorio: github.com/Svakira/xd (privado hasta presentación)
- QR de acceso al demo en Replit

---

## Tarea 3 — Script del demo en vivo

### Tiempo total: 3–4 minutos

#### Paso 1 — Abrir la interfaz de Rosa (30 seg)
1. Ir a la URL pública de Replit → `/app`
2. Decir: "Este es lo que Rosa ve. Una conversación simple."
3. Mostrar el botón de micrófono.

#### Paso 2 — Rosa habla (1 min)
Dictarle al sistema (voz o texto):

> "Hola, compré un Samsung Galaxy A54 en TecnoPlus en octubre del año pasado, pagué $1.200.000. A los dos meses empezó a fallar la pantalla, se apaga sola. Fui a la tienda y me dijeron que no me aplica garantía porque yo lo golpeé, pero yo nunca lo golpeé. Quiero que me lo cambien o que me devuelvan la plata."

4. El sistema debe responder con la siguiente pregunta del árbol de decisiones.

#### Paso 3 — Subir documento (30 seg)
1. El sistema pedirá la factura.
2. Subir `demo/escenario_a/factura_celular.pdf`
3. El sistema debe mostrar que extrajo: IMEI, precio, fecha, tienda.

#### Paso 4 — Ver el borrador (1 min)
1. Cambiar al dashboard del abogado: `/admin`
2. Mostrar el caso en la queue con clasificación automática: **Escenario A — Garantía Legal**
3. Abrir el caso → mostrar el borrador con los 14 campos SIC y los artículos citados.
4. Decir: "El abogado revisa. Si aprueba, el caso va a la SIC. Si no, puede editar o pedir más documentos."
5. Hacer clic en **APROBAR**.

#### Paso 5 — Rosa recibe (30 seg)
1. Mostrar la notificación de WhatsApp (Twilio Sandbox) en el teléfono o en pantalla.
2. Mensaje: "Hola Rosa, tu caso fue aprobado por el abogado. Número de referencia: JUS-2026-001."

---

## Tarea 4 — Preparar fallback para el demo

Si algo falla en el demo en vivo (internet, API, etc.), prepara:

1. **Capturas de pantalla** de cada paso del pipeline (guardadas como imágenes en el deck)
2. Un **video de 2 minutos** grabado previamente con el demo completo (como backup)
3. Un slide de "arquitectura animada" que muestre el flujo aunque no funcione en vivo

---

## Tarea 5 — Análisis financiero / business case (opcional, si el hackathon lo pide)

Si los jueces preguntan por viabilidad económica:

### Modelo de costos (demo)
- Costo por caso procesado: ~$0.002 USD (Groq free tier cubre demo completo)
- Costo operativo mensual: $20 USD (Replit Core)
- Costo escala 1.000 casos/mes: ~$2–5 USD adicional en Groq si supera free tier

### Modelo de ingresos (potencial)
- Licencia SaaS a clínicas jurídicas: $50–150 USD/mes por clínica
- 47 clínicas universitarias en Colombia = $2.350–7.050 USD/mes
- Punto de equilibrio: ~14–40 clínicas

### Impacto social (no financiero)
- Reducción de carga en SIC: casos mejor documentados = menos devoluciones
- Acceso a justicia para consumidores informales (70% sin asesoría)
- Replicable en otros países latinoamericanos con regulación de consumo similar

---

## Cronograma sugerido

| Cuándo | Qué hacer |
|---|---|
| Hoy | Crear los documentos de prueba (Tarea 1) |
| Hoy | Estructura base del deck (Tarea 2, slides 1–8) |
| Cuando el sistema esté funcionando | Tomar capturas de pantalla reales |
| 1 día antes del demo | Grabar video de respaldo (Tarea 4) |
| Día del demo | Llegar 30 min antes, probar el flujo completo con los documentos de prueba |

---

## Preguntas frecuentes

**¿Los documentos de prueba tienen que ser reales?**
No. Son completamente ficticios. Solo necesitan ser coherentes internamente (fechas, montos, nombres que cuadren).

**¿Qué formato de slide recomiendas?**
Google Slides o PowerPoint. Fondo oscuro (azul marino o negro) con texto blanco — se ve mejor en proyector.

**¿Cuánto tiempo tenemos para el demo en el hackathon?**
Confirma con el equipo. Este script asume 3–4 minutos de demo + 8 minutos de presentación.

**¿Necesito entender el código?**
No. Tu rol es la narrativa, los documentos de prueba y la presentación.

---

*Última actualización: 2026-04-11 — Semillero LegalTech ICESI*
