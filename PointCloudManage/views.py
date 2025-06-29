from threading import local
from time import time
from django.http import JsonResponse
from django.shortcuts import render
from django.shortcuts import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from glob import glob
import os
import shutil
import json
import math
import cv2
import numpy as np
import requests
from requests.exceptions import RequestException, Timeout, HTTPError, ConnectionError
import base64

from PointCloudManage.exception import FileExistsException, ShapeException, FileNotExistsException, NoFilesException
from PointCloudManage.utils import clear_dir_with_time, get_file_name, generate_points_obj, upsample_points, save_file, get_file_ext, load_file, xyz2ply_with_rgb, zip_dir, delete_files_and_dirs, clear_dir, count_num_files_for_dir, xyz2ply, normalize_points

STATIC_DIR = os.path.join(os.path.dirname(__file__), '..', 'static')
MYPCBASE_DIRNAME = 'mypcbase'
RECYCLEBIN_DIRNAME = 'recyclebin'
PCUPSAMPLE_DIRNAME = 'pcupsample'
SCENEUPSAMPLE_DIRNAME = 'sceneupsample'
SEGDATASET_DIRNAME = 'segdataset'
SCENESEG_DIRNAME = 'sceneseg'

UPSAMPLE_DIRNAME = 'upsample'


# for page-render request (page)
def index(request):
    oral_scan_path = '/static/models/0140W3ND_lower_origin.ply'
    seg_path = '/static/models/0140W3ND_lower.ply'
    landmark_mesh_path = ['/static/models/0140W3ND_lower/0140W3ND_lower_LL1.ply', '/static/models/0140W3ND_lower/0140W3ND_lower_LL2.ply',
                          '/static/models/0140W3ND_lower/0140W3ND_lower_LL3.ply', '/static/models/0140W3ND_lower/0140W3ND_lower_LL4.ply',
                          '/static/models/0140W3ND_lower/0140W3ND_lower_LL5.ply', '/static/models/0140W3ND_lower/0140W3ND_lower_LL6.ply',
                          '/static/models/0140W3ND_lower/0140W3ND_lower_LL7.ply', '/static/models/0140W3ND_lower/0140W3ND_lower_LR1.ply',
                          '/static/models/0140W3ND_lower/0140W3ND_lower_LR2.ply', '/static/models/0140W3ND_lower/0140W3ND_lower_LR3.ply',
                          '/static/models/0140W3ND_lower/0140W3ND_lower_LR4.ply', '/static/models/0140W3ND_lower/0140W3ND_lower_LR5.ply',
                          '/static/models/0140W3ND_lower/0140W3ND_lower_LR6.ply', '/static/models/0140W3ND_lower/0140W3ND_lower_LR7.ply']
    landmark_mesh_path = json.dumps(landmark_mesh_path)
    landmark_point_path = ['/static/models/0140W3ND_lower/0140W3ND_lower_LL1_landmarks.ply', '/static/models/0140W3ND_lower/0140W3ND_lower_LL2_landmarks.ply',
                          '/static/models/0140W3ND_lower/0140W3ND_lower_LL3_landmarks.ply', '/static/models/0140W3ND_lower/0140W3ND_lower_LL4_landmarks.ply',
                          '/static/models/0140W3ND_lower/0140W3ND_lower_LL5_landmarks.ply', '/static/models/0140W3ND_lower/0140W3ND_lower_LL6_landmarks.ply',
                          '/static/models/0140W3ND_lower/0140W3ND_lower_LL7_landmarks.ply', '/static/models/0140W3ND_lower/0140W3ND_lower_LR1_landmarks.ply',
                          '/static/models/0140W3ND_lower/0140W3ND_lower_LR2_landmarks.ply', '/static/models/0140W3ND_lower/0140W3ND_lower_LR3_landmarks.ply',
                          '/static/models/0140W3ND_lower/0140W3ND_lower_LR4_landmarks.ply', '/static/models/0140W3ND_lower/0140W3ND_lower_LR5_landmarks.ply',
                          '/static/models/0140W3ND_lower/0140W3ND_lower_LR6_landmarks.ply', '/static/models/0140W3ND_lower/0140W3ND_lower_LR7_landmarks.ply']
    landmark_point_path = json.dumps(landmark_point_path)
    
    return render(request, 'index.html', locals())


def pcupsample_display_page(request):
    folder_path = os.path.join(STATIC_DIR, PCUPSAMPLE_DIRNAME, 'oral_scans')
    pc_names = [get_file_name(file_path)
                for file_path in glob(os.path.join(folder_path, '*.ply'))
                if 'qem' not in file_path and 'selective' not in file_path]
    pc_names.sort()
    
    num_models = len(pc_names)
    show_pages = (num_models > 0)
    if not show_pages:
        return render(request, 'pcupsample-display.html', locals())
    
    num_per_page = 6
    request_page_id = 1
    if 'request_page_id' in request.GET:
        request_page_id = request.GET['request_page_id']
        request_page_id = int(request_page_id)
    num_pages, page_ids, first_page_id, last_page_id, prev_page_id, next_page_id = _get_pages(num_models, request_page_id, num_per_page=num_per_page)
    if request_page_id > num_pages:
        request_page_id = num_pages
    
    disable_first_page = (request_page_id == first_page_id)
    disable_last_page = (request_page_id == last_page_id)
    disable_prev_page = (request_page_id == prev_page_id)
    disable_next_page = (request_page_id == next_page_id)

    start_id = (request_page_id - 1) * num_per_page
    end_id = request_page_id * num_per_page
    pc_names = pc_names[start_id:end_id]
    
    # for pc_name in pc_names:
    #     xyz_path = os.path.join(folder_path, '%s.xyz' % pc_name)
    #     obj_path = os.path.join(folder_path, '%s.obj' % pc_name)
    #     if os.path.exists(obj_path):
    #         continue
    #     generate_points_obj(xyz_path, obj_path, prog_record=False)
    
    return render(request, 'pcupsample-display.html', locals())


