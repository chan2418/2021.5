print("***************** Inside main init file ******************** ")
import sys
import os
sys.path.insert(1, os.path.dirname(__file__))
import getpass

lst_of_users = [
    "prasad.jairam",
    # "ilambharathi",
    # "manikanda.srinivasulu",
    # "kalaiselvan.j",
    # "arunkumar.p",
    # "shybin.benny",
    # "suriya.prakash",
    # "mugesh.jothikrishnan",
    # "vignesh.elumalai",
    # "anandhakumar.vijayakumar",
    # "umapathi.v",
]

# current_user = getpass.getuser()
# if current_user in lst_of_users:
#     print("Silhouette script called user ___________^^^^^^^^^^______________")
#     import silhouette_idle_monitor
#     print("current_user:", current_user)
#     silhouette_idle_monitor.start_idle_monitor()
