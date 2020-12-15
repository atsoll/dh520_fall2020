import psycopg2
import csv
from dotenv import load_dotenv
import requests
import os
import json
from collections import OrderedDict
from operator import itemgetter
from lxml import etree

if not os.path.exists("results"):
    os.mkdir("results")

#IMPORTANT! THIS ONE ONLY COVERS 65-93 BECAUSE I WANT ACCESS TO FEUX DATA
#vis à vis DB things --- yeah I could use the api, but direct queries are so much easier....

data_path = "../data/"
ns={'w': 'http://www.w3.org/1999/xhtml'}


#load in globally useful data from csv files (actors, authors, plays) and shove it into dictionaries
#use the graph api here - it's already decently set up to only include folks who appeared in the feux window
resp = requests.get("https://graph-api.cfregisters.org/actors")
a_list = list(filter(lambda a: a.get("status_osp") and 'S' in a["status_osp"],resp.json()))

actors = {}
for a in a_list:
    actors[a["id"]] = {"honorific": a["honorific"],"pseudonym": a["pseudonym"],"status_osp": a["status_osp"], "entree":(a["entree"] if a.get("entree") else a["debut"][0]), "societariat":a["societariat"], "depart":a["depart"]}
    try:
        c = open("career_data/{}.json".format(a["id"]))
        content = json.load(c)
        for k in content.keys():
            for elem in content[k]:
                elem["xml"] = etree.fromstring(elem["xml"])
        actors[a["id"]]["data"] = content
        actors[a["id"]]["years"] = [int(y) for y in content.keys()]

    except Exception as e:
        continue



plays = {r["id"]:r for r in csv.DictReader(open(data_path+"plays.csv", encoding="utf-16"), fieldnames=["id","author","title","genre","date_de_creation"])}
roles = {r["id"]:r for r in csv.DictReader(open(data_path+"chars.csv", encoding="utf-16"), fieldnames=["id","nom","gender","play_id","author","title","genre"])}
authors = {r["id"]:r for r in csv.DictReader(open(data_path+"authors.csv", encoding="utf-16"), fieldnames=["id","pref_label","plays"])}
plays.pop("id")
roles.pop("id")
authors.pop("id")

def connect():
  load_dotenv()
  #grab the environment variables
  user = os.environ.get("DB_USER")
  pwd = os.environ.get("DB_PASSWORD")
  db = os.environ.get("DB_NAME")
  host = os.environ.get("DB_HOST")

  return psycopg2.connect(dbname=db, user=user, password=pwd, host=host)

def count_vectorize(l):
    res = {}
    for elem in l:
        if res.get(elem):
            res[elem] += 1
        else:
            res[elem]=1
    return OrderedDict(sorted(res.items(), key=itemgetter(1), reverse=True))


def format_play(p):
    st = "{}, {}, {}".format(p["title"], p["author"], p["genre"])
    if p.get("date_de_creation"):
        st += " ({})".format(p["date_de_creation"])
    return st

def format_role(r):
    return "{} ({}), {} ({}), {}".format(r["nom"], r["gender"], r["title"], r["author"], r["genre"])

#for each actors look at:
#perfs vs mentions vs revenue (by year, from career start to end)
#perf numbers from that query ARE counting multiple roles per night

#most mentioned plays vs top plays (by revenue and by #perfs)
#most mentioned roles vs top roles (by revenue and by #perfs)
#roles don't need to look at time (molé shows us how they played wildly inaccurate roles wrt age)

