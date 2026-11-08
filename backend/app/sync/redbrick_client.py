import requests

"""function that supports event requests to Redbrick's API
   this function is used by features:
   - A: to get weekly timetables and provide access to tools for its features
   - B: to access daily events for a given location 
   - C: to get info from lecturer's timetables? Need to check. 
"""
def fetch_timetable_events(url, start, end):
    headers = {
        "accept": '*/*',
        "media-type": "application/json"
    }

    response = requests.get(
        url,
        headers=headers,
        params={
            "start": start,
            "end": end
        },
        timeout=15)
    
    response.raise_for_status()
    return response.json() #turning the response into a dictionary

if __name__ == "__main__":
    for line in fetch_timetable_events("https://timetable.redbrick.dcu.ie/api/v3/timetable/category/course/items/0b5f2026-989f-0035-5e70-b86354e625a8/events", "2026-11-02T00:00:00Z", "2026-11-06T23:59:59Z"):
        print(line)