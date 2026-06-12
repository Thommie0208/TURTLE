# -- coding: utf-8 --

import sys
import platform
import threading
import os
import atexit
import cv2
import numpy as np
from ctypes import *
from datetime import datetime


currentsystem = platform.system()
if currentsystem == 'Windows':
    sys.path.append(os.path.join(os.getenv('MVCAM_COMMON_RUNENV'), "Samples", "Python", "MvImport"))
else: # Assume the Raspberry Pi environment
    sys.path.append(os.path.join("/opt/MVS/Samples/aarch64/Python")) #This is also where ImageSave.py and GrabImage.py are located, the files adapted into this single file.

from MvImport.MvCameraControl_class import *

# Global flags
g_bExit = False
g_capture_request = False
g_captured_frame = None
g_capture_complete = threading.Event()
g_last_frame_info = None
g_last_image_data = None
_capture_lock = threading.Lock()
_sdk_initialized = False


def _finalize_sdk():
    global _sdk_initialized
    if _sdk_initialized:
        try:
            MvCamera.MV_CC_Finalize()
        except Exception:
            pass
        _sdk_initialized = False


atexit.register(_finalize_sdk)

# HB format list (from ImageSave.py)
HB_format_list = [
    PixelType_Gvsp_HB_Mono8,
    PixelType_Gvsp_HB_Mono10,
    PixelType_Gvsp_HB_Mono10_Packed,
    PixelType_Gvsp_HB_Mono12,
    PixelType_Gvsp_HB_Mono12_Packed,
    PixelType_Gvsp_HB_Mono16,
    PixelType_Gvsp_HB_BayerGR8,
    PixelType_Gvsp_HB_BayerRG8,
    PixelType_Gvsp_HB_BayerGB8,
    PixelType_Gvsp_HB_BayerBG8,
    PixelType_Gvsp_HB_BayerRBGG8,
    PixelType_Gvsp_HB_BayerGR10,
    PixelType_Gvsp_HB_BayerRG10,
    PixelType_Gvsp_HB_BayerGB10,
    PixelType_Gvsp_HB_BayerBG10,
    PixelType_Gvsp_HB_BayerGR12,
    PixelType_Gvsp_HB_BayerRG12,
    PixelType_Gvsp_HB_BayerGB12,
    PixelType_Gvsp_HB_BayerBG12,
    PixelType_Gvsp_HB_BayerGR10_Packed,
    PixelType_Gvsp_HB_BayerRG10_Packed,
    PixelType_Gvsp_HB_BayerGB10_Packed,
    PixelType_Gvsp_HB_BayerBG10_Packed,
    PixelType_Gvsp_HB_BayerGR12_Packed,
    PixelType_Gvsp_HB_BayerRG12_Packed,
    PixelType_Gvsp_HB_BayerGB12_Packed,
    PixelType_Gvsp_HB_BayerBG12_Packed,
    PixelType_Gvsp_HB_YUV422_Packed,
    PixelType_Gvsp_HB_YUV422_YUYV_Packed,
    PixelType_Gvsp_HB_RGB8_Packed,
    PixelType_Gvsp_HB_BGR8_Packed,
    PixelType_Gvsp_HB_RGBA8_Packed,
    PixelType_Gvsp_HB_BGRA8_Packed,
    PixelType_Gvsp_HB_RGB16_Packed,
    PixelType_Gvsp_HB_BGR16_Packed,
    PixelType_Gvsp_HB_RGBA16_Packed,
    PixelType_Gvsp_HB_BGRA16_Packed]

# Decoding Characters
def decoding_char(ctypes_char_array):
    byte_str = memoryview(ctypes_char_array).tobytes()
    
    null_index = byte_str.find(b'\x00')
    if null_index != -1:
        byte_str = byte_str[:null_index]
    
    for encoding in ['gbk', 'utf-8', 'latin-1']:
        try:
            return byte_str.decode(encoding)
        except UnicodeDecodeError:
            continue
    
    return byte_str.decode('latin-1', errors='replace')

