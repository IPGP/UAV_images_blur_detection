#!/usr/bin/env python3
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
import os
import sys
import re
import logging
import pickle
import math
import datetime
from exif import Image as Image_exif
from folium.plugins import HeatMap
import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import variance
from skimage.filters import laplace
from skimage.filters import sobel
from PIL import Image

dateFormat = '%Y:%m:%d %H:%M:%S'

class PhotoDrone:
    def __init__(self, filename):
        self.filename = filename

# Verifier que le fichier existe

    # ouvrir le fichier et lire les exifs
        with open(self.filename, 'rb') as image_file:
            print(self.filename)

            image_exif = Image_exif(image_file)
            if not image_exif.has_exif:
                print('File {} does not have exif data'.format(image_file))
                sys.exit()
        #from IPython import embed; embed();sys.exit()
            self.gps_latitude = image_exif.gps_latitude
            self.gps_latitude_dec = image_exif.gps_latitude[0] + \
                image_exif.gps_latitude[1]/60+image_exif.gps_latitude[2]/3600

            self.gps_longitude = image_exif.gps_longitude
            self.gps_longitude_dec = image_exif.gps_longitude[0] + \
                image_exif.gps_longitude[1]/60+image_exif.gps_longitude[2]/3600

            self.gps_altitude = image_exif.gps_altitude

            self.datetime_original = image_exif.datetime_original
            self.gps_timestamp = image_exif.datetime_original.split()[1]
            self.epoch = datetime.datetime.strptime(self.datetime_original, dateFormat).timestamp()

            self.change_distance = False
            self.change_direction = False

            self.distance = 0.0
            self.direction = 0.0

#            from IPython import embed; embed();sys.exit()
    def print(self):
        print('{: >20}\t{: >20}\t{: >20}\t{: >20}\t{: >10}\t{: >10}'
        .format(self.filename, self.direction, self.distance, self.percent_distance_difference,
        self.change_distance,self.change_direction ))
        #print('{: >20}\t{: >20}\t{: >20}\t{}\t{: >10}\t{: >10}\t{: >10}\t{: >10}'
        #.format(self.filename, self.distance, self.percent_distance_difference,
        #self.change_distance, self.vari_laplace_1, self.maxi_laplace_1, self.vari_sobel_1, self.maxi_sobel_1))

    def compute_laplace_sobel(self):

        img = Image.open(self.filename)

        # square crops
        square_size = 300
        # im1.show()

        # square crops
        square_size = 400
        # Setting the points for cropped image
        width, height = img.size

        # Cropped image of above dimension
        # (It will not change orginal image)
        im1 = img.crop((0, 0, square_size, square_size))
        im2 = img.crop((0, height-square_size, square_size, height))
        im3 = img.crop((width-square_size, 0, width, square_size))
        im4 = img.crop((width-square_size, height-square_size, width, height))

        # Edge detection
        edge_laplace_1 = laplace(im1, ksize=3)
        edge_sobel_1 = sobel(im1)

        # Print output
        self.vari_laplace_1 = variance(edge_laplace_1)
        self.maxi_laplace_1 = np.amax(edge_laplace_1)
        self.vari_sobel_1 = variance(edge_sobel_1)
        self.maxi_sobel_1 = np.amax(edge_sobel_1)


