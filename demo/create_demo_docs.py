"""
Script para crear los documentos de prueba de los 3 escenarios del demo.
Genera PDFs simples usando reportlab.
Ejecutar desde la raíz del proyecto: python3 demo/create_demo_docs.py
"""
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import cm

BASE = os.path.dirname(os.path.abspath(__file__))

def make_pdf(path: str, lines: list[str], title: str = ""):
    c = canvas.Canvas(path, pagesize=letter)
    w, h = letter
    y = h - 2 * cm
    if title:
        c.setFont("Helvetica-Bold", 14)
        c.drawString(2 * cm, y, title)
        y -= 0.8 * cm
        c.setLineWidth(0.5)
        c.line(2 * cm, y, w - 2 * cm, y)
        y -= 0.6 * cm
    c.setFont("Helvetica", 10)
    for line in lines:
        if y < 2 * cm:
            c.showPage()
            y = h - 2 * cm
            c.setFont("Helvetica", 10)
        if line.startswith("**") and line.endswith("**"):
            c.setFont("Helvetica-Bold", 10)
            line = line[2:-2]
        else:
            c.setFont("Helvetica", 10)
        c.drawString(2 * cm, y, line)
        y -= 0.5 * cm
    c.save()
    print(f"  Creado: {path}")


# ─── ESCENARIO A: Producto defectuoso ────────────────────────────────────────
a_dir = os.path.join(BASE, "escenario_a")
os.makedirs(a_dir, exist_ok=True)

make_pdf(
    os.path.join(a_dir, "factura_samsung.pdf"),
    title="FACTURA DE VENTA — TecnoPlus S.A.S.",
    lines=[
        "NIT: 900.123.456-7",
        "Carrera 9 # 14-45, Cali, Valle del Cauca",
        "Tel: (602) 555-0101",
        "",
        "**FACTURA No. 2025-10847**",
        "Fecha: 15 de octubre de 2025",
        "",
        "DATOS DEL CLIENTE",
        "Nombre: Rosa Inés Morales Vargas",
        "Cédula: 32.456.789",
        "Dirección: Calle 15 # 8-32, Barrio San Nicolás, Cali",
        "Teléfono: 301-567-8901",
        "",
        "DESCRIPCIÓN DEL PRODUCTO",
        "Artículo: Samsung Galaxy A54 — Color Negro Grafito",
        "IMEI: 352 547 113 456 789",
        "Cantidad: 1 (una) unidad",
        "Precio unitario: $1.200.000 COP",
        "Descuento: $0",
        "**TOTAL: $1.200.000 COP**",
        "",
        "Forma de pago: Efectivo",
        "",
        "GARANTÍA",
        "Este producto cuenta con garantía legal de 1 año conforme a la Ley 1480 de 2011.",
        "Para hacer efectiva la garantía diríjase a cualquiera de nuestros puntos de servicio",
        "con esta factura y el empaque original.",
        "",
        "Recibí conforme: _______________________",
        "                Rosa Inés Morales Vargas",
        "",
        "Vendedor: Carlos Andrés Peña",
        "Firma del vendedor: _______________________",
    ],
)

