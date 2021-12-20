#!/usr/bin/env python3
# coding: utf-8

from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
import os
import sys
import re
import logging
import math
import datetime
from os import path
from geopy import distance
import exiftool
from cv2 import cv2
import numpy


DATE_FORMAT = '%Y:%m:%d %H:%M:%S'


def variance_of_laplacian(image):
    # compute the Laplacian of the image and then return the focus
    # measure, which is simply the variance of the Laplacian
    return cv2.Laplacian(image, cv2.CV_64F).var()


def compute_laplacian(image_path):
    percentage = 2
    # load the image, convert it to grayscale, and compute the
    # focus measure of the image using the Variance of Laplacian
    # method
    image = cv2.imread(image_path)
    #from IPython import embed; embed()

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    height, width, _ = image.shape
    crop_1 = gray[0:int(height*percentage/100), 0:int(width*5/100)]
    crop_2 = gray[0:int(height*percentage/100), width-int(width*5/100):width]
    crop_3 = gray[height - int(height*percentage/100):height, width-int(width*percentage/100):width]
    crop_4 = gray[height-int(height*percentage/100)
                             :height, 0:int(width*percentage/100)]

    fm_crops = []
    var = []
    fm_crops.append(variance_of_laplacian(crop_1))
    fm_crops.append(variance_of_laplacian(crop_2))
    fm_crops.append(variance_of_laplacian(crop_3))
    fm_crops.append(variance_of_laplacian(crop_4))
    var.append(numpy.max(cv2.convertScaleAbs(cv2.Laplacian(crop_1, 3))))
    var.append(numpy.max(cv2.convertScaleAbs(cv2.Laplacian(crop_2, 3))))
    var.append(numpy.max(cv2.convertScaleAbs(cv2.Laplacian(crop_3, 3))))
    var.append(numpy.max(cv2.convertScaleAbs(cv2.Laplacian(crop_4, 3))))

    with exiftool.ExifTool() as et:
        metadata = et.get_metadata(filename=image_path)
    inverse_speed = metadata['Composite:ShutterSpeed']
    speed = int(1/inverse_speed)

    seuil = 330
    somme_convertScaleAbs = int(var[0])+int(var[1])+int(var[2])+int(var[3])

    if (int(var[0])+int(var[1])+int(var[2])+int(var[3])) < seuil:
        text = 'Blurry'
        print(
            F"{image_path}\tfm_crop {fm_crops[0]:.0f} {fm_crops[1]:.0f} {fm_crops[2]:.0f} {fm_crops[3]:.0f}\t convertScaleAbs: {somme_convertScaleAbs}\t speed: 1/{speed}\t{text}")
        return 1
    return 0


class PhotoDrone:
    def __init__(self, directory, file):
        self.file = file
        self.photos_directory = directory
        self.filename = directory+file

        print(self.filename)

        # Read exifs
        with exiftool.ExifTool() as exifreader:
            image_exif = exifreader.get_metadata(self.filename)

        self.gps_latitude = image_exif['Composite:GPSLatitude']
        self.gps_latitude_dec = image_exif['Composite:GPSLatitude']

        self.gps_longitude = image_exif['Composite:GPSLongitude']
        self.gps_longitude_dec = image_exif['Composite:GPSLongitude']

        #self.gps_altitude = image_exif[ 'Composite:GPSAltitude']
        self.datetime_original = image_exif['EXIF:DateTimeOriginal']

       # from IPython import embed; embed();sys.exit()

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
            print(F'Directory {self.photos_directory} is empty')
            sys.exit()
        # search all files without hidden ones
        all_files = sorted([f for f in os.listdir(
            self.photos_directory) if not f.startswith('.')])

        # filter with regex
        regex_filter = re.compile(regex, re.MULTILINE)
        files = [f for f in all_files if regex_filter.search(f)]

        # for each picture, create an photo_drone object
        for file in enumerate(files):
            self.images.append(PhotoDrone(self.photos_directory + '/', file))
            # if i>255:
            #    break

        if len(files) == 0:
            print(
                F'{self.photos_directory} does not contains images with this REGEX {regex}')
            sys.exit(-1)
        print(len(files))

    def compute_data(self):
        first_image = True

        for image in self.images:
            if first_image:
                image.distance = 0.0
                image.direction = 0.0
               # image.speed = 0.0
                image.first_image = True
                first_image = False
                image.delta_t = 0

            else:
                image.first_image = False
                image.delta_x = image.gps_longitude_dec-last_image.gps_longitude_dec
                image.delta_y = image.gps_latitude_dec-last_image.gps_latitude_dec
                image.delta_t = image.epoch-last_image.epoch
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
                # print('{}\t{}\t{}\t{}'.format(
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
            print('{}\t{}\t{}'.format(image.filename,
                  image.distance, image.direction))

    def check_changes(self, direction_offset=40, distance_difference_limit=20):
        previous_image = False

        ##print('self.change_direction ')
        for image in self.images:
            image.percent_distance_difference = 100 * \
                (image.distance - self.average_distance)/self.average_distance

            if previous_image:
                image.direction_difference = image.direction - previous_image.direction

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
                if abs(image.epoch - previous_image.epoch) > 30:
                    previous_image.change_direction = False
                    previous_image.change_distance = False
                    image.is_blurry = False
                    image.first_image = True

                # 2nd image should be not blurry. Drone is accelerating
                if previous_image.first_image :
                    image.second_image = True
                    image.is_blurry = False

            else:
                # première image de la série
                image.first_image = True

            previous_image = image


def main():
    parser = ArgumentParser(prog='drone_photos_scan',
                            description='Scan Drones pictures to detect blurry ones',
                            formatter_class=ArgumentDefaultsHelpFormatter)

    parser.add_argument('-d', '--photos_directory', type=str, required=True,
                        help='The directory where drones pictures are. default is pwd')

    parser.add_argument('-r', '--regex',  type=str, required=False,
                        help='Regex expression to filter images. \
                        Default is ".*(jpg|jpeg|JPEG|JPG)"',
                        default='.*(jpg|jpeg|JPEG|JPG)')

    parser.add_argument('-v', '--verbose', default=False,
                        action="store_true", dest="verbose",
                        help='show verbose debugging output')

    # parse the arguments
    args = parser.parse_args()

    if not path.exists(args.photos_directory):
        print(F'{args.photos_directory} does not exist')
        sys.exit(-1)

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

    print(F"{'file': ^50}\t{'distance': ^10}\t{'%_dist_diff': ^10}\t{'direction': ^10}\t{'dir_diff': ^10}\t{'chg_dist': ^8}\t{'chg_dir': ^8}")

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
    count_laplacian = 0

    for image in project.images:
        if image.is_blurry:
            # print('{: ^20}\t{:>10.2f}\t{:>10.2f}\t{:>10.2f}\t{:>10.2f}\t{: ^8}\t{: ^8}'
            #      .format(image.file, image.distance, image.percent_distance_difference,
            #              image.direction, image.direction_difference,
            #               image.change_distance, image.change_direction))
            count_laplacian += compute_laplacian(
                args.photos_directory+'/'+image.file)

            count = count+1

    #print(str(count) + ' images may be blurry')
    print(str(count_laplacian) + ' images may be blurry with laplacian test')

   # from IPython import embed; embed()


if __name__ == '__main__':
    main()
