blur_scan will detect in a set of UAV images the ones that could be blurry. Those images are usually taken when the UAV is changing direction and with a low speed. 
blur_scan scan a directory with a regex filter and create a list of potentially blurry images.
<img src="https://github.com/IPGP/UAV_images_blur_detection/blob/main/map_exemple.png" width="800px" height="auto">


# Requirements
`pip install -r requirements.txt`
# usage
`blur_scan.py  /directory/images -r "IMG.*JPG"`
or
`blur_scan.py  `