def actor_report(id, cursor):
    a = actors[id]
    label = str(id) + "_" + a["pseudonym"].replace(" ", "_")
    if(not os.path.exists("results/{}".format(label))):
        os.mkdir("results/"+label)


    #compare activity in feux vs activity in the press
    writer = csv.writer(open("results/{}/activity_comp.csv".format(label), 'w'))
    writer.writerow(["year", "perfs", "revenue", "mentions"])
    cursor.execute("select extract(year from date) as year, sum(roles) as perfs, sum(recettes) as revenue from ( select  date, count(*) as roles,  (coalesce(total_receipts_recorded_l, 0)*240 + coalesce(total_receipts_recorded_s,0) * 12 + coalesce(total_receipts_recorded_d,0) )/240  as recettes  from casting_records join feux_plays on feux_play_id=feux_plays.id join feux on feux_id = feux.id join registers on registers.id= register_id where actor_id  = %s group by date, recettes) as t group by year", [id])
    feux_data= {}
    for elem in cursor.fetchall():
        feux_data[str(int(elem[0]))] = (int(elem[1]), elem[2])
    for y in sorted([str(int(e)) for e in feux_data.keys()]):
        mentions = len(a["data"][y]) if a["data"].get(y) else 0
        writer.writerow([y, int(feux_data[y][0]), feux_data[y][1], mentions])

    #get some stats about entities
    entities = {'piece':[], 'personnage':[]}
    for elem in a["data"].values():
        for tag in entities.keys():
            for item in elem:
                entities[tag].extend([e.get("id") for e in item["xml"].findall(".//w:{}".format(tag), ns)])

    entity_query = "select {0}, count(*) as reps, sum(recettes) as revenue from ( select  {0},  (coalesce(total_receipts_recorded_l, 0)*240 + coalesce(total_receipts_recorded_s,0) * 12 + coalesce(total_receipts_recorded_d,0) )/240  as recettes  from casting_records join feux_plays on feux_play_id=feux_plays.id join feux on feux_id = feux.id join registers on registers.id= register_id where actor_id  = {1}) as t where {0} is not null group by {0} order by {2} desc limit 5"
    #get top plays and roles, compare (expect roles to be similar ish to plays)
    cursor.execute(entity_query.format("role_id", id, 'reps'))
    pop_roles_reps = cursor.fetchall()

    cursor.execute(entity_query.format('role_id', id, 'revenue'))
    pop_roles_recettes = cursor.fetchall()

    pop_roles_mentions = list(count_vectorize(entities["personnage"]).items())[:5]


    cursor.execute(entity_query.format("play_id", id, 'reps'))
    pop_plays_reps = cursor.fetchall()

    cursor.execute(entity_query.format('play_id', id, 'revenue'))
    pop_plays_recettes = cursor.fetchall()

    pop_plays_mentions = list(count_vectorize(entities["piece"]).items())[:5]

    #not quite sure how to export this data
    #text for now (I'll probably regret this later
    outfile = open("results/{}/entity_comp.txt".format(label), 'w')

    outfile.write("roles\n\n")
    outfile.write("top 5 mentions\n\n")
    for elem in pop_roles_mentions:
        outfile.write("{}: {}\n".format(elem[1], format_role(roles[str(elem[0])])))
    outfile.write("\n\ntop 5 recettes\n\n")
    for elem in pop_roles_recettes:
        outfile.write("{}: {}, {}\n".format(elem[2], format_role(roles[str(elem[0])]), elem[1]))
    outfile.write("\n\ntop 5 représentations\n\n")
    for elem in pop_roles_reps:
        outfile.write("{}: {}, {}\n".format(elem[1], format_role(roles[str(elem[0])]), elem[2]))

    outfile.write("\n\nplays\n\n")
    outfile.write("top 5 mentions\n\n")
    for elem in pop_plays_mentions:
        outfile.write("{}: {}\n".format(elem[1], format_play(plays[str(elem[0])])))
    outfile.write("\n\ntop 5 recettes\n\n")
    for elem in pop_plays_recettes:
        outfile.write("{}: {}, {}\n".format(elem[2], format_play(plays[str(elem[0])]), elem[1]))
    outfile.write("\n\ntop 5 représentations\n\n")
    for elem in pop_plays_reps:
        outfile.write("{}: {}, {}\n".format(elem[1], format_play(plays[str(elem[0])]), elem[2]))






def run_actor_report(cursor):
    for (k,v) in actors.items():
        #yes there are people who are left out, they're covered by the overall report
        if(v.get("data")):
            actor_report(k, cursor)


