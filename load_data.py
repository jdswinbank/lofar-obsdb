import sys
import glob
import datetime
import os.path
from pyrap.quanta import quantity
from lofar.parameterset import parameterset
from pyrap.measures import measures

from observationdb.models import Survey
from observationdb.models import Field
from observationdb.models import Station
from observationdb.models import Observation
from observationdb.models import Beam
from observationdb.models import Subband

SURVEY = "MSSS LBA"

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

def check_for_msss_run(parsets, length, start_positions, step):
    assert(len(parsets) == length)

    # Zeroth check: no data reuse
    if True in [parset.allocated for parset in parsets]:
        return False

    # First check: every second observation is of the same calibrator
    calibrators = {parset.is_calibrator() for parset in parsets[::2]}
    if False in calibrators or len(calibrators) != 1:
        return False

    # Second check: every other observation has 3 or 4 beams
    nr_beams = {parset.get_int("Observation.nrBeams") for parset in parsets[1::2]}
    if (not 3 in nr_beams and not 4 in nr_beams) or len(nr_beams) != 1:
        return False

    # Third check: every eighth observation should be of the same field *or*
    # might be None
    targets = []
    for start_position in start_positions:
        for beam in [0,1,2]:
            targets.append(
                {
                    (
                        parset.get_float("Observation.Beam[%d].angle1" % beam),
                        parset.get_float("Observation.Beam[%d].angle2" % beam)
                    )
                    for parset in parsets[start_position::step]
                }
            )
    for target in targets:
        if len(target) != 1:
            return False

    # All done!
    return True

def check_for_high_dec(parsets):
    return check_for_msss_run(parsets, 72, [1,3,5,7], 8)

def check_for_low_dec(parsets):
    return check_for_msss_run(parsets, 54, [1,3,5], 6)


def upload_to_djangodb(parsets):
    survey = Survey.objects.get(name=SURVEY)

    for parset in parsets:
        obsid = os.path.basename(parset.filename).rstrip(".parset")
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
            else:
                print "WARNING! Unrecognized field: %s beam %d" % (obsid, beam_number)


if __name__ == "__main__":
    if not Subband.objects.count() == 512:
        Subband.objects.bulk_create(
            [Subband(number=number) for number in xrange(513)]
        )

    filenames = glob.glob("/home/jds/tmp/parsets/L*.parset")
    parsets = load_parsets(filenames)
    parsets = [
        parset for parset in parsets if
        parset.has_key("Observation.Campaign.name") and
        parset.get_string("Observation.Campaign.name") == "MSSS"
    ]
    parsets.sort(key=lambda parset: parset.start_time())

#    for pset in parsets:
#        if pset.is_calibrator():
#            print pset.filename, pset.is_calibrator(), pset.start_time()
#        else:
#            print pset.filename, pset.field_name(0, field_list), pset.field_name(1, field_list), pset.field_name(2, field_list), pset.start_time()
    for idx, parset in enumerate(parsets):
        if not parset.allocated and len(parsets[idx:idx+72]) == 72:
            if check_for_high_dec(parsets[idx:idx+72]):
                print "Got a run of 36 calibrators starting at %s %d" % (parset.filename, idx)
                upload_to_djangodb(parsets[idx:idx+72])
                for pset in  parsets[idx:idx+72]:
                    pset.allocated = True
#                    if pset.is_calibrator():
#                        print pset.filename, pset.is_calibrator(), pset.start_time()
#                    else:
#                        print pset.filename, pset.field_name(0), pset.field_name(1), pset.field_name(2), pset.start_time()
        if not parset.allocated and len(parsets[idx:idx+54]) == 54:
            if check_for_low_dec(parsets[idx:idx+54]):
                print "Got a run of 27 calibrators starting at %s %d" % (parset.filename, idx)
                upload_to_djangodb(parsets[idx:idx+54])
                for pset in  parsets[idx:idx+54]:
                    pset.allocated = True
#                    if pset.is_calibrator():
#                        print pset.filename, pset.is_calibrator(), pset.start_time()
#                    else:
#                        print pset.filename, pset.field_name(0), pset.field_name(1), pset.field_name(2), pset.start_time()
