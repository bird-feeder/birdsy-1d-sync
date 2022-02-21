import os
from glob import glob
from pathlib import Path

import cv2
from loguru import logger
from tqdm import tqdm


def get_frames(video_path, output_folder):
    """
    https://stackoverflow.com/questions/54045766/python-extracting-distinct-unique-frames-from-videos
    """
    video = cv2.VideoCapture(video_path)
    Path(output_folder).mkdir(exist_ok=True)

    (major_ver, minor_ver, subminor_ver) = (cv2.__version__).split('.')
    if int(major_ver) < 3:
        fps = int(video.get(cv2.cv.CV_CAP_PROP_FPS))
    else:
        fps = int(video.get(cv2.CAP_PROP_FPS))

    currentframe = 0
    extracted_frames = 0

    while True:
        ret, frame = video.read()
        if ret:
            name = f'{output_folder}/{Path(video_path).stem}__frame_{currentframe}.jpg'
            if currentframe % fps == 1:
                cv2.imwrite(name, frame)
                extracted_frames += 1
            currentframe += 1
        else:
            break

    logger.info(
        f'VIDEO: {Path(video_path).name} | FPS: {fps} | TOTAL: {currentframe}'
        f' | EXTRACTED: {extracted_frames}')
    video.release()


if __name__ == '__main__':
    logger.add('logs.log')
    for file in tqdm(glob(f'birdsy/*.mp4')):
        get_frames(file, 'birdsy-frames')
