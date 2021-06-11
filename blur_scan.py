#!/usr/bin/env python3
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
import os
import sys
import re
import logging
import math
import datetime
#from exif import Image as Image_exif
from geopy import distance
import folium
from gpxplotter import create_folium_map
import exiftool  

DATE_FORMAT = '%Y:%m:%d %H:%M:%S'


class PhotoDrone:
    def __init__(self, directory, file):
        self.file = file
        self.photos_directory = directory
        self.filename = directory+file


        print(self.filename)

        # Lire les exifs fichier et lire les exifs
        with exiftool.ExifTool() as et:
            image_exif  = et.get_metadata(self.filename)

        self.gps_latitude = image_exif[ 'Composite:GPSLatitude']
        self.gps_latitude_dec = image_exif[ 'Composite:GPSLatitude']

        self.gps_longitude =  image_exif[ 'Composite:GPSLongitude']
        self.gps_longitude_dec =  image_exif[ 'Composite:GPSLongitude']
        
        #self.gps_altitude = image_exif[ 'Composite:GPSAltitude']
        self.datetime_original = image_exif['EXIF:DateTimeOriginal']
        
       # from IPython import embed; embed();sys.exit()


        #self.gps_timestamp = image_exif.datetime_original.split()[1]
        self.epoch = datetime.datetime.strptime(
            self.datetime_original, DATE_FORMAT).timestamp()

        self.change_distance = False
        self.change_direction = False

        self.distance = 0.0
        self.direction = 999
        self.direction_difference = 0.0
        self.percent_distance_difference = 0

        self.is_blurry = False
        self.first_image = False

#            from IPython import embed; embed();sys.exit()
    def print(self):
        print('{: >20}\t{: >20}\t{: >20}\t{: >20}\t{: >10}\t{: >10}'
              .format(self.filename, self.direction, self.distance,
                      self.percent_distance_difference,
                      self.change_distance, self.change_direction))


class BlurScan:

    def __init__(self, photos_directory, regex):
        self.photos_directory = photos_directory
        self.images = []
        self.images_nb = None
        self.average_distance = None

        if len([f for f in os.listdir(self.photos_directory) if not f.startswith('.')]) == 0:
            print('Directory {} is empty'.format(self.photos_directory))
            sys.exit()
        # search all files without hidden ones
        all_files = sorted([f for f in os.listdir(
            self.photos_directory) if not f.startswith('.')])

        # filter with regex
        regex_filter = re.compile(regex, re.MULTILINE)
        files = [f for f in all_files if regex_filter.search(f)]

        # for each picture, create an photo_drone object
        for file in files:
            self.images.append(PhotoDrone(self.photos_directory + '/', file))

    def compute_data(self):
        first_image = True

        for image in self.images:
            if first_image:
                image.distance = 0.0
                image.direction = 0.0
               # image.speed = 0.0
                first_image = False
            else:
                image.delta_x = image.gps_longitude_dec-last_image.gps_longitude_dec
                image.delta_y = image.gps_latitude_dec-last_image.gps_latitude_dec
                #last_image.distance = 10000*pow(pow(delta_x, 2)+pow(delta_y, 2), 0.5)
                #image.distance = 100000*pow(pow(image.delta_x, 2)+pow(image.delta_y, 2), 0.5)
                coords_1 = (image.gps_longitude_dec, image.gps_latitude_dec)
                coords_2 = (last_image.gps_longitude_dec,
                            last_image.gps_latitude_dec)

                image.distance = distance.geodesic(coords_1, coords_2).m

                # image.speed = image.distance / \
                #    (image.gps_timestamp_sec-last_image.gps_timestamp_sec)
                last_image.direction = math.degrees(
                    math.atan2(image.delta_y, image.delta_x))
                #print('{}\t{}\t{}\t{}'.format(
                #    image.delta_x, image.delta_y, image.distance, image.direction))
            last_image = image

        ### average_speed and average_distance
        self.images_nb = len(self.images)
        # self.average_speed = (
        #     sum(im.speed for im in self.images))/self.images_nb
        self.average_distance = sum(
            im.distance for im in self.images)/self.images_nb
        print("Average_distance " + str(self.average_distance))

    def print_values(self):
        for image in self.images:

            print('filename\tdistance\tdirection{}')
            print('{}\t{}\t{}'.format(image.filename, image.distance, image.direction))

    def check_changes(self, direction_offset=40, distance_difference_limit=20):
        last_image = False

        ##print('self.change_direction ')
        for image in self.images:
            image.percent_distance_difference = 100 * \
                (image.distance - self.average_distance)/self.average_distance

            if last_image:
                image.direction_difference = image.direction - last_image.direction

                # image.direction = 999 for the last image
                if ((image.percent_distance_difference) < 0
                    and abs(image.percent_distance_difference) > distance_difference_limit
                        and (image.direction < 999)):

                    image.change_distance = True
                    image.is_blurry = True
                else:
                    image.change_distance = False

                # image.direction = 999 for the last image

                if abs(((image.direction_difference) > direction_offset) & (image.direction < 999)):
                    image.change_direction = True
                    image.is_blurry = True
                else:
                    image.change_direction = False

                # In case there is more than 10 secondes between images
                # remove change_direction and change_distance
                if abs(image.epoch - last_image.epoch) > 10:
                    last_image.change_direction = False
                    last_image.change_distance = False
                    image.is_blurry = False
            else:
                # première image de la série
                image.first_image = True

            last_image = image

    def map(self):

        the_map = create_folium_map(zoom_start=3, max_zoom=50)

        # Add custom base maps to folium
        basemaps = {
            'Google Maps': folium.TileLayer(
                tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}',
                attr='Google',
                name='Google Maps',
                overlay=False,
                control=True
            ),
            'Google Satellite': folium.TileLayer(
                tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
                attr='Google',
                name='Google Satellite',
                overlay=True,
                control=True
            ),
            'Google Terrain': folium.TileLayer(
                tiles='https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}',
                attr='Google',
                name='Google Terrain',
                overlay=True,
                control=True
            ),
            'Google Satellite Hybrid': folium.TileLayer(
                tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
                attr='Google',
                name='Google Satellite',
                overlay=True,
                control=True
            ),
            'Esri Satellite': folium.TileLayer(
                tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attr='Esri',
                name='Esri Satellite',
                overlay=True,
                control=True
            )
        }

        # Add custom basemaps
        basemaps['Google Maps'].add_to(the_map)
        basemaps['Google Satellite'].add_to(the_map)
        basemaps['Google Terrain'].add_to(the_map)
        basemaps['Google Satellite Hybrid'].add_to(the_map)
        basemaps['Esri Satellite'].add_to(the_map)

        tiles_maps = ['openstreetmap', 'Stamen Terrain']
        # tiles_maps=[ 'openstreetmap',''Cartodb Positron',
        # 'Stamen Terrain','Stamen Toner','Stamen Watercolor']
        for tile in tiles_maps:
            folium.TileLayer(tile).add_to(the_map)

        folium.LayerControl(sortLayers=False).add_to(the_map)

        for image in self.images:
            if image.is_blurry:
                color_image = 'darkred'
            else:
                color_image = 'green'

            folium.Marker(
                location=[image.gps_latitude_dec, image.gps_longitude_dec],
                popup=image.filename,
                # color=color_image,
                #                icon=folium.Icon(color=color_image,icon='fas fa-camera')
                icon=folium.Icon(color=color_image, icon='fa-map-pin')

            ).add_to(the_map)

        boundary = the_map.get_bounds()
        the_map.fit_bounds(boundary, padding=(3, 3))

        the_map.save(self.photos_directory+'/carte.html')
        # sys.exit()


