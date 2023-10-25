import requests, time

while True: 
    r =requests.get('http://kpupd.herokuapp.com') 
    #print(r.text) 
    print(r.status_code) 
    time.sleep(3500)
