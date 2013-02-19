import sys
import os
import fnmatch
import datetime
from pyrap.quanta import quantity
from lofar.parameterset import parameterset
from pyrap.measures import measures

from obsdb.observationdb.models import Survey
from obsdb.observationdb.models import Field
from obsdb.observationdb.models import Station
from obsdb.observationdb.models import Observation
from obsdb.observationdb.models import Beam
from obsdb.observationdb.models import Subband
from obsdb.observationdb.models import SubbandData

SURVEY = "MSSS HBA"

class Parset(object):
    def __init__(self, filename):
        self.parset = parameterset(filename)
        self.filename = filename
        self.allocated = False

    def get_field(self, beam, threshold=0.05):
        ra = self.get_float("Observation.Beam[%d].angle1" % beam)
        dec = self.get_float("Observation.Beam[%d].angle2" % beam)
        try:
            return Field.objects.near_position(
                ra, dec, threshold
            ).filter(
                survey__name=SURVEY
            ).order_by("distance")[0]
        except:
            pass

    def is_calibrator(self, threshold=0.05):
        if self.get_int("Observation.nrBeams") == 1:
            ra = self.get_float("Observation.Beam[0].angle1")
            dec = self.get_float("Observation.Beam[0].angle2")
            try:
                return Field.objects.near_position(
                    ra, dec, threshold
                ).filter(
                    survey__name=SURVEY, calibrator=True
                ).order_by("distance")[0].name
            except:
                pass
        return False

    def start_time(self):
        return datetime.datetime.strptime(
            self.parset.getString('Observation.startTime'),
            "%Y-%m-%d %H:%M:%S"
        )

    def duration(self):
        end_time = datetime.datetime.strptime(
            self.parset.getString('Observation.stopTime'),
            "%Y-%m-%d %H:%M:%S"
        )
        duration = end_time - self.start_time()
        return duration.seconds

    def stations(self):
        return self.parset.get('Observation.VirtualInstrument.stationList').expand().getStringVector()

    def subbands(self, beam):
        return self.parset.get('Observation.Beam[%d].subbandList' % beam).expand().getIntVector()

    def clock(self):
        return int(self.parset.getString("Observation.clockMode")[-3:])

    def has_key(self, key):
        return True if key in self.parset.keys() else False

    def get_string(self, key):
        return self.parset.getString(key)

    def get_int(self, key):
        return self.parset.getInt(key)

    def get_float(self, key):
        return self.parset.getFloat(key)

def load_parsets(filenames):
    return [Parset(filename) for filename in filenames]


def upload_to_djangodb(parsets):
    survey = Survey.objects.get(name=SURVEY)

    for parset in parsets:
        obsid = os.path.basename(parset.filename).rstrip(".parset")
        print "Processing " + obsid
        with open(parset.filename, 'r') as parset_file:
            parset_contents = parset_file.read()

        observation = Observation.objects.create(
            obsid=obsid,
            antennaset=parset.get_string("Observation.antennaSet"),
            start_time=parset.start_time(),
            duration=parset.duration(),
            parset=parset_contents,
            clock=parset.clock(),
            filter=parset.get_string("Observation.bandFilter")
        )
        observation.stations = Station.objects.filter(name__in=parset.stations())
        observation.save()

        sb_ctr = 0
        for beam_number in range(parset.get_int("Observation.nrBeams")):
            field = parset.get_field(beam_number)
            if field:
                beam = Beam.objects.create(
                    observation=observation,
                    field=field,
                    beam=beam_number
                )
                beam.subbands = Subband.objects.filter(number__in=parset.subbands(beam_number))
                beam.save()
                sb_list = []
                for subband in beam.subbands.all():
                    sb_list.append(
                        SubbandData(
                            id=obsid+"_"+str(sb_ctr),
                            beam=beam,
                            number=sb_ctr,
                            subband=subband
                        )
                    )
                    sb_ctr += 1
                SubbandData.objects.bulk_create(sb_list)
            else:
                print "WARNING! Unrecognized field: %s beam %d" % (obsid, beam_number)


def get_file_list(root_dir):
    matches = []
    for root, dirnames, filenames in os.walk(root_dir):
        for filename in fnmatch.filter(filenames, "*.parset"):
            matches.append(os.path.join(root, filename))
    return matches

if __name__ == "__main__":
    if not Subband.objects.count() == 513:
        Subband.objects.bulk_create(
            [Subband(number=number) for number in xrange(513)]
        )

    filenames = get_file_list(sys.argv[1])
    for filename in filenames:
        parset = Parset(filename)

        if (parset.has_key("Observation.Campaign.name") and
            parset.get_string("Observation.Campaign.name") == "MSSS_HBA_2013" and
            parset.has_key("Observation.Campaign.title") and
            parset.get_string("Observation.Campaign.title") == "MSSS HBA Survey"
        ):
            upload_to_djangodb([parset])
