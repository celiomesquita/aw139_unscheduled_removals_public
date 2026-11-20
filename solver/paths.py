from pathlib import Path

ROOT       = Path(__file__).resolve().parent.parent
ANONYMISED = ROOT / "data" / "anonymised"   # real operator data, anonymised (tracked)
RAW        = ROOT / "data" / "raw"          # confidential originals (gitignored)
# Synthetic-data inputs of the original pipeline; removed, pending adaptation to ANONYMISED.
HISTORY    = ROOT / "data" / "history"
MODELS     = ROOT / "data" / "models"
COMPONENTS = ROOT / "data" / "components.txt"
FIGURES    = ROOT / "paper" / "png"
