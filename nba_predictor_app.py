import streamlit as st
import pandas as pd
import requests
from datetime import date, timedelta
from io import BytesIO

# Constants
API_KEY = st.secrets["sportsdata_api_key"]
BASE_URL = "https://api.sportsdata.io/v3/nba/stats/json"
HEADERS = {"Ocp-Apim-Subscription-Key": API_KEY}
TEAM_LOGOS = {
    "ATL": "https://loodibee.com/wp-content/uploads/nba-atlanta-hawks-logo.png",
    "BOS": "https://loodibee.com/wp-content/uploads/nba-boston-celtics-logo.png",
    "BRK": "https://loodibee.com/wp-content/uploads/nba-brooklyn-nets-logo.png",
    "CHA": "https://loodibee.com/wp-content/uploads/nba-charlotte-hornets-logo.png",
    "CHI": "https://loodibee.com/wp-content/uploads/nba-chicago-bulls-logo.png",
    "CLE": "https://loodibee.com/wp-content/uploads/nba-cleveland-cavaliers-logo.png",
    "DAL": "https://loodibee.com/wp-content/uploads/nba-dallas-mavericks-logo.png",
    "DEN": "https://loodibee.com/wp-content/uploads/nba-denver-nuggets-logo.png",
    "DET": "https://loodibee.com/wp-content/uploads/nba-detroit-pistons-logo.png",
    "GSW": "https://loodibee.com/wp-content/uploads/nba-golden-state-warriors-logo.png",
    "HOU": "https://loodibee.com/wp-content/uploads/nba-houston-rockets-logo.png",
    "IND": "https://loodibee.com/wp-content/uploads/nba-indiana-pacers-logo.png",
    "LAC": "https://loodibee.com/wp-content/uploads/nba-la-clippers-logo.png",
    "LAL": "https://loodibee.com/wp-content/uploads/nba-la-lakers-logo.png",
    "MEM": "https://loodibee.com/wp-content/uploads/nba-memphis-grizzlies-logo.png",
    "MIA": "https://loodibee.com/wp-content/uploads/nba-miami-heat-logo.png",
    "MIL": "https://loodibee.com/wp-content/uploads/nba-milwaukee-bucks-logo.png",
    "MIN": "https://loodibee.com/wp-content/uploads/nba-minnesota-timberwolves-logo.png",
    "NOP": "https://loodibee.com/wp-content/uploads/nba-new-orleans-pelicans-logo.png",
    "NYK": "https://loodibee.com/wp-content/uploads/nba-new-york-knicks-logo.png",
    "OKC": "https://loodibee.com/wp-content/uploads/nba-oklahoma-city-thunder-logo.png",
    "ORL": "https://loodibee.com/wp-content/uploads/nba-orlando-magic-logo.png",
    "PHI": "https://loodibee.com/wp-content/uploads/nba-philadelphia-76ers-logo.png",
    "PHX": "https://loodibee.com/wp-content/uploads/nba-phoenix-suns-logo.png",
    "POR": "https://loodibee.com/wp-content/uploads/nba-portland-trail-blazers-logo.png",
    "SAC": "https://loodibee.com/wp-content/uploads/nba-sacramento-kings-logo.png",
    "SAS": "https://loodibee.com/wp-content/uploads/nba-san-antonio-spurs-logo.png",
    "TOR": "https://loodibee.com/wp-content/uploads/nba-toronto-raptors-logo.png",
    "UTA": "https://loodibee.com/wp-content/uploads/nba-utah-jazz-logo.png",
    "WAS": "https://loodibee.com/wp-content/uploads/nba-washington-wizards-logo.png"
}

TODAY = date.today()
DATE_RANGE = [(TODAY - timedelta(days=i)).isoformat() for i in range(1, 22)]

def get_today_games():
    games_url = f"https://api.sportsdata.io/v3/nba/scores/json/GamesByDate/{TODAY.isoformat()}"
    response = requests.get(games_url, headers=HEADERS)
    return response.json() if response.status_code == 200 else []

def get_recent_game_stats():
    all_stats = []
    for d in DATE_RANGE:
        url = f"{BASE_URL}/PlayerGameStatsByDate/{d}"
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            day_stats = response.json()
            for entry in day_stats:
                entry["GameDate"] = d
            all_stats.extend(day_stats)
    df = pd.DataFrame(all_stats)
    df.rename(columns={"GameDate": "Date"}, inplace=True)
    return df

