import streamlit as st
import pandas as pd
import requests
from datetime import date
from io import BytesIO

# Constants
API_KEY = st.secrets["sportsdata_api_key"]
BASE_URL = "https://api.sportsdata.io/v3/nba/projections/json"
HEADERS = {"Ocp-Apim-Subscription-Key": API_KEY}

def get_today_games():
    today = date.today().isoformat()
    games_url = f"https://api.sportsdata.io/v3/nba/scores/json/GamesByDate/{today}"
    response = requests.get(games_url, headers=HEADERS)
    return response.json() if response.status_code == 200 else []

def get_player_projections():
    today = date.today().isoformat()
    url = f"{BASE_URL}/PlayerGameProjectionStatsByDate/{today}"
    response = requests.get(url, headers=HEADERS)
    return response.json() if response.status_code == 200 else []

def run_predictive_formula(player_projections):
    predictions = []
    for player in player_projections:
        pred_pts = round(player.get('Points', 0), 1)
        pred_reb = round(player.get('Rebounds', 0), 1)
        pred_ast = round(player.get('Assists', 0), 1)
        predictions.append({
            "Name": player['Name'],
            "Team": player['Team'],
            "Opponent": player['Opponent'],
            "Predicted PTS": pred_pts,
            "Predicted REB": pred_reb,
            "Predicted AST": pred_ast
        })
    return pd.DataFrame(predictions)

def create_excel_download(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Predictions')
        writer.save()
    output.seek(0)
    return output

# Streamlit App
st.title("NBA Predictive Formula Tool")
st.subheader("Today's Game Predictions")

with st.spinner('Loading today\'s games...'):
    games = get_today_games()

game_options = {f"{g['AwayTeam']} @ {g['HomeTeam']} ({g['DateTime'][:10]})": g['HomeTeam'] for g in games}
selected_game = st.selectbox("Select a game:", list(game_options.keys()))
selected_team = game_options[selected_game]

with st.spinner('Fetching player projections...'):
    player_projections = get_player_projections()

# Filter projections to players in selected game
filtered_players = [p for p in player_projections if p['Team'] == selected_team or p['Opponent'] == selected_team]

if filtered_players:
    df_predictions = run_predictive_formula(filtered_players)
    st.dataframe(df_predictions)

    excel_data = create_excel_download(df_predictions)
    st.download_button(
        label="📥 Download Predictions as Excel",
        data=excel_data,
        file_name="nba_predictions.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.warning("No player projections available for this game.")
