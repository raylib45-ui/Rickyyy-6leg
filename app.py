import base64
import json
import os
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Rick Sanchez PrizePicks Engine", page_icon="🧪", layout="wide")

SYSTEM_PROMPT = r"""
You are Rick Sanchez, a strict PrizePicks analytics parser. Read the supplied screenshot.
Return JSON only with this schema:
{"sport":"string","captured_at_utc":"ISO-8601","entries":[
 {"player":"string","team":"string|null","opponent":"string|null","market":"string",
  "line":number,"direction_options":["OVER","UNDER"],"game_time":"string|null",
  "screenshot_confidence":number}
]}
Rules: transcribe only what is visible. Never invent a player, line, team, market, or game.
If a field is not visible, use null. Include every visible PrizePicks entry. Screenshot confidence is 0-1.
"""

REQUIRED_COLUMNS = ["player", "team", "opponent", "market", "line", "sport", "game_time"]


def image_to_data_url(uploaded_file) -> str:
    raw = uploaded_file.getvalue()
    mime = uploaded_file.type or "image/png"
    return f"data:{mime};base64," + base64.b64encode(raw).decode("utf-8")


def parse_screenshot(uploaded_file) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing. Add it in Streamlit secrets before using screenshot parsing.")
    payload = {
        "model": os.getenv("VISION_MODEL", "gpt-4o-mini"),
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": [
            {"type": "text", "text": "Parse this PrizePicks screenshot exactly."},
            {"type": "image_url", "image_url": {"url": image_to_data_url(uploaded_file)}}
        ]}]
    }
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=90,
    )
    response.raise_for_status()
    return json.loads(response.json()["choices"][0]["message"]["content"])


