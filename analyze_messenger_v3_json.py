#!/usr/bin/env python3

# This script is fed a directory containing all conversations that a particular user participates in
# The data can be fetched from Facebook by going to Account Settings and clicking "Download a copy of your Facebook data"

# The data is stored in the threads list
# The threads list contains dictionaries, each of them representing a distinct thread
# The dictionary entries are "members" which maps to a list of names, and "messages"
# The messages list entries are dictionaries containing "date" (a datetime object), "sender" and "content"

threads = []

import json
from datetime import datetime
from datetime import timedelta
import os

# for the names to id conversion
import setup

def debug_log(s):
    if setup.debug:
        print(s)

def load_data(messages_directory):
    for threadname in os.listdir(messages_directory):
        if threadname.startswith('.'):
            continue
        if threadname == 'stickers_used':
            continue
        # the messages are stored in the "message.json" file in the threadname directory
        # we want to load those json dictionaries, put them in the threads list, and do some data conversion
        filename = os.path.join(messages_directory, threadname, "message.json")
        threaddict = {}
        with open(filename) as f:
            threaddict = json.load(f)
        # alter every message a bit
        for message in threaddict['messages']:
            # now convert the timestamp into a real datetime object
            message['date'] = datetime.fromtimestamp(message['timestamp'])
            # for consistency, change sender_name to sender
            message['sender'] = message['sender_name']
            if 'content' not in message:
                message['content'] = ''
        # for consistency, copy participants to members
        threaddict['members'] = []
        if 'participants' in threaddict:
            for participant in threaddict['participants']:
                threaddict['members'].append(participant)
        threaddict['members'].append(setup.user)
        # add index
        global threads
        threaddict['index'] = len(threads)
        threads.append(threaddict)



           
def main(messages_directory):

    # read the json files and put them in the threads list
    load_data(messages_directory)

    # group threads that are split due to too many messages
    #group_threads()

    # sort the messages
    sort_messages()

    # create conversations
    create_conversations()

    # meta data rules
    calculate_meta_data()

    # time interval data for neat graphs
    generate_time_interval_data()

    generate_global_time_data()


    # temporary
    show_arvid_per_thread("words")
    #show_arvid_per_thread("messages",threshold=100)



# sort all messages, so that the oldest are first
def sort_messages():
    global threads
    for thread in threads:
        thread["messages"].sort(key = lambda message: message["date"])



"""
# group threads
def group_threads():
    global threads
    # reverse the threads list, since I think the threads that are split are in reverse chronological order
    threads.reverse()
    # Do simple O(n^2)
    # It won't do for people with really many threads, but those are probably few and far between
    remove_indices = []
    for index, thread in enumerate(threads):
        for past_thread in threads[:index]:
            same = True
            for member in past_thread["members"]:
                if member not in thread["members"]:
                    same = False
                    break
            for member in thread["members"]:
                if member not in past_thread["members"]:
                    same = False
                    break
            if same:
                remove_indices.append(index)
                past_thread["messages"].extend(thread["messages"])
                break
    has_removed = 0
    for remove_index in remove_indices:
        del threads[remove_index - has_removed]
        has_removed += 1
"""