make_pdf(
    os.path.join(a_dir, "pqr_tecnoplus.pdf"),
    title="DERECHO DE PETICIÓN / PQR — TecnoPlus S.A.S.",
    lines=[
        "Cali, 18 de diciembre de 2025",
        "",
        "Señores",
        "TECNOPLUS S.A.S.",
        "Carrera 9 # 14-45, Cali, Valle del Cauca",
        "",
        "Asunto: Solicitud de garantía legal — Samsung Galaxy A54",
        "",
        "Yo, ROSA INÉS MORALES VARGAS, identificada con cédula de ciudadanía No. 32.456.789,",
        "respetuosamente me dirijo a ustedes para solicitar la aplicación de la garantía legal",
        "sobre el equipo Samsung Galaxy A54, IMEI 352547113456789, adquirido en su",
        "establecimiento el 15 de octubre de 2025 por valor de $1.200.000 COP.",
        "",
        "**HECHOS:**",
        "1. Adquirí el equipo el 15/10/2025 en la tienda TecnoPlus de Cali.",
        "2. A partir del 20 de noviembre de 2025 el equipo presentó fallas:",
        "   - Apagado espontáneo sin causa aparente",
        "   - Manchas en la pantalla (líneas amarillas y azules)",
        "3. El 10 de diciembre de 2025 acudí a la tienda y el vendedor Carlos Peña",
        "   indicó que el daño era por mal uso del usuario y se negó a aplicar la garantía.",
        "",
        "**PRETENSIÓN:**",
        "Que se haga efectiva la garantía legal mediante la reparación o cambio del equipo",
        "por uno nuevo en perfectas condiciones, conforme al artículo 10 de la Ley 1480.",
        "",
        "En caso de no atender esta solicitud en el término legal (15 días hábiles),",
        "acudiré ante la Superintendencia de Industria y Comercio (SIC).",
        "",
        "Atentamente,",
        "",
        "Rosa Inés Morales Vargas",
        "C.C. 32.456.789",
        "Calle 15 # 8-32, Barrio San Nicolás, Cali",
        "Tel: 301-567-8901",
        "rosa.morales@email.com",
    ],
)

make_pdf(
    os.path.join(a_dir, "respuesta_tecnoplus.pdf"),
    title="RESPUESTA A PQR — TecnoPlus S.A.S.",
    lines=[
        "Cali, 30 de diciembre de 2025",
        "",
        "Señora",
        "Rosa Inés Morales Vargas",
        "Calle 15 # 8-32, Barrio San Nicolás, Cali",
        "",
        "Respetada señora:",
        "",
        "En respuesta a su petición radicada el 18 de diciembre de 2025 con radicado",
        "No. TPS-2025-4421, relacionada con el equipo Samsung Galaxy A54,",
        "informamos lo siguiente:",
        "",
        "Luego de revisar el caso, nuestro técnico certificado determinó que las fallas",
        "reportadas son producto de golpes y maltrato del usuario, evidenciados por",
        "micro-rayones en el chasis y humedad interna.",
        "",
        "En consecuencia, el daño no está cubierto por la garantía legal, ya que",
        "corresponde a causas imputables al consumidor conforme al artículo 16,",
        "parágrafo 2 de la Ley 1480 de 2011.",
        "",
        "Lamentamos no poder atender favorablemente su solicitud.",
        "",
        "Cordialmente,",
        "",
        "Gerencia de Servicio al Cliente",
        "TecnoPlus S.A.S.",
        "NIT: 900.123.456-7",
    ],
)

print("\n✅ Escenario A — 3 documentos creados")

# ─── ESCENARIO B: Cobro indebido financiero ──────────────────────────────────
b_dir = os.path.join(BASE, "escenario_b")
os.makedirs(b_dir, exist_ok=True)

make_pdf(
    os.path.join(b_dir, "contrato_credito.pdf"),
    title="CONTRATO DE CRÉDITO DE CONSUMO — FinCrece S.A.",
    lines=[
        "NIT: 800.987.654-3 (No vigilado por Superfinanciera)",
        "Calle 72 # 10-15, Bogotá D.C.",
        "",
        "**CONTRATO No. CC-2025-00892**",
        "Fecha: 5 de marzo de 2025",
        "",
        "DATOS DEL DEUDOR",
        "Nombre: Pedro Alejandro Gómez Rueda",
        "Cédula: 79.234.567",
        "Dirección: Carrera 45 # 26-33, Bogotá",
        "",
        "CONDICIONES DEL CRÉDITO",
        "Monto aprobado: $5.000.000 COP",
        "Tasa de interés mensual: 2.4% (dentro del límite legal)",
        "Plazo: 24 cuotas mensuales",
        "Cuota mensual: $279.000 COP",
        "Seguro de vida deudor: $8.500/mes (incluido en cuota)",
        "**TOTAL DESEMBOLSADO: $5.000.000 COP**",
        "",
        "CARGOS ADICIONALES PACTADOS: Ninguno",
        "",
        "Firma del deudor: _______________________",
        "Firma FinCrece: _______________________",
    ],
)

