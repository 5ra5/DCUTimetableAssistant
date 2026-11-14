from datetime import datetime

"""these are the tools that the Ollama LLM 
and the agent can have access to provide the 
weekly analysis for Feature A. Note that these 
tools receive the validated weekly_events list produced
by get_weekly_timetable() in weekly_calendar.py.
"""

"""get_daily_breakdown() returns the number of events that happen everyday such as
- labs
- lectures
- tutorials
- the total number of events per day (all events combined)
- total hours of events per day (all events combined)
- the time of the 1st class of the day 
- the time of the last class of the day"""

def get_daily_breakdown(weekly_events: list) -> dict:
    """Analyse the daily breakdown of a student's weekly timetable.
    
    The tool returns the number of lectures, labs, tutorials and other activities
    for each weekday, the total number of scheduled events, total scheduled hours,
    first class start time and last class end time

    Args:
        weekly_events: List of dictionaries containing events. 
                       Each event contains: 
                                        'module_name1' 
                                        'module_name2': 
                                        'location'
                                        'long_description'
                                        'short_description'
                                        'start'
                                        'end'
                       Example: [{'module_name1': 'CSC1042[1] Computer Networks 2', 
                                  'module_name2': 'CSC1042 Computer Networks 2 (Lecture)', 
                                  'location': 'FTG11', 
                                  'long_description': 'Lecture, On Campus', 
                                  'short_description': 'Lecture', 
                                  'start': '2026-11-02T09:00:00Z', 
                                  'end': '2026-11-02T11:00:00Z'}].  
    Returns:
        Dictionary keyed by weekday, containing the corresponding daily timetable statistics.
        Example:
                {
                    "Monday": {
                        "lecture": 5,
                        "total_daily_events": 5,
                        "total_scheduled_hours": 6.0,
                        "first_class": "09:00",
                        "last_class": "17:00"
                    },
                    "Tuesday": {
                        "lab": 1,
                        "lecture": 2,
                        "total_daily_events": 3,
                        "total_scheduled_hours": 4.0,
                        "first_class": "11:00",
                        "last_class": "16:00"
                    },
                    "Wednesday": {
                        "lecture": 3,
                        "tutorial": 1,
                        "lab": 1,
                        "total_daily_events": 5,
                        "total_scheduled_hours": 7.0,
                        "first_class": "09:00",
                        "last_class": "18:00"
                    },
                    "Thursday": {
                        "lecture": 1,
                        "lab": 1,
                        "total_daily_events": 2,
                        "total_scheduled_hours": 3.0,
                        "first_class": "10:00",
                        "last_class": "15:00"
                    },
                    "Friday": {
                        "total_daily_events": 0,
                        "total_scheduled_hours": 0,
                        "first_class": None,
                        "last_class": None
                    }
                }"""
    
    days_to_event = get_events_per_day(weekly_events) 
    results = dict() #final dictionary with results

    #for each day and the events of the corresponding day, get the:
    #- type of the event (lab, lecture, tutorial)
    #- total hours of events on that day
    #- first class of the day
    #- last class of the day  
    for day, events in days_to_event.items():
        event_types = {} 
        total_hours = 0
        first_class = None
        last_class = None
        #for every event of a particular day
        for event in events:
            #get the number of events in that day lecture, lab, tutorial etc etc
            long_description = event.get("long_description") or "Undetermined"
            activity = long_description.split(",")[0].strip().lower()

            if activity not in event_types:
                event_types[activity] = 0
            event_types[activity] += 1


            #getting the total hours on that day
            start = datetime.fromisoformat(event["start"]) #get the start time of the event in python datetime object year-month-day hour:minute:second+UTC ->  2026-11-04 09:00:00+00
            end = datetime.fromisoformat(event["end"]) #get the end time of the event in python datetime object year-month-day hour:minute:second+UTC ->  2026-11-04 09:00:00+00
            duration = (end -  start).total_seconds() / 3600 #calculate the entire event's duration based on start and end times and also turn that calculation into int to present the amount of hours
            total_hours += duration

            #getting the very first class and very last class
            if first_class is None or start < first_class:
                first_class = start

            if last_class is None or end > last_class:
                last_class = end

        
        event_types["total_daily_events"] = len(events)#total number of events per day
        event_types["total_scheduled_hours"] = total_hours #total hours per day
        
        if first_class:
            event_types["first_class"] = first_class.strftime("%H:%M") #formatting the datetime object into a string containing the hour and minute in 24 hour format from  2026-11-04 09:00:00+00 to 09:00 
        else: 
            event_types["first_class"] = None
        if last_class:
            event_types["last_class"] = last_class.strftime("%H:%M") #formatting the datetime object into a string containing the hour and minute in 24 hour format from  2026-11-04 09:00:00+00 to 09:00
        else:
            event_types["last_class"] = None
       
        results[day] = event_types #store the entire calculations of the events on this day to the corresponding day.

    return results


