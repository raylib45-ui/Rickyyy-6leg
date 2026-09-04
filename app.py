import streamlit as st
import pandas as pd
import numpy as np
import math

st.set_page_config(
    page_title="Rick C-137 Live CS2 Miner",
    page_icon="🧪",
    layout="wide"
)

# Standardized layout settings to prevent black screen rendering bugs on mobile browsers
st.title("🧪 Rick C-137 Live CS2 PrizePicks Miner")
st.markdown("*“Clean layout initialized, Morty. No custom dark overrides crashing the mobile view.”*")
st.write("")

def clamp(x, low=0.01, high=0.99):
    return max(low, min(high, x))

def probability_from_z(projected, line, uncertainty):
    if uncertainty <= 0:
        uncertainty = 1
    z = (projected - line) / uncertainty
    return clamp(0.5 * (1 + math.erf(z / math.sqrt(2))))

def calculate_candidate(row):
    try:
        raw_recent = row["recent_results"]
        if isinstance(raw_recent, str):
            recent = np.array([float(x.strip()) for x in raw_recent.replace("[", "").replace("]", "").split(",")], dtype=float)
        else:
            recent = np.array(raw_recent, dtype=float)

        recent_mean = np.mean(recent)
        recent_median = np.median(recent)
        recent_std = np.std(recent, ddof=1) if len(recent) > 1 else 0.0

        projection = (
            0.25 * row["season_projection"]
            + 0.30 * recent_mean
            + 0.20 * recent_median
            + 0.15 * row["matchup_projection"]
            + 0.10 * row["role_projection"]
        ) * row["pace_volume_projection"]

        uncertainty = max(
            row["market_baseline_uncertainty"],
            recent_std * row["sport_variance_factor"]
        )

        raw_more = probability_from_z(projection, row["line"], uncertainty)
        more_prob = clamp(raw_more)
        less_prob = 1 - more_prob

        if more_prob >= less_prob:
            side = "MORE 🔨"
            model_prob = more_prob
            margin = projection - row["line"]
        else:
            side = "LESS 🔨"
            model_prob = less_prob
            margin = row["line"] - projection

        edge = model_prob - row["estimated_market_probability"]

        return {
            "player": row["player"],
            "sport": row["sport"],
            "stat": row["stat"],
            "line": row["line"],
            "side": side,
            "projection": round(projection, 2),
            "margin": round(margin, 2),
            "model_prob": round(model_prob * 100, 1),
            "edge": round(edge * 100, 2),
            "uncertainty": round(uncertainty, 3)
        }
    except Exception:
        return None

@st.cache_data(ttl=600)
def get_cs2_board():
    return pd.DataFrame([
        {
            "player": "Donk", "sport": "CS2", "stat": "Maps 1-2 Kills", "line": 38.5,
            "recent_results": [42.0, 40.0, 44.0, 41.0],
            "season_projection": 41.5, "matchup_projection": 42.0, "role_projection": 41.0,
            "pace_volume_projection": 1.05, "market_baseline_uncertainty": 1.2,
            "sport_variance_factor": 1.1, "estimated_market_probability": 0.52
        },
        {
            "player": "cairne", "sport": "CS2", "stat": "Maps 1-2 Headshots", "line": 16.5,
            "recent_results": [12.0, 13.0, 11.0, 14.0],
            "season_projection": 12.5, "matchup_projection": 12.0, "role_projection": 12.2,
            "pace_volume_projection": 0.92, "market_baseline_uncertainty": 0.8,
            "sport_variance_factor": 1.0, "estimated_market_probability": 0.53
        },
        {
            "player": "xKacpersky", "sport": "CS2", "stat": "Maps 1-2 Kills", "line": 30.5,
            "recent_results": [25.0, 26.0, 24.0, 27.0],
            "season_projection": 25.5, "matchup_projection": 25.0, "role_projection": 25.2,
            "pace_volume_projection": 0.94, "market_baseline_uncertainty": 1.0,
            "sport_variance_factor": 1.1, "estimated_market_probability": 0.54
        },
        {
            "player": "NiKo", "sport": "CS2", "stat": "Maps 1-2 Kills", "line": 28.5,
            "recent_results": [32.0, 31.0, 33.0, 30.0],
            "season_projection": 31.5, "matchup_projection": 32.0, "role_projection": 31.0,
            "pace_volume_projection": 1.04, "market_baseline_uncertainty": 1.1,
            "sport_variance_factor": 1.1, "estimated_market_probability": 0.52
        },
        {
            "player": "m0NESY", "sport": "CS2", "stat": "Maps 1-2 Kills", "line": 35.5,
            "recent_results": [40.0, 39.0, 41.0, 39.0],
            "season_projection": 39.5, "matchup_projection": 40.0, "role_projection": 39.2,
            "pace_volume_projection": 1.07, "market_baseline_uncertainty": 1.1,
            "sport_variance_factor": 1.1, "estimated_market_probability": 0.52
        },
        {
            "player": "sh1ro", "sport": "CS2", "stat": "Maps 1-2 Kills", "line": 32.0,
            "recent_results": [36.0, 35.0, 37.0, 36.0],
            "season_projection": 36.0, "matchup_projection": 36.5, "role_projection": 35.8,
            "pace_volume_projection": 1.06, "market_baseline_uncertainty": 1.1,
            "sport_variance_factor": 1.1, "estimated_market_probability": 0.52
        }
    ])

board_df = get_cs2_board()

candidates = []
for _, row in board_df.iterrows():
    res = calculate_candidate(row)
    if res:
        candidates.append(res)

if candidates:
    df_res = pd.DataFrame(candidates).sort_values(by="edge", ascending=False)
    st.success(f"Successfully processed {len(df_res)} active CS2 player props!")
    
    st.subheader("🎯 Top Player Prop Recommendations")
    for idx, row in df_res.head(6).iterrows():
        st.info(f"**{row['player']}** ({row['sport']} - {row['stat']}) | Line: **{row['line']}** | Action: **{row['side']}** | Edge: **+{row['edge']}%**")
        
    st.subheader("📊 Full Analysis Table")
    st.dataframe(df_res, use_container_width=True)

if st.button("🔄 Clear Cache & Reload"):
    st.cache_data.clear()
    st.rerun()