make_pdf(
    os.path.join(b_dir, "extracto_enero_2026.pdf"),
    title="EXTRACTO DE CUENTA — FinCrece S.A. — Enero 2026",
    lines=[
        "Cuenta No.: CC-2025-00892",
        "Titular: Pedro Alejandro Gómez Rueda",
        "C.C.: 79.234.567",
        "Período: 01/01/2026 — 31/01/2026",
        "",
        "**MOVIMIENTOS DEL MES**",
        "",
        "Fecha       Concepto                          Débito      Saldo",
        "01/01/2026  Saldo anterior                              $3.900.000",
        "05/01/2026  Cuota mensual No. 11              $279.000  $3.621.000",
        "05/01/2026  Cobro administración plataforma   $35.000   $3.586.000",
        "05/01/2026  Seguro adicional «Protección Plus» $22.000  $3.564.000",
        "15/01/2026  Cargo por 'consulta de saldo'     $5.000    $3.559.000",
        "",
        "**TOTAL COBRADO EN EL MES: $341.000 COP**",
        "Cuota contractual: $279.000 COP",
        "**COBROS ADICIONALES NO PACTADOS: $62.000 COP**",
        "",
        "Nota: Los cargos adicionales corresponden a nuevos servicios",
        "incluidos en sus beneficios desde enero 2026.",
    ],
)

make_pdf(
    os.path.join(b_dir, "pqr_fincrece.pdf"),
    title="PETICIÓN DE DEVOLUCIÓN DE COBROS INDEBIDOS — FinCrece S.A.",
    lines=[
        "Bogotá, 20 de enero de 2026",
        "",
        "Señores",
        "FINCREICE S.A.",
        "Calle 72 # 10-15, Bogotá",
        "",
        "Asunto: Cobros no autorizados en crédito CC-2025-00892",
        "",
        "Yo, PEDRO ALEJANDRO GÓMEZ RUEDA, C.C. 79.234.567, solicito la devolución",
        "de $62.000 COP cobrados de forma indebida en enero de 2026:",
        "",
        "- Cobro administración plataforma: $35.000 (no pactado en contrato)",
        "- Seguro «Protección Plus»: $22.000 (no autorizado, no mencionado en contrato)",
        "- Cargo consulta de saldo: $5.000 (servicio gratuito en contrato)",
        "",
        "Ninguno de estos cargos fue pactado en el contrato No. CC-2025-00892",
        "firmado el 5 de marzo de 2025, ni fue informado previamente conforme",
        "a los artículos 3, 5 y 23 de la Ley 1480 de 2011.",
        "",
        "Solicito:",
        "1. Devolución inmediata de $62.000 COP",
        "2. Garantía de no repetición de estos cobros",
        "3. Respuesta por escrito en 15 días hábiles",
        "",
        "Pedro Alejandro Gómez Rueda",
        "C.C. 79.234.567",
    ],
)

print("✅ Escenario B — 3 documentos creados")

# ─── ESCENARIO C: Telecomunicaciones con PQR previa ──────────────────────────
c_dir = os.path.join(BASE, "escenario_c")
os.makedirs(c_dir, exist_ok=True)

make_pdf(
    os.path.join(c_dir, "contrato_claro.pdf"),
    title="CONTRATO DE PRESTACIÓN DE SERVICIOS — Claro Colombia S.A.",
    lines=[
        "NIT: 800.153.993-6",
        "Plan contratado: Hogar Total Plus",
        "Contrato No.: CLR-2024-774321",
        "Fecha: 10 de julio de 2024",
        "",
        "DATOS DEL SUSCRIPTOR",
        "Nombre: María Fernanda Ospina Castro",
        "Cédula: 43.567.890",
        "Dirección: Avenida El Poblado # 43A-25, Medellín",
        "Teléfono de contacto: 300-456-7890",
        "",
        "SERVICIOS CONTRATADOS",
        "Internet fibra óptica: 200 Mbps simétrico",
        "Televisión por cable: 120 canales HD",
        "Teléfono fijo: incluido",
        "",
        "**TARIFA MENSUAL: $89.900 COP (incluye IVA)**",
        "Permanencia mínima: 12 meses",
        "",
        "Velocidad garantizada mínima: 60% velocidad contratada = 120 Mbps",
        "Disponibilidad del servicio garantizada: 99.5% mensual",
        "",
        "Firma del suscriptor: _______________________",
        "Representante Claro: _______________________",
    ],
)

