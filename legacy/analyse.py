from lxml import etree
import csv
import json
import string
from collections import OrderedDict
from operator import itemgetter
import os
from nltk import word_tokenize
from nltk.util import ngrams
import requests


if not os.path.exists("results"):
    os.mkdir("results")

data_path = "../data/"
punct = string.punctuation + '’'
ns={'w': 'http://www.w3.org/1999/xhtml'}

stopwords = [w.strip() for w in open(data_path + "stopwords.txt")]

actors = {r["id"]:r for r in csv.DictReader(open("actors.csv", encoding="utf-16"), fieldnames=["id","honorific","pseudonym","status_osp","depart"])}
actors.pop("id")

all_actors = {a["id"]:{"pseudonym":a["pseudonym"], "honorific":a["honorific"], "status_osp":a["status_osp"]} for a in requests.get('https://feux.cfregisters.org/api/acteurs').json()}


for a in actors.keys():
    try:
        c = open("legacy_data/{}.json".format(a))
        content = json.load(c)
        total_m = 0
        for k in content.keys():
            total_m += content[k]["mentions"]
            for elem in content[k]["data"]:
                elem["xml"] = etree.fromstring(elem["xml"])
        actors[a]["data"] = content
        actors[a]["years"] = sorted([int(y) for y in content.keys()])
        actors[a]["total_mentions"] = total_m
    except Exception as e:
        continue



plays = {r["id"]:r for r in csv.DictReader(open(data_path+"plays.csv", encoding="utf-16"), fieldnames=["id","author","title","genre","date_de_creation"])}
roles = {r["id"]:r for r in csv.DictReader(open(data_path+"chars.csv", encoding="utf-16"), fieldnames=["id","nom","gender","play_id","author","title","genre"])}
authors = {r["id"]:r for r in csv.DictReader(open(data_path+"authors.csv", encoding="utf-16"), fieldnames=["id","pref_label","plays"])}
plays.pop("id")
roles.pop("id")
authors.pop("id")

#top poeple
def top_people_by_mention():
    mention_dict = {k:v["total_mentions"] for (k,v) in actors.items() if v.get("data")}
    mention_dict = OrderedDict(sorted(mention_dict.items(), key=itemgetter(1), reverse=True))
    writer = csv.writer(open("results/mention_comp.csv", 'w'))
    #id, pseudo, pure mentions, and normalized
    writer.writerow(["id", "pseudonym", "mentions", "normalized"])
    for (k,v) in mention_dict.items():
        writer.writerow([k, actors[k]["pseudonym"], v, v/(1793-int(actors[k]["depart"]))])

#mentions over time (like careers except for n years after they've left)
def mention_chronology():
    res_dict = {}
    for (k,v) in actors.items():
        if v.get("data"):
            res_dict[k] = [v["data"][str(y)]["mentions"] if v["data"].get(str(y)) else 0 for y in range(v["years"][0], v["years"][-1]+1)]
    max_len = max([len(x) for x in res_dict.values()])
    k_list = ["id", "gender"] + [i+1 for i in range(max_len)]
    writer = csv.writer(open("results/mention_chronology.csv",'w'))
    writer.writerow(k_list)
    for (k,v) in res_dict.items():
        gender = "F" if actors[k]["honorific"]=="Madame" or actors[k]["honorific"]=='Mademoiselle' or actors[k]["honorific"]=='Citoyenne' else 'M'
        m_list = [v[i] if i<len(v) else 0 for i in range(max_len)]
        writer.writerow([k, gender] + m_list)

#word comp helpers - same code as in debut analysis
def make_bow(text_list, stop_filter=True):
    res_list = []
    for elem in text_list:
        #extra step to account for the fact that the tokenizer doesn't like french
        tokens = [e.split("'") for e in word_tokenize(elem.lower())]
        #flatten and add
        res_list.extend([val for sublist in tokens for val in sublist])
    return [w for w in res_list if w not in stopwords and w not in punct]

def make_freq_vec(bow):
    counts = {}
    for e in bow:
        if(counts.get(e)):
            counts[e] += 1
        else:
            counts[e] = 1
    return OrderedDict(sorted(counts.items(), key=itemgetter(1), reverse=True))


#comprehension rather than in place because I don't want to modify data
def normalized_vector(d):
    return {k:(v/sum(d.values()))*100 for (k,v) in d.items()}

def make_ngrams(n, bow):
    n_grams = [' '.join(grams) for grams in ngrams(bow, n)]
    freq_grams = {n_grams.count(k):k for k in set(n_grams)}
    return OrderedDict(sorted(freq_grams.items(), reverse=True))


def ngram_report(text, filename):
    with open(filename, 'w') as f:
        for n in range(2,5):
            f.write("{}-grams\n\n".format(n))
            pop_grams = make_ngrams(n, text)
            for (k,v) in pop_grams.items():
                f.write("{}: {}\n".format(k,v))
            f.write("\n\n----------------------\n\n")



