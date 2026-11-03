"""Load mode-isolated histories and explicit historical evidence, never infer membership."""
import json
import os
from pathlib import Path

from app.repositories.portfolio import load_dataset
from app.schemas.backtest import HistoryReviewFile
from app.services.portfolio import PortfolioError
from app.services.synthetic_history import dataset


def load_history(db,mode):
    if mode=="synthetic":
        return dataset()
    data=load_dataset(db,"real",load_reviews=False)
    data.update(calendar=[],membership_events=[],membership_history_verified=False,
                universe_reference="No verified historical universe; 2026 snapshot is not 2022–2025 membership",
                universe_kind="unverified",coverage_start=None,coverage_end=None,reviews={})
    path=os.environ.get("BACKTEST_REVIEW_FILE")
    if path:
        try:
            evidence=HistoryReviewFile.model_validate(json.loads(Path(path).read_text()))
            data.update(evidence.model_dump(mode="json"))
        except (OSError,ValueError,TypeError) as exc:
            raise PortfolioError("Historical review file invalid/unreadable; no point-in-time approval inferred") from exc
    return data
