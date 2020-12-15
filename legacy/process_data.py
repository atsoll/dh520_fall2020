import json
from lxml import etree
import os
import requests
import re
import csv

#this one can span all of the possible years
#but also only really works for sociétaires (and a few pensionnaires) because they're the only ones we have departure dates for
#frankly that's ok though as it's super unlikely that a occasionnel would be held up as a comparison

ns={'w': 'http://www.w3.org/1999/xhtml'}
prefix = "{http://www.w3.org/1999/xhtml}"


def fetchDocuments():
  docs = None
  res_list = []
  #this is terrible error handling, but if something goes wrong with this then I'm already in deep shit so...
  try:
    resp = requests.get("https://api-encodage.cfregisters.org/docs")
    docs = resp.json()
  except Exception as e:
    print(e)
    exit()
  doc_dict = {}
  for elem in docs:
      if 'mercure' in elem["name"].lower():
          y = int(re.findall("\d{4}", elem["name"])[0])
          if(y<1794 and y>1748):
              doc_dict[y] = {"id":elem["id"], "xml":elem["content"], "name":elem["name"]}
  f = open("documents.json", 'w', encoding="utf-16")
  f.write(json.dumps(doc_dict))

def getTextObj(xml):
    encoded = etree.tostring(xml).decode()
    plain = re.sub(r'<(.+?)>', " ", re.sub(r'&#\d{3,4};', lambda x: chr(int(x[0][2:-1])) , encoded)).replace("&amp;", "&").strip()
    return {"xml":encoded, "plaintext":plain}

#again, it was easier to just use a csv, though obviously I could have grabbed it from the feux api
#after getting the data, look through documents for mentions of them *after* they've died/retired
#this time, since it *is* interesting to see who/what they are mentioned in conjuction with, back up to paragraph level, with no redaction
def extractData(doc_list):
    actors = [a for a in csv.DictReader(open("actors.csv", 'r', encoding="utf16"))]
    #nearly identical structure to the career data
    data = {a["id"]:{} for a in actors}
    #iterate over years, with actors as the inner loop (even though the reverse seems a bit more natural...) so as not to constantly be parsing xml
    for y in list(map(lambda d : int(d), doc_list.keys())):
        tmp_tree = etree.fromstring(doc_list[str(y)]["xml"])
    #for each actor, look for mentions in documents starting a year after their departure
        for a in actors:
            if(y>int(a["depart"])):
                #just so as not to repeat the casting
                s_id = str(a["id"])
                mentions =  [elem for elem in tmp_tree.findall(".//w:comedien", ns) if elem.get("id")==s_id]
                #only bother if there's something there
                if(len(mentions)>0):
                    #Since we're backtracking to paragraph level I only want unique ones
                    res_list = set()
                    for m in mentions:
                        parent = m.getparent()
                        while(parent.tag!= prefix + "p"):
                            parent = parent.getparent()
                        res_list.add(parent)
                    #despite removing duplicates, I still want to be able to track the number of discrete mentions
                    data[a["id"]][y] = {"mentions": len(mentions), "data":list(map(getTextObj, res_list))}
    return data




def main():
    if not os.path.exists("documents.json"):
        fetchDocuments()
    d = json.loads(open("documents.json", encoding="utf-16").read())
    if not os.path.exists("legacy_data"):
        actor_data = extractData(d)
        os.mkdir("legacy_data")
        os.chdir("legacy_data")
        for a_id in actor_data.keys():
            if len(actor_data[a_id])>0:
                with open(str(a_id) + ".json", 'w') as f:
                    f.write(json.dumps(actor_data[a_id]))

main()