"""analyse_free_gaps(weekly_events) finds gaps between scheduled classes, it returns:
    - Total free-gap hours for each day
    - number of gaps in each day
    - Each day's gaps with their start time, end time, and duration.
    - The longest gap in the week. 
    its purpose is for the llm to suggest good times for studying, 
    taking breaks or completing assignments.
"""
def analyse_free_gaps(weekly_events: list) -> dict:
    """Find free gaps between scheduled classes in a weekly timetable.

    Calculates each weekday's total free gap hours, number of gaps,
    individual gap start and end times, and longest gap across the week.

    Use this tool when analysing free time between classes or identifying
    possible study breaks.

    Args:
        weekly_events: List of dictionaries containing events. 
                       Each event contains: 
                                        'module_name1' 
                                        'module_name2': 
                                        'location'
                                        'long_description'
                                        'short_description'
                                        'start'
                                        'end'
                       Example: [{'module_name1': 'CSC1042[1] Computer Networks 2', 
                                  'module_name2': 'CSC1042 Computer Networks 2 (Lecture)', 
                                  'location': 'FTG11', 
                                  'long_description': 'Lecture, On Campus', 
                                  'short_description': 'Lecture', 
                                  'start': '2026-11-02T09:00:00Z', 
                                  'end': '2026-11-02T11:00:00Z'}].  

    Returns:
        Dictionary containing daily gap information and longest_weekly_gap.
        Example: {
                    "Monday": {
                        "total_gaps_hours": 2.0,
                        "number_gaps": 2,
                        "individual_daily_gaps": {
                            "gap0": {
                                "gap_duration": 1.0,
                                "gap_start": "13:00",
                                "gap_end": "14:00"
                            },
                            "gap1": {
                                "gap_duration": 1.0,
                                "gap_start": "15:00",
                                "gap_end": "16:00"
                            }
                        }
                    },
                    "Tuesday": {
                        "total_gaps_hours": 1.0,
                        "number_gaps": 1,
                        "individual_daily_gaps": {
                            "gap0": {
                                "gap_duration": 1.0,
                                "gap_start": "13:00",
                                "gap_end": "14:00"
                            }
                        }
                    },
                    "Wednesday": {
                        "total_gaps_hours": 2.0,
                        "number_gaps": 2,
                        "individual_daily_gaps": {
                            "gap0": {
                                "gap_duration": 1.0,
                                "gap_start": "10:00",
                                "gap_end": "11:00"
                            },
                            "gap1": {
                                "gap_duration": 1.0,
                                "gap_start": "14:00",
                                "gap_end": "15:00"
                            }
                        }
                    },
                    "Thursday": {
                        "total_gaps_hours": 2.0,
                        "number_gaps": 1,
                        "individual_daily_gaps": {
                            "gap0": {
                                "gap_duration": 2.0,
                                "gap_start": "11:00",
                                "gap_end": "13:00"
                            }
                        }
                    },
                    "Friday": {
                        "total_gaps_hours": 0,
                        "number_gaps": 0,
                        "individual_daily_gaps": {}
                    },
                    "longest_weekly_gap": [
                        {
                            "day": "Thursday",
                            "gap_start": "11:00",
                            "gap_end": "13:00",
                            "gap_duration": 2.0
                        }
                    ]
                }
    """
    days_to_event = get_events_per_day(weekly_events) #get the timetable's events with the events divided from monday to friday
    results = {} #we store results here
    longest_gap = None #to track longest gap

    for day, events in days_to_event.items():  #for all events in every day
        events.sort(key=sortHelper)   #sort the events on the day based on their dates/times
        
        #all the variables below reset every new day
        all_gaps_info = {} #dictionary where to store the information about the gaps for each day
        total_gap_hours = 0 #adds all free hours for this day
        number_gaps = 0  #counts how many gaps have been found
        individual_daily_gaps = {} #dictonary where to store the details of each gap on a specific day

        if events: #if there are events scheduled on that day
            previous_end = datetime.fromisoformat(events[0]["end"]) #get the end time of the 1st event

            #for every event except the last one
            for i in range(len(events) - 1):
                #get the start and end times of the next event
                next_start = datetime.fromisoformat(events[i + 1]["start"]) 
                next_end = datetime.fromisoformat(events[i + 1]["end"])
                
                #calculcate a gap: if the next start time is later than the previous class end time -> there is a gap
                if next_start > previous_end:
                    gap_info = {} #where we store the information related to this specific gap
                    gap_duration = (next_start - previous_end).total_seconds() / 3600 #get the duration of this gap
                    gap_start = previous_end.strftime("%H:%M") #start time of this gap is the end of the last class
                    gap_end = next_start.strftime("%H:%M") #end time of this gap is the beginning of the next class
                    
                    #store the duration, start and end times of this gap
                    gap_info["gap_duration"] = gap_duration
                    gap_info["gap_start"] = gap_start
                    gap_info["gap_end"] = gap_end

                    #store this gap's information in the corresponding day that has it
                    individual_daily_gaps[f"gap{number_gaps}"] = gap_info
                    
                    #increment the overall gap hours of the day
                    total_gap_hours += gap_duration
                    #increment the number of gaps in the day
                    number_gaps += 1
                    
                    #calculate the longest gap in the week
                    if longest_gap is None or gap_duration > longest_gap[0]["gap_duration"]: #LUCERO: i assume [0] cux all element sin the lsit will have the same duration so it does not matter
                        longest_gap = [{
                            "day": day,
                            "gap_start": gap_start,
                            "gap_end": gap_end,
                            "gap_duration": gap_duration
                        }]
                    elif gap_duration == longest_gap[0]["gap_duration"]:
                        longest_gap.append({
                            "day": day,
                            "gap_start": gap_start,
                            "gap_end": gap_end,
                            "gap_duration": gap_duration
                        })

                #handling overlaping classes. Example: 
                # class a from 9 am to 12 am
                # class b from 10 am to 11 am
                # class c from 11:30 to 13 pm
                # class a continues until 12 even though class b finishes before class c. 
                #there is no gap. In this ase, previous end stays to be 12 until trader ending time comes. Because there are overlapping times.
                if next_end > previous_end:
                    previous_end = next_end
        #save  daily results 
        all_gaps_info["total_gaps_hours"] = total_gap_hours
        all_gaps_info["number_gaps"] = number_gaps
        all_gaps_info["individual_daily_gaps"] = individual_daily_gaps

        results[day] = all_gaps_info
    
    #adding the longest gap in the week to the results.
    results["longest_weekly_gap"] = longest_gap
    return results

