import sys
from pyrap.quanta import quantity
from obsdb.observationdb.models import Survey, Field

def insert_grid_points(survey, filename, calibrator=False):
    with open(filename, 'r') as f:
        lines = f.readlines()

    for line in lines:
        split_string = line.split(None, 3)
        name = split_string[0]
        ra = quantity(split_string[1]).get_value('rad')
        dec = quantity(split_string[2].replace(":", ".", 2)).get_value('rad')
        if len(split_string) == 4:
            description = split_string[3].strip()
        else:
            description = ""
        f = Field.objects.create(
            name=name, ra=ra, dec=dec, description=description,
            survey=survey, calibrator=calibrator
        )

if __name__ == "__main__":
    survey_name = sys.argv[1]
    field_size = float(sys.argv[2])
    beams_per_field = int(sys.argv[3])
    calibrator_filename = sys.argv[4]
    grid_filename = sys.argv[5]

    survey, created = Survey.objects.get_or_create(
        name=survey_name, field_size=field_size, beams_per_field=beams_per_field
    )
    insert_grid_points(survey, calibrator_filename, calibrator=True)
    insert_grid_points(survey, grid_filename, calibrator=False)