class DronePhotosScan:

    def __init__(self, photos_directory, regex):
        self.photos_directory = photos_directory
        self.images = []

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
            self.images.append(PhotoDrone(self.photos_directory + '/'+file))

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
                image.distance = pow(pow(image.delta_x, 2)+pow(image.delta_y, 2), 0.5)

                # image.speed = image.distance / \
                #    (image.gps_timestamp_sec-last_image.gps_timestamp_sec)
                image.direction = math.degrees(
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
        for im in self.images:

            print('filename\tdistance\tdirection{}')
            print('{}\t{}\t{}'.format(im.filename, im.distance, im.direction))

    def check_changes(self,direction_offset = 2,distance_difference_limit = 20):
        last_image = False
        

        ##print('self.change_direction ')
        for image in self.images:
            image.percent_distance_difference = 100 * \
                (image.distance - self.average_distance)/self.average_distance
        
            if last_image:
                if ((image.percent_distance_difference) < 0) & (abs(image.percent_distance_difference) > distance_difference_limit):
                    #print('{}\t{}\t{}'.format(image.filename, image.distance, image.direction))
                    # print(image.filename)
                    image.change_distance = True
                else:
                    image.change_distance = False
                
                if abs(image.direction - last_image.direction) > direction_offset:
                    #print('{}\t{}\t{}'.format(image.filename, image.distance, image.direction))
                    image.change_direction = True
                else:
                    image.change_direction = False

                #### In case there is more than 10 secondes between images, remove change_direction and change_distance
                if abs(image.epoch - last_image.epoch) > 10:
                    last_image.change_direction = False
                    last_image.change_distance = False

            last_image = image


    def change_direction(self,direction_offset = 2):
        last_image = False
        

        ##print('self.change_direction ')
        for image in self.images:
            if last_image:
                if abs(image.direction - last_image.direction) > direction_offset:
                    #print('{}\t{}\t{}'.format(image.filename, image.distance, image.direction))
                    image.change_direction = True
                else:
                    image.change_direction = False
            last_image = image

    def change_distance(self,distance_difference_limit = 20):
        
        last_image = False
        for image in self.images:
            image.percent_distance_difference = 100 * \
                (image.distance - self.average_distance)/self.average_distance
            # print('{}\t{}\t'.format(image.filename,image.percent_distance_difference))
            if last_image:
                if ((image.percent_distance_difference) < 0) & (abs(image.percent_distance_difference) > distance_difference_limit):
                    #print('{}\t{}\t{}'.format(image.filename, image.distance, image.direction))
                    # print(image.filename)
                    image.change_distance = True
                else:
                    image.change_distance = False


            last_image = image

    def map_vectors(self):
        X = []
        Y = []
        U = []
        V = []
        C = []

        for img in self.images:
            X.append(img.gps_longitude_dec)
            Y.append(img.gps_latitude_dec)
            if (img.distance > self.average_distance*0, 75):
                U.append(math.cos(math.radians((img.direction)))*img.distance)
                V.append(math.sin(math.radians((img.direction)))*img.distance)
                C.append(0)
            else:
                U.append(math.cos(math.radians((img.direction)))*img.distance)
                V.append(math.sin(math.radians((img.direction)))*img.distance)
                C.append(10)

        Fig, Ax = plt.subplots()
        Ax.quiver(X, Y, U, V, C, units='xy', scale=1)
        #q = ax.quiver(X, Y, U, V, C, units='xy', scale=1)

        plt.grid()
        plt.show()



    def map(self):

        the_map = create_folium_map(tiles='openstreetmap')
        data = []
        for im in self.images:
            data.append(
                [im.gps_latitude_dec, im.gps_longitude_dec, im.distance])
        HeatMap(data, name='Heart rate', radius=5).add_to(the_map)
        boundary = the_map.get_bounds()
        the_map.fit_bounds(boundary, padding=(3, 3))
        the_map.save('map_000.html')
        # sys.exit()


def main():
    parser = ArgumentParser(prog='drone_photos_scan',
                            description='Scan Drones pictures to detect blurry ones',
                            formatter_class=ArgumentDefaultsHelpFormatter)

    parser.add_argument('-d', '--photos_directory', type=str, required=False,
                        help='The directory where drones pictures are. default is pwd', default=os.getcwd())

    parser.add_argument('-r', '--regex',  type=str, required=False,
                        help='Regex expression to filter images. Default is ".*jpg"',
                        default=".*(jpg|jpeg|JPEG|JPG)")

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

    # from_files = False
    # from_files = True

    # if from_files:
    #    # print("Init")
    #     project = DronePhotosScan(args.photos_directory, args.regex)
    #     #print("Compute data")
    #     project.compute_data()
    #     # print("change_direction")
    #     project.change_direction()
    #     project.change_distance()
    # # sauvegarde
    #     with open('multi.obj', 'wb') as file_pi:
    #         #        with open('multi.obj', 'wb') as file_pi:
    #         pickle.dump(project, file_pi)
    # else:
    #     with open('multi.obj', 'rb') as file_pi:
    #      #       with open('multi.obj', 'rb') as file_pi:
    #         project = pickle.load(file_pi)



    print("Init")
    project = DronePhotosScan(args.photos_directory, args.regex)
    print("Compute data")
    project.compute_data()
    print("check_changes")
    project.check_changes()

    print('The following images may be blurry')


    print('{: >50}\t{: >20}\t{: >20}\t{: >20}\t{: >5}\t{: >5}'
          .format('filename', 'distance', 'percent_distance_difference',
                  'direction', 'change_distance', 'change_direction'))
    count = 0
    for image in project.images:
       # image.compute_laplace_sobel()
        if image.change_distance:
            print('{: >50}\t{: >20}\t{: >20}\t{: >20}\t{: >5}\t{: >5}'
                  .format(image.filename, image.distance, image.percent_distance_difference,
                          image.direction, image.change_distance, image.change_direction))
            count=count+1

    print(str(count)+ ' images may be blurry')
 
    #from IPython import embed; embed()

    # print("Map")
    # project.map()
    # project.print_values()


if __name__ == '__main__':
    main()