def calculate_meta_data():
    # calculating extra data, such as number of messages per person, number of words per person, and so forth
    global threads
    for thread in threads:

        # relevant data lists
        members = thread["members"]
        messages = thread["messages"]
        conversations = thread["conversations"]

        meta = {}
        meta["number_of_messages"] = len(messages)

        messages_per_member = {}
        words_per_member = {}
        conversations_started_per_member = {}
        conversations_ended_per_member = {}
        mobbade_conversations_per_member = {}
        top_words_per_member = {}
        all_words_per_member_count = {}

        # initialize all to zero
        for member in members:
            messages_per_member[member] = 0
            words_per_member[member] = 0
            conversations_started_per_member[member] = 0
            conversations_ended_per_member[member] = 0
            mobbade_conversations_per_member[member] = 0
            top_words_per_member[member] = []
            all_words_per_member_count[member] = {}

        skip_words = {"det", "är", "jag", "att", "inte", "på", "vi", "du", "har", "man", "och", "eller", "så", "i"}

        # iterate over each message, and update the relevant metrics
        for message in messages:
            if message["sender"] in members:
                messages_per_member[message["sender"]] += 1
                words_per_member[message["sender"]] += len(message["content"].split())
                for word in message["content"].split():
                    word = word.lower().strip()
                    #if word in skip_words:
                    #    continue
                    if word in all_words_per_member_count[message["sender"]]:
                        all_words_per_member_count[message["sender"]][word] += 1
                    else:
                        all_words_per_member_count[message["sender"]][word] = 1

        for member in members:
            top_ten = []
            i = 0
            while i < 100 and len(all_words_per_member_count[member]) > 0:
                i += 1
                greatest_val = 0
                word_tuple = ("hej", 0)
                for word in all_words_per_member_count[member]:
                    if all_words_per_member_count[member][word] > greatest_val:
                        greatest_val = all_words_per_member_count[member][word]
                        word_tuple = (word, all_words_per_member_count[member][word])
                top_ten.append(word_tuple)
                del all_words_per_member_count[member][word_tuple[0]]
            top_words_per_member[member] = top_ten
        
                

        # iterate over each conversation
        for conversation in conversations:
            start_message = conversation["messages"][0]
            start_user = start_message["sender"]
            end_user = conversation["messages"][len(conversation["messages"])-1]["sender"]
            if start_user in members:
                conversations_started_per_member[start_user] += 1
                if len(conversation["members"]) == 1:
                    # mobbad!
                    mobbade_conversations_per_member[start_user] += 1
            if end_user in members:
                conversations_ended_per_member[end_user] += 1

        # add the data to the meta dictionary
        meta["messages_per_member"] = messages_per_member
        meta["words_per_member"] = words_per_member
        meta["conversations_started_per_member"] = conversations_started_per_member
        meta["conversations_ended_per_member"] = conversations_ended_per_member
        meta["mobbade_conversations_per_member"] = mobbade_conversations_per_member
        meta["top_words_per_member"] = top_words_per_member
        

        # finally, add the meta data to the thread dictionary
        thread["meta_data"] = meta

        

