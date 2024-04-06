# Copyright 2023-2024 antillia.com Toshiyuki Arai
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


# EBHIColorectalImageMaskDatasetGenerator.py
# 2024/04/06 antillia.com

import os
import sys
import glob
import shutil
import numpy as np

import cv2
from PIL import Image, ImageOps
import traceback
import random


class EBHIColorectalImageMaskDatasetGenerator:
  def __init__(self, resize=512, augmentation = False):
    self.W      = resize
    self.H      = resize
    self.RESIZE = (self.W, self.H)

    self.augmentation = augmentation
    if self.augmentation:
      self.hflip = True
      self.vflip = True
      self.rotation = True
      self.ANGLES   =[90, 180, 270]

  def generate(self, root_dir, output_dir):
    dirs = os.listdir(root_dir)
    print("--- dirs {}".format(dirs))
    categories = []
    for dir in dirs:
      if os.path.isdir(root_dir + "/" + dir):
        categories += [dir]
    
    random.seed(137)
    # PIL color format (R, G, B)
    mask_colors = [(110,  80,  50),   # mustard
                   (240, 130, 240),   # violet
                   (255, 255,   0),   # yellow
                   (255, 255,  255),  # white
                   (  0, 255,   0),   # green
                   (  0,   0, 255)]   # blue

    for i, category in enumerate(categories):
      color = mask_colors[i]
      full_category = os.path.join(root_dir, category)
      print("--- category {}".format(full_category))

      if not os.path.isdir(full_category):
        print("NOT DIR skip {}".format(full_category))
        continue
      
      images_dir  = os.path.join(full_category, "image")
      masks_dir   = os.path.join(full_category, "label")

      #output_category = os.path.join(output_dir, category)
      output_images_dir = "/images"
      output_masks_dir  = "/masks"
      self.generate_one(images_dir, masks_dir, color, output_dir, category, 
                output_images_dir, output_masks_dir)
      
  def generate_one(self, images_dir, masks_dir, color, output_dir, category, 
                output_images_dir, output_masks_dir):
    print("=== split_one {} {}".format(images_dir, output_dir))
    #input("--- split_one")
    image_files = glob.glob(images_dir + "/*.png")
    random.shuffle(image_files)
    num = len(image_files)
    if num == 0:
      input("FATAL Error")
      return 
    num_train = int(num * 0.7)
    num_valid = int(num * 0.2)
    num_test  = int(num * 0.1)
    print("num_train {}".format(num_train))
    print("num_valid {}".format(num_valid))
    print("num_test  {}".format(num_test ))

    train_files = image_files[:num_train]
    valid_files = image_files[num_train:num_train+ num_valid]
    test_files  = image_files[num_train+ num_valid:]
    
    category    = category.replace(" ", "_")
    train_images_dir   = os.path.join(output_dir, "train/" + category + output_images_dir)
    valid_images_dir   = os.path.join(output_dir, "valid/" + category + output_images_dir)
    test_images_dir    = os.path.join(output_dir, "test/"  + category + output_images_dir)

    train_masks_dir   = os.path.join(output_dir, "train/" + category + output_masks_dir)
    valid_masks_dir   = os.path.join(output_dir, "valid/" + category + output_masks_dir)
    test_masks_dir    = os.path.join(output_dir, "test/"  + category + output_masks_dir)
    
    self.resize_and_save(train_files, train_images_dir, color, train_masks_dir)
    self.resize_and_save(valid_files, valid_images_dir, color, valid_masks_dir)
    self.resize_and_save(test_files,  test_images_dir,  color, test_masks_dir )

  def resize_and_save(self, image_files, dataset_images_dir, color, dataset_masks_dir):
    if not os.path.exists(dataset_images_dir):
      os.makedirs(dataset_images_dir)
    print("=== resize_and_save  dataset_dir:{}".format(dataset_images_dir))
    
    if not os.path.exists(dataset_masks_dir):
      os.makedirs(dataset_masks_dir)
    print("=== resize_and_save  dataset_dir:{}".format(dataset_masks_dir))

    for image_file in image_files:
      basename = os.path.basename(image_file)

      if os.path.exists(image_file):
        image = Image.open(image_file)
        image = image.resize(self.RESIZE)
        basename = basename.replace(".png", ".jpg")
        output_imagefile = os.path.join(dataset_images_dir, basename)
        image.save(output_imagefile)
        print("Saved {} to {}".format(image_file, output_imagefile))

        if self.augmentation and dataset_images_dir.find("test") <0:
          self.augment(image, basename, dataset_images_dir)

        mask_file = image_file.replace("image", "label")
        if not os.path.exists(mask_file):
          print("=== FATAL Error not found mask file {}".format(mask_file))
          break
        mask = Image.open(mask_file)
        mask = mask.resize(self.RESIZE)
        mask = ImageOps.colorize(mask, black=(0, 0, 0), white=color)

        basename = os.path.basename(mask_file)
        basename = basename.replace(".png", ".jpg")
        output_maskfile = os.path.join(dataset_masks_dir, basename)
        mask.save(output_maskfile)
        print("Saved {} to {}".format(mask_file, output_maskfile))

        if self.augmentation and dataset_masks_dir.find("test") <0:
          self.augment(mask, basename, dataset_masks_dir)

      else:
        if not os.path.exists(image_file):
          print("NOT FOUND {}".format(image_file))


  def pil2cv(self, image):
    new_image = np.array(image, dtype=np.uint8)
    if new_image.ndim == 2: 
        pass
    elif new_image.shape[2] == 3: 
        new_image = cv2.cvtColor(new_image, cv2.COLOR_RGB2BGR)
    elif new_image.shape[2] == 4: 
        new_image = cv2.cvtColor(new_image, cv2.COLOR_RGBA2BGRA)
    return new_image

  def augment(self, image, basename, output_dir):
    image = self.pil2cv(image)
    if self.hflip:
      flipped = self.horizontal_flip(image)
      output_filepath = os.path.join(output_dir, "hflipped_" + basename)
      cv2.imwrite(output_filepath, flipped)
      print("--- Saved {}".format(output_filepath))

    if self.vflip:
      flipped = self.vertical_flip(image)
      output_filepath = os.path.join(output_dir, "vflipped_" + basename)
      cv2.imwrite(output_filepath, flipped)
      print("--- Saved {}".format(output_filepath))

    if self.rotation:
      self.rotate(image, basename, output_dir)

  def horizontal_flip(self, image): 
    print("shape image {}".format(image.shape))
    if len(image.shape)==3:
      return  image[:, ::-1, :]
    else:
      return  image[:, ::-1, ]

  def vertical_flip(self, image):
    if len(image.shape) == 3:
      return image[::-1, :, :]
    else:
      return image[::-1, :, ]

  def rotate(self, image, basename, output_dir):
    for angle in self.ANGLES:      

      center = (self.W/2, self.H/2)
      rotate_matrix = cv2.getRotationMatrix2D(center=center, angle=angle, scale=1)

      rotated_image = cv2.warpAffine(src=image, M=rotate_matrix, dsize=(self.W, self.H))
      output_filepath = os.path.join(output_dir, "rotated_" + str(angle) + "_" + basename)
      cv2.imwrite(output_filepath, rotated_image)
      print("--- Saved {}".format(output_filepath))
     

if __name__ == "__main__":
  try:
    root_dir   = "./EBHI-SEG/"
    output_dir = "./EBHI-Colorectal-Cancer-ImageMask-Dataset-V2"
    if os.path.exists(output_dir):
      shutil.rmtree(output_dir)
    if not os.path.exists(output_dir):
      os.makedirs(output_dir)
    resize       = 512
    augmentation = True
    generator = EBHIColorectalImageMaskDatasetGenerator(resize=resize, augmentation=augmentation)
    generator.generate(root_dir, output_dir)

  except:
    traceback.print_exc()
