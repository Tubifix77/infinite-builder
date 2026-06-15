import re
import requests

_ANGLES = [
    "{goal} UX patterns best practices",
    "{goal} visual design inspiration",
    "{goal} features comparison",
    "{goal} accessibility design",
    "{goal} animation interaction design",
]


def inspiration_query(goal: str, iteration: int) -> str:
    template = _ANGLES[(iteration - 1) % len(_ANGLES)]
    return template.format(goal=goal)


class Searcher:
    def search(self, query: str, n: int = 5) -> list[str]:
        try:
            resp = requests.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=2,
            )
            titles = re.findall(r'class="result__a"[^>]*>([^<]+)<', resp.text)
            snippets = re.findall(r'class="result__snippet"[^>]*>([^<]+)<', resp.text)
            results = titles + snippets
            return [r.strip() for r in results if r.strip()][:n]
        except Exception:
            return []
