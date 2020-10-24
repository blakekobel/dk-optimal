from bs4 import BeautifulSoup
import requests
import pandas as pd
from itertools import permutations
from pulp import *
from io import StringIO
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import re


def scrape_fantasypros():
    position_list = ['qb', 'rb', 'wr', 'te', 'dst']
    players = []
    for position in position_list:
        url = 'https://www.fantasypros.com/nfl/projections/{0}.php?scoring=PPR'.format(
            position)
        response = requests.get(url)
        soup_sref = BeautifulSoup(response.content, 'lxml')
        sref_table = soup_sref.find(
            "table", {"id": "data"}).find('tbody').findAll('tr')
        for x in sref_table:
            name = x.find('a').text
            if name == 'Mitch Trubisky':
                name = name.replace('Mitch', 'Mitchell')
            if name == 'Chris Herndon IV':
                name = name.replace('Herndon IV', 'Herndon')
            if name in ['Pittsburgh Steelers', 'Tampa Bay Buccaneers', 'Indianapolis Colts', 'San Francisco 49ers', 'Cleveland Browns', 'Los Angeles Chargers', 'New England Patriots', 'Los Angeles Rams', 'New York Giants', 'Arizona Cardinals', 'Jacksonville Jaguars', 'Washington Football Team', 'Philadelphia Eagles', 'Carolina Panthers', 'Minnesota Vikings', 'Chicago Bears', 'Buffalo Bills', 'Atlanta Falcons', 'Dallas Cowboys', 'Tennessee Titans', 'Kansas City Chiefs', 'Cincinnati Bengals', 'Detroit Lions', 'New Orleans Saints', 'Seattle Seahawks', 'Miami Dolphins', 'Baltimore Ravens', 'New York Jets', 'Denver Broncos', 'Houston Texans', 'Las Vegas Raiders', 'Green Bay Packers']:
                name = name.split(' ')[-1] + " "
            proj = x.findAll('td')[-1].text
            players.append([name, proj])

    fantasypros_proj = pd.DataFrame(
        players, columns=['Name', 'Projected Points'])
    fantasypros_proj['Name'] = fantasypros_proj['Name'].str.replace('.', '')
    fantasypros_proj['Name'] = fantasypros_proj['Name'].str.replace(' II', '')
    fantasypros_proj['Name'] = fantasypros_proj['Name'].str.replace(' III', '')
    return fantasypros_proj


def scrape_dk(group_id):
    dk_url = "https://www.draftkings.com/lineup/getavailableplayerscsv?contestTypeId=21&draftGroupId={0}".format(
        group_id)
    site = requests.get(dk_url)
    soup_sref = BeautifulSoup(site.content, 'lxml').find('p').text
    df = pd.read_csv(StringIO(soup_sref))
    df['Name'] = df['Name'].str.replace('.', '')
    return df


def make_master_df(projections, week, dk_scrape):
    dk = dk_scrape
    proj = projections

    proj = proj[~proj['Projected Points'].isin(
        ['-', '_', ' ', '+', '='])]
    proj['Projected Points'] = proj['Projected Points'].astype(float)
    dk = dk.drop(['Name + ID', 'ID', 'Game Info'], axis=1)

    master_df = dk.merge(proj, left_on='Name', right_on='Name')
    master_df = master_df.drop(['Roster Position'], axis=1)
    master_df = master_df.rename(
        columns={"Position": "Pos"})

    return master_df


def setup(master_df, pos_num_array, cap):
    availables = master_df[['Pos', 'Name', 'Salary', 'Projected Points']]
    availables = availables[["Pos", "Name", "Salary", "Projected Points"]].groupby(
        ["Pos", "Name", "Salary", "Projected Points"]).agg("count")
    availables = availables.reset_index()
    salaries = {}
    points = {}
    for pos in availables.Pos.unique():
        available_pos = availables[availables.Pos == pos]
        salary = list(available_pos[["Name", "Salary"]].set_index(
            "Name").to_dict().values())[0]
        point = list(available_pos[["Name", "Projected Points"]].set_index(
            "Name").to_dict().values())[0]
        salaries[pos] = salary
        points[pos] = point

    pos_num_available = {  # LOOP THROUGH HERE
        "QB": 1,
        "RB": pos_num_array[0],
        "WR": pos_num_array[1],
        "TE": pos_num_array[2],
        "FLEX": 1,
        "DST": 1,
    }

    pos_flex = {
        "QB": 0,
        "RB": 1,
        "WR": 1,
        "TE": 1,
        "FLEX": 0,
        "DST": 0
    }
    pos_flex_available = 5
    SALARY_CAP = cap
    _vars = {k: LpVariable.dict(k, v, cat="Binary") for k, v in points.items()}

    prob = LpProblem("Fantasy", LpMaximize)
    rewards = []
    costs = []
    position_constraints = []

    # Setting up the reward
    for k, v in _vars.items():
        costs += lpSum([salaries[k][i] * _vars[k][i] for i in v])
        rewards += lpSum([points[k][i] * _vars[k][i] for i in v])
        prob += lpSum([_vars[k][i] for i in v]) <= pos_num_available[k]
        prob += lpSum([pos_flex[k] * _vars[k][i]
                       for i in v]) <= pos_flex_available

    prob += lpSum(rewards)
    prob += lpSum(costs) <= SALARY_CAP

    prob.solve()

    return prob


