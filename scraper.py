import requests
from bs4 import BeautifulSoup
from datetime import datetime
import logging
import time


# setup logging
logging.basicConfig(filename='ncaa.log', level=logging.INFO, format='%(asctime)s:%(levelname)s:%(message)s')

# log if used in a different file
logging.info("Importing scraper.py")

def make_request_with_retry_after(url):
    """
    This function makes a request to the specified url and sleeps for the
    amount of time specified in the 'Retry-After' header
    parameters:
     - url (str): URL to make request to
    returns: Response object
    """
    # sleep 2 second in attempt to avoid 429 error
    time.sleep(1)

    r = requests.get(url)
    while r.status_code == 429:
        # log if the retry-after header is not present
        if 'Retry-After' not in r.headers.keys():
            logging.info("No Retry-After header present")
        else:
            # log the retry wait time in a human readable format
            # convert to hours, minutes, seconds if > 60 seconds or > 60 minutes
            if int(r.headers['Retry-After']) > 60:
                if int(r.headers['Retry-After']) > 3600:
                    # log hours minutes and seconds
                    logging.info(f"Waiting {int(r.headers['Retry-After'])/3600} hours {int(r.headers['Retry-After'])%60} minutes {int(r.headers['Retry-After'])%60} seconds")
                else:
                    logging.info(f"Waiting {int(r.headers['Retry-After'])/60} minutes {int(r.headers['Retry-After'])%60} seconds")
            else:
                logging.info(f"Waiting {r.headers['Retry-After']} seconds")

        # parse the headers and sleep for the time specified in the 'Retry-After' header
        time.sleep(int(r.headers['Retry-After']) + 10)
        r = requests.get(url)
        # log if request is not successful but not 429
        if r.status_code != 200 and r.status_code != 429:
            logging.error(f"Request not successful. Status code: {r.status_code}")
            # raise an exception
            raise Exception(f"Request not successful. Status code: {r.status_code}")
    return r.text

base_url = 'https://www.sports-reference.com'
def get_all_schools():
    """
    This function collects all schools from the Men's NCAA Schools Table
    at https://www.sports-reference.com/cbb/schools
    returns: List of Dictionaries of table data
    """

    # Get schools page
    schools_url = '/cbb/schools/'
    schools = make_request_with_retry_after(base_url + schools_url)

    # Get schools table rows
    schools_table = BeautifulSoup(schools, 'lxml').find("table", {"id": "NCAAM_schools"})
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
    """
    This function scraps the roster table for a/the particular season(s) specified
    parameters:
     - schools_link (str): URL of the school. Can be scraped using the get_all_schools function
     - years (list): List of the years of which to pull rosters
     returns: List of Dictionaries with the roster table data
    """
    # Initialize roster data
    roster_data = []

    # Get seasons
    for year in years:
        season_roster_url = f"{school_link}{year}.html"

        # Get Team Roster page
        players_html = make_request_with_retry_after(base_url + season_roster_url)

        # Parse Roster table rows
        roster_table = BeautifulSoup(players_html, 'lxml').find("table", {"id": "roster"})
        # log
        logging.info(f"Getting roster for {year}")
        # check if team has roster for this year
        if roster_table:
            roster = roster_table.find_all('tr')
            # debug log number of rows
            logging.debug(f"Number of rows: {len(roster)}")

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
                    #print("Could not get player link...skipping player")
                    logging.info(f"Could not get player link...skipping player: {e}")

                # Check if player has a link
                if 'player_link' in player_data_temp.keys():

                    # Get other player cells
                    for player_data in player.find_all('td'):
                        data_type = player_data['data-stat']
                        data = player_data.text
                        player_data_temp[data_type] = data

                    # Add player data to roster
                    roster_data.append(player_data_temp)
        else:
            logging.error(f"Could not get roster at {base_url + season_roster_url}")
    return roster_data

