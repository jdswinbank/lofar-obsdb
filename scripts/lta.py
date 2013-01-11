import sys
from django.core.exceptions import ObjectDoesNotExist
from obsdb.observationdb.models import SubbandData, Observation, ArchiveSite, Constants

def mark_as_archived(obsid, location):
    obsid = "L" + str(obsid)
    try:
        obs = Observation.objects.get(obsid=obsid)
        SubbandData.objects.filter(beam__in=obs.beam_set.all()).update(archive=site)
        for beam in obs.beam_set.all():
            beam.archived = Constants.TRUE
            beam.save()
        print "Done %s" % obsid
    except ObjectDoesNotExist:
        print "%s is not in the database" % obsid


if __name__ == "__main__":
    site, created = ArchiveSite.objects.get_or_create(name="LTA")
    archive_list = sys.argv[1]
    with open(archive_list, 'r') as f:
        l = f.readlines()
        for line in l[1:]:
            mark_as_archived(line.strip(), site)
