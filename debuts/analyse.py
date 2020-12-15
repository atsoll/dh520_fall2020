import csv
import json
import os
from nltk import word_tokenize
from lxml import etree
from collections import OrderedDict
from operator import itemgetter
import string
from nltk.util import ngrams
from lxml import etree

if not os.path.exists("results"):
    os.mkdir("results")


data_path = "../data/"
punct = string.punctuation + '’'
ns={'w': 'http://www.w3.org/1999/xhtml'}



stopwords = [w.strip() for w in open(data_path + "stopwords.txt")]
#load in globally useful data from csv files (actors, authors, plays) and shove it into dictionaries
actors = {r["id"]:r for r in csv.DictReader(open("actors.csv", encoding="utf-16"), fieldnames=["id","honorific","pseudonym","status_osp","first_date"])}
actors.pop("id")

for a in actors.keys():
    try:
        c = open("./debut_data/" + a + ".json")
        content = json.load(c)
        actors[a]["text"] = content["plaintext"]
        actors[a]["xml"] = etree.fromstring(content["xml"])
        actors[a]["year"] = content["year"]
    except:
        continue



plays = {r["id"]:r for r in csv.DictReader(open(data_path+"plays.csv", encoding="utf-16"), fieldnames=["id","author","title","genre","date_de_creation"])}
roles = {r["id"]:r for r in csv.DictReader(open(data_path+"chars.csv", encoding="utf-16"), fieldnames=["id","nom","gender","play_id","author","title","genre"])}
authors = {r["id"]:r for r in csv.DictReader(open(data_path+"authors.csv", encoding="utf-16"), fieldnames=["id","pref_label","plays"])}
plays.pop("id")
roles.pop("id")
authors.pop("id")

#works but it might be worth trying lemmatization
#mind you, the lemmatizer would have a field day with the accents and alternative spellings...
#also comédiens/comédie would mess shit up
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

#do some basic plaintext reporting
#freq vector, ngrams
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



#could do tf-idf but there aren't really enough docs to make it worth it
def editor_report():
    editors= [{"name":"Fuzelier", "min":1745, "max":1752}, {"name":"Boissy", "min":1753, "max":1758}, {"name":"Marmontel", "min":1758, "max":1760}, {"name":"De La Place", "min":1761, "max":1767}, {"name":"Lacombe", "min":1768, "max":1778}, {"name":"De La Harpe", "min":1779, "max":1779}]

    all_text = [(int(a["year"]), a["text"]) for a in actors.values() if a.get("text")]
    all_vec = normalized_vector(make_freq_vec([t[1] for t in all_text]))
    editor_texts = {e["name"]:[t[1] for t in all_text if t[0]>= e["min"] and t[0]<= e["max"]]  for e in editors}
    #now do the same analysis for each editor
    for i in range(len(editors)):
        f_name = editors[i]["name"].replace(' ', "_")
        bow = make_bow(editor_texts[editors[i]["name"]])
        ngram_report(bow, "results/ngrams_{}.txt".format(f_name))
        editors[i]["freq_vec"] = make_freq_vec(bow)
        editors[i]["norm_vec"] = normalized_vector(editors[i]["freq_vec"])
        with open("results/{}_freq.txt".format(f_name), 'w') as f:
            f.write("{}\n".format(len(editors[i]["freq_vec"])))
            for (k,v) in editors[i]["freq_vec"].items():
                f.write("{}:{},{}\n".format(k,v, editors[i]["norm_vec"][k]))


    writer = csv.writer(open("results/editor_comp.csv", "w"))
    writer.writerow(["word", "norm"]+ [e["name"] for e in editors])
    for word in all_vec.keys():
        editor_words = [e["norm_vec"][word] if e["norm_vec"].get(word) else 0 for e in editors]
        writer.writerow([word, all_vec[word]] + editor_words)




#super basic word comp csv
#leave out a year if there's nothing and deal with it in graphing
#keys will need to be whole vocab
#input: dict where keys are years and values are lists of texts from that year
def word_timelines(yeartexts, filename, t):
    all_words = set()
    vec_dict = {}
    for (k,v) in yeartexts.items():
        vec_dict[k] = normalized_vector(make_freq_vec(make_bow(v)))
        all_words.update(vec_dict[k].keys())
    writer = csv.writer(open(filename, 'w'))
    years = sorted(vec_dict.keys())
    writer.writerow(["word"] + years)
    threshold = int(len(years)*t)
    for word in all_words:
        nums = [vec_dict[y][word] if vec_dict[y].get(word) else 0 for y in years]
        #only actually write if it appears in a decent amount of years
        if(nums.count(0) < threshold):
            writer.writerow([word] + nums)