def get_basic_gamelog(school_link, years=[datetime.now().strftime('%Y') if int(datetime.now().strftime('%m'))<10 else int(datetime.now().strftime('%Y'))+1]):
    """
    This function will get the basic gamelog table from table id="sgl-basic"
    parameters:
     - team_link (str): URL for the team
     - season (str): Year of the season
    """

    for year in years:
        basic_gamelog_url = f"{school_link}{year}-gamelogs.html"

        # Get Team Roster page
        basic_gamelog_html = make_request_with_retry_after(base_url + basic_gamelog_url)

        # Parse Roster table rows
        basic_gamelog_table = BeautifulSoup(basic_gamelog_html, 'lxml').find("table", {"id": "sgl-basic"})
        # log
        logging.info(f"Getting basic gamelog for {year}")

        basic_gamelogs = []
        # check if team has roster for this year
        if basic_gamelog_table:
            # iterate over tbody from above example HTML basic_gamelog_table
            # get the th data-stat and text value and store it in a dictionary
            # the dictionary is then appended to the basic_gamelogs list
            for row in basic_gamelog_table.find('tbody').find_all('tr'):
                basic_gamelog_dict = {}
                # check if tr id is like sgl-basic.20230128 where the end is the data
                if row.has_attr('id') and row['id'].startswith('sgl-basic.'):
                    # loop through th and td's 
                    for cell in row.find_all(['th', 'td']):
                        # check if the cell has a data-stat attribute
                        if cell.has_attr('data-stat'):
                            data_type = cell['data-stat']
                            data = cell.text
                            basic_gamelog_dict[data_type] = data
                    # check if game_result key has a value
                    if basic_gamelog_dict['game_result']:
                        # delete key 'x' from dictionary
                        del basic_gamelog_dict['x']
                        # append the dictionary to the list
                        basic_gamelogs.append(basic_gamelog_dict)
        else:
            logging.info(f"Could not get basic gamelog at {base_url + basic_gamelog_url}")

    return basic_gamelogs

def get_player_gamelog(player_link):       
    """
    This function will scrap the gamelog for a specific player
    parameters:
     - plyer_link (str): URL for the player
    returns: List of Dictionaries of the player gamelog (all games the player has played)
    """
    # Get gamelog page
    # Note: using full URL, so need to strip ".html"
    gamelog_url = player_link.replace('.html', '') + '/gamelog'
    gamelog_html = make_request_with_retry_after(base_url + gamelog_url)

    # Parse gamelog table rows
    gamelog_table = BeautifulSoup(gamelog_html, 'lxml').find("table", {"id": "gamelog"})

    # Initialize gamelog array
    gamelog = []
    # log
    logging.info(f"Getting gamelog for {player_link}")
    # Some players have not played any games
    # Check for the gamelog table before getting rows
    if gamelog_table:
        player_games = gamelog_table.find_all('tr')
        # debug log number of rows
        logging.debug(f"Number of games in gamelog: {len(player_games)}")
        # Loop through each gamelog row
        for player_game in player_games:

            # Initialize game data dict
            player_game_data_temp = {}

            # Loop through gamelog row's cells
            for player_game_data in player_game.find_all('td'):
                data_type = player_game_data['data-stat']
                data = player_game_data.text
                player_game_data_temp[data_type] = data
            # game_result data type is if the game was won ("W") or 
            # lost ("L"). If there is no game result, then the row
            # contains a summary row for that season. We want to 
            # ignore that row. The row will be None, so we can use
            # a simple if statement to check if this is a summary row
            if 'game_result' in player_game_data_temp.keys():
                if player_game_data_temp['game_result']: # i.e. this shit ain't None
                    gamelog.append(player_game_data_temp)
    else:
        logging.info(f"Could not get gamelog at {base_url + gamelog_url}")
    
    return gamelog


if __name__ == "__main__":
    import pandas as pd

    # Create a schools dataframe
    s = get_all_schools()
    schools_df = pd.DataFrame(s).dropna()
    print(schools_df.head())

    # Get a random school
    random_school = schools_df.sample().to_dict('records')[0]
    # while the school did not play in the current season i.e. year_max >= current_year
    while not int(random_school['year_max']) >= int(datetime.now().strftime('%Y')):
        random_school = schools_df.sample().to_dict('records')[0]


    print(f'Randomly selected school: {random_school["school_name"]}')

    # Get basic gamelog
    b = get_basic_gamelog(random_school['school_link'])
    basic_gamelog_df = pd.DataFrame(b)
    # export to csv
    basic_gamelog_df.to_csv('basic_gamelog.csv', index=False)

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