blur_scan will detect in a set of UAV images the ones that could be blurry. Those images are usually taken when the UAV is changing direction and with a low speed. 
blur_scan scan a directory with a regex filter and create a list of potentially blurry iamges and an html map with the images. 
<img src="https://github.com/IPGP/UAV_images_blur_detection/blob/main/map_exemple.png" width="800px" height="auto">


# Requirements
`pip3 install exiftool geopy gpxplotter folium`

# usage
`blur_scan.py -d /directory/images -r "IMG.*JPG"`
