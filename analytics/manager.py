import json
from pathlib import Path


class AnalyticsManager:
    def __init__(self):
        self.file = Path("analytics/analytics.json")

        if not self.file.exists():
            self.file.parent.mkdir(exist_ok=True)

            with open(self.file, "w") as f:
                json.dump(
                    {
                        "total_questions": 0,
                        "answered_questions": 0,
                        "escalated_questions": 0,
                        "avg_confidence": 0,
                        "top_questions": {}
                    },
                    f,
                    indent=2,
                )

    def load(self):
        with open(self.file, "r") as f:
            return json.load(f)

    def save(self, data):
        with open(self.file, "w") as f:
            json.dump(data, f, indent=2)

    def log_question(self, question, confidence, escalated=False):
        data = self.load()

        data["total_questions"] += 1

        if escalated:
            data["escalated_questions"] += 1
        else:
            data["answered_questions"] += 1

        prev_total = data["total_questions"] - 1

        if prev_total == 0:
            data["avg_confidence"] = confidence
        else:
            data["avg_confidence"] = (
                (data["avg_confidence"] * prev_total + confidence)
                / data["total_questions"]
            )

        key = question.lower()

        data["top_questions"][key] = (
            data["top_questions"].get(key, 0) + 1
        )

        self.save(data)

    def get_stats(self):
        return self.load()