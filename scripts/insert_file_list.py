from obsdb.observationdb.models import SubbandData, Observation
import sys

if __name__ == "__main__":
    obsid = sys.argv[1]
    input_file = sys.argv[2]
    with open(input_file, 'r') as f:
        input_lines = f.readlines()

    subbands = SubbandData.objects.filter(beam__observation__obsid=obsid)
    hostname = None

    print obsid
    for line in input_lines:
        if line.startswith("***********") or                   \
            line.startswith("Warning: No xauth data") or       \
            line.startswith("/usr/bin/xauth:") or              \
            line.startswith("find:") or                        \
            line.startswith("ssh: connect to host") or         \
            line.startswith("X11 connection rejected because") \
        :
            # Nothing to see here
            continue
        elif line.startswith("--------"):
            hostname = line.split()[1]
            print "Hostname is %s" % hostname
        else:
            size, path = line.split()
            size = int(size)
            band_number = int(path.split("_")[2][-3:], 10)
            subbands.filter(number=band_number).update(
                hostname=hostname, size=size, path=path
            )
            print "Done subband %d" % band_number

    # Need to call this once to ensure beam/observation/field status is
    # updated to reflect the data we have inserted.
    observation = Observation.objects.get(obsid=obsid)
    for beam in observation.beam_set.all():
        beam._update_status()
