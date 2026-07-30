def clean_repeated_phrases(text: str) -> str:
    """Remove repetições de palavras/expressões coladas umas nas outras no
    mesmo texto (comum em títulos de produto com "recheio" de palavra-chave
    pra SEO, ex: "Secador de cabelo Secador de cabelo Secador de cabelo").

    Só remove uma repetição quando ela aparece exatamente colada (sem
    palavras diferentes no meio) - isso evita cortar por engano conteúdo
    legítimo que apenas menciona o mesmo termo mais de uma vez em contextos
    diferentes.
    """
    if not text:
        return text

    words = text.split()
    changed = True
    while changed:
        changed = False
        max_phrase_len = len(words) // 2
        for phrase_len in range(max_phrase_len, 0, -1):
            new_words = []
            i = 0
            found_at_this_length = False
            while i < len(words):
                window_a = words[i:i + phrase_len]
                window_b = words[i + phrase_len:i + 2 * phrase_len]
                if len(window_b) == phrase_len and [w.lower() for w in window_a] == [
                    w.lower() for w in window_b
                ]:
                    new_words.extend(window_a)
                    i += 2 * phrase_len
                    found_at_this_length = True
                else:
                    new_words.append(words[i])
                    i += 1
            if found_at_this_length:
                words = new_words
                changed = True
                break

    return " ".join(words)


def format_currency_2_decimals(raw_value) -> str:
    """Converte um valor numérico (string ou número) para o formato
    "1234,56" (2 casas decimais, vírgula). Se não for numérico, devolve o
    valor original sem alterar."""
    if raw_value is None:
        return None
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        return str(raw_value)
    return f"{value:.2f}".replace(".", ",")
