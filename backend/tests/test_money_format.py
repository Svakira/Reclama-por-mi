from backend.utils.money_format import number_to_cop_words, format_cop_amount


def test_cop_words_simple_millions():
    assert number_to_cop_words(1_200_000) == "un millon doscientos mil pesos colombianos"


def test_cop_words_zero():
    assert number_to_cop_words(0) == "cero pesos colombianos"


def test_format_cop_amount_includes_number_and_words():
    assert format_cop_amount(98500) == "$98.500 (noventa y ocho mil quinientos pesos colombianos)"
