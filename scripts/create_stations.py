import sys
from obsdb.observationdb.models import Station

if __name__ == "__main__":
    station_file = sys.argv[1]

    with open(station_file, 'r') as f:
        lines = f.readlines()

    stations = []
    for line in lines:
        split_string = line.split(None, 5)
        name = split_string[0]
        idnumber = int(split_string[1])
        longitude = float(split_string[2])
        latitude = float(split_string[3])
        altitude = float(split_string[4])
        if len(split_string) == 6:
            description = split_string[5]
        else:
            description = ""
        stations.append(
            Station(name=name, idnumber=idnumber, longitude=longitude,
                latitude=latitude, altitude=altitude, description=description
            )
        )

    Station.objects.bulk_create(stations)
