import sys
from obsdb.observationdb.models import SubbandData, Observation, ArchiveSite

def mark_as_archived(lower, upper, location):
    site = ArchiveSite.objects.get_or_create(name=location)

    for obsid in xrange(lower, upper+1):
        obsid = "L" + str(obsid)
        try:
            obs = Observation.objects.get(obsid=obsid)
            for sb in SubbandData.objects.filter(beam__in=obs.beam_set.all()):
                sb.archive = site
                sb.save()
            print "Done %s" % obsid
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

