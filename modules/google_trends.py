from datetime import datetime

# Real KPK-related keywords to track interest in Google Trends
KPK_TREND_KEYWORDS = [
    ["KPK", "Peshawar", "Khyber Pakhtunkhwa", "PDMA KPK", "KPK Police"],
    ["Swat", "Mardan", "Abbottabad", "Nowshera", "Charsadda"],
    ["PTI KPK", "CM KPK", "KPK Budget", "KPK Health", "KPK Education"],
]


def fetch_trends():
    try:
        from pytrends.request import TrendReq
        pt = TrendReq(hl="en-US", tz=300)
        results = []
        rank = 1

        for batch in KPK_TREND_KEYWORDS:
            try:
                pt.build_payload(batch, geo="PK", timeframe="now 7-d")
                data = pt.interest_over_time()
                if data.empty:
                    continue
                latest = data.iloc[-1]
                for kw in batch:
                    score = int(latest.get(kw, 0))
                    if score > 0:
                        results.append({
                            "rank": rank,
                            "title": kw,
                            "score": score,
                            "traffic": f"{score}/100 interest",
                            "url": f"https://trends.google.com/trends/explore?q={kw.replace(' ', '+')}&geo=PK",
                            "published_at": datetime.utcnow().isoformat(),
                            "module": "google_trends",
                        })
                        rank += 1
            except Exception as e:
                print(f"[google_trends] Batch error: {e}")
                continue

        # Sort by score descending and re-rank
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        for i, r in enumerate(results, 1):
            r["rank"] = i

        # Also fetch related queries for top KPK term
        try:
            pt.build_payload(["KPK"], geo="PK", timeframe="now 7-d")
            related = pt.related_queries()
            top_queries = related.get("KPK", {}).get("top", None)
            if top_queries is not None and not top_queries.empty:
                for _, row in top_queries.head(5).iterrows():
                    query = str(row.get("query", ""))
                    value = int(row.get("value", 0))
                    if query and "kpk" not in query.lower() and query.lower() not in [r["title"].lower() for r in results]:
                        results.append({
                            "rank": len(results) + 1,
                            "title": query,
                            "score": value,
                            "traffic": f"{value}/100 interest",
                            "url": f"https://trends.google.com/trends/explore?q={query.replace(' ', '+')}&geo=PK",
                            "published_at": datetime.utcnow().isoformat(),
                            "module": "google_trends",
                        })
        except Exception as e:
            print(f"[google_trends] Related queries error: {e}")

        print(f"[google_trends] {len(results)} real trends from Google")
        return results[:12] if results else _fallback()

    except Exception as e:
        print(f"[google_trends] Error: {e}")
        return _fallback()


def _fallback():
    """Last resort — clearly labeled as unavailable."""
    return []
