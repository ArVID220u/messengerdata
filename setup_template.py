

debug = True

user = "My Name"

# for some reason, some names are replaced by their facebook ID, in some way
# this probably only affects old versions of downloaded data
# as of May 2018 this issue seems to be fixed.
# that is, for data downloaded after May 2018 this dictionary is unnecessary
names_per_id = {"<id-number>@facebook.com": "Real Name",
                }
