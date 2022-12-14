from colorama                   import Fore, Back, Style
from magic                      import Magic
from time                       import sleep
import json,csv,sys,os,linecache,PyPDF2 

keywords = []
with open("misc/keywords.csv") as csv_file:
    csv_reader = csv.reader(csv_file, delimiter=',')
    line_count = 0
    for row in csv_reader:
        if line_count <= 0:
            line_count += 1
        else:
            keywords.append(row[0].split("+"))

keywords = list(set([i for l in keywords for i in l]))
keywords.sort()
keywords.reverse()

dois = {}
with open("misc/tokens.csv") as csv_file:
    csv_reader = csv.reader(csv_file, delimiter=',')
    line_count = 0
    for row in csv_reader:
        if line_count <= 0:
            line_count += 1
        else:
            dois[row[0]] = row[1]

mime = Magic(mime=True)

def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    filename = f.f_code.co_filename
    linecache.checkcache(filename)
    line = linecache.getline(filename, lineno, f.f_globals)
    print('{}{}:{}{} {}'.format(Fore.RED, filename.split("/")[-1], lineno, Style.RESET_ALL, exc_obj))

def parse_journals(file):
    papers = {}
    processed = []
    for token in keywords:
        with open(file) as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=',')
            line_count = 0
            result_count = 0
            for row in csv_reader:
                if line_count <= 0:
                    line_count += 1
                else:
                    print(f"{Fore.CYAN}Querying journal {row[3]}:{Style.RESET_ALL} {token}")
                    succeeded = False

                    # check if results are cached
                    for issn in row[2].split(", "):
                        fn = f"json/journals/{issn}-{token}.json"
                        if os.path.exists(fn) and os.stat(fn).st_size > 1:
                            with open(fn) as i:
                                try:
                                    j = json.load(i)
                                    count = len(j)
                                    print("{}Found cached: {}{} {}".format(Fore.GREEN,issn,Style.RESET_ALL,count))
                                    succeeded = True


                                    # Analyse the thing here:

                                    for item in j:
                                        if item["DOI"] in dois.keys() and item["DOI"] not in processed:
                                            result_count += 1

                                            journal = "_".join(str.lower(row[3]).split(" "))
                                            title = "-".join(str.lower(item["DOI"]).split("/"))
                                            pfn = f"./pdfs/{journal}/{title}.pdf"
                                            num_pages = "-"
                                            if os.path.exists(pfn) and os.stat(pfn).st_size > 1:
                                                if mime.from_file(pfn) == "application/pdf":
                                                    sci_stat = "0: Downloaded"
                                                    num_pages = PyPDF2.PdfFileReader(open(pfn,"rb")).numPages
                                                else:
                                                    sci_stat = "1: Not found"
                                            else:
                                                sci_stat = "2: DOI not reckoned"

                                            funders = " "
                                            if "funder" in list(item.keys()):
                                                funder = []
                                                for f in item["funder"]:
                                                    if "DOI" in list(f.keys()):
                                                        funder.append(f"{f['name']} ({f['DOI']})")
                                                    else:
                                                        funder.append(f['name'])
                                                funders = "\n".join(funder)

                                            authors = " "
                                            if "author" in list(item.keys()):
                                                author = []
                                                for a in item["author"]:

                                                    if "given" in list(a.keys()) and "family" in list(a.keys()):
                                                        nam = f"{a['family']}, {a['given']}"
                                                    elif "given" in list(a.keys()):
                                                        nam = a["given"]
                                                    elif "family" in list(a.keys()):
                                                        nam = a["family"]
                                                    else:
                                                        nam = ""

                                                    affies = ""
                                                    if "affiliation" in list(a.keys()) and len(a["affiliation"])>0:
                                                        affies = " ({})".format("; ".join([x["name"] for x in a["affiliation"]]))

                                                    author.append(f"{nam}{affies}")

                                                authors = "\n".join(author)

                                            licenses = " "
                                            if "license" in list(item.keys()):
                                                licenses = "\n".join([f"{str.upper(x['content-version'])} {x['start']['date-time'].split('T')[0]} ({x['URL']})" for x in item["license"]]),
                                            lang = " "
                                            if "language" in list(item.keys()):
                                                lang = str.upper(item["language"])
                                            paper = {
                                                        "DOI": item["DOI"],
                                                        "Title": "\n".join([x for x in item["title"]]),
                                                        "Subject (Tags)": "\n".join([x for x in item["subject"]]),
                                                        "Authors": authors,
                                                        "Funders": funders,
                                                        "License": licenses,
                                                        "ISSN": issn,
                                                        "Journal": "\n".join([x for x in item["container-title"]]),
                                                        "List": row[0],
                                                        "Query match": dois[item["DOI"]],
                                                        "References": item["references-count"],
                                                        "Referenced": item["is-referenced-by-count"],
                                                        "Publisher": item["publisher"],
                                                        "Published": "-".join([str(x) for x in item["published"]["date-parts"][0]]),
                                                        "Language": lang,
                                                        "Sci-Hub Status": sci_stat,
                                                        "Pages": num_pages,
                                                        "Abstract": "",
                                                        "Conflict of Interest": ""
                                                    }
                                            jfn = f"grobid/{journal}/{title}.json"
                                            if os.path.exists(jfn) and os.stat(jfn).st_size > 1:
                                                with open(jfn) as ii:
                                                    jj = json.load(ii)
                                                    paper["Abstract"] = jj["abstract"]
                                                    coi = []
                                                    for para in jj["pdf_parse"]["back_matter"]:
                                                        coi.append(f"{para['section']}\n{para['text']}")
                                                    paper["Conflict of Interest"] = "\n\n".join(coi)

                                            papers[item["DOI"]] = paper
                                            processed.append(item["DOI"])
                                except:
                                    succeeded = False
                                    PrintException()
                    line_count += 1

            print(f"Found {result_count} results.")

    with open('misc/papers.csv', 'w') as outfile:
        writer = csv.writer(outfile)
        writer.writerow(list(list(papers.values())[0].keys()))
        for doi in dois.keys():
            writer.writerow(list(papers[doi].values()))
    

#journals.query('Cadernos')
parse_journals('misc/journals.csv')