#overall look at mentions by gender
#do a ranking of actor mentions, with info about gender and reps/revenue
#everything should be normalized by # years present
#graph api unfortunately normalizes by #perf not year
#keep people in who don't have mentions
def overall_comp(cur):
    cur.execute("select actor_id,extract(year from max_date)+1 - extract(year from min_date) as duration from ( select max(perf_date) as max_date, min(perf_date) as min_date, actor_id from casting_records join feux_plays on feux_play_id = feux_plays.id join feux on feux_id = feux.id join acteurs on acteurs.id= actor_id where actor_id is not null group by actor_id) as t")
    duration = {int(x[0]): int(x[1]) for x in cur.fetchall()}

    cur.execute("select actor_id, count(*) from casting_records join acteurs on actor_id = acteurs.id where actor_id is not null group by actor_id ")
    rep_data = cur.fetchall()
    reps = {int(x[0]): (int(x[1]), rep_data.index(x)+1) for x in rep_data}

    cur.execute("select actor_id, sum(recettes) from ( select distinct actor_id, (coalesce(total_receipts_recorded_l, 0)*240 + coalesce(total_receipts_recorded_s,0) * 12 + coalesce(total_receipts_recorded_d,0) )/240  as recettes from casting_records join feux_plays on feux_play_id= feux_plays.id join feux on feux_id = feux.id join registers on register_id = registers.id) as t where actor_id is not null group by actor_id")
    rec_data = cur.fetchall()
    recettes = {int(x[0]): (int(x[1]), rec_data.index(x)+1) for x in rec_data }

    mentions = {k: sum([len(x) for x in v["data"].values()]) if v.get("data") else 0 for (k,v) in actors.items()}
    mentions = OrderedDict(sorted(mentions.items(), key=itemgetter(1), reverse=True))

    res_dict = {}
    
    for k in mentions.keys():
        gender = "F" if actors[k]["honorific"]=="Madame" or actors[k]["honorific"]=='Mademoiselle' or actors[k]["honorific"]=='Citoyenne' else 'M'
        res_dict[k] = {"id":k, "duration":duration[k], "gender":gender, "pseudo":actors[k]["pseudonym"], "total_mentions": mentions[k], "mentions":mentions[k]/duration[k], "reps":(reps[k][0])/duration[k], "recettes":(recettes[k][0])/duration[k], "reps_rank":reps[k][1], "recettes_rank":recettes[k][1] }
    writer = csv.writer(open("results/stats_comp.csv", 'w'))
    writer.writerow(res_dict[35].keys())
    for item in res_dict.values():
        writer.writerow(item.values())

#do overall mentions n years after their first appearence (and note if it's men vs women) to see if they continue to be talked about
def mention_chronology():
    writer = csv.writer(open("results/mention_chronology.csv", 'w'))
    mention_dict = {}
    for (k,v) in actors.items():
        if(v.get("data")):
            years = sorted([int(x) for x in v["data"].keys()])
            min_year = min(years[0], max(int(v["entree"]), 1765))
            max_year = max(years[-1], int(v["depart"]))
            #I don't care about the actual year, just about it being n years since they first showed up
            mention_dict[k] = [len(v["data"][str(y)]) if v["data"].get(str(y)) else 0 for y in range(min_year, max_year+1)]
    max_len = max([len(x) for x in mention_dict.values()])
    k_list = ["id", "gender"] + [i+1 for i in range(max_len)]
    writer.writerow(k_list)
    #pad with 0 to make potential future viz easier
    for (k,v) in actors.items():
        if(v.get("data")):
            gender = "F" if v["honorific"]=="Madame" or v["honorific"]=='Mademoiselle' or v["honorific"]=='Citoyenne' else 'M'
            m_list = [mention_dict[k][i] if i<len(mention_dict[k]) else 0 for i in range(max_len)]
            writer.writerow([k, gender] + m_list)




def main():
    con = connect()
    cur = con.cursor()
    run_actor_report(cur)
    overall_comp(cur)
    mention_chronology()

main()
