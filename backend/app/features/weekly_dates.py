from datetime import date, time, datetime, timedelta, timezone

#setting this semester's start
teaching_start = "2026-09-07"
teaching_end = "2026-11-27"


"""This function belongs to endpoint GET /weeks. its purpose is to calculate the monday dates 
   of every week in the current semester to avoid  storing them in the DB or querying Redbrick's API
   whenever a user clicks the dates for the weekly in the frontend, this returns the weekly dates
"""

def get_monday_dates():
    #get the start and end of the teaching period on date object
    start = date.fromisoformat(teaching_start)
    end = date.fromisoformat(teaching_end)

    mondays = [] #store the dates here

    #calculate the date of the next monday
    currentMonday = start + timedelta(
        days=(7 - start.weekday()) % 7
    )

    #while current monday does not pass end
    while currentMonday <= end:
        friday = min(currentMonday + timedelta(days=4), end) #calculate fridays

        mondays.append({"label": currentMonday.strftime("%A, %d %B %Y"), #convert date object to string: week day name, day number, month, year  
                        "start": f"{currentMonday.isoformat()}T00:00:00Z",
                        "end": f"{friday.isoformat()}T23:59:59Z"})

        currentMonday += timedelta(days=7) #move to the next monday

    return mondays


if __name__ == "__main__":
    for row in get_monday_dates():
        print(row)