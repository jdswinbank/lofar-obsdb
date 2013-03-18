import sys
from obsdb.observationdb.models import Observation

if __name__ == "__main__":
    bad_list = sys.argv[1]

    with open(bad_list, 'r') as f:
        l = f.readlines()

    for line in l:
        o = Observation.objects.get(obsid=line.strip())
        print o.obsid
        o.invalid = True
        o.save()
        for beam in o.beam_set.all():
            beam.save()
