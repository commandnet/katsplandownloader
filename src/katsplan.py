import requests
import logging
import re
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json
class api():
    
    token = ""
    files = []
    username =""
    password = ""
    org = ""

    def __init__(self, username, password, org):
            self.username = username
            self.password = password
            self.org = org
            self.login()
            pass

    def login(self):    
        resp = requests.post(url="https://www.kats-plan.de/%s/api/graphql/login" % self.org,data={
            "username": self.username,
            "password": self.password
        })
        self.token = resp.text

    def get_graphql(self,operationName ="", query ="", variables=False):

        if variables:
            json_r = {
                "operationName": operationName,
                "query": query,
                "variables": variables
            }
        else:
            json_r = {
                "operationName": operationName,
                "query": query,
            }

        resp = requests.post(url="https://www.kats-plan.de/%s/api/graphql" % self.org, json=json_r, headers={
             'authorization': "Bearer %s" % (self.token),
             'content-type': "application/json",
             "Accept-Encoding": "gzip, deflate, br, zstd",
             "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:140.0) Gecko/20100101 Firefox/140.0"
        })
        resp.encoding = 'utf-8' 

        if resp.status_code != 200:
            raise Exception("Failed to get graphql: %s" %resp.text)
        else:
            return resp.json()["data"]
    
    def get_root_trees(self):
        return self.get_graphql(
            operationName="getTrees",
            query="query getTrees {\n trees {\n id\n createDate\n ...Tree\n __typename\n }\n}\n\nfragment Tree on TreeType {\n id\n name\n description\n __typename\n}\n"
        )["trees"]

    trees = {}
    branches = []
    def get_branches(self, tree_id):
        self.branches = self.get_branches_with_details(tree_id=tree_id)
        return self._generate_html()

    def get_branches_with_details(self, tree_id):
        query = """
        query branchesWithDetails($treeId: Int!) {
        branches(treeId: $treeId) {
            id
            name
            treeId
            codeNumber
            changeDateStr
            createDateStr
            isLocked
            empty
            parentId
            weighting
            permissions {
            update
            }
            directChildren {
            id
            }
            texts {
            id
            title
            content
            weightings {
                branchId
                myWeighting
            }
            }
            links {
            id
            title
            description
            url
            changeDateStr
            createDateStr
            }
            images {
            id
            title
            description
            url
            changeDateStr
            createDateStr
            }
            files {
            id
            title
            type
            description
            url
            createDateStr
            changeDateStr
            }
            contacts {
            id
            prename
            surname
            company
            latitude
            longitude
            contactType
            phone
            email
            subcontacts {
                id
                latitude
                longitude
                contactType
            }
            }
        }
        }
        """

        result = self.get_graphql(
            operationName="branchesWithDetails",
            query=query,
            variables={"treeId": tree_id}
        )

        return result["branches"]

    def _render_branch(self, branch_id ):
        html = ""

        for branch in sorted(self.branches, key=lambda x: self.parse_code_number(x["codeNumber"])):
            if branch["parentId"] == None:
                branch["parentId"] = -1

            if int(branch["parentId"]) == branch_id and branch["empty"] != True:
                html += f"<ul><a href='branch_{branch['id']}.html'>{branch['codeNumber']}. {branch['name']}</a>"
                html += self._render_branch(branch_id=branch['id'])
                self.get_branch(branch['id'])
                html += "</ul>\n"

        return html

    def _generate_html(self):
        html_output = self._render_branch(branch_id=-1)
        return html_output
    
    def parse_code_number(self,code):
        """Parst codeNumber in eine Liste von Zahlen zur korrekten Sortierung"""
        parts = re.findall(r'\d+', code)
        return [int(part) for part in parts]
    
    def get_branch(self, branch_id):

        for branch in self.branches:
            if branch["id"] == branch_id:
            
                with open("content/branch_%s.html" % (branch_id), "w", encoding="utf-8") as f:
                    f.write("<!DOCTYPE html>\n<html>\n<head>\n<meta charset='UTF-8'>\n</head>\n<body>\n")
                    f.write("<h1>%s - %s</h1>" % (branch["codeNumber"],branch["name"]))
                    for text in branch["texts"]:
                        f.write("<h2>%s</h2>" % (text["title"]))
                        f.write(text["content"])

                    if len(branch["files"]) > 0:
                        f.write("<h2>%s</h2>" % ("Datein"))

                    for file in branch["files"]:
                        if len(file["type"]) == 0:
                            file["type"] = "pdf"
                        self.add_download_file(file)
                        f.write("<a href='%s.%s'><p>%s - %s (%s)</p></a>" % (file["url"],file["type"],file["title"],file["description"],file["type"]))

                    if len(branch["contacts"]) > 0:
                        f.write("<h2>%s</h2>" % ("Kontakte"))
                        for contact in branch["contacts"]:
                            f.write("<table border=\"1\" width=\"100%\">")
                            f.write("<tr>")
                            f.write("<td colspan=\"4\">%s</td>" % contact["company"])
                            f.write("</tr>")
                            f.write("<tr>")
                            f.write("<td>Vorname:</td><td>%s</td><td>Nachname:</td><td>%s</td>" % (contact["prename"],contact["surname"]))
                            f.write("</tr>")
                            f.write("<tr>")
                            f.write("<td>LAT:</td><td>%s</td><td>LON:</td><td>%s</td>" % (contact["latitude"],contact["longitude"]))
                            f.write("</tr>")
                            f.write("<tr>")
                            f.write("<td>Email:</td><td>%s</td><td>phone:</td><td>%s</td>" % (contact["email"],contact["phone"]))
                            f.write("</tr>")
                            f.write("</table>")


    def add_download_file(self,file):
        logging.debug("adding file %s" % file)
        self.files.append(file)

    def download_files(self):
        for file in self.files:
            self.download_file(file)

    def download_file(self,file):
        url = f"https://www.kats-plan.de/{self.org}/api/graphql/download?fileid={file['url']}&token={self.token}"
        local_path = f"content/{file['url']}.{file['type']}"

        session = requests.Session()
        retry = Retry(
            total=5,  # Anzahl der Versuche
            backoff_factor=1,  # Sek. zwischen den Versuchen (exponentiell steigend)
            status_forcelist=[429, 500, 502, 503, 504],
            raise_on_status=False
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('https://', adapter)
        session.mount('http://', adapter)

        try:
            response = session.get(url, allow_redirects=True, timeout=10)
            response.raise_for_status()
            with open(local_path, 'wb') as f:
                f.write(response.content)
            logging.info(f"downloaded: {local_path}")
        except requests.exceptions.RequestException as e:
            logging.error(f"download failure: {e}")
                        