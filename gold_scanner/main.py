from .sources.fed import fetch_v01_snapshot as fetch_fed
from .sources.bls import fetch_v01_snapshot as fetch_bls
from .report import print_v01_report
from .scoring import weighted_score, classify


def run():
    fed = fetch_fed()
    bls = fetch_bls()

    print_v01_report(fed, bls)

    # V0.1 deliberately does not infer a market bias yet.
    # Real data is connected and verified first.
    score = weighted_score({})
    print(f"\nCURRENT GOLD SCORE: {score:.1f}")
    print(f"STATE: {classify(score)}")
    print("V0.1.1 STATUS: DATA CONNECTIONS OK; BIAS ENGINE NOT ACTIVE.")


if __name__ == "__main__":
    run()
