"""
Rule-based, explainable recommendation engine.

Honesty note (also in README): this combines a fixed set of signals
(genre match, mood, a simplified MBTI-to-genre heuristic, and overlap with
movies the user says they liked/disliked) into a weighted score against the
bundled dataset. It is a transparent heuristic scorer, not a trained
machine-learning model — there is no claim here of a literal "1000 factor"
neural recommender, since that would require real training data and an ML
pipeline this bot doesn't have. It IS, however, a genuinely useful,
multi-signal, tunable scoring system.
"""

from data.imdb_top import IMDB_TOP
from data.genre_extra import GENRE_EXTRA

MOOD_GENRE_WEIGHTS = {
    "happy": {"Comedy": 3, "Adventure": 2, "Animation": 2, "Family": 1, "Musical": 1},
    "thoughtful": {"Drama": 3, "Sci-Fi": 2, "Mystery": 2, "Biography": 1},
    "relax": {"Comedy": 2, "Family": 2, "Animation": 2, "Romance": 1},
    "intense": {"Action": 3, "Thriller": 3, "Crime": 2, "War": 1},
    "sad": {"Drama": 3, "Romance": 2, "War": 1},
}

# Simplified, non-clinical heuristic mapping of MBTI axes to genre affinity.
# This is a fun heuristic, NOT a validated psychological instrument.
MBTI_GENRE_WEIGHTS = {
    "I": {"Drama": 1, "Mystery": 1},
    "E": {"Action": 1, "Comedy": 1, "Adventure": 1},
    "N": {"Sci-Fi": 2, "Fantasy": 1, "Mystery": 1},
    "S": {"Biography": 1, "History": 1, "Crime": 1},
    "T": {"Thriller": 1, "Sci-Fi": 1, "Crime": 1},
    "F": {"Drama": 1, "Romance": 2, "Family": 1},
    "J": {"Crime": 1, "Drama": 1},
    "P": {"Adventure": 1, "Comedy": 1, "Fantasy": 1},
}


def _all_candidates():
    pool = {}
    for row in IMDB_TOP:
        rank, title, year, kind, imdb, rt, meta, genres = row
        pool[title] = {
            "title": title, "year": year, "type": kind,
            "imdb": imdb, "rt": rt, "meta": meta, "genres": genres,
        }
    for genre, items in GENRE_EXTRA.items():
        for title, year, kind, imdb, rt, meta, genres in items:
            if title not in pool:
                pool[title] = {
                    "title": title, "year": year, "type": kind,
                    "imdb": imdb, "rt": rt, "meta": meta, "genres": genres,
                }
    return list(pool.values())


def _base_score(item):
    scores = [s for s in (item["imdb"], item["rt"] / 10 if item["rt"] else None,
                          item["meta"] / 10 if item["meta"] else None) if s is not None]
    return sum(scores) / len(scores) if scores else 5.0


def _liked_disliked_genre_bias(liked_titles, disliked_titles, pool):
    liked_genres, disliked_genres = {}, {}
    lower_pool = {p["title"].lower(): p for p in pool}
    for name in liked_titles:
        match = lower_pool.get(name.strip().lower())
        if match:
            for g in match["genres"]:
                liked_genres[g] = liked_genres.get(g, 0) + 2
    for name in disliked_titles:
        match = lower_pool.get(name.strip().lower())
        if match:
            for g in match["genres"]:
                disliked_genres[g] = disliked_genres.get(g, 0) + 2
    return liked_genres, disliked_genres


def recommend(genre_pref, mood, mbti, liked_titles, disliked_titles, top_n=6):
    pool = _all_candidates()
    liked_genres, disliked_genres = _liked_disliked_genre_bias(liked_titles, disliked_titles, pool)

    mood_weights = MOOD_GENRE_WEIGHTS.get(mood, {})
    mbti_weights = {}
    if mbti and mbti.upper() != "UNKNOWN":
        for letter in mbti.upper():
            for g, w in MBTI_GENRE_WEIGHTS.get(letter, {}).items():
                mbti_weights[g] = mbti_weights.get(g, 0) + w

    scored = []
    for item in pool:
        score = _base_score(item)
        for g in item["genres"]:
            if genre_pref and g == genre_pref:
                score += 3
            score += mood_weights.get(g, 0) * 0.5
            score += mbti_weights.get(g, 0) * 0.4
            score += liked_genres.get(g, 0) * 0.6
            score -= disliked_genres.get(g, 0) * 0.6
        scored.append((score, item))

    # Filter out things the user explicitly said they disliked
    disliked_lower = {d.strip().lower() for d in disliked_titles}
    scored = [s for s in scored if s[1]["title"].lower() not in disliked_lower]

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:top_n]]