@csrf_exempt
def pcupsample_vis_page(request, pc_name):
    folder_path = os.path.join(STATIC_DIR, 'pcupsample')
    input_xyz_path = os.path.join(folder_path, 'oral_scans', '%s.ply' % pc_name)
    qem_xyz_path = os.path.join(folder_path, 'oral_scans', '%s_qem_downsample.ply' % pc_name)
    selective_xyz_path = os.path.join(folder_path, 'oral_scans', '%s_selective_downsample.ply' % pc_name)
    exists = os.path.exists(input_xyz_path)
    exists &= os.path.exists(qem_xyz_path)
    exists &= os.path.exists(selective_xyz_path)
    if not exists:
        return render(request, '404.html', locals())

    input_file = os.path.join('/static/pcupsample/oral_scans/', '%s.ply' % pc_name)
    qem_file = os.path.join('/static/pcupsample/oral_scans/', '%s_qem_downsample.ply' % pc_name)
    selective_file = os.path.join('/static/pcupsample/oral_scans/', '%s_selective_downsample.ply' % pc_name)

    return render(request, 'pcupsample-vis.html', locals())


def sceneupsample_display_page(request):
    folder_path = os.path.join(STATIC_DIR, SCENEUPSAMPLE_DIRNAME)
    pc_names = [get_file_name(os.path.basename(file_path)) for file_path in glob(os.path.join(folder_path, 'oral_scans', '*.ply'))]
    pc_names.sort()
    
    num_models = len(pc_names)
    show_pages = (num_models > 0)
    if not show_pages:
        return render(request, 'sceneupsample-display.html', locals())
    
    num_per_page = 6
    request_page_id = 1
    if 'request_page_id' in request.GET:
        request_page_id = request.GET['request_page_id']
        request_page_id = int(request_page_id)
    num_pages, page_ids, first_page_id, last_page_id, prev_page_id, next_page_id = _get_pages(num_models, request_page_id, num_per_page=num_per_page)
    if request_page_id > num_pages:
        request_page_id = num_pages
    
    disable_first_page = (request_page_id == first_page_id)
    disable_last_page = (request_page_id == last_page_id)
    disable_prev_page = (request_page_id == prev_page_id)
    disable_next_page = (request_page_id == next_page_id)

    start_id = (request_page_id - 1) * num_per_page
    end_id = request_page_id * num_per_page
    pc_names = pc_names[start_id:end_id]

    return render(request, 'sceneupsample-display.html', locals())


def sceneupsample_vis_page(request):
    if 'pc_name' not in request.GET:
        return render(request, '404.html', locals())
    pc_name = request.GET['pc_name']

    img_names = [get_file_name(os.path.basename(file_path)) for file_path in
                glob(os.path.join(STATIC_DIR, SCENEUPSAMPLE_DIRNAME, 'render_imgs', pc_name, 'img', '*.png'))]
    # 排序来看
    img_names.sort()
    image_paths = []
    for name in img_names:
        image_paths.append(os.path.join('/static', SCENEUPSAMPLE_DIRNAME, 'render_imgs', pc_name, 'img', '%s.png' % name))
        image_paths.append(os.path.join('/static', SCENEUPSAMPLE_DIRNAME, 'render_imgs', pc_name, 'label', '%s.png' % name))

    return render(request, 'sceneupsample-vis.html', locals())




def segdataset_display_page(request):
    folder_path = os.path.join(STATIC_DIR, SEGDATASET_DIRNAME)
    pc_names = [get_file_name(os.path.basename(file_path)) for file_path in glob(os.path.join(folder_path, 'seg_results', '*.ply'))]
    pc_names.sort()
    
    num_models = len(pc_names)
    show_pages = (num_models > 0)
    if not show_pages:
        return render(request, 'segdataset-display.html', locals())
    
    num_per_page = 6
    request_page_id = 1
    if 'request_page_id' in request.GET:
        request_page_id = request.GET['request_page_id']
        request_page_id = int(request_page_id)
    num_pages, page_ids, first_page_id, last_page_id, prev_page_id, next_page_id = _get_pages(num_models, request_page_id, num_per_page=num_per_page)
    if request_page_id > num_pages:
        request_page_id = num_pages
    
    disable_first_page = (request_page_id == first_page_id)
    disable_last_page = (request_page_id == last_page_id)
    disable_prev_page = (request_page_id == prev_page_id)
    disable_next_page = (request_page_id == next_page_id)

    start_id = (request_page_id - 1) * num_per_page
    end_id = request_page_id * num_per_page
    pc_names = pc_names[start_id:end_id]

    return render(request, 'segdataset-display.html', locals())


def segdataset_vis_page(request):
    if 'pc_name' not in request.GET:
        return render(request, '404.html', locals())
    pc_name = request.GET['pc_name']

    raw_file_path = os.path.join('/static', SEGDATASET_DIRNAME, 'oral_scans', 'gt_%s.ply' % pc_name)
    seg_file_path = os.path.join('/static', SEGDATASET_DIRNAME, 'seg_results', '%s.ply' % pc_name)
    gt_file_path = os.path.join('/static', SEGDATASET_DIRNAME, 'oral_scans', 'gt_%s.ply' % pc_name)
    return render(request, 'segdataset-vis.html', locals())



def sceneseg_display_page(request):
    folder_path = os.path.join(STATIC_DIR, SCENESEG_DIRNAME)
    pc_names = [get_file_name(os.path.basename(file_path)) for file_path in glob(os.path.join(folder_path, 'oral_scans', '*.ply'))]
    pc_names.sort()
    
    num_models = len(pc_names)
    show_pages = (num_models > 0)
    if not show_pages:
        return render(request, 'sceneseg-display.html', locals())
    
    num_per_page = 6
    request_page_id = 1
    if 'request_page_id' in request.GET:
        request_page_id = request.GET['request_page_id']
        request_page_id = int(request_page_id)
    num_pages, page_ids, first_page_id, last_page_id, prev_page_id, next_page_id = _get_pages(num_models, request_page_id, num_per_page=num_per_page)
    if request_page_id > num_pages:
        request_page_id = num_pages
    
    disable_first_page = (request_page_id == first_page_id)
    disable_last_page = (request_page_id == last_page_id)
    disable_prev_page = (request_page_id == prev_page_id)
    disable_next_page = (request_page_id == next_page_id)

    start_id = (request_page_id - 1) * num_per_page
    end_id = request_page_id * num_per_page
    pc_names = pc_names[start_id:end_id]

    return render(request, 'sceneseg-display.html', locals())