def save_non_raw_image(save_type: int, frame_info: MV_FRAME_OUT, cam_instance: MvCamera, custom_filename: str | None = None) -> tuple[int, str | None]:
    """
    Save image in non-raw format (JPEG, BMP, TIFF, PNG)
    From ImageSave.py
    
    Args:
        save_type: 1-JPEG, 2-BMP, 3-TIFF, 4-PNG
        frame_info: MV_FRAME_OUT structure
        cam_instance: MvCamera instance
        custom_filename: Optional custom filename (without extension)
    
    Returns:
        Tuple (ret_code, saved_filename)
    """
    if save_type == 1:
        mv_image_type = MV_Image_Jpeg
        ext = "jpg"
    elif save_type == 2:
        mv_image_type = MV_Image_Bmp
        ext = "bmp"
    elif save_type == 3:
        mv_image_type = MV_Image_Tif
        ext = "tif"
    else:  # save_type == 4
        mv_image_type = MV_Image_Png
        ext = "png"
    
    # Generate filename
    if custom_filename:
        file_path = "%s.%s" % (custom_filename, ext)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = "Image_%s_w%d_h%d_fn%d.%s" % (
            timestamp,
            frame_info.stFrameInfo.nWidth, 
            frame_info.stFrameInfo.nHeight, 
            frame_info.stFrameInfo.nFrameNum,
            ext)
    
    c_file_path = file_path.encode('ascii')
    stSaveParam = MV_SAVE_IMAGE_TO_FILE_PARAM_EX()
    stSaveParam.enPixelType = frame_info.stFrameInfo.enPixelType
    stSaveParam.nWidth = frame_info.stFrameInfo.nWidth
    stSaveParam.nHeight = frame_info.stFrameInfo.nHeight
    stSaveParam.nDataLen = frame_info.stFrameInfo.nFrameLen
    stSaveParam.pData = frame_info.pBufAddr
    stSaveParam.enImageType = mv_image_type
    stSaveParam.pcImagePath = create_string_buffer(c_file_path)
    stSaveParam.iMethodValue = 1
    stSaveParam.nQuality = 95  # JPEG quality (50-99)
    
    mv_ret = cam_instance.MV_CC_SaveImageToFileEx(stSaveParam)
    return mv_ret, file_path

def save_raw(frame_info: MV_FRAME_OUT, cam_instance: MvCamera, custom_filename: str | None = None) -> tuple[int, str | None]:
    """
    Save raw image data (with HB decode if needed)
    From ImageSave.py
    
    Args:
        frame_info: MV_FRAME_OUT structure
        cam_instance: MvCamera instance
        custom_filename: Optional custom filename (without extension)
    
    Returns:
        Tuple (ret_code, saved_filename)
    """
    if frame_info.stFrameInfo.enPixelType in HB_format_list:
        # HB format - need to decode first
        stDecodeParam = MV_CC_HB_DECODE_PARAM()
        memset(byref(stDecodeParam), 0, sizeof(stDecodeParam))
        
        # Get payload size
        stParam = MVCC_INTVALUE()
        memset(byref(stParam), 0, sizeof(stParam))
        
        ret = cam_instance.MV_CC_GetIntValue("PayloadSize", stParam)
        if 0 != ret:
            print("Get PayloadSize fail! ret[0x%x]" % ret)
            return ret, None
            
        nPayloadSize = stParam.nCurValue
        stDecodeParam.pSrcBuf = frame_info.pBufAddr
        stDecodeParam.nSrcLen = frame_info.stFrameInfo.nFrameLen
        stDecodeParam.pDstBuf = (c_ubyte * nPayloadSize)()
        stDecodeParam.nDstBufSize = nPayloadSize
        
        ret = cam_instance.MV_CC_HBDecode(stDecodeParam)
        if ret != 0:
            print("HB Decode fail! ret[0x%x]" % ret)
            return ret, None
        else:
            if custom_filename:
                file_path = "%s.raw" % custom_filename
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_path = "Image_%s_w%d_h%d_fn%d.raw" % (
                    timestamp,
                    stDecodeParam.nWidth, 
                    stDecodeParam.nHeight,
                    frame_info.stFrameInfo.nFrameNum)
            
            try:
                file_open = open(file_path, 'wb+')
                img_save = (c_ubyte * stDecodeParam.nDstBufLen)()
                memmove(byref(img_save), stDecodeParam.pDstBuf, stDecodeParam.nDstBufLen)
                file_open.write(img_save)
                file_open.close()
                return 0, file_path
            except Exception as e:
                print("Save raw file failed: %s" % str(e))
                return MV_E_OPENFILE, None
    else:
        # Standard raw format
        if custom_filename:
            file_path = "%s.raw" % custom_filename
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = "Image_%s_w%d_h%d_fn%d.raw" % (
                timestamp,
                frame_info.stFrameInfo.nWidth, 
                frame_info.stFrameInfo.nHeight, 
                frame_info.stFrameInfo.nFrameNum)
        
        try:
            file_open = open(file_path, 'wb+')
            img_save = (c_ubyte * frame_info.stFrameInfo.nFrameLen)()
            memmove(byref(img_save), frame_info.pBufAddr, frame_info.stFrameInfo.nFrameLen)
            file_open.write(img_save)
            file_open.close()
            return 0, file_path
        except Exception as e:
            print("Save raw file failed: %s" % str(e))
            return MV_E_OPENFILE, None

