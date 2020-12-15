#misc things for legacy
#do trajectory graph for mentions (like for careers)
#make node-link graph for interactions

import matplotlib.pyplot as plt
import csv
import os
import networkx as nx



def chron_graph():
    plt.style.use('seaborn-darkgrid')
    chron_reader = csv.reader(open("results/mention_chronology.csv"))
    plt.xlabel("Years after departure/death")
    plt.ylabel("Mentions")
    plt.xlim(1,35)
    plt.ylim(0,10.5)
    x = [int(x) for x in next(chron_reader)[2:]]
    for row in chron_reader:
      y=[int(y) for y in row[2:]]
      color = 'b' if row[1]=='F' else 'r'
      plt.plot(x,y,color, linewidth=0.7, alpha=0.9)
    fig = plt.gcf()
    fig.set_size_inches(16, 6)
    plt.savefig("results/mention_chronology.png")
    plt.close()


def count_vectorize(l):
    res = {}
    for elem in l:
        if res.get(elem):
            res[elem] += 1
        else:
            res[elem]=1
    return res

#get things ready for graphing software
#this is the point where I regret using .txt files
#knew it would happen eventually
def actor_clusters():
    edge_pairs = {}
    distinct_n = set()
    for elem in os.listdir('results'):
        if 'entities' in elem:
            lines = open("results/"+elem).readlines()
            for l in lines[2:]:
                sp = l.split(':')
                if(len(sp)==1):
                    break
                #make sure order isn't affecting anything
                n = elem.split("_")[0]
                distinct_n.add(n)
                n2 = sp[1].strip()
                distinct_n.add(n2)
                pair = (min(n2, n), max(n2, n))
                if(edge_pairs.get(pair)):
                    edge_pairs[pair] += int(sp[0])
                else:
                    edge_pairs[pair] = int(sp[0])

    G=nx.Graph()
    G.add_nodes_from(list(distinct_n))
    for k,v in edge_pairs.items():
        G.add_edge(k[0], k[1], weight=v)
    nx.draw(G,font_size=5, with_labels=True)
    fig = plt.gcf()
    fig.set_size_inches(16, 16)
    plt.savefig("results/interaction_graph.png")

chron_graph()
actor_clusters()
