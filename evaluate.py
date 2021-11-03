import sys
sys.path.append('core')

from PIL import Image
import argparse
import os
import numpy as np
import torch
import torch.nn.functional as F
import imageio
import cv2

from network import CRAFT
import network
# back-compatible with older checkpoints.
network.RAFTER = CRAFT
from torchvision import transforms
import torch.utils.data as data

import datasets
from utils import flow_viz
from utils import frame_utils

from utils.utils import InputPadder, forward_interpolate

# Just an empty Logger definition to satisfy torch.load().
class Logger:
    def __init__(self):
        self.total_steps = 0
        self.running_loss_dict = {}
        self.train_epe_list = []
        self.train_steps_list = []
        self.val_steps_list = []
        self.val_results_dict = {}
        
@torch.no_grad()
def create_sintel_submission(model, warm_start=False, output_path='sintel_submission', test_mode=1):
    """ Create submission for the Sintel leaderboard """
    model.eval()
    for dstype in ['clean', 'final']:
        test_dataset = datasets.MpiSintel(split='test', aug_params=None, dstype=dstype)

        flow_prev, sequence_prev = None, None
        for test_id in range(len(test_dataset)):
            image1, image2, (sequence, frame) = test_dataset[test_id]
            if sequence != sequence_prev:
                flow_prev = None

            padder = InputPadder(image1.shape)
            image1, image2 = padder.pad(image1[None].to(f'cuda:{model.device_ids[0]}'), image2[None].to(f'cuda:{model.device_ids[0]}'))

            flow_low, flow_pr = model.module(image1, image2, iters=32, flow_init=flow_prev, test_mode=test_mode)
            flow = padder.unpad(flow_pr[0]).permute(1, 2, 0).cpu().numpy()

            if warm_start:
                flow_prev = forward_interpolate(flow_low[0])[None].cuda()

            output_dir = os.path.join(output_path, dstype, sequence)
            output_file = os.path.join(output_dir, 'frame%04d.flo' % (frame+1))

            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            frame_utils.writeFlow(output_file, flow)
            sequence_prev = sequence

    print("Created sintel submission.")

@torch.no_grad()
def create_sintel_submission_vis(model, warm_start=False, output_path='sintel_submission', test_mode=1):
    """ Create submission for the Sintel leaderboard """
    model.eval()
    for dstype in ['clean', 'final']:
        test_dataset = datasets.MpiSintel(split='test', aug_params=None, dstype=dstype)

        flow_prev, sequence_prev = None, None
        for test_id in range(len(test_dataset)):
            image1, image2, (sequence, frame) = test_dataset[test_id]
            if sequence != sequence_prev:
                flow_prev = None

            padder = InputPadder(image1.shape)
            image1, image2 = padder.pad(image1[None].to(f'cuda:{model.device_ids[0]}'), image2[None].to(f'cuda:{model.device_ids[0]}'))

            flow_low, flow_pr = model.module(image1, image2, iters=32, flow_init=flow_prev, test_mode=test_mode)
            flow = padder.unpad(flow_pr[0]).permute(1, 2, 0).cpu().numpy()

            # Visualizations
            flow_img = flow_viz.flow_to_image(flow)
            image = Image.fromarray(flow_img)
            if not os.path.exists(f'vis_test/RAFT/{dstype}/'):
                os.makedirs(f'vis_test/RAFT/{dstype}/flow')

            if not os.path.exists(f'vis_test/ours/{dstype}/'):
                os.makedirs(f'vis_test/ours/{dstype}/flow')

            if not os.path.exists(f'vis_test/gt/{dstype}/'):
                os.makedirs(f'vis_test/gt/{dstype}/image')

            # image.save(f'vis_test/ours/{dstype}/flow/{test_id}.png')
            image.save(f'vis_test/RAFT/{dstype}/flow/{test_id}.png')
            imageio.imwrite(f'vis_test/gt/{dstype}/image/{test_id}.png', image1[0].cpu().permute(1, 2, 0).numpy())
            if warm_start:
                flow_prev = forward_interpolate(flow_low[0])[None].cuda()

            output_dir = os.path.join(output_path, dstype, sequence)
            output_file = os.path.join(output_dir, 'frame%04d.flo' % (frame+1))

            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            frame_utils.writeFlow(output_file, flow)
            sequence_prev = sequence

    print("Created sintel submission.")

@torch.no_grad()
def create_kitti_submission(model, output_path='kitti_submission', test_mode=1):
    """ Create submission for the Sintel leaderboard """
    model.eval()
    test_dataset = datasets.KITTI(split='testing', aug_params=None)

    if not os.path.exists(output_path):
        os.makedirs(output_path)

    for test_id in range(len(test_dataset)):
        image1, image2, (frame_id, ) = test_dataset[test_id]
        padder = InputPadder(image1.shape, mode='kitti')
        image1, image2 = padder.pad(image1[None].to(f'cuda:{model.device_ids[0]}'), image2[None].to(f'cuda:{model.device_ids[0]}'))

        _, flow_pr = model.module(image1, image2, iters=24, test_mode=test_mode)
        flow = padder.unpad(flow_pr[0]).permute(1, 2, 0).cpu().numpy()

        output_filename = os.path.join(output_path, frame_id)
        frame_utils.writeFlowKITTI(output_filename, flow)

    print("Created KITTI submission.")