def convert_to_opencv(frame_info: MV_FRAME_OUT) -> np.ndarray | None:
    """
    Convert MVS frame to OpenCV format for display
    
    Args:
        frame_info: MV_FRAME_OUT structure
    
    Returns:
        OpenCV image or None
    """
    try:
        if None == frame_info.pBufAddr:
            return None
        
        width = frame_info.stFrameInfo.nWidth
        height = frame_info.stFrameInfo.nHeight
        pixel_type = frame_info.stFrameInfo.enPixelType
        data_size = frame_info.stFrameInfo.nFrameLen
        
        # Copy image data
        image_data = string_at(frame_info.pBufAddr, data_size)
        
        # Handle different pixel formats
        if pixel_type == PixelType_Gvsp_Mono8:
            img_array = np.frombuffer(image_data, dtype=np.uint8)
            img = img_array.reshape((height, width))
            return img
            
        elif pixel_type == PixelType_Gvsp_RGB8_Packed:
            img_array = np.frombuffer(image_data, dtype=np.uint8)
            img = img_array.reshape((height, width, 3))
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            return img
            
        elif pixel_type == PixelType_Gvsp_BGR8_Packed:
            img_array = np.frombuffer(image_data, dtype=np.uint8)
            img = img_array.reshape((height, width, 3))
            return img
            
        elif pixel_type in [PixelType_Gvsp_BayerGR8, PixelType_Gvsp_BayerRG8, 
                            PixelType_Gvsp_BayerGB8, PixelType_Gvsp_BayerBG8]:
            img_array = np.frombuffer(image_data, dtype=np.uint8)
            bayer_img = img_array.reshape((height, width))
            img = cv2.cvtColor(bayer_img, cv2.COLOR_BAYER_BG2BGR)
            return img
            
        else:
            # For other formats, just return raw data info
            return None
            
    except Exception as e:
        print("Convert error: %s" % str(e))
        return None

def work_thread(cam=0, pData=0, nDataSize=0):
    """
    Continuous grabbing thread with on-demand capture support
    """
    global g_bExit, g_capture_request, g_captured_frame, g_capture_complete
    global g_last_frame_info, g_last_image_data
    
    stOutFrame = MV_FRAME_OUT()  
    memset(byref(stOutFrame), 0, sizeof(stOutFrame))
    
    frame_count = 0
    
    while not g_bExit:
        ret = cam.MV_CC_GetImageBuffer(stOutFrame, 100)
        
        if None != stOutFrame.pBufAddr and 0 == ret:
            frame_count += 1
            
            # Store last frame data for potential saving
            g_last_frame_info = stOutFrame
            g_last_image_data = stOutFrame.pBufAddr
            
            # Print frame info periodically (every 30 frames to reduce output)
            if frame_count % 30 == 0:
                print("Frame %d: Width[%d], Height[%d]" % (
                    frame_count,
                    stOutFrame.stFrameInfo.nWidth, 
                    stOutFrame.stFrameInfo.nHeight))
            
            # Check if there's a capture request
            if g_capture_request:
                print("\n>>> Capturing image on demand...")
                # Store a copy of the frame data
                data_size = stOutFrame.stFrameInfo.nFrameLen
                g_captured_frame = MV_FRAME_OUT()
                memset(byref(g_captured_frame), 0, sizeof(g_captured_frame))
                
                # Copy frame info
                g_captured_frame.stFrameInfo = stOutFrame.stFrameInfo
                
                # Copy image data
                g_captured_frame.pBufAddr = create_string_buffer(data_size)
                memmove(g_captured_frame.pBufAddr, stOutFrame.pBufAddr, data_size)
                
                g_capture_request = False
                g_capture_complete.set()
            
            # Free the buffer
            cam.MV_CC_FreeImageBuffer(stOutFrame)
        # else:
        #     # No data, just continue
        #     pass