def generate_time_interval_data():
    # generate daily, weekly, monthly and yearly data

    global threads
    for thread in threads:

        # relevant data lists
        members = thread["members"]
        messages = thread["messages"]
        conversations = thread["conversations"]

        time_data = {}

        if len(messages) == 0:
            continue
        
        start_date = messages[0]["date"].date()
        end_date = messages[len(thread["messages"])-1]["date"].date()

        # days
        time_data["daily"] = {}
        date_count = (end_date - start_date).days + 1
        for n in range(date_count):
            this_date = start_date + timedelta(days = n)
            time_data["daily"][this_date] = {}

            # init teodor theodore
            time_data["daily"][this_date]["teodortheodore"] = {}
            time_data["daily"][this_date]["teodortheodore"]["teodor"] = 0
            time_data["daily"][this_date]["teodortheodore"]["theodore"] = 0

            # init messages per member
            time_data["daily"][this_date]["messages_per_member"] = {}
            time_data["daily"][this_date]["words_per_member"] = {}
            for member in members:
                time_data["daily"][this_date]["messages_per_member"][member] = 0
                time_data["daily"][this_date]["words_per_member"][member] = 0


        # create daily
        for message in messages:
            this_date = message["date"].date()

            # teodor theodore
            if "teodor" in message["content"].lower():
                time_data["daily"][this_date]["teodortheodore"]["teodor"] += 1
            if "théodòre" in message["content"].lower():
                time_data["daily"][this_date]["teodortheodore"]["theodore"] += 1
            
            # per member
            if message["sender"] in members:
                time_data["daily"][this_date]["messages_per_member"][message["sender"]] += 1
                time_data["daily"][this_date]["words_per_member"][message["sender"]] += len(message["content"].split())


        # months
        time_data["monthly"] = {}
        month_count = diff_month(end_date, start_date) + 1
        month_start = start_date.replace(day = 1)
        for n in range(month_count):
            this_month = add_months(month_start, n)
            time_data["monthly"][this_month] = {}

            # init teodor theodore
            time_data["monthly"][this_month]["teodortheodore"] = {}
            time_data["monthly"][this_month]["teodortheodore"]["teodor"] = 0
            time_data["monthly"][this_month]["teodortheodore"]["theodore"] = 0

            time_data["monthly"][this_month]["emoji_per_member"] = {}
            time_data["monthly"][this_month]["adjusted_emoji_per_member"] = {}

            # init messages per member
            time_data["monthly"][this_month]["messages_per_member"] = {}
            time_data["monthly"][this_month]["words_per_member"] = {}
            for member in members:
                time_data["monthly"][this_month]["messages_per_member"][member] = 0
                time_data["monthly"][this_month]["words_per_member"][member] = 0
                time_data["monthly"][this_month]["emoji_per_member"][member] = 0
                time_data["monthly"][this_month]["adjusted_emoji_per_member"][member] = 0

        # create monthly
        for message in messages:
            this_date = message["date"].date()
            this_date = this_date.replace(day = 1)

            # teodor theodore
            if "teodor" in message["content"].lower():
                time_data["monthly"][this_date]["teodortheodore"]["teodor"] += 1
            if "théodòre" in message["content"].lower():
                time_data["monthly"][this_date]["teodortheodore"]["theodore"] += 1

            # per member
            if message["sender"] in members:
                time_data["monthly"][this_date]["messages_per_member"][message["sender"]] += 1
                time_data["monthly"][this_date]["words_per_member"][message["sender"]] += len(message["content"].split())
                
                global emoji
                for e in emoji:
                    if e in message["content"]:
                        time_data["monthly"][this_date]["emoji_per_member"][message["sender"]] += 1

        for n in range(month_count):
            this_month = add_months(month_start, n)
            for member in members:
                if time_data["monthly"][this_month]["words_per_member"][member] != 0:
                    time_data["monthly"][this_month]["adjusted_emoji_per_member"][member] = time_data["monthly"][this_month]["emoji_per_member"][member] / time_data["monthly"][this_month]["words_per_member"][member]


        thread["time_data"] = time_data

def generate_global_time_data():
    # generate daily data globally, i.e. for all threads at once. used to compare threads.
    global global_time_data

    global threads

    start_date = None
    end_date = None
    for thread in threads:
        tstart = thread["messages"][0]["date"].date()
        tend = thread["messages"][len(thread["messages"])-1]["date"].date()
        if start_date == None and end_date == None:
            start_date = tstart
            end_date = tend
        if tstart < start_date:
            start_date = tstart
        if tend > end_date:
            end_date = tend

    global_time_data = {}
    global_time_data["daily"] = {}
    date_count = (end_date - start_date).days + 1

    
    for thread in threads:

        # relevant data lists
        members = thread["members"]
        messages = thread["messages"]
        conversations = thread["conversations"]

        if len(messages) == 0:
            continue

        # days
        ti = thread["index"]
        global_time_data["daily"][thread["index"]] = {}
        for n in range(date_count):
            this_date = start_date + timedelta(days = n)
            global_time_data["daily"][ti][this_date] = {}

            # init messages per member
            global_time_data["daily"][ti][this_date]["messages_per_member"] = {}
            global_time_data["daily"][ti][this_date]["words_per_member"] = {}
            for member in members:
                global_time_data["daily"][ti][this_date]["messages_per_member"][member] = 0
                global_time_data["daily"][ti][this_date]["words_per_member"][member] = 0

        # create daily
        for message in messages:
            this_date = message["date"].date()

            # per member
            if message["sender"] in members:
                global_time_data["daily"][ti][this_date]["messages_per_member"][message["sender"]] += 1
                global_time_data["daily"][ti][this_date]["words_per_member"][message["sender"]] += len(message["content"].split())