make_pdf(
    os.path.join(c_dir, "pqr_claro_radicado.pdf"),
    title="RADICADO PQR ANTE CLARO — No. 2025-CLR-88234",
    lines=[
        "Medellín, 5 de octubre de 2025",
        "",
        "Radicado: 2025-CLR-88234",
        "Canal: App MiClaro",
        "Estado: RESPONDIDA",
        "",
        "**DESCRIPCIÓN DEL PROBLEMA:**",
        "Desde el 1 de octubre de 2025 el servicio de internet presenta fallas continuas:",
        "- Velocidad real medida: 15-20 Mbps (contratada: 200 Mbps)",
        "- Interrupciones diarias entre 7pm y 11pm (horario pico)",
        "- Televisión con pixelación constante y canales no disponibles",
        "",
        "Herramientas de medición utilizadas: fast.com, speedtest.net",
        "Capturas de pantalla adjuntas: Sí (4 imágenes)",
        "",
        "**RESPUESTA DE CLARO (12 de octubre de 2025):**",
        "'Su queja fue revisada por nuestro equipo técnico. Se realizó mantenimiento",
        "preventivo en la red de su sector. El servicio debe estar normalizado.",
        "Si persisten inconvenientes, comuníquese nuevamente.'",
        "",
        "**RESULTADO:** El problema NO fue solucionado. Las fallas continúan",
        "después de la supuesta intervención técnica.",
        "",
        "Suscriptor: María Fernanda Ospina Castro",
        "C.C.: 43.567.890",
    ],
)

make_pdf(
    os.path.join(c_dir, "evidencia_velocidad.pdf"),
    title="EVIDENCIA DE FALLAS EN SERVICIO DE INTERNET — Claro",
    lines=[
        "Titular del servicio: María Fernanda Ospina Castro",
        "C.C.: 43.567.890",
        "Contrato No.: CLR-2024-774321",
        "Período de mediciones: 1 al 31 de octubre de 2025",
        "",
        "**MEDICIONES DE VELOCIDAD INTERNET**",
        "(Herramienta: speedtest.net — Servidor: Claro Medellín)",
        "",
        "Fecha        Hora    Bajada   Subida   Latencia",
        "01/10/2025   20:15   16 Mbps  14 Mbps  145 ms",
        "03/10/2025   21:00   11 Mbps   9 Mbps  210 ms",
        "05/10/2025   19:45   18 Mbps  15 Mbps  132 ms",
        "08/10/2025   22:10    8 Mbps   7 Mbps  287 ms",
        "10/10/2025   20:30   22 Mbps  18 Mbps  118 ms",
        "15/10/2025   21:15   13 Mbps  11 Mbps  198 ms",
        "20/10/2025   20:45   17 Mbps  14 Mbps  156 ms",
        "25/10/2025   22:00    9 Mbps   8 Mbps  312 ms",
        "31/10/2025   21:30   19 Mbps  16 Mbps  143 ms",
        "",
        "**PROMEDIO MEDIDO: 14.8 Mbps bajada**",
        "**VELOCIDAD CONTRATADA: 200 Mbps**",
        "**VELOCIDAD MÍNIMA GARANTIZADA: 120 Mbps**",
        "**INCUMPLIMIENTO: 87.6% por debajo del mínimo garantizado**",
        "",
        "Nota: Interrupciones totales registradas en octubre: 23 eventos",
        "Tiempo acumulado sin servicio: aprox. 18 horas",
        "Disponibilidad real: 97.5% (por debajo del 99.5% contractual)",
        "",
        "Certifico que esta información es veraz.",
        "",
        "María Fernanda Ospina Castro",
        "C.C. 43.567.890",
        "Fecha de elaboración: 1 de noviembre de 2025",
    ],
)

print("✅ Escenario C — 3 documentos creados")
print("\n✅ Todos los documentos de demo creados exitosamente.")