def run_predictive_formula(stats_df, selected_teams):
    predictions = []
    team1, team2 = selected_teams
    filtered_df = stats_df[(stats_df['Team'].isin([team1, team2])) & (stats_df['Opponent'].isin([team1, team2]))]
    game_players = filtered_df['Name'].unique()

    for player in game_players:
        pstats = filtered_df[filtered_df['Name'] == player].sort_values(by='Date', ascending=False).head(10)
        if pstats.empty:
            continue

        team = pstats.iloc[0]['Team']
        sl5 = pstats.head(5)
        sl5_min = sl5['Minutes'].mean()
        sl5_pts = (sl5['Points'] * sl5['Minutes']).sum() / sl5['Minutes'].sum() if sl5['Minutes'].sum() else 0
        sl5_reb = (sl5['Rebounds'] * sl5['Minutes']).sum() / sl5['Minutes'].sum() if sl5['Minutes'].sum() else 0
        sl5_ast = (sl5['Assists'] * sl5['Minutes']).sum() / sl5['Minutes'].sum() if sl5['Minutes'].sum() else 0

        opponent_team = team2 if team == team1 else team1
        h2h = pstats[pstats['Opponent'] == opponent_team].head(5)
        h2h_pts = h2h['Points'].mean() if not h2h.empty else 0
        h2h_reb = h2h['Rebounds'].mean() if not h2h.empty else 0
        h2h_ast = h2h['Assists'].mean() if not h2h.empty else 0

        loc_type = 'Home' if team == team1 else 'Away'
        loc_games = pstats[pstats['HomeOrAway'] == loc_type]
        ls_pts = loc_games['Points'].mean() if not loc_games.empty else 0
        ls_reb = loc_games['Rebounds'].mean() if not loc_games.empty else 0
        ls_ast = loc_games['Assists'].mean() if not loc_games.empty else 0

        pred_pts = round(0.60 * sl5_pts + 0.35 * h2h_pts + 0.15 * ls_pts, 1)
        pred_reb = round(0.60 * sl5_reb + 0.35 * h2h_reb + 0.15 * ls_reb, 1)
        pred_ast = round(0.60 * sl5_ast + 0.35 * h2h_ast + 0.15 * ls_ast, 1)

        predictions.append({
            "Player": player,
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
st.set_page_config(page_title="NBA Prop Predictor", layout="wide")
st.title("🏀 NBA Predictive Formula Tool")

with st.spinner("📅 Loading today's games..."):
    games = get_today_games()

game_labels = [f"{g['AwayTeam']} @ {g['HomeTeam']} ({g['DateTime'][:10]})" for g in games]
game_lookup = {label: (g['AwayTeam'], g['HomeTeam']) for label, g in zip(game_labels, games)}
selected_game = st.selectbox("Select a matchup:", game_labels)
selected_teams = game_lookup[selected_game]

with st.spinner("📊 Fetching and calculating predictions..."):
    stats_df = get_recent_game_stats()

if not stats_df.empty:
    df_predictions = run_predictive_formula(stats_df, selected_teams)

    if 'Team' in df_predictions.columns and not df_predictions.empty:
        team1, team2 = selected_teams
        df_team1 = df_predictions[df_predictions['Team'] == team1].reset_index(drop=True)
        df_team2 = df_predictions[df_predictions['Team'] == team2].reset_index(drop=True)

        col1, col2 = st.columns(2)

        with col1:
            logo1 = TEAM_LOGOS.get(team1)
            if logo1:
                st.image(logo1, width=100)
            st.markdown(f"### {team1} Player Predictions")
            st.dataframe(df_team1)

        with col2:
            logo2 = TEAM_LOGOS.get(team2)
            if logo2:
                st.image(logo2, width=100)
            st.markdown(f"### {team2} Player Predictions")
            st.dataframe(df_team2)

        excel_data = create_excel_download(df_predictions)
        st.download_button(
            label="📥 Download Excel Predictions",
            data=excel_data,
            file_name="nba_predictions.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("No predictions available for this matchup.")
else:
    st.warning("No stats found for this matchup.")