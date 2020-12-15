import requests
import re
from lxml import etree
import json
import os
import csv


BASE_URL = "https://api-encodage.cfregisters.org/"
ns={'w': 'http://www.w3.org/1999/xhtml'}
prefix = "{http://www.w3.org/1999/xhtml}"


def fetchDocuments():
  docs = None
  res_list = []
  #this is terrible error handling, but if something goes wrong with this then I'm already in deep shit so...
  try:
    resp = requests.get(BASE_URL + "docs")
    docs = resp.json()
  except Exception as e:
    print(e)
    exit()
  #loop through docs, drop the ones we don't care about, pull out only the important shit, parse the xml
  doc_dict = {}
  for elem in docs:
      if 'mercure' in elem["name"].lower():
          y = int(re.findall("\d{4}", elem["name"])[0])
          if(y<1794 and y>1748):
              doc_dict[str(y)] = {"id":elem["id"], "xml":elem["content"], "name":elem["name"]}
  f = open("documents.json", 'w', encoding="utf-16")
  f.write(json.dumps(doc_dict))

def extractActorData():
    data = open("documents.json").read()
    doc_list = json.loads(data)
    actors = [a for a in csv.DictReader(open("actors.csv", 'r', encoding="utf16"))]
    mentions = []
    for a in actors:
        fy = int(a["first_date"])
        #sometimes, like with bellecour for example, they officially joined in december but didn't appear in the press until january
        #so if they don't show up in the first year, look one further (hence the loop)
        for y in range(fy,fy+2):
            if(y>1793 or y<1749 ):
                continue
            rel_doc = doc_list[str(y)]
            tree = etree.fromstring(rel_doc["xml"])
            mentions = [elem for elem in tree.findall(".//w:comedien", ns) if elem.get("id")==a["id"]]
            if(len(mentions) > 0):
                break
        #take a step back and grab the outer paragraph, and the following one if need be (provided it doesn't mention other people)
        if(len(mentions) > 0):
            #they describe them the first time they were mentioned
            #we don't care about after that
            #it's usually just roles they played
            elem = mentions[0]
            parent = elem.getparent()
            while(parent.tag != prefix+'p'):
                parent = parent.getparent()
            #parent holds the main paragraph
            #but we also want to look at the next paragraph, so long as it doesn't mention other actors??
            #also skip the next one and move onto its sibling if ot starts with [note]
            stop = False
            iter = 1
            for next in parent.itersiblings():
                #don't bother if it's the start of a new section
                if next.tag != prefix + 'p':
                    break
                if(iter>= 2):
                    break
                #this skips notes and sectionbreaks
                if((next.text or len(next)>0) and not (next.text and next.text.strip().startswith("["))):
                    #look through an keep everyhting until finding another actor
                    #this obviously isn't entirely foolproof but hey
                    #note that it doesn't preserve paragraph structure
                    iter +=1
                    if next.text:
                        if(len(parent)>0):
                            parent[-1].tail =  next.text if parent[-1].tail==None else parent[-1].tail + " " + next.text
                        else:
                            parent.text += " " + next.text
                    for elem in next:
                        if (elem.tag==prefix + "comedien") or (len(elem) > 0 and elem[0].tag==prefix + "comedien"):
                            break
                        parent.append(elem)
            #do something with the monster paragraph
            outfile = open("./debut_data/" + a["id"] + ".json", 'w' )
            #having the year will be useful
            person_data = {"year": str(y)}
            #write out the xml so it can be reconstituted at need
            person_data["xml"]= etree.tostring(parent).decode()
            #write out a nice neatened up text only version
            #the stupid etree doesn't play well with differebt encodings so there's some fancy regex instead
            person_data["plaintext"] = re.sub(r'<(.+?)>', " ", re.sub(r'&#\d{3,4};', lambda x: chr(int(x[0][2:-1])) , etree.tostring(parent).decode())).replace("&amp;", "&").strip()
            outfile.write(json.dumps(person_data))
            outfile.close()


def main():
    if not os.path.exists("documents.json"):
        fetchDocuments()
    if not os.path.exists("debut_data"):
        os.mkdir("debut_data")
        extractActorData()

main()