def sceneseg_vis_page(request):
    if 'pc_name' not in request.GET:
        return render(request, '404.html', locals())
    pc_name = request.GET['pc_name']

    # exists = os.path.exists(os.path.join(STATIC_DIR, SCENESEG_DIRNAME, 'raw', '%s.ply' % pc_name))
    # exists &= os.path.exists(os.path.join(STATIC_DIR, SCENESEG_DIRNAME, 'color', '%s.ply' % pc_name))
    # exists &= os.path.exists(os.path.join(STATIC_DIR, SCENESEG_DIRNAME, 'seg', '%s.ply' % pc_name))
    # if not exists:
    #     return render(request, '404.html', locals())

    seg_file_path = os.path.join('/static', SCENESEG_DIRNAME, 'oral_scans', '%s.ply' % pc_name)
    # 单独牙齿以及特征点
    landmark_files = [get_file_name(os.path.basename(file_path))
                      for file_path in glob(os.path.join(STATIC_DIR, SCENESEG_DIRNAME, 'landmarks', pc_name, '*.ply'))]

    # print(landmark_files)

    landmark_mesh_files = [os.path.join('/static', SCENESEG_DIRNAME, 'landmarks', pc_name, '%s.ply' % file)
                           for file in landmark_files if 'heatmap' not in file and 'landmark' not in file]
    landmark_point_files = [os.path.join('/static', SCENESEG_DIRNAME, 'landmarks', pc_name, '%s.ply' % file)
                           for file in landmark_files if 'landmark' in file]

    print(landmark_point_files)
    print(landmark_mesh_files)
    return render(request, 'sceneseg-vis.html', locals())




def _get_mypcbase_pc_names(folder_name='default'):
    files = glob(os.path.join(STATIC_DIR, MYPCBASE_DIRNAME, folder_name, '*.ply'))
    pc_names = []
    for file in files:
        pc_name = get_file_name(file)
        pc_names.append({'pc_name': pc_name})
    return pc_names

def _get_mypcbase_folders():
    items = glob(os.path.join(STATIC_DIR, MYPCBASE_DIRNAME, '*'))
    folders = []
    for item in items:
        if not os.path.isdir(item):
            continue
        folder = os.path.basename(item)
        if folder not in ['default', 'temp']:
            folders.append(folder)
    folders.sort()
    return folders

def mypcbase_upload_page(request):
    folder_names = _get_mypcbase_folders()
    return render(request, 'mypcbase-upload.html', locals())

def _get_pages(num_models, request_page_id=1, num_per_page=4):
    num_pages = int(math.ceil(num_models / num_per_page))
    if request_page_id > num_pages:
        request_page_id = num_pages
    
    first_page_id = 1
    last_page_id = num_pages
    prev_page_id = request_page_id - 1
    if prev_page_id < 1:
        prev_page_id = 1
    next_page_id = request_page_id + 1
    if next_page_id > num_pages:
        next_page_id = num_pages

    page_ids = []
    for page_id in range(request_page_id - 2, request_page_id + 3):
        if 1 <= page_id <= num_pages:
            page_ids.append(page_id)
    
    return num_pages, page_ids, first_page_id, last_page_id, prev_page_id, next_page_id


def mypcbase_display_page(request):
    folder_names = _get_mypcbase_folders()
    num_folders = len(folder_names)
    show_pages = True
    
    num_per_page = 8
    request_page_id = 1
    if 'request_page_id' in request.GET:
        request_page_id = request.GET['request_page_id']
        request_page_id = int(request_page_id)
    num_pages, page_ids, first_page_id, last_page_id, prev_page_id, next_page_id = _get_pages(num_folders+1, request_page_id, num_per_page=num_per_page)
    if request_page_id > num_pages:
        request_page_id = num_pages
    if request_page_id < 1:
        request_page_id = 1
    
    disable_first_page = (request_page_id == first_page_id)
    disable_last_page = (request_page_id == last_page_id)
    disable_prev_page = (request_page_id == prev_page_id)
    disable_next_page = (request_page_id == next_page_id)

    start_id = (request_page_id - 1) * num_per_page
    end_id = request_page_id * num_per_page
    if request_page_id == 1:
        folder_names = folder_names[start_id:end_id-1]
    else:
        folder_names = folder_names[start_id-1:end_id]

    return render(request, 'mypcbase-display.html', locals())


def mypcbase_folder_display_page(request):
    folder_names = _get_mypcbase_folders()
    folder_names = ['default'] + folder_names

    folder_name = 'default'
    if 'folder_name' in request.GET:
        folder_name = request.GET['folder_name']

    pc_names = _get_mypcbase_pc_names(folder_name)
    num_models = len(pc_names)
    show_pages = (num_models > 0)
    if not show_pages:
        return render(request, 'mypcbase-folder-display.html', locals())    
    
    num_per_page = 6
    request_page_id = 1
    if 'request_page_id' in request.GET:
        request_page_id = request.GET['request_page_id']
        request_page_id = int(request_page_id)
    num_pages, page_ids, first_page_id, last_page_id, prev_page_id, next_page_id = _get_pages(num_models, request_page_id, num_per_page=num_per_page)
    if request_page_id > num_pages:
        request_page_id = num_pages
    
    disable_first_page = (request_page_id == first_page_id)
    disable_last_page = (request_page_id == last_page_id)
    disable_prev_page = (request_page_id == prev_page_id)
    disable_next_page = (request_page_id == next_page_id)

    start_id = (request_page_id - 1) * num_per_page
    end_id = request_page_id * num_per_page
    pc_names = pc_names[start_id:end_id]

    return render(request, 'mypcbase-folder-display.html', locals())


def mypcbase_vis_page(request, folder_name, pc_name):
    vis_type = 'obj'
    if 'vis_type' in request.GET:
        vis_type = request.GET['vis_type']
    
    folder_path = os.path.join(STATIC_DIR, MYPCBASE_DIRNAME, folder_name)
    xyz_file_path = os.path.join(folder_path, '%s.xyz' % pc_name)
    exists = os.path.exists(xyz_file_path)
    if not exists:
        return render(request, '404.html', locals())
    
    data = {}
    data['folder_name'] = folder_name
    data['pc_name'] = pc_name
    if vis_type == 'obj':
        obj_file_path = os.path.join(folder_path, '%s.obj' % pc_name)
        if not os.path.exists(obj_file_path):
            generate_points_obj(xyz_file_path, obj_file_path, prog_record=False)
        data['pc_file_path'] = os.path.join('/static', MYPCBASE_DIRNAME, folder_name, '%s.obj' % pc_name)
        return render(request, 'mypcbase-vis-obj.html', data)
    elif vis_type == 'ply':
        ply_file_path = os.path.join(folder_path, '%s.ply' % pc_name)
        if not os.path.exists(ply_file_path):
            xyz2ply(xyz_file_path, ply_file_path)
        data['pc_file_path'] = os.path.join('/static', MYPCBASE_DIRNAME, folder_name, '%s.ply' % pc_name)
        return render(request, 'mypcbase-vis-ply.html', data)
    
    return render(request, '404.html')


