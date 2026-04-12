def _under_hundred(n: int) -> str:
    units = [
        "cero",
        "uno",
        "dos",
        "tres",
        "cuatro",
        "cinco",
        "seis",
        "siete",
        "ocho",
        "nueve",
        "diez",
        "once",
        "doce",
        "trece",
        "catorce",
        "quince",
        "dieciseis",
        "diecisiete",
        "dieciocho",
        "diecinueve",
    ]
    tens = [
        "",
        "",
        "veinte",
        "treinta",
        "cuarenta",
        "cincuenta",
        "sesenta",
        "setenta",
        "ochenta",
        "noventa",
    ]

    if n < 20:
        return units[n]
    if n < 30:
        if n == 20:
            return "veinte"
        return "veinti" + units[n - 20]

    dec = n // 10
    rem = n % 10
    if rem == 0:
        return tens[dec]
    return f"{tens[dec]} y {units[rem]}"


def _under_thousand(n: int) -> str:
    hundreds_map = {
        1: "ciento",
        2: "doscientos",
        3: "trescientos",
        4: "cuatrocientos",
        5: "quinientos",
        6: "seiscientos",
        7: "setecientos",
        8: "ochocientos",
        9: "novecientos",
    }

    if n == 0:
        return ""
    if n < 100:
        return _under_hundred(n)
    if n == 100:
        return "cien"

    c = n // 100
    rem = n % 100
    base = hundreds_map[c]
    if rem == 0:
        return base
    return f"{base} {_under_hundred(rem)}"


def _int_to_words_es(n: int) -> str:
    if n == 0:
        return "cero"

    parts = []

    billions = n // 1_000_000_000
    n %= 1_000_000_000
    millions = n // 1_000_000
    n %= 1_000_000
    thousands = n // 1000
    remainder = n % 1000

    if billions:
        if billions == 1:
            parts.append("mil millones")
        else:
            parts.append(f"{_under_thousand(billions)} mil millones")

    if millions:
        if millions == 1:
            parts.append("un millon")
        else:
            parts.append(f"{_under_thousand(millions)} millones")

    if thousands:
        if thousands == 1:
            parts.append("mil")
        else:
            parts.append(f"{_under_thousand(thousands)} mil")

    if remainder:
        parts.append(_under_thousand(remainder))

    return " ".join(p for p in parts if p).strip()


def number_to_cop_words(value: int) -> str:
    value = int(value)
    if value < 0:
        return f"menos {_int_to_words_es(abs(value))} pesos colombianos"
    return f"{_int_to_words_es(value)} pesos colombianos"


def format_cop_amount(value: int) -> str:
    amount = int(value)
    numeric = f"${amount:,}".replace(",", ".")
    return f"{numeric} ({number_to_cop_words(amount)})"
