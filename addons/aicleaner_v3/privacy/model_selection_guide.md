# Privacy Pipeline Model Selection Guide

This document provides detailed recommendations for ONNX models used in the AICleaner v3 Privacy Pipeline, optimized for AMD 780M iGPU performance.

## Model Categories by Privacy Level

### Speed Level (Performance Priority)
**Target: <2 seconds processing time**

#### Face Detection
- **Model**: YuNet
- **Source**: OpenCV Zoo - https://github.com/opencv/opencv_zoo/tree/master/models/face_detection_yunet
- **ONNX File**: `yunet_2023mar.onnx`
- **Input Size**: 320x240 or 640x480
- **Performance**: ~15ms on AMD 780M
- **Accuracy**: Good for frontal faces, struggles with profile views
- **Use Case**: Quick privacy screening

#### Object Detection  
- **Model**: YOLOv8n (Nano)
- **Source**: Ultralytics - https://github.com/ultralytics/ultralytics
- **ONNX File**: `yolov8n.onnx`
- **Input Size**: 640x640
- **Performance**: ~50ms on AMD 780M
- **Classes**: Filter for laptop, cell phone, tv, book
- **Use Case**: Basic screen/document detection

#### Text Detection
- **Model**: PaddleOCR Light
- **Source**: PaddlePaddle - https://github.com/PaddlePaddle/PaddleOCR
- **ONNX File**: `en_PP-OCRv3_det_infer.onnx` (lightweight version)
- **Input Size**: Variable (max 960x960)
- **Performance**: ~100ms on AMD 780M
- **Use Case**: Basic text region detection

### Balanced Level (Recommended Default)
**Target: 3-5 seconds processing time**

#### Face Detection
- **Model**: RetinaFace ResNet-50
- **Source**: InsightFace - https://github.com/deepinsight/insightface/tree/master/detection/retinaface
- **ONNX File**: `retinaface_r50_v1.onnx`
- **Input Size**: 640x640
- **Performance**: ~80ms on AMD 780M
- **Accuracy**: Excellent for various angles and lighting
- **Features**: Face landmarks, better profile detection

#### Object Detection
- **Primary Model**: YOLOv8m (Medium)
- **Source**: Ultralytics
- **ONNX File**: `yolov8m.onnx` 
- **Input Size**: 640x640
- **Performance**: ~150ms on AMD 780M
- **Classes**: laptop, cell phone, tv, book, person

- **Secondary Model**: License Plate Detection
- **Model**: YOLOv8 Fine-tuned
- **Source**: Custom training on OpenALPR dataset
- **ONNX File**: `yolov8_license_plates.onnx`
- **Input Size**: 640x640
- **Performance**: ~100ms on AMD 780M
- **Dataset**: Train on EU/US license plate dataset

#### Text Detection + OCR
- **Text Detection**: PaddleOCR Standard
- **ONNX File**: `en_PP-OCRv4_det_infer.onnx`
- **Input Size**: 960x960
- **Performance**: ~200ms on AMD 780M

- **Text Recognition**: PaddleOCR Recognition
- **ONNX File**: `en_PP-OCRv4_rec_infer.onnx`
- **Use Case**: Extract text for PII analysis

#### PII Detection
- **Model**: spaCy Transformer (en_core_web_trf)
- **Format**: Custom ONNX export
- **Performance**: ~50ms per text region
- **Entities**: PERSON, GPE, DATE, MONEY, EMAIL, PHONE

### Paranoid Level (Maximum Privacy)
**Target: <8 seconds processing time**

#### Face Detection
- **Model**: SCRFD (Sample and Computation Redistribution for Face Detection)
- **Source**: InsightFace - https://github.com/deepinsight/insightface/tree/master/detection/scrfd
- **ONNX File**: `scrfd_2.5g_bnkps.onnx`
- **Input Size**: 640x640
- **Performance**: ~120ms on AMD 780M
- **Accuracy**: State-of-the-art face detection
- **Features**: Handles difficult poses, occlusion, small faces

#### Object Detection
- **Primary Model**: YOLOv8l (Large)
- **ONNX File**: `yolov8l.onnx`
- **Input Size**: 1280x1280
- **Performance**: ~400ms on AMD 780M
- **Accuracy**: Highest detection accuracy

- **Specialized Models**:
  - **License Plates**: High-accuracy fine-tuned model
  - **Documents**: Custom model for papers, IDs, cards
  - **Screens**: Specialized for monitors, phones, tablets

#### Advanced Text Processing
- **Text Detection**: PaddleOCR Server
- **ONNX File**: `en_PP-OCRv4_det_server_infer.onnx`
- **Performance**: ~300ms on AMD 780M
- **Features**: Multi-oriented text, small text detection

