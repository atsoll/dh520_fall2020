#misc code to generate graphs

import matplotlib.pyplot as plt
import csv
import os



def chron_graph():
    plt.style.use('seaborn-darkgrid')
    chron_reader = csv.reader(open("results/mention_chronology.csv"))
    plt.xlim(1,30)
    plt.ylim(0,45)
    plt.xlabel("Years into career")
    plt.ylabel("Mentions")
    x = [int(x) for x in next(chron_reader)[2:]]
    for row in chron_reader:
      y=[int(y) for y in row[2:]]
      color = 'b' if row[1]=='F' else 'r'
      plt.plot(x,y,color, linewidth=0.7, alpha=0.9)
    fig = plt.gcf()
    fig.set_size_inches(16, 6)
    plt.savefig("results/mention_chronology.png")
    plt.close()

def activity_graphs():


    for obj in os.listdir("results"):
        plt.style.use('seaborn-darkgrid')
        if os.path.isdir("results/"+ obj):
            reader = csv.reader(open("results/{}/activity_comp.csv".format(obj)))
            next(reader)
            fig, (reps, rev, men) = plt.subplots(1, 3, sharex=True)
            plt.locator_params(axis="x", integer=True)
            reps.set_ylabel("number of performances")
            rev.set_ylabel("total performance revenue (livres)")
            men.set_ylabel("press mentions")
            x = []
            y_reps = []
            y_rev= []
            y_men = []
            for row in reader:
                x.append(int(row[0]))
                y_reps.append(int(row[1]))
                y_rev.append(int(row[2]))
                y_men.append(int(row[3]))
            reps.plot(x,y_reps)
            rev.plot(x,y_rev)
            men.plot(x,y_men)
            fig.set_size_inches(16, 6)
            fig.tight_layout()
            plt.savefig("results/{}/activity.png".format(obj))
            plt.close()

chron_graph()
#activity_graphs()