@torch.no_grad()
def create_kitti_submission_vis(model, output_path='kitti_submission', test_mode=1):
    """ Create submission for the KITTI leaderboard """
    model.eval()
    test_dataset = datasets.KITTI(split='testing', aug_params=None)

    if not os.path.exists(output_path):
        os.makedirs(output_path)

    for test_id in range(len(test_dataset)):
        image1, image2, (frame_id, ) = test_dataset[test_id]
        padder = InputPadder(image1.shape, mode='kitti')
        image1, image2 = padder.pad(image1[None].to(f'cuda:{model.device_ids[0]}'), image2[None].to(f'cuda:{model.device_ids[0]}'))

        _, flow_pr = model.module(image1, image2, iters=24, test_mode=test_mode)
        flow = padder.unpad(flow_pr[0]).permute(1, 2, 0).cpu().numpy()

        output_filename = os.path.join(output_path, frame_id)
        frame_utils.writeFlowKITTI(output_filename, flow)

        # Visualizations
        flow_img = flow_viz.flow_to_image(flow)
        image = Image.fromarray(flow_img)
        if not os.path.exists(f'vis_kitti'):
            os.makedirs(f'vis_kitti/flow')
            os.makedirs(f'vis_kitti/image')

        image.save(f'vis_kitti/flow/{test_id}.png')
        imageio.imwrite(f'vis_kitti/image/{test_id}_0.png', image1[0].cpu().permute(1, 2, 0).numpy())
        imageio.imwrite(f'vis_kitti/image/{test_id}_1.png', image2[0].cpu().permute(1, 2, 0).numpy())

    print("Created KITTI submission.")

@torch.no_grad()
def create_viper_submission(model, output_path='viper_submission', test_mode=1):
    """ Create submission for the viper leaderboard """
    model.eval()
    test_dataset = datasets.VIPER(split='test', aug_params=None)

    if not os.path.exists(output_path):
        os.makedirs(output_path)

    scale = 0.5
    inv_scale = 1.0 / scale

    for test_id in range(len(test_dataset)):
        image1, image2, (frame_id, ) = test_dataset[test_id]
        image1 = image1[None].to(f'cuda:{model.device_ids[0]}')
        image2 = image2[None].to(f'cuda:{model.device_ids[0]}')
        # To reduce RAM use, scale images to half size.
        image1 = F.interpolate(image1, scale_factor=scale, mode='bilinear', align_corners=False)
        image2 = F.interpolate(image2, scale_factor=scale, mode='bilinear', align_corners=False)

        padder = InputPadder(image1.shape, mode='kitti')
        image1, image2 = padder.pad(image1, image2)

        _, flow_pr = model.module(image1, image2, iters=24, test_mode=test_mode)
        flow = padder.unpad(flow_pr[0]).permute(1, 2, 0).cpu().numpy()
        # Scale flow back to original size.
        flow = cv2.resize(flow, None, fx=inv_scale, fy=inv_scale, interpolation=cv2.INTER_LINEAR)
        flow = flow * [inv_scale, inv_scale]

        output_filename = os.path.join(output_path, frame_id + ".flo")
        frame_utils.writeFlow(output_filename, flow)

    print("Created VIPER submission.")

@torch.no_grad()
def validate_chairs(model, iters=6, test_mode=1):
    """ Perform evaluation on the FlyingChairs (test) split """
    model.eval()
    epe_list = []

    val_dataset = datasets.FlyingChairs(split='validation')
    for val_id in range(len(val_dataset)):
        image1, image2, flow_gt, _ = val_dataset[val_id]
        image1 = image1[None].cuda()
        image2 = image2[None].cuda()

        _, flow_pr = model(image1, image2, iters=iters, test_mode=test_mode)
        epe = torch.sum((flow_pr[0].cpu() - flow_gt)**2, dim=0).sqrt()
        epe_list.append(epe.view(-1).numpy())

    epe = np.mean(np.concatenate(epe_list))
    print("Validation Chairs EPE: %f" % epe)
    return {'chairs_epe': epe}