- **Advanced PII**: Custom NER model
- **Model**: BERT-based NER trained on privacy dataset
- **Entities**: Extended PII including SSN patterns, addresses, etc.

## Model Sources and Download Instructions

### 1. OpenCV Zoo Models
```bash
# YuNet Face Detection
wget https://github.com/opencv/opencv_zoo/raw/master/models/face_detection_yunet/face_detection_yunet_2023mar.onnx
```

### 2. Ultralytics YOLOv8 Models
```python
from ultralytics import YOLO

# Export YOLOv8 models to ONNX
models = ['yolov8n.pt', 'yolov8m.pt', 'yolov8l.pt']
for model in models:
    yolo = YOLO(model)
    yolo.export(format='onnx', simplify=True)
```

### 3. PaddleOCR Models
```bash
# Download PaddleOCR ONNX models
wget https://paddleocr.bj.bcebos.com/PP-OCRv4/english/en_PP-OCRv4_det_infer.tar
wget https://paddleocr.bj.bcebos.com/PP-OCRv4/english/en_PP-OCRv4_rec_infer.tar

# Convert to ONNX using paddle2onnx
paddle2onnx --model_dir ./en_PP-OCRv4_det_infer --model_filename inference.pdmodel --params_filename inference.pdiparams --opset_version 16 --save_file en_PP-OCRv4_det_infer.onnx
```

### 4. InsightFace Models
```bash
# RetinaFace
wget https://github.com/deepinsight/insightface/releases/download/v0.7/retinaface_r50_v1.onnx

# SCRFD
wget https://github.com/deepinsight/insightface/releases/download/v0.7/scrfd_2.5g_bnkps.onnx
```

### 5. Custom License Plate Detection
Training dataset recommendations:
- **OpenALPR**: https://github.com/openalpr/openalpr
- **CCPD**: Chinese City Parking Dataset (adapt for other regions)
- **Custom Collection**: Use data augmentation tools

```python
# Fine-tune YOLOv8 for license plates
from ultralytics import YOLO

model = YOLO('yolov8m.pt')
model.train(
    data='license_plate_dataset.yaml',
    epochs=100,
    imgsz=640,
    batch=16
)
model.export(format='onnx')
```

## Performance Optimization Tips

### 1. Model Quantization
```python
# Convert FP32 models to FP16 for AMD iGPU
import onnxruntime as ort
from onnxruntime.quantization import quantize_dynamic, QuantType

quantize_dynamic(
    model_input='model_fp32.onnx',
    model_output='model_fp16.onnx', 
    weight_type=QuantType.QUInt8
)
```

### 2. Input Resolution Optimization
- Speed Level: 320x240 - 640x640
- Balanced Level: 640x640 - 960x960  
- Paranoid Level: 960x960 - 1280x1280

### 3. Batch Processing
- Process multiple detected regions in single inference
- Group similar-sized detections together
- Use dynamic batching when possible

## Integration with Model Manager

The Model Manager will automatically select appropriate models based on privacy level:

```python
# Model selection logic
model_configs = {
    PrivacyLevel.SPEED: {
        'face_detection': 'yunet_2023mar.onnx',
        'object_detection': 'yolov8n.onnx', 
        'text_detection': 'en_PP-OCRv3_det_infer.onnx'
    },
    PrivacyLevel.BALANCED: {
        'face_detection': 'retinaface_r50_v1.onnx',
        'object_detection': 'yolov8m.onnx',
        'text_detection': 'en_PP-OCRv4_det_infer.onnx',
        'license_plate_detection': 'yolov8_license_plates.onnx'
    },
    PrivacyLevel.PARANOID: {
        'face_detection': 'scrfd_2.5g_bnkps.onnx',
        'object_detection': 'yolov8l.onnx',
        'text_detection': 'en_PP-OCRv4_det_server_infer.onnx',
        'license_plate_detection': 'yolov8_license_plates_high_acc.onnx'
    }
}
```

## Hardware-Specific Optimizations for AMD 780M

### 1. Memory Management
- Keep models under 2GB total
- Use FP16 precision when possible
- Enable memory pooling in ONNX Runtime

### 2. Execution Providers
- Primary: ROCMExecutionProvider
- Fallback: CPUExecutionProvider
- Alternative: DirectMLExecutionProvider (Windows)

### 3. Threading Configuration
- Inter-op threads: 4 (half of 8845HS cores)
- Intra-op threads: 8 (leverage SMT)
- Use GPU for inference, CPU for pre/post-processing

This model selection provides a solid foundation for the privacy pipeline while maintaining the target performance requirements for each privacy level.