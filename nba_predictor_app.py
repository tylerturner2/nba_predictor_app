import streamlit as st
import pandas as pd
import requests
from datetime import date, timedelta
from io import BytesIO

# Constants
API_KEY = st.secrets["sportsdata_api_key"]
BASE_URL = "https://api.sportsdata.io/v3/nba/stats/json"
HEADERS = {"Ocp-Apim-Subscription-Key": API_KEY}

# Utilities to get recent dates
TODAY = date.today()
DATE_RANGE = [(TODAY - timedelta(days=i)).isoformat() for i in range(1, 22)]  # last 3 weeks

# Get today's games
def get_today_games():
    games_url = f"https://api.sportsdata.io/v3/nba/scores/json/GamesByDate/{TODAY.isoformat()}"
    response = requests.get(games_url, headers=HEADERS)
    return response.json() if response.status_code == 200 else []

# Get player stats over last X days
def get_recent_game_stats():
    all_stats = []
    for d in DATE_RANGE:
        url = f"{BASE_URL}/PlayerGameStatsByDate/{d}"
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            day_stats = response.json()
            for entry in day_stats:
                entry["GameDate"] = d  # safely store the date field
            all_stats.extend(day_stats)
    df = pd.DataFrame(all_stats)
    df.rename(columns={"GameDate": "Date"}, inplace=True)
    return df

# Predictive formula using SL5, H2H5, LS with weights and minutes factored in

def run_predictive_formula(stats_df, selected_team):
    predictions = []

    # Identify players in today's game
    game_players = stats_df[(stats_df['Team'] == selected_team) | (stats_df['Opponent'] == selected_team)]['Name'].unique()

    for player in game_players:
        pstats = stats_df[stats_df['Name'] == player].sort_values(by='Date', ascending=False).head(10)
        if pstats.empty:
            continue

        team = pstats.iloc[0]['Team']

        # SL5: Last 5 games
        sl5 = pstats.head(5)
        sl5_min = sl5['Minutes'].mean()
        sl5_pts = (sl5['Points'] * sl5['Minutes']).sum() / sl5['Minutes'].sum() if sl5['Minutes'].sum() else 0
        sl5_reb = (sl5['Rebounds'] * sl5['Minutes']).sum() / sl5['Minutes'].sum() if sl5['Minutes'].sum() else 0
        sl5_ast = (sl5['Assists'] * sl5['Minutes']).sum() / sl5['Minutes'].sum() if sl5['Minutes'].sum() else 0

        # H2H5: Head-to-head vs selected team
        h2h = pstats[pstats['Opponent'] == selected_team].head(5)
        h2h_pts = h2h['Points'].mean() if not h2h.empty else 0
        h2h_reb = h2h['Rebounds'].mean() if not h2h.empty else 0
        h2h_ast = h2h['Assists'].mean() if not h2h.empty else 0

        # LS: Location-specific
        loc_type = 'Home' if team == selected_team else 'Away'
        loc_games = pstats[pstats['HomeOrAway'] == loc_type]
        ls_pts = loc_games['Points'].mean() if not loc_games.empty else 0
        ls_reb = loc_games['Rebounds'].mean() if not loc_games.empty else 0
        ls_ast = loc_games['Assists'].mean() if not loc_games.empty else 0

        # Weighted formula
        pred_pts = round(0.60 * sl5_pts + 0.35 * h2h_pts + 0.15 * ls_pts, 1)
        pred_reb = round(0.60 * sl5_reb + 0.35 * h2h_reb + 0.15 * ls_reb, 1)
        pred_ast = round(0.60 * sl5_ast + 0.35 * h2h_ast + 0.15 * ls_ast, 1)

        predictions.append({
            "Name": player,
            "Team": team,
            "Predicted PTS": pred_pts,
            "Predicted REB": pred_reb,
            "Predicted AST": pred_ast,
            "Avg MIN (Last 5)": round(sl5_min, 1)
        })
    return pd.DataFrame(predictions)

def create_excel_download(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Predictions')
    output.seek(0)
    return output

# Streamlit App
st.title("NBA Predictive Formula Tool")
st.subheader("Today's Game Predictions")

with st.spinner('Loading today\'s games...'):
    games = get_today_games()

# Display only today's games in dropdown with cleaner keys
game_labels = [f"{g['AwayTeam']} @ {g['HomeTeam']}" for g in games]
game_lookup = {f"{g['AwayTeam']} @ {g['HomeTeam']}": g['HomeTeam'] for g in games}
selected_game = st.selectbox("Select a game:", game_labels)
selected_team = game_lookup[selected_game]

with st.spinner('Fetching and analyzing recent player stats...'):
    stats_df = get_recent_game_stats()

# Filter to relevant players in today’s game
players_today = stats_df[(stats_df['Team'] == selected_team) | (stats_df['Opponent'] == selected_team)]

if not players_today.empty:
    df_predictions = run_predictive_formula(stats_df, selected_team)
    st.dataframe(df_predictions)

    excel_data = create_excel_download(df_predictions)
    st.download_button(
        label="📥 Download Predictions as Excel",
        data=excel_data,
        file_name="nba_predictions.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.warning("No player stats available for the selected matchup.")
