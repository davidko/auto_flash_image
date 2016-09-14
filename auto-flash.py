#!/usr/bin/env python3

import hashlib
import linkbot3 as linkbot
import logging
import os
import stat
import subprocess
import time
import traceback

SD_CARD_DEVICE = '/dev/sda1'

force_flash_command = False

logging.basicConfig(level=logging.DEBUG)

IMAGE_FILENAME='barobo-odroid-20160913.img'

def button_callback(button, state, timestamp):
    global force_flash_command
    if (button == 1) and (state == 1):
        force_flash_command = True

def disk_exists(path):
    try:
        return stat.S_ISBLK(os.stat(path).st_mode)
    except:
        return False

def flash_sd_card(my_linkbot):
    # First, try to unmount the sd card
    try:
        logging.debug('Unmounting sd card...')
        subprocess.check_call(["udisks", "--unmount", SD_CARD_DEVICE])
    except Exception as e:
        logging.warning('Failed to umount sd card: {}'.format(traceback.format_exc()))

    # Turn the robot led yellow
    logging.info("Setting LED to yellow...")
    my_linkbot.led.set_color(255, 255, 0)

    # Now, run the dd command
    logging.info("Running dd command...")
    subprocess.check_call(["dd", "if={}".format(IMAGE_FILENAME), "of=/dev/sda", "bs=4M"])

    # run `sync`
    logging.info("Running sync command...")
    subprocess.check_call(["sync", ])

    # Verify the image flashed correctly
    # Get the image size
    statinfo = os.stat(IMAGE_FILENAME)
    size = statinfo.st_size

    with open("{}.md5sum".format(IMAGE_FILENAME), 'r') as md5file:
        md5sum = md5file.read().split()[0]

    with open('/dev/sda', 'rb') as sd_card_image:
        calculated_md5 = hashlib.md5()
        bytes_left = size
        while bytes_left > 0:
            readsize = min(128, bytes_left)
            chunk = sd_card_image.read(readsize)
            bytes_left -= readsize
            if not chunk:
                break
            calculated_md5.update(chunk)
        digest = calculated_md5.hexdigest()

    if digest != md5sum:
        # Turn the robot red
        logging.info("Setting led color to red...")
        my_linkbot.led.set_color(255, 0, 0)

    else:
        # Turn the robot led green
        logging.info("Setting led color to green...")
        my_linkbot.led.set_color(0, 255, 0)

    # Wait for the SD card to be removed
    while disk_exists(SD_CARD_DEVICE):
        logging.info("SD card still plugged in. Waiting 1 second...")
        time.sleep(1)

    # Turn the LED red
    logging.info("SD card removed.")
    my_linkbot.led.set_color(0, 0, 255)

def main():
    # First, see if we can connect to a Linkbot
    while True:
        try:
            l = linkbot.Linkbot('locl')
            l.led.set_color(0, 0, 255)
            l.buttons.set_event_handler(button_callback)
            break
        except:
            logging.warning('Could not connect to Linkbot. Waiting for 10 seconds...')
            time.sleep(10)

    logging.info('Ready to begin flashing SD cards.')

    global force_flash_command
    while True:
        # Now, we should check to see if the SD card is plugged in
        if disk_exists(SD_CARD_DEVICE) or force_flash_command:
            force_flash_command = False
            logging.debug('SD card detected.')
            try:
                flash_sd_card(l)
            except Exception as e:
                print("Failed to flash SD card: {}".format(traceback.format_exc()))
        else:
            logging.debug('No sd card detected. waiting for 1 second...')
            time.sleep(1)

if __name__ == '__main__':
    main()