def diff_month(d1, d2):
    return (d1.year - d2.year)*12 + d1.month - d2.month

from datetime import date
import calendar
def add_months(sourcedate,months):
    month = sourcedate.month - 1 + months
    year = int(sourcedate.year + month / 12 )
    month = month % 12 + 1
    day = min(sourcedate.day,calendar.monthrange(year,month)[1])
    return date(year,month,day)


# plot using pyplot
from matplotlib import pyplot as plt
from matplotlib import dates as pltdates
# times is list of datetimes. series is list of dicts containing "label" string and "datapoints" list.
def plot_time_data(times, series, stackplot=True):
    #dates = pltdates.date2num(times)
    if not stackplot:
        for sery in series:
            plt.plot(times,sery["datapoints"],label=sery["label"],linestyle="-",marker="")
    else:
        labels = []
        ys = []
        for sery in series:
            labels.append(sery["label"])
            ys.append(sery["datapoints"])
        plt.stackplot(times,ys,labels=labels)
    plt.legend(loc="upper left")
    plt.show()


# plot number of words or messages per thread
# threshold is number of words/messages user must have sent to show the thread in the graph
# movingaverage creates a movingaverage for smoother plots
def show_arvid_per_thread(worm, threshold=1000, movingaverage=50):
    k = None
    if worm == "words":
        k = "words_per_member"
    elif worm == "messages":
        k = "messages_per_member"
    else:
        print("ERROR. Argument must be 'words' or 'messages'.")
        return
    
    global global_time_data
    global threads

    times = []


    series = []
    for thread in threads:
        ti = thread["index"]
        sery = {}
        sery["label"] = thread["title"]
        sery["datepoints"] = []
        totalcount = 0
        for dd,datad in global_time_data["daily"][ti].items():
            sery["datepoints"].append({"date": dd, "data": datad[k][setup.user]})
            totalcount += datad[k][setup.user]
        # sort datapoints by date
        sery["datepoints"].sort(key = lambda day: day["date"])
        sery["datapoints"] = []
        addlengths = len(times) == 0
        for dd in sery["datepoints"]:
            sery["datapoints"].append(dd["data"])
            if addlengths:
                times.append(dd["date"])
        if totalcount >= threshold:
            series.append(sery)

    # now apply moving average
    #averageseries = []
    for seryy in series:
        sery = seryy["datapoints"]
        avsery = []
        curavg = 0
        for i in range(movingaverage):
            curavg += sery[i]
            avsery.append(curavg / (i+1))
        curavg /= movingaverage
        for i, s in enumerate(sery[movingaverage:]):
            curavg -= sery[i]/movingaverage
            curavg += s/movingaverage
            avsery.append(curavg)
        assert len(avsery) == len(sery)
        seryy["datapoints"] = avsery
        #averageseries.append(avsery)

    plot_time_data(times, series)