def mypcbase_vis_upsample_page(request, folder_name, pc_name):
    exists = os.path.exists(os.path.join(STATIC_DIR, MYPCBASE_DIRNAME, folder_name, '%s.obj' % pc_name))
    exists &= os.path.exists(os.path.join(STATIC_DIR, MYPCBASE_DIRNAME, folder_name, UPSAMPLE_DIRNAME, '%s.obj' % pc_name))
    if not exists:
        return render(request, '404.html', locals())

    raw_file_path = os.path.join('/static', MYPCBASE_DIRNAME, folder_name, '%s.obj' % pc_name)
    upsample_file_path = os.path.join('/static', MYPCBASE_DIRNAME, folder_name, UPSAMPLE_DIRNAME, '%s.obj' % pc_name)
    return render(request, 'mypcbase-vis-upsample.html', locals())


def recyclebin_display_page(request):
    # clear empty folders
    for folder_path in glob(os.path.join(STATIC_DIR, RECYCLEBIN_DIRNAME, '*')):
        if not os.path.isdir(folder_path):
            continue
        if count_num_files_for_dir(folder_path) == 0:
            delete_files_and_dirs(folder_path)

    folder_names = [os.path.basename(path) for path in glob(os.path.join(STATIC_DIR, RECYCLEBIN_DIRNAME, '*'))]
    folder_names.sort()
    num_folders = len(folder_names)
    show_pages = (num_folders > 0)
    if not show_pages:
        return render(request, 'recyclebin_display.html', locals())
    
    num_per_page = 8
    request_page_id = 1
    if 'request_page_id' in request.GET:
        request_page_id = request.GET['request_page_id']
        request_page_id = int(request_page_id)
    num_pages, page_ids, first_page_id, last_page_id, prev_page_id, next_page_id = _get_pages(num_folders, request_page_id, num_per_page=num_per_page)
    if request_page_id > num_pages:
        request_page_id = num_pages
    
    disable_first_page = (request_page_id == first_page_id)
    disable_last_page = (request_page_id == last_page_id)
    disable_prev_page = (request_page_id == prev_page_id)
    disable_next_page = (request_page_id == next_page_id)

    start_id = (request_page_id - 1) * num_per_page
    end_id = request_page_id * num_per_page
    folder_names = folder_names[start_id:end_id]

    return render(request, 'recyclebin_display.html', locals())


def recyclebin_folder_display_page(request):
    if 'folder_name' not in request.GET:
        return render(request, '404.html', locals())
    folder_name = request.GET['folder_name']

    files = glob(os.path.join(STATIC_DIR, RECYCLEBIN_DIRNAME, folder_name, '*.xyz'))
    pc_names = [get_file_name(file) for file in files]
    pc_names.sort()

    num_models = len(pc_names)
    show_pages = (num_models > 0)
    if not show_pages:
        return render(request, 'recyclebin_folder_display.html', locals())
    
    num_per_page = 6
    request_page_id = 1
    if 'request_page_id' in request.GET:
        request_page_id = request.GET['request_page_id']
        request_page_id = int(request_page_id)
    num_pages, page_ids, first_page_id, last_page_id, prev_page_id, next_page_id = _get_pages(num_models, request_page_id, num_per_page=num_per_page)
    if request_page_id > num_pages:
        request_page_id = num_pages
    
    disable_first_page = (request_page_id == first_page_id)
    disable_last_page = (request_page_id == last_page_id)
    disable_prev_page = (request_page_id == prev_page_id)
    disable_next_page = (request_page_id == next_page_id)

    start_id = (request_page_id - 1) * num_per_page
    end_id = request_page_id * num_per_page
    pc_names = pc_names[start_id:end_id]

    return render(request, 'recyclebin_folder_display.html', locals())


# =================================================================================================
# for ajax request (json)
@csrf_exempt
def mypcbase_upload(request):
    try:
        folder_name = 'default'
        if 'folder_name' in request.POST:
            folder_name = request.POST['folder_name']

        obj = request.FILES.get('file')
        file_name = get_file_name(obj.name)
        file_ext = get_file_ext(obj.name)
        file_name = file_name.replace('.', '_')

        file_path = os.path.join(STATIC_DIR, MYPCBASE_DIRNAME, folder_name, '%s.%s' % (file_name, file_ext))
        f = open(file_path, 'wb')
        for chunk in obj.chunks():
            f.write(chunk)
        f.close()

        # output_dir = os.path.join(STATIC_DIR, MYPCBASE_DIRNAME, folder_name)
        # file_name = get_file_name(file_path)
        # if get_file_ext(file_path) != 'xyz':
        #     points = load_file(file_path)
        #     save_file(output_dir, '%s.xyz' % file_name, points)

        # output_file_path = os.path.join(output_dir, '%s.obj' % file_name)
        # generate_points_obj(file_path, output_file_path, prog_record=True)
        data = { 'succ': 1, 'outputpath': os.path.join('/static', MYPCBASE_DIRNAME, folder_name, '%s.%s' % (file_name, file_ext)) }
    except TypeError:
        data = { 'succ': 0, 'errcode': 2 }
    except ShapeException:
        data = { 'succ': 0, 'errcode': 3 }
    except FileExistsException:
        data = { 'succ': 0, 'errcode': 4 }
    except:
        data = { 'succ': 0, 'errcode': 1 }

    return HttpResponse(json.dumps(data), content_type="application/json")