@torch.no_grad()
def validate_things(model, iters=6, test_mode=1, blur_params=None, max_val_count=-1):
    """ Perform evaluation on the FlyingThings (test) split """
    model.eval()
    results = {}
    mag_endpoints = [3, 5, 10, np.inf]

    for dstype in ['frames_cleanpass', 'frames_finalpass']:
        epe_list = {}
        segs_len  = []
        epe_seg  = []
        mags_seg = {}
        mags_err = {}
        mags_segs_err = {}
        mags_segs_len = {}

        # test_mode == 1, a list of iters=6 flows.
        if test_mode == 1:
            its = [0]
        # test_mode == 2, the final flow only.
        elif test_mode == 2:
            its = range(iters)
        elif test_mode == 0:
            breakpoint()
                       
        val_dataset = datasets.FlyingThings3D(dstype=dstype, aug_params=None, split='validation')
        print(f'Dataset length {len(val_dataset)}')
        val_count = 0
        if max_val_count == -1:
            max_val_count = len(val_dataset)

        # if blur_params is not None:
        #     GaussianBlur = transforms.GaussianBlur(blur_params['kernel'], blur_params['sigma'])
        # else:
        #     GaussianBlur = None

        for val_id in range(len(val_dataset)):
            image1, image2, flow_gt, _ = val_dataset[val_id]
            image1 = image1[None].cuda()
            image2 = image2[None].cuda()

            # if GaussianBlur is not None:
            #     image1 = GaussianBlur(image1)
            #     image2 = GaussianBlur(image2)

            padder = InputPadder(image1.shape)
            image1, image2 = padder.pad(image1, image2)

            _, flow_prs = model(image1, image2, iters=iters, test_mode=test_mode)
            # if test_mode == 2: list of iters=6 tensors, each is [1, 2, 544, 960].
            # if test_mode == 1: a tensor of [1, 2, 544, 960].
            if test_mode == 1:
                flow_prs = [ flow_prs ]
            
            for it, flow_pr in enumerate(flow_prs):
                flow = padder.unpad(flow_pr[0]).cpu()
                epe = torch.sum((flow - flow_gt)**2, dim=0).sqrt()
                epe_list.setdefault(it, [])
                epe_list[it].append(epe.view(-1).numpy())

            epe_seg.append(epe.view(-1).numpy())
            mag = torch.sum(flow_gt**2, dim=0).sqrt()

            prev_mag_endpoint = 0
            for mag_endpoint in mag_endpoints:
                mags_seg.setdefault(mag_endpoint, [])
                mag_in_range = (mag >= prev_mag_endpoint) & (mag < mag_endpoint)
                mags_seg[mag_endpoint].append(mag_in_range.view(-1).numpy())
                prev_mag_endpoint = mag_endpoint

            val_count += len(image1)
            segs_len.append(len(image1))

            if val_count % 100 == 0 or val_count >= max_val_count:
                epe_seg     = np.concatenate(epe_seg)
                mean_epe    = np.mean(epe_seg)
                px1 = np.mean(epe_seg < 1)
                px3 = np.mean(epe_seg < 3)
                px5 = np.mean(epe_seg < 5)

                for mag_endpoint in mag_endpoints:
                    mag_seg = np.concatenate(mags_seg[mag_endpoint])
                    if mag_seg.sum() == 0:
                        mag_err = 0
                    else:
                        mag_err = np.mean(epe_seg[mag_seg])
                    mags_err[mag_endpoint] = mag_err
                    mags_segs_err.setdefault(mag_endpoint, [])
                    mags_segs_err[mag_endpoint].append(mags_err[mag_endpoint])
                    mags_segs_len.setdefault(mag_endpoint, [])
                    mags_segs_len[mag_endpoint].append(mag_seg.sum().item())

                print(f"{val_count}/{max_val_count}: EPE {mean_epe:.4f}, "
                      f"1px {px1:.4f}, 3px {px3:.4f}, 5px {px5:.4f}", end='')
                prev_mag_endpoint = 0
                for mag_endpoint in mag_endpoints:
                    print(f", {prev_mag_endpoint}-{mag_endpoint} {mags_err[mag_endpoint]:.2f}", end='')
                    prev_mag_endpoint = mag_endpoint
                print()

                epe_seg = []
                mags_seg = {}

            # The validation data is too big. Just evaluate some.
            if val_count >= max_val_count:
                break

        for it in its:
            epe_all = np.concatenate(epe_list[it])

            epe = np.mean(epe_all)
            px1 = np.mean(epe_all < 1)
            px3 = np.mean(epe_all < 3)
            px5 = np.mean(epe_all < 5)

            print(f"Iter {it}, Valid ({dstype}) EPE: {epe:.4f}, 1px: {px1:.4f}, 3px: {px3:.4f}, 5px: {px5:.4f}", end='')

        for mag_endpoint in mag_endpoints:
            mag_errs = np.array(mags_segs_err[mag_endpoint])
            mag_lens = np.array(mags_segs_len[mag_endpoint])
            mag_err = np.sum(mag_errs * mag_lens) / np.sum(mag_lens)
            mags_err[mag_endpoint] = mag_err

        prev_mag_endpoint = 0
        for mag_endpoint in mag_endpoints:
            print(f", {prev_mag_endpoint}-{mag_endpoint} {mags_err[mag_endpoint]:.2f}", end='')
            prev_mag_endpoint = mag_endpoint
        print()

        results[dstype] = epe

    return results