def capture_and_save(cam: MvCamera, save_type: int, custom_filename: str | None = None, timeout_ms: int = 2000) -> tuple[bool, str | None]:
    """
    Capture a single frame and save it
    
    Args:
        cam: MvCamera instance
        save_type: 0-raw, 1-JPEG, 2-BMP, 3-TIFF, 4-PNG
        custom_filename: Optional custom filename (without extension)
        timeout_ms: Timeout in milliseconds
    
    Returns:
        Tuple (success, saved_filename)
    """
    try:
        stOutFrame = MV_FRAME_OUT()
        memset(byref(stOutFrame), 0, sizeof(stOutFrame))
        
        # Capture one frame
        ret = cam.MV_CC_GetImageBuffer(stOutFrame, timeout_ms)
        
        if ret != 0 or None == stOutFrame.pBufAddr:
            print("Failed to capture frame, error: 0x%x" % ret)
            return False, None
        
        print("Captured: Width[%d], Height[%d], FrameNum[%d]" % (
            stOutFrame.stFrameInfo.nWidth,
            stOutFrame.stFrameInfo.nHeight,
            stOutFrame.stFrameInfo.nFrameNum))
        
        # Save based on type
        if save_type == 0:
            ret_code, saved_path = save_raw(stOutFrame, cam, custom_filename)
        else:
            ret_code, saved_path = save_non_raw_image(save_type, stOutFrame, cam, custom_filename)
        
        # Free buffer
        cam.MV_CC_FreeImageBuffer(stOutFrame)
        
        if ret_code == 0:
            print("Save successful: %s" % saved_path)
            return True, saved_path
        else:
            print("Save failed with error: 0x%x" % ret_code)
            return False, None
            
    except Exception as e:
        print("Capture error: %s" % str(e))
        return False, None

def capture_single_image(save_type: int = 1, filename: str | None = None, camera_index: int = 0, timeout_ms: int = 2000) -> bool:
    """
    Simplified function to capture a single image (connect, capture, disconnect)
    
    Args:
        save_type: 0-raw, 1-JPEG, 2-BMP, 3-TIFF, 4-PNG
        filename: Output filename (without extension, auto-generated if None)
        camera_index: Index of camera to use
        timeout_ms: Timeout in milliseconds
    
    Returns:
        True if successful, False otherwise
    """
    if type(filename) == str and len(filename) == 0:
        filename = None  # Ensure empty string is treated as None
        
    global _sdk_initialized

    if not _sdk_initialized:
        try:
            MvCamera.MV_CC_Initialize()
            _sdk_initialized = True
        except Exception as e:
            print("Failed to initialize camera SDK: %s" % str(e))
            return False

    cam = None
    with _capture_lock:
        try:
            deviceList = MV_CC_DEVICE_INFO_LIST()
            tlayerType = MV_GIGE_DEVICE | MV_USB_DEVICE

            ret = MvCamera.MV_CC_EnumDevices(tlayerType, deviceList)
            if ret != 0 or deviceList.nDeviceNum == 0:
                print("No devices found!")
                return False

            if camera_index >= deviceList.nDeviceNum:
                print("Camera index out of range!")
                return False

            cam = MvCamera()
            stDeviceList = cast(deviceList.pDeviceInfo[camera_index], POINTER(MV_CC_DEVICE_INFO)).contents
            ret = cam.MV_CC_CreateHandle(stDeviceList)
            if ret != 0:
                print("Failed to create handle!")
                return False

            ret = cam.MV_CC_OpenDevice(MV_ACCESS_Exclusive, 0)
            if ret != 0:
                print("Failed to open device!")
                return False

            if stDeviceList.nTLayerType == MV_GIGE_DEVICE:
                nPacketSize = cam.MV_CC_GetOptimalPacketSize()
                if int(nPacketSize) > 0:
                    cam.MV_CC_SetIntValue("GevSCPSPacketSize", nPacketSize)

            ret = cam.MV_CC_SetEnumValue("TriggerMode", MV_TRIGGER_MODE_OFF)
            if ret != 0:
                print("Failed to set trigger mode!")
                return False

            ret = cam.MV_CC_StartGrabbing()
            if ret != 0:
                print("Failed to start grabbing!")
                return False

            import time
            time.sleep(0.05)

            success, _ = capture_and_save(cam, save_type, filename, timeout_ms)
            return success

        except Exception as e:
            print("Error: %s" % str(e))
            return False

        finally:
            if cam:
                try:
                    cam.MV_CC_StopGrabbing()
                    cam.MV_CC_CloseDevice()
                    cam.MV_CC_DestroyHandle()
                except Exception:
                    pass

