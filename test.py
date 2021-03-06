import torch
import os
import numpy as np
import cv2
from detectors.ctdet import CtdetDetector
from detectors.base_detector import BaseDetector
from dataset.ctdet import CTDetDataset
from utils.opts import opts
import json
import time

class PrefetchDataset(torch.utils.data.Dataset):
    def __init__(self, opt, dataset, pre_process_func):
        self.images = dataset.images
        self.load_image_func = dataset.coco.loadImgs
        self.img_dir = dataset.img_dir
        self.pre_process_func = pre_process_func
        self.opt = opt
    def __getitem__(self, index):
        img_id = self.images[index]
        img_info = self.load_image_func(ids = [img_id])[0]
        img_path = os.path.join(self.img_dir, img_info['file_name'])
        image = cv2.imread(img_path)
        images, meta = {}, {}
        for scale in self.opt.test_scales:
            images[scale], meta[scale] = self.pre_process_func(image, scale)
        return img_id, {'images':images, 'image':image, 'meta': meta  }

    def __len__(self):
        return len(self.images)

def prefetch_test(opt):
    os.environ['CUDA_VISIBLE_DEVICES'] = opt.gpus_str
    opt = opts().update_dataset_info_and_set_heads(opt, CTDetDataset)
    print(opt)
    split = 'val'

    dataset = CTDetDataset(opt, split)
    detector = CtdetDetector(opt)


    result = {}
    if not os.path.exists(os.path.join(opt.save_dir, 'result.json')):
        data_loader = torch.utils.data.DataLoader(PrefetchDataset(opt, dataset, detector.pre_process), batch_size = 1, shuffle=False, pin_memory=True )

        for ind, (img_id, pre_processes_images) in enumerate(data_loader):
            ret = detector.run(pre_processes_images)
            result[img_id.numpy().astype(np.int32)[0]] = ret['results']
            print(ind)

    dataset.run_eval(result, os.path.join(opt.save_dir, 'result.json'))

if __name__=='__main__':
    opt = opts().parse()
    prefetch_test(opt)

 #ctdet --exp_id resdcn_18 --backbon resdcn_18 --resume --gpus 0 --load_model /home/kobe/CenterNet_Easy_Pytorch/exp/ctdet/resdcn_18/model_best.pth