def summary(prob):
    string = ''
    div = '---------------------------------------\n'
    string += "Play:</strong>\n\n"
    score = str(prob.objective)
    constraints = [str(const) for const in prob.constraints.values()]
    for v in prob.variables():
        score = score.replace(v.name, str(v.varValue))
        constraints = [const.replace(v.name, str(v.varValue))
                       for const in constraints]
        if v.varValue != 0:
            string += v.name.replace('_', ' ')
            string += " = "
            string += str(v.varValue)
            string += "\n"
    string += div
    string += "Player Costs: "
    for constraint in constraints:
        constraint_pretty = " + ".join(re.findall("[0-9\.]*\*1.0", constraint))
        if constraint_pretty != "":
            string += "{} = {}".format(constraint_pretty,
                                       eval(constraint_pretty))
    string += "\n"
    string += div
    string += "Projected Score: "
    score_pretty = " + ".join(re.findall("[0-9\.]+\*1.0", score))
    string += "{} = {}".format(score_pretty, eval(score))
    string += "\n\n\n"
    string = string.replace('*1.0', '').replace(' = 1.0', '')
    return string


def send_email(score_string, week):
    emailMsg = """ 
            <html>
            <p>
            <h1>Draft Kings Week {0} Optimal Lineups</h1>
            <h2> Here are the Sat Morning projections for Sunday's Games. Good Luck!
            <p>
            <h3>Below you will see 3 lineups. Each of the lineups is dependent on what position you want to use as a flex (RB/WR/TE). These projections are based on the projections from sites such as the NFL, CBS, and Stats.com.
            </h3>
            <h4>All the lineups are PPR and now includes defenses as well.
            </h4>
            <br>
            <body>
            """.format(week) + score_string.replace('\n', '<br>') + """
            </body>
            <p style="font-size: 30px;">From your friends at <a href="https://www.FastBreakStats.com">Fast Break Stats</a></p>
            <br><br><small>
            <h4>Legal Disclaimer</h4>
            <ol>
                <li>Gambling involves risk. Please only gamble with funds that you can comfortably afford to lose.</li>
                <li>Whilst we do our upmost to offer good advice and information we cannot be held responsible for any loss that maybe be incurred as a result of gambling.</li>
                <li>This email does not take responsibility for injuries that are announced after the email was sent. All projections are grabbed seconds before the email is sent.</li>
                <li>We do our best to make sure all the information that we provide is correct. However from time to time mistakes will be made and we will not be held liable. Please check any stats or information if you are unsure how accurate they are.</li>
                <li>These are only projections. This means they are not required to come true and we are not responsible for a player not performing as projected.</li>
                <li>No guarantees are made with regards to results or financial gain. All forms of betting carry financial risk and it is down to the individual to make bets with or without the assistance of information provided on this site.</li>
                <li>FastBreakStats.com cannot be held responsible for any loss that maybe be incurred as a result of following the betting tips provided on this site.</li>
                <li>The material contained on this site is intended to inform and educate the reader and in no way represents an inducement to gamble legally or illegally. Betting is illegal in some countries, or areas of countries. It is the sole responsibility of the user to act in accordance with their local laws.</li>
                <li>Past performances do not guarantee success in the future. There are no dead certainties when it comes to betting so only risk money that you can comfortable afford to lose.</li>
            </ol></small>
            </html>"""

    email_list = ['Blakekobel@gmail.com', 'jake_mdws@yahoo.com', 'Luke.darity@yahoo.com', 'Potzmanm1@gmail.com', 'Ctaylor9502@gmail.com', 'zackwool@gmail.com',
                  'zfletcher018@gmail.com', 'ericnews512@gmail.com', 'wadehagebusch@gmail.com', 'kodykingree@gmail.com', 't.hahn3@yahoo.com', 'bkobel928@lsr7.net']

    for email_addr in email_list:
        message = Mail(
            from_email='contact@fastbreakstats.com',
            to_emails=email_addr,
            subject='Draft Kings Week {} Projections'.format(week),
            html_content=emailMsg)

        try:
            sg = SendGridAPIClient(
                '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')
            response = sg.send(message)
            print(response.status_code)
            # print(response.body)
            # print(response.headers)
        except Exception as e:
            print(e.message)


def main():
    week = "7"
    group_id = "40909"
    proj = scrape_fantasypros()
    dk_scrape = scrape_dk(group_id)
    proj_and_dk = make_master_df(proj, week, dk_scrape)
    # print(proj_and_dk)

    # master_df = pd.read_csv('week_4.csv')
    extra_pos = [[3, 3, 1], [2, 4, 1], [2, 3, 2]]
    pos_name = ["RB Flex ", "WR Flex ", "TE Flex "]
    cap = 50000
    big_string = ""
    for x in range(len(extra_pos)):
        prob = setup(proj_and_dk, extra_pos[x], cap)
        big_string += '<strong>'+pos_name[x]
        small_str = summary(prob)
        big_string += small_str
    # print(big_string)
    send_email(big_string, week)


main()
