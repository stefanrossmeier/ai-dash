import json


class FakeImpactRanker:
    def __init__(self, score=80, groups=None):
        self.score, self.groups = score, groups
        self.calls, self.traces = [], []

    def request(self, route, body):
        self.calls.append(body)
        candidates = json.loads(body["messages"][1]["content"])["candidates"]
        if body["purpose"] == "ai-news-consolidation":
            return {
                "content": {
                    "groups": self.groups
                    or [{"representative": c["id"], "duplicates": []} for c in candidates]
                }
            }
        if body["purpose"] == "ai-news-summaries":
            return {
                "content": {
                    "summaries": {
                        c[
                            "id"
                        ]: "New AI capabilities change production workflows with measured gains. "
                        * 4
                        for c in candidates
                    }
                }
            }
        return {
            "content": {
                "evaluations": {
                    c["id"]: {
                        "rank_score": self.score,
                        "impact": self.score,
                        "breadth": self.score,
                        "novelty": self.score,
                        "quality": self.score,
                        "tier": 4,
                        "change_type": "new_capability",
                        "event_key": f"event-{n}",
                        "reason": "Material capability with broad engineering consequences.",
                    }
                    for n, c in enumerate(candidates)
                }
            }
        }