#word comp + ngrams (all/men/women)
def word_comp():
    actors_texts = {}
    for (k,v) in actors.items():
        if v.get("data"):
            texts = []
            for elem in v["data"].values():
                texts.extend(e["plaintext"] for e in elem["data"])
            actors_texts[k] = texts
    all_texts = []
    men_texts = []
    women_texts = []
    for (k,v) in actors_texts.items():
        all_texts.extend(v)
        if(actors[k]["honorific"]=="Madame" or actors[k]["honorific"]=='Mademoiselle' or actors[k]["honorific"]=='Citoyenne'):
            women_texts.extend(v)
        else:
            men_texts.extend(v)

    #do basically the workflow from debuts
    #skip the individual non normalized freq though - comp is more interesting
    all_bow =make_bow(all_texts)
    ngram_report(all_bow, "results/ngrams_all.txt")
    all_freq_vec = normalized_vector(make_freq_vec(all_bow))

    men_bow =make_bow(men_texts)
    ngram_report(men_bow, "results/ngrams_men.txt")
    men_freq_vec = normalized_vector(make_freq_vec(men_bow))

    women_bow =make_bow(women_texts)
    ngram_report(women_bow, "results/ngrams_women.txt")
    women_freq_vec = normalized_vector(make_freq_vec(women_bow))

    writer = csv.writer(open("results/freq_comp.csv", 'w'))
    writer.writerow(("word", "all", "men", "women"))
    for word in all_freq_vec.keys():
        writer.writerow((word, all_freq_vec[word], men_freq_vec[word] if men_freq_vec.get(word) else 0, women_freq_vec[word] if women_freq_vec.get(word) else 0))

def count_vectorize(l):
    res = {}
    for elem in l:
        if res.get(elem):
            res[elem] += 1
        else:
            res[elem]=1
    return OrderedDict(sorted(res.items(), key=itemgetter(1), reverse=True))

#most mentioned entities (overall and by actor) - will allow a look at roles etc


#helper
#boy do I wish python had switch statements
#yes the first line of each block is unecessary, but it makes the code look so much neater
def format_entity(tag, id):
    if(tag=='comedien'):
        a = all_actors[int(id)]
        return "{}, {} ({})".format(a["pseudonym"], a["honorific"], a["status_osp"])
    elif(tag=='piece'):
        p = plays[id]
        st = "{}, {}, {}".format(p["title"], p["author"], p["genre"])
        if p.get("date_de_creation"):
            st += " ({})".format(p["date_de_creation"])
        return st
    elif(tag=='personnage'):
        r=roles[id]
        return "{} ({}), {} ({}), {}".format(r["nom"], r["gender"], r["title"], r["author"], r["genre"])
    elif(tag=='auteur'):
        return authors[id]["pref_label"]

def entity_comp():
    overall_entities = {"comedien":[], 'piece':[], 'personnage':[], 'auteur':[]}
    for (k,v) in actors.items():
        if v.get("data"):
            entities = {"comedien":[], 'piece':[], 'personnage':[], 'auteur':[]}
            for elem in v["data"].values():
                for e in elem["data"]:
                    for tag in entities:
                        en = [e.get("id") for e in e["xml"].findall(".//w:{}".format(tag), ns)]
                        if(tag=='comedien'):
                            en = [e for e in en if e!=k]
                        entities[tag].extend(en)
                        overall_entities[tag].extend(en)

            person_writer = open("results/{}_entities.txt".format(format_entity('comedien', k)), 'w')
            for tag in entities.keys():
                person_writer.write(tag + "\n\n")
                counts = count_vectorize(entities[tag])
                for k in list(counts.keys())[:5]:
                    person_writer.write("{}: {}\n".format(counts[k], format_entity(tag, k)))
                person_writer.write("\n\n")

   #I could have done this more efficiently
   #ah well
    writer = csv.writer(open("results/actor_rank.csv", 'w'))
    writer.writerow(["count"] + list(all_actors[35].keys()))
    for (k,v) in count_vectorize(overall_entities["comedien"]).items():
        writer.writerow([v] + list(all_actors[int(k)].values()))

    writer = csv.writer(open("results/author_rank.csv", 'w'))
    writer.writerow(["count"] + list(authors["1"].keys()))
    for (k,v) in count_vectorize(overall_entities["auteur"]).items():
        writer.writerow([v] + list(authors[k].values()))

    writer = csv.writer(open("results/play_rank.csv", 'w'))
    writer.writerow(["count"] + list(plays["5155"].keys()))
    for (k,v) in count_vectorize(overall_entities["piece"]).items():
        writer.writerow([v] + list(plays[k].values()))

    writer = csv.writer(open("results/role_rank.csv", 'w'))
    writer.writerow(["count"] + list(roles["1"].keys()))
    for (k,v) in count_vectorize(overall_entities["personnage"]).items():
        writer.writerow([v] + list(roles[k].values()))




def main():
    top_people_by_mention()
    mention_chronology()
    word_comp()
    entity_comp()

main()
