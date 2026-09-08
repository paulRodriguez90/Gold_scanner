from datetime import datetime, timezone
from .scoring import weighted_score, classify

def run():
    # Connector layer will populate these values.
    # Keeping this empty prevents fake market data from entering the scanner.
    factor_scores = {}

    score = weighted_score(factor_scores)
    state = classify(score)

    print(f"[{datetime.now(timezone.utc).isoformat()}] Gold Score={score:.1f} State={state}")

if __name__ == "__main__":
    run()
