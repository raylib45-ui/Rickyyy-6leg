import streamlit as st
import pandas as pd
import numpy as np
import math

# --- Page Config ---
st.set_page_config(
    page_title="Rick C-137 PrizePicks Board Miner",
    page_icon="🧪",
    layout="wide"
)

# --- CSS Styling (Rick Portal Theme) ---
st.markdown("""
    <style>
    .stApp {
        background-color: #0e1117;
        color: #00ff66;
    }
    .stButton>button {
        background-color: #00ff66;
        color: #0e1117;
        font-weight: bold;
        border-radius: 4px;
    }
    .stButton>button:hover {
        background-color: #00cc52;
        color: #ffffff;
    }
    .hammer-card {
        background-color: #161b22;
        border: 2px solid #00ff66;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# --- Constants & Thresholds ---
MIN_EDGE = 0.075
MIN_PROB = 0.70
MAX_UNCERTAINTY = 0.12
MIN_SAMPLE = 5

# --- Core Model Functions ---
def clamp(x, low=0.01, high=0.99):
    return max(low, min(high, x))

def probability_from_z(projected, line, uncertainty):
    if uncertainty <= 0:
        uncertainty = 1
    z = (projected - line) / uncertainty
    return clamp(0.5 * (1 + math.erf(z / math.sqrt(2))))

def calculate_candidate(row):
    try:
        recent = np.array(row["recent_results"], dtype=float)
        if len(recent) < MIN_SAMPLE:
            return None

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
        raw_less = 1 - raw_more

        shrink = min(1.0, len(recent) / 20) * row.get("data_quality", 1.0)
        more_prob = clamp(0.50 + (raw_more - 0.50) * shrink)
        less_prob = 1 - more_prob

        penalty = row.get("availability_penalty", 0.0) + row.get("matchup_uncertainty", 0.0)
        more_prob = clamp(more_prob - penalty)
        less_prob = clamp(less_prob - penalty)

        if more_prob >= less_prob:
            side = "MORE 🔨"
            model_prob = more_prob
            margin = projection - row["line"]
        else:
            side = "LESS 🔨"
            model_prob = less_prob
            margin = row["line"] - projection

        edge = model_prob - row["estimated_market_probability"]

        # Rigorous Veto Checks
        if side == "LESS 🔨" and row["line"] <= recent_median:
            return None
        if side == "MORE 🔨" and row["line"] >= recent_median:
            return None
        if uncertainty > MAX_UNCERTAINTY or model_prob < MIN_PROB or edge < MIN_EDGE:
            return None

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

# --- UI Layout ---
st.title("🧪 Rick C-137 PrizePicks Board Miner")
st.markdown("*“Syntax errors fixed, Morty. Now let's mine the board and hit that 6-leg parlay.”*")

# Default Board Data (Ready for custom CSV uploads)
@st.cache_data
def get_default_board():
    return pd.DataFrame([
        {
            "player": "Shane Drohan", "sport": "MLB", "stat": "Pitcher Strikeouts", "line": 3.5,
            "recent_results": [5, 4, 6, 5, 4, 5],
            "season_projection": 4.8, "matchup_projection": 5.0, "role_projection": 4.5,
            "pace_volume_projection": 1.10, "market_baseline_uncertainty": 0.06,
            "sport_variance_factor": 0.9, "estimated_market_probability": 0.52
        },
        {
            "player": "Chris Sale", "sport": "MLB", "stat": "Pitcher Strikeouts", "line": 4.5,
            "recent_results": [7, 6, 8, 7, 6, 7],
            "season_projection": 6.5, "matchup_projection": 6.8, "role_projection": 6.2,
            "pace_volume_projection": 1.15, "market_baseline_uncertainty": 0.05,
            "sport_variance_factor": 0.85, "estimated_market_probability": 0.51
        },
        {
            "player": "Blake Snell", "sport": "MLB", "stat": "Pitcher Strikeouts", "line": 8.0,
            "recent_results": [10, 11, 9, 10, 11, 10],
            "season_projection": 10.5, "matchup_projection": 10.2, "role_projection": 10.3,
            "pace_volume_projection": 1.20, "market_baseline_uncertainty": 0.04,
            "sport_variance_factor": 0.8, "estimated_market_probability": 0.51
        },
        {
            "player": "Logan Gilbert", "sport": "MLB", "stat": "Pitcher Strikeouts", "line": 6.5,
            "recent_results": [8, 9, 8, 9, 8, 9],
            "season_projection": 8.6, "matchup_projection": 8.4, "role_projection": 8.5,
            "pace_volume_projection": 1.12, "market_baseline_uncertainty": 0.05,
            "sport_variance_factor": 0.85, "estimated_market_probability": 0.51
        },
        {
            "player": "Nolan McLean", "sport": "MLB", "stat": "Pitcher Strikeouts", "line": 6.0,
            "recent_results": [8, 9, 7, 8, 9, 8],
            "season_projection": 8.2, "matchup_projection": 8.0, "role_projection": 8.1,
            "pace_volume_projection": 1.12, "market_baseline_uncertainty": 0.05,
            "sport_variance_factor": 0.85, "estimated_market_probability": 0.51
        },
        {
            "player": "Ranger Suarez", "sport": "MLB", "stat": "Pitcher Strikeouts", "line": 5.5,
            "recent_results": [7, 8, 6, 7, 8, 7],
            "season_projection": 7.2, "matchup_projection": 7.0, "role_projection": 7.1,
            "pace_volume_projection": 1.08, "market_baseline_uncertainty": 0.06,
            "sport_variance_factor": 0.9, "estimated_market_probability": 0.52
        }
    ])

uploaded_file = st.file_uploader("Upload PrizePicks Board Data (CSV)", type=["csv"])
board_df = pd.read_csv(uploaded_file) if uploaded_file else get_default_board()

if st.button("🚀 Run Rick's Brutal Filter"):
    candidates = []
    for _, row in board_df.iterrows():
        res = calculate_candidate(row)
        if res:
            candidates.append(res)
            
    if not candidates:
        st.error("🧪 Brutal filter executed: 0 plays cleared the A+ threshold. Walking away.")
    else:
        df_res = pd.DataFrame(candidates).sort_values(by="edge", ascending=False)
        st.success(f"Found {len(df_res)} elite high-confidence targets!")
        
        st.subheader("📊 Analyzed Board Targets")
        st.dataframe(df_res, use_container_width=True)
        
        st.subheader("🎯 Recommended Top 6-Leg Parlay Targets")
        parlay_picks = df_res.head(6)
        
        for idx, row in parlay_picks.iterrows():
            st.markdown(f"""
            <div class="hammer-card">
                <b>{row['player']}</b> ({row['sport']} - {row['stat']})<br>
                Line: <b>{row['line']}</b> | Action: <span style="color:#00ff66;"><b>{row['side']}</b></span><br>
                Model Prob: <b>{row['model_prob']}%</b> | Edge: <b>+{row['edge']}%</b> | Projection: <b>{row['projection']}</b>
            </div>
            """, unsafe_allow_html=True)