@torch.no_grad()
def validate_sintel(model, iters=6, test_mode=1, blur_params=None, max_val_count=-1):
    """ Peform validation using the Sintel (train) split """
    model.eval()
    results = {}
    mag_endpoints = [3, 5, 10, np.inf]
    
    for dstype in ['clean', 'final']:
        val_dataset = datasets.MpiSintel(split='training', aug_params=None, dstype=dstype)
        print(f'Dataset length {len(val_dataset)}')
        val_count = 0
        if max_val_count == -1:
            max_val_count = len(val_dataset)

        epe_list = {}
        segs_len = []
        epe_seg  = []
        mags_seg = {}
        mags_err = {}
        mags_segs_err = {}
        mags_segs_len = {}

        if test_mode == 1:
            its = [0]
        elif test_mode == 2:
            its = range(iters)
        elif test_mode == 0:
            breakpoint()
        
        val_count = 0
        # if blur_params is not None:
        #     GaussianBlur = transforms.GaussianBlur(blur_params['kernel'], blur_params['sigma'])
        # else:
        #     GaussianBlur = None

        for val_id in range(len(val_dataset)):
            image1, image2, flow_gt, _ = val_dataset[val_id]
            image1 = image1[None].cuda()
            image2 = image2[None].cuda()

            # if GaussianBlur is not None:
            #     #image1 = GaussianBlur(image1)
            #     image2 = GaussianBlur(image2)

            padder = InputPadder(image1.shape)
            image1, image2 = padder.pad(image1, image2)

            _, flow_prs = model(image1, image2, iters=iters, test_mode=test_mode)
            # if test_mode == 2: list of 12 tensors, each is [1, 2, H, W].
            # if test_mode == 1: a tensor of [1, 2, H, W].
            if test_mode == 1:
                flow_prs = [ flow_prs ]

            for it, flow_pr in enumerate(flow_prs):
                flow = padder.unpad(flow_pr[0]).cpu()
                epe = torch.sum((flow - flow_gt)**2, dim=0).sqrt()
                epe_list.setdefault(it, [])
                epe_list[it].append(epe.view(-1).numpy())

            epe_seg.append(epe.view(-1).numpy())
            mag = torch.sum(flow_gt**2, dim=0).sqrt()

            prev_mag_endpoint = 0
            for mag_endpoint in mag_endpoints:
                mags_seg.setdefault(mag_endpoint, [])
                mag_in_range = (mag >= prev_mag_endpoint) & (mag < mag_endpoint)
                mags_seg[mag_endpoint].append(mag_in_range.view(-1).numpy())
                prev_mag_endpoint = mag_endpoint

            val_count += len(image1)
            segs_len.append(len(image1))

            if val_count % 100 == 0 or val_count >= max_val_count:
                epe_seg     = np.concatenate(epe_seg)
                mean_epe    = np.mean(epe_seg)
                px1 = np.mean(epe_seg < 1)
                px3 = np.mean(epe_seg < 3)
                px5 = np.mean(epe_seg < 5)

                for mag_endpoint in mag_endpoints:
                    mag_seg = np.concatenate(mags_seg[mag_endpoint])
                    if mag_seg.sum() == 0:
                        mag_err = 0
                    else:
                        mag_err = np.mean(epe_seg[mag_seg])
                    mags_err[mag_endpoint] = mag_err
                    mags_segs_err.setdefault(mag_endpoint, [])
                    mags_segs_err[mag_endpoint].append(mags_err[mag_endpoint])
                    mags_segs_len.setdefault(mag_endpoint, [])
                    mags_segs_len[mag_endpoint].append(mag_seg.sum().item())

                print(f"{val_count}/{max_val_count}: EPE {mean_epe:.4f}, "
                      f"1px {px1:.4f}, 3px {px3:.4f}, 5px {px5:.4f}", end='')

                prev_mag_endpoint = 0
                for mag_endpoint in mag_endpoints:
                    print(f", {prev_mag_endpoint}-{mag_endpoint} {mags_err[mag_endpoint]:.2f}", end='')
                    prev_mag_endpoint = mag_endpoint
                print()

                epe_seg = []
                mags_seg = {}

        for it in its:
            epe_all = np.concatenate(epe_list[it])
            
            epe = np.mean(epe_all)
            px1 = np.mean(epe_all<1)
            px3 = np.mean(epe_all<3)
            px5 = np.mean(epe_all<5)

            print("Iter %d, Valid (%s) EPE: %f, 1px: %f, 3px: %f, 5px: %f" % (it, dstype, epe, px1, px3, px5))

        for mag_endpoint in mag_endpoints:
            mag_errs = np.array(mags_segs_err[mag_endpoint])
            mag_lens = np.array(mags_segs_len[mag_endpoint])
            mag_err = np.sum(mag_errs * mag_lens) / np.sum(mag_lens)
            mags_err[mag_endpoint] = mag_err

        prev_mag_endpoint = 0
        for mag_endpoint in mag_endpoints:
            print(f", {prev_mag_endpoint}-{mag_endpoint} {mags_err[mag_endpoint]:.2f}", end='')
            prev_mag_endpoint = mag_endpoint
        print()

        results[dstype] = epe

    return results

@torch.no_grad()
def validate_sintel_occ(model, iters=6, test_mode=1):
    """ Peform validation using the Sintel (train) split """
    model.eval()
    results = {}
    for dstype in ['clean', 'final', 'albedo']:
    # for dstype in ['clean', 'final']:
        val_dataset = datasets.MpiSintel(split='training', dstype=dstype, occlusion=True)
        epe_list = []
        epe_occ_list = []
        epe_noc_list = []

        for val_id in range(len(val_dataset)):
            image1, image2, flow_gt, _, occ, _ = val_dataset[val_id]
            image1 = image1[None].cuda()
            image2 = image2[None].cuda()

            padder = InputPadder(image1.shape)
            image1, image2 = padder.pad(image1, image2)

            _, flow_pr = model(image1, image2, iters=iters, test_mode=test_mode)
            flow = padder.unpad(flow_pr[0]).cpu()

            epe = torch.sum((flow - flow_gt)**2, dim=0).sqrt()
            epe_list.append(epe.view(-1).numpy())

            epe_noc_list.append(epe[~occ].numpy())
            epe_occ_list.append(epe[occ].numpy())

        epe_all = np.concatenate(epe_list)

        epe_noc = np.concatenate(epe_noc_list)
        epe_occ = np.concatenate(epe_occ_list)

        epe = np.mean(epe_all)
        px1 = np.mean(epe_all<1)
        px3 = np.mean(epe_all<3)
        px5 = np.mean(epe_all<5)

        epe_occ_mean = np.mean(epe_occ)
        epe_noc_mean = np.mean(epe_noc)

        print("Validation (%s) EPE: %f, 1px: %f, 3px: %f, 5px: %f" % (dstype, epe, px1, px3, px5))
        print("Occ epe: %f, Noc epe: %f" % (epe_occ_mean, epe_noc_mean))
        results[dstype] = np.mean(epe_list)

    return results


