import sys
import glob
import datetime
import os.path
from pyrap.quanta import quantity
from lofar.parameterset import parameterset
from pyrap.measures import measures

EPOCH="J2000"
dm = measures()
calibrators = {
    "CygA":  dm.direction(EPOCH, "19:59:28.4", "40.44.02"),
    "3C48":  dm.direction(EPOCH, "01:37:41.3", "33.09.35"),
    "3C147": dm.direction(EPOCH, "05:42:36.1", "49.51.07"),
    "3C196": dm.direction(EPOCH, "08:13:36.0", "48.13.03"),
    "3C286": dm.direction(EPOCH, "13:31:08.3", "30.30.33"),
    "3C287": dm.direction(EPOCH, "13:30:37.7", "25.09.11"),
    "3C295": dm.direction(EPOCH, "14:11:20.5", "52.12.10"),
    "3C380": dm.direction(EPOCH, "18:29:31.8", "48.44.46")
}

class FieldList(dict):
    def closest_to(self, target):
        dm = measures()
        min_name, min_sep = min(
            [
                (item[0], dm.separation(target, item[1]).get_value())
                for item in self.items()
            ],
            key=lambda x: x[1]
        )
        return min_name, min_sep

class Parset(object):
    def __init__(self, filename):
        self.parset = parameterset(filename)
        self.filename = filename
        self.allocated = False

    def field_name(self, beam, field_list, threshold=0.5):
        ra = self.get_float("Observation.Beam[%d].angle1" % beam)
        dec = self.get_float("Observation.Beam[%d].angle2" % beam)
        target_loc = dm.direction(EPOCH, "%frad" % ra, "%frad" % dec)
        name, sep = field_list.closest_to(target_loc)
        if sep <= threshold:
            return name

    def is_calibrator(self, threshold=0.1):
        if self.get_int("Observation.nrBeams") == 1:
            ra = self.get_float("Observation.Beam[0].angle1")
            dec = self.get_float("Observation.Beam[0].angle2")
            target_loc = dm.direction(EPOCH, "%frad" % ra, "%frad" % dec)
            min_name, min_sep = min(
                [
                    (calibrator[0], dm.separation(target_loc, calibrator[1]).get_value())
                    for calibrator in calibrators.items()
                ],
                key=lambda x: x[1]
            )
            if min_sep <= threshold:
                return min_name
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
        return self.parset.get('Observation.existingStations').expand().getStringVector()

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

def parse_field_file(filename):
    dm = measures()
    fields = FieldList()
    with open(filename, "r") as fieldfile:
        for line in fieldfile:
            name, ra, dec = line.split()
            fields[name] = dm.direction(EPOCH, ra, dec.replace(':', '.', 2))
    return fields


def upload_to_djangodb(parsets, field_list):

    from observationdb.models import Survey
    from observationdb.models import Field
    from observationdb.models import Station
    from observationdb.models import Observation
    from observationdb.models import Beam

    survey = Survey.objects.get(name="MSSS LBA")

    for calibrator, target in zip(parsets[::2], parsets[1::2]):
        cal_name = calibrator.is_calibrator()
        cal_field = Field.objects.get(name=cal_name)
        cal_antennaset = calibrator.get_string("Observation.antennaSet")
        cal_obsid = os.path.basename(calibrator.filename).rstrip(".parset")
        with open(calibrator.filename, 'r') as pset:
            cal_parset = pset.read()

        cal_observation = Observation(
            obsid=cal_obsid,
            antennaset=cal_antennaset,
            start_time=calibrator.start_time(),
            duration=calibrator.duration(),
            parset=cal_parset
        )
        cal_observation.save()
        cal_observation.stations = Station.objects.filter(name__in=calibrator.stations())
        cal_observation.save()

        cal_beam = Beam(
            observation=cal_observation,
            field=cal_field,
            beam = 0
        )
        cal_beam.save()

        with open(target.filename, 'r') as pset:
            target_parset = pset.read()

        target_observation = Observation(
            obsid=os.path.basename(target.filename).rstrip(".parset"),
            antennaset=target.get_string("Observation.antennaSet"),
            start_time=target.start_time(),
            duration=target.duration(),
            parset=target_parset
        )
        target_observation.save()
        target_observation.stations = Station.objects.filter(name__in=target.stations())
        target_observation.save()

        for beam in [0,1,2]:
            field_name = target.field_name(beam, field_list)
            if field_name:
                target_beam = Beam(
                    observation=target_observation,
                    calibrator=cal_beam,
                    field=Field.objects.get(name=field_name),
                    beam=beam
                )
                target_beam.save()


if __name__ == "__main__":
    field_list = parse_field_file(sys.argv[1])

    filenames = glob.glob("/home/jds/tmp/parsets/L52*.parset")
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
                upload_to_djangodb(parsets[idx:idx+72], field_list)
                for pset in  parsets[idx:idx+72]:
                    pset.allocated = True
                    if pset.is_calibrator():
                        print pset.filename, pset.is_calibrator(), pset.start_time()
                    else:
                        print pset.filename, pset.field_name(0, field_list), pset.field_name(1, field_list), pset.field_name(2, field_list), pset.start_time()
        if not parset.allocated and len(parsets[idx:idx+54]) == 54:
            if check_for_low_dec(parsets[idx:idx+54]):
                print "Got a run of 27 calibrators starting at %s %d" % (parset.filename, idx)
                upload_to_djangodb(parsets[idx:idx+54], field_list)
                for pset in  parsets[idx:idx+54]:
                    pset.allocated = True
                    if pset.is_calibrator():
                        print pset.filename, pset.is_calibrator(), pset.start_time()
                    else:
                        print pset.filename, pset.field_name(0, field_list), pset.field_name(1, field_list), pset.field_name(2, field_list), pset.start_time()