def main():
    parser = ArgumentParser(prog='drone_photos_scan',
                            description='Scan Drones pictures to detect blurry ones',
                            formatter_class=ArgumentDefaultsHelpFormatter)

    parser.add_argument('-d', '--photos_directory', type=str, required=True,
                        help='The directory where drones pictures are. default is pwd')
    # default=os.getcwd())

    parser.add_argument('-r', '--regex',  type=str, required=False,
                        help='Regex expression to filter images. \
                        Default is ".*(jpg|jpeg|JPEG|JPG)"',
                        default='.*(jpg|jpeg|JPEG|JPG)')

    parser.add_argument('-v', '--verbose', default=False,
                        action="store_true", dest="verbose",
                        help='show verbose debugging output')

    # parse the arguments
    args = parser.parse_args()

    # absolut and relative path
    if not os.path.isabs(args.photos_directory):
        args.photos_directory = os.path.abspath(args.photos_directory)

    if args.verbose:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.CRITICAL
    logging.basicConfig(level=loglevel)

#########################################################


    project = BlurScan(args.photos_directory, args.regex)
    print("Compute data")
    project.compute_data()
    print("check_changes")
    project.check_changes(direction_offset=40, distance_difference_limit=20)

    print('{: ^50}\t{: ^10}\t{: ^10}\t{: ^10}\t{: ^10}\t{: ^8}\t{: ^8}'
          .format('file', 'distance', '%_dist_diff',
                  'direction', 'dir_diff', 'chg_dist', 'chg_dir'))
    for image in project.images:
        print('{: ^50}\t{:>10.2f}\t{:>10.2f}\t{:>10.2f}\t{:>10.2f}\t{: ^8}\t{: ^8}'
              .format(image.filename, image.distance, image.percent_distance_difference,
                      image.direction, image.direction_difference,
                      image.change_distance, image.change_direction))

    print('The following images may be blurry')
    print('{: ^20}\t{: ^10}\t{: ^10}\t{: ^10}\t{: ^10}\t{: ^8}\t{: ^8}'
          .format('file', 'distance', '%_dist_diff',
                  'direction', 'dir_diff', 'chg_dist', 'chg_dir'))
    count = 0
    for image in project.images:
        if image.is_blurry:
            print('{: ^20}\t{:>10.2f}\t{:>10.2f}\t{:>10.2f}\t{:>10.2f}\t{: ^8}\t{: ^8}'
                  .format(image.file, image.distance, image.percent_distance_difference,
                          image.direction, image.direction_difference,
                           image.change_distance, image.change_direction))
            count = count+1

    print(str(count) + ' images may be blurry')

    project.map()

   # from IPython import embed; embed()

if __name__ == '__main__':
    main()
