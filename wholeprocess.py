import datetime as dt
from bs4 import BeautifulSoup
import requests
import re
import time
import random
import pandas as pd
import os
import numpy as np
from itertools import permutations
from pulp import *
import smtplib
from smtplib import SMTPException
from Google import Create_Service
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from io import StringIO


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


def main():
    week = "5"
    group_id = "40304"
    proj = scrape_fantasypros()
    dk_scrape = scrape_dk(group_id)
    proj_and_dk = make_master_df(proj, week, dk_scrape)
    proj.to_csv('fpros.csv'.format(week), index=False)
    dk_scrape.to_csv('DKsalaries_week{}.csv'.format(week), index=False)
    proj_and_dk.to_csv('week_{}.csv'.format(week), index=False)


main()
