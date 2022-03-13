import requests
from bs4 import BeautifulSoup
import pandas as pd

n=0
all_data = []

base_url = 'https://www.sports-reference.com'
schools_url = '/cbb/schools/'

schools = requests.get(base_url + schools_url).text
schools_table = BeautifulSoup(schools, 'lxml').find("table", {"id": "schools"})

schools = schools_table.find_all('tr')

schools_data = []
for school in schools:
    n = n + 1
    school_data_temp = {}
    for school_data in school.find_all('td'):
        data_type = school_data['data-stat']
        data = school_data.text
        school_data_temp[data_type] = data
        if data_type == 'school_name':
            school_data_temp['school_link'] = school_data.find('a')['href']

    # schools_data.append(school_data_temp)

# schools_df = pd.DataFrame(schools_data)
    players_data = []
    # Get roster for team
    try:
        print(f"Getting roster for team: {school_data_temp['school_name']}")
        # Get seasons back to 2010
        for year in range(2010, 2022):
            print(f"Season: {year}")
            test_url = f"{school_data_temp['school_link']}{year}.html"

            players_html = requests.get(base_url + test_url).text
            roster_table = BeautifulSoup(players_html, 'lxml').find("table", {"id": "roster"})

            players = roster_table.find_all('tr')

            # players_data = []
            for player in players:
                try:
                    player_data_temp = {}
                    try:
                        p = player.find('th')
                        player_data_temp[p['data-stat']] = p.text
                        player_data_temp['player_link'] = p.find('a')['href']
                    except Exception as e:
                        pass
                    if 'player_link' in player_data_temp.keys():
                        for player_data in player.find_all('td'):
                            data_type = player_data['data-stat']
                            data = player_data.text
                            player_data_temp[data_type] = data
                            player_data_temp.update(school_data_temp)
                        # players_data.append(player_data_temp)

                    
                        #print(f"Getting data for player {player_data_temp['player']}")
                        gamelog_url = player_data_temp['player_link'][:-5] + '/gamelog'
                        player_games_html = requests.get(base_url + gamelog_url).text
                        roster_table = BeautifulSoup(player_games_html, 'lxml').find("table", {"id": "gamelog"})

                        player_games = roster_table.find_all('tr')

                        player_games_data = []
                        for player_game in player_games:
                            player_game_data_temp = {}

                            for player_game_data in player_game.find_all('td'):
                                data_type = player_game_data['data-stat']
                                data = player_game_data.text
                                player_game_data_temp[data_type] = data
                                player_game_data_temp.update(player_data_temp)
                            player_games_data.append(player_game_data_temp)
                            all_data.append(player_game_data_temp)
                except Exception as e:
                    print("Error in player loop")
                    print(e)

    except Exception as e:
        print("Error in school loop")
        print(e)

        
    # if players_data:
    #     players_df = pd.DataFrame(players_data).dropna()
    #     print(players_df)


df = pd.DataFrame(all_data).dropna()
df.to_csv('player_data.csv')