@torch.no_grad()
def separate_inout_sintel_occ():
    """ Peform validation using the Sintel (train) split """
    dstype = 'clean'
    val_dataset = datasets.MpiSintel(split='training', dstype=dstype, occlusion=True)
    # coords = torch.meshgrid(torch.arange(ht), torch.arange(wd))
    # coords = torch.stack(coords[::-1], dim=0).float()
    # return coords[None].expand(batch, -1, -1, -1)

    for val_id in range(len(val_dataset)):
        image1, image2, flow_gt, _, occ, occ_path = val_dataset[val_id]
        _, h, w = image1.size()
        coords = torch.meshgrid(torch.arange(h), torch.arange(w))
        coords = torch.stack(coords[::-1], dim=0).float()

        coords_img_2 = coords + flow_gt
        out_of_frame = (coords_img_2[0] < 0) | (coords_img_2[0] > w) | (coords_img_2[1] < 0) | (coords_img_2[1] > h)
        occ_union = out_of_frame | occ
        in_frame = occ_union ^ out_of_frame

        # Generate union of occlusions and out of frame
        # path_list = occ_path.split('/')
        # path_list[-3] = 'occ_plus_out'
        # dir_path = os.path.join('/', *path_list[:-1])
        # img_path = os.path.join('/', *path_list)
        # if not os.path.exists(dir_path):
        #     os.makedirs(dir_path)
        #
        # imageio.imwrite(img_path, occ_union.int().numpy() * 255)

        # Generate out-of-frame
        # path_list = occ_path.split('/')
        # path_list[-3] = 'out_of_frame'
        # dir_path = os.path.join('/', *path_list[:-1])
        # img_path = os.path.join('/', *path_list)
        # if not os.path.exists(dir_path):
        #     os.makedirs(dir_path)
        #
        # imageio.imwrite(img_path, out_of_frame.int().numpy() * 255)

        # # Generate in-frame occlusions
        # path_list = occ_path.split('/')
        # path_list[-3] = 'in_frame_occ'
        # dir_path = os.path.join('/', *path_list[:-1])
        # img_path = os.path.join('/', *path_list)
        # if not os.path.exists(dir_path):
        #     os.makedirs(dir_path)
        #
        # imageio.imwrite(img_path, in_frame.int().numpy() * 255)

@torch.no_grad()
def validate_hd1k(model, iters=6, test_mode=1):
    """ Peform validation using the HD1k data """
    model.eval()
    results = {}
    val_dataset = datasets.HD1K()
    epe_list = []
    
    for val_id in range(len(val_dataset)):
        image1, image2, flow_gt, _ = val_dataset[val_id]
        image1 = image1[None].cuda()
        image2 = image2[None].cuda()

        halfsize = transforms.Resize((360, 853))
        image1   = halfsize(image1)
        image2   = halfsize(image2)
        flow_gt  = halfsize(flow_gt)
            
        padder = InputPadder(image1.shape)
        image1, image2 = padder.pad(image1, image2)

        _, flow_pr = model(image1, image2, iters=iters, test_mode=test_mode)
        flow = padder.unpad(flow_pr[0]).cpu()

        epe = torch.sum((flow - flow_gt)**2, dim=0).sqrt()
        epe_list.append(epe.view(-1).numpy())

        if val_id % 100 == 0:
            print(f"{val_id}/{len(val_dataset)}")
            epe_all = np.concatenate(epe_list)
            epe = np.mean(epe_all)
            px1 = np.mean(epe_all<1)
            px3 = np.mean(epe_all<3)
            px5 = np.mean(epe_all<5)
            print("EPE: %f, 1px: %f, 3px: %f, 5px: %f" % (epe, px1, px3, px5))

    print(f"{val_id}/{len(val_dataset)}")
    epe_all = np.concatenate(epe_list)
    epe = np.mean(epe_all)
    px1 = np.mean(epe_all<1)
    px3 = np.mean(epe_all<3)
    px5 = np.mean(epe_all<5)
    print("EPE: %f, 1px: %f, 3px: %f, 5px: %f" % (epe, px1, px3, px5))
                    
    results = np.mean(epe_list)

    return results

@torch.no_grad()
def validate_kitti(model, iters=6, test_mode=1):
    """ Peform validation using the KITTI-2015 (train) split """
    model.eval()
    val_dataset = datasets.KITTI(split='training')

    out_list, epe_list = [], []

    for val_id in range(len(val_dataset)):
        image1, image2, flow_gt, valid_gt = val_dataset[val_id]
        image1 = image1[None].cuda()
        image2 = image2[None].cuda()

        padder = InputPadder(image1.shape, mode='kitti')
        image1, image2 = padder.pad(image1, image2)

        _, flow_pr = model(image1, image2, iters=iters, test_mode=test_mode)
        flow = padder.unpad(flow_pr[0]).cpu()

        epe = torch.sum((flow - flow_gt)**2, dim=0).sqrt()
        mag = torch.sum(flow_gt**2, dim=0).sqrt()

        epe = epe.view(-1)
        mag = mag.view(-1)
        val = valid_gt.view(-1) >= 0.5

        out = ((epe > 3.0) & ((epe/mag) > 0.05)).float()
        epe_list.append(epe[val].mean().item())
        out_list.append(out[val].cpu().numpy())

    epe_list = np.array(epe_list)
    out_list = np.concatenate(out_list)

    epe = np.mean(epe_list)
    f1 = 100 * np.mean(out_list)

    print("Validation KITTI: %f, %f" % (epe, f1))
    return {'kitti_epe': epe, 'kitti_f1': f1}