@csrf_exempt
def mypcbase_predict(request):
    try:
        folder_name = 'default'
        if 'folder_name' in request.POST:
            folder_name = request.POST['folder_name']
        obj = request.FILES.get('file')
        if not obj:
            return HttpResponse(json.dumps({'succ': 0, 'json': 'No file uploaded'}), content_type="application/json")

        file_name = get_file_name(obj.name)
        file_ext = get_file_ext(obj.name)
        file_name = file_name.replace('.', '_')
        local_file_path = os.path.join(STATIC_DIR, MYPCBASE_DIRNAME, folder_name, '%s.%s' % (file_name, file_ext))
        target_url = 'http://3672c6ae.r38.cpolar.top/predict_file/'  # 目标服务器的上传 URL

        # 获取目标服务器的 CSRF token
        session = requests.Session()

        # 获取 CSRF token
        # csrf_token = session.cookies.get('csrftoken')
        # if not csrf_token:
        #     return HttpResponse(json.dumps({'succ': 0, 'json': 'CSRF token not found'}),
        #                         content_type="application/json")

        # 使用 POST 请求上传文件
        with open(local_file_path, 'rb') as f:
            files = {'file': (os.path.basename(local_file_path), f)}  # 包装文件
            # headers = {
            #     'X-CSRFToken': csrf_token  # 添加 CSRF token 到请求头
            # }
            # print(f"Headers: {headers}")
            print(f"Local file path: {local_file_path}")

            # 使用 POST 请求上传文件
            response = session.post(target_url, files=files)

            if response.status_code == 200:
                data = {'succ': 1, 'json': response.json()}  # 成功信息
                base64_content = response.json().get('file_content')
                # 解码 Base64 字符串
                file_data = base64.b64decode(base64_content)
                # 写入到本地文件
                with open(os.path.join(STATIC_DIR, SEGDATASET_DIRNAME, 'oral_scans', 'gt_%s.%s' % (file_name, file_ext)), 'wb') as f:  # 可以选择一个不同的文件路径
                    f.write(file_data)
                with open(os.path.join(STATIC_DIR, SEGDATASET_DIRNAME, 'seg_results', '%s.%s' % (file_name, file_ext)), 'wb') as f:  # 可以选择一个不同的文件路径
                    f.write(file_data)

                landmarks = response.json().get('landmarks')
                if len(landmarks) != 0:
                    with open(os.path.join(STATIC_DIR, SCENESEG_DIRNAME, 'oral_scans', '%s.%s' % (file_name, file_ext)), 'wb') as f:  # 可以选择一个不同的文件路径
                        f.write(file_data)
                    os.mkdir(os.path.join(STATIC_DIR, SCENESEG_DIRNAME, 'landmarks', file_name))
                    for lm_name, lm_data in landmarks.items():
                        lm_data = base64.b64decode(lm_data)
                        with open(os.path.join(STATIC_DIR, SCENESEG_DIRNAME, 'landmarks', file_name, lm_name), 'wb') as f:
                            f.write(lm_data)
                        print(lm_name)
            else:
                data = {'succ': 0, 'json': response.text}  # 错误信息

        print("End of predict")

    except Timeout as e:
        print(f"请求超时: {e}")
        data = {'succ': 0, 'json': str(e)}
    except ConnectionError as e:
        print(f"连接错误: {e}")
        data = {'succ': 0, 'json': str(e)}
    except HTTPError as e:
        print(f"HTTP 错误: {e}")
        data = {'succ': 0, 'json': str(e)}
    except RequestException as e:
        print(f"请求异常: {e}")
        data = {'succ': 0, 'json': str(e)}
    except Exception as e:
        print(f"发生了意外的错误: {e}")
        data = {'succ': 0, 'json': str(e)}

    # print(data)
    return HttpResponse(json.dumps(data), content_type="application/json")

def mypcbase_delete(request):
    try:
        pc_name = request.GET['pc_name']
        folder_name = request.GET['folder_name']

        recyclebin_dir = os.path.join(STATIC_DIR, RECYCLEBIN_DIRNAME, folder_name)
        recyclebin_upsample_dir = os.path.join(STATIC_DIR, RECYCLEBIN_DIRNAME, folder_name, UPSAMPLE_DIRNAME)

        if not os.path.exists(recyclebin_dir):
            os.mkdir(recyclebin_dir)
        if not os.path.exists(recyclebin_upsample_dir):
            os.mkdir(recyclebin_upsample_dir)

        if os.path.exists(os.path.join(recyclebin_dir, '%s.xyz' % pc_name)):
            raise FileExistsException()

        related_files = glob(os.path.join(STATIC_DIR, MYPCBASE_DIRNAME, folder_name, '%s.*' % pc_name))
        if len(related_files) == 0:
            raise FileNotExistsException()
        for file in related_files:
            # os.remove(file)
            shutil.move(file, recyclebin_dir)
        
        related_upsample_files = glob(os.path.join(STATIC_DIR, MYPCBASE_DIRNAME, folder_name, UPSAMPLE_DIRNAME, '%s.*' % pc_name))
        for file in related_upsample_files:
            # os.remove(file)
            shutil.move(file, recyclebin_upsample_dir)

        data = { 'succ': 1 }
    except FileNotExistsException as e:
        print(e)
        data = { 'succ': 0, 'errcode': 2 }
    except FileExistsException as e:
        print(e)
        data = { 'succ': 0, 'errcode': 3 }
    except Exception as e:
        print(e)
        data = { 'succ': 0, 'errcode': 1 }
    
    return HttpResponse(json.dumps(data), content_type="application/json")


def mypcbase_folder_delete_all(request):
    try:
        if 'folder_name' not in request.GET:
            return HttpResponse(json.dumps({}), content_type="application/json")
        folder_name = request.GET['folder_name']

        delete_folder = 0
        if 'delete_folder' in request.GET:
            delete_folder = int(request.GET['delete_folder'])

        recyclebin_dir = os.path.join(STATIC_DIR, RECYCLEBIN_DIRNAME, folder_name)
        recyclebin_upsample_dir = os.path.join(STATIC_DIR, RECYCLEBIN_DIRNAME, folder_name, UPSAMPLE_DIRNAME)
        if not os.path.exists(recyclebin_dir):
            os.mkdir(recyclebin_dir)
        if not os.path.exists(recyclebin_upsample_dir):
            os.mkdir(recyclebin_upsample_dir)

        related_files = glob(os.path.join(STATIC_DIR, MYPCBASE_DIRNAME, folder_name, '*'))
        for file in related_files:
            if os.path.isfile(file):
                shutil.move(file, recyclebin_dir)
        
        related_upsample_files = glob(os.path.join(STATIC_DIR, MYPCBASE_DIRNAME, folder_name, UPSAMPLE_DIRNAME, '*'))
        for file in related_upsample_files:
            if os.path.isfile(file):
                shutil.move(file, recyclebin_upsample_dir)
        
        if delete_folder == 1:
            delete_files_and_dirs(os.path.join(STATIC_DIR, MYPCBASE_DIRNAME, folder_name))
        data = { 'succ': 1 }
    except Exception as e:
        print(e)
        data = { 'succ': 0, 'errcode': 1 }
    
    return HttpResponse(json.dumps(data), content_type="application/json")