def normalize_entries(parsed: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for item in parsed.get("entries", []):
        try:
            line = float(item["line"])
        except (KeyError, TypeError, ValueError):
            continue
        rows.append({
            "player": str(item.get("player", "")).strip(),
            "team": item.get("team"),
            "opponent": item.get("opponent"),
            "market": str(item.get("market", "")).strip(),
            "line": line,
            "sport": item.get("sport") or parsed.get("sport") or "unknown",
            "game_time": item.get("game_time"),
            "screenshot_confidence": float(item.get("screenshot_confidence", 0)),
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=REQUIRED_COLUMNS + ["screenshot_confidence"])
    return df.drop_duplicates(subset=["player", "market", "line"]).reset_index(drop=True)


def fetch_current_analytics(df: pd.DataFrame) -> pd.DataFrame:
    url = os.getenv("ANALYTICS_URL")
    if not url:
        raise RuntimeError("ANALYTICS_URL is missing. Connect a current-data analytics service before generating picks.")
    response = requests.post(url, json={"entries": df.to_dict(orient="records")}, timeout=90)
    response.raise_for_status()
    result = pd.DataFrame(response.json().get("entries", []))
    if result.empty:
        raise RuntimeError("The analytics service returned no current entries.")
    required = ["player", "market", "line", "projection", "projection_low", "projection_high",
                "season_rate", "recent_rate", "hit_probability_over", "hit_probability_under",
                "availability_status", "data_as_of_utc", "matchup_note", "risk_note"]
    missing = [c for c in required if c not in result.columns]
    if missing:
        raise RuntimeError(f"Analytics response is missing required fields: {', '.join(missing)}")
    return df.merge(result, on=["player", "market", "line"], how="inner")


def score_candidates(df: pd.DataFrame) -> pd.DataFrame:
    now = datetime.now(timezone.utc)
    out = df.copy()
    out["data_age_hours"] = (now - pd.to_datetime(out["data_as_of_utc"], utc=True)).dt.total_seconds() / 3600
    out["direction"] = out.apply(lambda r: "OVER" if r["hit_probability_over"] >= r["hit_probability_under"] else "UNDER", axis=1)
    out["win_probability"] = out.apply(lambda r: max(r["hit_probability_over"], r["hit_probability_under"]), axis=1)
    out["edge_vs_line"] = out.apply(lambda r: (r["projection"] - r["line"]) if r["direction"] == "OVER" else (r["line"] - r["projection"]), axis=1)
    out["range_clear"] = out.apply(lambda r: (r["projection_low"] > r["line"]) if r["direction"] == "OVER" else (r["projection_high"] = 0.80) &
        (out["win_probability"] >= 0.57) &
        (out["edge_vs_line"].abs() >= 0.35) &
        (out["range_clear"])
    )
    out["hammer"] = out["eligible"] & (out["win_probability"] >= 0.62) & (out["edge_vs_line"].abs() >= 0.65)
    out["quality_score"] = (
        out["win_probability"] * 100 + out["edge_vs_line"].abs() * 12 + out["recent_rate"] * 8
        - out["data_age_hours"] * 1.5
    )
    return out.sort_values(["hammer", "quality_score"], ascending=False).reset_index(drop=True)


def build_six_legs(scored: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    errors = []
    eligible = scored[scored["eligible"]].copy()
    eligible = eligible.drop_duplicates(subset=["player"])
    if len(eligible)  6:
        errors.append("A selected leg has analytics older than six hours.")
    if selected["availability_status"].str.upper().ne("ACTIVE").any():
        errors.append("A selected leg is not marked ACTIVE.")
    return selected, errors


def render_card(legs: pd.DataFrame, errors: list[str], parsed: dict[str, Any]):
    st.subheader("Rick Sanchez six-leg card")
    if errors:
        st.error("NO CARD ISSUED")
        for error in errors:
            st.write(f"• {error}")
        return
    st.success("Six legs passed the screenshot, freshness, availability, and hammer rules.")
    display_cols = ["player", "team", "market", "line", "direction", "projection", "projection_low", "projection_high", "win_probability", "hammer", "data_as_of_utc"]
    view = legs[display_cols].copy()
    view["win_probability"] = (view["win_probability"] * 100).round(1).astype(str) + "%"
    st.dataframe(view, use_container_width=True, hide_index=True)
    hammers = legs[legs["hammer"]]
    st.markdown(f"**Hammer count:** {len(hammers)}/6")
    st.caption("Hammer means the model found both a meaningful projection gap and a current probability edge. It is not a guarantee.")
    for _, row in legs.iterrows():
        st.write(f"**{row['player']} {row['direction']} {row['line']} {row['market']}**. Projection {row['projection']:.2f}, range {row['projection_low']:.2f} to {row['projection_high']:.2f}, win probability {row['win_probability']:.1%}. {row['matchup_note']} Risk: {row['risk_note']}")
    audit = {"generated_at_utc": datetime.now(timezone.utc).isoformat(), "screenshot_parse": parsed, "legs": legs.to_dict(orient="records"), "errors": errors}
    st.download_button("Download analytics audit JSON", json.dumps(audit, indent=2, default=str), "rick-sanchez-audit.json", "application/json")

st.title("🧪 Rick Sanchez PrizePicks Engine")
st.caption("Screenshot-gated • current analytics required • exactly six unique players")
st.warning("Upload every PrizePicks board screenshot first. The app refuses to issue a card when OCR, availability, freshness, or analytics checks fail.")

uploads = st.file_uploader("PrizePicks screenshots (mandatory)", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True)
if not uploads:
    st.info("No screenshots, no picks. This is intentional.")
    st.stop()

if st.button("Parse screenshots and run Rick's audit", type="primary"):
    try:
        parsed_all = []
        for upload in uploads:
            parsed = parse_screenshot(upload)
            parsed_all.extend(parsed.get("entries", []))
        parsed = {"sport": "mixed", "captured_at_utc": datetime.now(timezone.utc).isoformat(), "entries": parsed_all}
        entries = normalize_entries(parsed)
        if entries.empty:
            st.error("No usable PrizePicks entries were read. Upload clearer screenshots with the player, market, and line visible.")
            st.stop()
        st.subheader("Screenshot transcription")
        st.dataframe(entries, use_container_width=True, hide_index=True)
        analytics = fetch_current_analytics(entries)
        scored = score_candidates(analytics)
        legs, errors = build_six_legs(scored)
        render_card(legs, errors, parsed)
        st.subheader("Full candidate audit")
        st.dataframe(scored, use_container_width=True, hide_index=True)
    except Exception as exc:
        st.error(f"Run stopped: {exc}")
        st.info("Fix the missing connection or screenshot quality issue. Rick never fills missing data with guesses.")