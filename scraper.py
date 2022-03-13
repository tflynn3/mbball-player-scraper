from pprint import pprint
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import random


all_data = []
base_url = 'https://www.sports-reference.com'


def get_all_schools():

    # Get schools page
    schools_url = '/cbb/schools/'
    schools = requests.get(base_url + schools_url).text

    # Get schools table rows
    schools_table = BeautifulSoup(schools, 'lxml').find("table", {"id": "schools"})
    schools = schools_table.find_all('tr')

    # Initialize output array
    schools_data = []

    # Loop through table rows, each row is one school
    for school in schools:
        school_data_temp = {}
        # Loop through the row's cells
        for school_data in school.find_all('td'):
            # grab the type of statistic
            data_type = school_data['data-stat']
            # the actual data in cell
            data = school_data.text
            # update school data dict
            school_data_temp[data_type] = data

            # if data is the school name, grab the link
            if data_type == 'school_name':
                school_data_temp['school_link'] = school_data.find('a')['href']

        schools_data.append(school_data_temp)

    return schools_data

# schools_df = pd.DataFrame(schools_data)
def get_roster(school_link, years=[datetime.now().strftime('%Y') if int(datetime.now().strftime('%m'))<10 else int(datetime.now().strftime('%Y'))+1]):

    # Initialize roster data
    roster_data = []

    # Get seasons
    for year in years:
        print(f"Season: {year}")
        season_roster_url = f"{school_link}{year}.html"

        print(season_roster_url)
        # Get Team Roster page
        players_html = requests.get(base_url + season_roster_url).text

        # Parse Roster table rows
        roster_table = BeautifulSoup(players_html, 'lxml').find("table", {"id": "roster"})
        roster = roster_table.find_all('tr')

        for player in roster:
            player_data_temp = {}

            # Not all players have a player link
            # If they do not have  link, then we cannot get game-level data
            # so they will be skipped
            try:
                p = player.find('th')
                player_data_temp[p['data-stat']] = p.text
                player_data_temp['player_link'] = p.find('a')['href']
            except Exception as e:
                print("Could not get player link...skipping player")

            # Check if player has a link
            if 'player_link' in player_data_temp.keys():

                # Get other player cells
                for player_data in player.find_all('td'):
                    data_type = player_data['data-stat']
                    data = player_data.text
                    player_data_temp[data_type] = data

                # Add player data to roster
                roster_data.append(player_data_temp)
    return roster_data

def get_player_gamelog(player_link):       

    # Get gamelog page
    gamelog_url = player_link[:-5] + '/gamelog'
    gamelog_html = requests.get(base_url + gamelog_url).text

    # Parse gamelog table rows
    gamelog_table = BeautifulSoup(gamelog_html, 'lxml').find("table", {"id": "gamelog"})

    # Some players have not played any games
    # Check for the gamelog table before getting rows
    if gamelog_table:
        player_games = gamelog_table.find_all('tr')

        # Initialize gamelog array
        gamelog = []

        # Loop through each gamelog row
        for player_game in player_games:

            # Initialize game data dict
            player_game_data_temp = {}

            # Loop through gamelog row's cells
            for player_game_data in player_game.find_all('td'):
                data_type = player_game_data['data-stat']
                data = player_game_data.text
                player_game_data_temp[data_type] = data

            gamelog.append(player_game_data_temp)
    
    return gamelog


if __name__ == "__main__":

    # Create a schools dataframe
    s = get_all_schools()
    schools_df = pd.DataFrame(s)
    print(schools_df.head())

    # Get a random school
    random_school = schools_df.sample().to_dict('records')[0] 
    # Check if school played this year
    while random_school['year_max'] != '2022':
        random_school = schools_df.sample().to_dict('records')[0]

    print(f'Randomly selected school: {random_school["school_name"]}')

    # Get team roster
    r = get_roster(random_school["school_link"])
    roster_df = pd.DataFrame(r)
    print(roster_df.head())

    # Get a random player
    random_player = roster_df.sample().to_dict('records')[0]
    print(f'Randomly selected player: {random_player["player"]}')
    
    # Get player game log
    p = get_player_gamelog(random_player['player_link'])
    # Player gamelog has some empty rows
    gamelog_df = pd.DataFrame(p).dropna()
    print(gamelog_df.head())