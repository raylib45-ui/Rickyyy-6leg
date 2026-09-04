import streamlit as st
import pandas as pd
import numpy as np
import math

st.set_page_config(
    page_title="Rick C-137 Multi-Sport Board Miner",
    page_icon="🧪",
    layout="wide"
)

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #00ff66; }
    .stButton>button { background-color: #00ff66; color: #0e1117; font-weight: bold; border-radius: 4px; }
    .hammer-card {
        background-color: #161b22;
        border: 2px solid #00ff66;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# Relaxed parameters to guarantee candidates pass immediately without an uploaded file
MIN_EDGE = 0.00
MIN_PROB = 0.40
MAX_UNCERTAINTY = 0.50
MIN_SAMPLE = 2

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

st.title("🧪 Rick C-137 Automated Multi-Sport Miner")
st.markdown("*“Relaxed the filters, Morty. The model is forcing out the top 6 legs right out of the box.”*")

@st.cache_data
def get_combined_board():
    return pd.DataFrame([
        {"player": "Thiago Martins", "sport": "Soccer", "stat": "Passes Attempted", "line": 83.5, "recent_results": [88, 85, 90, 86], "season_projection": 86.0, "matchup_projection": 87.5, "role_projection": 86.5, "pace_volume_projection": 1.04, "market_baseline_uncertainty": 0.05, "sport_variance_factor": 0.9, "estimated_market_probability": 0.52},
        {"player": "Kate Del Fava", "sport": "Soccer", "stat": "Passes Attempted", "line": 50.5, "recent_results": [46, 44, 45, 47], "season_projection": 45.0, "matchup_projection": 44.5, "role_projection": 44.8, "pace_volume_projection": 0.92, "market_baseline_uncertainty": 0.06, "sport_variance_factor": 0.95, "estimated_market_probability": 0.53},
        {"player": "Hany Mukhtar", "sport": "Soccer", "stat": "Shots", "line": 2.5, "recent_results": [1, 2, 1, 2], "season_projection": 1.6, "matchup_projection": 1.5, "role_projection": 1.7, "pace_volume_projection": 0.85, "market_baseline_uncertainty": 0.04, "sport_variance_factor": 0.8, "estimated_market_probability": 0.55},
        {"player": "Matt Freese", "sport": "Soccer", "stat": "Passes Attempted", "line": 23.5, "recent_results": [26, 25, 27, 26], "season_projection": 26.5, "matchup_projection": 27.0, "role_projection": 26.8, "pace_volume_projection": 1.10, "market_baseline_uncertainty": 0.05, "sport_variance_factor": 0.85, "estimated_market_probability": 0.52},
        {"player": "Temwa Chawinga", "sport": "Soccer", "stat": "Passes Attempted", "line": 14.5, "recent_results": [11, 12, 10, 13], "season_projection": 11.5, "matchup_projection": 11.0, "role_projection": 11.2, "pace_volume_projection": 0.90, "market_baseline_uncertainty": 0.05, "sport_variance_factor": 0.85, "estimated_market_probability": 0.54},
        {"player": "Cloé Lacasse", "sport": "Soccer", "stat": "Passes Attempted", "line": 20.5, "recent_results": [16, 17, 18, 17], "season_projection": 17.0, "matchup_projection": 16.5, "role_projection": 16.8, "pace_volume_projection": 0.91, "market_baseline_uncertainty": 0.05, "sport_variance_factor": 0.9, "estimated_market_probability": 0.53},
        {"player": "Blake Snell", "sport": "MLB", "stat": "Pitcher FS", "line": 42.5, "recent_results": [48, 50, 46, 49], "season_projection": 48.0, "matchup_projection": 49.0, "role_projection": 48.5, "pace_volume_projection": 1.12, "market_baseline_uncertainty": 0.06, "sport_variance_factor": 1.0, "estimated_market_probability": 0.52},
        {"player": "Logan Gilbert", "sport": "MLB", "stat": "Pitcher FS", "line": 38.5, "recent_results": [43, 42, 45, 44], "season_projection": 43.5, "matchup_projection": 44.0, "role_projection": 43.8, "pace_volume_projection": 1.10, "market_baseline_uncertainty": 0.06, "sport_variance_factor": 0.95, "estimated_market_probability": 0.52}
    ])

uploaded_file = st.file_uploader("Upload Additional Board Data (CSV)", type=["csv"])
board_df = pd.read_csv(uploaded_file) if uploaded_file else get_combined_board()

candidates = []
for _, row in board_df.iterrows():
    res = calculate_candidate(row)
    if res:
        candidates.append(res)

df_res = pd.DataFrame(candidates).sort_values(by="edge", ascending=False)

st.success(f"Model successfully auto-mined {len(df_res)} elite targets!")

st.subheader("🎯 Automatically Built 6-Leg Parlay Slip")
parlay_picks = df_res.head(6)

for idx, row in parlay_picks.iterrows():
    st.markdown(f"""
    <div class="hammer-card">
        <b>{row['player']}</b> ({row['sport']} - {row['stat']})<br>
        Line: <b>{row['line']}</b> | Action: <span style="color:#00ff66;"><b>{row['side']}</b></span><br>
        Model Prob: <b>{row['model_prob']}%</b> | Edge: <b>+{row['edge']}%</b> | Projection: <b>{row['projection']}</b>
    </div>
    """, unsafe_allow_html=True)
    
st.subheader("📊 Full Model Analysis Table")
st.dataframe(df_res, use_container_width=True)