def timeline_report():
    diff_dates = set([a["year"] for a in actors.values() if a.get("year")])
    #do holistic and gender split
    all_dates = {}
    women_dates = {}
    men_dates = {}
    for item in actors.values():
        if(not item.get("text")):
            continue
        y = item["year"]
        if(all_dates.get(y)):
            all_dates[y].append(item["text"])
        else:
            all_dates[y] = [item["text"]]
        if(item["honorific"]=="Mademoiselle" or item["honorific"]=="Madame" or item["honorific"]=="Citoyenne"):
            if(women_dates.get(y)):
                women_dates[y].append(item["text"])
            else:
                women_dates[y] = [item["text"]]
        else:
            if(men_dates.get(y)):
                men_dates[y].append(item["text"])
            else:
                men_dates[y] = [item["text"]]
    word_timelines(all_dates, "results/chronology_all.csv", 0.75)
    word_timelines(all_dates, "results/chronology_constrained.csv", 0.50)
    word_timelines(men_dates, "results/chronology_men.csv", 1)
    word_timelines(women_dates, "results/chronology_women.csv", 1)





#do a basic gender check - of the people who debuted in this time period, how many were women/how many women were reported (+ same for men)
#could do length, but it doesn't necessarily mean a ton b/c of extraction methods
def basics():
    f = open("results/basics.txt", "w")
    f.write("total debuts in period: {}\n".format(len(actors)))
    total_men =[]
    total_women = []
    press_men = []
    press_women = []
    for k in actors.keys():
        if actors[k]["honorific"]=="Mademoiselle" or actors[k]["honorific"]=="Madame" or actors[k]["honorific"]=="Citoyenne":
            total_women.append(k)
            if actors[k].get("text"):
                press_women.append(k)
        else:
            total_men.append(k)
            if actors[k].get("text"):
                press_men.append(k)
    all_press = press_men + press_women
    f.write("total press debuts: {}\n".format(len(all_press)))
    f.write("total debuts women: {}\n".format(len(total_women)))
    f.write("total debuts men: {}\n".format(len(total_men)))
    f.write("press debuts women: {}\n".format(len(press_women)))
    f.write("press debuts men: {}\n".format(len(press_men)))
    left_out = set(actors.keys()).difference(set(all_press))

    all_status = list(map(lambda x: actors[x]["status_osp"], all_press))
    out_status = list(map(lambda x: actors[x]["status_osp"], left_out))

    press_div = {k:all_status.count(k) for k in set(all_status)}
    out_div = {k:out_status.count(k) for k in set(out_status)}


    f.write("eventual osp status of press covered debuts: {}\n".format(press_div))
    f.write("eventual osp status of non covered debuts: {}\n".format(out_div))

#ok it doesn't exactly make sense to throw in the call to the ngram report here, but it's convenient
def report():
    alltext = [actors[a]["text"] for a in actors.keys() if actors[a].get("text")]
    all_bow =make_bow(alltext)
    ngram_report(all_bow, "results/ngrams_all.txt")
    all_freq_vec = make_freq_vec(all_bow)
    norm_all = normalized_vector(all_freq_vec)

    mentext = [actors[a]["text"] for a in actors.keys() if actors[a].get("text") and (actors[a]["honorific"]!="Mademoiselle" and actors[a]["honorific"]!="Madame" and actors[a]["honorific"]!='Citoyenne') ]
    men_bow = make_bow(mentext)
    ngram_report(men_bow, "results/ngrams_men.txt")
    men_freq_vec = make_freq_vec(men_bow)
    norm_men = normalized_vector(men_freq_vec)

    womentext = [actors[a]["text"] for a in actors.keys() if actors[a].get("text") and (actors[a]["honorific"]=="Mademoiselle" or actors[a]["honorific"]=="Madame" or actors[a]["honorific"]=="Citoyenne") ]
    women_bow = make_bow(womentext)
    ngram_report(women_bow, "results/ngrams_women.txt")
    women_freq_vec = make_freq_vec(women_bow)
    norm_women = normalized_vector(women_freq_vec)

    soctext = [actors[a]["text"] for a in actors.keys() if actors[a].get("text") and 'S' in actors[a]["status_osp"]]
    soc_bow = make_bow(soctext)
    ngram_report(soc_bow, "results/ngrams_sociétaires.txt")
    soc_freq = make_freq_vec(soc_bow)
    norm_soc = normalized_vector(soc_freq)

    non_soc = [actors[a]["text"] for a in actors.keys() if actors[a].get("text") and 'S' not in actors[a]["status_osp"]]
    non_soc_bow =make_bow(non_soc)
    ngram_report(non_soc_bow, "results/ngrams_non_sociétaires.txt")
    non_soc_freq = make_freq_vec(non_soc_bow)
    norm_non_soc = normalized_vector(non_soc_freq)

    #the individuals work but it's the comparisons that are telling
    with open("results/all_freq.txt", 'w') as f:
        f.write("{}\n".format(len(all_freq_vec)))
        for (k,v) in all_freq_vec.items():
            f.write("{}:{},{}\n".format(k,v, norm_all[k]))

    with open("results/men_freq.txt", 'w') as f:
        f.write("{}\n".format(len(men_freq_vec)))
        for (k,v) in men_freq_vec.items():
            f.write("{}:{},{}\n".format(k,v, norm_men[k]))

    with open("results/women_freq.txt", 'w') as f:
        f.write("{}\n".format(len(women_freq_vec)))
        for (k,v) in women_freq_vec.items():
            f.write("{}:{},{}\n".format(k,v,norm_women[k]))

    with open("results/sociétaires_freq.txt", 'w') as f:
        f.write("{}\n".format(len(soc_freq)))
        for (k,v) in soc_freq.items():
            f.write("{}:{},{}\n".format(k,v,norm_soc[k]))

    with open("results/non_sociétaires_freq.txt", 'w') as f:
        f.write("{}\n".format(len(non_soc_freq)))
        for (k,v) in non_soc_freq.items():
            f.write("{}:{},{}\n".format(k,v,norm_non_soc[k]))

    freq_writer = csv.writer(open("results/freq_comp_gender.csv", 'w'))
    freq_writer.writerow(("word", "all", "men", "women"))
    for word in norm_all.keys():
        freq_writer.writerow((word, norm_all[word], norm_men[word] if norm_men.get(word) else 0, norm_women[word] if norm_women.get(word) else 0))

    status_writer = csv.writer(open("results/freq_comp_status.csv", 'w'))
    status_writer.writerow(("word", "sociétaires", "non_sociétaires"))
    words = set(list(norm_soc.keys()) + list(norm_non_soc.keys()))
    for word in list(words):
        status_writer.writerow((word, norm_soc[word] if norm_soc.get(word) else 0, norm_non_soc[word] if norm_non_soc.get(word) else 0))