"""analyse_class_patterns(weekly_events) finds weekly metrics, it returns:
    - The busiest days of the week
    - The lightest days of the week
    - Any free days in the week
    - The days that start the earliest in the week
    - The days that finish the latest in the week
    - The most common events in the week (meaning labs, lectures, etc)
"""
def analyse_class_patterns(weekly_events: list) -> dict:
    """Identify patterns across a student's weekly timetable.

    Finds the most common activity/event, busiest and lightest teaching days, 
    days without classes, earliest class starts, latest class finishes, and 
    most common activity types such as lectures, labs and tutorials.

    Use this tool for questions about weekly workload and class patterns.

    Args:
        weekly_events: List of dictionaries containing events. 
                       Each event contains: 
                                        'module_name1' 
                                        'module_name2': 
                                        'location'
                                        'long_description'
                                        'short_description'
                                        'start'
                                        'end'
                       Example: [{'module_name1': 'CSC1042[1] Computer Networks 2', 
                                  'module_name2': 'CSC1042 Computer Networks 2 (Lecture)', 
                                  'location': 'FTG11', 
                                  'long_description': 'Lecture, On Campus', 
                                  'short_description': 'Lecture', 
                                  'start': '2026-11-02T09:00:00Z', 
                                  'end': '2026-11-02T11:00:00Z'}].
    Returns:
        Dictionary containing weekly timetable patterns and statistics in the form
        The key values are:
                        'most_common_activity'
                        'busiest_day'
                        'lightest_day'
                        'days_without_classes'
                        'earliest_start'
                        'latest_finish'
        Example:
            {'most_common_activity': {'activities': ['lecture'], 'count': 11}, 
            'busiest_day': {'days': ['Wednesday'], 'scheduled_hours': 7.0}, 
            'lightest_day': {'days': ['Thursday'], 'scheduled_hours': 3.0}, 
            'days_without_classes': ['Friday'], 
            'earliest_start': {'days': ['Monday', 'Wednesday'], 'time': '09:00'}, 
            'latest_finish': {'days': ['Wednesday'], 'time': '18:00'}}
    """
    days_breakdown = get_daily_breakdown(weekly_events) #get the weekly breakdown

    results = {}

    #variable to store the busiest day    
    busiest_days = []
    most_hours = 0
    #variable to store the least busiest day
    lightest_days = []
    least_hours = None
    
    #variable to store free days
    free_days = []

    #variable to store the day that starts the earliest
    earliest_days = []
    earliest_time = None

    #variable to store the day that finishes the latest
    latest_days = []
    latest_time = None

    #most common events this week
    most_common_events = []

    #variable to store the weekly amount of lectures, labs, etc
    activity_counts = {}

    #for every day and its events
    for day, information in days_breakdown.items():
        #get the total number of hours scheduled for this day
        hours = information["total_scheduled_hours"]
        #get the 1st class of this day
        first_class = information["first_class"]
        #get the last class of this day
        last_class = information["last_class"]

        #if there are no hours this day (free day), add it to the free day list
        if hours == 0:
            free_days.append(day)

        if hours > 0:
            #get tje day of the week with the most hours
            if hours > most_hours:
                busiest_days = [day]
                most_hours = hours
            elif hours == most_hours:
                busiest_days.append(day)

            #get the day of the week with the least hours
            if least_hours is None or hours < least_hours:
                lightest_days = [day]
                least_hours = hours
            elif hours == least_hours:
                lightest_days.append(day)

        #get the earliest class throughout the week
        if first_class is not None:
            if earliest_time is None or first_class < earliest_time:
                earliest_time = first_class
                earliest_days = [day]
            elif first_class == earliest_time:
                earliest_days.append(day)

        #get the last class throughout the week
        if last_class is not None:
            if latest_time is None or last_class > latest_time:
                latest_time = last_class
                latest_days = [day]
            elif last_class == latest_time:
                latest_days.append(day)
        
        #get the number of lectures, labs, etc per week (not per day opposed to get_daily_breakdown())
        for activity, count in information.items(): #for each key and value of every event on each day, check if it is a lecture, lab, etc
            if activity not in ["total_daily_events", "total_scheduled_hours", "first_class", "last_class"]: #if it is a lecture, lab etc
                activity_counts[activity] = activity_counts.get(activity, 0) + count #add its count to the corresponding key

    #get the activity that happens the most in this week (lebs, lecture, etc)
    #if there multiple acitivies that happen the same number of times just add them to the list
    if activity_counts:
        highest_count = max(activity_counts.values()) #get the biggest count of events this week 
 
        for activity, count in activity_counts.items():
            if count == highest_count:
                most_common_events.append(activity)

        results["most_common_activity"] = {"activities": most_common_events, "count": highest_count}
    else:
        results["most_common_activity"] = None

    #store all calculations in results
    if busiest_days:
        results["busiest_day"] = {"days": busiest_days, "scheduled_hours":most_hours}
    else:
        results["busiest_day"] = None
    
    if lightest_days:
        results["lightest_day"] = {"days": lightest_days, "scheduled_hours":least_hours}
    else:
        results["lightest_day"] = None

    results["days_without_classes"] = free_days
    results["earliest_start"] = {"days": earliest_days, "time": earliest_time}
    results["latest_finish"] = {"days": latest_days, "time": latest_time}
    return results