if __name__ == "__main__":
    # Check for command line arguments (single capture mode)
    if len(sys.argv) > 1 and sys.argv[1] in ['--capture', '-c']:
        # Parse arguments for single capture
        save_type = 1  # Default JPEG
        filename = None
        camera_idx = 0
        
        i = 2
        while i < len(sys.argv):
            if sys.argv[i] == '--type' and i+1 < len(sys.argv):
                save_type = int(sys.argv[i+1])
                i += 2
            elif sys.argv[i] == '--output' and i+1 < len(sys.argv):
                filename = sys.argv[i+1]
                i += 2
            elif sys.argv[i] == '--index' and i+1 < len(sys.argv):
                camera_idx = int(sys.argv[i+1])
                i += 2
            else:
                i += 1
        
        # Map save type to name
        type_names = {0: 'RAW', 1: 'JPEG', 2: 'BMP', 3: 'TIFF', 4: 'PNG'}
        print("Capturing %s image..." % type_names.get(save_type, 'Unknown'))
        
        if capture_single_image(save_type, filename, camera_idx):
            print("Image captured successfully!")
            sys.exit(0)
        else:
            print("Failed to capture image!")
            sys.exit(1)
    
    # Interactive mode (original GrabImage.py behavior with saving)
    try:
        # initialize SDK
        MvCamera.MV_CC_Initialize()

        SDKVersion = MvCamera.MV_CC_GetSDKVersion()
        print("SDKVersion[0x%x]" % SDKVersion)

        deviceList = MV_CC_DEVICE_INFO_LIST()
        tlayerType = MV_GIGE_DEVICE | MV_USB_DEVICE
        
        # Enum device
        ret = MvCamera.MV_CC_EnumDevices(tlayerType, deviceList)
        if ret != 0:
            print("enum devices fail! ret[0x%x]" % ret)
            sys.exit()

        if deviceList.nDeviceNum == 0:
            print("find no device!")
            sys.exit()

        print("Find %d devices!" % deviceList.nDeviceNum)

        for i in range(0, deviceList.nDeviceNum):
            mvcc_dev_info = cast(deviceList.pDeviceInfo[i], POINTER(MV_CC_DEVICE_INFO)).contents
            if mvcc_dev_info.nTLayerType == MV_GIGE_DEVICE:
                print("\ngige device: [%d]" % i)
                strModeName = decoding_char(mvcc_dev_info.SpecialInfo.stGigEInfo.chModelName)
                print("device model name: %s" % strModeName)

                nip1 = ((mvcc_dev_info.SpecialInfo.stGigEInfo.nCurrentIp & 0xff000000) >> 24)
                nip2 = ((mvcc_dev_info.SpecialInfo.stGigEInfo.nCurrentIp & 0x00ff0000) >> 16)
                nip3 = ((mvcc_dev_info.SpecialInfo.stGigEInfo.nCurrentIp & 0x0000ff00) >> 8)
                nip4 = (mvcc_dev_info.SpecialInfo.stGigEInfo.nCurrentIp & 0x000000ff)
                print("current ip: %d.%d.%d.%d\n" % (nip1, nip2, nip3, nip4))
            elif mvcc_dev_info.nTLayerType == MV_USB_DEVICE:
                print("\nu3v device: [%d]" % i)
                strModeName = decoding_char(mvcc_dev_info.SpecialInfo.stUsb3VInfo.chModelName)
                print("device model name: %s" % strModeName)

                strSerialNumber = decoding_char(mvcc_dev_info.SpecialInfo.stUsb3VInfo.chSerialNumber)                
                print("user serial number: %s" % strSerialNumber)

        nConnectionNum = input("please input the number of the device to connect: ")

        if int(nConnectionNum) >= deviceList.nDeviceNum:
            print("input error!")
            sys.exit()

        # Select save format
        print("\nSave format options:")
        print("  0 - RAW")
        print("  1 - JPEG")
        print("  2 - BMP")
        print("  3 - TIFF")
        print("  4 - PNG")
        nSaveImageType = input("please input number (0-4): ")
        if int(nSaveImageType) not in {0, 1, 2, 3, 4}:
            print("input error!")
            sys.exit()

        # Create Camera Object
        cam = MvCamera()
        
        # Select device and create handle
        stDeviceList = cast(deviceList.pDeviceInfo[int(nConnectionNum)], POINTER(MV_CC_DEVICE_INFO)).contents

        ret = cam.MV_CC_CreateHandle(stDeviceList)
        if ret != 0:
            raise Exception("create handle fail! ret[0x%x]" % ret)

        # Open device
        ret = cam.MV_CC_OpenDevice(MV_ACCESS_Exclusive, 0)
        if ret != 0:
            raise Exception("open device fail! ret[0x%x]" % ret)
        
        # Detection network optimal package size(It only works for the GigE camera)
        if stDeviceList.nTLayerType == MV_GIGE_DEVICE:
            nPacketSize = cam.MV_CC_GetOptimalPacketSize()
            if int(nPacketSize) > 0:
                ret = cam.MV_CC_SetIntValue("GevSCPSPacketSize", nPacketSize)
                if ret != 0:
                    print("Warning: Set Packet Size fail! ret[0x%x]" % ret)
            else:
                print("Warning: Get Packet Size fail! ret[0x%x]" % nPacketSize)

        # Set trigger mode as off
        ret = cam.MV_CC_SetEnumValue("TriggerMode", MV_TRIGGER_MODE_OFF)
        if ret != 0:
            raise Exception("set trigger mode fail! ret[0x%x]" % ret)

        # Start grabbing image
        ret = cam.MV_CC_StartGrabbing()
        if ret != 0:
            raise Exception("start grabbing fail! ret[0x%x]" % ret)

        # Start continuous grabbing thread
        try:
            hThreadHandle = threading.Thread(target=work_thread, args=(cam, None, None))
            hThreadHandle.daemon = True
            hThreadHandle.start()
        except:
            print("error: unable to start thread")
            
        print("\n" + "="*50)
        print("Camera is running. Commands:")
        print("  'c' + Enter - Capture and save image")
        print("  'q' + Enter - Quit")
        print("="*50)
        
        capture_count = 0
        
        while True:
            user_input = input("\nCommand (c/q): ").lower()
            
            if user_input == 'c':
                capture_count += 1
                print("\nCapturing image #%d..." % capture_count)
                
                # Capture and save using the existing functions
                stOutFrame = MV_FRAME_OUT()
                memset(byref(stOutFrame), 0, sizeof(stOutFrame))
                
                ret = cam.MV_CC_GetImageBuffer(stOutFrame, 2000)
                
                if None != stOutFrame.pBufAddr and 0 == ret:
                    print("Frame captured: Width[%d], Height[%d], FrameNum[%d]" % (
                        stOutFrame.stFrameInfo.nWidth, 
                        stOutFrame.stFrameInfo.nHeight, 
                        stOutFrame.stFrameInfo.nFrameNum))
                    
                    # Save based on selected format
                    if int(nSaveImageType) == 0:
                        ret_code, saved_path = save_raw(stOutFrame, cam)
                    else:
                        ret_code, saved_path = save_non_raw_image(int(nSaveImageType), stOutFrame, cam)
                    
                    if ret_code == 0:
                        print("Image saved: %s" % saved_path)
                    else:
                        print("Failed to save image! Error: 0x%x" % ret_code)
                    
                    cam.MV_CC_FreeImageBuffer(stOutFrame)
                else:
                    print("Failed to capture frame! Error: 0x%x" % ret)
                    
            elif user_input == 'q':
                print("\nStopping...")
                break
            else:
                print("Unknown command. Use 'c' to capture, 'q' to quit.")

        g_bExit = True
        hThreadHandle.join(timeout=1)

        # Stop grabbing image
        ret = cam.MV_CC_StopGrabbing()
        if ret != 0:
            raise Exception("stop grabbing fail! ret[0x%x]" % ret)

        # Close device
        ret = cam.MV_CC_CloseDevice()
        if ret != 0:
            raise Exception("close deivce fail! ret[0x%x]" % ret)

        # Destroy handle
        cam.MV_CC_DestroyHandle()

    except Exception as e:
        print(e)
        try:
            cam.MV_CC_CloseDevice()
            cam.MV_CC_DestroyHandle()
        except:
            pass
    finally:
        # ch:反初始化SDK | en: finalize SDK
        MvCamera.MV_CC_Finalize()
        print("\nDone!")