#helper
def count_vectorize(l):
    res = {}
    for elem in l:
        if res.get(elem):
            res[elem] += 1
        else:
            res[elem]=1
    return OrderedDict(sorted(res.items(), key=itemgetter(1), reverse=True))

#extract entities
#look for common roles
#could consider straight up comparing the debut stuff of people who played the same roles
def entity_report():
    #first pull together some essential data
    entities = {"piece":[], "personnage":[], "auteur":[]}
    for (k,v) in actors.items():
        if(v.get("xml") is None):
            continue
        for tag in entities.keys():
            en = [e.get("id") for e in v["xml"].findall(".//w:{}".format(tag), ns)]
            entities[tag].extend(en)
            actors[k][tag]= en

    writer = csv.writer(open("results/pop_plays.csv", 'w'))
    p_keys = list(plays["5155"].keys())
    writer.writerow(["counts"] + p_keys)
    for (k,v) in count_vectorize(entities["piece"]).items():
        writer.writerow([v] + list(plays[k].values()))
    print("play mentions: {}".format(len(entities["piece"])))

    writer = csv.writer(open("results/pop_roles.csv", 'w'))
    r_keys = list(roles["1"].keys())
    writer.writerow(["counts"] + r_keys)
    for (k,v) in count_vectorize(entities["personnage"]).items():
        writer.writerow([v] + list(roles[k].values()))
    print("role mentions: {}".format(len(entities["personnage"])))


    writer = csv.writer(open("results/pop_authors.csv", 'w'))
    au_keys = list(authors["1"].keys())
    writer.writerow(["counts"] + au_keys)
    for (k,v) in count_vectorize(entities["auteur"]).items():
        writer.writerow([v] + list(authors[k].values()))
    print("author mentions: {}".format(len(entities["auteur"])))

#look to see how diff genres are talked about
#just do overall - gender makes the sample too small, ditto for time
#also, for the sake of convenience, pull together files with the descriptions of the most mentioned roles
#égiste (254) for men, phèdre (4) for women
def by_genre():
    tragedy = []
    comedy = []
    phedre = []
    egiste = []
    for (k,v) in actors.items():
        if not v.get("personnage"):
            continue
        if "4" in v["personnage"]:
            phedre.append((k, v["text"]))
        if "254" in v["personnage"]:
            egiste.append((k,v["text"]))
        genres = list(set([roles[e]["genre"] for e in v["personnage"]]))
        if(len(genres)==1):
            if(genres[0]=='comédie'):
                comedy.append(v["text"])
            elif(genres[0]=="tragédie"):
                tragedy.append(v["text"])

        trag_vec = normalized_vector(make_freq_vec(make_bow(tragedy)))
        com_vec = normalized_vector(make_freq_vec(make_bow(comedy)))
        #usually it's interesting to look at diff, but this time, onlu consider the intersection (b/c so may of the unique genre words are just character names)
        words = set(set(trag_vec.keys()).intersection(set(com_vec.keys())))
        writer = csv.writer(open("results/freq_comp_genre.csv", 'w'))
        writer.writerow(["word", "comédie", "tragédie"])
        for w in words:
            writer.writerow([w, com_vec[w] if com_vec.get(w) else 0, trag_vec[w] if trag_vec.get(w) else 0])

        writer= csv.writer(open("results/phèdre.csv", "w"))
        writer.writerow(["year", "pseudonym", "text"])
        for elem in phedre:
            writer.writerow([actors[elem[0]]["year"],actors[elem[0]]["pseudonym"], elem[1]] )

        writer= csv.writer(open("results/égiste.csv", "w"))
        writer.writerow(["year", "pseudonym", "text"] )
        for elem in egiste:
            writer.writerow([actors[elem[0]]["year"],actors[elem[0]]["pseudonym"], elem[1]] )





def main():
    report()
    basics()
    editor_report()
    timeline_report()
    entity_report()
    by_genre()


main()