#------------------supporting functions------------
def get_events_per_day(weekly_events):
    #dividing raw timetable events per day from the response of weekly_calendar.py
    days_to_event = {
        "Monday": [],
        "Tuesday": [],
        "Wednesday": [],
        "Thursday": [],
        "Friday": [] 
    }

    #matching every event to their corresponding days
    for event in weekly_events:
        start = datetime.fromisoformat(event["start"])#convert the format string date (2026-11-04T09:00:00Z) into python datetime object year-month-day hour:minute:second+UTC -> 2026-11-04 09:00:00+00
        day = start.strftime("%A") #extracts the day of a python datetime

        #if the events happen on a weekday, store these events in their corresponding lists
        if day in days_to_event :
            days_to_event [day].append(event)
    
    return days_to_event

def sortHelper(event):
    return event.get("start")


if __name__ == "__main__":
    weekly_timetable = [
        {'module_name1': 'CSC1042[1] Computer Networks 2', 'module_name2': 'CSC1042 Computer Networks 2 (Lecture)', 'location': 'FTG11', 'long_description': 'Lecture, On Campus', 'short_description': 'Lecture', 'start': '2026-11-02T09:00:00Z', 'end': '2026-11-02T11:00:00Z'},
        {'module_name1': 'CSC1046[1] OO Analysis & Design', 'module_name2': 'CSC1046 OO Analysis & Design (Lecture)', 'location': 'FTG13', 'long_description': 'Lecture, On Campus', 'short_description': 'Lecture', 'start': '2026-11-02T11:00:00Z', 'end': '2026-11-02T12:00:00Z'},
        {'module_name1': 'CSC1047[1] Advanced Algorithms & A.I. Search', 'module_name2': 'CSC1047 Advanced Algorithms & A.I. Search (Lecture)', 'location': 'FTG13', 'long_description': 'Lecture, On Campus', 'short_description': 'Lecture', 'start': '2026-11-02T12:00:00Z', 'end': '2026-11-02T13:00:00Z'},
        {'module_name1': 'CSC1047[1] Advanced Algorithms & A.I. Search', 'module_name2': 'CSC1047 Advanced Algorithms & A.I. Search (Lecture)', 'location': 'FTG13', 'long_description': 'Lecture, On Campus', 'short_description': 'Lecture', 'start': '2026-11-02T14:00:00Z', 'end': '2026-11-02T15:00:00Z'},
        {'module_name1': 'CSC1202[1] Prompt Engineering and LLM-Based Agents', 'module_name2': 'CSC1202 Prompt Engineering and LLM-Based Agents (Lecture)', 'location': 'FTG11', 'long_description': 'Lecture, On Campus', 'short_description': 'Lecture', 'start': '2026-11-02T16:00:00Z', 'end': '2026-11-02T17:00:00Z'},
        {'module_name1': 'CSC1047[1] Advanced Algorithms & A.I. Search', 'module_name2': 'CSC1047 Advanced Algorithms & A.I. Search (Lab)', 'location': 'LG27, L101, L114, L129', 'long_description': 'Lab, On Campus', 'short_description': 'Lab', 'start': '2026-11-03T11:00:00Z', 'end': '2026-11-03T13:00:00Z'},
        {'module_name1': 'CSC1048[1] Computability & Complexity', 'module_name2': 'CSC1048 Computability & Complexity (Lecture)', 'location': 'CG12', 'long_description': 'Lecture, On Campus', 'short_description': 'Lecture', 'start': '2026-11-03T14:00:00Z', 'end': '2026-11-03T15:00:00Z'},
        {'module_name1': 'CSC1058[1] User Interface Design & Implementation', 'module_name2': 'CSC1058 User Interface Design & Implementation (Lecture)', 'location': 'SA101', 'long_description': 'Lecture, On Campus', 'short_description': 'Lecture', 'start': '2026-11-03T15:00:00Z', 'end': '2026-11-03T16:00:00Z'},
        {'module_name1': 'CSC1202[1] Prompt Engineering and LLM-Based Agents', 'module_name2': 'CSC1202 Prompt Engineering and LLM-Based Agents (Lecture)', 'location': 'HG20', 'long_description': 'Lecture, On Campus', 'short_description': 'Lecture', 'start': '2026-11-04T09:00:00Z', 'end': '2026-11-04T10:00:00Z'},
        {'module_name1': 'CSC1058[1] User Interface Design & Implementation', 'module_name2': 'CSC1058 User Interface Design & Implementation (Lecture)', 'location': 'FTG11', 'long_description': 'Lecture, On Campus', 'short_description': 'Lecture', 'start': '2026-11-04T11:00:00Z', 'end': '2026-11-04T12:00:00Z'},
        {'module_name1': 'CSC1046[1] OO Analysis & Design', 'module_name2': 'CSC1046 OO Analysis & Design (Tutorial)', 'location': 'CG12', 'long_description': 'Tutorial, On Campus', 'short_description': 'Tutorial', 'start': '2026-11-04T12:00:00Z', 'end': '2026-11-04T13:00:00Z'},
        {'module_name1': 'CSC1046[1] OO Analysis & Design', 'module_name2': 'CSC1046 OO Analysis & Design (Lecture)', 'location': 'CG12', 'long_description': 'Lecture, On Campus', 'short_description': 'Lecture', 'start': '2026-11-04T13:00:00Z', 'end': '2026-11-04T14:00:00Z'},
        {'module_name1': 'CSC1042[1] Computer Networks 2', 'module_name2': 'CSC1042 Computer Networks 2 (Lab)', 'location': 'L114, L125', 'long_description': 'Lab, On Campus', 'short_description': 'Lab', 'start': '2026-11-04T15:00:00Z', 'end': '2026-11-04T18:00:00Z'},
        {'module_name1': 'CSC1048[1] Computability & Complexity', 'module_name2': 'CSC1048 Computability & Complexity (Lecture)', 'location': 'QG13', 'long_description': 'Lecture, On Campus', 'short_description': 'Lecture', 'start': '2026-11-05T10:00:00Z', 'end': '2026-11-05T11:00:00Z'},
        {'module_name1': 'CSC1048[1] Computability & Complexity', 'module_name2': 'CSC1048 Computability & Complexity (Lab)', 'location': 'L101, L125', 'long_description': 'Lab, On Campus', 'short_description': 'Lab', 'start': '2026-11-05T13:00:00Z', 'end': '2026-11-05T15:00:00Z'}
    ]
    #print(get_daily_breakdown(weekly_timetable))
    #print(get_daily_breakdown(weekly_timetable))
    #print(analyse_free_gaps(weekly_timetable))
    #print(analyse_class_patterns(weekly_timetable))