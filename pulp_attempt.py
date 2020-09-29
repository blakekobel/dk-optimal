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


def send_email(score_string):
    email_list = ['Blakekobel@gmail.com']
    # , 'jake_mdws@yahoo.com', 'Luke.darity@yahoo.com', 'Potzmanm1@gmail.com', 'Ctaylor9502@gmail.com', 'zackwool@gmail.com',
    #               'zfletcher018@gmail.com', 'ericnews512@gmail.com', 'wadehagebusch@gmail.com', 'kodykingree@gmail.com', 't.hahn3@yahoo.com', 'bkobel928@lsr7.net']
    CLIENT_SECRET_FILE = 'client_secret.json'
    API_NAME = 'gmail'
    API_VERSION = 'v1'
    SCOPES = ['https://mail.google.com/']

    service = Create_Service(CLIENT_SECRET_FILE, API_NAME, API_VERSION, SCOPES)

    emailMsg = """ 
            <html>
            <p>
            <h1>Draft Kings Week 4 Optimal Lineups</h1>
            <h2> Here are the early projections for this upcoming weekend. More to come as the week progresses.
            <p>
            <h3>Below you will see 3 lineups. Each of the lineups is dependent on what position you want to use as a flex (RB/WR/TE). These projections are based on the projections from sites such as the NFL, CBS, and Stats.com.
            </h3>
            <h4>All the lineups are PPR and now includes defenses as well.
            </h4>
            <br>
            <body>
            """ + score_string.replace('\n', '<br>') + """
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
    # score_string

    for email_addr in email_list:
        mimeMessage = MIMEMultipart()
        mimeMessage['to'] = email_addr
        mimeMessage['subject'] = 'Draft Kings Week 4 Projections'
        mimeMessage.attach(MIMEText(emailMsg, 'html'))
        raw_string = base64.urlsafe_b64encode(mimeMessage.as_bytes()).decode()

        message = service.users().messages().send(
            userId='me', body={'raw': raw_string}).execute()
        print(message)


def main():
    master_df = pd.read_csv('week_4.csv')
    extra_pos = [[3, 3, 1], [2, 4, 1], [2, 3, 2]]
    pos_name = ["RB Flex ", "WR Flex ", "TE Flex "]
    cap = 50000
    big_string = ""
    for x in range(len(extra_pos)):
        prob = setup(master_df, extra_pos[x], cap)
        # print(prob)
        big_string += '<strong>'+pos_name[x]
        small_str = summary(prob)
        big_string += small_str
    print(big_string)
    send_email(big_string)


main()