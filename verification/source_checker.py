TRUSTED_SOURCES = {
    "bbc": 0.95,
    "reuters": 0.98,
    "cnn": 0.85,
    "guardian": 0.9,
    "ap": 0.97
}


def source_score(source):

    if not source:
        return 0.4

    source = source.lower()

    for s in TRUSTED_SOURCES:
        if s in source:
            return TRUSTED_SOURCES[s]

    return 0.5