# Set max_val_count=-1 to evaluate the whole dataset.
@torch.no_grad()
def validate_viper(model, iters=6, test_mode=1, batch_size=2, max_val_count=500):
    """ Peform validation using the VIPER validation split """
    model.eval()
    # original size: (1080, 1920).
    # real_scale = 2** scale = 0.5. scale: log(0.5) / log(2) = -1.
    val_dataset = datasets.VIPER(split='validation', 
                                 aug_params={'crop_size': (540, 960), 'min_scale': -1, 'max_scale': -1,
                                             'spatial_aug_prob': 1})

    val_loader  = data.DataLoader(val_dataset, batch_size=batch_size,
                                  pin_memory=False, shuffle=False, num_workers=8, drop_last=False)

                                   
    out_list, epe_list = {}, {}
    out_seg,  epe_seg  = [], []
    mag_endpoints = [3, 5, 10, np.inf]
    segs_len = []
    mags_seg = {}
    mags_err = {}
    mags_segs_err = {}
    mags_segs_len = {}

    if test_mode == 1:
        its = [0]
    elif test_mode == 2:
        its = range(iters)
    elif test_mode == 0:
        breakpoint()
    
    val_count = 0
    if max_val_count == -1:
        max_val_count = len(val_dataset)
    else:
        max_val_count = min(max_val_count, len(val_dataset))
        if max_val_count < len(val_dataset):
            print(f"Evaluate first {max_val_count} of {len(val_dataset)}")
            
    for data_blob in iter(val_loader):
        image1, image2, flow_gt, valid_gt = data_blob
        image1 = image1.cuda()
        image2 = image2.cuda()
        
        # (540, 960) => (544, 960), to be divided by 8.
        padder = InputPadder(image1.shape, mode='kitti')
        image1, image2 = padder.pad(image1, image2)

        _, flow_prs = model(image1, image2, iters=iters, test_mode=test_mode)
        
        # if test_mode == 2: list of 12 tensors, each is [1, 2, H, W].
        # if test_mode == 1: a tensor of [1, 2, H, W].
        if test_mode == 1:
            flow_prs = [ flow_prs ]

        for it, flow_pr in enumerate(flow_prs):
            flow = padder.unpad(flow_pr).cpu()
            epe = torch.sum((flow - flow_gt)**2, dim=1).sqrt()
            mag = torch.sum(flow_gt**2, dim=1).sqrt()
            epe = epe.view(-1)
            mag = mag.view(-1)
            val = valid_gt.view(-1) >= 0.5

            out = ((epe > 3.0) & ((epe/mag) > 0.05)).float()
                        
            epe_list.setdefault(it, [])
            out_list.setdefault(it, [])
            epe_list[it].append(epe[val].view(-1).numpy())
            out_list[it].append(out[val].view(-1).numpy())

        epe_seg.append(epe[val].view(-1).numpy())
        out_seg.append(out[val].view(-1).numpy())
        mag = torch.sum(flow_gt**2, dim=0).sqrt()

        prev_mag_endpoint = 0
        for mag_endpoint in mag_endpoints:
            mags_seg.setdefault(mag_endpoint, [])
            mag_in_range = (mag >= prev_mag_endpoint) & (mag < mag_endpoint)
            mags_seg[mag_endpoint].append(mag_in_range.view(-1)[val].numpy())
            prev_mag_endpoint = mag_endpoint

        val_count += len(image1)
        segs_len.append(len(image1))

        if val_count % 100 == 0 or val_count >= max_val_count:
            epe_seg     = np.concatenate(epe_seg)
            out_seg     = np.concatenate(out_seg)
            mean_epe    = np.mean(epe_seg)
            px1 = np.mean(epe_seg < 1)
            px3 = np.mean(epe_seg < 3)
            px5 = np.mean(epe_seg < 5)

            print(f"{val_count}/{max_val_count}: EPE {mean_epe:.4f}, "
                    f"1px {px1:.4f}, 3px {px3:.4f}, 5px {px5:.4f}", end='')
                    
            for mag_endpoint in mag_endpoints:
                mag_seg = np.concatenate(mags_seg[mag_endpoint])
                if mag_seg.sum() == 0:
                    mag_err = 0
                else:
                    mag_err = np.mean(epe_seg[mag_seg])
                mags_err[mag_endpoint] = mag_err
                mags_segs_err.setdefault(mag_endpoint, [])
                mags_segs_err[mag_endpoint].append(mags_err[mag_endpoint])
                mags_segs_len.setdefault(mag_endpoint, [])
                mags_segs_len[mag_endpoint].append(mag_seg.sum().item())

            prev_mag_endpoint = 0
            for mag_endpoint in mag_endpoints:
                print(f", {prev_mag_endpoint}-{mag_endpoint} {mags_err[mag_endpoint]:.2f}", end='')
                prev_mag_endpoint = mag_endpoint
            print()

            epe_seg = []
            out_seg = []
            mags_seg = {}

        # The validation data is too big. Just evaluate some.
        if val_count >= max_val_count:
            break
                                                       
    for it in its:
        epe_all = np.concatenate(epe_list[it])
        out_all = np.concatenate(out_list[it])
        
        epe = np.mean(epe_all)
        px1 = np.mean(epe_all<1)
        px3 = np.mean(epe_all<3)
        px5 = np.mean(epe_all<5)

        f1 = 100 * np.mean(out_all)
        print("Iter %d, Valid EPE: %.4f, F1: %.4f, 1px: %.4f, 3px: %.4f, 5px: %.4f" % (it, epe, f1, px1, px3, px5))

    for mag_endpoint in mag_endpoints:
        mag_errs = np.array(mags_segs_err[mag_endpoint])
        mag_lens = np.array(mags_segs_len[mag_endpoint])
        mag_err = np.sum(mag_errs * mag_lens) / np.sum(mag_lens)
        mags_err[mag_endpoint] = mag_err

    prev_mag_endpoint = 0
    for mag_endpoint in mag_endpoints:
        print(f", {prev_mag_endpoint}-{mag_endpoint} {mags_err[mag_endpoint]:.2f}", end='')
        prev_mag_endpoint = mag_endpoint
    print()

    return {'epe': epe, 'f1': f1}
        