def mypcbase_upsample(request):
    try:
        if 'pc_name' not in request.GET or 'folder_name' not in request.GET:
            return HttpResponse(json.dumps({}), content_type="application/json")

        pc_name = request.GET['pc_name']
        folder_name = request.GET['folder_name']
        if os.path.exists(os.path.join(STATIC_DIR, MYPCBASE_DIRNAME, folder_name, UPSAMPLE_DIRNAME, '%s.xyz' % pc_name)):
            raise FileExistsException()
        file_path = os.path.join(STATIC_DIR, MYPCBASE_DIRNAME, folder_name, '%s.xyz' % pc_name)
        pred_points = upsample_points(file_path)
        save_file(os.path.join(STATIC_DIR, MYPCBASE_DIRNAME, folder_name, UPSAMPLE_DIRNAME), '%s.xyz' % pc_name, pred_points)
        
        xyz_file_path = os.path.join(STATIC_DIR, MYPCBASE_DIRNAME, folder_name, UPSAMPLE_DIRNAME, '%s.xyz' % pc_name)
        obj_file_path = os.path.join(STATIC_DIR, MYPCBASE_DIRNAME, folder_name, UPSAMPLE_DIRNAME, '%s.obj' % pc_name)
        generate_points_obj(xyz_file_path, obj_file_path, prog_record=True)

        data = { 'succ': 1 }
    except FileExistsException as e:
        print(e)
        data = { 'succ': 0, 'errcode': 2 }
    except ShapeException as e:
        print(e)
        data = { 'succ': 0, 'errcode': 3 }
    except Exception as e:
        print(e)
        data = { 'succ': 0, 'errcode': 1 }
    
    return HttpResponse(json.dumps(data), content_type="application/json")


def mypcbase_zip_all(request):
    try:
        num_files = 0
        source_folders = []
        for path in glob(os.path.join(STATIC_DIR, MYPCBASE_DIRNAME, '*')):
            if os.path.isdir(path):
                folder_name = os.path.basename(path)
                if folder_name not in ['temp']:
                    source_folders.append(folder_name)
        
        ts = int(time())
        dest_dir = os.path.join(STATIC_DIR, MYPCBASE_DIRNAME, 'temp', str(ts))
        if not os.path.exists(dest_dir):
            os.mkdir(dest_dir)

        for folder_name in source_folders:
            source_files = glob(os.path.join(STATIC_DIR, MYPCBASE_DIRNAME, folder_name, '*.xyz'))
            source_upsample_files = glob(os.path.join(STATIC_DIR, MYPCBASE_DIRNAME, folder_name, UPSAMPLE_DIRNAME, '*.xyz'))
            if len(source_files) == 0:
                continue
            num_files += len(source_files)
        
            if not os.path.exists(os.path.join(dest_dir, folder_name)):
                os.mkdir(os.path.join(dest_dir, folder_name))
            if not os.path.exists(os.path.join(dest_dir, folder_name, UPSAMPLE_DIRNAME)):
                os.mkdir(os.path.join(dest_dir, folder_name, UPSAMPLE_DIRNAME))
        
            for file in source_files:
                shutil.copy(file, os.path.join(dest_dir, folder_name))
            for file in source_upsample_files:
                shutil.copy(file, os.path.join(dest_dir, folder_name, UPSAMPLE_DIRNAME))
        
        if num_files == 0:
            raise NoFilesException()

        output_zip_path = os.path.join(STATIC_DIR, MYPCBASE_DIRNAME, 'temp', '%d.zip' % ts)
        zip_dir(dest_dir, output_zip_path)
        delete_files_and_dirs(dest_dir)
        data = { 'succ': 1, 'zipfile_url': os.path.join('/static', MYPCBASE_DIRNAME, 'temp', '%d.zip' % ts) }
    except NoFilesException as e:
        print(e)
        data = { 'succ': 0, 'errcode': 0 }
    except Exception as e:
        print(e)
        data = { 'succ': 0, 'errcode': 1 }

    return HttpResponse(json.dumps(data), content_type="application/json")


def mypcbase_folder_zip_all(request):
    try:
        if 'folder_name' not in request.GET:
            return HttpResponse(json.dumps({}), content_type="application/json")
        folder_name = request.GET['folder_name']

        source_files = glob(os.path.join(STATIC_DIR, MYPCBASE_DIRNAME, folder_name, '*.xyz'))
        source_upsample_files = glob(os.path.join(STATIC_DIR, MYPCBASE_DIRNAME, folder_name, UPSAMPLE_DIRNAME, '*.xyz'))
        if 0 == len(source_files):
            raise NoFilesException()

        ts = int(time())
        dest_dir = os.path.join(STATIC_DIR, MYPCBASE_DIRNAME, 'temp', str(ts))
        if not os.path.exists(dest_dir):
            os.mkdir(dest_dir)
        if not os.path.exists(os.path.join(dest_dir, 'upsample')):
            os.mkdir(os.path.join(dest_dir, 'upsample'))
        
        for file in source_files:
            shutil.copy(file, dest_dir)
        for file in source_upsample_files:
            shutil.copy(file, os.path.join(dest_dir, 'upsample'))
        
        output_zip_path = os.path.join(STATIC_DIR, MYPCBASE_DIRNAME, 'temp', '%d.zip' % ts)
        zip_dir(dest_dir, output_zip_path)
        delete_files_and_dirs(dest_dir)
        data = { 'succ': 1, 'zipfile_url': os.path.join('/static', MYPCBASE_DIRNAME, 'temp', '%d.zip' % ts) }
    except NoFilesException as e:
        print(e)
        data = { 'succ': 0, 'errcode': 0 }
    except Exception as e:
        print(e)
        data = { 'succ': 0, 'errcode': 1 }

    return HttpResponse(json.dumps(data), content_type="application/json")


def mypcbase_clear_temp_dir(request):
    limited_time = float(request.GET['limited_time'])
    temp_dir = os.path.join(STATIC_DIR, MYPCBASE_DIRNAME, 'temp')
    clear_dir_with_time(temp_dir, limited_time=limited_time)
    data = { 'succ': 1 }

    return HttpResponse(json.dumps(data), content_type="application/json")

def mypcbase_get_progress_val(request):
    prog_file_name = request.GET['prog_file_name']
    file_path = os.path.join(STATIC_DIR, MYPCBASE_DIRNAME, 'temp', prog_file_name)
    prog_val = 0
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            prog_val = f.read().strip()
            if prog_val == '':
                prog_val = -1
            else:
                prog_val = int(prog_val)
    return JsonResponse(prog_val, safe=False)


