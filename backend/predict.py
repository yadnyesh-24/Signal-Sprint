import os
import pickle
import tempfile
import io
import numpy as np
from PIL import Image
from ultralytics import YOLO

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PICKLE_PATH = os.path.join(SCRIPT_DIR, "model.pkl")

STAGE1_CONFIDENCE_THRESHOLD  = 0.25
STAGE1_SCORE_THRESHOLD       = 0.5
GARBAGE_CONFIDENCE_THRESHOLD = 0.25


def load_model():
    with open(MODEL_PICKLE_PATH, 'rb') as f:
        data = pickle.load(f)
    tmp_dir = tempfile.mkdtemp()
    stage1_path = os.path.join(tmp_dir, "stage1.pt")
    stage2_path = os.path.join(tmp_dir, "stage2.pt")
    with open(stage1_path, "wb") as f:
        f.write(data['stage1_bytes'])
    with open(stage2_path, "wb") as f:
        f.write(data['stage2_bytes'])
    
    xgboost_model = None
    xgboost_feature_names = None
    
    if 'xgboost_bytes' in data:
        xgboost_buffer = io.BytesIO(data['xgboost_bytes'])
        xgboost_data = pickle.load(xgboost_buffer)
        xgboost_model = xgboost_data['xgboost_model']
        xgboost_feature_names = xgboost_data['xgboost_feature_names']
    
    return {
        'yolo_bin_model': YOLO(stage1_path),
        'yolo_garbage_model': YOLO(stage2_path),
        'device': data['device'],
        'xgboost_model': xgboost_model,
        'xgboost_feature_names': xgboost_feature_names,
    }


def box_intersection_area(box1, box2):
    x1_min, y1_min, x1_max, y1_max = box1[:4]
    x2_min, y2_min, x2_max, y2_max = box2[:4]

    inter_x_min = max(x1_min, x2_min)
    inter_y_min = max(y1_min, y2_min)
    inter_x_max = min(x1_max, x2_max)
    inter_y_max = min(y1_max, y2_max)

    if inter_x_max <= inter_x_min or inter_y_max <= inter_y_min:
        return 0.0

    return (inter_x_max - inter_x_min) * (inter_y_max - inter_y_min)


def compute_distance_between_boxes(garbage_box, bin_box):
    g_x1, g_y1, g_x2, g_y2 = garbage_box[:4]
    b_x1, b_y1, b_x2, b_y2 = bin_box[:4]
    
    g_cx = (g_x1 + g_x2) / 2
    g_cy = (g_y1 + g_y2) / 2
    b_cx = (b_x1 + b_x2) / 2
    b_cy = (b_y1 + b_y2) / 2
    
    distance = np.sqrt((g_cx - b_cx)**2 + (g_cy - b_cy)**2)
    return distance


def compute_garbage_area(box):
    x1, y1, x2, y2 = box[:4]
    return (x2 - x1) * (y2 - y1)




def compute_xgboost_features(trash_can_boxes, garbage_boxes, 
                            bin_allowed_confs, bin_not_allowed_confs, 
                            garbage_conf_scores, feature_names):
    
    features = {}
    
    if not garbage_boxes:
        features['total_garbage_area'] = 0.0
        features['avg_garbage_area'] = 0.0
        features['num_garbage_pieces'] = 0
        features['min_distance_to_bin'] = 0.0
        features['avg_distance_to_bins'] = 0.0
        features['max_distance_to_bins'] = 0.0
        features['mean_overlap_area'] = 0.0
    elif not trash_can_boxes:
        garbage_areas = [compute_garbage_area(gb) for gb in garbage_boxes]
        features['total_garbage_area'] = float(sum(garbage_areas))
        features['avg_garbage_area'] = float(np.mean(garbage_areas))
        features['num_garbage_pieces'] = len(garbage_boxes)
        features['min_distance_to_bin'] = 500.0
        features['avg_distance_to_bins'] = 500.0
        features['max_distance_to_bins'] = 500.0
        features['mean_overlap_area'] = 0.0
    else:
        garbage_areas = []
        distances_to_nearest_bin = []
        total_overlap_area = 0.0
        
        for garbage_box in garbage_boxes:
            garbage_areas.append(compute_garbage_area(garbage_box))
            distances = [compute_distance_between_boxes(garbage_box, bin_box) for bin_box in trash_can_boxes]
            nearest_dist = min(distances)
            distances_to_nearest_bin.append(nearest_dist)
            
            for bin_box in trash_can_boxes:
                overlap = box_intersection_area(garbage_box, bin_box)
                total_overlap_area += overlap
        
        total_garbage_area = sum(garbage_areas)
        features['total_garbage_area'] = float(total_garbage_area)
        features['avg_garbage_area'] = float(np.mean(garbage_areas))
        features['num_garbage_pieces'] = len(garbage_boxes)
        features['min_distance_to_bin'] = float(min(distances_to_nearest_bin))
        features['avg_distance_to_bins'] = float(np.mean(distances_to_nearest_bin))
        features['max_distance_to_bins'] = float(max(distances_to_nearest_bin))
        
        features['mean_overlap_area'] = float(total_overlap_area / total_garbage_area) if total_garbage_area > 0 else 0.0
    
    features['mean_allowed_bin_conf'] = float(np.mean(bin_allowed_confs)) if bin_allowed_confs else 0.0
    features['mean_not_allowed_bin_conf'] = float(np.mean(bin_not_allowed_confs)) if bin_not_allowed_confs else 0.0
    features['bin_conf_diff'] = features['mean_allowed_bin_conf'] - features['mean_not_allowed_bin_conf']
    
    features['num_allowed_bins'] = len(bin_allowed_confs)
    features['num_unauthorized_bins'] = len(bin_not_allowed_confs)
    
    if garbage_conf_scores:
        features['mean_garbage_conf'] = float(np.mean(garbage_conf_scores))
        features['std_garbage_conf'] = float(np.std(garbage_conf_scores))
        features['min_garbage_conf'] = float(np.min(garbage_conf_scores))
        features['max_garbage_conf'] = float(np.max(garbage_conf_scores))
    else:
        features['mean_garbage_conf'] = 0.0
        features['std_garbage_conf'] = 0.0
        features['min_garbage_conf'] = 0.0
        features['max_garbage_conf'] = 0.0
    
    feature_vector = np.array([[features[fname] for fname in feature_names]])
    return feature_vector




