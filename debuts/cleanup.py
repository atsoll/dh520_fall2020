#random odds and end of code to help with making graphics
#for debuts:
#gender comp
#sociétaires comp
#genre comp
#editor comp
#chronology (all, men, women)
import os
import csv
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


if not os.path.exists("clean"):
    os.mkdir("clean")

#ok hardcoded isn't fab but there aren't many of them
words = ['intelligence', 'jeu', 'figure', 'talent', 'succès', 'emploi', 'vérité', 'art', 'voix', 'organe', 'applaudi', 'naturel', 'agréable', 'fort', 'taille', 'plaisir', 'province', 'défauts', 'sensibilité', 'timidité', 'manque', 'corriger', 'prononciation', 'passion', 'finesse', 'mérite', 'gestes', 'vivacité', 'beautés', 'justice', 'physionomie', 'noble', 'froid', 'feu', 'esprit']


#this could have gone in a function ... but whatever
writer = csv.writer(open("clean/gender_comp.csv", 'w'))
reader = csv.reader(open("results/freq_comp_gender.csv"))
#write the header
writer.writerow(next(reader))
for row in reader:
    if row[0] in words:
        writer.writerow(row)

writer = csv.writer(open("clean/genre_comp.csv", 'w'))
reader = csv.reader(open("results/freq_comp_genre.csv"))
#write the header
writer.writerow(next(reader))
for row in reader:
    if row[0] in words:
        writer.writerow(row)

writer = csv.writer(open("clean/status_comp.csv", 'w'))
reader = csv.reader(open("results/freq_comp_status.csv"))
#write the header
writer.writerow(next(reader))
for row in reader:
    if row[0] in words:
        writer.writerow(row)

chron_men = {}
chron_women = {}
chron_all = {}

reader = csv.reader(open("results/chronology_all.csv"))

all_years = next(reader)
for row in reader:
    if row[0] in words:
        chron_all[row[0]] = {y:row[all_years.index(y)] for y in all_years}

reader = csv.reader(open("results/chronology_men.csv"))

men_years = next(reader)
for row in reader:
    if row[0] in words:
        chron_men[row[0]] = {y:row[men_years.index(y)] if y in men_years else 0 for y in all_years}


reader = csv.reader(open("results/chronology_women.csv"))

women_years = next(reader)
for row in reader:
    if row[0] in words:
        chron_women[row[0]] = {y:row[women_years.index(y)] if y in women_years else 0 for y in all_years}


for k in chron_all.keys():
    writer = csv.writer(open("clean/chronology_{}.csv".format(k), 'w'))
    writer.writerow(["year"] + all_years[1:])
    writer.writerow(["all"] + [chron_all[k][y] for y in all_years[1:]])
    if(chron_men.get(k)):
        writer.writerow(["men"] + [chron_men[k][y] for y in all_years[1:]])
    if(chron_women.get(k)):
        writer.writerow(["women"] +[chron_women[k][y] for y in all_years[1:]])

#just for good measure, do a super constraind one
writer = csv.writer(open("clean/chronology_limited.csv", 'w'))
reader = csv.reader(open("results/chronology_constrained.csv"))
#write the header
writer.writerow(next(reader))
for row in reader:
    if row[0] in words:
        writer.writerow(row)


editors= ["Fuzelier","Boissy", "Marmontel", "De La Place", "Lacombe","De La Harpe"]
data_dict = {}
for e in editors:
    res = {}
    with open("results/{}_freq.txt".format(e.replace(" ", "_"))) as f:
        for l in f:
            parts = l.strip().split(":")
            if(len(parts)==1 or parts[0] not in words):
                continue
            res[parts[0]] = float(parts[1].split(',')[1])
    data_dict[e] = res
writer = csv.writer(open("clean/freq_comp_editor.csv", 'w'))
writer.writerow(["word"] + editors)
for word in words:
    r = [data_dict[e][word] if data_dict[e].get(word) else 0 for e in editors]
    writer.writerow([word] + r)