def save_checkpoint(cp_path, model, optimizer_state, lr_scheduler_state, logger):
    save_state = { 'model':        model.state_dict(),
                   'optimizer':    optimizer_state,
                   'lr_scheduler': lr_scheduler_state,
                   'logger':       logger.__dict__
                 }

    torch.save(save_state, cp_path)
    print(f"{cp_path} saved")

@torch.no_grad()
def gen_flow(model, model_name, iters, image1_path, image2_path, output_path='output', test_mode=1):
    """ Generate flow given two images """
    model.eval()

    if not os.path.exists(output_path):
        os.makedirs(output_path)

    image1 = cv2.imread(image1_path)
    image2 = cv2.imread(image2_path)
    # grayscale images
    if len(image1.shape) == 2:
        image1 = np.tile(image1[...,None], (1, 1, 3))
        image2 = np.tile(image2[...,None], (1, 1, 3))
    else:
        image1 = image1[..., :3]
        image2 = image2[..., :3]

    image1 = torch.from_numpy(image1).permute(2, 0, 1).float()
    image2 = torch.from_numpy(image2).permute(2, 0, 1).float()
        
    padder = InputPadder(image1.shape, mode='kitti')
    image1, image2 = padder.pad(image1[None].to(f'cuda:{model.device_ids[0]}'), image2[None].to(f'cuda:{model.device_ids[0]}'))

    _, flow_pr = model.module(image1, image2, iters=iters, test_mode=test_mode)
    flow = padder.unpad(flow_pr[0]).permute(1, 2, 0).cpu().numpy()

    # split image1_path into path and file name
    _, image1_name = os.path.split(image1_path)
    # split file name into file name and extension
    image1_name_noext, _ = os.path.splitext(image1_name)
    output_filename = os.path.join(output_path, image1_name_noext + f"-{model_name}-{iters}.png")
    frame_utils.writeFlowKITTI(output_filename, flow)

    print(f"Generated flow {output_filename}.")

