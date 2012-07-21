import sys
from observationdb.models import Observation

def mark_as_archived(lower, upper, location):
    for obsid in xrange(lower, upper+1):
        obsid = "L" + str(obsid)
        try:
            obs = Observation.objects.get(obsid=obsid)
            obs.archive = location
            obs.save()
        except:
            print "%s is not in the database" % obsid

if __name__ == "__main__":
    archive_list = sys.argv[1]

    with open(archive_list, 'r') as f:
        l = f.readlines()

    for line in l:
        lower = int(line.split()[0])
        upper = int(line.split()[1])
        location = line.split()[2]
        mark_as_archived(lower, upper, location)

