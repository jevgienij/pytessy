#!/usr/bin/python3
"""
        _                 _
       (_)               | |
 _ __   _  __  __   ___  | |
| '__| | | \ \/ /  / _ \ | |
| |    | |  >  <  |  __/ | |
|_|    |_| /_/\_\  \___| |_|



PyTessy
=======

Tesseract-OCR, faster!

This module allows faster access to Tesseract-OCR from Python scripts.

This module is always faster than common Tesseract-OCR wrappers like pytesseract
because it uses direct access to Tesseract-OCR's core library instead of calling
its executable.

The specification of the connection to the driver is based on the source code
from here: https://github.com/UB-Mannheim/tesseract/blob/master/src/api/capi.cpp

Copyright rixel 2020
Distributed under the Boost Software License, Version 1.0.
See accompanying file LICENSE or a copy at https://www.boost.org/LICENSE_1_0.txt
"""


import ctypes
import ctypes.util
from os import chdir, environ, getcwd
from os.path import abspath, dirname, isabs, isdir, isfile, join
from sys import platform
from distutils.spawn import find_executable
import numpy as np


class PyTessyError(Exception):
    """
    PyTessyError class
    ------------------
    Empty subclass of Exception to throw module-specific errors.
    """

    pass


class TesseractHandler(object):
    """
    TesseractHandler class
    ----------------------
    Handles raw Tesseract-OCR calls with limited functionality only.
    """

    _lib = None
    _api = None

    class TessBaseAPI(ctypes._Pointer):
        """
        TessBaseAPI
        -----------
        Empty ctypes._Pointer subclass to serve as TessBaseAPI handler pointer.
        """

        _type_ = type('_TessBaseAPI', (ctypes.Structure,), {})

    def __init__(self, lib_path=None,  data_path=None, language='eng'):
        """
        Initializes Tesseract-OCR api handler object instance
        -----------------------------------------------------
        @Params: lib_path   (string)    [optional] Path to Tesseract-OCR library.
                 data_path  (string)    [optional] Path to Tesseract-OCR data files.
                 language   (string)    [optional] Language code to work with.
        """

        if self._lib is None:
            self.setup_lib(lib_path)
        self._api = self._lib.TessBaseAPICreate()
        if self._lib.TessBaseAPIInit3(self._api, data_path.encode('ascii'),
                                      language.encode('ascii')):
            raise PyTessyError('Failed to initialize Tesseract-OCR library.')

    def get_text(self):
        """
        Gets text as utf-8 decoded string
        ---------------------------------
        @Return: (string)   Text read by Tesseract-OCR as utf-8 string.
        """

        self._check_setup()
        result = self._lib.TessBaseAPIGetUTF8Text(self._api)
        if result:
            return result.decode('utf-8')

    def get_text_raw(self):
        """
        Gets text as raw bytes data
        ---------------------------
        @Return: (bytes)    Text read by Tesseract-OCR as raw bytes.
        """

        self._check_setup()
        return self._lib.TessBaseAPIGetUTF8Text(self._api)

    def set_image(self, imagedata, width, height, bytes_per_pixel, bytes_per_line,
                  resolution):
        """
        Sets image to read
        ------------------
        @Params: imagedata          (ctypes.int array)  Raw imagedata to read.
                 width              (int)               Width of the image.
                 height             (int)               Height of the image.
                 bytes_per_pixel    (int)               Number of bytes that
                                                        represents a pixel.
                 bytes_per_line     (int)               Number of bytes in a line.
                 resolution         (int)               Resolution of the image
                                                        in dpi.
        """

        self._check_setup()
        self._lib.TessBaseAPISetImage(self._api,
                                      imagedata, width, height,
                                      bytes_per_pixel, bytes_per_line)
        self._lib.TessBaseAPISetSourceResolution(self._api, resolution)

    def set_psm(self, psm):
        """
        Sets Page Segmentation Mode, as per TessPageSegMode enum:
        ------------------
        @Params: psm (int) Page Segmentation Mode, as per TessPageSegMode enum:

        typedef enum TessPageSegMode {
          PSM_OSD_ONLY,
          PSM_AUTO_OSD,
          PSM_AUTO_ONLY,
          PSM_AUTO,
          PSM_SINGLE_COLUMN,
          PSM_SINGLE_BLOCK_VERT_TEXT,
          PSM_SINGLE_BLOCK,
          PSM_SINGLE_LINE,
          PSM_SINGLE_WORD,
          PSM_CIRCLE_WORD,
          PSM_SINGLE_CHAR,
          PSM_SPARSE_TEXT,
          PSM_SPARSE_TEXT_OSD,
          PSM_RAW_LINE,
          PSM_COUNT
        } TessPageSegMode;
        https://github.com/UB-Mannheim/tesseract/blob/master/include/tesseract/capi.h
        """

        self._check_setup()
        self._lib.TessBaseAPISetPageSegMode(self._api, psm)

    def get_psm(self):
        """
        Gets Page Segmentation Mode, as per TessPageSegMode enum:
        ------------------
        @Return: psm (int) Page Segmentation Mode, as per TessPageSegMode enum:

        typedef enum TessPageSegMode {
          PSM_OSD_ONLY,
          PSM_AUTO_OSD,
          PSM_AUTO_ONLY,
          PSM_AUTO,
          PSM_SINGLE_COLUMN,
          PSM_SINGLE_BLOCK_VERT_TEXT,
          PSM_SINGLE_BLOCK,
          PSM_SINGLE_LINE,
          PSM_SINGLE_WORD,
          PSM_CIRCLE_WORD,
          PSM_SINGLE_CHAR,
          PSM_SPARSE_TEXT,
          PSM_SPARSE_TEXT_OSD,
          PSM_RAW_LINE,
          PSM_COUNT
        } TessPageSegMode;
        https://github.com/UB-Mannheim/tesseract/blob/master/include/tesseract/capi.h
        """

        self._check_setup()
        return self._lib.TessBaseAPIGetPageSegMode(self._api)

    def set_variable(self, key, val):
        """
        Set the value of an internal parameter.
        Supply the name of the parameter and the value as a string, just as
        you would in a config file.
        Eg set_variable("tessedit_char_blacklist", "xyz"); to ignore x, y and z.
        Or set_variable("classify_bln_numeric_mode", "1"); to set numeric-only mode.
        SetVariable may be used before Init, but settings will revert to
        defaults on End().
        @Params: key (str) Variable name
                 val (str) Variable value
        @Return: (bool) ``False`` if the name lookup failed.
        """

        self._check_setup()
        return self._lib.TessBaseAPISetVariable(self._api, key.encode('ascii'), val.encode('ascii'))

    def mean_text_conf(self):
        """
        @Return: (int) average confidence value between 0 and 100.
        """
        self._check_setup()
        return self._lib.TessBaseAPIMeanTextConf(self._api)

    @classmethod
    def setup_lib(cls, lib_path=None):
        """
        Binds Tesseract-OCR library to the handler
        ------------------------------------------
        @Params: (string)       [optional] Path to Tesseract-OCR library.
        @Raises: PyTessyError   If ctypes cannot find Tesseract-OCR library.
        """

        if cls._lib is not None:
            return
        lib_path = ctypes.util.find_library(lib_path)
        if lib_path is None:
            raise PyTessyError('Ctypes couldn\'t find Tesseract-OCR library')
        cls._lib = lib = ctypes.CDLL(lib_path)

        lib.TessBaseAPICreate.restype = cls.TessBaseAPI         # handle

        lib.TessBaseAPIDelete.restype = None                    # void
        lib.TessBaseAPIDelete.argtypes = (cls.TessBaseAPI,)     # handle

        lib.TessBaseAPIInit3.argtypes = (cls.TessBaseAPI,       # handle
                                         ctypes.c_char_p,       # datapath
                                         ctypes.c_char_p)       # language

        lib.TessBaseAPISetImage.restype = None                  # void
        lib.TessBaseAPISetImage.argtypes = (cls.TessBaseAPI,    # handle
                                            ctypes.c_void_p,    # imagedata
                                            ctypes.c_int,       # width
                                            ctypes.c_int,       # height
                                            ctypes.c_int,       # bytes_per_pixel
                                            ctypes.c_int)       # bytes_per_line

        lib.TessBaseAPIGetUTF8Text.restype = ctypes.c_char_p        # text
        lib.TessBaseAPIGetUTF8Text.argtypes = (cls.TessBaseAPI, )   # handle

        lib.TessBaseAPISetSourceResolution.restype = None               # void
        lib.TessBaseAPISetSourceResolution.argtypes = (cls.TessBaseAPI, # handle
                                                       ctypes.c_int)    # ppi

        lib.TessBaseAPISetPageSegMode.restype = None
        lib.TessBaseAPISetPageSegMode.argtypes = (cls.TessBaseAPI,  # handle
                                                  ctypes.c_int)     # mode

        lib.TessBaseAPIGetPageSegMode.restype = ctypes.c_int         # mode
        lib.TessBaseAPIGetPageSegMode.argtypes = (cls.TessBaseAPI,)  # handle

        lib.TessBaseAPISetVariable.restype = ctypes.c_bool       # bool
        lib.TessBaseAPISetVariable.argtypes = (cls.TessBaseAPI,  # handle
                                               ctypes.c_char_p,  # name
                                               ctypes.c_char_p)  # value

        lib.TessBaseAPIMeanTextConf.restype = ctypes.c_int         # int
        lib.TessBaseAPIMeanTextConf.argtypes = (cls.TessBaseAPI,)  # handle

    def _check_setup(self):
        """
        Checks whether Tesseract-OCR is set up or not
        ---------------------------------------------
        @Raises: PyTessyError       If library handler not yet configured.
                 PyTessyError       If api handler not yet configured.
        """

        if not self._lib:
            raise PyTessyError('Tesseract handler library not configured.')
        if not self._api:
            raise PyTessyError('Tesseract handler api not created.')

    def __del__(self):
        """
        Disconnects TessBaseAPI when instance is deleted
        ------------------------------------------------
        """

        if not self._lib or not self._api:
            return
        if not getattr(self, 'closed', False):
            self._lib.TessBaseAPIDelete(self._api)
            self.closed = True


