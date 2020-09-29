import datetime as dt
from bs4 import BeautifulSoup
import requests
import re
import time
import random
import pandas as pd
import os


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
    fantasypros_proj.to_csv("fpros.csv")
    return fantasypros_proj


def scrape_dk(week):
    dk_url = "https://www.draftkings.com/lineup/getavailableplayerscsv?contestTypeId=21&draftGroupId=40224"
    site = requests.get(dk_url)
    with open(os.path.join("//Users//kobelb//Documents//dk-optimal//DKsalaries_week{0}.csv".format(week)), "wb") as code:
        code.write(site.content)
    # pass


def make_master_df(projections, week):
    dk = pd.read_csv('DKsalaries_week{0}.csv'.format(week))
    proj = projections
    historical = pd.read_csv('pos_sal_avg.csv')

    proj = proj[~proj['Projected Points'].isin(
        ['-', '_', ' ', '+', '='])]
    proj['Projected Points'] = proj['Projected Points'].astype(float)
    dk = dk.drop(['Name + ID', 'ID', 'Game Info'], axis=1)

    master_df = dk.merge(proj, left_on='Name', right_on='Name')
    master_df = master_df.merge(
        historical, left_on=['Position', 'Salary'], right_on=['Pos', 'DK salary'])
    master_df = master_df.drop(['Roster Position', 'Pos', 'DK salary'], axis=1)
    master_df = master_df.rename(
        columns={"Position": "Pos", "DK points": "dk_pos_sal_avg_points"})

    # master_df['Points Per Dollar'] = master_df['Projected Points'] / \
    #     master_df['Salary']
    # master_df['Points Per 1K'] = master_df['Projected Points'] / 1000
    # master_df['Value'] = master_df['Projected Points'] / \
    #     (master_df['Salary']/1000)

    print(master_df)

    # team1 = master_df[master_df['Name'].isin(['Mitchell Trubisky',
    #                                           'Austin Ekeler', 'Devin Singletary', 'Julio Jones', 'Michael Gallup', 'Jamison Crowder', 'Travis Kelce', 'Diontae Johnson'])]
    # team2 = master_df[master_df['Name'].isin(['Kyler Murray',
    #                                           'Austin Ekeler', 'Kenyan Drake', 'Julio Jones', 'Amari Cooper', 'Jamison Crowder', 'Zach Ertz', 'Diontae Johnson'])]

    # print(team2['Projected Points'].sum())
    master_df.to_csv("week_{0}.csv".format(week), index=False)


def main():
    week = input("Enter week number: ")
    proj = scrape_fantasypros()
    scrape_dk(week)
    make_master_df(proj, week)


main()