def predict_scores(model, image_path, garbage_conf_threshold=GARBAGE_CONFIDENCE_THRESHOLD):
    yolo_bin_model     = model['yolo_bin_model']
    yolo_garbage_model = model['yolo_garbage_model']

    bin_model_names          = yolo_bin_model.names
    ALLOWED_BIN_CLASS_ID     = next((k for k, v in bin_model_names.items() if v == "allowed_bin"), None)
    NOT_ALLOWED_BIN_CLASS_ID = next((k for k, v in bin_model_names.items() if v == "not_allowed_bin"), None)
    if ALLOWED_BIN_CLASS_ID is None or NOT_ALLOWED_BIN_CLASS_ID is None:
        raise ValueError(f"Unexpected class names in model: {bin_model_names}")

    try:
        image = Image.open(str(image_path)).convert('RGB')
        image = np.array(image)
    except Exception:
        return {
            'stage1_score':      -1.0,
            'stage1_passed':     0,
            'trash_can_boxes':   [],
            'garbage_boxes':     [],
            'allowed_confs':     [],
            'not_allowed_confs': [],
            'garbage_confs':     [],
        }
    if image is None:
        return {
            'stage1_score':      -1.0,
            'stage1_passed':     0,
            'trash_can_boxes':   [],
            'garbage_boxes':     [],
            'allowed_confs':     [],
            'not_allowed_confs': [],
            'garbage_confs':     [],
        }

    stage1_results    = yolo_bin_model.predict(source=image, conf=STAGE1_CONFIDENCE_THRESHOLD, imgsz=512, verbose=False)
    allowed_confs     = []
    not_allowed_confs = []
    trash_can_boxes   = []

    r = stage1_results[0]
    if len(r.boxes) > 0:
        for box in r.boxes:
            cls_id = int(box.cls)
            conf   = float(box.conf)
            coords = box.xyxy.cpu().numpy()[0]
            trash_can_boxes.append(coords)

            if cls_id == ALLOWED_BIN_CLASS_ID:
                allowed_confs.append(conf)
            elif cls_id == NOT_ALLOWED_BIN_CLASS_ID:
                not_allowed_confs.append(conf)

    allowed_mean     = sum(allowed_confs) / len(allowed_confs) if allowed_confs else 0.0
    not_allowed_mean = sum(not_allowed_confs) / len(not_allowed_confs) if not_allowed_confs else 0.0
    stage1_score     = allowed_mean - not_allowed_mean
    stage1_passed    = int(stage1_score >= STAGE1_SCORE_THRESHOLD)

    if not stage1_passed:
        return {
            'stage1_score':      stage1_score,
            'stage1_passed':     0,
            'trash_can_boxes':   trash_can_boxes,
            'garbage_boxes':     [],
            'allowed_confs':     allowed_confs,
            'not_allowed_confs': not_allowed_confs,
            'garbage_confs':     [],
        }

    garbage_boxes       = []
    garbage_conf_scores = []
    garbage_results = yolo_garbage_model(image, conf=garbage_conf_threshold, imgsz=512, verbose=False)

    if garbage_results and len(garbage_results) > 0:
        boxes = garbage_results[0].boxes
        if boxes is not None and len(boxes) > 0:
            xyxy  = boxes.xyxy.cpu().numpy()
            confs = boxes.conf.cpu().numpy()
            for box_coords, conf in zip(xyxy, confs):
                garbage_boxes.append(box_coords)
                garbage_conf_scores.append(float(conf))

    return {
        'stage1_score':      stage1_score,
        'stage1_passed':     1,
        'trash_can_boxes':   trash_can_boxes,
        'garbage_boxes':     garbage_boxes,
        'allowed_confs':     allowed_confs,
        'not_allowed_confs': not_allowed_confs,
        'garbage_confs':     garbage_conf_scores,
    }


def predict(model, image_path):
    
    scores = predict_scores(model, image_path, garbage_conf_threshold=GARBAGE_CONFIDENCE_THRESHOLD)

    xgboost_model = model.get('xgboost_model')
    feature_names = model.get('xgboost_feature_names')
    
    if xgboost_model is None or feature_names is None:
        return 0
    
    stage1_passed = scores['stage1_score'] >= STAGE1_SCORE_THRESHOLD
    
    if not stage1_passed:
        trash_can_boxes = scores['trash_can_boxes']
        garbage_boxes = []
        allowed_confs = scores['allowed_confs']
        not_allowed_confs = scores['not_allowed_confs']
        garbage_confs = []
    else:
        trash_can_boxes = scores['trash_can_boxes']
        garbage_boxes = scores['garbage_boxes']
        allowed_confs = scores['allowed_confs']
        not_allowed_confs = scores['not_allowed_confs']
        garbage_confs = scores['garbage_confs']
    
    feature_vector = compute_xgboost_features(
        trash_can_boxes,
        garbage_boxes,
        allowed_confs,
        not_allowed_confs,
        garbage_confs,
        feature_names
    )
    
    xgb_pred = int(xgboost_model.predict(feature_vector)[0])
    return xgb_pred