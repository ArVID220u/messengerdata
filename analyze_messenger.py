#!/usr/bin/env python3

# This script is fed an htm document containing all the messages sent to and from a particular user
# The data can be fetched from Facebook by going to Account Settings and clicking "Download a copy of your Facebook data"

# The data is stored in the threads list
# The threads list contains dictionaries, each of them representing a distinct thread
# The dictionary entries are "members" which maps to a list of names, and "messages"
# The messages list entries are dictionaries containing "date" (a datetime object), "sender" and "content"

threads = []

from html.parser import HTMLParser
from datetime import datetime
from datetime import timedelta

# for the names to id conversion
import setup

class MessengerParser(HTMLParser):

    # the current thread dictionary
    current_thread = None

    # next content
    next_content = ""

    nest_level = 0

    n_messages = 0

    def handle_starttag(self, tag, attrs):
        self.nest_level += 1
        for attr in attrs:
            name, value = attr
            if name == "class" and value == "thread":
                # create the current thread
                self.n_messages = 0
                self.current_thread = {"members": None, "messages": []}
                self.next_content = "members"
                self.nest_level = 0
            elif name == "class" and value == "message":
                self.n_messages += 1
                self.current_thread["messages"].append({"date": None, "sender": None, "content": ""})
            elif name == "class" and value == "user":
                self.next_content = "sender"
            elif name == "class" and value == "meta":
                self.next_content = "date"
        if tag == "p":
            self.next_content = "content"


    def handle_data(self, data):
        if self.current_thread != None:
            if self.next_content == "members":
                rawmembers = data.split(", ")
                members = []
                for member in rawmembers:
                    name = member
                    if name in setup.names_per_id:
                        name = setup.names_per_id[name]
                    members.append(name)
                self.current_thread["members"] = members
            elif self.next_content == "sender":
                name = data
                if name in setup.names_per_id:
                    name = setup.names_per_id[name]
                self.current_thread["messages"][self.n_messages - 1]["sender"] = name
            elif self.next_content == "date":
                self.current_thread["messages"][self.n_messages - 1]["date"] = datetime.strptime(data + "00", "%A, %B %d, %Y at %I:%M%p %Z%z")
            elif self.next_content == "content":
                self.current_thread["messages"][self.n_messages - 1]["content"] = data


    def handle_endtag(self, tag):
        self.nest_level -= 1
        if self.nest_level < 0 and self.current_thread != None:
            global threads
            threads.append(self.current_thread)
            self.current_thread = None
           
def main(messages_url):
    messengerParser = MessengerParser()
    messengerParser.convert_charrefs = True

    with open(messages_url, "r") as messages_file:
        messengerParser.feed(messages_file.read())

    # group threads that are split due to too many messages
    group_threads()

    # sort the messages
    sort_messages()

    # create convos
    create_convos()

    # meta data rules
    calculate_meta_data()

    # time interval data for neat graphs
    generate_time_interval_data()




# sort all messages, so that the oldest are first
def sort_messages():
    global threads
    for thread in threads:
        thread["messages"].sort(key = lambda message: message["date"])



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
        for convo in conversations:
            start_message = convo["messages"][0]
            start_user = start_message["sender"]
            end_user = convo["messages"][len(convo["messages"])-1]["sender"]
            if start_user in members:
                conversations_started_per_member[start_user] += 1
                if len(convo["members"]) == 1:
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
def create_convos():
    global threads
    for thread in threads:
        members = thread["members"]
        messages = thread["messages"]
        # create convos
        # each convo is a dictionary with a "members" list and a sorted "messages" list
        convos = []
        for message in messages:
            last_convo = None
            if len(convos) > 0:
                last_convo = convos[len(convos)-1]
            if starts_convo(message, last_convo):
                new_convo = {"members": [message["sender"]], "messages": [message]}
                convos.append(new_convo)
            else:
                if message["sender"] not in convos[len(convos)-1]["members"]:
                    convos[len(convos)-1]["members"].append(message["sender"])
                convos[len(convos)-1]["messages"].append(message)

        # finally, add the convos to the thread
        thread["conversations"] = convos



# returns bool
# last_convo is dictionary "members" list and "messages" list
def starts_convo(message, last_convo):
    if last_convo == None:
        return True
    last_time = last_convo["messages"][len(last_convo["messages"]) - 1]["date"]
    this_time = message["date"]
    time_delta = this_time - last_time
    if time_delta.total_seconds() > 60*60*5:
        return True
    if time_delta.total_seconds() > 60*60:
        # check if this user belongs to last_convo
        if message["sender"] in last_convo["members"]:
            return True
    return False



# list of emoji
emoji = [":)", ";)", ":/", "😆", "😅", "😀", "😂", "😉"]


def print_threads():
    global threads
    for i, thread in enumerate(threads):
        print("Thread " + str(i) + " with " + str(len(thread["messages"])) + " messages")
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
