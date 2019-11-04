# Moduls
import requests
import os
import json
#++++folder migrait process++++++
#upload response in file
response = requests.get('http://admin:admin@localhost:3000/api/folders')
with open('response_folder.json', 'w') as outfile:
    outfile.write(response.content)

#parsing file
items = open('response_folder.json')
data = json.load(items)
items.close()
length = len(data)
print length
i = 0
while i < length:
    id = data[i]['id']
    title =  data[i]['title']
    uid = data[i]['uid']
    i+=1
    #create new items in grafana
    headers = {'Content-Type': 'application/json',}
    data_items = '{  "uid": "'+uid+'", "title": "'+title+'"}'
    response = requests.post('http://admin:admin@localhost:3001/api/folders', headers=headers, data=data_items)
    if response.status_code == 200:
        print ( title, "Create folder" )
    else:
        print ( "Can't create folder", title, response )

#++++Teams migrait process++++++
#Get team
i=1
while i < 100:
#    data_teams = '{"message": "0"}'
#    data_teams["message"] = 0
    url = ('http://admin:admin@localhost:3000/api/teams/'+str(i))
    response = requests.get(url)
    #Get team name
    data_teams = json.loads(response.content)
    data_teams_test = data_teams.values()
    if data_teams_test[0] == "Team not found":
        print ("Team not found")
    else:
        name = data_teams["name"]
        #create new items in grafana
        headers = {'Content-Type': 'application/json',}
        data_team_name = '{"name": "'+name+'"}'
        response = requests.post('http://admin:admin@localhost:3001/api/teams', headers=headers, data=data_team_name)
        if response.status_code == 200:
            print ( "Create team", name)
        else:
            print ( "Can't create team", response )
    i+=1

print ("final")
