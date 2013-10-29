import sys
import os
import gc
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

SURVEY = "MSSS LBA"

class Parset(object):
    __slots__ = [
        "filename",
        "allocated",
        "positions",
        "time",
        "stations",
        "subbands",
        "clock",
        "antennaset",
        "filter",
        "campaign"
    ]

    def __init__(self, filename):
        parset = parameterset(filename)
        self.filename = filename
        self.allocated = False

        self.positions = []
        self.subbands = []
        try:
            for beam in range(parset.getInt("Observation.nrBeams")):
                ra = parset.getFloat("Observation.Beam[%d].angle1" % beam)
                dec = parset.getFloat("Observation.Beam[%d].angle2" % beam)
                self.positions.append((ra, dec))
                try:
                    self.subbands.append(parset.get('Observation.Beam[%d].subbandList' % beam).expand().getIntVector())
                except RuntimeError:
                    self.subbands.append([])
        except RuntimeError:
            pass

        try:
            self.time = [
                parset.getString('Observation.startTime'),
                parset.getString('Observation.stopTime'),
            ]
        except RuntimeError:
            self.time = []

        try:
            self.stations = parset.get('Observation.VirtualInstrument.stationList').expand().getStringVector()
        except RuntimeError:
            self.stations = []
        try:
            self.clock = int(parset.getString("Observation.clockMode")[-3:])
        except RuntimeError:
            self.clock = None
        try:
            self.antennaset = parset.getString('Observation.antennaSet')
        except RuntimeError:
            self.antennaset = None
        try:
            self.filter = parset.getString("Observation.bandFilter")
        except RuntimeError:
            self.filter = None
        self.campaign = {}
        if "Observation.Campaign.name" in parset.keys():
            self.campaign['name'] = parset.getString("Observation.Campaign.name")
        else:
            self.campaign['name'] = None
        if "Observation.Campaign.title" in parset.keys():
            self.campaign['title'] = parset.getString("Observation.Campaign.title")
        else:
            self.campaign['title'] = None

    def get_field(self, beam, survey_name, threshold=0.05):
        ra, dec = self.positions[beam]
        try:
            return Field.objects.near_position(
                ra, dec, threshold
            ).filter(
                survey__name=survey_name
            ).order_by("distance")[0]
        except:
            pass

    def is_calibrator(self, survey_name, threshold=0.05):
        if len(self.positions) == 1:
            ra, dec = self.positions[0]
            try:
                return Field.objects.near_position(
                    ra, dec, threshold
                ).filter(
                    survey__name=survey_name, calibrator=True
                ).order_by("distance")[0].name
            except:
                pass
        return False

    def start_time(self):
        return datetime.datetime.strptime(self.time[0], "%Y-%m-%d %H:%M:%S")

    def duration(self):
        end_time = datetime.datetime.strptime(self.time[1], "%Y-%m-%d %H:%M:%S")
        duration = end_time - self.start_time()
        return duration.seconds

    def get_subbands(self, beam):
        return self.subbands[beam]

def load_parsets(filenames):
    return [Parset(filename) for filename in filenames]

def check_for_msss_lba_run(parsets, length, start_positions, step):
    assert(len(parsets) == length)
    survey_name="MSSS LBA"

    # Zeroth check: no data reuse
    if True in [parset.allocated for parset in parsets]:
        return False

    # First check: every second observation is of the same calibrator
    calibrators = {parset.is_calibrator(survey_name) for parset in parsets[::2]}
    if False in calibrators or len(calibrators) != 1:
        return False

    # Second check: every other observation has 3 or 4 beams
    nr_beams = {len(parset.positions) for parset in parsets[1::2]}
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
                        parset.positions[beam]
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
    return check_for_msss_lba_run(parsets, 72, [1,3,5,7], 8)

def check_for_low_dec(parsets):
    return check_for_msss_lba_run(parsets, 54, [1,3,5], 6)


def upload_to_djangodb(parsets, survey_name):
    survey = Survey.objects.get(name=survey_name)

    for parset in parsets:
        obsid = os.path.basename(parset.filename).rstrip(".parset")
        with open(parset.filename, 'r') as parset_file:
            parset_contents = parset_file.read()

        observation = Observation.objects.create(
            obsid=obsid,
            antennaset=parset.antennaset,
            start_time=parset.start_time(),
            duration=parset.duration(),
            parset=parset_contents,
            clock=parset.clock,
            filter=parset.filter
        )
        observation.stations = Station.objects.filter(name__in=parset.stations)
        observation.save()

        sb_ctr = 0
        for beam_number in range(len(parset.positions)):
            field = parset.get_field(beam_number, survey_name)
            if field:
                beam = Beam.objects.create(
                    observation=observation,
                    field=field,
                    beam=beam_number
                )
                beam.subbands = Subband.objects.filter(number__in=parset.get_subbands(beam_number))
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
    # Ensure we don't have any garbage lying around.
    gc.collect()


def get_file_list(root_dir):
    matches = []
    seen = set()
    for root, dirnames, filenames in os.walk(root_dir):
        for filename in fnmatch.filter(filenames, "*.parset"):
            if filename not in seen:
                matches.append(os.path.join(root, filename))
                seen.add(filename)
    return matches

if __name__ == "__main__":
    if not Subband.objects.count() == 513:
        Subband.objects.bulk_create(
            [Subband(number=number) for number in xrange(513)]
        )

    print "Getting filenames..."
    filenames = get_file_list(sys.argv[1])
    print "%d filenames." % (len(filenames),)

    print "Loading parsets..."
    parsets = load_parsets(filenames)
    print "%d parsets." % (len(parsets),)

    print "Searching for MSSS HBA..."
    for parset in parsets:
        if (parset.campaign["name"] == "MSSS_HBA_2013" and
            parset.campaign["title"] == "MSSS HBA Survey"
        ):
            print "Adding %s to MSSS HBA" % parset.filename
            upload_to_djangodb([parset], "MSSS HBA")
    print "done."

    print "Filtering parsets..."
    parsets = [parset for parset in parsets if parset.campaign['name'] == "MSSS"]
    print "%d filtered parsets." % (len(parsets),)

    print "Sorting parsets..."
    parsets.sort(key=lambda parset: parset.start_time())
    print "%d sorted parsets." % (len(parsets),)

    print "Searching for MSSS LBA..."
    for idx, parset in enumerate(parsets):
        if not parset.allocated and len(parsets[idx:idx+72]) == 72:
            if check_for_high_dec(parsets[idx:idx+72]):
                print "Got a run of 36 calibrators starting at %s %d" % (parset.filename, idx)
                upload_to_djangodb(parsets[idx:idx+72], "MSSS LBA")
                for pset in  parsets[idx:idx+72]:
                    pset.allocated = True
        if not parset.allocated and len(parsets[idx:idx+54]) == 54:
            if check_for_low_dec(parsets[idx:idx+54]):
                print "Got a run of 27 calibrators starting at %s %d" % (parset.filename, idx)
                upload_to_djangodb(parsets[idx:idx+54], "MSSS LBA")
                for pset in  parsets[idx:idx+54]:
                    pset.allocated = True
    print "done."