class PyTessy(object):
    """
    PyTessy
    -------
    Provides user-friendly and fast Tesseract-OCR interface.
    """

    DEFAULT_HORIZONTAL_DPI = 96
    TESSDATA_DIRNAME = 'tessdata'
    TESSERACT_DIRNAME = 'Tesseract-OCR'
    TESSERACT_DEFAULT_HORIZONTAL_DPI = 70
    VERSION = '0.0.1'

    def __init__(self, tesseract_path=None, api_version=None, lib_path=None,
                 data_path=None, language='eng', verbose_search=False):
        """
        Initializes PyTessy instance
        ----------------------------
        @Params: tesseract_path (string)    [optional] Path (directory's name)
                                            to Tesseract-OCR library.
                 api_version    (string)    [optional] Api version suffix string
                                            (should be compatible with
                                            Tesseract-OCR 3).
                 lib_path       (string)    [optional] Exact path to the
                                            Tesseract-OCR library.
                                            to data directory (usually "tessdata").
                 data_path      (string)    [optional] Path (directory's name)
                                            to data directory (usually "tessdata").
                 language       (string)    [optional] Language code to use.
                 verbose_search (boolean)   [optional] Whether to display
                                            library searching process or not.
        @Raises: NotImplementedError        If the operating system is not
                                            implemented yet (linux, macOS).
                                            You can avoid this error by giving
                                            exact path of Tesseract-OCR library.
                 NotImplementedError        If the operating system will be
                                            never implemented.
                                            You can avoid this error by giving
                                            exact path of Tesseract-OCR library.
                 FileNotFoundError          If the given exact library path
                                            doesn't point to existing file.
                 FileNotFoundError          If failed to found library with
                                            search process.
                 FileNotFoundError          If cannot found "tessdata" directory.
        """

        run_path = dirname(abspath(getcwd()))
        no_lib = True
        if lib_path is not None:
            if isfile(lib_path):
                no_lib = False
            else:
                raise FileNotFoundError('PyTessy: lib_path: "{}" doesn\'t exist.'
                                        .format(lib_path))
        if no_lib:
            if verbose_search:
                verbose = lambda *pa, **pk: print(*pa, **pk)
            else:
                verbose = lambda *pa, **pk: None
            if platform.startswith('win'):
                verbose('PyTessy v{} on {} searching for Tesseract-OCR library...'
                        .format(PyTessy.VERSION, platform))
                if api_version is None:
                    lib_name = 'libtesseract-5'
                else:
                    lib_name = 'libtesseract{}'.format(api_version)
                verbose('--- Target library name: {}'.format(lib_name))
                if tesseract_path is not None:
                    dirs = [tesseract_path, run_path, join(run_path, PyTessy.TESSERACT_DIRNAME)]
                else:
                    dirs = [run_path, join(run_path, PyTessy.TESSERACT_DIRNAME)]
                if 'PROGRAMFILES' in environ:
                    dirs.append(join(environ['PROGRAMFILES'], PyTessy.TESSERACT_DIRNAME))
                if 'PROGRAMFILES(X86)' in environ:
                    dirs.append(join(environ['PROGRAMFILES(X86)'], PyTessy.TESSERACT_DIRNAME))
                for dir_ in dirs:
                    test = join(dir_, '{}.dll'.format(lib_name))
                    if isfile(test):
                        lib_path = test
                        verbose('    {} SUCCESS.'.format(test))
                        break
                    else:
                        verbose('    {} FAILED.'.format(test))
                if lib_path is None:
                    raise FileNotFoundError('Cannot locate Tesseract-OCR library.')
            elif platform.startswith('linux'):
                find_program = find_executable('tesseract')
                if len(find_program) == 0:
                    raise FileNotFoundError('Cannot locate Tesseract-OCR library.')
                else:
                    lib_path = 'tesseract'
                    data_path = "/usr/share/tessdata/"
            elif platform.startswith('darwin'):
                raise NotImplementedError('PyTessy: Library search on MacOS is not implemented yet.')
            else:
                raise NotImplementedError('PyTessy: Library search on this system is not implemented.')
        tess_path = dirname(abspath(lib_path))
        no_tessdata = True
        if data_path is not None:
            if isdir(data_path):
                no_tessdata = False
        if no_tessdata:
            for test_path in [run_path, join(run_path, PyTessy.TESSERACT_DIRNAME), tess_path]:
                test_path = join(test_path, PyTessy.TESSDATA_DIRNAME)
                if isdir(test_path):
                    data_path = test_path
                    break
            if data_path is None:
                raise FileNotFoundError('PyTessy: Couldn\'t find "tessdata" directory.')
        orig_path = getcwd()
        chdir(tess_path)
        self._tess = TesseractHandler(lib_path=lib_path, data_path=data_path,
                                      language=language)
        chdir(orig_path)

    def justread(self, raw_image_ctypes, width, height, bytes_per_pixel,
                 bytes_per_line, resolution=96, psm=None):
        """
        Reads text as utf-8 string from raw image data without any check
        ----------------------------------------------------------------
        @Params: raw_image_ctypes (ctypes int array)  Raw image data.
                 width            (int)               Image width.
                 height           (int)               Image height.
                 bytes_per_pixel  (int)               Number of bytes per pixel.
                 bytes_per_line   (int)               Number of bytes per line.
                 resolution       (int)               [optional] Resolution in
                                                      dpi. Default: 96.
                 psm              (int)               [optional] Page Segmentation
                                                      Mode as per TessPageSegMode
                                                      enum (see set_psm method)
        @Return: (string)                             Text read by Tesseract-OCR
                                                      as utf-8 string.
        """

        if psm is None:
            psm = self.get_psm()

        self._tess.set_psm(psm)
        self._tess.set_image(raw_image_ctypes, width, height, bytes_per_pixel,
                             bytes_per_line, resolution)
        return self._tess.get_text()

    def justread_raw(self, raw_image_ctypes, width, height, bytes_per_pixel,
                     bytes_per_line, resolution=96, psm=None):
        """
        Reads text as raw bytes data from raw image data without any check
        ------------------------------------------------------------------
        @Params: raw_image_ctypes (ctypes int array)  Raw image data.
                 width            (int)               Image width.
                 height           (int)               Image height.
                 bytes_per_pixel  (int)               Number of bytes per pixel.
                 bytes_per_line   (int)               Number of bytes per line.
                 resolution       (int)               [optional] Resolution in
                                                      dpi. Default: 96.
                 psm              (int)               [optional] Page Segmentation
                                                      Mode as per TessPageSegMode
                                                      enum (see set_psm method)
        @Return: (bytes)                              Text read by Tesseract-OCR
                                                      as raw bytes data.
        """

        if psm is None:
            psm = self.get_psm()

        self._tess.set_psm(psm)
        self._tess.set_image(raw_image_ctypes, width, height, bytes_per_pixel,
                             bytes_per_line, resolution)
        return self._tess.get_text_raw()

    def read(self, imagedata, width, height, bytes_per_pixel, resolution=96,
             raw=False, psm=None):
        """
        Reads text from image data
        --------------------------
        @Params: imagedata        (ctypes int array)  Raw image data.
                 width            (int)               Image width.
                 height           (int)               Image height.
                 bytes_per_pixel  (int)               Number of bytes per pixel.
                 resolution       (int)               [optional] Resolution in
                                                      dpi. Default: 96.
                 raw              (boolean)           [optional] Whether to read
                                                      in raw or utf-8 mode.
                 psm              (int)               [optional] Page Segmentation
                                                      Mode as per TessPageSegMode
                                                      enum (see set_psm method)
        @Return: (bytes) or (string)                  Text read by Tesseract-OCR
        """

        if psm is None:
            psm = self.get_psm()

        bytes_per_line = width * bytes_per_pixel
        if raw:
            return self.justread_raw(imagedata, width, height, bytes_per_pixel,
                                     bytes_per_line, resolution, psm)
        else:
            return self.justread(imagedata, width, height, bytes_per_pixel,
                                 bytes_per_line, resolution, psm)

    def readnp(self, imagedata: np.ndarray, resolution=96, raw=False, psm=None):
        """
        Reads text from image data contained in a numpy ndarray
        --------------------------
        @Params: imagedata   (np.ndarray)  Raw image data in a numpy ndarray.
                 resolution  (int)         [optional] Resolution in dpi.
                                           Default: 96.
                 raw         (boolean)     [optional] Whether to read
                                           in raw or utf-8 mode.
                 psm         (int)         [optional] Page Segmentation
                                           Mode as per TessPageSegMode
                                           enum (see set_psm method)
        @Return: (bytes) or (string)       Text read by Tesseract-OCR
        """
        if len(imagedata.shape) == 2:  # greyscale picture
            height, width = imagedata.shape
            bytes_per_pixel = 1
        elif len(imagedata.shape) == 3:  # 24 or 32 bits color picture
            height, width, bytes_per_pixel = imagedata.shape
        else:
            raise PyTessyError('imagedata should be 3- or 2- dimensional numpy ndarray')

        if psm is None:
            psm = self.get_psm()

        return self.read(imagedata.ctypes, width, height, bytes_per_pixel, resolution, raw, psm)

    def set_psm(self, psm):
        """
        Sets Page Segmentation Mode, as per TessPageSegMode enum:
        ------------------
        @Params: psm (int) Page Segmentation Mode, as per TessPageSegMode enum
        """
        self._tess.set_psm(psm)

    def get_psm(self):
        """
        Gets Page Segmentation Mode, as per TessPageSegMode enum:
        ------------------
        @Return: psm (int) Page Segmentation Mode, as per TessPageSegMode enum
        """
        return self._tess.get_psm()

    def set_variable(self, key, val):
        """
        Set the value of an internal parameter.
        Supply the name of the parameter and the value as a string, just as
        you would in a config file.
        Eg set_variable("tessedit_char_blacklist", "xyz"); to ignore x, y and z.
        Or set_variable("classify_bln_numeric_mode", "1"); to set numeric-only mode.
        SetVariable may be used before Init, but settings will revert to
        defaults on End().
        @Params: key (str) Variable name
                 val (str) Variable value
        @Return: (bool) ``False`` if the name lookup failed.
        """
        return self._tess.set_variable(key, val)

    def mean_text_conf(self):
        """
        @Return: (int) average confidence value between 0 and 100.
        """
        return self._tess.mean_text_conf()


if __name__ == '__main__':
    print('This is a module not a script.')
