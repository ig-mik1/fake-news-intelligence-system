from verification.source_checker import source_score
from verification.consensus_checker import consensus_score


def compute_trust(prediction, confidence, text, source=None):

    # ML risk component
    ml_score = confidence

    # Source credibility
    src_score = source_score(source)

    # News consensus
    cons_score = consensus_score(text)

    # Final weighted trust
    trust = (
        0.4 * ml_score +
        0.3 * src_score +
        0.3 * cons_score
    )

    return {
        "trust_score": round(trust * 100, 2),
        "ml_score": round(ml_score * 100, 2),
        "source_score": round(src_score * 100, 2),
        "consensus_score": round(cons_score * 100, 2)
    }