def fix_checkpoint(args, model):
    checkpoint = torch.load(args.model, map_location='cuda')

    if 'model' in checkpoint:
        msg = model.load_state_dict(checkpoint['model'], strict=False)
    else:
        # Load old checkpoint.
        msg = model.load_state_dict(checkpoint, strict=False)

    print(f"Model checkpoint loaded from {args.model}: {msg}.")

    logger = Logger()
    if 'logger' in checkpoint:
        if type(checkpoint['logger']) == dict:
            logger_dict = checkpoint['logger']
        else:
            logger_dict = checkpoint['logger'].__dict__
        
        # The scheduler will be updated by checkpoint['lr_scheduler'], no need to update here.
        for key in ('args', 'scheduler', 'model'):
            if key in logger_dict:
                del logger_dict[key]
        logger.__dict__.update(logger_dict)
        print("Logger loaded.")
    else:
        print("Logger NOT loaded.")
    
    optimizer_state     = checkpoint['optimizer']    if 'optimizer'    in checkpoint else None
    lr_scheduler_state  = checkpoint['lr_scheduler'] if 'lr_scheduler' in checkpoint else None
    
    save_checkpoint(args.model + "2", model, optimizer_state, lr_scheduler_state, logger)
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', help="restore checkpoint")
    parser.add_argument('--dataset', help="dataset for evaluation")
    parser.add_argument('--img1', type=str, default=None, help="first image for evaluation")
    parser.add_argument('--img2', type=str, default=None, help="second image for evaluation")
    parser.add_argument('--output', type=str, default="output", help="output directory")

    parser.add_argument('--iters', type=int, default=12)
    parser.add_argument('--num_heads', default=1, type=int,
                        help='number of heads in attention and aggregation')
    parser.add_argument('--position_only', default=False, action='store_true',
                        help='only use position-wise attention')
    parser.add_argument('--position_and_content', default=False, action='store_true',
                        help='use position and content-wise attention')
    parser.add_argument('--fullprec', dest='mixed_precision',
                        action='store_false', help='use full precision (default: mixed precision)')
    parser.add_argument('--model_name')
    parser.add_argument('--fix', action='store_true', help='Fix loaded checkpoint')
    parser.add_argument('--submit', action='store_true', help='Make a sintel/kitti submission')
    parser.add_argument('--test_mode', default=1, type=int, 
                        help='Test mode (1: normal, 2: evaluate performance of every iteration)')
    parser.add_argument('--maxval', dest='max_val_count', default=-1, type=int, 
                        help='Maximum number of evaluated examples')
    parser.add_argument('--bs', dest='batch_size', default=2, type=int, 
                        help='Batch size')
    parser.add_argument('--blurk', dest='blur_kernel', default=5, type=int, 
                        help='Gaussian blur kernel size')
    # Only if blur_sigma > 0 (regardless of blur_kernel), Gaussian blur will be applied.
    parser.add_argument('--blurs', dest='blur_sigma', default=-1, type=int, 
                        help='Gaussian blur sigma')

    # Ablations
    parser.add_argument('--replace', default=False, action='store_true',
                        help='Replace local motion feature with aggregated motion features')
    parser.add_argument('--no_alpha', default=False, action='store_true',
                        help='Remove learned alpha, set it to 1')
    parser.add_argument('--no_residual', default=False, action='store_true',
                        help='Remove residual connection. Do not add local features with the aggregated features.')
    parser.add_argument('--radius', dest='corr_radius', type=int, default=4)    

    parser.add_argument('--corrnorm', dest='corr_norm_type', type=str, 
                        choices=['none', 'local', 'global'], default='none')
    parser.add_argument('--posr', dest='pos_bias_radius', type=int, default=7, 
                        help='The radius of positional biases')
                        
    parser.add_argument('--f2trans', dest='f2trans', action='store_true', 
                        help='Use transformer on frame 2 features')
    parser.add_argument('--f2half', dest='f2trans_do_half_chan', action='store_true', 
                        help='Use half channel of frame 2 features for transformer self-attention')                        
    parser.add_argument('--f2posw', dest='f2_pos_code_weight', type=float, default=0.5)
                            
    parser.add_argument('--setrans', dest='setrans', action='store_true', 
                        help='use setrans (Squeeze-Expansion Transformer)')
    parser.add_argument('--intermodes', dest='inter_num_modes', type=int, default=4, 
                        help='Number of modes in inter-frame attention')
    parser.add_argument('--intramodes', dest='intra_num_modes', type=int, default=4, 
                        help='Number of modes in intra-frame attention')
    parser.add_argument('--craft', dest='craft', action='store_true', 
                        help='use craft (Cross-Attentional Flow Transformer)')
    # In inter-frame attention, having QK biases performs slightly better.
    parser.add_argument('--interqknobias', dest='inter_qk_have_bias', action='store_false', 
                        help='Do not use biases in the QK projections in the inter-frame attention')
                        
    parser.add_argument('--interpos', dest='inter_pos_code_type', type=str, 
                        choices=['lsinu', 'bias'], default='bias')
    parser.add_argument('--interposw', dest='inter_pos_code_weight', type=float, default=0.5)
    parser.add_argument('--intrapos', dest='intra_pos_code_type', type=str, 
                        choices=['lsinu', 'bias'], default='bias')
    parser.add_argument('--intraposw', dest='intra_pos_code_weight', type=float, default=1.0)
    
    args = parser.parse_args()

    print("Args:\n{}".format(args))
    
    if args.dataset == 'separate':
        separate_inout_sintel_occ()
        sys.exit()

    model = torch.nn.DataParallel(CRAFT(args))
    
    if args.fix:
        fix_checkpoint(args, model)
        exit()
        
    checkpoint = torch.load(args.model)
    if 'model' in checkpoint:
        msg = model.load_state_dict(checkpoint['model'], strict=False)
    else:
        # Load old checkpoint.
        msg = model.load_state_dict(checkpoint, strict=False)
    
    print(f"Model checkpoint loaded from {args.model}: {msg}.")
        
    model.cuda()
    model.eval()
    

    if args.img1 is not None:
        model_name = os.path.split(args.model)[-1].split(".")[0]
        if 'craft' in model_name:
            if args.f2trans_do_halfchan:
                model_name = model_name.replace("craft", "craft-half")
            else:
                model_name = model_name.replace("craft", "craft-base")

        gen_flow(model, model_name, args.iters, args.img1, args.img2, args.output)
        exit(0)

    if args.dataset == 'sintel' and args.submit:
        create_sintel_submission(model, warm_start=True)
        exit(0)
        # create_sintel_submission_vis(model, warm_start=True)
        
    if args.dataset == 'kitti' and args.submit:
        create_kitti_submission(model)
        exit(0)
    
    if args.dataset == 'viper' and args.submit:
        create_viper_submission(model)
        exit(0)
    # create_kitti_submission_vis(model)

    if args.blur_sigma > 0:
        print(f"Blur kernel size: {args.blur_kernel}, sigma: {args.blur_sigma}".format(args.blur_kernel))
        blur_params = { 'kernel': args.blur_kernel, 'sigma': args.blur_sigma }
    else:
        blur_params = None

    with torch.no_grad():
        if args.dataset == 'chairs':
            validate_chairs(model.module, iters=args.iters, test_mode=args.test_mode)

        elif args.dataset == 'things':
            validate_things(model.module, iters=args.iters, test_mode=args.test_mode, 
                            max_val_count=args.max_val_count, blur_params=blur_params)

        elif args.dataset == 'sintel':
            validate_sintel(model.module, iters=args.iters, test_mode=args.test_mode, 
                            max_val_count=args.max_val_count, blur_params=blur_params)

        elif args.dataset == 'sintel_occ':
            validate_sintel_occ(model.module, iters=args.iters, test_mode=args.test_mode)

        elif args.dataset == 'kitti':
            validate_kitti(model.module, iters=args.iters, test_mode=args.test_mode)

        elif args.dataset == 'viper':
            validate_viper(model.module, iters=args.iters, test_mode=args.test_mode, 
                           max_val_count=args.max_val_count, batch_size=args.batch_size)

        elif args.dataset == 'hd1k':
            validate_hd1k(model.module, iters=args.iters, test_mode=args.test_mode)