def mypcbase_create_folder(request):
    if 'folder_name' not in request.GET:
        return HttpResponse(json.dumps({}), content_type="application/json")
    
    try:
        folder_name = request.GET['folder_name']
        folder_path = os.path.join(STATIC_DIR, MYPCBASE_DIRNAME, folder_name)
        if os.path.exists(folder_path):
            raise FileExistsException()
        
        os.mkdir(folder_path)
        os.mkdir(os.path.join(folder_path, UPSAMPLE_DIRNAME))
        data = { 'succ': 1 }
    except FileExistsException as e:
        print(e)
        data = { 'succ': 0, 'errcode': 2 }
    except Exception as e:
        print(e)
        data = { 'succ': 0, 'errcode': 1 }
    return HttpResponse(json.dumps(data), content_type="application/json")


def mypcbase_rename_folder(request):
    if 'old_folder_name' not in request.GET or 'new_folder_name' not in request.GET:
        return HttpResponse(json.dumps({}), content_type="application/json")

    try:
        old_folder_name = request.GET['old_folder_name']
        new_folder_name = request.GET['new_folder_name']

        old_path = os.path.join(STATIC_DIR, MYPCBASE_DIRNAME, old_folder_name)
        new_path = os.path.join(STATIC_DIR, MYPCBASE_DIRNAME, new_folder_name)
        if os.path.exists(new_path):
            raise FileExistsException()
        
        os.rename(old_path, new_path)
        data = { 'succ': 1 }
    except FileExistsException as e:
        print(e)
        data = { 'succ': 0, 'errcode': 2 }
    except Exception as e:
        print(e)
        data = { 'succ': 0, 'errcode': 1 }
    return HttpResponse(json.dumps(data), content_type="application/json")

def mypcbase_folder_move_pc(request):
    if 'source_folder_name' not in request.GET or 'dest_folder_name' not in request.GET or 'pc_name' not in request.GET:
        return HttpResponse(json.dumps({}), content_type="application/json")
    
    try:
        pc_name = request.GET['pc_name']
        source_folder_name = request.GET['source_folder_name']
        dest_folder_name = request.GET['dest_folder_name']
        
        dest_folder_path = os.path.join(STATIC_DIR, MYPCBASE_DIRNAME, dest_folder_name)
        dest_upsample_folder_path = os.path.join(STATIC_DIR, MYPCBASE_DIRNAME, dest_folder_name, UPSAMPLE_DIRNAME)
        if not os.path.exists(dest_folder_path):
            raise FileNotExistsException()
        if os.path.exists(os.path.join(dest_folder_path, '%s.xyz' % pc_name)):
            raise FileExistsException()

        related_files = glob(os.path.join(STATIC_DIR, MYPCBASE_DIRNAME, source_folder_name, '%s.*' % pc_name))
        for file in related_files:
            shutil.move(file, dest_folder_path)
        related_upsample_files = glob(os.path.join(STATIC_DIR, MYPCBASE_DIRNAME, source_folder_name, UPSAMPLE_DIRNAME, '%s.*' % pc_name))
        for file in related_upsample_files:
            shutil.move(file, dest_upsample_folder_path)

        data = { 'succ': 1 }
    except FileNotExistsException as e:
        print(e)
        data = { 'succ': 0, 'errcode': 2 }
    except FileExistsException as e:
        print(e)
        data = { 'succ': 0, 'errcode': 3 }
    except Exception as e:
        print(e)
        data = { 'succ': 0, 'errcode': 1 }
    return HttpResponse(json.dumps(data), content_type="application/json")


def mypcbase_save_ply_with_rgb(request):
    if 'folder_name' not in request.GET or 'pc_name' not in request.GET or 'red' not in request.GET or 'green' not in request.GET or 'blue' not in request.GET:
        return HttpResponse(json.dumps({}), content_type="application/json")
    try:
        folder_name = request.GET['folder_name']
        pc_name = request.GET['pc_name']
        red = int(request.GET['red'])
        green = int(request.GET['green'])
        blue = int(request.GET['blue'])
        
        folder_path = os.path.join(STATIC_DIR, MYPCBASE_DIRNAME, folder_name)
        input_xyz_path = os.path.join(folder_path, '%s.xyz' % pc_name)
        output_ply_path = os.path.join(folder_path, '%s.ply' % pc_name)
        xyz2ply_with_rgb(input_xyz_path, output_ply_path, red, green, blue)
        data = { 'succ': 1 }
    except Exception as e:
        print(e)
        data = { 'succ': 0 }
    return HttpResponse(json.dumps(data), content_type="application/json")


def mypcbase_get_texture_path(request):
    if 'red' not in request.GET or 'green' not in request.GET or 'blue' not in request.GET:
        return HttpResponse(json.dumps({}), content_type="application/json")
    try:
        folder_path = os.path.join(STATIC_DIR, 'img', 'texture')
        red = int(request.GET['red'])
        green = int(request.GET['green'])
        blue = int(request.GET['blue'])
        
        texture_file_path = os.path.join(folder_path, "%d_%d_%d.png" % (red, green, blue))
        if not os.path.exists(texture_file_path):
            arr =  np.zeros((1024, 1024, 3))
            arr[:, :, :] = np.array([blue, green, red])
            arr = np.array(arr, dtype=np.int)
            cv2.imwrite(texture_file_path, arr)

        texture_file_path = '/static/img/texture/%d_%d_%d.png' % (red, green, blue)
        data = { 'texture_file_path': texture_file_path, 'succ': 1 }
    except Exception as e:
        print(e)
        data = { 'succ': 0 }
    return HttpResponse(json.dumps(data), content_type="application/json")


def recyclebin_delete(request):
    try:
        if 'pc_name' not in request.GET or 'folder_name' not in request.GET:
            return HttpResponse(json.dumps({}), content_type="application/json")
        
        pc_name = request.GET['pc_name']
        folder_name = request.GET['folder_name']
        related_files = glob(os.path.join(STATIC_DIR, RECYCLEBIN_DIRNAME, folder_name, '%s.*' % pc_name))
        if len(related_files) == 0:
            raise FileNotExistsException()
        for file in related_files:
            os.remove(file)
        
        related_upsample_files = glob(os.path.join(STATIC_DIR, RECYCLEBIN_DIRNAME, folder_name, UPSAMPLE_DIRNAME, '%s.*' % pc_name))
        for file in related_upsample_files:
            os.remove(file)
            
        data = { 'succ': 1 }
    except FileNotExistsException as e:
        print(e)
        data = { 'succ': 0, 'errcode': 2 }
    except Exception as e:
        print(e)
        data = { 'succ': 0, 'errcode': 1 }
    
    return HttpResponse(json.dumps(data), content_type="application/json")


