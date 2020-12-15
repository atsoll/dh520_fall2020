import requests
from lxml import etree
import json
import os
import re

ns={'w': 'http://www.w3.org/1999/xhtml'}
#basically, just grab all the instances of them being mentioned, partitioned by year, and save it to a json object
#just for the sake of ease, do plaintext and xml rep


def fetchDocuments():
  docs = None
  res_list = []
  #this is terrible error handling, but if something goes wrong with this then I'm already in deep shit so...
  try:
    resp = requests.get("https://api-encodage.cfregisters.org/docs")
    docs = resp.json()
  except Exception(e):
    print(e)
    exit()
  doc_dict = {}
  for elem in docs:
      if 'mercure' in elem["name"].lower():
          y = int(re.findall("\d{4}", elem["name"])[0])
          #this one will be only 65-93 so that I can track their careers through the feux
          if(y<1794 and y>1764):
              doc_dict[y] = {"id":elem["id"], "xml":elem["content"], "name":elem["name"]}
  f = open("documents.json", 'w', encoding="utf-16")
  f.write(json.dumps(doc_dict))

#a helper for year logic
def checkDoc(year, actor):
    if (actor["debut"] is None or len(actor["debut"])==0)  and actor["entree"] is None:
        return True
    if(actor["depart"]):
        if year > actor["depart"]:
            return False
    fy = actor["entree"] if actor["entree"] is not None else actor["debut"][0]
    if(year < fy):
        return False
    return True

def getIndexList(mentions, parent):
    res = []
    for item in mentions:
        while(item.getparent()!=parent):
            item = item.getparent()
        res.append(parent.index(item))
    return res
#this time, just grab the actors from the feux graph
#since that api already does the work of filtering the list to include only folks who are actually in the feux
#this will also be useful in analysis for identifying exclusions (way more important here than with debuts)
def extractActorData(docs):
    #some more appallingly bad error checking
    #because, likewise, if this doesn't work, I am in trouble
    actors = None
    try:
      resp = requests.get("https://graph-api.cfregisters.org/actors")
      #only keep sociétaires - they're the ones likely to be consistenly mentioned
      actors = list(filter(lambda a: a.get("status_osp") and 'S' in a["status_osp"],resp.json()))
    except Exception as e:
      print(e)
      exit()
    #top level dict: actors ids
    #each value is a dict where the keys are years and the values are text
    data = {a["id"]: {} for a in actors}
    #iterate over years as an outside loop so it doesn't double up on costly conversions
    for y in list(docs.keys()):
        tmp_tree = etree.fromstring(docs[y]["xml"])
        for a in actors:
            if(checkDoc(int(y),a)):
                s_id = str(a["id"])
                #extract all of the mentions
                #sometimes all this will be is a character they played
                mentions =  [elem for elem in tmp_tree.findall(".//w:comedien", ns) if elem.get("id")==s_id]
                if(len(mentions) > 0):
                    data[a["id"]][y]=[]
                    for m in mentions:
                        p = m.getparent()
                        child=m
                        while(p.tag!="{http://www.w3.org/1999/xhtml}p"):
                            child=p
                            p=p.getparent()

                        #move forward and backward through parent siblings until hitting another actor
                        loc = p.index(child)
                        act = getIndexList([pa for pa in p.findall(".//w:comedien", ns)], p)
                        ind = act.index(loc)
                        start = 0 if ind==0 else act[ind-1] + 1
                        end = len(p)-1 if ind==len(act)-1 else act[ind + 1]-1
                        s = etree.Element("mention")
                        for e in (p[start:end+1]):
                            s.append(e)
                        data[a["id"]][y].append({"xml":etree.tostring(s, pretty_print=True).decode(), "plaintext":re.sub(r'<(.+?)>', " ", re.sub(r'&#\d{3,4};', lambda x: chr(int(x[0][2:-1])) , etree.tostring(s).decode())).replace("&amp;", "&").strip()})
    return data



def main():
    if not os.path.exists("documents.json"):
        fetchDocuments()
    d = json.loads(open("documents.json", encoding="utf-16").read())
    actor_data = extractActorData(d)
    if not os.path.exists("career_data"):
        os.mkdir("career_data")
        os.chdir("career_data")
        for a_id in actor_data.keys():
            if len(actor_data[a_id])>0:
                with open(str(a_id) + ".json", 'w') as f:
                    f.write(json.dumps(actor_data[a_id]))

main()
