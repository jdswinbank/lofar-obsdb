# Load per-node data file list into the database.
# Provide one or more files on the command line which are named according to
# <nodename>.log and contain lines of the format:
#
#   <size> <path>
#
# Where <size> is in bytes and <path> is the full path to an MS named
# according to MSSS standards (eg /data/LXXXXX/LXXXXX_SAPYYY_SBZZZ_uv.MS).

import sys
import os
from obsdb.observationdb.models import Observation, SubbandData
from collections import defaultdict

class SubbandFileData(object):
    def __init__(self, band_number, size, hostname, path):
        self.band_number = band_number
        self.size = size
        self.hostname = hostname
        self.path = path

if __name__ == "__main__":
    per_obs_id = defaultdict(list)
    for filename in sys.argv[1:]:
        hostname = os.path.splitext(os.path.basename(filename))[0]
        with open(filename, 'r') as f:
            for line in f:
                size, path = line.split()
                size = int(size) * 1024
                band_number = int(path.split("_")[2][-3:], 10)
                obsid = path.split("/")[2]
                per_obs_id[obsid].append(SubbandFileData(band_number, size, hostname, path))

    for obs in Observation.objects.all():
        if not per_obs_id.has_key(obs.obsid):
#            print "Obsid %s not recorded" % obs.obsid
            pass
        else:
            print "Processing %s" % obs.obsid
            subbands = SubbandData.objects.filter(beam__observation__obsid=obs.obsid)
            for subband in per_obs_id[obs.obsid]:
                print "Processing SB %d" % subband.band_number
                subbands.filter(number=subband.band_number).update(
                    hostname=subband.hostname,
                    size=subband.size,
                    path=subband.path
                )
            for beam in obs.beam_set.all():
                beam._update_status()