# interval parameter can be "daily", "weekly" or "monthly" or "yearly"
# thread is indexed
def csv_export_interval_data(thread, interval, data, f = None):
    # export dict
    export_dict = threads[thread]["time_data"][interval]

    start_date = threads[thread]["messages"][0]["date"].date()
    end_date = threads[thread]["messages"][len(threads[thread]["messages"])-1]["date"].date()

    if interval == "daily":
        s = "Date"
        for data_point in export_dict[start_date][data]:
            s += "," + str(data_point)
        s += "\n"

        date_count = (end_date - start_date).days + 1
        for n in range(date_count):
            d = start_date + timedelta(days = n)
            s += str(d)
            for data_point in export_dict[d][data]:
                s += "," + str(export_dict[d][data][data_point])
            s += "\n"

        if f == None:
            print(s)
        else:
            # print to file
            with open(f, "w") as fi:
                fi.write(s)
    elif interval == "monthly":
        month_start = start_date.replace(day = 1)
        s = "Date"
        for data_point in export_dict[month_start][data]:
            s += "," + str(data_point)
        s += "\n"

        month_count = diff_month(end_date, start_date) + 1
        for n in range(month_count):
            d = add_months(month_start, n)
            s += str(d)
            for data_point in export_dict[d][data]:
                s += "," + str(export_dict[d][data][data_point])
            s += "\n"

        if f == None:
            print(s)
        else:
            # print to file
            with open(f, "w") as fi:
                fi.write(s)











# Create conversations
def create_conversations():
    global threads
    for thread in threads:
        members = thread["members"]
        messages = thread["messages"]
        # create conversations
        # each conversation is a dictionary with a "members" list and a sorted "messages" list
        conversations = []
        for message in messages:
            last_conversation = None
            if len(conversations) > 0:
                last_conversation = conversations[len(conversations)-1]
            if starts_conversation(message, last_conversation):
                new_conversation = {"members": [message["sender"]], "messages": [message]}
                conversations.append(new_conversation)
            else:
                if message["sender"] not in conversations[len(conversations)-1]["members"]:
                    conversations[len(conversations)-1]["members"].append(message["sender"])
                conversations[len(conversations)-1]["messages"].append(message)

        # finally, add the conversations to the thread
        thread["conversations"] = conversations



# returns bool
# last_conversation is dictionary "members" list and "messages" list
def starts_conversation(message, last_conversation):
    if last_conversation == None:
        return True
    last_time = last_conversation["messages"][len(last_conversation["messages"]) - 1]["date"]
    this_time = message["date"]
    time_delta = this_time - last_time
    if time_delta.total_seconds() > 60*60*5:
        return True
    if time_delta.total_seconds() > 60*60:
        # check if this user belongs to last_conversation
        if message["sender"] in last_conversation["members"]:
            return True
    return False



# list of emoji
emoji = [":)", ";)", ":/", "😆", "😅", "😀", "😂", "😉"]


def print_threads():
    global thread
    for i, thread in enumerate(threads):
        print("Thread " + str(i) + " with " + str(len(thread["messages"])) + " messages")
        print("Title: " + str(thread["title"]))
        for member in thread["members"]:
            message_count = thread["meta_data"]["messages_per_member"][member]
            word_count = thread["meta_data"]["words_per_member"][member]
            conversations_started = thread["meta_data"]["conversations_started_per_member"][member]
            conversations_ended = thread["meta_data"]["conversations_ended_per_member"][member]
            mobbade_conversations = thread["meta_data"]["mobbade_conversations_per_member"][member]
            top_words = thread["meta_data"]["top_words_per_member"][member]
            ratio = None
            if message_count != 0:
                ratio = word_count / message_count
            else:
                ratio = "(no messages sent)"
            # correct spelling!
            if member == "Teodor Bucht":
                member = "Théodòre Bucht"
            print("\t" + member + ":")
            print("\t\tMessage count: " + str(message_count))
            print("\t\tWord count: " + str(word_count))
            print("\t\tWords per message: " + str(ratio))
            print("\t\tStarted conversations: " + str(conversations_started))
            print("\t\tMobbade conversations: " + str(mobbade_conversations))
            print("\t\tEnded conversations: " + str(conversations_ended))
            """print("\t\tTop words: ", end="")
            for (word, count) in top_words:
                print(word + " (" + str(count) + "), ", end="")
            print("")"""

        # ONLY PRINT FIRST GROUP
        #break


import sys
if __name__ == "__main__":
    main(sys.argv[1]) 
