# Generate mapping between MSSS slices and MoM IDs.
# Requested by Alwin de Jong, 2012-09-06.

from obsdb.observationdb.models import Field
from obsdb.observationdb.models import Constants
from cStringIO import StringIO
from itertools import izip
import re
import os

output_dir = "/tmp/alwin-msss"
project_name = "MSSS LBA"
n_slices = 9

def get_mom_id(parset, beam):
    m = re.search(r"Observation.Beam\[%d\].momID = (\d+)" % (beam,), parset)
    return int(m.groups()[0])

for field in Field.objects.filter(survey__name=project_name):
    if field.name == "NCP":
        print "Skipping NCP"
        continue

    if field.calibrator:
        print "Skipping %s: Calibrator" % (field.name)
        continue

    if not field.on_cep in (Constants.TRUE, Constants.PARTIAL):
        print "Skipping %s: not on CEP" % (field.name)
        continue

    if field.beam_set.count() % n_slices:
        print "%s is a problem: %d beams" % (field.name, field.beam_set.count())
        continue

    print "Processing %s" % (field.name)

    for beam_group in izip(*[iter(field.beam_set.all())]*n_slices):
        output = StringIO()
        package_name = "%d_Slices_%s" % (n_slices, beam_group[0].observation.start_time.strftime("%b%d_%H:%M"))
        package_description = "%s %s %d-slices" % (beam_group[0].observation.start_time.strftime("%b%d %H:%M"), project_name, n_slices)
        print >>output, "projectName=%s;" % (project_name,)
        print >>output, "packageName=%s;" % (package_name,)
        print >>output, "packageDescription=%s;" % (package_description,)

        have_data = False
        for ctr, beam in enumerate(beam_group):
            if beam.on_cep in (Constants.TRUE, Constants.PARTIAL):
                have_data = True
            n_slice = ctr+1
            observation = beam.observation
            cal_observation = observation.get_previous_by_start_time()
            assert(cal_observation.beam_set.count() == 1)
            print >>output, ""
            print >>output, "slice%d.calibrator.mom2Id:mom2Id=%d;" % (n_slice, get_mom_id(cal_observation.parset, 0)-1)
            print >>output, "slice%d.calibrator.calibratorSource=%s;" % (n_slice, cal_observation.beam_set.all()[0].field.name)
            print >>output, "slice%d.beam0.mom2Id:mom2Id=%d;" % (n_slice, get_mom_id(cal_observation.parset, 0),)
            print >>output, "slice%d.target.mom2Id:mom2Id=%d;" % (n_slice, get_mom_id(observation.parset, 0)-1)

            for n_beam in range(3):
                try:
                    print >>output, "slice%d.beam%d.mom2Id:mom2Id=%d;" % (n_slice, n_beam+1, get_mom_id(observation.parset, n_beam))
                except AttributeError:
                    print "Observation %s missing beam %d" % (observation.obsid, n_beam)


        if have_data:
            print "Data on CEP; writing out description"
            with open(os.path.join(output_dir, package_name), 'w') as f:
                f.write(output.getvalue())
        else:
            print "No data on CEP"