def recyclebin_folder_delete_all(request):
    try:
        if 'folder_name' not in request.GET:
            return HttpResponse(json.dumps(data), content_type="application/json")

        folder_name = request.GET['folder_name']
        related_files = glob(os.path.join(STATIC_DIR, RECYCLEBIN_DIRNAME, folder_name, '*'))
        for file in related_files:
            if os.path.isfile(file):
                os.remove(file)
        
        related_upsample_files = glob(os.path.join(STATIC_DIR, RECYCLEBIN_DIRNAME, folder_name, UPSAMPLE_DIRNAME, '*'))
        for file in related_upsample_files:
            if os.path.isfile(file):
                os.remove(file)
            
        data = { 'succ': 1 }
    except Exception as e:
        print(e)
        data = { 'succ': 0, 'errcode': 1 }
    
    return HttpResponse(json.dumps(data), content_type="application/json")


def recyclebin_delete_all(request):
    try:
        for path in glob(os.path.join(STATIC_DIR, RECYCLEBIN_DIRNAME, '*')):
            delete_files_and_dirs(path)

        data = { 'succ': 1 }
    except Exception as e:
        print(e)
        data = { 'succ': 0, 'errcode': 1 }
    
    return HttpResponse(json.dumps(data), content_type="application/json")


def recyclebin_restore(request):
    try:
        if 'pc_name' not in request.GET or 'folder_name' not in request.GET:
            return HttpResponse(json.dumps({}), content_type="application/json")
        
        folder_name = request.GET['folder_name']
        pc_name = request.GET['pc_name']
        pcbase_dir = os.path.join(STATIC_DIR, MYPCBASE_DIRNAME, folder_name)
        pcbase_upsample_dir = os.path.join(STATIC_DIR, MYPCBASE_DIRNAME, folder_name, UPSAMPLE_DIRNAME)
        if not os.path.exists(pcbase_dir):
            os.mkdir(pcbase_dir)
        if not os.path.exists(pcbase_upsample_dir):
            os.mkdir(pcbase_upsample_dir)

        if os.path.exists(os.path.join(pcbase_dir, '%s.xyz') % pc_name):
            raise FileExistsException()

        related_files = glob(os.path.join(STATIC_DIR, RECYCLEBIN_DIRNAME, folder_name, '%s.*' % pc_name))
        if len(related_files) == 0:
            raise FileNotExistsException()
        for file in related_files:
            shutil.move(file, pcbase_dir)
        
        related_upsample_files = glob(os.path.join(STATIC_DIR, RECYCLEBIN_DIRNAME, folder_name, UPSAMPLE_DIRNAME, '%s.*' % pc_name))
        for file in related_upsample_files:
            shutil.move(file, pcbase_upsample_dir)

        data = { 'succ': 1 }
    except FileNotExistsException as e:
        print(e)
        data = { 'succ': 0, 'errcode': 2 }
    except FileExistsException as e:
        print(e)
        data = { 'succ': 0, 'errcode': 3 }
    except Exception as e:
        print(e)
        data = { 'succ': 0, 'errcode': 1 }

    return HttpResponse(json.dumps(data), content_type="application/json")


def recyclebin_folder_restore_all(request):
    try:
        if 'folder_name' not in request.GET:
            return HttpResponse(json.dumps({}), content_type="application/json")
        
        folder_name = request.GET['folder_name']
        pcbase_dir = os.path.join(STATIC_DIR, MYPCBASE_DIRNAME, folder_name)
        pcbase_upsample_dir = os.path.join(STATIC_DIR, MYPCBASE_DIRNAME, folder_name, UPSAMPLE_DIRNAME)
        if not os.path.exists(pcbase_dir):
            os.mkdir(pcbase_dir)
        if not os.path.exists(pcbase_upsample_dir):
            os.mkdir(pcbase_upsample_dir)

        related_files = glob(os.path.join(STATIC_DIR, RECYCLEBIN_DIRNAME, folder_name, '*'))
        for file in related_files:
            if os.path.isfile(file):
                shutil.move(file, pcbase_dir)
        
        related_upsample_files = glob(os.path.join(STATIC_DIR, RECYCLEBIN_DIRNAME, folder_name, UPSAMPLE_DIRNAME, '*'))
        for file in related_upsample_files:
            if os.path.isfile(file):
                shutil.move(file, pcbase_upsample_dir)
            
        data = { 'succ': 1 }
    except Exception as e:
        print(e)
        data = { 'succ': 0, 'errcode': 1 }
    
    return HttpResponse(json.dumps(data), content_type="application/json")


def recyclebin_restore_all(request):
    try:
        for item in glob(os.path.join(STATIC_DIR, RECYCLEBIN_DIRNAME, '*')):
            folder_name = os.path.basename(item)
        
            pcbase_dir = os.path.join(STATIC_DIR, MYPCBASE_DIRNAME, folder_name)
            pcbase_upsample_dir = os.path.join(STATIC_DIR, MYPCBASE_DIRNAME, folder_name, UPSAMPLE_DIRNAME)
            if not os.path.exists(pcbase_dir):
                os.mkdir(pcbase_dir)
            if not os.path.exists(pcbase_upsample_dir):
                os.mkdir(pcbase_upsample_dir)

            related_files = glob(os.path.join(STATIC_DIR, RECYCLEBIN_DIRNAME, folder_name, '*'))
            for file in related_files:
                if os.path.isfile(file):
                    shutil.move(file, pcbase_dir)
        
            related_upsample_files = glob(os.path.join(STATIC_DIR, RECYCLEBIN_DIRNAME, folder_name, UPSAMPLE_DIRNAME, '*'))
            for file in related_upsample_files:
                if os.path.isfile(file):
                    shutil.move(file, pcbase_upsample_dir)
            
            delete_files_and_dirs(os.path.join(STATIC_DIR, RECYCLEBIN_DIRNAME, folder_name))
            
        data = { 'succ': 1 }
    except Exception as e:
        print(e)
        data = { 'succ': 0, 'errcode': 1 }
    
    return HttpResponse(json.dumps(data), content_type="application/json")


# ===============================================================================================
@csrf_exempt
def test(request):
    pc_file_path = os.path.join('/static', MYPCBASE_DIRNAME, '%s.obj' % 'eight')
    return render(request, 'test.html', locals())
